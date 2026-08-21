#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Office 文档（docx / pptx）→ md 转换器（stdlib-only，零第三方依赖）

本脚本是 ct- 系列**共享件**（单一真源位于 ct-base/scripts/office_to_md.py），
供各 ct- 技能经 `publish_inject.py` 注入或在本地 `sys.path` 导入复用。

用途（对应 ct-base/BASE.md §6.7 用户上传文件处理规范）：
用户以 .docx / .pptx 附件提供模板、方案、材料时，本地先把附件转成 md
（段落 + 表格结构保留），再拼入处理链路（如 original_question / 本地分析上下文）。

设计约束（§6.7 分层方案）：
- docx / pptx 同为 OOXML zip 格式（zipfile + xml.etree.ElementTree 即可解析），
  **一个解析器覆盖两种**，不为每种格式维护一套轮子；
- .pdf 无法 stdlib 可靠解析（二进制格式）→ 指引调用环境 pdf 技能 / 提示安装；
- .doc 老格式（OLE 二进制）→ 提示安装 word-reader / antiword。

用法：
    python office_to_md.py <file.docx|file.pptx>        # 输出 md 到 stdout
    python office_to_md.py <file.docx|file.pptx> --check # 仅校验，输出字符数
"""

import sys
import zipfile
import re
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


# ===== docx =====

def _w_para_text(p) -> str:
    """docx 段落文本：w:t 拼接，w:tab→制表符，w:br→换行。"""
    parts = []
    for node in p.iter():
        tag = node.tag
        if tag == W + "t":
            parts.append(node.text or "")
        elif tag == W + "tab":
            parts.append("\t")
        elif tag == W + "br":
            parts.append("\n")
    return "".join(parts).strip()


def _w_cell_text(tc) -> str:
    """docx 单元格文本：多段落用空格连接。"""
    texts = []
    for p in tc.findall(W + "p"):
        t = _w_para_text(p)
        if t:
            texts.append(t)
    return " ".join(texts)


def _rows_to_md(rows) -> str:
    """二维单元格列表 → md 表格（首行作表头 + 分隔行，列数按首行补齐）。"""
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    lines = []
    header = (rows[0] + [""] * ncol)[:ncol]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * ncol) + " |")
    for r in rows[1:]:
        row = (r + [""] * ncol)[:ncol]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def docx_to_md(path: str) -> str:
    """docx → md：段落与表格按文档顺序交错输出。"""
    with zipfile.ZipFile(path) as z:
        xml_data = z.read("word/document.xml")
    root = ET.fromstring(xml_data)
    body = root.find(W + "body")
    if body is None:
        return ""
    out = []
    for child in body:
        if child.tag == W + "p":
            t = _w_para_text(child)
            if t:
                out.append(t)
        elif child.tag == W + "tbl":
            rows = []
            for tr in child.findall(W + "tr"):
                rows.append([_w_cell_text(tc) for tc in tr.findall(W + "tc")])
            t = _rows_to_md(rows)
            if t:
                out.append(t)
    return "\n\n".join(out)


# ===== pptx =====

def _iter_els(el, skip_tag=None):
    """递归遍历元素，可跳过指定标签的整棵子树（iter() 无法跳过）。"""
    if skip_tag is not None and el.tag == skip_tag:
        return
    yield el
    for child in el:
        yield from _iter_els(child, skip_tag)


def _pptx_shape_text(sp) -> str:
    """pptx 形状内文本：a:p → 段落，a:t 拼接。"""
    lines = []
    for p in sp.findall(".//" + A + "p"):
        t = "".join(n.text or "" for n in p.iter(A + "t")).strip()
        if t:
            lines.append(t)
    return "\n".join(lines)


def _pptx_graphic_tables(gf) -> list:
    """pptx graphicFrame 内的表格 → md 表格列表。"""
    tables = []
    for tbl in gf.iter(A + "tbl"):
        rows = []
        for tr in tbl.iter(A + "tr"):
            cells = []
            for tc in tr.iter(A + "tc"):
                c = " ".join(
                    "".join(t.text or "" for t in p.iter(A + "t")).strip()
                    for p in tc.iter(A + "p")
                    if "".join(t.text or "" for t in p.iter(A + "t")).strip()
                )
                cells.append(c)
            rows.append(cells)
        t = _rows_to_md(rows)
        if t:
            tables.append(t)
    return tables


def _pptx_slide_text(root) -> str:
    """单张 slide → md：spTree 内按顺序交替文本形状与表格。"""
    sp_tree = root.find(".//" + P + "spTree")
    if sp_tree is None:
        return ""
    out = []
    for child in sp_tree:
        if child.tag == P + "sp":
            t = _pptx_shape_text(child)
            if t:
                out.append(t)
        elif child.tag == P + "graphicFrame":
            for t in _pptx_graphic_tables(child):
                if t:
                    out.append(t)
    return "\n\n".join(out)


def pptx_to_md(path: str) -> str:
    """pptx → md：每张 slide 一节（### Slide N），保留表格。"""
    with zipfile.ZipFile(path) as z:
        slides = sorted(
            [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
            key=lambda n: int(re.search(r"(\d+)", n).group(1)),
        )
        if not slides:
            raise ValueError(f"{path} 不是有效的 pptx（缺少 ppt/slides/slideN.xml）")
        parts = []
        for i, s in enumerate(slides, 1):
            root = ET.fromstring(z.read(s))
            text = _pptx_slide_text(root)
            if text:
                parts.append(f"### Slide {i}\n\n{text}")
    return "\n\n".join(parts)


# ===== 统一入口 =====

def office_to_md(path: str) -> str:
    """按扩展名分发：.docx / .pptx。其他格式抛 ValueError。

    依据 BASE.md §6.7 分层方案：
    - .docx / .pptx → 本解析器（stdlib-only 零依赖）；
    - .ppt 老格式（OLE）→ 抛错，指引安装 word-reader / antiword；
    - .pdf → 抛错，指引调用环境中的 pdf 技能（扫描件需 OCR）。
    """
    low = path.lower()
    if low.endswith(".docx"):
        return docx_to_md(path)
    if low.endswith(".pptx") or low.endswith(".ppt"):
        if low.endswith(".ppt"):
            raise ValueError(".ppt 老格式（OLE）无法 stdlib 解析，请安装 word-reader / antiword")
        return pptx_to_md(path)
    if low.endswith(".pdf"):
        raise ValueError(".pdf 无法 stdlib 解析，请调用环境中的 pdf 技能（扫描件需 OCR）")
    raise ValueError(f"不支持的格式: {path}（支持 .docx / .pptx）")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python office_to_md.py <file.docx|file.pptx> [--check]", file=sys.stderr)
        return 2
    path = sys.argv[1]
    try:
        md = office_to_md(path)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    if "--check" in sys.argv:
        print(f"OK: {len(md)} 字符, {md.count(chr(10))} 行")
        return 0
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
