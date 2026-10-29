#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interpretation.py — 结果解读引擎（统计顾问层）

基于 coze 返回的 stats，生成结构化解读：结论、警告、下一步建议。
纯 Python 标准库，无外部依赖。

用法:
    from interpretation import interpret_result
    interp = interpret_result(stats, task="pairwise_meta", params={"sm": "OR"})
    # interp = {"conclusion": "...", "caveats": [...], "suggestions": [...], "reviewer_questions": [...]}

设计原则:
  - 防御性：任何字段缺失都不抛异常，fallback 到安全默认值。
  - 独立：仅依赖 stats 字典 + 少量参数，不调用外部服务。
  - 可单测：所有判定逻辑集中在 interpret_result()，便于覆盖边界。
"""

from __future__ import annotations

import contextvars
import math
from typing import Any

# 输出语言（2026-10-29）：只影响**叙述文案**，不影响任何统计口径。
# 用 contextvar 而非模块级变量：工作台在线程池里并发跑请求，全局变量会串语言。
_LANG = contextvars.ContextVar("meta_interp_lang", default="zh")


def _is_en() -> bool:
    return str(_LANG.get() or "zh").lower().startswith("en")


def _t(zh: str, en: str) -> str:
    """按当前语言取文案。"""
    return en if _is_en() else zh


def set_lang(lang) -> None:
    """设置本模块叙述层语言（zh/en）。

    2026-10-29 i18n 链路补全：本模块与 block_b 各持一个独立 _LANG ContextVar，
    此前 block_b.run_block_b 只设自己的 → _interpretation 块恒为中文（英文界面
    下 B1/B2/B3 页面的结论/建议/关键数字整块中文泄漏）。所有语言入口
    （run_block_b / demo_b_env / evaluate_quality）必须**同时**调用本函数。
    """
    _LANG.set("en" if str(lang or "zh").lower().startswith("en") else "zh")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 效应量类型分组
_RATIO_SM = frozenset({"OR", "RR", "HR", "PLO", "PLOGIT", "IRR", "RRR"})
_SM_SM = frozenset({"MD", "SMD", "ZCOR", "MC", "SMCR"})
_ALL_KNOWN_SM = _RATIO_SM | _SM_SM

# 无效值（CI 跨此值 → 差异无统计学显著性）
_NULL_VALUE: dict[str, float] = {sm: 1.0 for sm in _RATIO_SM}
_NULL_VALUE.update({sm: 0.0 for sm in _SM_SM})


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


def _safe_float(v: Any) -> float | None:
    """安全转 float；None / NaN / Inf / 非数值 → None。"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _sig_text(p: float | None) -> str:
    """p 值文本化（p < 0.001 简写）。"""
    if p is None:
        return _t("p 值缺失", "p value missing")
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}"


def _norm_i2(i2: float | None) -> float | None:
    """I² 百分比归一化（2026-10-27 端到端 bug 修复）。

    R 引擎（meta 包）按**比例**返回 I²（如 0.8879 = 88.79%），此前直接 {i2:.0f}%
    会把 0.8879 四舍五入成 1% 并误判「低异质性」。0≤i2≤1 视为比例 ×100。
    """
    if i2 is None:
        return None
    return i2 * 100.0 if 0.0 <= i2 <= 1.0 else i2


def _direction_text(sm: str, est: float) -> str:
    """效应量方向描述（OR/RR/SMD 等）。"""
    if sm in _RATIO_SM:
        if est > 1:
            return _t("提示暴露/干预组事件风险更高", "indicating a higher event risk in the exposed/intervention group")
        if est < 1:
            return _t("提示暴露/干预组事件风险更低（保护效应）", "indicating a lower event risk in the exposed/intervention group (protective effect)")
        return _t("提示两组无差异", "indicating no difference between groups")
    if sm in _SM_SM:
        if est > 0:
            return _t("提示实验组效应高于对照组", "indicating a higher effect in the experimental group than in the control group")
        if est < 0:
            return _t("提示实验组效应低于对照组", "indicating a lower effect in the experimental group than in the control group")
        return _t("提示两组无差异", "indicating no difference between groups")
    return ""


# ---------------------------------------------------------------------------
# 2026-10-27 解读强化（方案二·规则层）：效应量临床幅度分级 / 证据强度评级 /
# 通读段 narrative / 关键数字 key_numbers。全部纯规则、可单测，LLM 层只做叙述。
# ---------------------------------------------------------------------------


