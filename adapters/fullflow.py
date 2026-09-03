"""Fullflow HITL 控制器（spec: contracts/fullflow/v0.1.0/SPEC.md · 设计期草稿）。

把 Block A（方向/文献/数据准备）→ Block B（分析）→ Block C（撰稿）串成一条
**可交互流水线**：每个低准确度环节提供人工闸，暂停 → 展示 AI 草稿 →
人工「确认 / 修改 / 跳过」→ 把人工结果回写信封后续跑。会话状态落盘 JSON，
任意时刻可从上次闸位续跑（会话文件即审计日志）。

设计原则（用户 2026-08-31 定）：人-AI 协作，非全自动——控制器**绝不**伪造
人工决策；🔴 红线闸（A4/B4/C3/C4）只能由人放行，不接受 skip。

交互模式：agent-mediated。agent 收到 await_human 信封 → 渲染给用户 →
收集答复（HumanDecision，§6）→ 调 resume_fullflow(session_path, decision)。

已知限制（v0.1）：
- 续跑 = 重跑当前块（块层无断点续跑入口）；A1/A3/A4 为确定性本地启发式，
  重跑幂等；A2 文献检索会重复执行（成本可接受，后续版本可做块内断点）。
- revision 走输入参数的接缝目前只有 A4（extracted_rows → Block B studies）；
  其余阶段的 revision 为记录后的 stage_result 事后补丁（下游已按原值计算，
  人工修订以补丁形式呈现于信封与审计日志）。
"""

import copy
import datetime
import json
import os
import uuid

import coze_client as cc
import block_a
import block_b
import block_c

SESSION_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# 停靠点配置（spec §3）
# ---------------------------------------------------------------------------
DEFAULT_PAUSE_AT = {
    "A1.topic_selection",    # 选题（低准确度：本地启发式 PICOS 须人工确认）
    "A2.literature_search",  # 🟡 检索策略/覆盖确认（防沉默漏检：跳库/空结果）
    "A3.screening",          # 筛选（易带偏，逐条裁决）
    "A4.data_extraction",    # 🔴 红线
    "B4.quality_gate",       # 🔴 红线（final_inclusion）
    "C1.draft",              # 初稿人工改
    "C3.ref_verify",         # 🔴 红线
    "C4.evidence_qa",        # 🔴 红线终闸
}

# 红线闸 → 阶段 id（与 coze_client._REDLINE_GATES 对齐）
GATE_TO_STAGE = {
    "extraction_review": "A4.data_extraction",
    "final_inclusion": "B4.quality_gate",
    "reference_verification": "C3.ref_verify",
    "manuscript_approval": "C4.evidence_qa",
}
STAGE_TO_GATE = {v: k for k, v in GATE_TO_STAGE.items()}

# 可被 revise 替换的 stage_result 键（spec §5 editable_payload / §6.4 接缝）
EDITABLE_KEYS = {
    "A1.topic_selection": ["report"],
    "A3.screening": ["screened"],
    "A4.data_extraction": ["extracted_rows"],   # 真实接缝：直接作为 Block B studies
    "B4.quality_gate": ["report"],
    "C1.draft": ["manuscript", "sections"],
}

