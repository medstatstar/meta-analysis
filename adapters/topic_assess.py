#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
topic_assess.py — Deterministic local topic-selection assessment for the
meta-analysis skill (no coze / no LLM required for the evidence-grounded dims).

This is the missing local half of the "Full" topic-selection path
(`scripts/generate_topic_report.py` renders an 11-section report from an
assessment JSON; previously that JSON's `scores` could ONLY be produced by
coze/LLM, so the standalone local flow never emitted a real evaluation).

What this module computes LOCALLY and DETERMINISTICALLY, grounded in REAL
probes (Europe PMC dedup + ClinicalTrials.gov registry):
  - data availability       (from real registered-trial / SR-MA counts)
  - novelty / saturation    (from real existing SR/MA counts)
  - methodological feasibility (from expected study count k + PICOS completeness)
  - clinical value          (JUDGMENT dimension — local default = mid, flagged
                             `needs_human`; override via `clinical_override`
                             when an LLM/coze is in the loop, per user intent)
  - total / verdict         (>=17 strongly_recommend / >=14 recommend /
                             >=10 hold / <10 not_recommended; any dim <=2 → veto)
  - R1–R6 cross-checks      (rule-based)
  - PRISMA 2020 / AMSTAR-2 pre-check (static topic-stage rubric)
  - dedup paragraph          (real Cochrane/PubMed counts + PROSPERO auto-probe
                               status / manual link)
  - real-gap evidence        (saturation label)

Every dimension carries an explicit `evidence` tag so the rendered report can
show which numbers are real vs which need human/LLM confirmation. Degrades
gracefully when probes are unavailable (scores still emitted, flagged
`unverified`).