def _cohen_text(sm: str, est: float | None) -> str:
    """效应量临床幅度分级（规则层）。

    - SMD/MD 类：Cohen 标准（|0.2| 小 / |0.5| 中 / |0.8| 大）；
    - OR/RR 类：按离无效值 1 的距离粗分（1.2-1.5 边缘 / 1.5-2.5 中等 / >2.5 强）。
    """
    if est is None:
        return ""
    if sm in _SM_SM:
        a = abs(est)
        if a < 0.2:
            return _t(f"效应幅度很小（|{sm}| = {a:.2f} < 0.2，Cohen 标准下限）",
                      f"very small effect magnitude (|{sm}| = {a:.2f} < 0.2, below Cohen's threshold)")
        if a < 0.5:
            return _t(f"小效应（|{sm}| = {a:.2f}，Cohen 标准：0.2 小 / 0.5 中 / 0.8 大）",
                      f"small effect (|{sm}| = {a:.2f}; Cohen: 0.2 small / 0.5 medium / 0.8 large)")
        if a < 0.8:
            return _t(f"中等效应（|{sm}| = {a:.2f}，Cohen 标准：0.5 中）",
                      f"medium effect (|{sm}| = {a:.2f}; Cohen: 0.5 medium)")
        return _t(f"大效应（|{sm}| = {a:.2f} ≥ 0.8，Cohen 标准）",
                  f"large effect (|{sm}| = {a:.2f} ≥ 0.8; Cohen)")
    if sm in _RATIO_SM:
        d = est / 1.0 if est >= 1 else 1.0 / est if est > 0 else 0.0
        if d < 1.2:
            return _t(f"效应接近无效值（{sm} = {est:.2f}，与 1 的距离不足 20%）",
                      f"effect close to the null value ({sm} = {est:.2f}, less than 20% away from 1)")
        if d < 1.5:
            return _t(f"边缘效应（{sm} = {est:.2f}）", f"marginal effect ({sm} = {est:.2f})")
        if d < 2.5:
            return _t(f"中等强度关联（{sm} = {est:.2f}）", f"moderate association ({sm} = {est:.2f})")
        return _t(f"强关联（{sm} = {est:.2f}，距无效值 1 较远，需复核数据真实性）",
                  f"strong association ({sm} = {est:.2f}, far from the null value of 1 — verify data integrity)")
    return ""


def _evidence_grade(k: float | None, i2: float | None,
                    ci_lo: float | None, ci_hi: float | None, sm: str):
    """证据强度综合评级（规则层简化 GRADE 取向，供通读与前端徽标）。

    起始 High，按不精确性（k 少）/ 异质性（I²）/ 不显著性（CI 跨无效值）降级。
    返回 (grade: str, reasons: list[str])。
    """
    grade = "High"
    reasons: list[str] = []
    if k is not None and k < 5:
        reasons.append(_t(f"研究数少（k = {int(k)} < 5，不精确性）",
                          f"few studies (k = {int(k)} < 5, imprecision)"))
        grade = "VeryLow" if k < 3 else "Low"
    if i2 is not None and i2 >= 75:
        reasons.append(_t(f"高异质性（I² = {i2:.0f}%）", f"high heterogeneity (I² = {i2:.0f}%)"))
        grade = {"High": "Low", "Moderate": "Low", "Low": "VeryLow", "VeryLow": "VeryLow"}[grade]
    elif i2 is not None and i2 >= 50:
        reasons.append(_t(f"中等异质性（I² = {i2:.0f}%）", f"moderate heterogeneity (I² = {i2:.0f}%)"))
        if grade == "High":
            grade = "Moderate"
    # sm 未知时不做显著性降级：_NULL_VALUE 默认 0 会把比值类 CI（如 0.5–2）误判为显著
    if sm in _ALL_KNOWN_SM and not _is_significant(ci_lo, ci_hi, sm):
        reasons.append(_t("95% CI 跨无效值（合并效应未达统计学显著）",
                          "95% CI crosses the null value (pooled effect not statistically significant)"))
        if grade == "High":
            grade = "Moderate"
        elif grade == "Moderate":
            grade = "Low"
    if not reasons:
        reasons.append(_t("研究数、异质性与精度均未见明显降级因素",
                          "no obvious downgrading factor in study count, heterogeneity or precision"))
    return grade, reasons


def _ci_precision_text(ci_lo: float | None, ci_hi: float | None, sm: str) -> str:
    """CI 宽度 → 精度表述（通读段用）。"""
    if ci_lo is None or ci_hi is None:
        return _t("区间精度不可评估", "precision cannot be assessed")
    w = ci_hi - ci_lo
    if sm in _RATIO_SM:
        if w > 10:
            return _t(f"95% CI 跨度很大（{ci_lo:.2f}–{ci_hi:.2f}），估计精度不足",
                      f"very wide 95% CI ({ci_lo:.2f}–{ci_hi:.2f}); insufficient precision")
        if w > 3:
            return _t(f"95% CI 跨度较大（{ci_lo:.2f}–{ci_hi:.2f}），精度有限",
                      f"wide 95% CI ({ci_lo:.2f}–{ci_hi:.2f}); limited precision")
        return _t(f"95% CI（{ci_lo:.2f}–{ci_hi:.2f}）跨度可接受，精度尚可",
                  f"acceptable 95% CI width ({ci_lo:.2f}–{ci_hi:.2f}); reasonable precision")
    if w > 3:
        return _t(f"95% CI 跨度很大（{ci_lo:.2f}–{ci_hi:.2f}），估计精度不足",
                  f"very wide 95% CI ({ci_lo:.2f}–{ci_hi:.2f}); insufficient precision")
    if w > 1:
        return _t(f"95% CI 跨度较大（{ci_lo:.2f}–{ci_hi:.2f}），精度有限",
                  f"wide 95% CI ({ci_lo:.2f}–{ci_hi:.2f}); limited precision")
    return _t(f"95% CI（{ci_lo:.2f}–{ci_hi:.2f}）较窄，精度较好",
              f"narrow 95% CI ({ci_lo:.2f}–{ci_hi:.2f}); good precision")


def _is_significant(
    ci_lo: float | None,
    ci_hi: float | None,
    sm: str,
) -> bool:
    """基于 CI 是否跨无效值判断显著性（不依赖 p 值）。"""
    if ci_lo is None or ci_hi is None:
        return False
    null = _NULL_VALUE.get(sm, 0.0)
    return not (ci_lo <= null <= ci_hi)


