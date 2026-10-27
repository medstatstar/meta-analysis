"""engine_dev — DEV-ONLY 本地 R(netmeta) 引擎封装（对照 coze 生产路径）。

⚠️ 生产路径为 coze-only：所有 NMA 数学在 coze 端 netmeta 完成，本地不计算。
本模块仅供「本地开发与离线验证」——用你指到的 C:\\Tools\\R4.42 跑通 netmeta 管道，
证明 coze 端调用的同一套 netmeta 调用在本地可复现。默认不进入生产路径。
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

DEFAULT_RSCRIPT = r"C:\Tools\R4.42\bin\x64\Rscript.exe"
HERE = Path(__file__).resolve().parent
R_SCRIPT = HERE / "nma_engine.R"


def run_netmeta_local(arm_df, rscript: str = DEFAULT_RSCRIPT, reference: str | None = None) -> dict:
    """用本地 netmeta 跑频率学派 NMA，返回 {treatments, league, sucra, ranks, tau2}。"""
    import pandas as pd

    if not os.path.exists(rscript):
        raise FileNotFoundError(f"本地 R 未找到: {rscript}（生产路径请用 coze）")
    tmp = tempfile.mkdtemp()
    csv = os.path.join(tmp, "arm.csv")
    arm_df.to_csv(csv, index=False)
    out_json = os.path.join(tmp, "nma_out.json")
    cmd = [rscript, str(R_SCRIPT), "--arm", csv, "--out", out_json]
    if reference:
        cmd += ["--ref", str(reference)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"netmeta 运行失败 (code={proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    with open(out_json, encoding="utf-8") as f:
        return json.load(f)
