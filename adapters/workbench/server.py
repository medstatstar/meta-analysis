"""meta-analysis 工作台：后端（Phase 1）。

包装现有 fullflow HITL 状态机，暴露 REST API + 静态 SPA。
- 红线校验原样保留：decide 走 resume_fullflow → _validate_decision（拒 skip / 人工放行）。
- 进度由 blocks[A/B/C].envelope.stages 动态重建，零重写核心逻辑。
- 启动默认仅跑 Block A（run_fullflow 止于首个人工闸），不触网即可在离线模式演示。

运行：用 coze venv 的 python 起（含 fastapi/uvicorn）。详见 launch_workbench.py。
"""
import os
import sys
import json
import asyncio
import queue
import threading
import time

# 把 adapters/ 与 workbench/（自身目录）加入路径：
# - adapters/ 使 import fullflow / block_a / coze_client 可用；
# - workbench/ 使同目录的 import form_schema 可用（无论从哪个 cwd 启动都稳）。
_HERE = os.path.dirname(os.path.abspath(__file__))
_ADAPTERS = os.path.dirname(_HERE)
for _p in (_ADAPTERS, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fullflow  # noqa: E402
import form_schema  # noqa: E402
import block_a  # noqa: E402
from fullflow import FullflowSession, run_fullflow, resume_fullflow, rewind_fullflow  # noqa: E402
import literature_probe  # noqa: E402

from fastapi import FastAPI, HTTPException, UploadFile, File, Form  # noqa: E402
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, Response  # noqa: E402
from typing import Optional  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

APP_DIR = _HERE
RUNS_DIR = os.path.join(APP_DIR, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

app = FastAPI(title="meta-analysis workbench", version="0.1.0")


def _session_studies(sess):
    """从会话 envelope 取 A2.studies（best-effort，取不到返回空列表）。"""
    try:
        env = ((sess.data.get("blocks") or {}).get("A") or {}).get("envelope") or {}
        return env.get("A2", {}).get("studies") or []
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# 状态重建（进度时间轴 + await + form_schema + 审计）
# ---------------------------------------------------------------------------
def build_state(sess):
    ff = (sess.data.get("last_view") or {}).get("fullflow") or {}
    await_block = ff.get("await") or {"kind": "done"}
    progress = []
    # 节点级 schema + result：供工作台点开「已完成的自动/人工节点」查看（不限于当前 await 节点）
    stage_schema = {}
    stage_results = {}
    for b in ("A", "B", "C"):
        env = sess.data["blocks"][b].get("envelope")
        if not env:
            continue
        for i, st in enumerate(env.get("stages") or []):
            sid = (st.get("stage") or {}).get("id")
            st_status = st.get("status")
            is_await = (sid == await_block.get("stage_id"))
            progress.append({
                "block": b, "index": i, "stage_id": sid,
                "status": st_status, "awaiting": bool(is_await),
            })
            if sid:
                stage_schema[sid] = form_schema.schema_for(sid)
                if st_status in ("completed", "done", "await_human"):
                    stage_results[sid] = st.get("stage_result")
    return {
        "session": {
            "pipeline_id": sess.data["pipeline_id"],
            "topic": sess.data["topic"],
            "created_at": sess.data["created_at"],
            "updated_at": sess.data["updated_at"],
            "cursor": ff.get("cursor") or sess.data["cursor"],
            "path": sess.path,
        },
        "progress": progress,
        "await": await_block,
        "form_schema": form_schema.schema_for(
            await_block.get("stage_id"), await_block.get("kind")),
        "audit": sess.data["human_decisions"],
        "handoff_preview": ff.get("handoff_preview"),
        "stage_schema": stage_schema,
        "stage_results": stage_results,
    }


# ---------------------------------------------------------------------------
# SSE 辅助 + A4 实时预览输入抽取
# ---------------------------------------------------------------------------
def _sse(obj):
    """把事件 dict 序列化为一条 SSE 报文（data: <json>\n\n）。"""
    return "data: " + json.dumps(obj, ensure_ascii=False, default=str) + "\n\n"


# ---------------------------------------------------------------------------
# 通用「阻塞调用 → SSE」包装（供前端底部信息栏消费）
#
# 复用上面 _sse + StreamingResponse 这套现成模式（A4 预览已在用），不另造一套。
# 背景：run_fullflow / resume_fullflow 是阻塞式的，一次 Block A 真实检索约 15–60s，
# 期间前端拿不到任何反馈。本包装把它放进线程，实时推：
#   log  —— 人类可读的阶段提示（开始 / 停在哪个闸 / 错误）；此外 call 可通过
#           on_line 回调把子进程（ct-literature）的实时输出行直接推流，
#           实现「细粒度进度」（检索到第几篇、引文核验结果等），而非只有块级提示。
#   tick —— 每 2s 心跳 + 已运行秒数（证明后端还活着，防「假死」误判）
#   done —— 完整 state（与 /api/start 返回结构一致，前端直接用）
#   error—— 异常（含类型名）
# 不改动 fullflow / block_a / coze_client 的既有行为：on_line 为可选参数，
# 不传时子进程走原一次性捕获路径。
# ---------------------------------------------------------------------------
_MAX_SUBPROC_LINES = 400   # 子进程实时行上限，超出后丢弃（防刷屏撑爆信息栏）


async def _stream_blocking(call, start_msg, stage_hint=""):
    # 必须是 async：端点在事件循环线程里执行，才能拿到 running loop 投递 executor。
    # （写成同步 def 会被 FastAPI 丢进 AnyIO worker 线程，那里没有事件循环。）
    loop = asyncio.get_running_loop()
    q: queue.Queue = queue.Queue()
    stop = threading.Event()

    def _ticker(t0):
        while not stop.wait(2.0):
            q.put({"event": "tick", "elapsed": round(time.time() - t0, 1)})

    def _make_on_line():
        """子进程实时输出 → SSE log 事件（带清洗 + 条数上限）。"""
        state = {"n": 0, "capped": False}

        def _push(line):
            txt = (line or "").rstrip()
            if not txt:
                return
            if state["n"] >= _MAX_SUBPROC_LINES:
                if not state["capped"]:
                    state["capped"] = True
                    q.put({"event": "log", "level": "warn",
                           "msg": f"（子进程输出超过 {_MAX_SUBPROC_LINES} 行，后续省略）"})
                return
            state["n"] += 1
            lvl = "warn" if txt.startswith("[WARN]") else (
                "err" if txt.startswith("[ERR") else (
                    "ok" if txt.startswith("[OK]") else "info"))
            q.put({"event": "log", "level": lvl, "msg": txt[:300]})

        return _push

    def _make_on_a4():
        """a4_stream 逐篇进度事件 → SSE 的 a4 事件（前端实时渲染下载/抽取进度）。"""
        def _push(ev):
            try:
                q.put({"event": "a4", "a4": ev,
                       "index": ev.get("index"), "total": ev.get("total")})
            except Exception:  # noqa: BLE001
                pass
        return _push

        return _push

    def _worker():
        t0 = time.time()
        threading.Thread(target=_ticker, args=(t0,), daemon=True).start()
        try:
            out = call(on_line=_make_on_line(), on_a4_event=_make_on_a4()) or {}
            if out.get("error"):
                q.put({"event": "log", "level": "warn",
                       "msg": f"引擎返回错误：{out['error']}"})
            path = (out.get("fullflow") or {}).get("session_path")
            if not path:
                q.put({"event": "error", "message": f"未返回会话路径：{out}"})
            else:
                state = build_state(FullflowSession.load(path))
                aw = state.get("await") or {}
                if aw.get("kind") == "done":
                    q.put({"event": "log", "level": "ok", "msg": "全部阶段已通过，流程完成"})
                elif aw.get("stage_id"):
                    title = (state.get("form_schema") or {}).get("title") or aw["stage_id"]
                    q.put({"event": "log", "level": "ok",
                           "msg": f"停在 {aw['stage_id']}（{title}），等待人工决策"})
                q.put({"event": "done", "elapsed": round(time.time() - t0, 1),
                       "state": state})
        except Exception as e:  # noqa: BLE001 — 线程内异常无法走 HTTPException，转为事件
            q.put({"event": "error", "message": f"{type(e).__name__}: {e}"})
        finally:
            stop.set()
            q.put(None)  # 哨兵：流结束

    async def _gen():
        q.put({"event": "log", "level": "info", "msg": start_msg})
        if stage_hint:
            q.put({"event": "log", "level": "info", "msg": stage_hint})
        loop.run_in_executor(None, _worker)
        while True:
            ev = await loop.run_in_executor(None, q.get)
            if ev is None:
                break
            yield _sse(ev)

    return StreamingResponse(_gen(), media_type="text/event-stream")


def _a4_inputs_from_session(sess):
    """从会话 Block A 信封抽取 A4 预览所需输入：A2 的 studies + A3 的 screened。"""
    env = (sess.data.get("blocks") or {}).get("A", {}).get("envelope") or {}
    studies, screened = [], []
    for st in env.get("stages") or []:
        sid = (st.get("stage") or {}).get("id")
        sr = st.get("stage_result") or {}
        if sid == "A2.literature_search":
            studies = sr.get("studies") or []
        elif sid == "A3.screening":
            screened = sr.get("screened") or []
    # 兜底：某些信封把 studies 直接挂在 A2 stage_result 的嵌套里
    if not studies:
        studies = ((env.get("stage_result") or {}).get("studies")) or []
    return studies, screened


# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------
class StartReq(BaseModel):
    topic: str
    max_results: int = 50
    year_from: Optional[int] = None
    effect_measure: str = "OR"
    nma: bool = False
    pause_at: Optional[list] = None
    session_dir: str = RUNS_DIR


class DecideReq(BaseModel):
    session_path: str
    stage_id: str
    action: str
    revision: Optional[dict] = None
    note: Optional[str] = None


class RewindReq(BaseModel):
    session_path: str
    target_stage_id: str
    note: Optional[str] = None


class A4PreviewReq(BaseModel):
    session_path: str = ""          # 主：从会话抽取 A2.studies / A3.screened
    studies: Optional[list] = None   # 覆盖：前端直接传入（优先于 session_path 抽取）
    screened: Optional[list] = None
    pdf_dir: Optional[str] = None
    max_attempts: int = 12
    email: Optional[str] = None
    cached_only: bool = False        # True=仅抽本地已下载 PDF 的篇目，待上传篇目不排队

class TopicHelpReq(BaseModel):
    topic: str
    year_from: Optional[int] = None


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "version": "0.1.0"}


@app.post("/api/start")
def api_start(req: StartReq):
    out = run_fullflow(
        req.topic, max_results=req.max_results, year_from=req.year_from,
        effect_measure=req.effect_measure, nma=req.nma,
        pause_at=set(req.pause_at) if req.pause_at else None,
        session_dir=req.session_dir)
    ff = out.get("fullflow") or {}
    path = ff.get("session_path")
    if not path:
        raise HTTPException(500, f"run_fullflow 未返回会话路径：{out}")
    return build_state(FullflowSession.load(path))


@app.post("/api/start_stream")
async def api_start_stream(req: StartReq):
    """启动流程（SSE 流式版）。语义与 /api/start 完全一致，仅传输方式不同：

    阻塞计算放线程执行，期间推送阶段提示 + 心跳，供前端底部信息栏实时显示，
    解决「单击提交后界面长期冻结无反馈」的问题。
    """
    def _call(on_line=None, on_a4_event=None):
        return run_fullflow(
            req.topic, max_results=req.max_results, year_from=req.year_from,
            effect_measure=req.effect_measure, nma=req.nma,
            pause_at=set(req.pause_at) if req.pause_at else None,
            session_dir=req.session_dir, on_line=on_line,
            on_a4_event=on_a4_event)

    msg = (f"启动流程 · 主题「{req.topic}」· 检索上限 {req.max_results}"
           + (f" · 起始年 {req.year_from}" if req.year_from else "")
           + f" · 效应量 {req.effect_measure}")
    return await _stream_blocking(_call, msg,
                            stage_hint="Block A 运行中：A1 选题 → A2 检索 → A3 初筛 → A4 数据提取"
                                       "（真实检索需联网，约 15–60 秒）")


@app.get("/api/session")
def api_session(path: str):
    if not os.path.exists(path):
        raise HTTPException(404, f"会话不存在：{path}")
    return build_state(FullflowSession.load(path))

@app.post("/api/topic_help")
def api_topic_help(req: TopicHelpReq):
    # 本地启发式分析（PICOS 推断 / 缺失维度 / 可行性判定）先算，与网络探针解耦：
    # 即使 Europe PMC 探针失败，分析结果 + 建议仍要输出（用户核心诉求：原按钮漏掉了这部分）。
    try:
        analysis, _ = block_a.a1_topic_selection(req.topic, registry_probe=None)
    except Exception:
        analysis = None
    # 命中题轨的自包含上游闸：literature_probe 直连 Europe PMC，
    # 返回真实命中数（Cochrane + PubMed SR/MA），用于选题可行性速览。
    try:
        res = literature_probe.dedup_probe(req.topic, year_from=req.year_from, max_results=8)
        res["ok"] = True
    except Exception as e:  # 网络/解析失败 → 优雅降级，不整页冒，但 analysis 仍返回
        res = {"topic": req.topic, "ok": False, "error": str(e),
               "layers": {}, "summary": "", "any_error": True}
    res["topic_analysis"] = analysis
    return res


@app.post("/api/rewind")
def api_rewind(req: RewindReq):
    out = rewind_fullflow(req.session_path, req.target_stage_id)
    if "error" in out:
        raise HTTPException(400, out["error"])
    # 审计：打回/回退必须留痕（rejected + 回退目标），human_decisions 在 rewind 中保留不丢
    sess = FullflowSession.load(req.session_path)
    sess.record_decision({
        "stage_id": None, "gate": None, "action": "rejected",
        "revision": {"rewind_to": req.target_stage_id},
        "note": (req.note or "") + (f" 打回并回退到 {req.target_stage_id}"
                                    if not req.note else ""),
        "decided_by": "workbench",
    })
    sess.save()
    ff = out.get("fullflow") or {}
    path = ff.get("session_path")
    if not path:
        raise HTTPException(500, f"rewind_fullflow 未返回会话路径：{out}")
    return build_state(FullflowSession.load(path))


@app.post("/api/decide")
def api_decide(req: DecideReq):
    decision = {
        "stage_id": req.stage_id,
        "action": req.action,
        "revision": req.revision,
        "note": req.note,
        "decided_by": "workbench",
    }
    out = resume_fullflow(req.session_path, decision)
    if "error" in out:
        raise HTTPException(400, out["error"])
    ff = out.get("fullflow") or {}
    path = ff.get("session_path")
    if not path:
        raise HTTPException(500, f"resume_fullflow 未返回会话路径：{out}")
    return build_state(FullflowSession.load(path))


@app.post("/api/decide_stream")
async def api_decide_stream(req: DecideReq):
    """提交人工决策（SSE 流式版）。语义与 /api/decide 一致，仅传输方式不同。

    revise 会触发下游块重算（可能再次联网检索 / 跑 R 合并计算），期间推送
    阶段提示 + 心跳，避免界面长时间无反馈。
    """
    decision = {
        "stage_id": req.stage_id,
        "action": req.action,
        "revision": req.revision,
        "note": req.note,
        "decided_by": "workbench",
    }

    def _call(on_line=None, on_a4_event=None):
        return resume_fullflow(req.session_path, decision, on_line=on_line,
                               on_a4_event=on_a4_event)

    extra = "（含修订，将重算下游阶段）" if req.revision else ""
    return await _stream_blocking(_call,
                            f"提交决策 · {req.stage_id} → {req.action}{extra}",
                            stage_hint="推进流程并重建状态中…")


@app.post("/api/a4_preview")
async def api_a4_preview(req: A4PreviewReq):
    """A4 下载/抽取实时预览（SSE）。逐篇研究 yield 进度事件，失败不中断。

    输入：session_path（best-effort 抽取 Block A 的 A2.studies / A3.screened），
    或 studies + screened 直接覆盖（前端优先传）。返回 text/event-stream。
    事件流：start → (downloading → extracting → extracted | failed | skip | deferred)
            → done（含完整结果）。下载失败/付费墙篇目标记 failed 并继续，不阻塞。
    """
    studies, screened = req.studies, req.screened
    if not studies and req.session_path and os.path.exists(req.session_path):
        sess = FullflowSession.load(req.session_path)
        studies, screened = _a4_inputs_from_session(sess)
    if not studies:
        async def _err():
            yield _sse({"event": "error",
                        "message": "无可用 studies：请先完成 A2/A3，或前端传入 studies/screened"})
        return StreamingResponse(_err(), media_type="text/event-stream")

    loop = asyncio.get_event_loop()
    q: queue.Queue = queue.Queue()

    def _worker():
        try:
            for ev in block_a.a4_stream(studies, screened or [],
                                        pdf_dir=req.pdf_dir,
                                        max_attempts=req.max_attempts,
                                        email=req.email,
                                        cached_only=req.cached_only):
                q.put(ev)
        except Exception as e:  # noqa: BLE001
            q.put({"event": "error", "message": f"{type(e).__name__}: {e}"})
        finally:
            q.put(None)  # 哨兵：流结束

    async def _gen():
        loop.run_in_executor(None, _worker)  # 后台线程跑阻塞式下载/抽取
        while True:
            ev = await loop.run_in_executor(None, q.get)
            if ev is None:
                break
            yield _sse(ev)
            # done 事件后把逐篇结果落盘，供工作台「逐篇文档展示」读取与编辑
            if ev.get("event") == "done" and req.session_path and os.path.exists(req.session_path):
                try:
                    block_a.a4_persist_result(req.session_path, ev["result"])
                except Exception:  # noqa: BLE001 落盘失败不影响预览
                    pass

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.get("/api/a4_pdf_cache")
def api_a4_pdf_cache(session_path: Optional[str] = None):
    """返回 A4 抽取将复用的本地 PDF 缓存清单（供界面提前告知用户「不重下」）。

    目录优先级：session_path 同级 pdfs → 否则默认 os.getcwd()/pdfs（与 a4_stream 一致）。
    仅返回确为真 PDF 的文件名，前端据此展示「已缓存 N 篇，将自动复用」。
    """
    pdf_dir = block_a.A4_PDF_CACHE_DIR
    files = []
    if os.path.isdir(pdf_dir):
        for fn in sorted(os.listdir(pdf_dir)):
            if fn.lower().endswith(".pdf") and block_a._is_pdf(os.path.join(pdf_dir, fn)):
                files.append(fn)
    return {"pdf_dir": pdf_dir, "count": len(files), "files": files}


@app.get("/api/export_screening")
def api_export_screening(session_path: str):
    """导出当前 A3 裁决表为 xlsx（ct-literature 模板 + 裁决/理由列），供用户下载编辑。"""
    if not os.path.exists(session_path):
        raise HTTPException(400, f"会话不存在：{session_path}")
    import tempfile
    out_dir = tempfile.mkdtemp(prefix="ma_export_")
    out_path = os.path.join(out_dir, "screening.xlsx")
    try:
        block_a.export_screening_xlsx(session_path, out_path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"导出失败：{type(e).__name__}: {e}")
    return FileResponse(out_path,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename="A3_裁决表.xlsx",
                        background=None)


@app.post("/api/upload_screening")
def api_upload_screening(session_path: str = Form(...), file: UploadFile = File(...)):
    """上传用户改好的裁决表 xlsx → 解析 → 回写当前会话 A3 decisions。

    匹配：按 DOI/标题任一命中；只覆盖「裁决/理由」两列，其余元数据保留。
    上传后**不自动前进**，回 A3 软停让用户复核再点「修订后放行」。
    返回 {session_path, state, stats}。
    """
    if not os.path.exists(session_path):
        raise HTTPException(400, f"会话不存在：{session_path}")
    import tempfile
    tmp = tempfile.mkdtemp(prefix="ma_upload_")
    up_path = os.path.join(tmp, "upload.xlsx")
    with open(up_path, "wb") as f:
        f.write(file.file.read())
    try:
        sess = FullflowSession.load(session_path)
        # await（含 A3 decisions）持久化在 last_view.fullflow.await（与 build_state 同源）
        await_blk = ((sess.data.get("last_view") or {}).get("fullflow") or {}).get("await") or {}
        decisions = (await_blk.get("nha") or {}).get("decisions") or []
        screened, stats = block_a.parse_screening_xlsx(up_path, decisions)
        block_a.apply_screening_upload(session_path, screened)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"上传解析失败：{type(e).__name__}: {e}")
    return {
        "session_path": session_path,
        "stats": stats,
        "state": build_state(FullflowSession.load(session_path)),
    }


