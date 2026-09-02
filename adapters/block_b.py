# -*- coding: utf-8 -*-
"""Phase 2 · Block B 管线驱动器（分析结果产出；本地只做编排 + 收发，计算上 coze）。

设计约束（对齐 contracts/pipeline_stage/v1.0.0/SPEC.md §9 / 架构终态原则 2026-09-01）：

- **coze = 唯一计算真相源**：B1 计算经 coze_client.run_stage 发往 ct-meta2 R 引擎（23 图/NMA/TSA）。
  本地不保留独立计算引擎；coze 未授权/失败 → 返回结构化错误，绝不回退本地（ct-base §5 授权门控）。
- **本地仅编排 + 收发**：本模块构造信封、调用 run_stage、消费返回 stats、驱动 B1→B2→B3→B4 阶段
  序列与 HITL 软停靠/红线闸。B1 的 pairwise 由 coze 产出，stats 经 _coze_stats_to_pairwise 映射为
  本地 pairwise 形状（对数尺度同构），供 B2/B3/B4 原样消费（零行为变更）。
- **b1_pairwise_python 仅回归/调试 oracle**（engine="local"），非运行路径，不进入发布计算。
- **NMA 暂本地 R**（b1_nma_r，待迁 coze）；B2 GRADE / B3 过度声明 / B4 质量门为本地启发式，
  同为待迁 coze 的计算大脑（见 contracts/migration）。
- B3 过度声明检测为**单点实现**，被 B4（质量门）与 C2（AI 评审，Phase 3）复用。
- 阶段序列（SPEC §9）：
    B1.meta_analysis      双范式 meta 分析（pairwise + NMA）
    B2.grade              半自动 GRADE
    B3.overclaim          过度声明检测（12 模式）
    B4.quality_gate       质量门三重（GRADE + 过度声明 + 人工闸），🔴 final_inclusion 红线
- 返回结构与 run_pipeline / run_block_a 同构：{done, await_human, gate, final, stages[],
  attachments[], tool_card_outputs[]}，便于上层统一消费。

依赖：coze_client（CONTRACT_VERSION / STAGE_SCHEMA_ID / _REDLINE_GATES / run_stage / AuthRequiredError）。
网络/R 动作在 b1_nma_r（本地 R）与 coze_client.run_stage（coze R）内部，测试可 monkeypatch。
"""

import json
import math
import os
import re
import subprocess
import tempfile
import uuid

import numpy as np

import coze_client as cc

# 本机唯一正确的 R（见用户内存 LRN：C:/Tools/R-4.6.1/bin/Rscript.exe）
R_BIN = "C:/Tools/R-4.6.1/bin/Rscript.exe"

# ---- Block B 阶段 ID（SPEC §9，严格匹配 coze 端编排对齐） ----
B1 = "B1.meta_analysis"
B2 = "B2.grade"
B3 = "B3.overclaim"
B4 = "B4.quality_gate"
BLOCK_B_SEQUENCE = [B1, B2, B3, B4]
BLOCK_B_TOTAL = len(BLOCK_B_SEQUENCE)

# 效应量零值（用于 CI 是否跨零判断）：OR/HR/RR 类零值=1，MD/SMD 类零值=0
_EFFECT_NULL = {"OR": 1.0, "HR": 1.0, "RR": 1.0, "MD": 0.0, "SMD": 0.0, "RD": 0.0}


# ---------------------------------------------------------------------------
# 信封构造（本地「prompt → 合法入参」层）
# ---------------------------------------------------------------------------
def build_block_b_env(extracted_data=None, effect_measure="OR",
                      pipeline_id=None, query_origin=None):
    env = {
        "contract_version": cc.CONTRACT_VERSION,
        "schema": cc.STAGE_SCHEMA_ID,
        "pipeline_id": pipeline_id or f"blkB-{uuid.uuid4().hex[:8]}",
        "pipeline": {"name": "block_b", "block": "B", "cfg": {}},
        "request_id": str(uuid.uuid4()),
        "task": "meta_analysis",
        "params": {"effect_measure": effect_measure},
        "stage": {"id": B1, "index": 0, "total": BLOCK_B_TOTAL,
                  "intent": "run", "prev_stage_id": None},
        "stage_context": {"human_decisions": [], "tool_card_outputs": [], "artifacts": []},
    }
    if extracted_data is not None:
        env["params"]["extracted_data"] = extracted_data
    if query_origin:
        env["query_origin"] = query_origin
    return env