# ---------------------------------------------------------------------------
# 网络 Meta（netmeta: NMA / CNMA）专属解读
# ---------------------------------------------------------------------------
# 2026-09-14：旧版解读引擎只认标量型 pooled（pairwise 形状）。网络 Meta 的 pooled 是
# **多对比向量**（estimate/ci_low/ci_high 均为 list）→ 下方 float(list) 抛 TypeError，
# 被调用方的 except 静默吞掉 → conclusion 恒为空、caveats 恒 0 条，报告"结果解读"卡
# 整块失语。本节按 CINeMA（Confidence In Network Meta-Analysis）六域取向补齐网络 Meta
# 的解读要素，并把 log 尺度（TE=log OR/RR/HR）效应量还原到比值尺度后再表述。

_NETMETA_TASKS = frozenset({"nma", "nma_rank", "cnma"})
_CNMA_TASKS = frozenset({"cnma"})
_Q_EPS = 1e-6  # τ²=0 时 netmeta 会留下浮点噪声（实测 6.17e-32），低于此值视为 0


def _flist(v) -> list:
    """list/tuple/标量 → [float|None,...]；保持下标对齐（None 占位）。"""
    if isinstance(v, (list, tuple)):
        return [_safe_float(x) for x in v]
    f = _safe_float(v)
    return [] if f is None else [f]


def _back_scale(v, sm: str):
    """log 尺度（TE=log OR/RR/HR）→ 比值尺度；MD/SMD 等原样返回。"""
    if v is None:
        return None
    if sm in _RATIO_SM:
        try:
            return float(math.exp(v))
        except (OverflowError, ValueError):
            return None
    return v


def _q_clean(v):
    """Q 统计量净化：|Q| < 1e-6 视为 0（浮点噪声），缺失返回 None。"""
    f = _safe_float(v)
    if f is None:
        return None
    return 0.0 if abs(f) < _Q_EPS else f


def _fmt_ci(lo, hi, digits: int = 2) -> str:
    if lo is None or hi is None:
        return "CI 不可用"
    return f"{lo:.{digits}f}–{hi:.{digits}f}"