ACTIONS = {"approved", "revised", "skipped", "rejected"}
_BLOCK_SEQ = ["A", "B", "C"]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 会话持久化（spec §7）
# ---------------------------------------------------------------------------
class FullflowSession:
    """会话状态（schema §7）：加载/保存/游标推进。文件即审计日志。"""

    def __init__(self, data, path):
        self.data = data
        self.path = path

    # -- 构造 ---------------------------------------------------------------
    @classmethod
    def new(cls, topic, cfg, session_dir):
        pid = "ff-" + uuid.uuid4().hex[:12]
        data = {
            "session_version": SESSION_VERSION,
            "pipeline_id": pid,
            "topic": topic,
            "created_at": _now(),
            "updated_at": _now(),
            "cfg": cfg,
            "cursor": {"block": "A", "stage_id": None, "await_kind": None},
            "blocks": {b: {"envelope": None, "status": "pending"} for b in _BLOCK_SEQ},
            "human_decisions": [],
            "handoff": {},
        }
        os.makedirs(session_dir, exist_ok=True)
        return cls(data, os.path.join(session_dir, f"fullflow_session_{pid}.json"))

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data, path)

    # -- 持久化（原子写：临时文件 + rename） --------------------------------
    def save(self):
        self.data["updated_at"] = _now()
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # -- 便捷视图 -----------------------------------------------------------
    @property
    def cursor(self):
        return self.data["cursor"]

    def effective_pause_at(self):
        """cfg.pause_at 减去被人工 skipped 的软停阶段（skip = 本会话不再停靠）。"""
        skipped = {d["stage_id"] for d in self.data["human_decisions"]
                   if d.get("action") == "skipped" and d.get("stage_id")}
        return set(self.data["cfg"].get("pause_at") or []) - skipped

    def decisions_for_block(self, letter):
        """本块已放行凭据列表 → 传给块层 human_decision。

        spec §6.3 降级映射：approved 原样传；revised 的 revision 已由控制器
        写进输入参数/补丁（_extraction_input / _apply_revisions），此处同样
        降级为 approved 凭据放行闸——块层零改动消费人工修改。
        """
        # 阶段 id 形如 "A1.topic_selection"（块字母 + 序号），按首字母归块
        return [{"stage_id": d["stage_id"], "action": "approved"}
                for d in self.data["human_decisions"]
                if d.get("action") in ("approved", "revised")
                and isinstance(d.get("stage_id"), str)
                and d["stage_id"][:1] == letter]

    def revisions_for_block(self, letter):
        """本块各阶段最新 revision（stage_id → revision dict）。"""
        out = {}
        for d in self.data["human_decisions"]:
            if (d.get("action") == "revised" and isinstance(d.get("stage_id"), str)
                    and d["stage_id"][:1] == letter
                    and isinstance(d.get("revision"), dict)):
                out[d["stage_id"]] = d["revision"]
        return out

    def record_decision(self, decision):
        rec = {
            "decision_id": decision.get("decision_id") or f"d-{uuid.uuid4().hex[:8]}",
            "stage_id": decision.get("stage_id"),
            "gate": decision.get("gate"),
            "action": decision.get("action"),
            "revision": decision.get("revision"),
            "note": decision.get("note"),
            "decided_by": decision.get("decided_by") or "user",
            "decided_at": decision.get("decided_at") or _now(),
        }
        self.data["human_decisions"].append(rec)
        return rec

    def rewind(self, target_block):
        """Phase 2：回退到 target_block 起点，清空该块及下游块信封/状态，清除 handoff，
        重置 cursor。保留 human_decisions（审计不丢）。块内为整体重跑（无块内断点）。
        target_block 可为块字母或 stage_id，自动解析为块字母。"""
        letter = _block_of(target_block)
        if letter is None:
            raise ValueError(f"无法解析回退目标块：{target_block!r}")
        affected = _downstream_blocks(letter)
        for b in affected:
            self.data["blocks"][b] = {"envelope": None, "status": "pending"}
        self.data["handoff"] = {}
        self.data["cursor"] = {"block": letter, "stage_id": None, "await_kind": None}
        self.save()
        return affected


