"""network — 治疗网络构建与校验（模块 C）。纯 Python，无 R 依赖。

在建网阶段（送 coze / 本地 netmeta 之前）做连通性、环、孤立节点校验，
提前暴露「网络不连通」「无间接证据路径」等会导致 NMA 失效的问题。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

import pandas as pd


def build(arm_df: pd.DataFrame) -> Dict:
    """从 arm-level 长表构建治疗网络。"""
    df = arm_df.copy()
    treatments = sorted(set(df["treat"].astype(str)))
    edges: Set[Tuple[str, str]] = set()
    for _, g in df.groupby("study"):
        ts = [str(t) for t in g["treat"]]
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = sorted([ts[i], ts[j]])
                edges.add((a, b))
    adj: Dict[str, Set[str]] = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    components = _connected_components(treatments, adj)
    loops = _find_loops(treatments, adj, max_len=4)
    orphans = [t for t in treatments if len(adj[t]) <= 1]
    return {
        "treatments": treatments,
        "edges": sorted(edges),
        "n_treatments": len(treatments),
        "n_edges": len(edges),
        "n_components": len(components),
        "connected": len(components) == 1,
        "components": components,
        "loops": loops,
        "orphan_treatments": orphans,
    }


def _connected_components(nodes: List[str], adj: Dict[str, Set[str]]) -> List[List[str]]:
    seen: Set[str] = set()
    comps: List[List[str]] = []
    for n in nodes:
        if n in seen:
            continue
        stack = [n]
        cur: Set[str] = set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            cur.add(x)
            stack.extend(adj[x] - seen)
        comps.append(sorted(cur))
    return comps


def _find_loops(nodes: List[str], adj: Dict[str, Set[str]], max_len: int = 4) -> List[List[str]]:
    """朴素环检测（长度 ≤ max_len 的简单环，起点=终点）。"""
    loops: List[List[str]] = []
    for start in nodes:
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nb in adj[node]:
                if nb == start and len(path) >= 3:
                    loops.append(path[:])
                elif nb not in path and len(path) < max_len:
                    stack.append((nb, path + [nb]))
    uniq: Set[tuple] = set()
    for lp in loops:
        if len(set(lp)) == len(lp):
            uniq.add(tuple(sorted(lp)))
    return [sorted(x) for x in uniq]


def to_markdown(net: Dict) -> str:
    lines = [
        "### 治疗网络 (Network)",
        "",
        f"- 干预数: {net['n_treatments']} | 直接比较边: {net['n_edges']}",
        f"- 连通性: {'✅ 全连通' if net['connected'] else '⚠️ 非连通 (' + str(net['n_components']) + ' 个分量)'}",
    ]
    if not net["connected"]:
        lines.append(f"  分量: {net['components']}")
    lines.append(f"- 闭合环（间接证据来源）: {net['loops']}")
    if net["orphan_treatments"]:
        lines.append(f"- ⚠️ 孤立/单连接干预: {net['orphan_treatments']}（核查是否真有间接路径）")
    return "\n".join(lines)
