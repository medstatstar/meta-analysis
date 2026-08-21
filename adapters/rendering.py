# -*- coding: utf-8 -*-
"""adapters/rendering.py — SVG 内联渲染工具（meta-analysis 技能，呈现层）。

将 coze 返回的 figures[].svg 转为可直接内嵌到对话流的标准 HTML fragment。

核心问题（实测 2026-08-19）：
  svglite 输出固定 viewBox（如 "0 0 504 360"），但内容可能**超出该区域**
  —— meta 包 forest() 把 Study/Events/OR/95%CI/Weight 列画在图形区外
  （x 可达 -140 / +644，宽度 785px）。按原 viewBox 渲染会被浏览器裁剪两侧文字。
  解决：content_bbox() 扫描内容元素极值，动态扩展 viewBox + 宽度。

规则（用户偏好，2026-08-19）：
  图固定原尺寸不缩放；容器装不下即出横向滚动条（overflow-x:auto）。

用法：
  from rendering import build_figure_widget
  html = build_figure_widget(figures, ["森林图 · OR", "漏斗图 · Egger"])
"""

from __future__ import annotations

import os
import re
import sys

__all__ = ["extract_svg", "content_bbox", "build_figure_widget", "svg_to_png"]

_Q = r"['\"]"  # svglite 用单引号属性，兼容双引号


def _num(v: str) -> float:
    """'39.34px' / '504.00' → 39.34 / 504.0"""
    return float(v.replace("px", "").strip())


def extract_svg(svg_str: str) -> tuple[str, str]:
    """从完整 SVG 字符串提取 (inner, viewbox)。兼容单/双引号属性。

    inner = <svg> 内部内容（供嵌入 <svg viewBox=...>），viewbox 为原值。
    """
    m = re.search(
        r"<svg[^>]*viewBox=['\"]([^'\"]+)['\"][^>]*>(.*)</svg>",
        svg_str,
        re.S,
    )
    if m:
        return (m.group(2), m.group(1))
    m = re.search(r"<svg[^>]*>(.*)</svg>", svg_str, re.S)
    if m:
        return (m.group(1), "0 0 504 360")
    return (svg_str, "0 0 504 360")


