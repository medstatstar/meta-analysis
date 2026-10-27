#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gov22.py — ct-base §22 governance sections for meta-analysis.

Meta-analysis specific port of ct-literature's gov22.py. Adapts to the
generate_topic_report.py data contract (topic_assess.py output).

Implements:
  §22.16 P1·h  RAG 三列待核对清单 (问题 / 原文位置 / 依据) + 显式「未覆盖项」
  §22.17 P2·a  确定性工具层 vs LLM 依赖输出 分层验收声明

Design constraints (ct-base AGENTS §2.1 function-first, §22 anti-hallucination):
  * PURE, deterministic, stdlib-only — same inputs always yield same output.
  * Takes explicit inputs (never reaches into global state) so the Markdown
    renderer (generate_topic_report.py) and the HTML renderer stay in lock-step.
  * Derives every figure from the real run payload (gap / dedup / compliance /
    evidence_tags / cross_checks) — no fabricated counts.
  * "漏项" (uncovered items) is the DEFAULT failure mode and is surfaced
    explicitly, never assumed complete.

Data contract (topic_assess.py output → generate_topic_report.py input):
  - gap          {verdict, label, probe_used, narrow, broad, ratio_narrow_over_broad, summary}
  - dedup        {prospero, cochrane, pubmed, non_english, near_duplicate, increment}
  - compliance   {prisma, amstar2, overall_risk, note}
  - prospero     {status, hit_count, sample, error, source, query_used, manual_url, note, register_before_extraction}
  - evidence_tags {clinical, feasibility, data, novelty}
  - cross_checks [{rule, triggered, note}]
  - scores       {clinical, feasibility, data, novelty, total}
  - score_anchors {clinical, feasibility, data, novelty}
  - works        list of work dicts (optional, may be absent)
  - meta         {topic, year_from, year_to, safety, ...}
