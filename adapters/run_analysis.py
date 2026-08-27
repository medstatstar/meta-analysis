"""
adapters/run_analysis.py — 元分析统一调用入口（coze 唯一路径）

默认行为（coze-only）：
  调用 coze 工作流（adapters/coze_client.run_meta）完成 R 计算。
  - 认证未授权（AuthRequiredError）→ 返回明确提示，不绕过 ct-base §5 授权门控、不回退本地。
  - coze 调用失败 → 返回结构化错误（含 coze 错误原文），不再本地兜底。

本地 R 引擎（原 adapters/local_engine.py）自 2026-08-26 起已从主路径移除，
移至 adapters/_dev/local_engine.py（git/clawhub 忽略、不随发布包分发），
仅作为开发者本地调试 / 复现保留，run_analysis 不再调用它。

返回结果统一带 `_source` 字段：
  "coze"         — 由 coze 工作流产出
  "auth_blocked" — 未授权出站，未使用云端分析
  "coze_error"   — coze 调用失败

CLI：
  python adapters/run_analysis.py <request.json>
  request.json = {"task":..., "data":..., "params":..., "figure":...}
"""

import os
import sys
import json
import time
import hashlib
import socket

# 让 coze_client / rendering 可被直接 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coze_client import run_meta as _coze_run
from coze_client import AuthRequiredError
from rendering import svg_to_png, render_html_report

# 渲染计时阈值（秒）：**本地渲染阶段**（拿到 SVG → 处理 → 界面渲染完成）超过该值，
# 提示用户可切换图片文件模式（PNG 不内联 SVG，界面渲染通常更快）。
# 注意：不是 coze 计算时间（那是 coze_elapsed_seconds，仅诊断参考）。
RENDER_SVG_THRESHOLD = 30.0
# SVG 体量辅助阈值（KB）：单图超过该值即使本地处理快，界面渲染（浏览器解析 + 滚动）
# 也可能明显变慢——一并提示。默认按森林图典型 18KB 的 ~10 倍余量。
RENDER_SVG_KB_THRESHOLD = 200.0


def run_analysis(task: str, data: dict, params: dict | None = None,
                 figure: dict | None = None, out_dir: str = ".") -> dict:
    """统一分析入口（coze-only）。coze 失败 / 未授权时返回结构化错误，不回退本地。

    out_dir: HTML 报告输出目录（默认当前工作目录 `.`）；由 run_meta.py 解析后传入，
             确保报告落在用户工作区，而非技能自身目录。
    """
    # §8.6 query_origin：客户端计算主机名 SHA-256 哈希（"sha256:" + 64hex = 71 字符），
    # 随请求发送，供 coze 端归因/限流；coze 端不得兜底生成（客户端唯一真相源）。
    query_origin = "sha256:" + hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()
    try:
        res = _coze_run(task, data, params, figure, query_origin=query_origin)
        res["_source"] = "coze"
        # 2026-08-26 展示改进：本地聚合 HTML 报告（内联 SVG + 统计表 + 折叠 R 代码），
        # 作为对话内联之外的"完整版"交付物；coze 返回体不变，固化在 agent 侧完成，
        # 不受 S3 链接过期与 4000 截断影响。生成失败不影响主结果。
        try:
            hp = render_html_report(res, out_dir=out_dir)
            if hp:
                res["html_report"] = hp
        except Exception:
            pass
        return res
    except AuthRequiredError as e_auth:
        # ct-base §5 授权门控：未授权出站不阻断、也不绕过 —— 返回明确提示，由用户确认授权后重试。
        return {
            "status": "error",
            "notes": (
                f"未授权出站（ct-base §5 授权门控），本次未使用云端分析。"
                f"如同意将分析数据发送至云端，请确认授权后重试"
                f"（端点 {_coze_run.__module__}）。"
            ),
            "_source": "auth_blocked",
            "_auth_required": True,
            "figures": [],
            "warnings": [],
        }
    except Exception as e_coze:
        return {
            "status": "error",
            "notes": f"coze 调用失败：{type(e_coze).__name__}: {e_coze}",
            "_source": "coze_error",
            "_coze_error": str(e_coze)[:500],
            "figures": [],
            "warnings": [],
        }


def render_figures(out: dict, mode: str = "svg_inline", out_dir: str = ".",
                   titles: list | None = None) -> dict:
    """按出图模式处理 figures，返回增强后的结果 dict。

    mode:
      svg_inline（默认）— figures[].svg 原样保留，由调用方（agent）嵌入 HTML 报告展示（不再内联 widget）
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

    ap = argparse.ArgumentParser(description="元分析统一调用（coze-only）")
    ap.add_argument("request", help="JSON 请求文件路径")
    ap.add_argument("--out-dir", default=".", help="HTML 报告输出目录（默认当前工作目录）")
    a = ap.parse_args()

    req = json.load(open(a.request, encoding="utf-8"))
    out = run_analysis(
        req.get("task"), req.get("data"), req.get("params"),
        req.get("figure"), out_dir=a.out_dir,
    )
    # 2026-08-26 设计迭代：完整结果（含内联 SVG / R）落盘，供渲染模板离线复用，
    # 避免每次调整 HTML 样式都重复触发真实 coze 调用。
    import os as _os
    _ld = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "output")
    _os.makedirs(_ld, exist_ok=True)
    with open(_os.path.join(_ld, "last_run.json"), "w", encoding="utf-8") as _fh:
        json.dump(out, _fh, ensure_ascii=False, indent=2)
    # 2026-08-27 硬控制：成功时单独打印报告绝对路径（单行、不被 4000 截断吞掉），
    # 让 agent 直接 present_files，无需再跑 Bash 用 ls/grep 找报告（消灭 §0.2 禁项的物理动机）。
    _hp = out.get("html_report")
    if _hp:
        print("META_HTML_REPORT=" + os.path.abspath(_hp))
    elif out.get("status") == "error":
        print("META_STATUS=error | " + str(out.get("notes") or "")[:200])
    print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
