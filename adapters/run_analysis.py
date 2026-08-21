"""
adapters/run_analysis.py — 元分析统一调用入口（coze 优先 + 本地兜底）

默认行为（prefer="coze"）：
  1. 调用 coze 工作流（adapters/coze_client.run_meta）；
  2. 若 coze 不可用（网络错误 / HTTP 非 2xx / 空响应），自动回退到本地 R 引擎
     （adapters/local_engine.run_meta），结果 _source 标记为 "local_fallback"；
  3. 若两者皆失败，抛出 RuntimeError 同时报告两路错误。

显式本地（prefer="local"）：
  仅调用本地 R 引擎（用户明确要求本地分析，或离线 / coze 不可达环境）。

返回结果统一带 `_source` 字段：
  "coze"          — 由 coze 工作流产出
  "local_fallback"— coze 失败、已本地兜底
  "local"         — 用户明确要求、仅本地产出

CLI：
  python adapters/run_analysis.py <request.json> [--prefer coze|local]
  request.json = {"task":..., "data":..., "params":..., "figure":...}
"""

import os
import sys
import json
import time
import hashlib
import socket

# 让 coze_client / local_engine / rendering 可被直接 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coze_client import run_meta as _coze_run
from coze_client import AuthRequiredError
from local_engine import run_meta as _local_run
from rendering import svg_to_png

# 渲染计时阈值（秒）：**本地渲染阶段**（拿到 SVG → 处理 → 界面渲染完成）超过该值，
# 提示用户可切换图片文件模式（PNG 不内联 SVG，界面渲染通常更快）。
# 注意：不是 coze 计算时间（那是 coze_elapsed_seconds，仅诊断参考）。
RENDER_SVG_THRESHOLD = 30.0
# SVG 体量辅助阈值（KB）：单图超过该值即使本地处理快，界面渲染（浏览器解析 + 滚动）
# 也可能明显变慢——一并提示。默认按森林图典型 18KB 的 ~10 倍余量。
RENDER_SVG_KB_THRESHOLD = 200.0


def run_analysis(task: str, data: dict, params: dict | None = None,
                 figure: dict | None = None, prefer: str = "coze") -> dict:
    """统一分析入口。prefer='coze'（默认）优先 coze、失败兜底本地；prefer='local' 仅本地。"""
    if prefer == "local":
        res = _local_run(task, data, params, figure)
        res["_source"] = "local"
        return res

    # 默认：coze 优先
    # §8.6 query_origin：客户端计算主机名 SHA-256 哈希（"sha256:" + 64hex = 71 字符），
    # 随请求发送，供 coze 端归因/限流；coze 端不得兜底生成（客户端唯一真相源）。
    query_origin = "sha256:" + hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()
    try:
        res = _coze_run(task, data, params, figure, query_origin=query_origin)
        res["_source"] = "coze"
        return res
    except AuthRequiredError as e_auth:
        # ct-base §5 授权门控：未授权出站不阻断 —— 优先本地兜底；本地不可用时
        # 返回明确提示（授权问题可解决，非系统故障，不抛 RuntimeError）
        try:
            res = _local_run(task, data, params, figure)
            res["_source"] = "local_fallback"
            note = res.get("notes") or ""
            res["notes"] = (
                f"{note}  [未授权出站（ct-base §5）：本次未使用云端分析，已用本地引擎。"
                f"如需云端分析请确认授权：{e_auth}]".strip()
            )
            res["_auth_required"] = True
            return res
        except Exception as e_local:
            return {
                "status": "error",
                "notes": (
                    f"未授权出站（ct-base §5 授权门控），本次未使用云端分析；"
                    f"本地引擎亦不可用（{type(e_local).__name__}: {e_local}）。"
                    f"如同意将分析数据发送至云端，请确认授权后重试（端点 {_coze_run.__module__}）。"
                ),
                "_source": "auth_blocked",
                "_auth_required": True,
                "figures": [],
                "warnings": [],
            }
    except Exception as e_coze:
        try:
            res = _local_run(task, data, params, figure)
            res["_source"] = "local_fallback"
            note = res.get("notes") or ""
            res["notes"] = (
                f"{note}  [coze 调用失败，已本地兜底：{type(e_coze).__name__}]".strip()
            )
            res["_coze_error"] = str(e_coze)[:500]
            return res
        except Exception as e_local:
            raise RuntimeError(
                f"coze 与本地 R 引擎均失败。\ncoze: {e_coze}\n本地: {e_local}"
            )