# ---------------------------------------------------------------------------
# 块运行（控制器 → 三块驱动器；复用既有闸语义，不重造）
# ---------------------------------------------------------------------------
def _run_block(letter, sess, debug, on_line=None, on_a4_event=None):
    cfg = sess.data["cfg"]
    creds = sess.decisions_for_block(letter) or None
    pause = sess.effective_pause_at() or None
    if letter == "A":
        # live 路径默认开启 A4 自动落盘（auto_fetch=True）：A3 摘要门控 → 下载 OA PDF →
        # 抽取 2×2 草稿。extracted_rows 经 handoff.studies_for_b 直送 B1。
        # extraction_table 为 None（演示/人工数据路径）时走 Path A，否则走 Path B 自动抽取。
        # Phase 2 真接缝：把本块 revision 解成覆盖参数注入块内重算（A2.query / A3.screened），
        # 使 revise 真正 propagate 到下游（A4 / studies_for_b / Block B），而非仅补丁信封。
        revs = sess.revisions_for_block("A")
        a2_rev = revs.get("A2.literature_search") or {}
        a3_rev = revs.get("A3.screening") or {}
        # A3 已批准且无任何 A2/A3 修订 → 仅跑 A4，复用缓存的 A1/A2/A3，避免整块重跑。
        # 普通 approve（非 revise）本就该直接续跑下游，原实现却把整块重算一遍。
        cached_env = sess.data["blocks"]["A"].get("envelope")
        a3_approved = bool(creds) and any(
            block_a._decision_approves(d, "A3") for d in
            (creds if isinstance(creds, list) else [creds]))
        start_stage = ("A4" if (a3_approved and not a2_rev and not a3_rev and cached_env)
                       else None)
        return block_a.run_block_a(
            sess.data["topic"], max_results=cfg.get("max_results", 50),
            year_from=cfg.get("year_from"),
            extraction_table=_extraction_input(sess),
            human_decision=creds, pause_at=pause, debug=debug,
            out_dir=cfg.get("session_dir", "."),
            auto_fetch=True,
            auto_fetch_dir=cfg.get("session_dir"),
            pdf_email=cfg.get("pdf_email"),
            max_attempts=cfg.get("max_attempts", 12),
            inclusion_hints=None,
            override_query=a2_rev.get("query"),
            override_screened=a3_rev.get("screened"), on_line=on_line,
            on_a4_event=on_a4_event,
            start_stage=start_stage,
            cached_envelope=(cached_env if start_stage else None))
    if letter == "B":
        return block_b.run_block_b(
            sess.data["handoff"].get("studies_for_b") or [],
            effect_measure=cfg.get("effect_measure", "OR"),
            nma=cfg.get("nma", False),
            human_decision=creds, pause_at=pause, debug=debug)
    return block_c.run_block_c(
        topic=sess.data["topic"], b_env=sess.data["blocks"]["B"].get("envelope"),
        human_decision=creds, pause_at=pause)


def _extraction_input(sess):
    """A4 extraction_table：优先人工 revision rows（list），否则原始配置值。"""
    rev = sess.revisions_for_block("A").get("A4.data_extraction") or {}
    rows = rev.get("extracted_rows")
    if isinstance(rows, list) and rows:
        return rows
    return sess.data["cfg"].get("extraction_table")


def _apply_revisions(env, revisions):
    """把人工 revision 补丁进信封对应 stage_result（A4 之外为事后补丁，见模块 docstring）。"""
    if not revisions:
        return env
    env = copy.deepcopy(env)
    for st in env.get("stages") or []:
        sid = (st.get("stage") or {}).get("id")
        rev = revisions.get(sid)
        if rev:
            base = st.get("stage_result") or {}
            st["stage_result"] = {**base, **{k: v for k, v in rev.items()
                                             if not str(k).startswith("_")}}
    return env


def _extraction_guard_check(sess):
    """进 B 前守卫双保险（spec §8.4）：extraction_table 为 CSV 路径时核验人工 stamp。"""
    table = _extraction_input(sess)
    if not (isinstance(table, str) and table.strip()):
        return None  # 非 CSV 路径（list / None）不适用守卫
    try:
        from extraction_guard import check_verified  # scripts/ 已在 sys.path（由调用方保证）
    except ImportError:
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "..", "scripts"))
            from extraction_guard import check_verified
        except ImportError:
            return None  # 守卫不可用时不阻塞（与 run_meta --trust-data 语义一致由人工闸兜底）
    ok, reason, status = check_verified(os.path.abspath(table))
    if ok:
        return None
    return {"gate": "extraction_review", "stage_id": "A4.data_extraction",
            "status": status, "reason": reason, "csv": os.path.abspath(table)}


# ---------------------------------------------------------------------------
# 控制器返回视图（FullflowView，spec §5）
# ---------------------------------------------------------------------------
def _stage_sid(stage):
    return (stage.get("stage") or {}).get("id")


