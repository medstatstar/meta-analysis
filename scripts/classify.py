#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify.py — meta-analysis 技能的双轨路由 / 归一化脚本

设计目标（对齐 §0 双轨门控 + 延迟不变量）：
  - 零 LLM 决策：确定性关键词表映射，LLM 不纠结"该用哪个 task / measure"。
  - 零计算：仅做字符串匹配 + 拼 JSON，绝不跑 R / Python 算任何统计量。
  - 零出网：纯本地字符串处理。
  - 对应 ct-advisor 的 scripts/route.py（一次 code 判定，LLM 不决策路由），
    但比 route.py 多输出结构化 spec，可直接喂 run_analysis.py 的 request.json。

输入：用户原始 query 字符串（命令行参数）
输出：spec JSON（stdout）
  {
    "track": "compute" | "topic",
    "task": "pairwise_meta" | "subgroup_analysis" | "metareg" | "nma" | "survival_meta" | "diagnostic_meta",
    "measure": "OR" | "RR" | "RD" | "MD" | "SMD" | "HR" | null,
    "model": "REM-L" | "MH",
    "data_type": "binary" | "continuous" | "diagnostic" | "survival" | "ipd",
    "params_extra": {"plots": [...], "subgroup": "..."},
    "needs_clarify": bool,
    "missing_fields": [str],
    "colmap": [列名建议]
  }