def render_figures(out: dict, mode: str = "svg_inline", out_dir: str = "output",
                   titles: list | None = None) -> dict:
    """按出图模式处理 figures，返回增强后的结果 dict。

    mode:
      svg_inline（默认）— figures[].svg 原样保留，由调用方（agent）内联渲染进对话流
      png_file          — 本地 cairosvg 将每个 SVG 转 PNG 文件存 out_dir/
                          figures 替换为 {type, format:"png", path}（更轻量、不出上下文）

    渲染计时（★ 用户要求：本地拿到 SVG 后到界面渲染完成的总时间）：
      - `render_elapsed_seconds`：本函数内 SVG 处理耗时（extract/strip/bbox/wrap/
        widget 生成 或 PNG 转换）——本地可精确测量；界面浏览器渲染部分无法在 agent
        侧计时，用 SVG 体量 `render_svg_kb` 作代理（体量越大界面渲染越慢）。
      - 若 render_elapsed_seconds > RENDER_SVG_THRESHOLD 或单图体量 >
        RENDER_SVG_KB_THRESHOLD，生成 `render_hint` 提示用户可切换 png_file 模式。
      - coze 计算/网络耗时见 `coze_elapsed_seconds`（仅诊断，**不参与**本提示）。

    Returns: 增强后的 out（新增 render_mode / render_elapsed_seconds / render_svg_kb /
             render_hint 字段）。
    """
    out = dict(out)
    _t0 = time.time()
    figs = out.get("figures") or []
    svg_kb = sum(len((f.get("svg") or "")) for f in figs) / 1024.0

    if mode == "png_file" and figs:
        os.makedirs(out_dir, exist_ok=True)
        out["figures"] = []
        for i, f in enumerate(figs):
            svg = f.get("svg") or ""
            if not svg:
                continue
            name = f.get("type") or f"fig{i + 1}"
            path = os.path.join(out_dir, f"{name}_{int(time.time())}.png")
            svg_to_png(svg, path)  # 同一处理链：strip clip → fix xml → bbox → viewBox → 光栅化
            out["figures"].append({"type": name, "format": "png", "path": path})

    out["render_elapsed_seconds"] = round(time.time() - _t0, 3)
    out["render_svg_kb"] = round(svg_kb, 1)
    out["render_mode"] = mode
    out["render_hint"] = _render_hint(out) if mode == "svg_inline" else None
    return out


def _render_hint(out: dict) -> str | None:
    """根据渲染耗时与 SVG 体量生成提示（仅 svg_inline 模式）。

    render_elapsed_seconds = 本地 SVG 处理 + widget 生成耗时（可精确测量）；
    界面浏览器渲染无法在 agent 侧计时 → 用 SVG 体量（render_svg_kb）作代理：
    体量越大，界面解析/滚动越慢。coze 计算/网络耗时（coze_elapsed_seconds）
    不参与本提示。
    """
    reasons = []
    elapsed = out.get("render_elapsed_seconds")
    if elapsed is not None and elapsed > RENDER_SVG_THRESHOLD:
        reasons.append(f"本地渲染处理耗时 {elapsed:.0f}s（> {RENDER_SVG_THRESHOLD:.0f}s 阈值）")
    svg_kb = out.get("render_svg_kb") or 0
    if svg_kb > RENDER_SVG_KB_THRESHOLD:
        reasons.append(f"SVG 体量 {svg_kb:.0f}KB（> {RENDER_SVG_KB_THRESHOLD:.0f}KB，界面渲染/滚动可能明显变慢）")
    if not reasons:
        return None
    return (
        "；".join(reasons) + "。可切换图片文件模式（figure_mode='png_file'）："
        "本地直接转 PNG 文件、不内联 SVG，界面渲染通常更快。"
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="元分析统一调用（coze 优先 + 本地兜底）")
    ap.add_argument("request", help="JSON 请求文件路径")
    ap.add_argument("--prefer", choices=["coze", "local"], default="coze",
                    help="coze=默认优先并兜底本地；local=仅本地")
    a = ap.parse_args()

    req = json.load(open(a.request, encoding="utf-8"))
    out = run_analysis(
        req.get("task"), req.get("data"), req.get("params"),
        req.get("figure"), prefer=a.prefer,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