@app.post("/api/upload_pdf")
def api_upload_pdf(session_path: str = Form(...), doc_index: int = Form(...),
                   file: UploadFile = File(...)):
    """上传某篇待补 PDF → 抽取 2×2 表 → 回写该篇到会话的 A4 逐篇结果。

    用于 A4 中「付费墙/下载失败/无入口」需人工上传的篇目：上传后即时抽取并
    更新该篇状态（needs_upload → extracted），返回更新后的逐篇条目。
    """
    import tempfile  # 局部导入（与 export/upload_screening 一致）
    if not os.path.exists(session_path):
        raise HTTPException(400, f"会话不存在：{session_path}")
    try:
        import pdf_extractor  # 懒加载（依赖 fitz，已在 venv 安装）
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"PDF 抽取库不可用：{type(e).__name__}: {e}")
    tmp = tempfile.mkdtemp(prefix="ma_updf_")
    up_path = os.path.join(tmp, "up.pdf")
    with open(up_path, "wb") as f:
        f.write(file.file.read())
    try:
        sess = FullflowSession.load(session_path)
        res = block_a.a4_get_result(session_path) or {}
        pds = res.get("per_doc") or []
        if not (0 <= doc_index < len(pds)):
            raise HTTPException(400, f"doc_index 越界：{doc_index} / {len(pds)}")
        doc = pds[doc_index]
        ext = pdf_extractor.extract(up_path)
        rows = pdf_extractor.to_a4_rows(ext)
        tworows = [r for r in rows if all(r.get(k) is not None for k in ("ai", "bi", "ci", "di"))]
        # 落盘该 PDF 到会话 pdf 目录（稳定命名 block_a._pdf_stem），便于
        # 「查看原文页」复用 + 后续 a4_stream 重跑直接命中缓存不重下
        study = next((s for s in _session_studies(sess)
                      if str(s.get("doi") or "").strip().lower() == str(doc.get("doi") or "").strip().lower()
                      and doc.get("doi")), None) or {"doi": doc.get("doi"), "title": doc.get("title")}
        pdf_dir = block_a.A4_PDF_CACHE_DIR
        os.makedirs(pdf_dir, exist_ok=True)
        saved_pdf = os.path.join(pdf_dir, block_a._pdf_stem(study) + ".pdf")
        import shutil
        shutil.copyfile(up_path, saved_pdf)
        doc.update({"status": "extracted", "pdf": saved_pdf, "rows": rows,
                    "n_rows": len(rows), "n_tworows": len(tworows),
                    "reason": None})
        pds[doc_index] = doc
        res["per_doc"] = pds
        block_a.a4_persist_result(session_path, res)
        return {"index": doc_index, "status": "extracted", "n_rows": len(rows),
                "n_tworows": len(tworows), "rows": rows,
                "message": f"第 {doc_index + 1} 篇已抽取 {len(tworows)} 条 2×2 行"}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"上传抽取失败：{type(e).__name__}: {e}")