"""
import sys
import json
import re
import argparse


# ---- 关键词表（语言中立，不翻译）----
TOPIC_WORDS = [
    "选题", "方向", "可行性", "没方向", "没思路", "选课题", "确定课题",
    "no topic", "which topic", "decide a topic", "choose a topic",
    "feasibility", "candidate", "topic",
]
BINARY_WORDS = ["二分类", "binary", "事件", "event", "发生率", "发生数", "阳性", "反应", "risk"]
CONT_WORDS = ["连续", "continuous", "均数", "mean", "均差", "smd", "mean diff"]
DIAG_WORDS = ["诊断", "diagnostic", "sroc"]
SURV_WORDS = ["生存", "survival", "survival meta"]
IPD_WORDS = ["个体", "ipd", "raw data", "个体数据"]
HR_WORDS = ["hr", "hazard", "风险比"]          # 风险比 → 生存 HR
OR_WORDS = ["or", "odds ratio", "比值比"]
RR_WORDS = ["rr", "risk ratio", "相对危险度", "relativerisk"]
RD_WORDS = ["rd", "risk difference", "危险差"]
MD_WORDS = ["md", "mean diff", "均数差"]
SMD_WORDS = ["smd", "标准化均数差", "standardized mean difference"]
REML_WORDS = ["随机效应", "reml", "random", "异质性", "随机"]
MH_WORDS = ["固定效应", "fixed", "mh", "mantel", "固定"]
SUBGROUP_WORDS = ["亚组", "subgroup", "分层"]
METAREG_WORDS = ["元回归", "metareg", "meta regression", "回归分析"]
NMA_WORDS = ["网络", "network", "nma", "网状"]
FUNNEL_WORDS = ["漏斗", "funnel"]
EGGER_WORDS = ["发表偏倚", "egger", "begg", "pub bias", "publication bias"]

# 默认列模板（data_type → 列名建议），供 agent 套用归一化
COLMAP = {
    "binary": ["event_exp", "n_exp", "event_ctrl", "n_ctrl"],
    "continuous": ["mean_exp", "sd_exp", "n_exp", "mean_ctrl", "sd_ctrl", "n_ctrl"],
    "diagnostic": ["tp", "fp", "fn", "tn"],
    "survival": ["n_event_exp", "time_exp", "n_event_ctrl", "time_ctrl"],
    "nma": ["treatment", "event", "n"],  # classify 默认提示=arm-based 二分类；连续/对比格式由 build_request._detect_nma_format 按数据列名自动探测（见 [2.2.11]）
    "ipd": ["study", "group", "outcome"],
}


def _hit(text, words):
    t = text.lower()
    return any(w.lower() in t for w in words)


def _extract_subgroup(text):
    # 匹配「按 X / by X / 分层 X / subgroup X」，X 为亚组列名（中文或英文，1-8 字符）。
    # 用前瞻在动词/标点处断词，避免贪心吞掉「做亚组分析」等后续词
    # （旧版 {1,6} 无边界，会把「按地区做亚组分析」截成「地区做亚组分」，
    #  导致下游别名表接不住、亚组静默失效）。
    # 修复：列名字符类必须含数字 0-9 —— pdl1 / ki67 / egfr / her2 等带数字的亚组列
    # 原 [A-Za-z_\u4e00-\u9fa5] 不含数字，导致整列无法被捕获，subgroup 退化为 None、
    # build_request 静默退化为无分层主分析（隐蔽错误，会诱使 agent 反复重试）。
    # 同时 (?:...)(?:\s+by)? 吃掉「subgroup by X」里多余的 by，避免把 by 误当成列名。
    pat = re.compile(
        r'(?:按|by|分层|subgroup)(?:\s+by)?\s*([A-Za-z0-9_\u4e00-\u9fa5]{1,8}?)'
        r'(?=做|进|行|分|析|亚组|分层|的|\(|\)|，|,|\s|$|。|；|;)',
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    return m.group(1) or None


def classify(query):
    q = query or ""

    # 1) track（选题词优先级最高）
    track = "topic" if _hit(q, TOPIC_WORDS) else "compute"

    # 2) task（覆盖默认 pairwise_meta）
    if _hit(q, NMA_WORDS):
        task = "nma"
    elif _hit(q, SUBGROUP_WORDS):
        task = "subgroup_analysis"
    elif _hit(q, METAREG_WORDS):
        task = "metareg"
    elif _hit(q, SURV_WORDS) or _hit(q, HR_WORDS):
        task = "survival_meta"
    elif _hit(q, DIAG_WORDS):
        task = "diagnostic_meta"
    else:
        task = "pairwise_meta"

    # 3) data_type
    if task == "diagnostic_meta":
        data_type = "diagnostic"
    elif task == "nma":
        data_type = "nma"
    elif task == "survival_meta":
        data_type = "survival"
    elif _hit(q, CONT_WORDS):
        data_type = "continuous"
    elif _hit(q, BINARY_WORDS):
        data_type = "binary"
    elif _hit(q, IPD_WORDS):
        data_type = "ipd"
    else:
        data_type = "binary"  # 默认二分类（最常见）

    # 4) measure
    if task == "survival_meta" or _hit(q, HR_WORDS):
        measure = "HR"
    elif _hit(q, OR_WORDS):
        measure = "OR"
    elif _hit(q, RR_WORDS):
        measure = "RR"
    elif _hit(q, RD_WORDS):
        measure = "RD"
    elif _hit(q, SMD_WORDS):
        measure = "SMD"
    elif _hit(q, MD_WORDS):
        measure = "MD"
    else:
        measure = "OR" if data_type == "binary" else ("SMD" if data_type == "continuous" else None)

    # 5) model（默认随机效应 REML）
    model = "MH" if _hit(q, MH_WORDS) else "REM-L"

    # 6) plots / subgroup var（不改 task）
    params_extra = {}
    plots = []
    if _hit(q, FUNNEL_WORDS):
        plots.append("funnel")
    if _hit(q, EGGER_WORDS):
        plots.append("egger")
    subgroup = _extract_subgroup(q) if task == "subgroup_analysis" else None
    if plots:
        params_extra["plots"] = plots
    if subgroup:
        params_extra["subgroup"] = subgroup

    # 7) 数据迹象校验（仅 compute 轨需要）
    has_data = bool(re.search(r'\d+\s*/\s*\d+', q)) or (
        _hit(q, ["研究", "数据", "事件", "样本", "effect", "or=", "rr=", "hr=", "md=", "se="])
        and re.search(r'\d', q)
    )
    if track == "compute" and not has_data:
        needs_clarify = True
        missing_fields = ["study data (event/n per arm, or effect size + SE)"]
    else:
        needs_clarify = False
        missing_fields = []

    if track == "topic":
        # 选题轨：task/measure/model/data_type/colmap 无意义，置空避免误导 agent
        task = measure = model = data_type = None
        colmap = []
        params_extra = {}

    return {
        "track": track,
        "task": task,
        "measure": measure,
        "model": model,
        "data_type": data_type,
        "params_extra": params_extra,
        "needs_clarify": needs_clarify,
        "missing_fields": missing_fields,
        "colmap": COLMAP.get(data_type, []),
    }


def main():
    ap = argparse.ArgumentParser(description="meta-analysis 双轨路由/归一化（零 LLM、零计算）")
    ap.add_argument("query", help="用户原始请求字符串")
    args = ap.parse_args()
    spec = classify(args.query)
    print(json.dumps(spec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
