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

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import HTMLResponse, StreamingResponse  # noqa: E402
from typing import Optional  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

APP_DIR = _HERE
RUNS_DIR = os.path.join(APP_DIR, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

app = FastAPI(title="meta-analysis workbench", version="0.1.0")


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


class A4PreviewReq(BaseModel):
    session_path: str = ""          # 主：从会话抽取 A2.studies / A3.screened
    studies: Optional[list] = None   # 覆盖：前端直接传入（优先于 session_path 抽取）
    screened: Optional[list] = None
    pdf_dir: Optional[str] = None
    max_attempts: int = 12
    email: Optional[str] = None

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


@app.get("/api/session")
def api_session(path: str):
    if not os.path.exists(path):
        raise HTTPException(404, f"会话不存在：{path}")
    return build_state(FullflowSession.load(path))

@app.post("/api/topic_help")
def api_topic_help(req: TopicHelpReq):
    # 命中题轨的自包含上游闸：literature_probe 直连 Europe PMC，
    # 返回真实命中数（Cochrane + PubMed SR/MA），用于选题可行性速览。
    try:
        res = literature_probe.dedup_probe(req.topic, year_from=req.year_from, max_results=8)
    except Exception as e:  # 网络/解析失败 → 优雅降级，不整页冒
        return {"topic": req.topic, "ok": False, "error": str(e),
                "layers": {}, "summary": "", "any_error": True}
    res["ok"] = True
    return res


@app.post("/api/rewind")
def api_rewind(req: RewindReq):
    out = rewind_fullflow(req.session_path, req.target_stage_id)
    if "error" in out:
        raise HTTPException(400, out["error"])
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
                                        email=req.email):
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

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(APP_DIR, "workbench.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
