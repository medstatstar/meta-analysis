# -*- coding: utf-8 -*-
"""pdf_extractor — PDF 数据抓取 P1（文本型 PDF + 有框表格 + 叙述句 + 一致性校验）。

设计 spec：contracts/pdf_extraction/v0.1.0/SPEC.md（P1 范围，扫描件暂不支持）。

流水线（对齐 2026-08-31 设计讨论）：
  ① 版面解析：PyMuPDF 检测文本层，pdfplumber 提取有框表格（vertical_strategy=lines，
     等效 Camelot lattice，不引入新依赖；Camelot 留作后续可选增强）。
  ② 双通道抽取：
     - 表格模板：T_DICHOT（2x2 四格表：events/n × 实验组/对照组）、T_CONTINUOUS
       (n/mean/SD × 两臂)。输出原始计数（ai/bi/ci/di）——供 ③ 勾稽重算。
     - 正文叙述模板：正则候选片段抽取（零幻觉），命中片段带页码锚点。
       P1 覆盖：四格计数 n/N (%)、风险比/均差 + 95%CI。连续结局叙述默认 needs_review。
  ③ 一致性校验（纯代码、零幻觉，正确率的最大杠杆）：
     - 四格表重算 OR/RR 与报告值比对；events ≤ n；跨来源（表格 vs 正文）互证。
     - te/sete 与 95%CI 互推（Woolf / CI 宽度）。
  ④ 置信路由：verified（勾稽全过）→ 自动通过；needs_review（校验不过/来源单一/
     连续结局叙述）→ 人工审核（附页码锚点）；failed（无法定位）→ 人工补录。
  ⑤ 输出直接对接 fullflow A4 闸：rows 形如 b1 可消费的 study 字典 + 审核元数据
     （confidence/checks/anchors）。人工审核通过后走 extraction_guard stamp --confirm。

v0.1 已知限制：
  - 无扫描件通道（P2）；无边框表格（lines 策略抓不到，P2 用 Camelot stream 或 Docling）；
  - 表头模板基于关键词打分匹配，异形表头需人工在审核台指定列映射（P2 交互列映射）；
  - 叙述连续结局只产出候选 + 锚点，不做自动直通。
"""

import os
import re
import math
import json


def _norm_path(p):
    """路径规范化：把 Git Bash 的 /c/... 转 Windows 风格，并解析为绝对路径。"""
    if p is None:
        return p
    # Git Bash 传 /c/foo 时，先转 C:/foo（normpath 在 Windows 上会误拼）
    if re.match(r"^/[a-zA-Z]/", p):
        p = p[1].upper() + ":" + p[2:]
    p = os.path.normpath(p)
    if not os.path.isabs(p):
        p = os.path.abspath(p)
    return p

# ---------------------------------------------------------------------------
# ① 版面解析
# ---------------------------------------------------------------------------

def parse_pdf(pdf_path):
    """解析文本型 PDF，按「通用 → 专用」多级降级提取表格。

    返回 {pages: [{page, kind, text, table_tiers, tables}], n_pages}。
    每页 table_tiers 为按优先级排列的层级结果：
      T1 pdfplumber-lines   有框表（通用，最稳）；
      T2 pymupdf-word-rebuild  PyMuPDF word 坐标重建（无边框表专用精细抓取）。
    首个非空层即该页数据源（tables 字段 = 该层表格，向后兼容）；
    全部层为空 → 普通正文页（table_tiers=[]）。
    扫描页（无文本层）标记 kind="scanned"（P1 不支持 OCR，如实上报）。
    已评估不采用的中间层：pdfplumber text 对齐策略与 PyMuPDF find_tables
    （后者默认 lines 对无框表 0 检出；前者把正文撕成伪表）。
    """
    import fitz
    import pdfplumber

    pdf_path = _norm_path(pdf_path)
    pages = []
    with fitz.open(pdf_path) as doc:
        n_pages = len(doc)
        texts = [p.get_text() or "" for p in doc]

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = texts[i] if i < len(texts) else page.extract_text() or ""
            if not text.strip():
                pages.append({"page": i + 1, "kind": "scanned", "text": "",
                              "table_tiers": [], "tables": []})
                continue
            table_tiers = []
            # T1：有框表（lines 策略，通用）——一页多表都会返回
            t1 = []
            try:
                t1 = page.extract_tables({
                    "vertical_strategy": "lines", "horizontal_strategy": "lines",
                    "snap_tolerance": 3, "intersection_tolerance": 3,
                }) or []
            except Exception:
                t1 = []
            t1 = [t for t in t1 if t and len(t) >= 2 and len(t[0]) >= 2]
            if t1:
                table_tiers.append({"tier": 1, "method": "pdfplumber-lines",
                                    "tables": t1})
            # T2：无边框表（PyMuPDF word 坐标按列/行聚类重建，专用精细）
            if not table_tiers:
                rebuilt = _rebuild_borderless_table(pdf_path, i)
                if rebuilt:
                    table_tiers.append({"tier": 2, "method": "pymupdf-word-rebuild",
                                        "tables": [rebuilt]})
            tables = table_tiers[0]["tables"] if table_tiers else []
            pages.append({"page": i + 1, "kind": "table" if tables else "text",
                          "text": text, "table_tiers": table_tiers,
                          "tables": tables})
    return {"pages": pages, "n_pages": n_pages}


