"""nma_codex — meta-analysis 技能内 CODEX 对齐的 NMA 模块骨架。

定位（对照 meta_analysis_nma_vs_codex.md / ct-base/references）：
- 本包只做 CODEX 方法论的「前端脚手架」：证据策展(A)、传递性(B)、网络构建(C)、报告(I)。
- 数学引擎（NMA 拟合 D / 节点分裂 F / SUCRA G）归属 netmeta（coze 生产路径）。
- engine_dev 为 DEV-ONLY 本地验证器，默认不进入生产路径（生产走 coze）。

红线：仅借结构/方法；不爬 CODEX 13,500 研究、不搬运患者级数据、不冒充其 UI。
"""
from .schema import CuratedStudy
from . import curation, transitivity, network, report, engine_dev

__all__ = ["CuratedStudy", "curation", "transitivity", "network", "report", "engine_dev"]
