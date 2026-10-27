"""CuratedStudy — CODEX 形状的证据策展 schema（模块 A）。

仅借 CODEX 的「研究记录字段形状」，不灌其专有数据。
所有数据来自 CT.gov / PubMed / 已发表荟萃（公开、可复现、零成本）。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


@dataclass
class CuratedStudy:
    """一条策展研究记录。字段设计对标 CODEX 的研究级结构化入库形态。"""

    study_id: str
    year: Optional[int] = None
    ta: Optional[str] = None                 # therapeutic area / 适应症大类
    indication: Optional[str] = None         # 具体适应症
    design: str = "RCT"                      # RCT / observational / RCT-multiarm
    population: Optional[str] = None         # 受试人群（入排标准摘要）
    intervention: Optional[str] = None       # 试验药
    comparator: Optional[str] = None         # 对照药
    control_type: Optional[str] = None       # placebo / active
    outcome: Optional[str] = None            # 主要终点
    effect_measure: str = "OR"               # OR / RR / HR / SMD（对数尺度优先）
    effect_size: Optional[float] = None      # 已取对数
    se: Optional[float] = None
    n: Optional[int] = None                  # 样本量
    baseline_chars: Dict[str, float] = field(default_factory=dict)   # 基线特征（如 age_mean）
    risk_of_bias: Optional[str] = None
    source: Optional[str] = None             # pubmed id / NCT id / citation
    direct_comparisons: List[Tuple[str, str]] = field(default_factory=list)  # [(t1,t2), ...]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["direct_comparisons"] = [list(p) for p in self.direct_comparisons]
        return d