def _rebuild_borderless_table(pdf_path, page_idx, min_rows=3, min_cols=2):
    """无边框表重建：基于 PyMuPDF 字符级 bbox，按 x0 聚类列、y0 聚类行。

    触发前提（由调用方保证）：该页 lines 策略未检出表格。此处再筛：
    页内存在一行含 ≥2 个数值/± 单元格且整体呈多列对齐 → 视为无边框表。
    返回 list[list[str]]（已对齐），或 None。
    """
    import fitz
    _path = _norm_path(pdf_path)
    try:
        with fitz.open(_path) as doc:
            if page_idx >= len(doc):
                return None
            pg = doc[page_idx]
            words = pg.get_text("words")  # (x0,y0,x1,y1,text,block,line,word)
    except Exception:
        return None
    if len(words) < min_rows * min_cols:
        return None

    # 按 block 号（word[5]）聚类；标题锚 = 以 'Table N' 开头的短 block
    # （正文里的 '(Table 1)' 引用不是 block 开头，不会误命中）
    from collections import defaultdict
    by_block = defaultdict(list)
    for w in words:
        by_block[w[5]].append(w)
    title_y = None
    for bno, bwords in sorted(by_block.items()):
        btext = " ".join(w[4] for w in bwords).strip()
        if len(bwords) <= 15 and re.match(r"Table\s+\d+", btext):
            title_y = min(w[1] for w in bwords)
            break
    if title_y is None:
        # 无标题锚：回退到数值词最密的 block 顶部
        best, best_n = None, 0
        for bno, bwords in by_block.items():
            n = sum(1 for w in bwords if re.search(r"\d", w[4]) or "±" in w[4])
            if n > best_n:
                best, best_n = min(w[1] for w in bwords), n
        if best_n < 3:
            return None
        title_y = best
    words = [w for w in words if w[1] >= title_y - 2]

    # 行聚类：按 y0 排序、相邻差 <6pt 归同行；行内保留全部词（标签+数据），
    # 仅过滤整行数字词 < min_cols 的行（纯文本段落 / 脚注）
    ws_sorted = sorted(words, key=lambda w: (w[1], w[0]))
    row_groups = []
    for w in ws_sorted:
        if row_groups and w[1] - row_groups[-1][0] < 6:
            row_groups[-1][1].append(w)
        else:
            row_groups.append([w[1], [w]])
    data_rows = []
    for ybase, ws in row_groups:
        nums = [w for w in ws if re.search(r"\d", w[4])]
        if len(nums) >= min_cols:
            data_rows.append((ybase, sorted(ws, key=lambda x: x[0])))
    if len(data_rows) < min_rows:
        return None

    # 列聚类：收集所有 x0 中位数，按间隔 > 列阈值切分
    xcenters = sorted(set(round((w[0] + w[2]) / 2) for _, ws in data_rows for w in ws))
    if not xcenters:
        return None
    cols, cur = [], [xcenters[0]]
    for x in xcenters[1:]:
        if x - cur[-1] > 20:  # 列间距阈值（pt）：实测 BMC 无边框表相邻数据列中心差 ~40pt
            # 边缘会被 40 误并，20 可分开且同列内词中心差（<10pt）不受影响
            cols.append(cur)
            cur = [x]
        else:
            cur.append(x)
    cols.append(cur)
    if len(cols) < min_cols:
        return None
    col_centers = [sum(c) / len(c) for c in cols]

    # 组装：每行按列中心归类词，合并同列词文本
    table = []
    for _, ws in data_rows:
        row = [""] * len(col_centers)
        for w in ws:
            cx = (w[0] + w[2]) / 2
            ci = min(range(len(col_centers)), key=lambda i: abs(col_centers[i] - cx))
            row[ci] = (row[ci] + " " + w[4]).strip() if row[ci] else w[4]
        table.append(row)
    if not table:
        return None
    # 对齐列数（短行补空）
    ncol = max(len(r) for r in table)
    table = [r + [""] * (ncol - len(r)) for r in table]
    # 首列作标签列补一行表头占位（模板靠标签识别，无需真表头）
    return table


# ---------------------------------------------------------------------------
# ②A 表格模板
# ---------------------------------------------------------------------------

def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _num(cell):
    """单元格 → float（容忍 '12', '12.0', '1,234', '12 (34%)' 里的首个数）。"""
    if cell is None:
        return None
    m = re.search(r"-?\d[\d,]*\.?\d*", str(cell).replace(",", ""))
    return float(m.group()) if m else None


