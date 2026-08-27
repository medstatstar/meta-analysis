#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_topic_report.py — Meta-analysis topic-selection report generator.

Reads a topic-assessment JSON (schema: references/topic-selection.md "Output
contract") and renders an 11-section Markdown or HTML report.

Usage:
    python generate_topic_report.py input.json output.md
    python generate_topic_report.py input.json output.html
    python generate_topic_report.py input.json output.md --format html
    python generate_topic_report.py input.json -            # stdout

Python 3.8+ standard library only. No third-party dependencies.
"""

import argparse
import html
import json
import sys
from datetime import date


# ---------------------------------------------------------------------------
# Verdict mapping
# ---------------------------------------------------------------------------

VERDICT_ZH = {
    "strongly_recommend": "强烈建议",
    "recommend": "建议",
    "hold": "暂缓",
    "not_recommended": "不建议",
    "veto": "一票否决",
}

RISK_ZH = {"green": "🟢 低", "yellow": "🟡 中", "red": "🔴 高"}


def verdict_label(v):
    if not v:
        return "—"
    if isinstance(v, str) and v.startswith("veto:"):
        return "一票否决 (veto)"
    return VERDICT_ZH.get(v, v)


def risk_label(r):
    if isinstance(r, dict):
        r = r.get("overall_risk", r.get("risk", "yellow"))
    return RISK_ZH.get(r, r or "—")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _g(d, key, default=""):
    """Safely get a nested value."""
    if d is None:
        return default
    return d.get(key, default)


def _fmt_list(items, sep="; "):
    """Render a list/tuple/string as a joined string."""
    if items is None:
        return ""
    if isinstance(items, str):
        return items
    if isinstance(items, (list, tuple)):
        return sep.join(str(x) for x in items if x not in (None, ""))
    return str(items)


def _fmt_bullets(items):
    """Render a list as Markdown bullets; dict items -> '**key**: value'."""
    if not items:
        return ""
    if isinstance(items, str):
        return "- " + items
    out = []
    for it in items:
        if isinstance(it, dict):
            parts = [f"**{k}**: {v}" for k, v in it.items() if v not in (None, "")]
            out.append("- " + "; ".join(parts))
        else:
            out.append("- " + str(it))
    return "\n".join(out)


def _md_table(headers, rows):
    """Render a Markdown table from headers + list-of-lists rows."""
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        cells = [str(c) if c is not None else "" for c in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def _pico_table(pico):
    """Render PICO table from pico dict."""
    p = pico or {}
    st = p.get("search_terms", {})
    rows = [
        ["P", p.get("P", ""), st.get("P", "")],
        ["I/E", p.get("I", ""), st.get("I", "")],
        ["C", p.get("C", ""), st.get("C", "")],
        ["O", p.get("O", ""), st.get("O", "")],
    ]
    table = _md_table(["Element", "Definition", "Search terms"], rows)
    if st.get("filters"):
        table += "\n\nFilters: " + str(st["filters"])
    return table


def _score_table(scores, anchors):
    """Render the four-dimension score table."""
    s = scores or {}
    a = anchors or {}
    rows = [
        ["Clinical value", s.get("clinical", "—"), a.get("clinical", "")],
        ["Methodological feasibility", s.get("feasibility", "—"), a.get("feasibility", "")],
        ["Data availability", s.get("data", "—"), a.get("data", "")],
        ["Novelty", s.get("novelty", "—"), a.get("novelty", "")],
    ]
    total = s.get("total", "—")
    return _md_table(["Dimension", "Score /5", "Anchor reason"], rows) + \
        f"\n\n**Total**: {total}/20 — 评分规则: ≥17 强烈建议 / ≥14 建议 / ≥10 暂缓 / <10 不建议; 任一维 ≤2 一票否决"


def _cross_check_summary(checks):
    """Summarize R1-R6 cross-check results."""
    if not checks:
        return "未记录 (Full 模式必须运行 R1–R6)"
    fired = [c for c in checks if c.get("triggered")]
    if not fired:
        return "R1–R6 全部通过 (无规则触发)"
    parts = [f"{c.get('rule')} 触发 → {c.get('note', '已重审')}" for c in fired]
    return "; ".join(parts)


def _compliance_sections(comp):
    """Render PRISMA + AMSTAR-2 rows from compliance dict."""
    comp = comp or {}
    prisma_rows = ""
    for item in comp.get("prisma", []):
        prisma_rows += f"| {item.get('item', '')} | {item.get('status', '')} | {item.get('note', '')} |\n"
    amstar_rows = ""
    for dom in comp.get("amstar2", []):
        amstar_rows += f"| {dom.get('domain', '')} | {dom.get('status', '')} | {dom.get('note', '')} |\n"
    return prisma_rows, amstar_rows


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _sec(num, title, body):
    return f"\n---\n\n## {num}. {title}\n\n{body}"


def build_markdown(d):
    """Build the full 11-section Markdown report."""
    pico = _pico_table(d.get("pico"))
    scores = _score_table(d.get("scores"), d.get("score_anchors"))
    cc = _cross_check_summary(d.get("cross_checks"))
    prisma_rows, amstar_rows = _compliance_sections(d.get("compliance"))
    comp = d.get("compliance") or {}
    dedup = d.get("dedup") or {}
    pros = d.get("prospero") or {}

    sections = [
        f"# {d.get('title', 'Untitled')}\n\n"
        f"**Slug**: `{d.get('slug', '')}` | **Date**: {d.get('date', '')} | "
        f"**Path**: {d.get('path', '')}\n\n"
        f"**Verdict**: **{verdict_label(d.get('verdict'))}** "
        f"(total {_g(d.get('scores'), 'total', '—')}/20)",
        _sec(1, "Background & Rationale", d.get("background", "")),
        _sec(2, "PICO/PECO Decomposition", pico),
        _sec(3, "Meta Type & Rationale",
             f"**Type**: {d.get('meta_type', '—')}\n\n{d.get('meta_type_rationale', '')}"),
        _sec(4, "Four-Dimension Assessment", f"{scores}\n\n**Cross-check rules (R1–R6)**: {cc}"),
        _sec(5, "Dedup Search Report",
             _md_table(["Layer", "Result"], [
                 ["PROSPERO", dedup.get("prospero", "")],
                 ["Cochrane", dedup.get("cochrane", "")],
                 ["PubMed (5y)", dedup.get("pubmed", "")],
                 ["Non-English", dedup.get("non_english", "")],
             ]) + f"\n\nNear-duplicate: **{dedup.get('near_duplicate', '')}**\n\n"
                  f"**Increment**: {dedup.get('increment', '')}"),
        _sec(6, "Search Strategy & Expected Yield",
             f"{d.get('search_strategy', '')}\n\nExpected studies: {d.get('expected_studies', '')}"),
        _sec(7, "PRISMA 2020 / AMSTAR-2 Pre-check",
             "**PRISMA 2020 key items**:\n\n| Item | Status | Note |\n|---|---|---|\n" + prisma_rows +
             "\n**AMSTAR-2 critical domains**:\n\n| Domain | Status | Note |\n|---|---|---|\n" + amstar_rows +
             f"\n**Overall compliance risk**: {risk_label(comp)} — {comp.get('note', '')}"),
        _sec(8, "Primary Outcomes & Effect Measures", _fmt_bullets(d.get("outcomes"))),
        _sec(9, "Pre-specified Subgroups & Sensitivity",
             f"Subgroups: {_fmt_list(d.get('subgroups'))}\n\nSensitivity: {_fmt_list(d.get('sensitivity'))}"),
        _sec(10, "Potential Risks & Mitigations", _fmt_bullets(d.get("risks"))),
        _sec(11, "Recommended Next Actions", _fmt_bullets(d.get("next_actions"))),
    ]

    # PROSPERO mapping appendix (conditional)
    if pros.get("ready") or pros.get("mapping_note"):
        missing = _fmt_list(pros.get("missing")) or "none"
        sections.append(_sec("A", "PROSPERO Registration Mapping",
                             f"Ready: {pros.get('ready', '—')} | Missing: {missing}\n\n"
                             f"{pros.get('mapping_note', '')}"))

    body = "\n".join(sections)
    body += ("\n\n---\n\n*Generated by meta-analysis skill — topic selection module. "
             "Sources: PRISMA 2020 (BMJ 2021;372:n71), AMSTAR-2 (BMJ 2017;358:j4008), "
             "Cochrane Handbook v6.x.*")
    return body


def build_quick_card(d):
    """Quick assessment: 1-page decision card (not a full report)."""
    s = d.get("scores") or {}
    lines = [
        f"# Quick Assessment — {d.get('title', 'Untitled')}",
        "",
        f"**Date**: {d.get('date', '')} | **Slug**: `{d.get('slug', '')}`",
        "",
        "| Dimension | Score /5 |",
        "|---|---|",
        f"| Clinical value | {s.get('clinical', '—')} |",
        f"| Methodological feasibility | {s.get('feasibility', '—')} |",
        f"| Data availability | {s.get('data', '—')} |",
        f"| Novelty | {s.get('novelty', '—')} |",
        f"| **Total** | **{s.get('total', '—')}/20** |",
        "",
        f"**Verdict (screen only)**: {verdict_label(d.get('verdict'))}",
        "",
        f"**Key risks**: {_fmt_list(d.get('key_risks')) or '—'}",
        "",
        "> ⚠️ Quick assessment is a screen, NOT a final go/no-go. "
        "Recommend Full assessment if any dimension is ⚠️/❌ or verdict is hold/veto.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _html_escape(s):
    # 标准库 html.escape：完整转义 & < > 及引号（quote=True），避免手动 replace 漏引号
    return html.escape(str(s), quote=True)


def md_to_html(md):
    """Minimal Markdown → HTML for report display (headings, tables, bold, lists)."""
    out = []
    in_table = False
    for line in md.splitlines():
        s = _html_escape(line)
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not in_table:
                out.append("<table>")
                in_table = True
            if set(cells) <= {"---", ""}:
                continue
            tag = "th" if (in_table and len(out) and "<table>" in out[-1] or len(out) == 0) else "td"
            # crude: first row after table start = header
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        else:
            if in_table:
                out.append("</table>")
                in_table = False
            if s.startswith("### "):
                out.append(f"<h3>{s[4:]}</h3>")
            elif s.startswith("## "):
                out.append(f"<h2>{s[3:]}</h2>")
            elif s.startswith("# "):
                out.append(f"<h1>{s[2:]}</h1>")
            elif s.startswith("> "):
                out.append(f"<blockquote>{s[2:]}</blockquote>")
            elif s.startswith("- ") or s.startswith("* "):
                out.append(f"<li>{s[2:]}</li>")
            elif s.strip() == "---":
                out.append("<hr>")
            elif s.strip() == "":
                out.append("<br>")
            else:
                s2 = s.replace("**", "<strong>", 1)
                # naive alternating bold
                parts = s.split("**")
                if len(parts) > 1:
                    s2 = parts[0] + "".join(
                        (f"<strong>{p}</strong>" if i % 2 else p) for i, p in enumerate(parts[1:], 1)
                    )
                out.append(f"<p>{s2}</p>")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


def build_html(d):
    md = build_markdown(d) if d.get("path") != "quick" else build_quick_card(d)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html_escape(d.get('title', 'Topic Report'))}</title>
<style>
body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
       max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #222; line-height: 1.65; }}
h1 {{ font-size: 1.5rem; border-bottom: 2px solid #4a7; padding-bottom: .4rem; }}
h2 {{ font-size: 1.15rem; margin-top: 1.8rem; color: #164; }}
table {{ border-collapse: collapse; width: 100%; margin: .6rem 0; }}
th, td {{ border: 1px solid #ccc; padding: .35rem .55rem; font-size: .9rem; text-align: left; }}
th {{ background: #eef7f2; }}
blockquote {{ border-left: 4px solid #4a7; margin: .5rem 0; padding: .3rem .8rem;
             background: #f6fbf8; color: #345; }}
hr {{ border: none; border-top: 1px dashed #bbb; margin: 1.2rem 0; }}
code {{ background: #f4f4f4; padding: .1rem .3rem; border-radius: 3px; }}
</style>
</head>
<body>
{md_to_html(md)}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Topic-selection report generator (11 sections).")
    ap.add_argument("input", help="input JSON file")
    ap.add_argument("output", help="output file (.md/.html) or '-' for stdout")
    ap.add_argument("--format", choices=["md", "html", "auto"], default="auto",
                    help="output format (default: auto-detect from extension)")
    args = ap.parse_args(argv)

    try:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"ERROR: input not found: {args.input}")
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: invalid JSON in {args.input}: {e}")

    fmt = args.format
    if fmt == "auto":
        fmt = "html" if args.output.lower().endswith((".html", ".htm")) else "md"

    if data.get("path") == "quick":
        body = build_quick_card(data)
    else:
        body = build_markdown(data)

    if fmt == "html":
        body = build_html(data)

    if args.output == "-":
        sys.stdout.write(body + "\n")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(body + "\n")
        print(f"OK wrote {args.output} ({fmt})")


if __name__ == "__main__":
    main()