def content_bbox(
    svg_inner: str, pad: float = 8.0, pad_y: float = 24.0
) -> tuple[float, float, float, float]:
    """扫描 SVG 内容元素，返回 (min_x, min_y, max_x, max_y) 含 padding。

    pad 用于 x 方向（紧凑，避免图过宽）；pad_y 用于 y 方向（留白更多，
    森林图等绘图区上下贴近内容时保持呼吸空间，见用户偏好 2026-08-19）。
    覆盖元素：text（含 textLength/text-anchor 计算文本宽度；transform 文本解析
    translate 锚点双向扩展）、rect（跳过 width=100% 白底）、line、circle、
    polyline/polygon points。无内容时回退原画布 (0, 0, 504, 360)。
    """
    xs: list[float] = []
    ys: list[float] = []

    # ---- text ----
    for m in re.finditer(r"<text\b([^>]*)>(.*?)</text>", svg_inner, re.S):
        attrs = m.group(1)
        tl = re.search(rf"textLength={_Q}([^'\"]+)", attrs)
        w = _num(tl.group(1)) if tl else 0.0
        tm = re.search(r"transform=['\"]([^'\"]+)['\"]", attrs)
        if tm:
            # transform 文本（如漏斗图 y 轴旋转标签）：取 translate 锚点，沿 x/y
            # 双向扩展 textLength（旋转方向不定，保守覆盖 → 保证不裁剪）
            t = re.search(
                r"translate\(\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*\)", tm.group(1)
            )
            if t:
                tx, ty = _num(t.group(1)), _num(t.group(2))
                xs += [tx - w, tx + w]
                ys += [ty - w, ty + w]
                continue
            continue  # 无 translate 的 transform（如纯 rotate）无法定位，跳过
        xm = re.search(rf"\bx={_Q}([^'\"]+)", attrs)
        ym = re.search(rf"\by={_Q}([^'\"]+)", attrs)
        if not xm or not ym:
            continue
        x, y = _num(xm.group(1)), _num(ym.group(1))
        an = re.search(rf"text-anchor={_Q}([^'\"]+)", attrs)
        anchor = an.group(1) if an else "start"
        if anchor == "start":
            x0, x1 = x, x + w
        elif anchor == "middle":
            x0, x1 = x - w / 2, x + w / 2
        else:  # end
            x0, x1 = x - w, x
        xs += [x0, x1]
        ys += [y, y]

    # ---- rect ----
    for m in re.finditer(r"<rect\b([^>]*)/?>", svg_inner):
        a = dict(re.findall(r"([a-zA-Z:_-]+)=['\"]([^'\"]*)['\"]", m.group(1)))
        if all(k in a for k in ("x", "y", "width", "height")) and a["width"] != "100%":
            x, y = _num(a["x"]), _num(a["y"])
            w, h = _num(a["width"]), _num(a["height"])
            xs += [x, x + w]
            ys += [y, y + h]

    # ---- line ----
    for m in re.finditer(r"<line\b([^>]*)/?>", svg_inner):
        a = dict(re.findall(r"([a-zA-Z:_-]+)=['\"]([^'\"]*)['\"]", m.group(1)))
        if all(k in a for k in ("x1", "y1", "x2", "y2")):
            xs += [_num(a["x1"]), _num(a["x2"])]
            ys += [_num(a["y1"]), _num(a["y2"])]

    # ---- circle ----
    for m in re.finditer(r"<circle\b([^>]*)/?>", svg_inner):
        a = dict(re.findall(r"([a-zA-Z:_-]+)=['\"]([^'\"]*)['\"]", m.group(1)))
        if all(k in a for k in ("cx", "cy", "r")):
            r = _num(a["r"])
            cx, cy = _num(a["cx"]), _num(a["cy"])
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]

    # ---- polyline / polygon points ----
    for tag in ("polyline", "polygon"):
        for m in re.finditer(rf"<{tag}\b([^>]*)/?>", svg_inner):
            a = dict(re.findall(r"([a-zA-Z:_-]+)=['\"]([^'\"]*)['\"]", m.group(1)))
            if "points" in a:
                pts = [_num(v) for v in a["points"].replace(",", " ").split()]
                xs += pts[0::2]
                ys += pts[1::2]

    if not xs or not ys:
        return (0.0, 0.0, 504.0, 360.0)
    return (min(xs) - pad, min(ys) - pad_y, max(xs) + pad, max(ys) + pad_y)


def _strip_clip(svg_inner: str) -> str:
    """移除 svglite 的 clipPath 定义与 clip-path 引用（100% 显示的关键）。

    svglite 用固定 0..504 的 clipPath 裁剪绘图区，但 meta 包森林图的左右文字列
    画在 0 外 / 504 外（实测 x∈[-140,644]），被内部 clip 裁掉——即使外层 viewBox
    已扩展也无效。移除后由外层动态 viewBox（content_bbox）保证完整显示。
    注意：必须在 content_bbox 之前调用（clipPath 里的 rect 0..504 会污染 bbox）。
    """
    s = re.sub(r"<clipPath\b.*?</clipPath>", "", svg_inner, flags=re.S)
    s = re.sub(r"\s*clip-path='url\(#[^)]+\)'", "", s)
    return s