@app.post("/api/upload_pdf_auto")
def api_upload_pdf_auto(session_path: str = Form(...), file: UploadFile = File(...)):
    """上传用户已有 PDF → 自动匹配到会话中的某篇待补文献 → 抽取回写。

    匹配策略（与 A3 上传同源键口径）：
      ① 从 PDF 前 3 页文本抽 DOI（正则）→ 与 per_doc 的 DOI 归一化精确匹配；
      ② 失败则按标题 difflib 相似度（≥0.62 取最高分）匹配；
      ③ 均失败 → 返回 candidates（全部 needs_upload 篇目）供前端手动指派
         （前端随后调 /api/upload_pdf 带 doc_index 补一刀，避免二次传大文件，
         故此处先把文件落盘为待指派暂存并返回 staged_path）。
    匹配成功时 PDF 落盘为该篇稳定命名（block_a._pdf_stem），后续 a4_stream
    重跑会直接命中缓存、不再重复下载。
    """
    import re as _re
    import difflib
    import tempfile
    import shutil
    if not os.path.exists(session_path):
        raise HTTPException(400, f"会话不存在：{session_path}")
    try:
        import pdf_extractor
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"PDF 抽取库不可用：{type(e).__name__}: {e}")

    tmp = tempfile.mkdtemp(prefix="ma_updfa_")
    up_path = os.path.join(tmp, "up.pdf")
    with open(up_path, "wb") as f:
        f.write(file.file.read())

    def _pdf_text(path, max_pages=3):
        try:
            with fitz.open(path) as d:  # noqa: F841 — pdf_extractor 已验证 fitz 可用
                pass
        except Exception:
            pass
        try:
            import fitz
            with fitz.open(path) as doc:
                return "\n".join(doc[i].get_text() for i in range(min(max_pages, doc.page_count)))
        except Exception:
            return ""

    def _norm_title(t):
        return " ".join(_re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", str(t or "").lower()).split())

    try:
        sess = FullflowSession.load(session_path)
        res = block_a.a4_get_result(session_path) or {}
        pds = res.get("per_doc") or []
        if not pds:
            raise HTTPException(400, "会话尚无 A4 逐篇结果（请先跑一次 A4）")

        text = _pdf_text(up_path)
        m = _re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text or "")
        up_doi = m.group(0).rstrip(".,;)").lower() if m else None

        need = [(i, d) for i, d in enumerate(pds)
                if (d or {}).get("status") in ("needs_upload", "failed", "deferred", None)]

        hit = None
        if up_doi:
            for i, d in need:
                if str(d.get("doi") or "").strip().lower() == up_doi:
                    hit = (i, d, "doi")
                    break
        if hit is None:
            # 标题相似度：取 PDF 首页前几行拼成参考串，与各篇标题比对
            first_lines = [ln for ln in (text or "").splitlines() if ln.strip()][:8]
            ref = _norm_title(" ".join(first_lines))
            if ref:
                best, best_score = None, 0.0
                for i, d in need:
                    t = _norm_title(d.get("title"))
                    if not t:
                        continue
                    score = max(difflib.SequenceMatcher(None, ref, t).ratio(),
                                difflib.SequenceMatcher(None, ref[:200], t[:200]).ratio())
                    if score > best_score:
                        best, best_score = (i, d), score
                if best and best_score >= 0.62:
                    hit = (best[0], best[1], f"title:{best_score:.2f}")
                elif best:
                    return {"matched": False,
                            "staged_path": up_path,
                            "best_guess": {"index": best[0], "title": best[1].get("title"),
                                           "score": round(best_score, 2)},
                            "candidates": [{"index": i, "title": d.get("title"),
                                            "doi": d.get("doi")} for i, d in need],
                            "message": f"未能确定匹配（最接近：第 {best[0] + 1} 篇，相似度 {best_score:.2f}）。"
                                       "请从候选列表手动指派。"}

        if hit is None:
            return {"matched": False, "staged_path": up_path,
                    "candidates": [{"index": i, "title": d.get("title"), "doi": d.get("doi")}
                                   for i, d in need],
                    "message": "PDF 中未识别出 DOI 且标题无法自动匹配，请从候选列表手动指派。"}

        i, d, how = hit
        # 落盘为该篇稳定命名 → 后续 a4_stream 重跑直接命中缓存
        studies = _session_studies(sess)
        study = next((s for s in studies
                      if str(s.get("doi") or "").strip().lower() == str(d.get("doi") or "").strip().lower()
                      and d.get("doi")), None) or {"doi": d.get("doi"), "title": d.get("title")}
        pdf_dir = block_a.A4_PDF_CACHE_DIR
        os.makedirs(pdf_dir, exist_ok=True)
        saved_pdf = os.path.join(pdf_dir, block_a._pdf_stem(study) + ".pdf")
        shutil.copyfile(up_path, saved_pdf)

        ext = pdf_extractor.extract(saved_pdf)
        rows = pdf_extractor.to_a4_rows(ext)
        tworows = [r for r in rows if all(r.get(k) is not None for k in ("ai", "bi", "ci", "di"))]
        d.update({"status": "extracted", "pdf": saved_pdf, "rows": rows,
                  "n_rows": len(rows), "n_tworows": len(tworows), "reason": None})
        pds[i] = d
        res["per_doc"] = pds
        block_a.a4_persist_result(session_path, res)
        return {"matched": True, "index": i, "match_via": how, "status": "extracted",
                "n_rows": len(rows), "n_tworows": len(tworows), "rows": rows,
                "message": f"已匹配到第 {i + 1} 篇（{d.get('title')}），抽取 {len(tworows)} 条 2×2 行"}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"上传匹配失败：{type(e).__name__}: {e}")