def _view(sess, env):
    ff = {
        "session_path": sess.path,
        "cursor": None,  # 返回前统一刷新（cursor 在各分支会被推进）
        "await": {"kind": "done"},
        "handoff_preview": None,
    }
    if env is None:
        return {"fullflow": ff}
    ff["pipeline_id"] = env.get("pipeline_id")

    if env.get("await_human"):
        stage = env.get("final") or {}
        sid = _stage_sid(stage)
        gate = env.get("gate")
        nha = stage.get("next_human_action") or {}
        if gate:
            kind = "gate"
            options = ["approved", "revised", "rejected"]          # 🔴 红线闸拒 skip
        else:
            kind = "pause"
            options = ["approved", "revised", "skipped", "rejected"]  # 软停可 skip
        editable = {k: (stage.get("stage_result") or {}).get(k)
                    for k in EDITABLE_KEYS.get(sid, []) if k in (stage.get("stage_result") or {})}
        ff["await"] = {"kind": kind, "gate": gate, "stage_id": sid,
                       "prompt": nha.get("prompt"), "options": options,
                       "editable_payload": editable,
                       "stage_result": stage.get("stage_result"),
                       "nha": nha}  # 富载荷（覆盖/逐条决策等）供工作台与 agent 渲染
        sess.cursor.update({"stage_id": sid, "await_kind": kind})
        ff["cursor"] = dict(sess.cursor)
        return {"fullflow": ff}

    # 块完成 → handoff 确认 / 终态
    letter = sess.cursor["block"]
    if letter == "C":
        ff["await"] = {"kind": "done", "stage_id": _stage_sid(env.get("final") or {})}
        sess.cursor.update({"block": "done", "stage_id": None, "await_kind": "done"})
        ff["cursor"] = dict(sess.cursor)
        return {"fullflow": ff}

    nxt = "B" if letter == "A" else "C"
    if letter == "A":
        rows = None
        for st in env.get("stages") or []:
            if _stage_sid(st) == "A4.data_extraction":
                rows = (st.get("stage_result") or {}).get("extracted_rows")
        sess.data["handoff"]["studies_for_b"] = rows or []
        n_studies = len(rows or [])
        fields = sorted({k for r in (rows or []) if isinstance(r, dict) for k in r})
    else:
        n_studies = len(sess.data["handoff"].get("studies_for_b") or [])
        fields = None
    ff["await"] = {"kind": "handoff_confirm", "gate": None, "stage_id": None,
                   "prompt": f"Block {letter} 完成，即将进入 Block {nxt}。请确认交接数据。",
                   "options": ["approved", "rejected"]}
    ff["handoff_preview"] = {"next": f"Block {nxt}", "n_studies": n_studies, "fields": fields}
    sess.cursor.update({"block": nxt, "stage_id": None, "await_kind": "handoff_confirm"})
    ff["cursor"] = dict(sess.cursor)
    return {"fullflow": ff}


# ---------------------------------------------------------------------------
# 公开入口（spec §4）
# ---------------------------------------------------------------------------
def run_fullflow(topic: str, *, max_results: int = 50, year_from=None,
                 effect_measure: str = "OR", nma: bool = False,
                 pause_at=None, extraction_table=None,
                 session_dir: str = ".", debug: bool = False,
                 pdf_email: str = None, max_attempts: int = 12,
                 on_line=None, on_a4_event=None) -> dict:
    """启动 fullflow：跑 Block A，遇停靠点即停。返回 = 块信封 + fullflow 视图。

    pdf_email / max_attempts 透传给 Block A 的 A4 自动落盘（A3 摘要门控 → OA PDF
    下载 → 抽取 2×2 表草稿）。live 路径默认开启 auto_fetch，使「检索→A4→B1」
    真正贯通：A4 产出的 extracted_rows 经 handoff.studies_for_b 直接喂给 B1。
    """
    if pause_at is None:
        pause_at = DEFAULT_PAUSE_AT
    cfg = {"max_results": max_results, "year_from": year_from,
           "effect_measure": effect_measure, "nma": nma,
           "pause_at": sorted(pause_at), "extraction_table": extraction_table,
           "session_dir": session_dir, "pdf_email": pdf_email,
           "max_attempts": max_attempts}
    sess = FullflowSession.new(topic, cfg, session_dir)
    return _advance(sess, debug=debug, on_line=on_line, on_a4_event=on_a4_event)