def _fix_xml(s: str) -> str:
    """补齐缺失的闭合标签（svglite 2.2.2 偶发缺一个 </g>）。

    浏览器按 HTML 解析规则宽容渲染没问题，但 cairosvg 用严格 XML 解析会报
    "mismatched tag"。用标签栈扫描，把未闭合的开标签按逆序补齐闭合标签。
    仅 SVG→PNG 路径使用；内联渲染（浏览器）不需要。
    """
    stack: list[str] = []
    out: list[str] = []
    i, n = 0, len(s)
    while i < n:
        if s[i] != "<":
            out.append(s[i]); i += 1; continue
        if s.startswith("<!--", i):
            j = s.find("-->", i); j = n if j < 0 else j + 3
            out.append(s[i:j]); i = j; continue
        if s.startswith("<![CDATA[", i):
            j = s.find("]]>", i); j = n if j < 0 else j + 3
            out.append(s[i:j]); i = j; continue
        if s[i + 1] in ("!", "?"):
            j = s.find(">", i); j = n if j < 0 else j + 1
            out.append(s[i:j]); i = j; continue
        j = s.find(">", i)
        if j < 0:
            out.append(s[i:]); break
        body = s[i + 1:j].strip()
        out.append(s[i:j + 1]); i = j + 1
        if not body or body.startswith("/") or body.endswith("/"):
            if body.startswith("/") and stack:
                stack.pop()  # 闭合标签弹栈
            continue
        name = body.split()[0]
        stack.append(name)
    for name in reversed(stack):
        out.append(f"</{name}>")
    return "".join(out)


# CJK 文本检测（中文 + 全角标点；含日韩假名区更宽，此处聚焦中文场景）
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def _default_cjk_font() -> str:
    """按平台选默认中文字体（可被环境变量 RENDERING_CJK_FONT 覆盖）。

    背景（2026-08-20 实测）：cairosvg 按 font-family 严格匹配字体、无系统回退，
    遇中文（SVG 里 font-family 恒为 "DejaVu Sans"）直接不渲染 → 中文 study 标签
    空白。本函数按平台返回本机存在的中文字体族，替换进含中文的 <text>。
    """
    env = os.environ.get("RENDERING_CJK_FONT")
    if env:
        return env
    if sys.platform == "darwin":
        return "PingFang SC"
    if sys.platform.startswith("win"):
        return "Microsoft YaHei"  # 已验证（cairosvg 渲染中文 OK）
    return "Noto Sans CJK SC"  # Linux 常见 CJK 包


def _fix_cjk_fonts(svg_inner: str, cjk_font: str | None = None) -> str:
    """把**含中文**的 <text> 元素字体族替换为中文字体族（纯英文/数字不动）。

    效果（实测 2026-08-20）：
      - 中文 text：font-family → 中文字体族 → cairosvg 正常渲染（像素验证 OK）
      - 英文/数字 text：保持原 font-family（"DejaVu Sans"）→ 英文图像素零变化
    仅 SVG→PNG 本地渲染路径调用；浏览器内联有系统字体回退，不需要。
    """
    if cjk_font is None:
        cjk_font = _default_cjk_font()

    def repl(m: re.Match) -> str:
        open_tag, text = m.group(1), m.group(2)
        if _CJK_RE.search(text):
            open_tag = re.sub(
                r"font-family:\s*['\"][^'\"]*['\"]",
                f'font-family: "{cjk_font}"',
                open_tag,
            )
        return f"<text{open_tag}>{text}</text>"

    return re.sub(r"<text\b([^>]*)>(.*?)</text>", repl, svg_inner, flags=re.S)


def _wrap_points(line: str, limit: int = 1200) -> str:
    """拆分超长行（svglite polyline points 单行可达 7000+ 字符）"""
    if len(line) <= limit:
        return line

    def repl(m):
        val = m.group(2)
        chunks, cur = [], ""
        for part in val.split():
            if len(cur) + len(part) + 1 > 1000:
                chunks.append(cur)
                cur = part
            else:
                cur = (cur + " " + part) if cur else part
        if cur:
            chunks.append(cur)
        return m.group(1) + chunks[0] + "\n" + "\n".join(chunks[1:]) + m.group(3)

    return re.sub(r"(points=['\"])(.*?)(['\"])", repl, line, flags=re.S)