@app.get("/api/pdf_page")
def api_pdf_page(session_path: str, doc_index: int = 0, page: int = 1, dpi: int = 110):
    """渲染某篇 PDF 的指定页为 PNG，供工作台「查看原文页」内联展示（fitz）。

    仅允许渲染来自该会话 A4 结果 per_doc 中记录的本地 PDF，杜绝任意路径读取。
    """
    if not os.path.exists(session_path):
        raise HTTPException(400, f"会话不存在：{session_path}")
    try:
        import fitz
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"PDF 渲染库不可用：{type(e).__name__}: {e}")
    try:
        res = block_a.a4_get_result(session_path) or {}
        pds = res.get("per_doc") or []
        if not (0 <= doc_index < len(pds)):
            raise HTTPException(400, f"doc_index 越界：{doc_index} / {len(pds)}")
        pdf_path = (pds[doc_index] or {}).get("pdf")
        if not pdf_path or not os.path.isabs(pdf_path) or not os.path.exists(pdf_path):
            raise HTTPException(404, "该篇无本地 PDF（可能尚未下载/上传）")
        with fitz.open(pdf_path) as doc:
            if not (1 <= page <= doc.page_count):
                raise HTTPException(400, f"页码越界：{page} / {doc.page_count}")
            pix = doc[page - 1].get_pixmap(dpi=max(40, min(dpi, 200)))
        return Response(content=pix.tobytes("png"), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"渲染失败：{type(e).__name__}: {e}")