def resume_fullflow(session_path: str, decision: dict, *, debug: bool = False,
                    on_line=None, on_a4_event=None) -> dict:
    """带人工决策续跑。自动判断该进下一阶段 / 下一块 / 结束。返回同 run_fullflow。"""
    sess = FullflowSession.load(session_path)
    err = _validate_decision(sess, decision)
    if err:
        return {"error": err, **_view(sess, sess.data["blocks"][sess._awaiting_block()]
                                      .get("envelope"))}
    action = decision.get("action")
    # Phase 2：revise 已离开的块 → 回退该块并重算下游（真重跑，而非仅补丁信封）
    if action == "revised":
        sid = decision.get("stage_id")
        tgt = _block_of(sid)
        cur = sess.cursor.get("block")
        if tgt is not None and cur in _BLOCK_SEQ and _BLOCK_SEQ.index(tgt) < _BLOCK_SEQ.index(cur):
            sess.record_decision(decision)
            sess.rewind(tgt)
            return _advance_until_pause(sess, debug=debug, on_line=on_line, on_a4_event=on_a4_event)
    sess.record_decision(decision)
    sess.save()
    if action == "rejected":
        # 打回重做：停在原地，重放上一视图（决策已留痕审计）
        view = sess.data.get("last_view") or _view(
            sess, sess.data["blocks"][sess._awaiting_block()].get("envelope"))
        view = copy.deepcopy(view)
        view["fullflow"]["note"] = decision.get("note") or "人工打回，请修订后重新决策。"
        return view
    return _advance(sess, debug=debug, on_a4_event=on_a4_event)


def _awaiting_block(self):
    """当前等待人工的块（cursor.block 的前一个块；done 时为 C）。"""
    b = self.cursor["block"]
    if b in _BLOCK_SEQ:
        return b
    return "C"


FullflowSession._awaiting_block = _awaiting_block


def _validate_decision(sess, decision):
    """红线校验（spec §8）：绝不自动 approve；红线闸拒 skip；stage/gate 必须对得上。"""
    if not isinstance(decision, dict):
        return "decision 必须是 dict（spec §6.1）"
    action = decision.get("action")
    if action not in ACTIONS:
        return f"action 须为 {sorted(ACTIONS)} 之一，收到 {action!r}"
    kind = sess.cursor.get("await_kind")
    if kind == "done":
        return "会话已完成，无待决策项"
    if kind == "handoff_confirm":
        if action not in ("approved", "rejected"):
            return "块间交接确认仅接受 approved / rejected"
        return None
    expect_sid = sess.cursor.get("stage_id")
    sid = decision.get("stage_id")
    if sid != expect_sid:
        # Phase 2：revise 已离开的块（如 cursor 在 B、revise A3）允许，将触发 rewind 重算
        if action == "revised":
            tgt = _block_of(sid)
            cur = sess.cursor.get("block")
            if tgt is not None and cur in _BLOCK_SEQ and _BLOCK_SEQ.index(tgt) < _BLOCK_SEQ.index(cur):
                return None
        return f"stage_id 不匹配：当前停靠在 {expect_sid!r}，收到 {sid!r}"
    if action == "revised" and not isinstance(decision.get("revision"), dict):
        return "action=revised 须提供 revision dict（可编辑键见 editable_payload）"
    if action == "skipped":
        gate = STAGE_TO_GATE.get(sid)
        if gate and gate in cc._REDLINE_GATES:
            return f"🔴 红线闸 {gate} 不接受 skipped（spec §8.2），请 approve/revise/reject"
    return None


