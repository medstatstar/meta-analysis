# -*- coding: utf-8 -*-
"""Phase 3 · Block C 本地优先管线驱动器（论文撰写与修改）。

设计约束（对齐 contracts/pipeline_stage/v1.0.0/SPEC.md §9 / roadmap Phase 3）：

- **不依赖 coze 部署**：本模块完全本地运行，不调用 run_stage/run_meta，故不触发出站鉴权。
  C1 初稿为**结构化骨架生成器**（本地启发式，数字自动填充 B1-B4 结果）；C2 AI 评审复用
  block_b.detect_overclaims（B3 单点实现）；C3 参考完整性核验为 🔴 红线（结构/PRISMA 检查 +
  CrossRef/PubMed 真实 API 核验，防 AI 虚构参考文献）；C4 证据表+投稿前 QA 含 🔴 终闸。
- 阶段序列（SPEC §9）：
    C1.draft          结构化初稿（Markdown，数字填充 B1-B4）
    C2.ai_review      AI 评审（复用 B3 过度声明检测）
    C3.ref_verify     参考完整性核验（🔴 reference_verification 红线）
    C4.evidence_qa    证据表 + 投稿前 QA（🔴 manuscript_approval 终闸）
- 返回结构与 run_pipeline / run_block_a / run_block_b 同构：{done, await_human, gate, final,
  stages[], attachments[], tool_card_outputs[]}。
- 红线闸名严格复用 coze_client._REDLINE_GATES：C3=reference_verification、C4=manuscript_approval。

依赖：coze_client（CONTRACT_VERSION / STAGE_SCHEMA_ID / _REDLINE_GATES）；block_b（_mk_stage /
detect_overclaims，信封与 B3 复用）；ref_verify（CrossRef/PubMed 真实参考文献核验，防虚构）。
"""

import re
import uuid

import coze_client as cc
from block_b import _mk_stage, detect_overclaims, B1, B2, B3, B4
from ref_verify import verify_references

# ---- Block C 阶段 ID（SPEC §9，严格匹配 coze 端编排对齐） ----
C1 = "C1.draft"
C2 = "C2.ai_review"
C3 = "C3.ref_verify"
C4 = "C4.evidence_qa"
BLOCK_C_SEQUENCE = [C1, C2, C3, C4]
BLOCK_C_TOTAL = len(BLOCK_C_SEQUENCE)

# C 阶段本地红线闸（严格复用 coze_client._REDLINE_GATES 枚举）
GATE_REF_VERIFY = "reference_verification"
GATE_MANUSCRIPT = "manuscript_approval"

# 初稿必含章节（本地结构核验用，中英文标题均识别）
_REQUIRED_SECTIONS = ["背景", "方法", "结果", "讨论", "结论",
                      "Background", "Methods", "Results", "Discussion", "Conclusion"]


# ---------------------------------------------------------------------------
# 信封构造（本地「prompt → 合法入参」层）
# ---------------------------------------------------------------------------
def build_block_c_env(topic=None, pipeline_id=None, query_origin=None):
    env = {
        "contract_version": cc.CONTRACT_VERSION,
        "schema": cc.STAGE_SCHEMA_ID,
        "pipeline_id": pipeline_id or f"blkC-{uuid.uuid4().hex[:8]}",
        "pipeline": {"name": "block_c", "block": "C", "cfg": {}},
        "request_id": str(uuid.uuid4()),
        "task": "manuscript_writing",
        "params": {"topic": topic},
        "stage": {"id": C1, "index": 0, "total": BLOCK_C_TOTAL,
                  "intent": "run", "prev_stage_id": None},
        "stage_context": {"human_decisions": [], "tool_card_outputs": [], "artifacts": []},
    }
    if query_origin:
        env["query_origin"] = query_origin
    return env