Output dict is aligned with `references/topic-selection.md` + `topic_report.example.json`
so `generate_topic_report.py` can render it directly.
"""
import datetime

# 输出语言（2026-10-29）：仅影响叙述文案，不影响任何评分口径。
import contextvars as _ctxvars

_LANG = _ctxvars.ContextVar("topic_assess_lang", default="zh")


def _tr(zh: str, en: str) -> str:
    """按当前语言取文案。"""
    return en if str(_LANG.get() or "zh").lower().startswith("en") else zh


GAP_EN = {
    "real_gap": "Real gap (this narrow question is still under-studied within the broader field)",
    "saturated": "Saturated (many similar meta-analyses; the increment must be explicit)",
    "caution": "Caution (the direction is already covered; differentiate it)",
    "empty": "Near-empty (novel but possibly under-powered; watch out for k<2)",
    "unverified": "Unverified (probe unavailable)",
}

GAP_ZH = {
    "real_gap": "真实缺口（该窄方向在大类中仍欠研究）",
    "saturated": "已饱和（已有大量同类 Meta，须明确增量）",
    "caution": "需谨慎（方向已有覆盖，须差异化）",
    "empty": "近空白（新颖但可能数据不足，需警惕 k<2）",
    "unverified": "未验证（探针不可用）",
}

VERDICT_ZH = {
    "strongly_recommend": "强烈建议",
    "recommend": "建议",
    "hold": "暂缓",
    "not_recommended": "不建议",
}


def _extract_dedup_counts(dedup):
    """Pull real Cochrane / PubMed SR-MA hit counts from either the
    literature_probe result shape (layers.*.hit_count) or a flat dict."""
    cochrane = pubmed = None
    if isinstance(dedup, dict):
        layers = dedup.get("layers") or {}
        if layers:
            cochrane = (layers.get("cochrane") or {}).get("hit_count")
            pm = layers.get("pubmed_meta") or {}
            # 2026-10-30 双口径：评分语义（同类综述饱和度/降级代理）需要的是「真实
            # SR/MA 数」，优先取严格 PUB_TYPE 口径（strict_hit_count）；宽松自由词数
            # （hit_count，含提及字样的普通文献）仅在严格口径缺失时兜底，避免把
            # 5956 这类宽松数灌进饱和阈值（≥20 判 saturated）造成过度悲观。
            pubmed = (pm.get("strict_hit_count")
                      if isinstance(pm, dict) else None)
            if pubmed is None:
                pubmed = pm.get("hit_count") if isinstance(pm, dict) else None
        else:
            cochrane = dedup.get("cochrane")
            pubmed = dedup.get("pubmed")
    try:
        cochrane = int(cochrane) if cochrane is not None else None
    except (TypeError, ValueError):
        cochrane = None
    try:
        pubmed = int(pubmed) if pubmed is not None else None
    except (TypeError, ValueError):
        pubmed = None
    return cochrane, pubmed


def _registry_total(registry):
    if isinstance(registry, dict):
        t = registry.get("total")
        try:
            return int(t) if t is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _rct_total(rct):
    """从 rct_probe 结果取「已发表 RCT 文献数」（可为 0；None=未探针/失败）。"""
    if isinstance(rct, dict):
        t = rct.get("total")
        try:
            return int(t) if t is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _primary_total(registry_total, rct_total, pubmed_hits, cochrane_hits):
    """统一「可纳入原始研究数」代理：已发表 RCT 文献数优先，交叉 CT.gov 注册数。

    返回 (total, source)，source ∈ {"rct","registry","unverified"}。
    已发表 RCT（Europe PMC PUB_TYPE:RCT）是最直接的「可纳入 Meta 的原始研究」代理；
    ClinicalTrials.gov 注册数仅反映试验注册活跃度（含进行中/未发表），作次选。
    两者都不可用 → (None, "unverified")，由上游降级处理。
    """
    if rct_total is not None:
        return rct_total, "rct"
    if registry_total is not None:
        return registry_total, "registry"
    return None, "unverified"


# ---------------------------------------------------------------------------
# Deterministic per-dimension scorers (0–5)
# ---------------------------------------------------------------------------
def _score_data(primary_total, pubmed_hits, cochrane_hits, primary_source="registry"):
    # 2026-10-30 修：primary_total 现统一为「可纳入原始研究数」代理——优先已发表
    # RCT 文献数（rct 探针），其次 ClinicalTrials.gov 注册数（registry）。原「注册库 0
    # 命中、文献库却已有大量同类 SR/MA」的降级逻辑保留（此时注册库计数不可信）。
    _sr = (pubmed_hits or 0) + (cochrane_hits or 0)
    degraded = False
    if primary_total == 0 and _sr >= 20:
        primary_total = None
        pubmed_hits = max(pubmed_hits or 0, _sr)
        degraded = True
    if primary_total is not None:
        t, conf = primary_total, primary_source
    elif pubmed_hits is not None:
        t, conf = pubmed_hits, "pubmed_proxy"
    else:
        return 0, "unverified", _tr("无真实探针数据（注册库/文献均未返回）",
                                    "no real probe data (neither registry nor literature returned results)")
    if t >= 50:
        s = 5
    elif t >= 20:
        s = 4
    elif t >= 10:
        s = 3
    elif t >= 5:
        s = 2
    elif t >= 1:
        s = 1
    else:
        s = 0
    if degraded:
        note = _tr("注册库未命中但文献库有 %d 篇同类 SR/MA → 按文献代理估计（原始研究数需人工核实）" % t,
                   "no registry hits, but %d similar SR/MA in the literature → literature-proxy estimate (primary-study count needs manual verification)" % t)
    elif conf == "rct":
        note = (_tr("已发表 RCT %d 篇 → 原始研究充足" % t,
                    "%d published RCTs → primary studies are plentiful" % t)
                if t >= 10 else
                _tr("已发表 RCT 仅 %d 篇 → 原始研究可能不足，需人工核实" % t,
                    "only %d published RCTs → primary studies may be insufficient; verify manually" % t))
    elif conf == "registry":
        note = (_tr("注册库 %d 项 → 原始研究充足" % t,
                    "%d registry records → primary studies are plentiful" % t)
                if t >= 10 else
                _tr("注册库仅 %d 项 → 原始研究可能不足，需人工核实" % t,
                    "only %d registry records → primary studies may be insufficient; verify manually" % t))
    else:
        note = _tr("PubMed SR/MA %d 篇（代理，置信低于注册库）" % pubmed_hits,
                   "%d PubMed SR/MA (proxy; lower confidence than the registry)" % pubmed_hits)
    return s, conf, note


def _score_novelty(pubmed_hits, cochrane_hits):
    n = (pubmed_hits or 0) + (cochrane_hits or 0)
    if n == 0:
        return 5, "empty", _tr("近无同类综述（新颖，但需警惕原始研究不足）",
                               "almost no similar reviews (novel, but watch out for too few primary studies)")
    if n >= 20:
        return 1, "saturated", _tr("已有大量同类 SR/MA，必须明确差异化增量",
                                   "many similar SR/MA already exist; a clear differentiating increment is essential")
    if n >= 10:
        return 2, "saturated", _tr("同类综述较多，须找新颖角度",
                                   "quite a few similar reviews; find a fresh angle")
    if n >= 5:
        return 3, "caution", _tr("方向已有覆盖，须差异化",
                                 "the direction is already covered; differentiate it")
    return 4, "real_gap", _tr("同类综述较少，存在真实缺口空间",
                              "few similar reviews — there is room for a genuine gap")


def _score_feasibility(primary_total, pubmed_hits, missing, primary_source="registry"):
    # 2026-10-30 修：primary_total 统一为「可纳入原始研究数」代理（已发表 RCT 优先）。
    _proxy = (primary_total == 0 and (pubmed_hits or 0) >= 20)
    if _proxy:
        s = 3
        k = None
    else:
        k = primary_total if primary_total is not None else (pubmed_hits
                                                                if pubmed_hits is not None else 0)
        if k >= 10:
            s = 5
        elif k >= 5:
            s = 4
        elif k >= 2:
            s = 3
        elif k >= 1:
            s = 1
        else:
            s = 0
    if len(missing or []) >= 3:
        s = min(s, 2)
    _src = (_tr("已发表 RCT", "published RCT") if primary_source == "rct"
            else _tr("注册库", "registry") if primary_source == "registry"
            else _tr("文献代理", "literature proxy"))
    if _proxy:
        note = _tr("注册库未命中，但文献库已有 %d 篇同类 SR/MA → 原始研究数按「可纳入、待核实」处理，不判空白方向" % pubmed_hits,
                   "no registry hits, but %d similar SR/MA in the literature → treat the primary-study count as \"includable, pending verification\" rather than a blank direction" % pubmed_hits)
    else:
        note = _tr("预期可纳入研究数 k=%s（来源：%s）" % (k, _src),
                   "expected includable studies k=%s (source: %s)" % (k, _src))
    return s, note


def _score_clinical(topic, override):
    rationale = None
    score = None
    if isinstance(override, dict):
        try:
            score = int(override.get("score"))
        except (TypeError, ValueError):
            score = None
        rationale = override.get("rationale")
    elif override is not None:
        try:
            score = int(override)
        except (TypeError, ValueError):
            score = None
    if score is not None:
        return score, False, _tr("由 LLM/Coze 评估覆盖", "assessed by LLM/Coze"), rationale
    # 本地默认中值：临床价值是判断项，无公开 API 可算，明确标注需人工确认。
    return 3, True, _tr("本地默认中值；临床价值属判断项，建议人工/LLM 确认",
                        "local default mid-point; clinical value is a judgement item — confirm manually or with an LLM"), None


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def _verdict(total, scores):
    if scores.get("data", 5) <= 1:
        return "veto:data", _tr("数据不足以支撑 meta（预期研究数 k<2）",
                                "not enough data to support a meta-analysis (expected studies k<2)")
    if total >= 17:
        return "strongly_recommend", _tr("证据充分、缺口明确，可推进",
                                         "adequate evidence with a clear gap — proceed")
    if total >= 14:
        return "recommend", _tr("总体可行，推进前补齐缺口说明",
                                "generally feasible; document the gap before proceeding")
    if total >= 10:
        return "hold", _tr("存在短板，建议先补强再启动",
                           "there are weak points — strengthen them before starting")
    return "not_recommended", _tr("多项偏弱，暂不建议启动",
                                  "several dimensions are weak — starting is not recommended yet")


# ---------------------------------------------------------------------------
# Cross-checks R1–R6 (rule-based)
# ---------------------------------------------------------------------------
def _cross_checks(picos, missing, pubmed_hits, cochrane_hits, novelty_label):
    n_sr = (pubmed_hits or 0) + (cochrane_hits or 0)
    checks = [
        {"rule": "R1", "triggered": bool(missing),
         "note": (_tr("PICO 可分解", "PICO can be decomposed") if not missing else
                  _tr("缺失维度 %s，须先明确研究问题" % "、".join(missing),
                      "missing dimension(s): %s — clarify the research question first" % ", ".join(missing)))},
        {"rule": "R2", "triggered": False,
         "note": _tr("默认 pairwise；若涉及 ≥3 同时干预需评估 NMA",
                     "default is pairwise; if ≥3 interventions are compared concurrently, consider NMA")},
        {"rule": "R3", "triggered": novelty_label in ("saturated",),
         "note": (_tr("新颖性已复核，同类 SR/MA=%d，须明确增量" % n_sr,
                      "novelty reviewed: %d similar SR/MA — the increment must be explicit" % n_sr)
                  if novelty_label in ("saturated",) else _tr("新颖性合理", "novelty is reasonable"))},
        {"rule": "R4", "triggered": False,
         "note": _tr("异质性预案（I²>50% 触发亚组）由技能提供",
                     "heterogeneity contingency (subgroup analysis triggered at I²>50%) is provided by the skill")},
        {"rule": "R5", "triggered": False,
         "note": _tr("结局-效应量对齐（时间-事件→HR，二分类→RR/OR）",
                     "outcome–effect-measure alignment (time-to-event → HR, binary → RR/OR)")},
        {"rule": "R6", "triggered": False,
         "note": _tr("PROSPERO 注册列入后续动作", "PROSPERO registration is listed as a follow-up action")},
    ]
    return checks


# ---------------------------------------------------------------------------
# Compliance rubric (topic stage)
# ---------------------------------------------------------------------------
def _compliance():
    return {
        "prisma": [
            {"item": "1", "status": "ok", "note": _tr("标题将标识为系统评价/Meta", "the title will identify this as a systematic review/meta-analysis")},
            {"item": "5", "status": "plan", "note": _tr("纳入标准草案（选题阶段）", "draft eligibility criteria (topic stage)")},
            {"item": "9", "status": "gap", "note": _tr("提取表待方案阶段构建", "extraction form to be built at the protocol stage")},
        ],
        "amstar2": [
            {"domain": "protocol", "status": "plan", "note": _tr("PROSPERO 注册应在数据提取前完成", "PROSPERO registration should be completed before data extraction")},
            {"domain": "publication_bias", "status": "ok", "note": _tr("Egger/Begg/trim-fill 由技能提供", "Egger/Begg/trim-and-fill are provided by the skill")},
        ],
        "overall_risk": "yellow",
        "note": _tr("选题阶段预检：2 项待补，方案阶段复检", "topic-stage pre-check: 2 items outstanding, re-check at the protocol stage"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def assess(topic, picos=None, missing=None, dedup=None, registry=None, rct=None,
           clinical_override=None, prospero=None, curation=None, topic_en=None,
           lang="zh"):
    """Build the full local topic assessment.

    Args:
        topic: original topic string.
        picos: dict {P,I,C,O,S} (from _infer_picos).
        missing: list of missing PICOS keys.
        dedup: literature_probe.dedup_probe result (real Cochrane/PubMed hits)
               or a flat {cochrane, pubmed} dict.
        registry: registry_probe result {total, sample, status} (real CT.gov).
        clinical_override: optional int (0-5) OR dict {"score":int,"rationale":str}
               supplied by LLM/coze for the judgment dimension; when present,
               clinical is NOT flagged needs_human (tag="coze") and rationale kept.
        curation: optional dict {"recommend":bool,"reason":str} from coze topic
               curation; rendered as a separate panel in the web UI.
        topic_en: optional English search term; PROSPERO probe uses this
                  for the manual-check URL instead of the raw Chinese topic.

    Returns: assessment dict aligned with generate_topic_report schema.
    """
    _LANG.set("en" if str(lang or "zh").lower().startswith("en") else "zh")
    picos = picos or {}
    missing = missing or []
    cochrane_hits, pubmed_hits = _extract_dedup_counts(dedup)
    registry_total = _registry_total(registry)
    rct_total = _rct_total(rct)
    # 2026-10-30：统一「可纳入原始研究数」代理——已发表 RCT 文献数优先，
    # 交叉 ClinicalTrials.gov 注册数；两者都不可用时退回 unverified。
    primary_total, primary_source = _primary_total(registry_total, rct_total,
                                                  pubmed_hits, cochrane_hits)

    data_s, data_conf, data_note = _score_data(primary_total, pubmed_hits, cochrane_hits, primary_source)
    nov_s, nov_label, nov_note = _score_novelty(pubmed_hits, cochrane_hits)
    fea_s, fea_note = _score_feasibility(primary_total, pubmed_hits, missing, primary_source)
    cli_s, cli_needs, cli_note, cli_rationale = _score_clinical(topic, clinical_override)

    scores = {"clinical": cli_s, "feasibility": fea_s, "data": data_s,
              "novelty": nov_s, "total": cli_s + fea_s + data_s + nov_s}
    verdict_key, verdict_note = _verdict(scores["total"], scores)
    cross_checks = _cross_checks(picos, missing, pubmed_hits, cochrane_hits, nov_label)

    # PROSPERO 自动检索（真实尝试 + 优雅降级；上游故障时不编造数据）
    # 2026-09-25：优先用英文检索词（PROSPERO 是英文注册库，中文 topic 检索≈0 命中）
    if isinstance(prospero, dict) and prospero.get("status") in ("available", "unavailable"):
        _prospero = prospero
    else:
        try:
            import prospero_probe
            _prospero = prospero_probe.probe(topic_en or topic)
        except Exception as _pe:  # noqa: BLE001
            _prospero = {"status": "unavailable", "hit_count": None, "sample": [],
                         "error": "probe import failed: %s" % _pe,
                         "manual_url": None, "note": ""}
    if _prospero.get("status") == "available":
        _prospero_line = _tr("已自动检索：命中 %s 项已注册方案（来源 %s）" % (
            _prospero.get("hit_count"), _prospero.get("source")),
            "auto-searched: %s registered protocols found (source: %s)" % (
            _prospero.get("hit_count"), _prospero.get("source")))
    else:
        _pu = _prospero.get("manual_url") or (
            "https://www.crd.york.ac.uk/prospero/#searchadvanced?search="
            + __import__("urllib.parse").parse.quote(topic))
        _prospero_line = _tr("自动检索暂不可用（%s）；手动核查：%s" % (
            (_prospero.get("error") or "上游故障"), _pu),
            "auto-search unavailable (%s); check manually: %s" % (
            (_prospero.get("error") or "upstream failure"), _pu))

    # dedup paragraph
    cochrane_txt = ("%s Cochrane reviews" % cochrane_hits) if cochrane_hits is not None else _tr("未探针", "not probed")
    pubmed_txt = _tr("%s 篇 SR/MA（近 5 年）" % pubmed_hits, "%s SR/MA (last 5 years)" % pubmed_hits) if pubmed_hits is not None else _tr("未探针", "not probed")
    pros_url = ("https://www.crd.york.ac.uk/prospero/#searchadvanced"
                "?search=%s" % urllib_parse_quote(topic))
    if nov_label == "saturated":
        near_dup = _tr("高饱和，须明确增量以避免近重复拒稿", "highly saturated; a clear increment is needed to avoid rejection for near-duplication")
        increment = _tr("需提出既往综述未覆盖的亚组/人群/结局作为增量", "propose a subgroup/population/outcome not covered by existing reviews as the increment")
    elif nov_label == "caution":
        near_dup = _tr("存在同类综述，须差异化", "similar reviews exist; differentiate")
        increment = _tr("明确与现有综述的差异点", "state explicitly how this differs from existing reviews")
    elif nov_label == "empty":
        near_dup = _tr("暂无近重复风险（但需警惕数据不足）", "no near-duplication risk (but watch out for insufficient data)")
        increment = _tr("空白方向，先确认是否有足够原始研究（k≥2）", "blank direction — first confirm there are enough primary studies (k≥2)")
    else:
        near_dup = _tr("暂无近重复风险", "no near-duplication risk")
        increment = _tr("真实缺口方向，常规推进", "genuine gap — proceed as usual")

    dedup = {
        "prospero": _prospero_line,
        "cochrane": cochrane_txt,
        "pubmed": pubmed_txt,
        "non_english": _tr("未覆盖（英文文献为主，按需手动补中文库）", "not covered (English literature dominates; add Chinese databases manually if needed)"),
        "near_duplicate": near_dup,
        "increment": increment,
    }

    gap = {
        "verdict": nov_label,
        "label": _tr(GAP_ZH.get(nov_label, nov_label), GAP_EN.get(nov_label, nov_label)),
        "probe_used": (cochrane_hits is not None or pubmed_hits is not None),
        "summary": nov_note,
    }

    # 2026-10-25：注册库 0 命中但文献库已有大量同类 SR/MA 时，不能写「约 0 项注册试验」——
    # 与「同类 SR/MA 已饱和」并列会自相矛盾，改为如实标注待核实。
    _sr_n = (pubmed_hits or 0) + (cochrane_hits or 0)
    if primary_total == 0 and _sr_n >= 20:
        expected = _tr("待核实（注册库未命中，但文献库已有 %d 篇同类 SR/MA）" % _sr_n,
                       "to be verified (no registry hits, but %d similar SR/MA in the literature)" % _sr_n)
    elif primary_total is not None:
        _src = (_tr("已发表 RCT", "published RCT") if primary_source == "rct"
                else _tr("注册试验", "registered trials"))
        expected = _tr("约 %s 项%s / 预期可纳入研究" % (primary_total, _src),
                       "about %s %s / expected includable studies" % (primary_total, _src))
    else:
        expected = _tr("未探针，预期研究数未知", "not probed; expected study count unknown")

    compliance = _compliance()

    assessment = {
        "topic": topic,
        "scores": scores,
        "clinical_rationale": cli_rationale,
        "score_anchors": {
            "clinical": cli_note,
            "feasibility": fea_note,
            "data": data_note,
            "novelty": nov_note,
        },
        "evidence_tags": {
            "clinical": "coze" if not cli_needs else "judgment",
            "feasibility": data_conf if data_conf != "unverified" else "unverified",
            "data": data_conf,
            "novelty": "probe" if gap["probe_used"] else "unverified",
        },
        "verdict": verdict_key if not verdict_key.startswith("veto") else "veto",
        "verdict_raw": verdict_key,
        "verdict_note": verdict_note,
        "cross_checks": cross_checks,
        "dedup": dedup,
        "gap": gap,
        "expected_studies": expected,
        "compliance": compliance,
        "prospero": {
            "status": _prospero.get("status"),
            "hit_count": _prospero.get("hit_count"),
            "sample": _prospero.get("sample") or [],
            "error": _prospero.get("error"),
            "source": _prospero.get("source"),
            # 2026-10-25：新版 PROSPERO 探针会回报实际生效的检索式，
            # 前端挂在命中数的 title 上，便于用户核对「51 条」是按什么口径查出来的。
            "query_used": _prospero.get("query_used"),
            "manual_url": _prospero.get("manual_url"),
            "note": _prospero.get("note") or "",
            "register_before_extraction": _tr("PROSPERO 注册应在数据提取前完成（AMSTAR-2 要求）",
                                              "PROSPERO registration should be completed before data extraction (AMSTAR-2 requirement)"),
        },
        "curation": curation,
        "assessed_on": datetime.date.today().isoformat(),
        "local": True,
        "note": _tr(
            "本地确定性评估：数据/新颖性/方法可行性由真实探针（Europe PMC + "
            "ClinicalTrials.gov）驱动；临床价值维度"
            + ("已由 Coze/LLM 评估覆盖" if not cli_needs else
               "属判断项，默认中值并标注需人工/LLM 确认（可用 clinical_override 由 Coze 覆盖）")
            + "。",
            "Local deterministic assessment: data / novelty / feasibility are driven by real probes "
            "(Europe PMC + ClinicalTrials.gov); the clinical-value dimension "
            + ("was assessed by Coze/LLM" if not cli_needs else
               "is a judgement item, defaulted to the mid-point and flagged for manual/LLM confirmation "
               "(Coze can override it via clinical_override)")
            + "."),
    }
    return assessment


def urllib_parse_quote(s):
    import urllib.parse
    return urllib.parse.quote(s)


if __name__ == "__main__":
    import json as _json
    import sys
    _t = sys.argv[1] if len(sys.argv) > 1 else "SGLT2 inhibitors heart failure"
    _a = assess(_t, picos={}, missing=[], dedup=None, registry=None)
    print(_json.dumps(_a, ensure_ascii=False, indent=2))