def _interpret_netmeta(stats: dict, task: str, sm: str) -> dict:
    """网络 Meta（NMA/CNMA）结果解读（CINeMA 六域取向）。

    覆盖：网络结构 / 各对比（或成分）效应 / 不一致性（全局 + 逐对比）/
    异质性 / 传递性假定 / 加性假定（CNMA）/ 不可识别成分 / 排序缺位。
    """
    pooled = stats.get("pooled") or {}
    het = stats.get("heterogeneity") or {}
    extra = stats.get("extra") or {}
    inc = extra.get("inconsistency") or {}
    net = extra.get("network") or {}
    add = extra.get("additivity") or {}
    components = extra.get("components") or {}
    unident = [u for u in (extra.get("unidentifiable") or []) if u]

    k = _safe_float(stats.get("k"))
    n_comp = _safe_float(stats.get("n_comp"))
    n_treat = _safe_float(stats.get("n_treat")) or _safe_float(net.get("n_interventions"))
    n_designs = _safe_float(net.get("n_designs"))
    is_cnma = task in _CNMA_TASKS or n_comp is not None
    subject = "成分网络 Meta（加性成分模型）" if is_cnma else "网络 Meta 分析"

    ratio_style = sm in _RATIO_SM
    unit = str(pooled.get("unit") or "")
    log_scale = unit == "log"

    conclusion = ""
    caveats: list[str] = []
    suggestions: list[str] = []
    reviewer_questions: list[str] = []

    # ---- 1) 网络结构摘要 ----
    # 口径：CNMA 讲「研究 / 治疗 / 成分」，NMA 讲「研究 / 干预 / 设计」。
    # 不用 netmeta 的 m（= 研究-对比数据行数，含臂数展开的重复）当"对比数"，否则
    # 3 个唯一对比的网络会被写成"9 个直接对比"。唯一对比数由下方结论的 total_n
    # （= pooled 上三角展开后的有效估计数）承载，故此处不再另取 net.n_comparisons。
    bits = []
    if k is not None:
        bits.append(f"{int(k)} 项研究")
    if is_cnma:
        if n_treat is not None:
            bits.append(f"{int(n_treat)} 种治疗")
        if n_comp is not None:
            bits.append(f"{int(n_comp)} 个成分")
    else:
        if n_treat is not None:
            bits.append(f"{int(n_treat)} 种干预")
        if n_designs is not None and n_designs > 1:
            bits.append(f"{int(n_designs)} 种设计")
    struct_txt = "、".join(bits) if bits else "网络结构信息缺失"

    # ---- 2) 效应量：NMA 逐对比 / CNMA 成分效应 ----
    eff_lines: list[str] = []
    sig_n = 0
    total_n = 0
    if is_cnma:
        c_name = list(components.get("name") or [])
        c_est = _flist(components.get("estimate"))
        c_lo = _flist(components.get("ci_low"))
        c_hi = _flist(components.get("ci_high"))
        c_p = _flist(components.get("p"))
        c_k = extra.get("comp_k") or {}
        for i, nm in enumerate(c_name):
            e = _back_scale(c_est[i] if i < len(c_est) else None, sm)
            lo = _back_scale(c_lo[i] if i < len(c_lo) else None, sm)
            hi = _back_scale(c_hi[i] if i < len(c_hi) else None, sm)
            if e is None:
                continue
            total_n += 1
            null = 1.0 if ratio_style else 0.0
            sig = lo is not None and hi is not None and not (lo <= null <= hi)
            if sig:
                sig_n += 1
            kc = c_k.get(nm) if isinstance(c_k, dict) else None
            pv = c_p[i] if i < len(c_p) else None
            eff_lines.append(
                f"成分 {nm} = {e:.2f}（95% CI {_fmt_ci(lo, hi)}"
                + (f"，{_sig_text(pv)}" if pv is not None else "")
                + (f"，{int(kc)} 项研究支撑" if isinstance(kc, (int, float)) else "")
                + f"）{'，差异有统计学显著性' if sig else '，CI 含无效值'}")
    else:
        comps = list(pooled.get("comparisons") or [])
        ests = _flist(pooled.get("estimate"))
        los = _flist(pooled.get("ci_low"))
        his = _flist(pooled.get("ci_high"))
        for i, raw_e in enumerate(ests):
            lo0 = los[i] if i < len(los) else None
            hi0 = his[i] if i < len(his) else None
            # 参考组自身对比占位项（log 尺度 est=lo=hi=0）→ 跳过，不是有效估计
            if log_scale and raw_e == 0 and lo0 == 0 and hi0 == 0:
                continue
            if raw_e is None:
                continue
            total_n += 1
            e = _back_scale(raw_e, sm)
            lo = _back_scale(lo0, sm)
            hi = _back_scale(hi0, sm)
            null = 1.0 if ratio_style else 0.0
            sig = lo is not None and hi is not None and not (lo <= null <= hi)
            if sig:
                sig_n += 1
            label = str(comps[i]) if i < len(comps) else f"对比 {i + 1}"
            eff_lines.append(f"{label} {sm} = {e:.2f}（95% CI {_fmt_ci(lo, hi)}）"
                             + ("，有统计学显著性" if sig else "，无统计学显著性"))

    # 结论：结构摘要 + 有效应量时的显著性概况
    if eff_lines:
        if is_cnma:
            conclusion = (f"{subject}：{struct_txt}。共 {total_n} 个成分效应，"
                          f"其中 {sig_n} 个 95% CI 不含无效值。")
        else:
            conclusion = (f"{subject}：{struct_txt}。共 {total_n} 个可比对比，"
                          f"其中 {sig_n} 个的 95% CI 不含无效值（{sm} 尺度）。")
    else:
        conclusion = f"{subject}：{struct_txt}。未取得可解读的效应量估计。"

    if eff_lines:
        suggestions.append("正文报告各对比/成分效应时需同时给出 95% CI 与网络估计"
                           "（NMA 的合并效应是网络估计，不是直接比较的简单合并）。")

    # ---- 3) 不一致性（CINeMA 第 6 域；网络 Meta 的核心诊断）----
    inc_p = _safe_float(inc.get("p"))
    inc_df = _safe_float(inc.get("df"))
    inc_q = _q_clean(inc.get("Q"))
    if is_cnma:
        # CNMA 分两层：加性假设（成分模型自身）+ 底层网络的设计-治疗交互
        add_p = _safe_float(add.get("p_diff"))
        add_q = _q_clean(add.get("Q_diff"))
        if add_p is None:
            caveats.append("加性假设检验（Q.diff）不可得，成分效应的可加性未经验证。")
        elif add_p < 0.05:
            caveats.append(
                f"⚠ 加性假设被拒绝（Q.diff = {add_q:.3f}，p = {add_p:.3f} < 0.05）："
                "成分效应不可简单相加，组合治疗的效应不能用成分效应线性外推。")
            suggestions.append("加性假设不成立时，建议改用交互模型（interaction=true，"
                               "C.matrix = createC）或退回标准 NMA（task=nma）并按对比解释。")
            reviewer_questions.append(
                "成分网络 Meta 的加性假设是否成立？Q.diff 检验结果如何报告？")
        else:
            caveats.append(f"加性假设未被拒绝（Q.diff = {add_q:.3f}，p = {add_p:.3f}）——"
                           "成分效应可按加性模型解释，但结论受该假定约束。")
    if inc_p is None or (inc_df is not None and inc_df <= 0):
        caveats.append("网络不一致性（设计-治疗交互）不可评估："
                       "网络可能仅含单一设计或连通结构不足以分解直接/间接证据——"
                       "≠ 已证明一致，须在讨论段说明该局限。")
        reviewer_questions.append(
            "网络一致性能否检验？若仅有单一设计，传递性假定如何论证？")
    elif inc_p < 0.05:
        caveats.append(
            f"⚠ 存在显著不一致性（设计-治疗交互 Q = {inc_q:.3f}，df = {int(inc_df)}，"
            f"p = {inc_p:.3f} < 0.05）：直接与间接证据不一致，"
            "网络合并效应可能被误导。")
        suggestions.append("建议用节点拆分（netsplit）/ 设计分解（decomp.design）"
                           "定位不一致来源，并对不一致对比做敏感性分析。")
        reviewer_questions.append(
            f"存在显著不一致性（p = {inc_p:.3f}），来源是什么？是否做了节点拆分？")
    else:
        caveats.append(f"未见显著不一致性（设计-治疗交互 Q = {inc_q:.3f}，"
                       f"df = {int(inc_df)}，p = {inc_p:.3f}）——该检验效能有限，"
                       "不构成一致性成立的充分证据。")

    # 逐对比不一致性定位（直接 vs 间接差异）
    by_cmp = inc.get("by_comparison") or {}
    if isinstance(by_cmp, dict) and by_cmp.get("comparison"):
        cp_p = _flist(by_cmp.get("p"))
        off = [str(by_cmp["comparison"][i]) for i, pv in enumerate(cp_p)
               if pv is not None and pv < 0.05]
        if off:
            head = "、".join(off[:4]) + ("…" if len(off) > 4 else "")
            caveats.append(f"逐对比检验显示 {len(off)} 个对比的直接/间接证据存在差异"
                           f"（{head}），建议重点核查。")
            suggestions.append("对上述对比分别报告直接证据与间接证据估计，"
                               "并说明差异的临床可比性。")

    # ---- 4) 异质性（CINeMA 第 5 域）----
    i2 = _norm_i2(_safe_float(het.get("I2")))
    tau = _safe_float(het.get("tau"))
    if i2 is None:
        caveats.append("未返回网络整体异质性（I²/τ²），该域无法评估——"
                       "网络 Meta 的 I² 是全网整体量，不能替代逐对比异质性。")
    else:
        if i2 >= 75:
            caveats.append(f"网络整体 I² = {i2:.0f}%，异质性很高，合并效应解释受限。")
            suggestions.append("建议按干预类别/剂量/地区做亚组或网络 meta-regression 探索异质性来源。")
        elif i2 >= 50:
            caveats.append(f"网络整体 I² = {i2:.0f}%，存在中等异质性，"
                           "讨论段需解释可能来源。")
        else:
            caveats.append(f"网络整体 I² = {i2:.0f}%，异质性可接受"
                           + (f"（τ = {tau:.3f}）" if tau is not None else "") + "。")

    # ---- 5) 传递性假定（网络 Meta 特有，恒需声明）----
    reviewer_questions.append("传递性（transitivity）假定如何在方案中论证？"
                              "各对比的研究人群、干预定义与结局是否可比？")
    if is_cnma:
        suggestions.append("CNMA 额外要求成分定义互斥且覆盖完整；"
                           "报告需给出成分-治疗设计矩阵（design）。")
    else:
        suggestions.append("NMA 报告需给出网络图、各对比的研究数与直接证据占比"
                           "（prop_direct），并说明哪些对比仅有间接证据。")

    # ---- 6) 排序（SUCRA / P-score）----
    if task == "nma_rank" or extra.get("rank"):
        suggestions.append("排序概率（SUCRA / P-score）只能作为辅助描述，"
                           "不得作为疗效优劣的唯一依据；须同时报告效应量及 CI。")
        reviewer_questions.append("排序结果是否与效应量的置信区间一致？"
                                  "是否解释了排序的不确定性？")
    elif not is_cnma:
        caveats.append("本次未计算干预排序（SUCRA / P-score）；"
                       "若结论涉及「哪种干预更优」，需补做 task=nma_rank。")

    # ---- 7) 不可识别成分（CNMA）----
    if unident:
        caveats.append(f"⚠ {len(unident)} 个成分不可唯一识别（{'、'.join(unident)}）："
                       "netmeta 以 NA 报告（不是 0，不等于无效）——"
                       "通常因这些成分在网络中总是同时出现，无法分离各自效应。")
        suggestions.append("若需分离不可识别成分的效应，须补充含单成分臂的研究。")
        reviewer_questions.append("存在不可识别成分时，成分效应的可解释性如何保证？")

    # ---- 8) 研究数 / 证据体 ----
    if k is not None and k < 5:
        caveats.append(f"仅 {int(k)} 项研究，网络估计不稳定，结论仅供参考。")
    if n_treat is not None and n_treat < 3:
        caveats.append(f"网络仅含 {int(n_treat)} 种干预，"
                       "不足 3 个节点时网络 Meta 与普通两两比较差异有限。")

    # ---- 9) CINeMA 报告建议 ----
    suggestions.append("网络 Meta 的证据质量应使用 CINeMA 六域评估"
                       "（研究内偏倚、报告偏倚、间接性、不精确性、异质性、不一致性），"
                       "不宜直接套用普通 GRADE。")
    reviewer_questions.append("是否按 CINeMA 六域报告了证据置信度？"
                              "研究内偏倚与报告偏倚的域评级依据是什么？")

    return {
        "conclusion": conclusion,
        "narrative": conclusion,  # netmeta 分支 conclusion 已是通读段，narrative 同体
        "caveats": caveats,
        "suggestions": suggestions,
        "reviewer_questions": reviewer_questions,
        "key_numbers": [],
        "evidence_grade": "",
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def interpret_result(
    stats: dict | None,
    task: str = "",
    params: dict | None = None,
    lang: str = None,
) -> dict:
    """基于 coze stats 生成结构化解读。

    Args:
        stats: coze 返回的 stats 字典（pooled/heterogeneity/bias/k/sm 等）。
        task: 任务类型（pairwise_meta / single_group_meta / nma / ...）。
        params: 请求参数（sm / model / subgroup 等），缺失时从 stats.sm 推断。
        lang: 显式语言覆盖（zh/en）。None = **继承**当前 _LANG（由调用入口如
              run_block_b / demo_b_env 预先 set_lang）。此前默认 "zh" 会在每次
              调用时把语言重置回中文，英文界面下解读块整块泄漏中文（2026-10-29）。

    Returns:
        interpretation 字典：
          - conclusion: str，一句话结论。
          - caveats: list[str]，需要提醒用户的注意事项。
          - suggestions: list[str]，后续分析或撰写建议。
          - reviewer_questions: list[str]，审稿人可能追问的问题。
    """
    # 输出语言（2026-10-29）：仅影响叙述文案，不影响数值；lang=None 继承上下文
    if lang is not None:
        _LANG.set("en" if str(lang or "zh").lower().startswith("en") else "zh")
    # 初始化
    empty = {"conclusion": "", "narrative": "", "caveats": [], "suggestions": [],
             "reviewer_questions": [], "key_numbers": [], "evidence_grade": ""}
    if not isinstance(stats, dict):
        return empty

    params = params or {}
    sm = str(params.get("sm") or stats.get("sm") or "").upper()

    # 子结构
    pooled = stats.get("pooled") or {}
    het = stats.get("heterogeneity") or {}
    bias = stats.get("bias") or {}
    k = _safe_float(stats.get("k"))

    # 网络 Meta（NMA/CNMA）走专属分支（2026-09-14）。
    # 触发条件含"pooled.estimate 为向量"这一形状判据——防止 task 名未传入时
    # 落回标量路径（下面 float(list) 会抛 TypeError → 结论静默为空）。
    if task in _NETMETA_TASKS or isinstance(pooled.get("estimate"), (list, tuple)):
        return _interpret_netmeta(stats, task, sm)

    # 核心数值（优先真实比值尺度 OR/RR，其次 log 尺度；SMD 直接用原始尺度）
    if sm in _RATIO_SM:
        est = _safe_float(pooled.get("estimate_exp") or pooled.get("estimate"))
        ci_lo = _safe_float(pooled.get("ci_low_exp") or pooled.get("ci_low"))
        ci_hi = _safe_float(pooled.get("ci_high_exp") or pooled.get("ci_high"))
    else:
        est = _safe_float(pooled.get("estimate_exp") or pooled.get("estimate"))
        ci_lo = _safe_float(pooled.get("ci_low_exp") or pooled.get("ci_low"))
        ci_hi = _safe_float(pooled.get("ci_high_exp") or pooled.get("ci_high"))

    p = _safe_float(pooled.get("p") or pooled.get("pval"))
    i2 = _norm_i2(_safe_float(het.get("I2")))
    tau2 = _safe_float(het.get("tau2"))
    egger_p = _safe_float(
        bias.get("egger_p") or bias.get("reg_p") or bias.get("begg_p")
    )

    conclusion = ""
    caveats: list[str] = []
    suggestions: list[str] = []
    reviewer_questions: list[str] = []

    # ---- 1. 结论 ----
    if est is not None:
        direction = _direction_text(sm, est)
        sig = _is_significant(ci_lo, ci_hi, sm)
        ci_txt = (
            f"{ci_lo:.2f}–{ci_hi:.2f}"
            if ci_lo is not None and ci_hi is not None
            else _t("不可用", "not available")
        )
        p_txt = _sig_text(p)

        if sig:
            conclusion = _t(
                f"合并 {sm} = {est:.2f}（95% CI {ci_txt}，{p_txt}），"
                f"{direction}，差异有统计学显著性。",
                f"Pooled {sm} = {est:.2f} (95% CI {ci_txt}, {p_txt}), "
                f"{direction}; the difference is statistically significant.",
            )
        else:
            conclusion = _t(
                f"合并 {sm} = {est:.2f}（95% CI {ci_txt}，{p_txt}），"
                f"{direction}，但差异无统计学显著性（CI 跨无效值）。",
                f"Pooled {sm} = {est:.2f} (95% CI {ci_txt}, {p_txt}), "
                f"{direction}; however the difference is not statistically significant (CI crosses the null value).",
            )

    # ---- 2. 异质性 ----
    if i2 is not None:
        if i2 >= 75:
            caveats.append(_t(
                f"I² = {i2:.0f}%，研究间存在高异质性，结论的普适性受限。",
                f"I² = {i2:.0f}% — high between-study heterogeneity; generalisability of the conclusion is limited.",
            ))
            if k is not None and k >= 5:
                suggestions.append(_t(
                    "建议进行亚组分析或 meta-regression 探索异质性来源（如地区、剂量、研究质量）。",
                    "Consider subgroup analysis or meta-regression to explore sources of heterogeneity (region, dose, study quality).",
                ))
            reviewer_questions.append(_t(
                f"高异质性（I² = {i2:.0f}%）的来源是什么？是否进行了亚组分析或 meta-regression？",
                f"What explains the high heterogeneity (I² = {i2:.0f}%)? Were subgroup analysis or meta-regression performed?",
            ))
        elif i2 >= 50:
            caveats.append(_t(
                f"I² = {i2:.0f}%，中等异质性，随机效应模型适用，但讨论段需解释异质性可能来源。",
                f"I² = {i2:.0f}% — moderate heterogeneity; a random-effects model is appropriate, but the Discussion should explain possible sources.",
            ))
            if k is not None and k >= 8:
                suggestions.append(_t(
                    "若存在可能的效应修饰因素，建议探索亚组分析。",
                    "If effect modifiers are plausible, consider exploring them with subgroup analysis.",
                ))
        elif i2 < 25 and (k is not None and k > 10):
            caveats.append(_t(
                f"I² = {i2:.0f}%，低异质性，结果稳健；可考虑固定效应模型作敏感性分析。",
                f"I² = {i2:.0f}% — low heterogeneity and robust results; consider a fixed-effect model as a sensitivity analysis.",
            ))

    # ---- 3. 发表偏倚 ----
    if egger_p is not None:
        if egger_p < 0.10 and (k is not None and k >= 5):
            caveats.append(_t(
                f"Egger 检验 p = {egger_p:.3f}，提示可能存在发表偏倚，合并效应可能被高估。",
                f"Egger's test p = {egger_p:.3f} — possible publication bias; the pooled effect may be overestimated.",
            ))
            suggestions.append(_t(
                "建议做剪补法（trim-and-fill）校正，并检查漏斗图不对称原因。",
                "Consider trim-and-fill correction and examine the cause of funnel-plot asymmetry.",
            ))
            reviewer_questions.append(_t(
                "是否存在发表偏倚？是否进行了剪补法或失安全系数分析？",
                "Is there publication bias? Were trim-and-fill or fail-safe N analyses performed?",
            ))
        elif egger_p < 0.10 and (k is None or k < 5):
            caveats.append(_t(
                f"Egger 检验 p = {egger_p:.3f}，但研究数不足（k = {k}），检验效能低，结果仅供参考。",
                f"Egger's test p = {egger_p:.3f}, but too few studies (k = {k}); the test has low power — interpret with caution.",
            ))
        elif egger_p >= 0.10 and (k is not None and k >= 10):
            caveats.append(_t(
                f"Egger 检验 p = {egger_p:.3f}，未见明显发表偏倚信号。",
                f"Egger's test p = {egger_p:.3f} — no clear signal of publication bias.",
            ))

    # ---- 4. 研究数 ----
    if k is not None:
        if k < 3:
            caveats.append(_t(
                f"仅纳入 {int(k)} 项研究，证据体极小，合并效应不稳定，结果仅供参考。",
                f"Only {int(k)} studies included — a very small evidence base; the pooled effect is unstable and indicative only.",
            ))
            reviewer_questions.append(_t(
                f"研究数过少（k = {int(k)}），合并结果的稳健性如何？",
                f"With so few studies (k = {int(k)}), how robust is the pooled result?",
            ))
        elif k < 5:
            caveats.append(_t(
                f"纳入 {int(k)} 项研究，研究数较少，GRADE 证据等级应降级。",
                f"{int(k)} studies included — few studies; the GRADE certainty rating should be downgraded.",
            ))
            suggestions.append(_t(
                "建议明确标注为初步探索，并谨慎解读结果。",
                "Label this as exploratory and interpret the results cautiously.",
            ))

    # ---- 5. 效应量极端 ----
    if sm in _RATIO_SM and est is not None:
        if est > 10:
            caveats.append(_t(
                f"{sm} = {est:.2f}，效应量极端偏大，请复核原始数据（尤其零单元格）。",
                f"{sm} = {est:.2f} — extremely large effect; re-check the raw data (especially zero cells).",
            ))
            reviewer_questions.append(_t(
                "效应量极端偏大的原因是什么？是否由零单元格导致？是否进行了连续性校正？",
                "What explains the extremely large effect? Is it driven by zero cells? Was a continuity correction applied?",
            ))
        elif est < 0.1:
            caveats.append(_t(
                f"{sm} = {est:.2f}，效应量极端偏小，请复核原始数据。",
                f"{sm} = {est:.2f} — extremely small effect; re-check the raw data.",
            ))
    elif sm in _SM_SM and est is not None:
        if abs(est) > 3:
            caveats.append(_t(
                f"{sm} = {est:.2f}，效应量极端偏大（|d| > 3），请复核原始数据或考虑离群研究。",
                f"{sm} = {est:.2f} — extremely large effect (|d| > 3); re-check the raw data or consider outlier studies.",
            ))
            suggestions.append(_t(
                "建议做逐一剔除敏感性分析，识别离群研究。",
                "Consider a leave-one-out sensitivity analysis to identify outlier studies.",
            ))

    # ---- 6. CI 跨度 ----
    if ci_lo is not None and ci_hi is not None:
        ci_width = ci_hi - ci_lo
        if sm in _RATIO_SM and ci_width > 10:
            caveats.append(_t(
                f"95% CI 跨度大（{ci_lo:.2f}–{ci_hi:.2f}），估计精度不足，结论需谨慎。",
                f"Wide 95% CI ({ci_lo:.2f}–{ci_hi:.2f}) — insufficient precision; interpret the conclusion cautiously.",
            ))
            suggestions.append(_t(
                "建议增加研究数或探索异质性来源以缩窄 CI。",
                "Consider adding studies or exploring heterogeneity to narrow the CI.",
            ))
        elif sm in _SM_SM and ci_width > 3:
            caveats.append(_t(
                f"95% CI 跨度大（{ci_lo:.2f}–{ci_hi:.2f}），估计精度不足。",
                f"Wide 95% CI ({ci_lo:.2f}–{ci_hi:.2f}) — insufficient precision.",
            ))

    # ---- 7. 敏感性分析建议 ----
    if k is not None and k >= 5:
        suggestions.append(_t(
            "推荐做逐一剔除敏感性分析，识别对合并效应影响最大的研究。",
            "A leave-one-out sensitivity analysis is recommended to identify the most influential study.",
        ))

    # ---- 8. GRADE / 汇报建议 ----
    if task in ("pairwise_meta", "subgroup_analysis", "single_group_meta"):
        if i2 is not None and k is not None:
            suggestions.append(_t(
                "正文应报告：合并效应、95% CI、I²、τ²（如有）、研究数、GRADE 证据等级、发表偏倚检验结果。",
                "The manuscript should report: pooled effect, 95% CI, I², τ² (if any), number of studies, GRADE certainty, and publication-bias test results.",
            ))
        reviewer_questions.append(_t(
            "是否报告了 PRISMA 检索策略和筛选流程？是否进行了偏倚风险评估？",
            "Were the PRISMA search strategy and screening process reported? Was risk of bias assessed?",
        ))

    # ---- 9. 解读强化（2026-10-27 方案二·规则层）：临床幅度 / 证据评级 / 通读段 / 关键数字 ----
    magnitude = _cohen_text(sm, est)
    if magnitude:
        caveats.insert(0, magnitude)  # 幅度分级放在注意事项首位，先定性再提醒
    grade, grade_reasons = _evidence_grade(k, i2, ci_lo, ci_hi, sm)
    precision_txt = _ci_precision_text(ci_lo, ci_hi, sm)

    # 通读段：统计顾问口吻的连贯叙述（数据 → 方向/显著性 → 幅度 → 异质性 → 精度 → 评级）
    narrative_parts: list[str] = []
    if k is not None:
        narrative_parts.append(_t(f"本次共纳入 {int(k)} 项研究", f"{int(k)} studies were included"))
    if est is not None:
        sig = _is_significant(ci_lo, ci_hi, sm)
        narrative_parts.append(
            _t(f"合并 {sm} = {est:.2f}", f"pooled {sm} = {est:.2f}")
            + (_t("（95% CI ", " (95% CI ") + f"{ci_lo:.2f}–{ci_hi:.2f}"
               if ci_lo is not None and ci_hi is not None else "")
            + (_t(f"，{_sig_text(p)}）", f", {_sig_text(p)})")
               if (ci_lo is not None and p is not None) else
               (_t("）", ")") if ci_lo is not None else ""))
            + f", {_direction_text(sm, est)}"
            + _t("，差异有统计学显著性" if sig else "，但 CI 跨无效值，差异无统计学显著性",
                 "; the difference is statistically significant" if sig
                 else "; however the CI crosses the null value, so the difference is not statistically significant")
        )
        if magnitude:
            narrative_parts.append(_t(f"效应幅度判定：{magnitude}", f"effect magnitude: {magnitude}"))
    if i2 is not None:
        narrative_parts.append(
            _t(f"研究间异质性 I² = {i2:.0f}%", f"between-study heterogeneity I² = {i2:.0f}%")
            + (f", τ² = {tau2:.3f}" if tau2 is not None else "")
        )
    narrative_parts.append(_t(f"估计精度：{precision_txt}", f"precision: {precision_txt}"))
    if egger_p is not None:
        if egger_p < 0.10:
            narrative_parts.append(
                _t(f"发表偏倚信号：Egger p = {egger_p:.3f} < 0.10",
                   f"publication-bias signal: Egger p = {egger_p:.3f} < 0.10")
                + _t("（但研究数少、检验效能有限）" if k is not None and k < 5 else "",
                    " (but few studies and limited test power)" if k is not None and k < 5 else "")
            )
        elif k is not None and k >= 10:
            narrative_parts.append(_t(
                f"发表偏倚：Egger p = {egger_p:.3f}，未见明显不对称信号",
                f"publication bias: Egger p = {egger_p:.3f}, no clear asymmetry signal",
            ))
    narrative_parts.append(_t(
        f"综合证据强度：{grade}（{'；'.join(grade_reasons)}）",
        f"overall certainty: {grade} ({'; '.join(grade_reasons)})",
    ))
    _sep = _t("。", ". ")
    _tail = _t("。", ".")
    narrative = _sep.join(p.rstrip("。") for p in narrative_parts if p) + _tail

    # 关键数字：供前端高亮展示
    key_numbers: list[dict] = []
    if k is not None:
        key_numbers.append({"label": _t("研究数", "Studies"), "value": int(k)})
    if est is not None:
        key_numbers.append({"label": _t(f"合并 {sm}", f"Pooled {sm}"), "value": round(est, 3)})
    if ci_lo is not None and ci_hi is not None:
        key_numbers.append({"label": "95% CI", "value": f"{ci_lo:.2f}–{ci_hi:.2f}"})
    if p is not None:
        key_numbers.append({"label": _t("p 值", "p value"), "value": _sig_text(p).replace("p ", "").lstrip("= ")} )
    if i2 is not None:
        key_numbers.append({"label": "I²", "value": f"{i2:.0f}%"})
    if tau2 is not None:
        key_numbers.append({"label": "τ²", "value": round(tau2, 4)})
    if egger_p is not None:
        key_numbers.append({"label": "Egger p", "value": round(egger_p, 3)})
    key_numbers.append({"label": _t("证据强度", "Certainty"), "value": grade})

    return {
        "conclusion": conclusion,
        "narrative": narrative,
        "caveats": caveats,
        "suggestions": suggestions,
        "reviewer_questions": reviewer_questions,
        "key_numbers": key_numbers,
        "evidence_grade": grade,
    }


def check_effect_size_extreme(stats: dict | None) -> str | None:
    """效应量极端判定（飞书 searchlog 实证：60/281 成功记录效应量极端）。

    返回警告文本（应贴到结果上）或 None（效应量在合理范围）。
    判定阈值：
      - 比值类（OR/RR/PLO/PLOGIT/HR/IRR/RRR...）：estimate_exp > 10 或 < 0.1（真实比值）
      - 差值类（MD/SMD/ZCOR/MC/SMCR...）：|estimate| > 3

    纯本地规则，无外部依赖；原 run_analysis._check_effect_size_extreme 已收敛到此单一实现。
    """
    if not isinstance(stats, dict):
        return None
    _sm = str(stats.get("sm") or "").upper()
    _pooled = stats.get("pooled") or {}
    _est_e = _safe_float(_pooled.get("estimate_exp"))  # 真实比值(OR/RR/PLO)
    _est = _safe_float(_pooled.get("estimate"))        # log 比值 或 均值差
    if _sm in _RATIO_SM and _est_e is not None:
        if _est_e > 10:
            return f"{_sm}={_est_e:.2f} (>10)"
        if _est_e < 0.1:
            return f"{_sm}={_est_e:.2f} (<0.1)"
    if _sm in _SM_SM and _est is not None:
        if abs(_est) > 3:
            return f"{_sm}={_est:.2f} (|d|>3)"
    return None