def build_figure_widget(
    figures: list, titles: list[str], pad: float = 8.0, pad_y: float = 24.0
) -> str:
    """figures: [{svg, type}, ...] → 完整内联 HTML fragment。

    宽度规则：
      1. content_bbox() 扫描内容实际边界 → 动态 viewBox（解决 svglite 内容超界裁剪）
      2. SVG 固定原尺寸（viewBox 宽）不缩放
      3. 外层 overflow-x:auto —— 容器装不下即出横向滚动条
    """
    blocks = []
    for fig, t in zip(figures, titles):
        inner, vb = extract_svg(fig.get("svg") or "")
        inner = _strip_clip(inner)          # ★ 先移除内部 clipPath（否则左右文字列被裁）
        min_x, min_y, max_x, max_y = content_bbox(inner, pad=pad, pad_y=pad_y)
        vb_fit = f"{min_x:g} {min_y:g} {max_x - min_x:g} {max_y - min_y:g}"
        w = max_x - min_x
        blocks.append(
            f'<div><div style="font-size:13px;font-weight:500;margin:0 0 6px;'
            f'color:var(--color-text-primary);">{t}</div>'
            f'<div style="overflow-x:auto;max-width:100%;background:#fff;'
            f'border:0.5px solid var(--color-border-tertiary);'
            f'border-radius:var(--border-radius-md);">'
            # margin:0 auto → 容器比图宽时水平居中；容器窄溢出时 auto 边距归零
            # 自动左对齐出滚动条（flex justify-center 会裁剪左侧不可达，不能用）
            f'<svg viewBox="{vb_fit}" style="width:{w:g}px;height:auto;display:block;'
            f'margin:0 auto;">'
            f"{_wrap_points(inner)}</svg></div></div>"
        )
    return (
        '<div style="display:flex;flex-direction:column;gap:16px;'
        'font-family:var(--font-sans);">' + "".join(blocks) + "</div>"
    )


def svg_to_png(svg_str: str, out_path: str, scale: float = 2.0,
               pad: float = 8.0, pad_y: float = 24.0) -> str:
    """SVG → PNG（本地 cairosvg 转换，coze 端零改动）。

    与内联渲染同一处理链：strip clip → content_bbox 扩展 viewBox（保证完整内容）
    → 重建完整 SVG → cairosvg 按 scale 光栅化 → 写 out_path。

    Returns: out_path（成功）; 转换失败抛 RuntimeError（含原因）。
    """
    try:
        import cairosvg
    except ImportError:
        raise RuntimeError("SVG→PNG 需 cairosvg：pip install cairosvg")

    inner, vb = extract_svg(svg_str)
    inner = _strip_clip(inner)
    inner = _fix_xml(inner)  # svglite 偶发缺 </g>，严格 XML 解析前补齐
    inner = _fix_cjk_fonts(inner)  # 2026-08-20: 含中文的 text 换中文字体族（英文不动）
    min_x, min_y, max_x, max_y = content_bbox(inner, pad=pad, pad_y=pad_y)
    vb_fit = f"{min_x:g} {min_y:g} {max_x - min_x:g} {max_y - min_y:g}"
    full = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_fit}" '
        f'width="{max_x - min_x}" height="{max_y - min_y}">'
        f"{_wrap_points(inner)}</svg>"
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cairosvg.svg2png(bytestring=full.encode("utf-8"), write_to=out_path, scale=scale)
    return out_path


if __name__ == "__main__":
    import sys

    # 自测：python rendering.py <case.json> [titles...]
    import json

    env = json.load(open(sys.argv[1], encoding="utf-8"))
    figs = env.get("figures") or env.get("result", {}).get("figures") or []
    titles = sys.argv[2:] or [f"图 {i+1}" for i in range(len(figs))]
    print(build_figure_widget(figs, titles))