# ---------------------------------------------------------------------------
# B 阶段结果归一（block_c 消费 run_block_b 的输出信封）
# ---------------------------------------------------------------------------
def _extract_b_summary(b_env):
    """从 run_block_b 输出信封抽取 B1-B4 摘要，归一为统一结构。

    返回 {pairwise, nma, grade, overclaims, critical}。若传入的已是归一 dict 则原样补全。
    """
    if isinstance(b_env, dict) and "pairwise" in b_env and "grade" in b_env:
        # 已是归一 dict
        return {
            "pairwise": b_env.get("pairwise", {}),
            "nma": b_env.get("nma", {"status": "skipped", "reason": "无网络数据"}),
            "grade": b_env.get("grade", {}),
            "overclaims": b_env.get("overclaims", []),
            "critical": b_env.get("critical", False),
        }
    stages = (b_env or {}).get("stages", [])
    s_by_id = {s["stage"]["id"]: s for s in stages}
    pw = (s_by_id.get(B1, {}) or {}).get("stage_result", {})
    nma = pw.get("nma", {"status": "skipped", "reason": "无网络数据"})
    pw = pw.get("pairwise", pw)
    grade = (s_by_id.get(B2, {}) or {}).get("stage_result", {})
    b3 = (s_by_id.get(B3, {}) or {}).get("stage_result", {})
    b4 = (s_by_id.get(B4, {}) or {}).get("stage_result", {})
    return {
        "pairwise": pw,
        "nma": nma,
        "grade": grade,
        "overclaims": b3.get("hits", []),
        "critical": b4.get("critical", False),
    }


# ---------------------------------------------------------------------------
# C1 初稿生成（结构化 Markdown 骨架，数字自动填充 B1-B4）
# ---------------------------------------------------------------------------
def c1_draft(topic, b_summary, studies=None, overclaim_hits=None):
    """由 B1-B4 结果生成结构化 Markdown 初稿骨架。

    本地启发式：章节齐全、关键统计量（k / 合并效应 / CI / p / I2 / tau² / GRADE）自动填充；
    B3 检出的过度声明以「⚠️ 待核验」标注于讨论段，不擅自删改结论。返回 {manuscript, sections[]}。
    """
    pw = b_summary.get("pairwise", {}) or {}
    nma = b_summary.get("nma", {}) or {}
    grade = b_summary.get("grade", {}) or {}
    k = pw.get("k", 0)
    em = pw.get("effect_measure", "OR")
    te_r = pw.get("TE_random")
    ci_r = pw.get("ci_random") or pw.get("ci_fixed")
    p_r = pw.get("p_random", pw.get("p_fixed"))
    i2 = pw.get("I2")
    tau2 = pw.get("tau2")
    null = {"OR": 1.0, "HR": 1.0, "RR": 1.0, "MD": 0.0, "SMD": 0.0, "RD": 0.0}.get(em, 1.0)
    direction = "升高" if (te_r is not None and te_r > null) else ("降低" if te_r is not None else "—")

    def _fmt(x, n=2):
        return ("%.*f" % (n, x)) if isinstance(x, (int, float)) else str(x)

    eff_line = "尚无可计算研究" if k == 0 else (
        f"{em} 合并效应 = {_fmt(te_r)} "
        f"(95% CI {_fmt(ci_r[0])}–{_fmt(ci_r[1])}, p = {_fmt(p_r, 3)})"
    )
    i2_line = ("I² = %.0f%%" % (i2 * 100)) if isinstance(i2, (int, float)) else "I² = —"
    tau_line = (f"τ² = {_fmt(tau2)}" if isinstance(tau2, (int, float)) else "τ² = —")

    nma_line = "未执行网络 meta 分析（NMA）。"
    if nma.get("status") == "ok":
        comps = nma.get("result", {}).get("comparisons", []) or []
        nma_line = (f"网络 meta 分析（{nma.get('result', {}).get('model', ['random'])[0]} 模型）"
                    f"纳入 {nma.get('result', {}).get('n_treatments', [0])[0]} 个干预、"
                    f"{len(comps)} 组间接比较。")
    elif nma.get("status") in ("skipped", "error"):
        nma_line = f"网络 meta 分析未执行（{nma.get('reason', 'n/a')}）。"

    grade_line = grade.get("grade", "—")
    reasons = grade.get("reasons", [])

    # B3 过度声明警示
    oc = overclaim_hits or b_summary.get("overclaims", []) or []
    if oc:
        oc_block = "\n".join(
            f"  - [{h.get('id')}] {h.get('label')}（严重度 {h.get('severity')}）：{h.get('evidence', '')}"
            for h in oc
        )
        oc_section = (
            "\n\n### ⚠️ 待人工核验的潜在过度声明（来自 B3 检测，请勿直接作为结论）\n"
            f"{oc_block}"
        )
    else:
        oc_section = ""

    n_stud = len(studies) if studies else k
    manuscript = f"""# {topic or '未命名 Meta 分析'}

## 摘要
本系统评价与 meta 分析旨在评估上述干预的疗效与安全性。共纳入 {n_stud} 项研究，
主要合并效应 {eff_line}；{i2_line}，{tau_line}。GRADE 证据质量评级：{grade_line}。

## 1. 背景
（待撰写：研究背景、临床问题、既往证据缺口。）

## 2. 方法
- **研究设计**：系统评价与 meta 分析（PRISMA 报告规范）。
- **检索与筛选**：基于已确定的 PICOS 框架进行文献检索与双盲筛选。
- **数据提取**：按预设模板提取效应量与方差。
- **统计分析**：采用逆方差加权法合并效应量（{em}），随机效应模型（DerSimonian-Laird）。
  {('网络 meta 分析经本地 R netmeta 实现。' if nma.get('status') == 'ok' else '')}
- **证据质量**：GRADE 系统评价降级因素：{('；'.join(reasons) if reasons else '无重大降级')}。

## 3. 结果
- **纳入研究**：{n_stud} 项。
- **主要合并效应**：{eff_line}（效应方向：{direction}）。
- **异质性**：{i2_line}，{tau_line}。
- **网络 meta 分析**：{nma_line}
- **证据质量（GRADE）**：{grade_line}。

## 4. 讨论
（待撰写：结果解释、与既往研究一致性、临床意义、局限性。）
{oc_section}

## 5. 结论
（待撰写：基于上述证据的临床结论，须与 GRADE 评级和 CI 跨零情况一致。）

## 参考文献
（待补充：由 C3 参考完整性核验后生成。）
"""
    # 章节清单（用于 C3 结构核验）
    sections = re.findall(r"^##\s+(.+)$", manuscript, re.MULTILINE)
    return {"manuscript": manuscript, "sections": sections, "char_count": len(manuscript)}