# ---------------------------------------------------------------------------
# 阶段响应构造（与 parse_stage_response 输出同构）
# ---------------------------------------------------------------------------
def _mk_stage(sid, index, status, stage_result, nha, tool_cards=None):
    nha = nha or {}
    return {
        "mode": "stage",
        "stage": {"id": sid, "index": index, "total": BLOCK_B_TOTAL, "status": status,
                  "prev_stage_id": BLOCK_B_SEQUENCE[index - 1] if index > 0 else None},
        "stage_result": stage_result,
        "next_human_action": nha,
        "tool_cards": tool_cards or [],
        "_gate_blocked": bool(
            nha.get("gate") in cc._REDLINE_GATES and nha.get("required")
        ),
    }


# ---------------------------------------------------------------------------
# B1 meta 分析：pairwise（纯 Python 主引擎）+ NMA（本地 R netmeta，优雅降级）
# ---------------------------------------------------------------------------
def _study_to_te_set(study, effect_measure):
    """把单条研究归一为 (TE, seTE)。支持 2x2（事件/样本）或预计算 (TE, seTE)。"""
    if "TE" in study and "seTE" in study:
        return float(study["TE"]), float(study["seTE"])
    # 2x2 表：ai=试验组事件, bi=试验组样本, ci=对照组事件, di=对照组样本
    a = float(study.get("ai", study.get("event_e", 0)))
    b = float(study.get("bi", study.get("n_e", 0)))
    c = float(study.get("ci", study.get("event_c", 0)))
    d = float(study.get("di", study.get("n_c", 0)))
    if b <= 0 or d <= 0:
        return None
    # Haldane-Anscombe 0.5 校正避免 0 单元格
    a, c = a + 0.5, c + 0.5
    b, d = b + 0.5, d + 0.5
    if effect_measure in ("OR", "HR", "RR"):
        TE = math.log((a * d) / (b * c))
        se = math.sqrt(1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    else:  # 连续型 MD
        m1 = float(study.get("mean_e", 0)); m2 = float(study.get("mean_c", 0))
        s1 = float(study.get("sd_e", 0)); s2 = float(study.get("sd_c", 0))
        n1 = b; n2 = d
        TE = m1 - m2
        se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
    return TE, se


def b1_pairwise_python(studies, effect_measure="OR"):
    """逆方差加权 pairwise meta 分析（固定+随机效应，DerSimonian-Laird）。

    ⚠️ **仅回归 / 调试 oracle（engine="local"），非运行路径**：架构终态原则（2026-09-01）规定
    coze 为唯一计算真相源，运行路径 B1 走 coze R 引擎、绝不回退本地。本函数保留作离线确定性
    回归基线 / deploy_retest 对照，不进入发布计算。

    返回 {k, TE_fixed, se_fixed, ci_fixed, p_fixed, TE_random, se_random, ci_random,
    p_random, tau2, I2, Q, forest[]}。纯 numpy，确定性、可离线测。CI 为对数尺度（TE=log OR/RR）。
    """
    pairs = []
    for s in studies:
        if not isinstance(s, dict):
            continue
        r = _study_to_te_set(s, effect_measure)
        if r is None:
            continue
        pairs.append(r)
    k = len(pairs)
    if k == 0:
        return {"k": 0, "error": "无可计算研究"}
    TE = np.array([p[0] for p in pairs], dtype=float)
    se = np.array([p[1] for p in pairs], dtype=float)
    w = 1.0 / (se ** 2)  # 固定效应权重
    # 固定效应
    TE_fe = float(np.sum(w * TE) / np.sum(w))
    se_fe = float(1.0 / math.sqrt(np.sum(w)))
    # Q 统计量与 DL 随机效应
    Q = float(np.sum(w * (TE - TE_fe) ** 2))
    df = max(k - 1, 1)
    C = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
    w_re = 1.0 / (se ** 2 + tau2)  # 随机效应权重
    TE_re = float(np.sum(w_re * TE) / np.sum(w_re))
    se_re = float(1.0 / math.sqrt(np.sum(w_re)))
    I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0
    z_re = TE_re / se_re
    p_re = 2 * (1 - _norm_cdf(abs(z_re)))
    z_fe = TE_fe / se_fe
    p_fe = 2 * (1 - _norm_cdf(abs(z_fe)))
    ci_re = (TE_re - 1.96 * se_re, TE_re + 1.96 * se_re)
    ci_fe = (TE_fe - 1.96 * se_fe, TE_fe + 1.96 * se_fe)
    forest = [{"TE": float(t), "seTE": float(s), "w_fixed": float(wi), "w_random": float(wri)}
              for t, s, wi, wri in zip(TE, se, w, w_re)]
    return {
        "k": k, "effect_measure": effect_measure, "engine": "python",
        "TE_fixed": TE_fe, "se_fixed": se_fe,
        "ci_fixed": [ci_fe[0], ci_fe[1]], "p_fixed": p_fe,
        "TE_random": TE_re, "se_random": se_re,
        "ci_random": [ci_re[0], ci_re[1]], "p_random": p_re,
        "tau2": tau2, "I2": I2, "Q": Q, "df": df, "forest": forest,
    }


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# 本地 R netmeta 脚本（NMA）。输入 JSON：{TE[],seTE[],t1[],t2[],studlab[],sm,reference}；输出 JSON。
# 适配 netmeta 3.6-1：参数名 TE/seTE（大写）、reference.group；NMA 结果分 .common(一致) /
# .random(不一致，netmeta 默认) 两套，须显式取其一；res$comparisons 为 "t1:t2" 标签向量。
_NMA_R_SCRIPT = r"""
library(jsonlite); library(netmeta)
# 2026-09-02：与 coze 镜像 run_task.R 一致，强制 UTF-8 locale。本地 R 默认 C locale 下
# 中文干预名（如「安慰剂」）会乱码，导致 netmeta reference.group 匹配失败；
# en_US.UTF-8 在 Windows R 4.2+ 自动映射系统 UTF-8（实测有效）。须在 fromJSON 前设置。
try(Sys.setlocale("LC_CTYPE", "en_US.UTF-8"), silent = TRUE)
try(Sys.setlocale("LC_ALL", "en_US.UTF-8"), silent = TRUE)
a <- fromJSON(commandArgs(trailingOnly=TRUE)[1])
sm <- if (is.null(a$sm)) "OR" else a$sm
ref <- if (is.null(a$reference)) NULL else a$reference
# reference.group 为 NULL 时 netmeta 3.6-1 会在 `== ""` 判定上崩（length zero），
# 故仅在非 NULL 时加入该参数（do.call 条件构造调用）。
nma_args <- list(TE = a$TE, seTE = a$seTE, treat1 = a$t1, treat2 = a$t2,
                 studlab = a$studlab, sm = sm)
if (!is.null(ref)) nma_args$reference.group <- ref
res <- do.call(netmeta, nma_args)
# 优先 random-effects NMA（netmeta 默认），回退 consistent (common)
# 2026-09-02 修复：netmeta 的 res$comparisons 为「唯一干预对」(m_unique)，
# 而 res$TE.nma.random 等按「输入对比」(m_input) 对齐——多研究共享同一对时 m_input>m_unique。
# 旧代码把二者直接 zip → "differing number of rows" 崩溃。正确做法：以输入 treat1/treat2
# (m_input) 为标签基准对齐估计向量，再按唯一干预对去重（网络估计本就是 per-pair）。
te   <- if (!is.null(res$TE.nma.random))  res$TE.nma.random  else res$TE.nma.common
sete <- if (!is.null(res$seTE.nma.random)) res$seTE.nma.random else res$seTE.nma.common
lo   <- if (!is.null(res$lower.nma.random)) res$lower.nma.random else res$lower.nma.common
hi   <- if (!is.null(res$upper.nma.random)) res$upper.nma.random else res$upper.nma.common
pv   <- if (!is.null(res$pval.nma.random)) res$pval.nma.random else res$pval.nma.common
if (length(te) == length(res$treat1)) {        # 估计向量按输入对比对齐（netmeta 3.6.x 实测）
  lbl_t1 <- res$treat1; lbl_t2 <- res$treat2
} else {                                         # 退化：估计向量按唯一对对齐
  pr <- strsplit(as.character(res$comparisons), ":")
  lbl_t1 <- sapply(pr, function(x) x[1]); lbl_t2 <- sapply(pr, function(x) x[2])
}
keep <- !duplicated(paste(lbl_t1, lbl_t2, sep = ":"))   # 唯一干预对只报一次网络估计
t1o <- lbl_t1[keep]; t2o <- lbl_t2[keep]
trx <- if (!is.null(res$trts)) res$trts else sort(unique(c(res$treat1, res$treat2)))
out <- list(
  model = if (!is.null(res$TE.nma.random)) "random" else "common",
  n_treatments = length(trx),
  treatments = trx,
  tau = if (is.null(res$tau)) NA_real_ else res$tau,
  comparisons = data.frame(t1 = t1o, t2 = t2o, TE = te[keep], seTE = sete[keep],
                           ci_low = lo[keep], ci_high = hi[keep], p = pv[keep],
                           stringsAsFactors = FALSE)
)
write_json(out, commandArgs(trailingOnly=TRUE)[2])
"""


def b1_nma_r(network_studies, effect_measure="OR", reference=None):
    """本地 R netmeta 真实 NMA。network_studies = [{t1,t2,TE,seTE,studlab}]。
    失败/缺 R/缺包 → 返回 {status:'error'/'skipped', reason}（不抛）。"""
    if not network_studies:
        return {"status": "skipped", "reason": "无网络数据"}
    try:
        data = {
            "TE": [float(s["TE"]) for s in network_studies],
            "seTE": [float(s["seTE"]) for s in network_studies],
            "t1": [str(s["t1"]) for s in network_studies],
            "t2": [str(s["t2"]) for s in network_studies],
            "studlab": [str(s.get("studlab", f"S{i}")) for i, s in enumerate(network_studies)],
            "sm": effect_measure, "reference": reference,
        }
        with tempfile.TemporaryDirectory() as td:
            inp = os.path.join(td, "nma_in.json")
            outp = os.path.join(td, "nma_out.json")
            with open(inp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            rfile = os.path.join(td, "nma.R")
            with open(rfile, "w", encoding="utf-8") as f:
                f.write(_NMA_R_SCRIPT)
            proc = subprocess.run([R_BIN, rfile, inp, outp], capture_output=True,
                                 text=True, timeout=120)
            if proc.returncode != 0:
                return {"status": "error", "reason": f"R exit {proc.returncode}: {proc.stderr[:300]}"}
            if not os.path.isfile(outp):
                return {"status": "error", "reason": "netmeta 未产出结果文件"}
            with open(outp, encoding="utf-8") as f:
                res = json.load(f)
        return {"status": "ok", "engine": "R_netmeta", "result": res}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "reason": f"{type(e).__name__}: {e}"}


def _norm_b1_rows(studies):
    """A4/抽取产出的 ai/bi/ci/di（事件/非事件，pdf_extractor 原生） → R 引擎 metabin 约定
    event_exp/n_exp/event_ctrl/n_ctrl（事件/总数）。

    - 已含 event_exp/n_exp/event_ctrl/n_ctrl 的行原样透传（兼容演示/手动数据路径）。
    - 形如 TE/seTE 的预计算行原样透传（R 引擎单独处理）。
    - 仅含 ai/bi/ci/di 的行做换算：event_exp=ai, n_exp=ai+bi, event_ctrl=ci, n_ctrl=ci+di。
    幂等：重复调用不会重复换算（一旦已含 event_exp 即透传）。
    """
    out = []
    for s in (studies or []):
        if not isinstance(s, dict):
            out.append(s)
            continue
        if all(k in s for k in ("event_exp", "n_exp", "event_ctrl", "n_ctrl")):
            out.append(s)
            continue
        if all(k in s for k in ("ai", "bi", "ci", "di")):
            try:
                ai, bi, ci, di = (float(s["ai"]), float(s["bi"]),
                                  float(s["ci"]), float(s["di"]))
                r = dict(s)
                r["event_exp"] = ai
                r["n_exp"] = ai + bi
                r["event_ctrl"] = ci
                r["n_ctrl"] = ci + di
                out.append(r)
                continue
            except (TypeError, ValueError):
                pass
        out.append(s)
    return out


def _build_b1_coze_env(studies, effect_measure):
    """构造 B1.meta_analysis 计算阶段信封（对齐 run_analysis._build_compute_stage_env）。

    studies 经 _norm_b1_rows 归一：A4 抽取的 ai/bi/ci/di（事件/非事件）自动换算为
    R 引擎 metabin 约定的 event_exp/n_exp/event_ctrl/n_ctrl（事件/总数），实现 A4→B1 真正闭环。
    """
    return {
        "task": "pairwise_meta",
        "data": _norm_b1_rows(studies),
        "params": {"effect_measure": effect_measure},
        "figure": {},
        "contract_version": cc.CONTRACT_VERSION,
        "schema": cc.STAGE_SCHEMA_ID,
        "pipeline_id": f"blkB-{uuid.uuid4().hex[:8]}",
        "pipeline": {"name": "block_b", "block": "B", "cfg": {}},
        "stage": {"id": B1, "index": 0, "total": BLOCK_B_TOTAL,
                  "intent": "run", "prev_stage_id": None},
        "stage_context": {"human_decisions": [], "tool_card_outputs": [], "artifacts": []},
        "query_origin": cc._default_query_origin(),
    }


def _extract_coze_stats(resp):
    """从 run_stage 返回信封中抽取 coze R 引擎的 stats（兼容顶层 stats 与 stage_result.result.stats）。"""
    if not isinstance(resp, dict):
        return None
    sr = resp.get("stage_result")
    if isinstance(sr, dict):
        inner = sr.get("result")
        if isinstance(inner, dict) and "stats" in inner:
            return inner["stats"]
    if "stats" in resp:
        return resp["stats"]
    return None


def _coze_stats_to_pairwise(stats, effect_measure):
    """coze R 引擎 stats → 本地 pairwise 形状（与 b1_pairwise_python 同构，CI 保持对数尺度），
    供 B2/B3/B4 原样消费，零行为变更。

    coze stats 结构：{k, model, sm, pooled:{estimate,ci_low,ci_high,p,unit,...},
    heterogeneity:{I2,tau2,H2,Q,Q_p}, bias:{...}, quality_gate:{...}}
    """
    if not isinstance(stats, dict):
        return {"k": 0, "error": "coze 未返回有效 stats"}
    pooled = stats.get("pooled") or {}
    het = stats.get("heterogeneity") or {}
    em = stats.get("sm") or effect_measure
    ci_low, ci_high, te, p = (pooled.get("ci_low"), pooled.get("ci_high"),
                              pooled.get("estimate"), pooled.get("p"))
    ci = [ci_low, ci_high] if (ci_low is not None and ci_high is not None) else None
    se = None
    if ci is not None and te is not None:
        half = (ci_high - ci_low) / 2.0
        if half > 0:
            se = half / 1.96
    return {
        "k": int(stats.get("k", 0) or 0),
        "effect_measure": em,
        "engine": "coze",
        "TE_fixed": te, "se_fixed": se,
        "ci_fixed": list(ci) if ci else None,
        "p_fixed": p,
        "TE_random": te, "se_random": se,
        "ci_random": list(ci) if ci else None,
        "p_random": p,
        "tau2": het.get("tau2"), "I2": het.get("I2"),
        "Q": het.get("Q"), "df": max(int(stats.get("k", 0) or 1) - 1, 1),
        "forest": [],
    }


def b1_meta_analysis(studies, effect_measure="OR", engine="coze", nma=False,
                     network_studies=None, nma_reference=None):
    """B1 双范式 meta 分析。

    - 默认 engine="coze"：B1 计算经 coze_client.run_stage 发往 ct-meta2 R 引擎（唯一计算真相源），
      stats 经 _coze_stats_to_pairwise 映射为本地 pairwise 形状，供 B2/B3/B4 原样消费。
      coze 未授权 / 失败 → 返回结构化错误，绝不回退本地（ct-base §5 授权门控；原则：本地不保留计算引擎）。
    - engine="local"（显式、仅回归 / 调试用，非运行路径）：走 b1_pairwise_python 本地 numpy 确定性实现。
    - NMA：nma=True 且提供 network_studies 时暂走本地 R netmeta（待迁 coze，见迁移规格）；否则 skipped。

    返回 {pairwise{...}, nma{...}, effect_measure, notes[], _source}。
    """
    notes = []
    if engine == "local":  # 回归/调试专用，非运行路径
        pairwise = b1_pairwise_python(studies, effect_measure)
        if pairwise.get("k", 0) == 0:
            notes.append("pairwise：无可计算研究（请检查 ai/bi/ci/di 或 TE/seTE 字段）。")
        nma_res = _nma_branch(nma, network_studies, effect_measure, notes, nma_reference)
        return {"effect_measure": effect_measure, "pairwise": pairwise,
                "nma": nma_res, "notes": notes, "_source": "local"}

    # 默认 coze-only（唯一计算真相源）
    try:
        env = _build_b1_coze_env(studies, effect_measure)
        resp = cc.run_stage(env)
        stats = _extract_coze_stats(resp)
        if stats is None:
            return {"effect_measure": effect_measure,
                    "pairwise": {"k": 0, "error": "coze 未返回 stats"},
                    "nma": {"status": "skipped", "reason": "B1 coze 无 stats"},
                    "notes": ["coze 响应缺 stats"], "_source": "coze_error"}
        pairwise = _coze_stats_to_pairwise(stats, effect_measure)
        if pairwise.get("k", 0) == 0:
            notes.append("pairwise：coze 返回无可计算研究。")
        nma_res = _nma_branch(nma, network_studies, effect_measure, notes, nma_reference)
        return {"effect_measure": effect_measure, "pairwise": pairwise,
                "nma": nma_res, "notes": notes, "_source": "coze"}
    except cc.AuthRequiredError as e:
        return {"effect_measure": effect_measure, "pairwise": {"k": 0, "error": "auth_blocked"},
                "nma": {"status": "skipped", "reason": "auth_blocked"},
                "notes": [f"未授权出站（ct-base §5 授权门控）：{e}"],
                "_source": "auth_blocked", "_auth_required": True}
    except Exception as e:
        return {"effect_measure": effect_measure, "pairwise": {"k": 0, "error": f"coze_error: {e}"},
                "nma": {"status": "skipped", "reason": "coze_error"},
                "notes": [f"coze 调用失败：{type(e).__name__}: {e}"], "_source": "coze_error"}


def _nma_branch(nma, network_studies, effect_measure, notes, reference=None):
    """NMA 分支（暂本地 R netmeta，待迁 coze）。返回与旧 nma_res 同构的 dict。"""
    nma_res = {"status": "skipped", "reason": "nma=False 或未提供 network_studies"}
    if nma:
        if network_studies:
            nma_res = b1_nma_r(network_studies, effect_measure, reference=reference)
            if nma_res.get("status") != "ok":
                notes.append(f"NMA 降级：{nma_res.get('reason')}")
        else:
            notes.append("未提供 network_studies，跳过 NMA（仅 pairwise）。")
    return nma_res


# ---------------------------------------------------------------------------
# B2 半自动 GRADE（启发式；κ=0.44 仅半自动，须经人工）
# ---------------------------------------------------------------------------
def b2_grade(pairwise, risk_of_bias="moderate", indirectness="none",
             publication_bias="none"):
    """从 B1 输出 + 领域标记推导 GRADE 草表。起点 HIGH，按 5 域降级。

    降级规则（启发式，须人工确认）：
      - 不一致性：I2 >= 75% → -2（very serious），>=50% → -1（serious），>=25% → -0.5
      - 不精确：k<3 或 CI 跨零 → -1
      - 偏倚风险：high → -1，moderate → -0.5
      - 间接性：serious → -1
      - 发表偏倚：serious → -1
    返回 {grade, reasons[], domain_ratings{}}。
    """
    I2 = float(pairwise.get("I2", 0.0) or 0.0)
    k = int(pairwise.get("k", 0) or 0)
    ci = pairwise.get("ci_random") or pairwise.get("ci_fixed") or [0, 0]
    crosses_null = (ci[0] < 1.0 < ci[1]) if pairwise.get("effect_measure") in ("OR", "HR", "RR") \
        else (ci[0] < 0 < ci[1])

    reasons = []
    domain = {}
    down = 0.0

    # 不一致性
    if I2 >= 75:
        down += 2; domain["inconsistency"] = "very serious"; reasons.append(f"不一致性很严重（I²={I2:.0f}% → -2）")
    elif I2 >= 50:
        down += 1; domain["inconsistency"] = "serious"; reasons.append(f"不一致性严重（I²={I2:.0f}% → -1）")
    elif I2 >= 25:
        down += 0.5; domain["inconsistency"] = "some"; reasons.append(f"不一致性中等（I²={I2:.0f}% → -0.5）")
    else:
        domain["inconsistency"] = "not serious"

    # 不精确
    if k < 3:
        down += 1; domain["imprecision"] = "serious"; reasons.append(f"样本研究少（k={k} → -1）")
    elif crosses_null:
        down += 1; domain["imprecision"] = "serious"; reasons.append("效应估计 CI 跨零（不精确 → -1）")
    else:
        domain["imprecision"] = "not serious"

    # 偏倚风险
    if risk_of_bias == "high":
        down += 1; domain["risk_of_bias"] = "serious"; reasons.append("偏倚风险高（→ -1）")
    elif risk_of_bias == "moderate":
        down += 0.5; domain["risk_of_bias"] = "some"; reasons.append("偏倚风险中等（→ -0.5）")
    else:
        domain["risk_of_bias"] = "not serious"

    if indirectness == "serious":
        down += 1; domain["indirectness"] = "serious"; reasons.append("间接性严重（→ -1）")
    else:
        domain["indirectness"] = indirectness

    if publication_bias == "serious":
        down += 1; domain["publication_bias"] = "serious"; reasons.append("发表偏倚严重（→ -1）")
    else:
        domain["publication_bias"] = publication_bias

    # 映射降级档位 → GRADE
    if down == 0:
        grade = "High"
    elif down <= 1:
        grade = "Moderate"
    elif down <= 2:
        grade = "Low"
    else:
        grade = "VeryLow"
    return {"grade": grade, "downgrades": down, "reasons": reasons,
            "domain_ratings": domain, "coze_ready": False,
            "note": "半自动 GRADE（κ=0.44 仅半自动），须人工确认各域评级。"}


# ---------------------------------------------------------------------------
# B3 过度声明检测（12 模式；被 B4 / C2 复用）
# ---------------------------------------------------------------------------
# (pattern_id, label, severity, regex/keyword, 需 CI 跨零辅助判定)
_OVERCLAIM_PATTERNS = [
    ("OC1", "绝对化治愈/根治/革命性措辞", "high",
     r"治愈|根治|完全治愈|cure|revolutionary|breakthrough|革命性|颠覆"),
    ("OC2", "声称显著但 CI 跨零", "high",
     r"显著|显著改善|significant|明显降低|明显减少", "ci_cross"),
    ("OC3", "称无差异但 p<0.05", "high",
     r"无差异|无统计学差异|相当|no difference|equivalent", "p_sig"),
    ("OC4", "称优效但 CI 重叠（跨零）", "medium",
     r"优于|显著优于|superior|胜过", "ci_cross"),
    ("OC5", "亚组结论外推总体", "medium",
     r"亚组|subset|亚人群", "to_all"),
    ("OC6", "首个/首创声明（待核实）", "low",
     r"首个|首例|first-in-class|first"),
    ("OC7", "极端 100%/完全", "medium",
     r"100%|完全|彻底|completely|entirely"),
    ("OC8", "以 p 值替代效应量", "low",
     r"p\s*[<≤]\s*0\.0?\d+"),
    ("OC9", "事后亚组作为主要结论", "low",
     r"事后|post[- ]?hoc|探索性亚组"),
    ("OC10", "以非劣效检验不显著推断非劣", "high",
     r"非劣|non-?inferior", "ns"),
    ("OC11", "绝对安全/无副作用", "medium",
     r"安全无副作用|无副作用|safe|没有任何不良反应"),
    ("OC12", "自称 meta 分析但证据薄弱", "medium",
     r"meta|荟萃|系统评价", "weak_meta"),
]


def detect_overclaims(claims_text, stats=None):
    """检测文本中的过度声明（12 模式）。stats 来自 B1：{effect_measure, ci_random/ci_fixed,
    p_random/p_fixed, k, I2}。返回命中列表 [{id,label,severity,evidence}]（被 B4/C2 复用）。"""
    stats = stats or {}
    text = (claims_text or "").lower()
    em = stats.get("effect_measure", "OR")
    ci = stats.get("ci_random") or stats.get("ci_fixed")
    p = stats.get("p_random") if stats.get("p_random") is not None else stats.get("p_fixed")
    k = stats.get("k", 0)
    I2 = stats.get("I2", 0.0)
    # CI 是否跨零（OR/HR/RR 零值=1；MD 零值=0）
    null = _EFFECT_NULL.get(em, 1.0)
    ci_cross = bool(ci and (ci[0] < null < ci[1]))
    hits = []
    for pid, label, sev, patt, *aux in _OVERCLAIM_PATTERNS:
        if not re.search(patt, text, re.IGNORECASE):
            continue
        aux_kind = aux[0] if aux else None
        evidence = label
        if aux_kind == "ci_cross" and not ci_cross:
            continue  # 需 CI 跨零但并未跨零 → 不误报
        if aux_kind == "p_sig" and not (p is not None and p < 0.05):
            continue
        if aux_kind == "ns" and not (p is not None and p >= 0.05):
            continue
        if aux_kind == "weak_meta" and not (k < 2 or I2 >= 75):
            # meta 证据薄弱：研究少或异质性极大；否则不误报
            if k >= 2 and I2 < 75:
                continue
        if aux_kind == "to_all" and "总体" not in text and "all" not in text and "整体" not in text:
            evidence += "（文中含亚组表述，请确认是否外推总体）"
        hits.append({"id": pid, "label": label, "severity": sev, "evidence": evidence})
    return hits


# ---------------------------------------------------------------------------
# B4 质量门三重（🔴 final_inclusion 红线，本地强执）
# ---------------------------------------------------------------------------
def b4_quality_gate(grade_report, overclaims):
    """质量门三重：GRADE + 过度声明 + 人工闸。

    始终产出 🔴 final_inclusion 人工闸（required=True）；若存在 high 级过度声明或 GRADE=VeryLow，
    标记 critical=True（必须人工显式批准方可放行，自动续跑被阻断）。
    """
    grade = grade_report.get("grade", "Low")
    high = [h for h in overclaims if h.get("severity") == "high"]
    critical = bool(high) or grade == "VeryLow"
    n_med = len([h for h in overclaims if h.get("severity") == "medium"])
    report = {
        "grade": grade,
        "n_overclaim": len(overclaims),
        "n_high": len(high),
        "n_medium": n_med,
        "critical": critical,
        "coze_ready": False,
        "note": "质量门三重：GRADE + 过度声明 + 人工闸。须人工显式批准方可进入 Block C 撰写。",
    }
    nha = {
        "type": "approve",
        "prompt": (f"质量门（final_inclusion）：GRADE={grade}，检出过度声明 {len(overclaims)} 条"
                   f"（high={len(high)}）。{'存在高危过度声明或极低质量证据，' if critical else ''}"
                   f"请人工核验后批准进入 Block C。"),
        "required": True,
        "gate": "final_inclusion",
    }
    return report, nha


# ---------------------------------------------------------------------------
# 人工决策判定（红线闸放行）
# ---------------------------------------------------------------------------
def _decision_approves(decision, stage_id):
    if not isinstance(decision, dict):
        return False
    return (decision.get("stage_id") == stage_id
            and str(decision.get("action", "")).lower() in ("approved", "approve"))


def _any_approve(decisions, stage_id):
    """human_decision 兼容单 dict / list（fullflow 累积凭据）；任一 approved 即 True。"""
    if isinstance(decisions, dict):
        decisions = [decisions]
    return any(_decision_approves(d, stage_id) for d in (decisions or []))


def _soft_stop(env, pid, stages, stage, sid, pause_at, decisions):
    """P3 软停靠（fullflow HITL，spec contracts/fullflow/v0.1.0）。

    pause_at 含 sid 且未持对应 approved 凭据 → 提前软停返回
    （done=False / await_human=True / gate=None / pause=True，区别于红线闸）。
    """
    if not (pause_at and sid in pause_at) or _any_approve(decisions, sid):
        return None
    return {"pipeline_id": pid, "pipeline": env["pipeline"], "stages": stages,
            "attachments": [], "tool_card_outputs": [],
            "done": False, "await_human": True, "gate": None, "final": stage,
            "pause": True, "human_decisions": []}


# ---------------------------------------------------------------------------
# 编排：B1 → B2 → B3 → B4（本地优先）
# ---------------------------------------------------------------------------
def run_block_b(studies, effect_measure="OR", nma=False, network_studies=None,
                claims_text=None, grade_inputs=None, debug=False,
                human_decision=None, pause_at=None):
    """Block B 驱动器（coze 计算 + 本地编排）。返回与 run_pipeline 同构的 dict。

    B1 计算上 coze（b1_meta_analysis 默认 engine="coze"）；B2/B3/B4 为本地启发式
    （待迁 coze，见 contracts/migration）。

    - human_decision：B4 红线闸人工放行凭据 {"stage_id": B4, "action": "approved"}
      （兼容单 dict 或 list 累积凭据）。
      未提供且 B4 闸触发 → done=False / await_human=True / gate="final_inclusion"。
    - pause_at：P3 软停靠集合（fullflow HITL）。默认 None = 现状行为（仅 B4 红线闸停）。
    """
    env = build_block_b_env(studies, effect_measure)
    pid = env["pipeline_id"]
    stages = []

    # B1（coze 计算；engine="coze" 为唯一运行路径，绝不回退本地）
    b1 = b1_meta_analysis(studies, effect_measure, engine="coze", nma=nma,
                          network_studies=network_studies)
    s1 = _mk_stage(B1, 0, "completed", {"pairwise": b1["pairwise"], "nma": b1["nma"],
                                         "effect_measure": effect_measure}, None)
    stages.append(s1)
    _st = _soft_stop(env, pid, stages, s1, B1, pause_at, human_decision)
    if _st:
        return _st

    # B2
    gi = grade_inputs or {}
    grade_rep = b2_grade(b1["pairwise"],
                        risk_of_bias=gi.get("risk_of_bias", "moderate"),
                        indirectness=gi.get("indirectness", "none"),
                        publication_bias=gi.get("publication_bias", "none"))
    s2 = _mk_stage(B2, 1, "completed", grade_rep, None)
    stages.append(s2)
    _st = _soft_stop(env, pid, stages, s2, B2, pause_at, human_decision)
    if _st:
        return _st

    # B3（stats 来自 B1 pairwise）
    pw = b1["pairwise"]
    stats = {"effect_measure": effect_measure,
             "ci_random": pw.get("ci_random"), "ci_fixed": pw.get("ci_fixed"),
             "p_random": pw.get("p_random"), "p_fixed": pw.get("p_fixed"),
             "k": pw.get("k"), "I2": pw.get("I2")}
    overclaims = detect_overclaims(claims_text or "", stats)
    s3 = _mk_stage(B3, 2, "completed", {"n_patterns": len(_OVERCLAIM_PATTERNS),
                                        "n_hits": len(overclaims), "hits": overclaims}, None)
    stages.append(s3)
    _st = _soft_stop(env, pid, stages, s3, B3, pause_at, human_decision)
    if _st:
        return _st

    # B4 — 🔴 红线闸
    b4_rep, nha4 = b4_quality_gate(grade_rep, overclaims)
    s4 = _mk_stage(B4, 3, "await_human", b4_rep, nha4)
    stages.append(s4)

    base = {
        "pipeline_id": pid, "pipeline": env["pipeline"],
        "stages": stages, "attachments": [], "tool_card_outputs": [],
    }

    gate = (s4.get("next_human_action") or {}).get("gate")
    if s4.get("_gate_blocked"):
        if _any_approve(human_decision, B4):
            return {**base, "done": True, "await_human": False, "gate": None,
                    "final": s4, "human_decisions": [human_decision]}
        return {**base, "done": False, "await_human": True, "gate": gate, "final": s4}

    return {**base, "done": True, "await_human": False, "gate": None, "final": s4}