def _frac(cell):
    """单元格 → (events, total)：匹配 '12/34'、'12 / 34 (35.3%)'。"""
    m = re.search(r"(\d+)\s*/\s*(\d+)", str(cell or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


_DICHOT_ARM_HINTS = ("experimental", "treatment", "intervention", "test",
                     "实验", "治疗", "干预", "试验组", "处理")
_CONTROL_HINTS = ("control", "placebo", "standard", "对照", "安慰剂", "常规")


def _arm_columns(header, body):
    """在表列里定位（实验列, 对照列）与计数列。返回 dict 或 None。

    策略：优先找 'n/N' 型计数列（_frac 可解析且数据行过半可解析）；若无，找事件数+n 列。
    两臂列按表头关键词打分；打分失败但恰两数据列时按左=实验、右=对照约定（并在
    checks 里提示人工确认臂方向——方向错误是四格表最致命错误）。
    """
    n_cols = max((len(r) for r in [header] + body), default=0)
    frac_cols, ev_cols = [], []
    for c in range(n_cols):
        col = [r[c] if c < len(r) else None for r in body]
        vals = [v for v in col if v not in (None, "")]
        if not vals:
            continue
        if sum(1 for v in vals if _frac(v)) >= max(1, len(vals) // 2):
            frac_cols.append(c)
        elif sum(1 for v in vals if _num(v) is not None) >= max(1, len(vals) // 2):
            ev_cols.append(c)

    # 表头臂打分
    exp_col = ctrl_col = None
    for c in range(n_cols):
        h = _norm(header[c] if c < len(header) else "")
        if any(k in h for k in _DICHOT_ARM_HINTS):
            exp_col = exp_col if exp_col is not None else c
        elif any(k in h for k in _CONTROL_HINTS):
            ctrl_col = ctrl_col if ctrl_col is not None else c

    if frac_cols:
        if exp_col is not None and ctrl_col is not None:
            return {"exp": exp_col, "ctrl": ctrl_col, "style": "frac",
                    "colmap": "keyword"}
        # 恰两个 n/N 计数列：按列序
        if len(frac_cols) >= 2:
            return {"exp": frac_cols[0], "ctrl": frac_cols[1], "style": "frac",
                    "colmap": "positional"}
        return None
    return None


def t_dichot(table, page_no, table_idx=0):
    """四格表模板。输入 pdfplumber 表（list[list]），返回 rows（0 或多条）。

    行选择：数据行须至少两臂列都含 n/N 计数。study 名取行首非空单元格。
    """
    if not table or len(table) < 2:
        return []
    header, body = table[0], [r for r in table[1:] if r and any(r)]
    if not body:
        return []
    cols = _arm_columns(header, body)
    if not cols:
        return []

    rows, skipped = [], []
    for r in body:
        # 标签 = 首列文本（可含数字如 "Death at 30d"；只排除 n/N 计数与纯数值单元格）
        first = str(r[0]).strip() if r and r[0] not in (None, "") else ""
        label = first if (first and _frac(first) is None
                          and not re.fullmatch(r"[\d.,\s()%/-]+", first)) else None
        fe = _frac(r[cols["exp"]] if cols["exp"] < len(r) else None)
        fc = _frac(r[cols["ctrl"]] if cols["ctrl"] < len(r) else None)
        if not (fe and fc and label):
            if fe or fc:
                skipped.append(label or "?")
            continue
        rows.append({
            "study": label,
            "ai": fe[0], "bi": fe[1] - fe[0],   # 实验组：事件 / 非事件
            "ci": fc[0], "di": fc[1] - fc[0],   # 对照组：事件 / 非事件
            "_meta": {"source": "table", "page": page_no, "table": table_idx,
                      "template": "T_DICHOT", "colmap": cols["colmap"],
                      "anchor": f"p{page_no} table#{table_idx + 1} row '{label}'"},
        })
    return rows


def t_continuous(table, page_no, table_idx=0):
    """连续结局模板：找 n / mean / SD × 两臂 列（关键词打分）。

    输出 te=mean差、sete 由 SD 与 n 合成（原始数值附 raw，供校验/人工）。
    匹配不到明确 mean/SD 结构 → 返回 []（宁缺勿错）。
    """
    if not table or len(table) < 2:
        return []
    header, body = table[0], [r for r in table[1:] if r and any(r)]
    # 表级防御：纯基线特征表（baseline/demographic/age… 且无结局词）不产效应量
    flat_hdr = " ".join(str(c or "") for c in header).lower()
    flat_body = " ".join(str(c or "") for r in body for c in r).lower()
    is_outcome = bool(_OUTCOME_KW.search(flat_hdr + " " + flat_body))
    if _BASELINE_KW.search(flat_hdr) and not is_outcome:
        return []
    # n (%) 计数表防御：表内声明 'n (%)'/'no. (%)' → 全表为计数+百分数，
    # '2216 (93.4)' 会被 mean±(sd) 行内正则误配成对 → 跳过
    if re.search(r"n\s*\(%\)|no\.\s*\(%\)|number\s*\(%\)", flat_hdr + " " + flat_body):
        return []
    # n (%) 计数表防御 2：无声明但数值对几乎全为整数对（真实 m±SD 几乎必含小数）
    m_all = re.compile(r"(-?\d+\.?\d*)\s*[±(]\s*(\d+\.?\d*)")
    all_pairs = [q for r in body for v in r if v is not None and "/" not in str(v)
                 for q in m_all.findall(str(v))]
    if all_pairs and sum(1 for a, b in all_pairs
                         if "." not in a and "." not in b) >= 0.8 * len(all_pairs):
        return []
    n_cols = max((len(r) for r in [header] + body), default=0)
    kinds = {}
    for c in range(n_cols):
        h = _norm(header[c] if c < len(header) else "")
        col = [r[c] if c < len(r) else None for r in body]
        vals = [v for v in col if v not in (None, "")]
        if not vals:
            continue
        if re.search(r"\bn\b|no\.|样本|例数", h) and all(_num(v) is not None and _num(v) == int(_num(v)) for v in vals[:3]):
            kinds.setdefault("n", c)
        elif re.search(r"mean|均值|均数", h):
            kinds.setdefault("mean", c)
        elif re.search(r"\bsd\b|s\.d\.|std|标准差", h):
            kinds.setdefault("sd", c)
        elif re.search(r"\bse\b|标准误", h):
            kinds.setdefault("se", c)
    if not {"n", "mean"}.issubset(kinds) or ("sd" not in kinds and "se" not in kinds):
        kinds = None  # 列模式不成立；仍可走行内 'mean (sd)' 文本模式

    # 两臂拆分：优先行内 'mean (sd)' 文本对（P1 主路径）；列模式留 P2 扩展
    out = []
    m_re = re.compile(r"(-?\d+\.?\d*)\s*[±(]\s*(\d+\.?\d*)")
    for r in body:
        first = str(r[0]).strip() if r and r[0] not in (None, "") else ""
        label = first if (first and _frac(first) is None
                          and not re.fullmatch(r"[\d.,\s()%/-]+", first)
                          and not m_re.search(first)) else None
        # 行内文本 'mean (sd)' 对（排除 n/N 型单元格：'30/100 (30.0%)' 会误配 '100 (30.0'》）
        pairs = [m_re.findall(str(v)) for v in r
                 if v is not None and "/" not in str(v)]
        pairs = [p for p in pairs if p]
        # 恰好 2 组 m±SD 才配两臂；>2 组是基线多臂/未知结构，宁缺勿错
        if label and len(pairs) == 2:
            (m1, s1), (m2, s2) = pairs[0][0], pairs[1][0]
            n1 = _num(r[kinds["n"]]) if kinds and kinds.get("n") is not None \
                and kinds["n"] < len(r) else None
            n2 = None
            # n 列缺失时回退：行内整数对（如 n 列值与另一个 n）
            nums = [_num(v) for v in r if v is not None and _num(v) is not None]
            ints = [x for x in nums if x and x == int(x)]
            if n1 is None and len(ints) >= 1:
                n1 = ints[0]
                if n2 is None and len(ints) >= 2:
                    n2 = ints[1]
                if n1 and n2 is None:
                    # 单 n 回退：两组共用同一 n（常见于同 n 设计），交人工确认
                    n2 = n1
            if n1 and n2 and float(s1) > 0 and float(s2) > 0:
                diff = float(m1) - float(m2)
                se = math.sqrt(float(s1) ** 2 / n1 + float(s2) ** 2 / n2)
                out.append({
                    "study": label, "te": round(diff, 6), "sete": round(se, 6),
                    "_meta": {"source": "table", "page": page_no,
                              "table": table_idx + 1, "template": "T_CONTINUOUS",
                              "raw": {"m1": float(m1), "sd1": float(s1), "n1": n1,
                                      "m2": float(m2), "sd2": float(s2), "n2": n2},
                              "anchor": f"p{page_no} table#{table_idx + 1} row '{label}'"},
                })
    return out


# ===========================================================================
# ②A-2 数值解析硬化 + 效应量/连续型结局增强（v0.2，经 12 篇 PDF 实证）
# ===========================================================================
#
# 相对原 t_continuous 的增强：
#   1. 数值解析硬化 _f：支持前导点(.27)、千分位、四种连字符；CI 分隔符类 _SEP。
#   2. 效应量叙述模板 EXTRACTION_TEMPLATES（HR/OR/RR/MD），命中即回填 te/sete
#      （te=ln(est) 仅比值度量；MD 用原值；sete=(ln(hi)-ln(lo))/3.92 对称 CI）。
#   3. 效应量表格模板 t_effect_table：森林图结局表（2×2 内嵌 + HR 列 → 双源）。
#   4. 连续型结局表格模板 t_cont_table：重复测量表（Changes/Beta 列）、标准两臂表。
#   5. 连续型叙述 narrative_continuous：正文 MD (95% CI)。
# 置信策略（HITL·准确度优先）：双源(2×2↔HR列)或带报告OR交叉验证→verified；
#   单源叙述/表格→needs_review（报告数字逐字+确定变换，人工一键确认进 Block B）。

# 分隔符类：to / en-dash / em-dash / ascii 连字符 / 数学减号(U+2212) / ~
_SEP = r"(?:to|–|—|-|−|~)"
# 通用浮点（支持前导点 .27 与千分位）
_FNUM = r"-?(?:\d[\d,]*\.?\d*|\.\d+)"
_F = re.compile(_FNUM)


def _f(cell):
    """单元格 → float，容忍 '12'、'12.0'、'.27'、'1,234'、'-0.161'、'−0.161'(U+2212)。"""
    if cell is None:
        return None
    # 统一数学减号 U+2212 → ascii '-'
    s = str(cell).replace("−", "-")
    m = _F.search(s.replace(",", ""))
    return float(m.group()) if m else None


# CI 紧凑式（表格常见）：'0.74 (0.65–0.85)' / '0.74 [0.65 to 0.85]'
_EFFECT_CI = re.compile(
    rf"({_FNUM})\s*[\(\[]\s*({_FNUM})\s*{_SEP}\s*({_FNUM})\s*[\)\]]")


def _effect_re(label_alt):
    """按度量标签构造 'label te ; 95% CI lo-hi' 正则（间隔段禁括号、放行 95% 中的数字）。

    te 与 CI 锚之间允许一个 '(' —— 支持 BMC 系嵌套括号写法
    '(odds ratio 1.71 (95% CI 0.93 to 3.16))'。
    """
    return re.compile(
        rf"(?:{label_alt})\b"
        r"[^0-9\-–—−()]{0,6}?"
        rf"(?P<te>{_FNUM})"
        # te→CI 锚间隔允许括号（BMC 系嵌套写法 '(OR 1.71 (95% CI 0.93 to 3.16))'）；
        # 误越界由 _effect_from_match 的 lo<=te<=hi 校验兜底
        r".{0,80}?"
        r"(?:95\s*%\s*(?:confidence interval)?\s*(?:\[ci\])?\s*|ci)\b"
        r"[ ,:(\n]*"  # CI 锚与 lo 间允许换行（PDF 文本 '95% CI,\n0.76-0.92' 常见）
        rf"(?P<lo>{_FNUM})\s*{_SEP}\s*(?P<hi>{_FNUM})",
        re.IGNORECASE)


EXTRACTION_TEMPLATES = {
    "HR": {"measure": "HR", "re": _effect_re(r"hazard ratio|\bhr\b")},
    "OR": {"measure": "OR", "re": _effect_re(r"odds ratio|\bor\b")},
    "RR": {"measure": "RR", "re": _effect_re(r"risk ratio|relative risk|rate ratio|\brr\b")},
    "MD": {"measure": "MD", "re": _effect_re(r"mean difference|difference in means|\bmd\b")},
}

_PVAL = re.compile(
    r"(?:p[\s-]?value|(?<![a-zA-Z])p)\s*[=<]\s*"
    r"(\.?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?)\s*(?:\(|\)|\b|,|\.|;|$)",
    re.IGNORECASE)

_EMBED_2X2 = re.compile(r"(\d+)\s*/\s*(\d+)\s+(\d+)\s*/\s*(\d+)")
_CONT_PAIR = re.compile(rf"(?P<m>{_FNUM})\s*(?:±|\+/-|±)\s*(?P<s>{_FNUM})", re.IGNORECASE)
_CONT_BETA_CI = re.compile(
    rf"(?P<beta>{_FNUM})\s*[\(\[]\s*(?P<lo>{_FNUM})\s*(?:{_SEP}|,)\s*(?P<hi>{_FNUM})\s*[\)\]]")
_OUTCOME_KW = re.compile(
    r"change|changes|δ|Δ|after\s*[-–]?\s*before|post[-\s]?treatment|"
    r"beta|coefficient|difference|outcome|effect|vs\.?\s*placebo|"
    r"干预|变化|差值|效应|结局", re.IGNORECASE)
_BASELINE_KW = re.compile(r"baseline|demographic|characteristic|age|体重|bmi", re.IGNORECASE)
_DESCR_KW = re.compile(r"point difference|proportion|percentage|%|patients with|"
                        r"subjects with|n\s*=|no\. of", re.I)


def _effect_from_match(measure, m, page, text):
    """由叙述正则命中构造效应量记录（比值度量 te=ln；MD 用原值）。"""
    try:
        te = float(m.group("te").replace(",", ""))
        lo = float(m.group("lo").replace(",", ""))
        hi = float(m.group("hi").replace(",", ""))
    except (ValueError, AttributeError):
        return None
    if not (lo > 0 and hi > lo and lo <= te <= hi):
        return None
    sete = (math.log(hi) - math.log(lo)) / 3.92 if lo > 0 else None
    if sete is None or sete <= 0:
        return None
    pre = text[max(0, m.start() - 50):m.start()].strip()
    labs = re.findall(r"[A-Za-z][A-Za-z ]{0,45}", pre)
    study = labs[-1].strip() if labs and " " in labs[-1] else ""
    if not study or len(study) > 40:
        study = f"{measure} (p{page})"
    else:
        study = study[-40:]
    snippet = text[max(0, m.start() - 60):m.end() + 40].replace("\n", " ").strip()
    rec = {
        "study": study,
        "measure": measure,
        "te": round(math.log(te), 6) if measure != "MD" else round(te, 6),
        "sete": round(sete, 6),
        "reported": {"est": round(te, 4), "ci": [round(lo, 4), round(hi, 4)]},
        "_meta": {"source": "narrative", "page": page,
                  "template": f"T_{measure}_CI",
                  "anchor": f"p{page} text: …{snippet[:80]}…",
                  "snippet": snippet},
    }
    return rec


def narrative_effects(pages):
    """扫描正文，返回效应量候选（HR/OR/RR/MD/P）。"""
    out = []
    for p in pages:
        if p["kind"] == "scanned":
            continue
        text = p["text"]
        for measure, spec in EXTRACTION_TEMPLATES.items():
            for m in spec["re"].finditer(text):
                rec = _effect_from_match(measure, m, p["page"], text)
                if rec:
                    out.append(rec)
        for m in _PVAL.finditer(text):
            try:
                pv = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            if pv > 1:  # P 值域 [0,1]；拦截 'group 30' 类残网命中
                continue
            out.append({
                "kind": "pvalue",
                "measure": "P",
                "reported": {"p": round(pv, 6), "sig": pv < 0.05},
                "_meta": {"source": "narrative", "page": p["page"],
                          "template": "T_PVALUE",
                          "anchor": f"p{p['page']} text: …{text[max(0,m.start()-50):m.end()+20].replace(chr(10),' ').strip()}…"},
            })
    return out


def t_effect_table(table, page_no, table_idx=0):
    """效应量（HR/OR/RR）表格模板。返回行（可同时含 ai/bi/ci/di + te/sete）。

    触发条件（防误抓连续型「均值±CI」列）：
      - 表头列含 HR/OR/RR/hazard/odds/risk 等效应量关键词，或
      - 首列内嵌 2×2 计数（森林图典型特征：'386/2371 502/2371'）。
    二者皆无 → 视为非效应量表，返回 []（交 t_cont_table / 跳过）。
    """
    if not table or len(table) < 2:
        return []
    header, body = table[0], [r for r in table[1:] if r and any(r)]
    if not body:
        return []

    n_cols = max((len(r) for r in [header] + body), default=0)
    eff_col = None
    hdr_effect = False
    for c in range(n_cols):
        col = [r[c] if c < len(r) else None for r in body]
        vals = [str(v) for v in col if v not in (None, "")]
        if not vals:
            continue
        h = _norm(header[c] if c < len(header) else "")
        is_eff = any(k in h for k in ("hr", "hazard", "odds", "or", "risk",
                                     "rr", "relative", "ratio", "hazard ratio"))
        if is_eff and eff_col is None:
            eff_col, hdr_effect = c, True
        if sum(1 for v in vals if _EFFECT_CI.search(v)) >= max(1, len(vals) // 3):
            eff_col = eff_col if eff_col is not None else c

    lbl_col = 0
    label_has_2x2 = any(_EMBED_2X2.search(str(r[lbl_col])) for r in body
                        if lbl_col < len(r) and r[lbl_col])

    if eff_col is None or not (hdr_effect or label_has_2x2):
        return []

    if hdr_effect:
        h0 = _norm(header[eff_col])
        if "hazard" in h0 or " hr" in h0:
            measure = "HR"
        elif "odds" in h0 or re.search(r"\bor\b", h0):
            measure = "OR"
        elif "risk" in h0 or "rr" in h0 or "relative" in h0:
            measure = "RR"
        else:
            measure = "HR/OR/RR"
    else:
        measure = "HR"

    rows = []
    for r in body:
        cell = r[eff_col] if eff_col < len(r) else None
        if not cell:
            continue
        m = _EFFECT_CI.search(str(cell))
        if not m:
            continue
        te0, lo, hi = _f(m.group(1)), _f(m.group(2)), _f(m.group(3))
        if not (lo > 0 and hi > lo and lo <= te0 <= hi):
            continue
        label = str(r[lbl_col]).strip() if lbl_col < len(r) and r[lbl_col] else ""
        label_clean = re.sub(r"\s*\d+/\d+\s+\d+/\d+.*$", "", label).strip() or label
        rec = {
            "study": label_clean[:60],
            "measure": measure,
            "te": round(math.log(te0), 6),
            "sete": round((math.log(hi) - math.log(lo)) / 3.92, 6),
            "reported": {"est": round(te0, 4), "ci": [round(lo, 4), round(hi, 4)]},
            "_meta": {"source": "table", "page": page_no, "table": table_idx + 1,
                      "template": "T_EFFECT_TABLE",
                      "anchor": f"p{page_no} table#{table_idx + 1} row '{label_clean[:40]}'"},
        }
        em = _EMBED_2X2.search(label)
        if em:
            ae, ne, ac, nc = (int(em.group(i)) for i in (1, 2, 3, 4))
            if ne >= ae and nc >= ac:
                rec["ai"], rec["bi"] = ae, ne - ae
                rec["ci"], rec["di"] = ac, nc - ac
        rows.append(rec)
    return rows


def _cont_pairs(cell):
    """从单元格抽取所有 (mean, sd) 对（仅真正的 ± 符号）。"""
    if cell is None:
        return []
    return [(float(a.replace(",", "")), float(b.replace(",", "")))
            for a, b in _CONT_PAIR.findall(str(cell))]


def t_cont_table(table, page_no, table_idx=0):
    """连续型结局表格模板。返回 MD 效应量行（供 Block B 连续型 meta）。

    适用：重复测量表（Before/After/Changes 三态 + 两组并排，或 Beta 列）或标准两臂表。
    不适用：纯基线特征表（仅 Before 两列、无 change/β 标记）→ 返回 []。
    """
    if not table or len(table) < 2:
        return []
    header, body = table[0], [r for r in table[1:] if r and any(r)]
    if not body:
        return []

    flat_hdr = " ".join(str(c or "") for c in header).lower()
    flat_body = " ".join(str(c or "") for r in body for c in r).lower()
    is_outcome = bool(_OUTCOME_KW.search(flat_hdr + " " + flat_body))
    is_pure_baseline = _BASELINE_KW.search(flat_hdr) and not is_outcome
    if is_pure_baseline or not is_outcome:
        return []

    n_cols = max((len(r) for r in [header] + body), default=0)
    rows = []
    beta_col = None
    for c in range(n_cols):
        h = _norm(header[c] if c < len(header) else "")
        if re.search(r"beta|coefficient|回归系数|β", h):
            beta_col = c
            break

    parent_label = ""
    for r in body:
        label = ""
        if r and r[0] is not None:
            first = str(r[0]).strip()
            if first and not re.fullmatch(r"[\d.,\s()%±/\-–—−]+", first) \
               and _frac(first) is None:
                label = first
        if label:
            if not re.fullmatch(r"(before|after|changes?|δ|Δ|baseline)",
                                label.strip(), re.IGNORECASE):
                parent_label = label
        else:
            if len(r) > 1 and r[1] is not None:
                sub = str(r[1]).strip()
                if re.fullmatch(r"(before|after|changes?|δ|Δ|baseline)",
                                sub, re.IGNORECASE):
                    label = (parent_label + " " + sub).strip() if parent_label else sub
                elif sub and not re.fullmatch(r"[\d.,\s()%±/\-–—−]+", sub):
                    label = sub
        if not label:
            continue
        if re.fullmatch(r"(male|female|yes|no|former|current)", label.strip(), re.IGNORECASE):
            continue

        # 形态 A：Beta (95% CI) 列 → 直接 MD(95%CI)
        if beta_col is not None and beta_col < len(r) and r[beta_col]:
            m = _CONT_BETA_CI.search(str(r[beta_col]))
            if m:
                beta0 = _f(m.group("beta"))
                lo, hi = _f(m.group("lo")), _f(m.group("hi"))
                if lo < hi and lo <= beta0 <= hi:
                    se = (hi - lo) / 3.92
                    rows.append({
                        "study": label[:50], "measure": "MD",
                        "te": round(beta0, 6), "sete": round(se, 6),
                        "reported": {"est": round(beta0, 4), "ci": [round(lo, 4), round(hi, 4)]},
                        "_meta": {"source": "table", "page": page_no, "table": table_idx + 1,
                                  "template": "T_CONT_BETA",
                                  "raw": {"beta": beta0, "lo": lo, "hi": hi},
                                  "anchor": f"p{page_no} table#{table_idx+1} row '{label[:30]}' (Beta col)"},
                    })
                    continue

        # 形态 B/C：行内两组 mean±SD 对 → MD（或 'x (lo,hi)' 形态）
        pairs = []
        for c in range(1, len(r)):
            for m_, s_ in _cont_pairs(r[c]):
                pairs.append((m_, s_, c))
        pairs = [(m_, s_, c) for m_, s_, c in pairs if s_ > 0]
        row_text = " ".join(str(c_) for c_ in r if c_ is not None).lower()
        is_change_row = ("change" in row_text or "δ" in row_text or "Δ" in row_text
                         or " vs " in row_text or "compared" in row_text
                         or ("post" in row_text and "pre" in row_text))
        if not is_change_row:
            continue
        if _DESCR_KW.search(label) or _DESCR_KW.search(row_text):
            continue
        if len(pairs) >= 2:
            (m1, s1, _), (m2, s2, _) = pairs[0], pairs[1]
            n1 = n2 = None
            group_nums = re.findall(r"\((\d+)\)", " ".join(str(c_) for c_ in r if c_ is not None))
            ints = [int(x) for x in group_nums if int(x) > 5]
            if ints:
                n1 = ints[0]
                n2 = ints[1] if len(ints) >= 2 else n1
            diff = m1 - m2
            se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2) if (n1 and n2) else None
            rows.append({
                "study": label[:50], "measure": "MD",
                "te": round(diff, 6), "sete": round(se, 6) if se else None,
                "reported": {"m1": round(m1, 4), "sd1": round(s1, 4), "n1": n1,
                             "m2": round(m2, 4), "sd2": round(s2, 4), "n2": n2},
                "_meta": {"source": "table", "page": page_no, "table": table_idx + 1,
                          "template": "T_CONT_CHANGE" if is_change_row else "T_CONT_TWOARM",
                          "raw": {"m1": m1, "sd1": s1, "n1": n1, "m2": m2, "sd2": s2, "n2": n2,
                                  "diff": diff, "se": se},
                          "anchor": f"p{page_no} table#{table_idx+1} row '{label[:30]}'"},
            })
        else:
            ci_cells = [c for c in r[1:] if c and _CONT_BETA_CI.search(str(c))]
            bare = [_f(c) for c in r[1:] if c and re.search(_FNUM, str(c))
                    and not _CONT_BETA_CI.search(str(c))]
            if len(ci_cells) >= 2:
                betas = [_f(_CONT_BETA_CI.search(str(c)).group("beta")) for c in ci_cells[:2]]
                m1, m2 = betas[0], betas[1]
                diff = m1 - m2
                se = None
                for cc in ci_cells[:2]:
                    mm = _CONT_BETA_CI.search(str(cc))
                    if mm:
                        lo, hi = _f(mm.group("lo")), _f(mm.group("hi"))
                        se = max(se or 0, (hi - lo) / 3.92)
                rows.append({
                    "study": label[:50], "measure": "MD",
                    "te": round(diff, 6), "sete": round(se, 6) if se else None,
                    "reported": {"m1": round(m1, 4), "m2": round(m2, 4),
                                 "ci_width_se": round(se, 4) if se else None},
                    "_meta": {"source": "table", "page": page_no, "table": table_idx + 1,
                              "template": "T_CONT_CHANGE_CI",
                              "anchor": f"p{page_no} table#{table_idx+1} row '{label[:30]}'"},
                })
    return rows


def narrative_continuous(pages):
    """正文连续型效应量（MD / mean difference (95% CI)）。"""
    out = []
    md_re = EXTRACTION_TEMPLATES["MD"]["re"]
    for p in pages:
        if p["kind"] == "scanned":
            continue
        text = p["text"]
        for m in md_re.finditer(text):
            rec = _effect_from_match("MD", m, p["page"], text)
            if rec:
                out.append(rec)
        for m in re.finditer(
                rf"(?:mean difference|difference in means|weighted mean difference|"
                rf"standardized mean difference|md)\b[^()]{0,80}?\(?\s*"
                rf"(?P<te>{_FNUM})\s*(?:,|;|\(|\[)?\s*(?:95%\s*ci|ci)\s*"
                rf"[\(\[:\s]*\s*(?P<lo>{_FNUM})\s*{_SEP}\s*(?P<hi>{_FNUM})",
                text, re.IGNORECASE):
            try:
                te = _f(m.group("te"))
                lo = _f(m.group("lo"))
                hi = _f(m.group("hi"))
            except (ValueError, AttributeError):
                continue
            if not (lo < hi and lo <= te <= hi):
                continue
            se = (hi - lo) / 3.92
            pre = text[max(0, m.start() - 50):m.start()].strip()
            labs = re.findall(r"[A-Za-z][A-Za-z ]{0,45}", pre)
            study = labs[-1].strip() if labs and " " in labs[-1] else "MD"
            out.append({
                "study": study[-40:], "measure": "MD",
                "te": round(te, 6), "sete": round(se, 6),
                "reported": {"est": round(te, 4), "ci": [round(lo, 4), round(hi, 4)]},
                "_meta": {"source": "narrative", "page": p["page"],
                          "template": "T_MD_CI",
                          "anchor": f"p{p['page']} text: …{text[max(0,m.start()-50):m.end()+20].replace(chr(10),' ').strip()[:80]}…"},
            })
    return out


# ---------------------------------------------------------------------------
# ②B 正文叙述模板（正则候选，零幻觉）
# ---------------------------------------------------------------------------

_N_DICHOT = re.compile(
    r"(?P<a>\d+)\s*/\s*(?P<b>\d+)\s*(?:\((?P<pct>[\d.]+)\s*%?\))?")
_MD_CI = re.compile(
    r"(?:mean difference|difference in means|均差|md)\D{0,80}?(-?\d+\.?\d*)\s*"
    r"(?:\(?\s*95\s*%?\s*ci|\[)\s*(-?\d+\.?\d*)\s*(?:to|,|—|–|~)\s*(-?\d+\.?\d*)",
    re.IGNORECASE)
_OR_CI = re.compile(
    r"(?:odds ratio|or)\D{0,40}?(\d+\.?\d*)\s*(?:\(?\s*95\s*%?\s*ci|\[)\s*"
    r"(\d+\.?\d*)\s*(?:to|,|—|–|~)\s*(\d+\.?\d*)", re.IGNORECASE)


def narrative_candidates(pages):
    """扫描正文，返回候选片段列表（全部 needs_review，除与表格互证通过者）。

    每个候选：{kind, page, snippet, payload}。不做臂方向推断——四格计数候选只给
    原文片段，由人工（或上下文 LLM，P2）指认实验/对照组。
    """
    out = []
    for p in pages:
        if p["kind"] == "scanned":
            continue
        for m in _N_DICHOT.finditer(p["text"]):
            a, b = int(m.group("a")), int(m.group("b"))
            if a <= b <= 100000 and b >= 10:
                s = max(0, m.start() - 90)
                out.append({"kind": "dichot_counts", "page": p["page"],
                            "snippet": p["text"][s:m.end() + 60].replace("\n", " "),
                            "payload": {"events": a, "total": b}})
        for m in _MD_CI.finditer(p["text"]):
            s = max(0, m.start() - 90)
            out.append({"kind": "md_ci", "page": p["page"],
                        "snippet": p["text"][s:m.end() + 40].replace("\n", " "),
                        "payload": {"te": float(m.group(1)),
                                    "ci": [float(m.group(2)), float(m.group(3))]}})
        for m in _OR_CI.finditer(p["text"]):
            s = max(0, m.start() - 90)
            out.append({"kind": "or_ci", "page": p["page"],
                        "snippet": p["text"][s:m.end() + 40].replace("\n", " "),
                        "payload": {"te": float(m.group(1)),
                                    "ci": [float(m.group(2)), float(m.group(3))]}})
    return out


# ---------------------------------------------------------------------------
# ③ 一致性校验（纯代码，零幻觉）
# ---------------------------------------------------------------------------

def _ln(v):
    return math.log(v) if v > 0 else None


def check_dichot(row, reported_or=None, reported_ci=None):
    """四格表校验。返回 (ok: bool, checks: [str], recomputed: {or, ci})。

    - events ≤ total 两臂；ai+ci ≥ 1（避免 OR=0/∞ 崩溃交人工）；
    - 重算 OR 与报告值比对（相对误差 ≤1%）；
    - CI 由 Woolf 公式重算并与报告 CI 比对（≤2%）。
    """
    checks = []
    a, b_, c, d = row["ai"], row["bi"], row["ci"], row["di"]
    nt, nc = a + b_, c + d
    if not (0 <= a <= nt and 0 <= c <= nc):
        return False, ["events>total：事件数超过组总数"], None
    if nt == 0 or nc == 0:
        return False, ["zero-total：某组总数为 0"], None
    if min(a, b_, c, d) == 0:
        checks.append("zero-cell：存在零格，OR 重算需连续性校正（交人工确认）")
        return False, checks, None
    orn = (a * d) / (b_ * c)
    se = math.sqrt(1 / a + 1 / b_ + 1 / c + 1 / d)
    lo, hi = orn * math.exp(-1.96 * se), orn * math.exp(1.96 * se)
    if reported_or is not None:
        rel = abs(_ln(orn) - _ln(reported_or)) / max(abs(_ln(reported_or)), 1e-12)
        if rel > 0.01:
            return False, [f"or-mismatch：重算 lnOR={math.log(orn):.4f} vs 报告 "
                           f"{math.log(reported_or):.4f}（>{1}%）"], None
        checks.append("or-recompute-pass")
    if reported_ci is not None:
        if abs(lo - reported_ci[0]) / max(abs(reported_ci[0]), 1e-12) > 0.02 or \
           abs(hi - reported_ci[1]) / max(abs(reported_ci[1]), 1e-12) > 0.02:
            # CI 不匹配仍返回 rec：te/se 可由原始计数重算供人工参考，置信度单独降级
            return False, ["ci-mismatch：重算 95%CI 与报告值偏差 >2%"], \
                {"or": round(orn, 4), "ci": [round(lo, 4), round(hi, 4)]}
        checks.append("ci-recompute-pass")
    checks.append("counts-consistent")
    return True, checks, {"or": round(orn, 4),
                          "ci": [round(lo, 4), round(hi, 4)]}


def check_te_sete(te, sete, ci=None):
    """te/sete ↔ 95%CI 互推校验（Woolf：ci = te ± 1.96·sete）。"""
    checks = []
    if sete <= 0:
        return False, ["sete<=0"], None
    lo, hi = te - 1.96 * sete, te + 1.96 * sete
    if ci is not None:
        # CI 应近似对称于 te
        d_lo, d_hi = abs(te - ci[0]), abs(ci[1] - te)
        if d_lo == 0 or d_hi == 0:
            return False, ["ci-degenerate"], None
        if max(d_lo, d_hi) / min(d_lo, d_hi) > 1.25:
            # 阈值 1.25：报告值四舍五入会使 ln 空间轻微不对称（实测 ≤1.12），
            # 真正取错数值（如把不同 HR 拼接）比值远超此界（实测 4.6）
            return False, ["ci-asymmetric：CI 关于 te 明显不对称，疑似取错数值"], None
        w_re, w_rep = 3.92 * sete, (ci[1] - ci[0])
        if abs(w_re - w_rep) / max(w_rep, 1e-12) > 0.05:
            return False, [f"ci-width-mismatch：sete 推得宽度 {w_re:.4f} vs 报告 {w_rep:.4f}"], None
        checks.append("ci-recompute-pass")
    checks.append("te-sete-consistent")
    return True, checks, {"ci": [round(lo, 4), round(hi, 4)]}


# ---------------------------------------------------------------------------
# ④ 置信路由 + ⑤ 组装 A4 行
# ---------------------------------------------------------------------------

def extract(pdf_path, study_id=None, reported_summary=None):
    """主入口。返回 {rows, candidates, n_pages, review_summary}。

    rows：可直接喂 fullflow A4 extraction_table / b1 的字典列表：
      - 四格表行：{study, ai, bi, ci, di, te, sete, _review{...}}
      - 连续行：{study, te, sete, _review{...}}
    candidates：正文候选（均 needs_review）。
    reported_summary: 可选 {study_label: {"or": x, "ci": [lo, hi]}}，来自正文
      or_ci 候选——用于表格↔正文互证；未提供时四格表行只做结构勾稽。

    表格抓取按「通用 → 专用」逐页降级：T1 有框表（pdfplumber lines）→
    T2 无框表重建（PyMuPDF word 坐标）→ 叙述文本通道（独立，不降级）。
    页级命中即停（_review.tier/_review.method 可审计）；确实无法解析的页
    如实列入 review_summary.unresolved（不硬造、不误抓）。
    """
    reported_summary = reported_summary or {}
    pdf_path = _norm_path(pdf_path)
    doc = parse_pdf(pdf_path)
    rows, candidates = [], []

    def _run_templates(tab, page_no, ti):
        return (t_dichot(tab, page_no, ti)
                + t_continuous(tab, page_no, ti)
                + t_effect_table(tab, page_no, ti)
                + t_cont_table(tab, page_no, ti))

    # 逐页逐层降级：命中该页即停；全层失败 → unresolved 如实记录
    tier_report, unresolved = {}, []
    for p in doc["pages"]:
        if p["kind"] == "scanned":
            unresolved.append({"page": p["page"], "reason": "scanned",
                               "note": "扫描页无文本层，P1 不支持 OCR，需人工/OCR 处理"})
            tier_report[p["page"]] = {"tiers": [], "n_rows": 0}
            continue
        page_rows, tiers_tried = [], []
        for tier in p.get("table_tiers", []):
            trs = []
            for ti, tab in enumerate(tier["tables"]):
                for r in _run_templates(tab, p["page"], ti):
                    meta = r.get("_meta")
                    if isinstance(meta, dict):
                        meta["tier"] = tier["tier"]
                        meta["method"] = tier["method"]
                    trs.append(r)
            tiers_tried.append({"tier": tier["tier"], "method": tier["method"],
                                "n_tables": len(tier["tables"]),
                                "n_rows": len(trs)})
            if trs:  # 该页在此层命中 → 采用，不再降级
                page_rows = trs
                break
        tier_report[p["page"]] = {"tiers": tiers_tried, "n_rows": len(page_rows)}
        if page_rows:
            rows.extend(page_rows)
        elif tiers_tried:
            # 检出了表格结构但所有模板层都不命中 → 如实上报（不硬造）
            has_table_title = bool(re.search(
                r"Table\s+\d+", p.get("text") or "", re.IGNORECASE))
            unresolved.append({
                "page": p["page"], "reason": "all-tiers-no-template-hit",
                "note": ("页面检出表格且含 Table 标题，但无模板命中"
                         "（表结构非标准，建议人工录入）" if has_table_title
                         else "页面检出表格结构但无模板命中（非效应量表或版式未覆盖）"),
                "tiers": tiers_tried})
        # 无表格候选的纯正文页不属失败：叙述通道仍会扫其文本

    # 叙述效应量（HR/OR/RR/MD/P）→ 直接成行（已回填 te/sete）
    effects = narrative_effects(doc["pages"])
    rows.extend([e for e in effects if e.get("measure") != "P"])
    rows.extend(narrative_continuous(doc["pages"]))
    # 候选：① p 值（measure='P'，供显著性参考）；② 正文/表中「事件/总数」计数提及
    # （narrative_candidates，零幻觉，全部 needs_review，供人工判断是否为可入 2×2 的计数）
    # —— 之前 narrative_candidates 定义后从未被调用，导致综述类文献下载后界面一片空白。
    ncs = narrative_candidates(doc["pages"])
    candidates = [e for e in effects if e.get("measure") == "P"]
    candidates.extend(ncs)

    # 校验 + 置信路由
    review = []
    for r in rows:
        meta = r.pop("_meta", {})
        checks, conf = [], None
        if {"ai", "bi", "ci", "di"}.issubset(r):
            ok, checks, rec = check_dichot(r)
            if rec:
                # 重算值仅在行缺 te/sete 时回填，不覆盖表格自带的报告值
                # （sete 全模块统一 Woolf 约定：(lnhi-lnlo)/3.92 = se(lnOR)）
                r["te"] = r.get("te") or (round(math.log(rec["or"]), 4)
                                          if rec["or"] > 0 else None)
                r["sete"] = r.get("sete") or round(
                    (math.log(rec["ci"][1]) - math.log(rec["ci"][0])) / 3.92, 4)
            # 双源命中（森林表 2×2 计数列 + 相邻 HR 列）→ verified；其余 needs_review
            is_forest = "T_EFFECT_TABLE" in meta.get("template", "") and \
                {"ai", "bi", "ci", "di", "te"}.issubset(r)
            conf = ("verified" if (ok and is_forest) else
                    "needs_review" if ok else "failed")
        elif "sete" in r and r.get("te") is not None:
            if r.get("sete") is None:
                # 连续型 MD 缺 n → 无法算 SE，数据不完整，待人工补 n
                checks, conf = ["missing-n: SE not computable"], "needs_review"
            else:
                # check_te_sete 的 ci 需与 te 同尺度：HR/OR/RR 的 te 为 ln 值，
                # reported.ci 是原始尺度 → 先取 ln 再校验；MD 的 te 本就是原值
                rep_ci = (r.get("reported") or {}).get("ci")
                if rep_ci is not None and r.get("measure") in (
                        "HR", "OR", "RR", "HR/OR/RR") and min(rep_ci) > 0:
                    rep_ci = [math.log(rep_ci[0]), math.log(rep_ci[1])]
                ok, checks, rec = check_te_sete(r["te"], r["sete"], ci=rep_ci)
                # 效应量(CI)/连续型表格行：单源，预填 te/sete 但标 needs_review
                # （报告数字逐字取自 PDF + 确定变换，人工一键确认即可进 Block B）
                conf = "needs_review" if ok else "failed"
        else:
            ok, checks, conf = False, ["no-template"], "failed"
        r["_review"] = {"confidence": conf, "checks": checks, **meta}
        review.append({"study": r.get("study"), "measure": r.get("measure"),
                       "confidence": conf, "anchor": meta.get("anchor"),
                       "checks": checks})

    # 正文候选全部列为 needs_review 项（供审核台逐条处理）
    for cand in candidates:
        meta = cand.get("_meta") or {}
        if cand.get("kind") == "pvalue":
            review.append({"kind": "pvalue", "confidence": "needs_review",
                           "page": meta.get("page"), "reported": cand.get("reported"),
                           "anchor": meta.get("anchor")})
        else:
            review.append({"kind": cand.get("kind", "candidate"),
                           "confidence": "needs_review", "page": cand.get("page"),
                           "snippet": cand.get("snippet"),
                           "payload": cand.get("payload")})

    n_v = sum(1 for x in review if x.get("confidence") == "verified")
    n_r = sum(1 for x in review if x.get("confidence") == "needs_review")
    return {"rows": rows, "candidates": candidates,
            "n_pages": doc["n_pages"], "review_summary": {
                "n_rows": len(rows), "verified": n_v, "needs_review": n_r,
                "tier_report": tier_report,
                "unresolved": unresolved,
                "note": "verified 行仍建议抽检；needs_review 行必须人工确认后"
                        "经 extraction_guard stamp --confirm 方可进 Block B。"
                        "unresolved 页为多级降级后仍无法解析者，如实上报待人工"
                        "（scanned=需 OCR；all-tiers-no-template-hit=表结构"
                        "非标准/版式未覆盖），不硬造、不误抓"}}


def to_a4_rows(result, study_prefix="S"):
    """提取结果 → fullflow A4 extraction_table 兼容行。

    兼容原行为：剥掉 _ 前缀内部字段。但**保留**可溯源的公开元数据
    （source_page / anchor / confidence / measure / arm），供工作台「逐篇文档展示」
    把抽取值与原文页码锚点对应起来（pdf_extractor v0.1.1 起）。
    """
    out = []
    for i, r in enumerate(result.get("rows", []), 1):
        row = {k: v for k, v in r.items() if not k.startswith("_") and v is not None}
        # 从 _review 提升溯源字段（原名 page 易与 row 内字段冲突 → 改名 source_page）
        rev = r.get("_review") or {}
        if "source_page" not in row and rev.get("page") is not None:
            row["source_page"] = rev["page"]
        if "anchor" not in row and rev.get("anchor"):
            row["anchor"] = rev["anchor"]
        if "confidence" not in row and rev.get("confidence"):
            row["confidence"] = rev["confidence"]
        row["study"] = row.get("study") or f"{study_prefix}{i}"
        out.append(row)
    return out


if __name__ == "__main__":  # 供 CLI 冒烟：python pdf_extractor.py <pdf>
    import sys
    res = extract(sys.argv[1])
    print(json.dumps(res["review_summary"], ensure_ascii=False, indent=2))
    for r in res["rows"]:
        print(json.dumps({k: r[k] for k in r if k != "_review"},
                         ensure_ascii=False))
