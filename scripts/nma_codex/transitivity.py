"""transitivity — 传递性（comparability）评估（模块 B）。定性方法论，无 R 依赖。

CODEX 对应能力 B：评估「间接比较是否公平」。本模块只产出结构化检查清单，
结论由分析者结合领域知识判读。
"""
from __future__ import annotations

from typing import Dict, List

from .schema import CuratedStudy


def assess(studies: List[CuratedStudy]) -> Dict:
    """对入网研究做传递性检查，输出结构化清单。"""
    dims = ["population", "design", "outcome", "control_type", "ta"]
    report: Dict = {"n_studies": len(studies), "dimensions": {}, "flags": []}
    for d in dims:
        vals = [getattr(s, d) for s in studies if getattr(s, d) is not None]
        uniq = sorted(set(map(str, vals)))
        report["dimensions"][d] = {"distinct": uniq, "n_distinct": len(uniq)}
        if len(uniq) > 1:
            report["flags"].append(f"{d} 跨研究不一致: {uniq}（注意比较公平性）")
    all_comps = [c for s in studies for c in s.direct_comparisons]
    report["n_direct_comparisons"] = len(all_comps)
    return report


def to_markdown(r: Dict) -> str:
    lines = [
        "### 传递性评估 (Transitivity)",
        "",
        f"- 入网研究数: {r['n_studies']}",
        f"- 直接比较对数: {r['n_direct_comparisons']}",
        "",
    ]
    for dim, info in r["dimensions"].items():
        lines.append(f"- **{dim}**: {info['n_distinct']} 类 → {info['distinct']}")
    lines.append("")
    if r["flags"]:
        lines.append("⚠️ 需关注的异质性:")
        for f in r["flags"]:
            lines.append(f"  - {f}")
    else:
        lines.append("✅ 各维度一致，网络内比较公平性良好。")
    return "\n".join(lines)