# ---------------------------------------------------------------------------
# C2 AI 评审（复用 B3 detect_overclaims）
# ---------------------------------------------------------------------------
def c2_ai_review(manuscript, b_summary):
    """对生成的初稿做 AI 评审：复用 block_b.detect_overclaims（B3 单点实现）。

    若传入 manuscript 非空则审初稿全文；否则回退到 B3 已有命中。返回 {hits[], n_patterns,
    stats}。stats 来自 B1 pairwise，避免重复计算。
    """
    pw = b_summary.get("pairwise", {}) or {}
    stats = {"effect_measure": pw.get("effect_measure", "OR"),
             "ci_random": pw.get("ci_random"), "ci_fixed": pw.get("ci_fixed"),
             "p_random": pw.get("p_random"), "p_fixed": pw.get("p_fixed"),
             "k": pw.get("k"), "I2": pw.get("I2")}
    text = (manuscript or "")
    if text.strip():
        hits = detect_overclaims(text, stats)
    else:
        hits = b_summary.get("overclaims", []) or []
    return {"n_patterns": 12, "n_hits": len(hits), "hits": hits, "stats": stats}


# ---------------------------------------------------------------------------
# C3 参考完整性核验（🔴 reference_verification 红线，结构/PRISMA 检查）
# ---------------------------------------------------------------------------
def c3_reference_verify(manuscript, sections, references=None):
    """参考完整性核验（结构 + 真实 API）。

    检查：
      - 初稿必含章节（背景/方法/结果/讨论/结论）齐全；
      - 若提供参考列表：每条须有 doi 或 pmid → **CrossRef/PubMed 真实 API 核验**存在性与元数据，
        缺失/虚构标 critical；撤稿文献标 critical；双侧 DOI+PMID 交叉验证防拼接幻觉。
      - 若未提供参考（本地-only）：标记 coze_ready=False，提示待补充。
    返回 {report, critical, notes, coze_ready, ref_verifications[]}；红线闸由 run_block_c 统一构造。
    """
    notes = []
    issues = []
    ref_verifications = []
    critical = False

    # 1) 章节结构核验
    sec_text = " ".join(sections)
    missing = [s for s in ["背景", "方法", "结果", "讨论", "结论"]
               if s not in sec_text and s.title() not in sec_text
               and s.capitalize() not in sec_text]
    if missing:
        issues.append(f"初稿缺失必要章节：{', '.join(missing)}")
        critical = True
        notes.append("结构缺陷：缺失 PRISMA 必要章节，须补全后再送审。")

    # 2) 参考文献真实核验（CrossRef/PubMed API）
    coze_ready = False
    n_retracted = 0
    n_not_found = 0
    n_mismatch = 0

    if references is None:
        notes.append("未提供参考列表：本地结构核验通过，但真实参考文献核验须待补充（coze_ready=False）。")
        coze_ready = False
    else:
        n_ref = len(references)
        if n_ref == 0:
            issues.append("参考列表为空但正文引用了研究")
            notes.append("参考列表为空，建议补充至少纳入研究的出处。")
        else:
            # 真实 API 批量核验（CrossRef/PubMed）
            ref_verifications = verify_references(references)
            for rv in ref_verifications:
                status = rv.get("status")
                if status == "retracted":
                    critical = True
                    n_retracted += 1
                    issues.append(f"⚠️ 撤稿文献：{rv.get('title') or rv.get('doi') or rv.get('pmid')} — {rv.get('message')}")
                elif status == "not_found":
                    critical = True
                    n_not_found += 1
                    issues.append(f"⚠️ 未查到（疑似虚构）：DOI={rv.get('doi')} PMID={rv.get('pmid')} — {rv.get('message')}")
                elif status == "mismatch":
                    critical = True
                    n_mismatch += 1
                    issues.append(f"⚠️ 元数据不一致（疑似拼接）：{rv.get('title') or ''} — {rv.get('message')}")
                elif status == "error" and not rv.get("doi") and not rv.get("pmid"):
                    issues.append(f"⚠️ 缺少 doi/pmid：{rv.get('title', '?')}（无法核验）")

            # 撤稿计数传递给下游 B4
            if n_retracted > 0:
                notes.append(f"核验发现 {n_retracted} 篇撤稿文献，必须人工处置。")
            if n_not_found > 0:
                notes.append(f"核验发现 {n_not_found} 篇未查到（可能虚构），必须人工核查。")
            if n_mismatch > 0:
                notes.append(f"核验发现 {n_mismatch} 篇元数据不一致（标题/作者），必须人工核查。")

        if issues:
            notes.append(f"参考核验发现 {len(issues)} 处问题。")
        if not critical and n_ref > 0:
            coze_ready = True

    report = {
        "n_references": len(references) if references is not None else 0,
        "missing_sections": missing,
        "issues": issues,
        "critical": critical,
        "n_retracted": n_retracted,
        "n_not_found": n_not_found,
        "n_mismatch": n_mismatch,
        "coze_ready": coze_ready,
        "ref_verifications": ref_verifications,
        "note": "参考完整性核验：结构/PRISMA 层 + CrossRef/PubMed 真实 API 存在性/元数据核验；撤稿/虚构/拼接标 critical。",
    }
    return report