"""
SKILL_VERSION = "2.20.2"


def _lang(lang):
    if lang in ("zh", "zh-CN", "zh-cn"):
        return "zh"
    if lang in ("en", "auto"):
        return "en"
    return "zh" if (lang or "").lower().startswith("zh") else "en"


# ---------------------------------------------------------------------------
# §22.16 — Explicit uncovered items
# ---------------------------------------------------------------------------

def build_uncovered(d, lang="auto"):
    """§22.16 — explicit 「未覆盖项」 (uncovered items).

    Meta-analysis 的选题评估不是多源检索，而是真实探针驱动（Cochrane/PubMed/
    ClinicalTrials.gov）。未覆盖项由以下维度推导：
      - gap 探针不可用（probe_used=False）
      - compliance 未完成的 PRISMA/AMSTAR-2 条目
      - evidence_tags 标记为 unverified / judgment 的维度
      - PROSPERO 自动检索失败（manual_url 回退）
      - 非英文库未覆盖
      - 临床价值维度未由 LLM/Coze 覆盖（默认中值）

    Returns list of {item, reason} (bilingual via lang).
    """
    L = _lang(lang)
    items = []

    T = {
        "zh": {
            "gap_unverified": "真实缺口探针不可用 — 新颖性/缺口判定未验证，结论不得外推",
            "gap_error": "缺口探针错误（%s）— 缺口判定不可靠",
            "compliance_gap": "合规预检未完成：%s 项待补（选题阶段须完成后再推进）",
            "compliance_risk": "合规风险：%s（%s）— 须在方案阶段前解决",
            "evidence_unverified": "「%s」维度未由真实探针验证（evidence_tag=%s），评分不可靠",
            "evidence_judgment": "「%s」维度为判断项（默认中值），建议人工/LLM 确认",
            "prospero_fail": "PROSPERO 自动检索不可用 — 已回退至手动核查链接，注册库未确认",
            "prospero_unavailable": "PROSPERO 自动检索不可用（%s）— 手动核查未完成",
            "non_english": "非英文库（中文/日文等）未覆盖 — 如需中文覆盖须手动补库",
            "cochrane_zero": "Cochrane 命中 0 — 原始研究可能不足，需警惕 k<2",
            "pubmed_zero": "PubMed SR/MA 命中 0 — 方向可能空白，需确认原始研究数",
            "prospero_no_registration": "PROSPERO 注册未列入下一步行动（R6 违规）— 推荐推进的选题必须先注册",
        },
        "en": {
            "gap_unverified": "Real-gap probe unavailable — novelty/gap verdict unverified, conclusions must not be extrapolated",
            "gap_error": "Gap probe error (%s) — gap verdict unreliable",
            "compliance_gap": "Compliance pre-check incomplete: %s items pending (must complete before proceeding)",
            "compliance_risk": "Compliance risk: %s (%s) — must be resolved before protocol phase",
            "evidence_unverified": "'%s' dimension NOT verified by real probe (evidence_tag=%s), score unreliable",
            "evidence_judgment": "'%s' dimension is a judgment item (default mid), suggest human/LLM confirmation",
            "prospero_fail": "PROSPERO auto-probe unavailable — fell back to manual check link, registry not confirmed",
            "prospero_unavailable": "PROSPERO auto-probe unavailable (%s) — manual check incomplete",
            "non_english": "Non-English databases (Chinese/Japanese/etc.) NOT covered — manual supplementation required if Chinese coverage needed",
            "cochrane_zero": "Cochrane hits = 0 — primary studies may be insufficient, watch for k<2",
            "pubmed_zero": "PubMed SR/MA hits = 0 — direction may be blank, confirm primary study count",
            "prospero_no_registration": "PROSPERO registration NOT listed in next actions (R6 violation) — recommended topics must register first",
        },
    }[L]

    gap = d.get("gap") or {}
    dedup = d.get("dedup") or {}
    compliance = d.get("compliance") or {}
    prospero = d.get("prospero") or {}
    evidence_tags = d.get("evidence_tags") or {}

    # 1) Gap probe status
    if gap.get("probe_used") is False:
        items.append({"item": "真实缺口 / Real-gap", "reason": T["gap_unverified"]})
    elif gap.get("verdict") == "unverified":
        items.append({"item": "真实缺口 / Real-gap", "reason": T["gap_unverified"]})

    # 2) Compliance gaps
    prisma = compliance.get("prisma", [])
    amstar = compliance.get("amstar2", [])
    gap_items = [p for p in prisma if p.get("status") == "gap"]
    gap_items += [a for a in amstar if a.get("status") in ("gap", "pending")]
    if gap_items:
        item_names = "; ".join(
            ("PRISMA #%s" % p.get("item", "?")) if "item" in p
            else ("AMSTAR-2 %s" % p.get("domain", "?"))
            for p in gap_items
        )
        items.append({"item": "合规预检 / Compliance pre-check",
                       "reason": T["compliance_gap"] % item_names})

    overall_risk = compliance.get("overall_risk", "yellow")
    if overall_risk == "red":
        items.append({"item": "合规风险 / Compliance risk",
                       "reason": T["compliance_risk"] % ("high", compliance.get("note", ""))})

    # 3) Evidence tag gaps
    dim_names_zh = {"clinical": "临床价值", "feasibility": "方法学可行性", "data": "数据可得性", "novelty": "新颖性"}
    dim_names_en = {"clinical": "Clinical value", "feasibility": "Methodological feasibility", "data": "Data availability", "novelty": "Novelty"}
    dn = dim_names_zh if L == "zh" else dim_names_en

    for dim, tag in evidence_tags.items():
        if tag == "unverified":
            items.append({"item": dn.get(dim, dim), "reason": T["evidence_unverified"] % (dim, tag)})
        elif tag == "judgment":
            items.append({"item": dn.get(dim, dim), "reason": T["evidence_judgment"] % dim})

    # 4) PROSPERO
    if prospero.get("status") == "unavailable":
        err = prospero.get("error") or "upstream failure"
        items.append({"item": "PROSPERO / PROSPERO", "reason": T["prospero_unavailable"] % err})
    elif prospero.get("manual_url") and not prospero.get("hit_count"):
        items.append({"item": "PROSPERO / PROSPERO", "reason": T["prospero_fail"]})

    # 5) Non-English
    items.append({"item": "语种 / Language", "reason": T["non_english"]})

    # 6) Zero hits warnings
    narrow = gap.get("narrow") or {}
    if narrow.get("cochrane") == 0:
        items.append({"item": "Cochrane", "reason": T["cochrane_zero"]})
    if narrow.get("pubmed") == 0:
        items.append({"item": "PubMed SR/MA", "reason": T["pubmed_zero"]})

    return items


# ---------------------------------------------------------------------------
# §22.16 — RAG three-column checklist
# ---------------------------------------------------------------------------

def build_rag_checklist(d, lang="auto"):
    """§22.16 — three-column review checklist (问题 / 原文位置 / 依据).

    For Meta-analysis, the synthesis questions map to report sections:
      - overall evidence volume & trend → §4 Four-Dimension Assessment + §5 Dedup
      - saturation / real-gap verdict → §4 gap evidence + §5 dedup
      - compliance pre-check status → §7 PRISMA/AMSTAR-2
      - cross-check rules R1–R6 → §4 cross_checks

    Returns list of dicts: {q, location, basis, covered(bool), note}.
    """
    L = _lang(lang)
    gap = d.get("gap") or {}
    dedup = d.get("dedup") or {}
    compliance = d.get("compliance") or {}
    cross_checks = d.get("cross_checks") or []
    scores = d.get("scores") or {}
    evidence_tags = d.get("evidence_tags") or {}
    topic = d.get("meta", {}).get("topic") or d.get("topic") or "—"

    n_sr = 0
    narrow = gap.get("narrow") or {}
    if narrow.get("cochrane") is not None:
        n_sr += narrow["cochrane"]
    if narrow.get("pubmed") is not None:
        n_sr += narrow["pubmed"]

    overall_risk = compliance.get("overall_risk", "yellow")
    risk_ok = overall_risk in ("green", "yellow")

    prisma_total = len(compliance.get("prisma", []))
    prisma_gap = len([p for p in compliance.get("prisma", []) if p.get("status") == "gap"])

    triggered_rules = [c.get("rule") for c in cross_checks if c.get("triggered")]

    if L == "zh":
        synth = [
            ("该选题的发表证据整体规模与饱和程度如何？",
             "§4 四维评估 + §5 去重检索报告",
             "Cochrane %d + PubMed SR/MA %d = 共 %d 篇同类综述；缺口判定=%s" % (
                 narrow.get("cochron", 0) or 0, narrow.get("pubmed", 0) or 0, n_sr,
                 gap.get("label", "未验证")),
             gap.get("probe_used") is True),
            ("是否存在近重复 Meta？增量是否明确？",
             "§5 去重检索报告（near_duplicate + increment）",
             "near_duplicate=%s; increment=%s" % (
                 dedup.get("near_duplicate", "—"), dedup.get("increment", "—")),
             bool(dedup.get("near_duplicate") and dedup.get("increment"))),
            ("PRISMA 2020 / AMSTAR-2 合规预检通过了吗？",
             "§7 合规预检",
             "PRISMA 共 %d 项，%d 待补；AMSTAR-2 整体风险=%s" % (
                 prisma_total, prisma_gap, overall_risk),
             risk_ok and prisma_gap == 0),
            ("R1–R6 交叉检查是否全部通过？",
             "§4 交叉检查规则",
             "触发规则：%s" % (", ".join(triggered_rules) if triggered_rules else "无"),
             len(triggered_rules) == 0),
            ("临床价值维度是否由真实探针或 LLM 评估覆盖？",
             "§4 四维评估（clinical）",
             "evidence_tag=%s, score=%s/5" % (
                 evidence_tags.get("clinical", "unverified"), scores.get("clinical", "—")),
             evidence_tags.get("clinical", "unverified") not in ("unverified", "judgment")),
        ]
    else:
        synth = [
            ("What is the overall evidence volume and saturation for this topic?",
             "§4 Four-Dimension Assessment + §5 Dedup Search Report",
             "Cochrane %d + PubMed SR/MA %d = %d同类 reviews total; gap verdict=%s" % (
                 narrow.get("cochrane", 0) or 0, narrow.get("pubmed", 0) or 0, n_sr,
                 gap.get("label", "unverified")),
             gap.get("probe_used") is True),
            ("Is there a near-duplicate meta? Is the increment clearly stated?",
             "§5 Dedup Search Report (near_duplicate + increment)",
             "near_duplicate=%s; increment=%s" % (
                 dedup.get("near_duplicate", "—"), dedup.get("increment", "—")),
             bool(dedup.get("near_duplicate") and dedup.get("increment"))),
            ("Did the PRISMA 2020 / AMSTAR-2 pre-check pass?",
             "§7 PRISMA/AMSTAR-2 Pre-check",
             "PRISMA %d items, %d pending; AMSTAR-2 risk=%s" % (
                 prisma_total, prisma_gap, overall_risk),
             risk_ok and prisma_gap == 0),
            ("Did all R1–R6 cross-check rules pass?",
             "§4 Cross-check rules",
             "Triggered rules: %s" % (", ".join(triggered_rules) if triggered_rules else "none"),
             len(triggered_rules) == 0),
            ("Is the clinical value dimension covered by real probe or LLM?",
             "§4 Four-Dimension Assessment (clinical)",
             "evidence_tag=%s, score=%s/5" % (
                 evidence_tags.get("clinical", "unverified"), scores.get("clinical", "—")),
             evidence_tags.get("clinical", "unverified") not in ("unverified", "judgment")),
        ]

    rows = []
    for q, loc, basis, covered in synth:
        rows.append({"q": q, "location": loc, "basis": basis,
                     "covered": covered, "note": ("" if covered else ("未覆盖 / NOT covered"))})

    return rows


# ---------------------------------------------------------------------------
# §22.17 — Stratified acceptance
# ---------------------------------------------------------------------------

def build_layer_acceptance(d, lang="auto"):
    """§22.17 — stratified acceptance: deterministic tool layer vs LLM-dependent output.

    Meta-analysis 的两层：
    - 确定性工具层：Europe PMC / Cochrane / PubMed 真实探针、注册库查询、
      PRISMA/AMSTAR-2 静态评分规则、R1–R6 规则校验。
    - LLM 依赖输出：临床价值维度（判断项，默认中值）、Coze 选题 curation、
      英文翻译确认（PICOS 检索词）。

    Returns dict with both layer blocks + their metrics.
    """
    L = _lang(lang)
    gap = d.get("gap") or {}
    dedup = d.get("dedup") or {}
    compliance = d.get("compliance") or {}
    cross_checks = d.get("cross_checks") or []
    scores = d.get("scores") or {}
    evidence_tags = d.get("evidence_tags") or {}
    triggered_rules = [c.get("rule") for c in cross_checks if c.get("triggered")]

    n_sr = 0
    narrow = gap.get("narrow") or {}
    if narrow.get("cochron") is not None:
        n_sr += narrow["cochron"]
    if narrow.get("pubmed") is not None:
        n_sr += narrow["pubmed"]

    overall_risk = compliance.get("overall_risk", "yellow")

    if L == "zh":
        deterministic = {
            "title": "确定性工具层（可独立验收 · 可入 CM0）",
            "components": [
                "真实探针驱动（Europe PMC / Cochrane / PubMed）— 非模板数字硬填",
                "ClinicalTrials.gov 注册库查询（%s）" % dedup.get("prospero", "自动检索"),
                "四维评分规则（R1–R6 规则校验，触发=%s）" % (", ".join(triggered_rules) if triggered_rules else "无"),
                "PRISMA 2020 / AMSTAR-2 静态合规预检（整体风险=%s）" % overall_risk,
            ],
            "metrics": "证据源：Cochrane=%s, PubMed=%s, 同类综述共 %d 篇；"
                       "coverage=%s；上述为确定性执行结果，可逐字节复现。" % (
                           narrow.get("cochron", "未探针"),
                           narrow.get("pubmed", "未探针"),
                           n_sr, gap.get("label", "未验证")),
            "accept": "确定性层可独立验证、可入 CM0；本运行 coverage=%s。" % gap.get("label", "未验证"),
        }
        llm_components = [
            "临床价值维度评估（evidence_tag=%s，默认中值 %s/5）" % (
                evidence_tags.get("clinical", "judgment"), scores.get("clinical", "—")),
            "Coze 选题 curation（如有，由 Coze 提供推荐 + 理由）",
            "英文翻译确认（PICOS 检索词派生，用户确认后生效）",
        ]
        # Count non-deterministic dims
        if evidence_tags:
            nondet = sum(1 for t in evidence_tags.values() if t in ("judgment", "unverified"))
        else:
            nondet = 4  # evidence_tags missing: assume all unverified
        llm = {
            "title": "LLM 依赖输出层（禁入 CM4 · 复杂域须人工复核）",
            "components": llm_components,
            "metrics": "非确定性维度数：%d / 4（evidence_tag 为 judgment/unverified）。"
                       "临床价值为判断项，默认中值不得视为可靠评估。" % nondet,
            "accept": "LLM 层仅在临床价值判断 + Coze curation + 翻译确认环节介入，"
                      "不生成证据结论、不操控探针结果；两层准确率分开声明，"
                      "严禁用「总体 X% 准」掩盖「判断项未验证」。",
        }
    else:
        deterministic = {
            "title": "Deterministic tool layer (independently verifiable · CM0-eligible)",
            "components": [
                "Real-probe driven (Europe PMC / Cochrane / PubMed) — not template-filled",
                "ClinicalTrials.gov registry query (%s)" % dedup.get("prospero", "auto-probe"),
                "Four-dimension scoring rules (R1–R6 rule check, triggered=%s)" % (
                    ", ".join(triggered_rules) if triggered_rules else "none"),
                "PRISMA 2020 / AMSTAR-2 static compliance pre-check (risk=%s)" % overall_risk,
            ],
            "metrics": "Sources: Cochrane=%s, PubMed=%s, total %d同类 reviews; "
                       "coverage=%s. Deterministic, byte-for-byte reproducible." % (
                           narrow.get("cochron", "not probed"),
                           narrow.get("pubmed", "not probed"),
                           n_sr, gap.get("label", "unverified")),
            "accept": "Deterministic layer is independently verifiable and CM0-eligible; "
                      "this run coverage=%s." % gap.get("label", "unverified"),
        }
        llm_components = [
            "Clinical value dimension (evidence_tag=%s, default mid %s/5)" % (
                evidence_tags.get("clinical", "judgment"), scores.get("clinical", "—")),
            "Coze topic curation (if present, Coze provides recommendation + rationale)",
            "English translation confirmation (PICOS search terms, user-confirmed)",
        ]
        nondet = sum(1 for t in evidence_tags.values() if t in ("judgment", "unverified"))
        llm = {
            "title": "LLM-dependent output layer (CM4-forbidden · complex domains need human review)",
            "components": llm_components,
            "metrics": "Non-deterministic dimensions: %d / 4 (evidence_tag judgment/unverified). "
                       "Clinical value is a judgment item; default mid is NOT a reliable assessment." % nondet,
            "accept": "The LLM layer only intervenes in clinical value judgment + Coze curation + "
                      "translation confirmation — it does NOT author evidence conclusions or "
                      "manipulate probe results. The two layers are reported separately; a single "
                      "'overall X% accurate' figure hiding 'unverified judgment items' is forbidden.",
        }

    return {"deterministic": deterministic, "llm": llm,
            "metrics": {
                "n_deterministic_dims": sum(1 for t in evidence_tags.values()
                                            if t not in ("judgment", "unverified")),
                "n_llm_dims": nondet,
                "total_evidence_hits": n_sr,
                "coverage": gap.get("label", "unverified"),
                "compliance_risk": overall_risk,
                "triggered_rules": triggered_rules,
            }}


# ---------------------------------------------------------------------------
# §22 Single entry point
# ---------------------------------------------------------------------------

def build_gov22(d, lang="auto"):
    """Single entry point used by both renderers.

    Args:
        d: generate_topic_report.py input JSON (topic_assess.py output)
        lang: 'zh' / 'en' / 'auto'

    Returns:
        {version, uncovered, checklist, layers, coverage, has_run}
    """
    return {
        "version": SKILL_VERSION,
        "uncovered": build_uncovered(d, lang),
        "checklist": build_rag_checklist(d, lang),
        "layers": build_layer_acceptance(d, lang),
        "coverage": (d.get("gap") or {}).get("label", "unverified"),
        "has_run": bool(d.get("gap") or d.get("dedup") or d.get("compliance")),
    }


# ---------------------------------------------------------------------------
# §22 Renderers (Markdown + HTML lock-step)
# ---------------------------------------------------------------------------

def render_gov22_md(gov, lang="auto"):
    """Render §22 governance sections as Markdown."""
    L = _lang(lang)
    lines = []

    # --- §22.16 Unchecked items ---
    if L == "zh":
        lines.append("\n---\n\n## §22.16 未覆盖项（显式漏项清单）\n")
        uncovered = gov.get("uncovered", [])
        if uncovered:
            lines.append("| 项目 | 原因 |\n|---|---|")
            for it in uncovered:
                lines.append("| %s | %s |" % (it.get("item", "—"), it.get("reason", "—")))
        else:
            lines.append("✅ 本运行无显式漏项（所有维度已覆盖）。")
    else:
        lines.append("\n---\n\n## §22.16 Uncovered Items (explicit gap list)\n")
        uncovered = gov.get("uncovered", [])
        if uncovered:
            lines.append("| Item | Reason |\n|---|---|")
            for it in uncovered:
                lines.append("| %s | %s |" % (it.get("item", "—"), it.get("reason", "—")))
        else:
            lines.append("✅ No uncovered items (all dimensions covered).")

    # --- §22.16 RAG checklist ---
    if L == "zh":
        lines.append("\n### RAG 三列待核对清单（问题 / 原文位置 / 依据）\n")
        checklist = gov.get("checklist", [])
        if checklist:
            lines.append("| 问题 | 原文位置 | 依据 | 已覆盖 | 备注 |\n|---|---|---|---|---|")
            for r in checklist:
                cov = "✅" if r.get("covered") else "❌"
                lines.append("| %s | %s | %s | %s | %s |" % (
                    r.get("q", "—"), r.get("location", "—"), r.get("basis", "—"),
                    cov, r.get("note", "")))
        else:
            lines.append("无清单项。")
    else:
        lines.append("\n### RAG Three-Column Checklist (question / location / basis)\n")
        checklist = gov.get("checklist", [])
        if checklist:
            lines.append("| Question | Location | Basis | Covered | Note |\n|---|---|---|---|---|")
            for r in checklist:
                cov = "✅" if r.get("covered") else "❌"
                lines.append("| %s | %s | %s | %s | %s |" % (
                    r.get("q", "—"), r.get("location", "—"), r.get("basis", "—"),
                    cov, r.get("note", "")))
        else:
            lines.append("No checklist items.")

    # --- §22.17 Layer acceptance ---
    layers = gov.get("layers", {})
    det = layers.get("deterministic", {})
    llm = layers.get("llm", {})

    if L == "zh":
        lines.append("\n---\n\n## §22.17 分层验收（确定性工具层 vs LLM 依赖输出）\n")
        lines.append("### %s\n" % det.get("title", ""))
        if det.get("components"):
            lines.append("\n".join("- %s" % c for c in det["components"]))
        lines.append("\n**指标**: %s" % det.get("metrics", ""))
        lines.append("\n**验收结论**: %s" % det.get("accept", ""))
        lines.append("\n### %s\n" % llm.get("title", ""))
        if llm.get("components"):
            lines.append("\n".join("- %s" % c for c in llm["components"]))
        lines.append("\n**指标**: %s" % llm.get("metrics", ""))
        lines.append("\n**验收结论**: %s" % llm.get("accept", ""))
    else:
        lines.append("\n---\n\n## §22.17 Layer Acceptance (Deterministic tool vs LLM-dependent)\n")
        lines.append("### %s\n" % det.get("title", ""))
        if det.get("components"):
            lines.append("\n".join("- %s" % c for c in det["components"]))
        lines.append("\n**Metrics**: %s" % det.get("metrics", ""))
        lines.append("\n**Acceptance**: %s" % det.get("accept", ""))
        lines.append("\n### %s\n" % llm.get("title", ""))
        if llm.get("components"):
            lines.append("\n".join("- %s" % c for c in llm["components"]))
        lines.append("\n**Metrics**: %s" % llm.get("metrics", ""))
        lines.append("\n**Acceptance**: %s" % llm.get("accept", ""))

    # Footer
    if L == "zh":
        lines.append("\n\n*§22 governance — processDefinitionVersion=%s。未覆盖项为默认失败模式，不得静默通过。*"
                     % gov.get("version", "—"))
    else:
        lines.append("\n\n*§22 governance — processDefinitionVersion=%s. Uncovered items are the default failure mode; silent pass is forbidden.*"
                     % gov.get("version", "—"))

    return "\n".join(lines)


def render_gov22_html(gov, lang="auto"):
    """Render §22 governance sections as HTML (lock-step with Markdown)."""
    import html as _html

    L = _lang(lang)
    lines = []

    def esc(s):
        return _html.escape(str(s), quote=True)

    # --- §22.16 Unchecked items ---
    if L == "zh":
        lines.append("<hr>\n<h2>§22.16 未覆盖项（显式漏项清单）</h2>\n")
        uncovered = gov.get("uncovered", [])
        if uncovered:
            lines.append("<table>\n<thead><tr><th>项目</th><th>原因</th></tr></thead>\n<tbody>")
            for it in uncovered:
                lines.append("<tr><td>%s</td><td>%s</td></tr>" % (
                    esc(it.get("item", "—")), esc(it.get("reason", "—"))))
            lines.append("</tbody>\n</table>")
        else:
            lines.append("<p>✅ 本运行无显式漏项（所有维度已覆盖）。</p>")
    else:
        lines.append("<hr>\n<h2>§22.16 Uncovered Items (explicit gap list)</h2>\n")
        uncovered = gov.get("uncovered", [])
        if uncovered:
            lines.append("<table>\n<thead><tr><th>Item</th><th>Reason</th></tr></thead>\n<tbody>")
            for it in uncovered:
                lines.append("<tr><td>%s</td><td>%s</td></tr>" % (
                    esc(it.get("item", "—")), esc(it.get("reason", "—"))))
            lines.append("</tbody>\n</table>")
        else:
            lines.append("<p>✅ No uncovered items (all dimensions covered).</p>")

    # --- §22.16 RAG checklist ---
    if L == "zh":
        lines.append("\n<h3>RAG 三列待核对清单（问题 / 原文位置 / 依据）</h3>\n")
        checklist = gov.get("checklist", [])
        if checklist:
            lines.append("<table>\n<thead><tr><th>问题</th><th>原文位置</th><th>依据</th><th>已覆盖</th><th>备注</th></tr></thead>\n<tbody>")
            for r in checklist:
                cov = "✅" if r.get("covered") else "❌"
                lines.append("<tr><td>%s</td><td>%s</td><td>%s</td><td style='text-align:center'>%s</td><td>%s</td></tr>" % (
                    esc(r.get("q", "—")), esc(r.get("location", "—")), esc(r.get("basis", "—")),
                    cov, esc(r.get("note", ""))))
            lines.append("</tbody>\n</table>")
        else:
            lines.append("<p>无清单项。</p>")
    else:
        lines.append("\n<h3>RAG Three-Column Checklist (question / location / basis)</h3>\n")
        checklist = gov.get("checklist", [])
        if checklist:
            lines.append("<table>\n<thead><tr><th>Question</th><th>Location</th><th>Basis</th><th>Covered</th><th>Note</th></tr></thead>\n<tbody>")
            for r in checklist:
                cov = "✅" if r.get("covered") else "❌"
                lines.append("<tr><td>%s</td><td>%s</td><td>%s</td><td style='text-align:center'>%s</td><td>%s</td></tr>" % (
                    esc(r.get("q", "—")), esc(r.get("location", "—")), esc(r.get("basis", "—")),
                    cov, esc(r.get("note", ""))))
            lines.append("</tbody>\n</table>")
        else:
            lines.append("<p>No checklist items.</p>")

    # --- §22.17 Layer acceptance ---
    layers = gov.get("layers", {})
    det = layers.get("deterministic", {})
    llm = layers.get("llm", {})

    if L == "zh":
        lines.append("\n<hr>\n<h2>§22.17 分层验收（确定性工具层 vs LLM 依赖输出）</h2>\n")
        lines.append("<h3>%s</h3>\n" % esc(det.get("title", "")))
        if det.get("components"):
            lines.append("<ul>" + "".join("<li>%s</li>" % esc(c) for c in det["components"]) + "</ul>")
        lines.append("<p><strong>指标</strong>: %s</p>" % esc(det.get("metrics", "")))
        lines.append("<p><strong>验收结论</strong>: %s</p>" % esc(det.get("accept", "")))
        lines.append("\n<h3>%s</h3>\n" % esc(llm.get("title", "")))
        if llm.get("components"):
            lines.append("<ul>" + "".join("<li>%s</li>" % esc(c) for c in llm["components"]) + "</ul>")
        lines.append("<p><strong>指标</strong>: %s</p>" % esc(llm.get("metrics", "")))
        lines.append("<p><strong>验收结论</strong>: %s</p>" % esc(llm.get("accept", "")))
    else:
        lines.append("\n<hr>\n<h2>§22.17 Layer Acceptance (Deterministic tool vs LLM-dependent)</h2>\n")
        lines.append("<h3>%s</h3>\n" % esc(det.get("title", "")))
        if det.get("components"):
            lines.append("<ul>" + "".join("<li>%s</li>" % esc(c) for c in det["components"]) + "</ul>")
        lines.append("<p><strong>Metrics</strong>: %s</p>" % esc(det.get("metrics", "")))
        lines.append("<p><strong>Acceptance</strong>: %s</p>" % esc(det.get("accept", "")))
        lines.append("\n<h3>%s</h3>\n" % esc(llm.get("title", "")))
        if llm.get("components"):
            lines.append("<ul>" + "".join("<li>%s</li>" % esc(c) for c in llm["components"]) + "</ul>")
        lines.append("<p><strong>Metrics</strong>: %s</p>" % esc(llm.get("metrics", "")))
        lines.append("<p><strong>Acceptance</strong>: %s</p>" % esc(llm.get("accept", "")))

    # Footer
    if L == "zh":
        lines.append("\n<p><em>§22 governance — processDefinitionVersion=%s。未覆盖项为默认失败模式，不得静默通过。</em></p>"
                     % esc(gov.get("version", "—")))
    else:
        lines.append("\n<p><em>§22 governance — processDefinitionVersion=%s. Uncovered items are the default failure mode; silent pass is forbidden.</em></p>"
                     % esc(gov.get("version", "—")))

    return "\n".join(lines)