@app.post("/api/a4_save_doc_edits")
def api_a4_save_doc_edits(session_path: str = Form(...), doc_index: int = Form(...),
                           rows_json: str = Form(...)):
    """保存用户在「逐篇文档」面板对某篇抽取行的就地修订（2×2 / 效应量）。

    仅更新 a4_result.per_doc[doc_index].rows 并重算 n_tworows，不涉及红线 decide。
    """
    if not os.path.exists(session_path):
        raise HTTPException(400, f"会话不存在：{session_path}")
    try:
        new_rows = json.loads(rows_json)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"rows_json 解析失败：{e}")
    try:
        res = block_a.a4_get_result(session_path) or {}
        pds = res.get("per_doc") or []
        if not (0 <= doc_index < len(pds)):
            raise HTTPException(400, f"doc_index 越界：{doc_index} / {len(pds)}")
        doc = dict(pds[doc_index])
        doc["rows"] = new_rows
        doc["n_rows"] = len(new_rows)
        doc["n_tworows"] = sum(1 for r in new_rows
                               if all(r.get(k) is not None for k in ("ai", "bi", "ci", "di")))
        pds[doc_index] = doc
        res["per_doc"] = pds
        block_a.a4_persist_result(session_path, res)
        return {"ok": True, "index": doc_index, "n_rows": doc["n_rows"],
                "n_tworows": doc["n_tworows"]}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"保存失败：{type(e).__name__}: {e}")


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(APP_DIR, "workbench.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
