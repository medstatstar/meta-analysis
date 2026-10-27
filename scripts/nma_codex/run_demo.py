"""run_demo — 端到端演示（模块 A → C → D → I）。

跑通：公开证据长表 → 策展 → 网络校验 → 传递性 → [dev] 本地 netmeta 拟合 → CODEX 风格报告。
生产环境第 4 步应替换为 coze 端 netmeta（见 README）。
"""
from __future__ import annotations

import os

from . import curation, network, transitivity, report, engine_dev

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_CSV = os.path.join(HERE, "demo_data.csv")
REPORT_OUT = os.path.join(HERE, "nma_codex_demo_report.md")


def _placeholder_results(net: dict) -> dict:
    ts = net["treatments"]
    return {"treatments": ts, "league": {}, "sucra": {t: 0.5 for t in ts}, "ranks": {t: 0.5 for t in ts}}


def run(use_local_r: bool = True) -> str:
    df = curation.load_arm_table(DEMO_CSV)
    arm = curation.to_netmeta_arm(df)
    studies = curation.curate_from_public(
        arm, meta={"ta": "Oncology", "indication": "NSCLC", "outcome": "OS", "effect_measure": "OR"}
    )
    net = network.build(arm)
    trans = transitivity.assess(studies)

    results = None
    if use_local_r:
        try:
            results = engine_dev.run_netmeta_local(arm)
        except Exception as e:  # 本地 R/netmeta 不可用时退回占位，仍演示报告模板
            print(f"[dev] 本地 R/netmeta 不可用: {e}\n→ 使用占位结果演示报告模板。")
            results = _placeholder_results(net)
    else:
        results = _placeholder_results(net)

    md = report.render(results, net, trans, evidence_notes="")
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write(md)
    return md


if __name__ == "__main__":
    print(run())