def _advance(sess, debug=False, on_line=None, on_a4_event=None):
    """推进：跑 cursor 所指块（含 revision 补丁），遇停即存即返。"""
    letter = sess.cursor["block"]
    if letter == "done":
        return {"fullflow": {"session_path": sess.path, "cursor": dict(sess.cursor),
                             "await": {"kind": "done"}}}

    # 进 B 前守卫双保险（spec §8.4）
    if letter == "B":
        guard = _extraction_guard_check(sess)
        if guard:
            sess.cursor["await_kind"] = "guard_blocked"
            sess.save()
            return {"fullflow": {"session_path": sess.path, "cursor": dict(sess.cursor),
                                 "await": {"kind": "guard_blocked", **guard,
                                           "prompt": (f"提取数据 CSV 未通过人工核验闸：{guard['reason']} "
                                                      "请先 extract_assist.py stamp --confirm 后再 approve。"),
                                           "options": ["approved"]},
                                 "handoff_preview": None}}

    try:
        env = _run_block(letter, sess, debug, on_line=on_line, on_a4_event=on_a4_event)
    except Exception as e:  # noqa: BLE001 — coze 失败/网络异常返回结构化错误，不推进
        sess.cursor["await_kind"] = sess.cursor.get("await_kind") or "error"
        sess.save()
        return {"error": f"{type(e).__name__}: {e}",
                "fullflow": {"session_path": sess.path, "cursor": dict(sess.cursor),
                             "await": {"kind": "error"}, "handoff_preview": None}}

    env = _apply_revisions(env, sess.revisions_for_block(letter))

    block = sess.data["blocks"][letter]
    block["envelope"] = env
    block["status"] = "done" if env.get("done") else "await_human"

    view = _view(sess, env)
    # handoff / done 时 cursor 已推进；gate/pause 时停在块内
    sess.data["last_view"] = view
    sess.save()
    return {"fullflow": view["fullflow"], **{k: v for k, v in env.items()
                                             if k not in ("fullflow",)}}


# ---------------------------------------------------------------------------
# Phase 2：_rewind(target) 回退重跑 + revise 真重跑下游
# ---------------------------------------------------------------------------
def _block_of(stage_id):
    """stage_id 形如 'A2.literature_search' 或块字母 'A'/'B'/'C' → 块字母；无法解析返回 None。"""
    if stage_id in _BLOCK_SEQ:
        return stage_id
    if isinstance(stage_id, str) and stage_id[:1] in _BLOCK_SEQ:
        return stage_id[:1]
    return None


def _downstream_blocks(letter):
    """letter 及其下游块（含自身）。A→[A,B,C]; B→[B,C]; C→[C]。"""
    return _BLOCK_SEQ[_BLOCK_SEQ.index(letter):]


def _advance_until_pause(sess, debug=False, on_line=None, on_a4_event=None):
    """rewind 后自动续跑：遇 handoff_confirm 自动批准续跑，遇 pause/gate/done/error 即停。
    使回退后下游真正重算到原闸位/完成态。"""
    for _ in range(len(_BLOCK_SEQ) + 2):
        kind = sess.cursor.get("await_kind")
        if kind == "handoff_confirm":
            sess.record_decision({
                "stage_id": None, "gate": None, "action": "approved",
                "note": "rewind 自动续跑：handoff 自动批准", "decided_by": "system_rewind",
            })
            view = _advance(sess, debug=debug, on_line=on_line, on_a4_event=on_a4_event)
        elif kind in (None,):
            view = _advance(sess, debug=debug, on_line=on_line, on_a4_event=on_a4_event)
        else:
            return {"fullflow": {"session_path": sess.path, "cursor": dict(sess.cursor),
                                 "await": {"kind": kind}}}
        if "error" in view:
            return view
        k = view.get("fullflow", {}).get("await", {}).get("kind")
        if k in ("pause", "gate", "done", "error"):
            return view
        # k == handoff_confirm → 下一轮循环继续
    return view


def rewind_fullflow(session_path: str, target_stage_id: str, *, debug: bool = False,
                    on_line=None, on_a4_event=None) -> dict:
    """Phase 2 公开入口：回退到 target 所属块并重算下游，直到回到原闸位/完成。

    target 可为块字母（'A'/'B'/'C'）或 stage_id（'A2.literature_search' 等）；
    回退粒度为块级（块内整体重跑）。清空 target 块及下游块信封 + handoff，
    重置 cursor 到该块起点，保留 human_decisions 审计。
    """
    sess = FullflowSession.load(session_path)
    letter = _block_of(target_stage_id)
    if letter is None:
        return {"error": f"无法解析回退目标块：{target_stage_id!r}"}
    sess.rewind(letter)
    return _advance_until_pause(sess, debug=debug, on_line=on_line, on_a4_event=on_a4_event)