# ---------------------------------------------------------------------------
# C4 证据表 + 投稿前 QA（🔴 manuscript_approval 终闸）
# ---------------------------------------------------------------------------
def c4_evidence_qa(b_summary, c2_hits, c3_report):
    """生成 GRADE 证据表 + 投稿前 QA 清单。

    GRADE 证据表来自 B2 grade_report；QA 清单覆盖：统计量报告、森林图占位、过度声明处置、
    参考核验。终闸 manuscript_approval（required=True）；critical = C3 critical 或 C2 含 high 过度声明未处置。
    """
    grade = b_summary.get("grade", {}) or {}
    domain = grade.get("domain_ratings", {})
    evidence_table = {
        "grade": grade.get("grade", "—"),
        "downgrades": grade.get("downgrades", 0),
        "reasons": grade.get("reasons", []),
        "domain_ratings": domain,
    }
    high_oc = [h for h in (c2_hits or []) if h.get("severity") == "high"]
    qa = [
        {"item": "主要效应量（k/合并效应/CI/p）已报告", "pass": bool(b_summary.get("pairwise", {}).get("k"))},
        {"item": "异质性与 τ² 已报告", "pass": "I2" in str(b_summary.get("pairwise", {}).get("I2", "")) or
         b_summary.get("pairwise", {}).get("I2") is not None},
        {"item": "GRADE 证据表已生成", "pass": bool(grade.get("grade"))},
        {"item": "过度声明已检出并标注（C2）", "pass": True,
         "detail": f"{len(c2_hits or [])} 条，high={len(high_oc)}"},
        {"item": "参考完整性核验通过（C3）", "pass": not c3_report.get("critical", False),
         "detail": c3_report.get("note", "")},
        {"item": "high 级过度声明已处置", "pass": len(high_oc) == 0,
         "detail": "存在未处置的 high 级过度声明" if high_oc else "无"},
    ]
    critical = bool(c3_report.get("critical", False)) or len(high_oc) > 0
    return {"evidence_table": evidence_table, "qa": qa, "critical": critical,
            "n_high_overclaim": len(high_oc)}


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
# 编排：C1 → C2 → C3 → C4（本地优先）
# ---------------------------------------------------------------------------
def run_block_c(topic=None, studies=None, b_env=None, analysis=None, references=None,
                human_decision=None, pause_at=None):
    """本地优先 Block C 驱动器。返回与 run_pipeline 同构的 dict。

    - 消费 B 阶段结果：优先 b_env（run_block_b 输出信封），否则 analysis（归一 dict）。
    - 红线闸：C3=reference_verification、C4=manuscript_approval（均 required=True）。
      未持对应批准 → done=False / await_human=True / gate=首个未批准红线闸。
    - human_decision：单个 {"stage_id": C3|C4, "action": "approved"}，或多个批准的 list
      （生产 coze 流中跨阶段累积的批准凭据，一次性传入；本地单轮即可放行多闸）。
    - pause_at：P3 软停靠集合（fullflow HITL）。默认 None = 现状行为（仅 C3/C4 红线闸停）。
    """
    b_summary = _extract_b_summary(b_env if b_env is not None else analysis)
    env = build_block_c_env(topic)
    pid = env["pipeline_id"]
    stages = []

    # C1 初稿
    c1 = c1_draft(topic, b_summary, studies=studies,
                  overclaim_hits=b_summary.get("overclaims", []))
    s1 = _mk_stage(C1, 0, "completed",
                   {"manuscript": c1["manuscript"], "sections": c1["sections"],
                    "char_count": c1["char_count"]},
                   {"type": "review", "prompt": "请人工审阅初稿结构与事实准确性。",
                    "required": False, "gate": None})
    stages.append(s1)
    _st = _soft_stop(env, pid, stages, s1, C1, pause_at, human_decision)
    if _st:
        return _st

    # C2 AI 评审（复用 B3）
    c2 = c2_ai_review(c1["manuscript"], b_summary)
    s2 = _mk_stage(C2, 1, "completed", c2,
                   {"type": "review", "prompt": "请人工复核 AI 评审检出的过度声明。",
                    "required": False, "gate": None})
    stages.append(s2)
    _st = _soft_stop(env, pid, stages, s2, C2, pause_at, human_decision)
    if _st:
        return _st

    # C3 参考完整性核验（🔴 红线）
    c3 = c3_reference_verify(c1["manuscript"], c1["sections"], references)
    nha3 = {
        "type": "approve",
        "prompt": (f"参考完整性核验：{c3['n_references']} 条参考、"
                   f"{'发现严重问题（撤稿/缺章）' if c3['critical'] else '结构通过'}。"
                   f"请人工核验后批准（reference_verification）。"),
        "required": True,
        "gate": GATE_REF_VERIFY,
    }
    s3 = _mk_stage(C3, 2, "await_human" if c3["critical"] or True else "completed",
                   c3, nha3)
    stages.append(s3)

    # C4 证据表 + QA（🔴 终闸）
    c4 = c4_evidence_qa(b_summary, c2.get("hits", []), c3)
    nha4 = {
        "type": "approve",
        "prompt": (f"投稿前 QA：GRADE={c4['evidence_table']['grade']}，"
                   f"high 过度声明={c4['n_high_overclaim']}。"
                   f"{'存在未处置重大问题，' if c4['critical'] else ''}请人工核验后批准（manuscript_approval）。"),
        "required": True,
        "gate": GATE_MANUSCRIPT,
    }
    s4 = _mk_stage(C4, 3, "await_human", c4, nha4)
    stages.append(s4)

    base = {
        "pipeline_id": pid, "pipeline": env["pipeline"],
        "stages": stages, "attachments": [], "tool_card_outputs": [],
    }

    # 红线闸解析（按 C1→C4 顺序，首个未批准红线闸即阻断点）
    # human_decision 支持 单 dict 或 list[dict]（累积多闸批准）
    decisions = human_decision if isinstance(human_decision, list) else (
        [human_decision] if human_decision else [])
    for st in stages:
        nha = st.get("next_human_action") or {}
        if nha.get("gate") in cc._REDLINE_GATES and nha.get("required"):
            if any(_decision_approves(d, st["stage"]["id"]) for d in decisions):
                continue  # 该闸已批准，继续看下一个
            return {**base, "done": False, "await_human": True,
                    "gate": nha.get("gate"), "final": st}
    return {**base, "done": True, "await_human": False, "gate": None, "final": s4}
