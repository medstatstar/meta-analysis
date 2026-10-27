"""curation — 公开证据策展 + 转 coze/netmeta 长表（模块 A 与 C 衔接）。

数据来源：CT.gov / PubMed / 已发表荟萃。本模块只做「形状」转换，不搬运任何专有库。
coze NMA 与 netmeta 共同消费 arm-level 长表 (study, treat, event, n)。
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, List

from .schema import CuratedStudy


# coze / netmeta 消费的 arm-level 长表列
ARM_COLUMNS = ["study", "treat", "event", "n"]


def load_arm_table(path_or_df) -> pd.DataFrame:
    """读入 arm-level 长表，或对比级长表 (study, treat, y, se)。"""
    if isinstance(path_or_df, pd.DataFrame):
        df = path_or_df.copy()
    else:
        df = pd.read_csv(path_or_df)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def to_netmeta_arm(df: pd.DataFrame) -> pd.DataFrame:
    """规范化为 netmeta / coze 消费的 arm-level 长表。"""
    cols = set(df.columns)
    if {"study", "treat", "event", "n"}.issubset(cols):
        out = df[["study", "treat", "event", "n"]].copy()
    elif {"study", "treat", "y", "se"}.issubset(cols):
        out = df[["study", "treat", "y", "se"]].copy()
    else:
        raise ValueError(f"需要列 {ARM_COLUMNS} 或 [study,treat,y,se]，实际: {list(df.columns)}")
    return out


def curate_from_public(df: pd.DataFrame, meta: Dict | None = None) -> List[CuratedStudy]:
    """从公开证据长表生成 CuratedStudy 列表（策展层）。

    meta 用于批量补充 TA / indication / outcome 等（同一汇集分析通常共享）。
    """
    meta = meta or {}
    arm = to_netmeta_arm(df)
    studies: List[CuratedStudy] = []
    for sid, g in arm.groupby("study"):
        treats = [str(t) for t in g["treat"]]
        comps = [(treats[i], treats[j]) for i in range(len(treats)) for j in range(i + 1, len(treats))]
        n_sum = int(g["n"].sum()) if "n" in g else None
        st = CuratedStudy(
            study_id=str(sid),
            ta=meta.get("ta"),
            indication=meta.get("indication"),
            design=meta.get("design", "RCT"),
            outcome=meta.get("outcome"),
            effect_measure=meta.get("effect_measure", "OR"),
            n=n_sum,
            source=meta.get("source"),
            direct_comparisons=comps,
        )
        studies.append(st)
    return studies
