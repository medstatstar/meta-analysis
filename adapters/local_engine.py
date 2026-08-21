"""
adapters/local_engine.py — 本地 R 兜底引擎（coze 不可用 / 用户明确要求时）

当 coze 工作流不可用，或用户明确要求"本地分析 / 离线"时，本模块在用户本机直接调用
技能内置的 R 引擎（r_engine/run_task.R，与 coze 项目 src/r_engine/ **同源**，靠
coze_contract.md 保持同步）完成数值计算。

接口信封与 coze_client 完全一致（task/data/params/figure → {status, stats, figures[], ...}），
因此上层（adapters/run_analysis.py）无需区分来源即可统一处理。

行为：
- 默认从 <skill>/r_engine/ 调用 run_task.R。
- 可用环境变量覆盖：
    META_LOCAL_ENGINE_DIR  本地引擎目录（含 run_task.R）
    RSCRIPT_PATH           Rscript 可执行文件路径（默认 "Rscript"，依赖 PATH）
- 仅依赖标准库（subprocess / json / os / tempfile / shutil）。

⚠️ 本地引擎需本机装有 R 及 15 核心包（metafor/meta/netmeta/...）；缺包 task 由
run_task.R 的 .need_pkg 守卫返回 warning，不崩溃。
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))


def _engine_dir() -> str:
    # 2026-08-19 镜像统一：默认指向 adapters/coze_project/src/r_engine（coze 远端双向同步唯一源）；
    # 允许环境变量覆盖（多机/自定义部署）
    return os.environ.get(
        "META_LOCAL_ENGINE_DIR",
        os.path.join(_HERE, "coze_project", "src", "r_engine"),
    )


def _rscript() -> str:
    return os.environ.get("RSCRIPT_PATH", "Rscript")


def run_meta(task: str, data: dict, params: dict | None = None,
             figure: dict | None = None) -> dict:
    """本地调用 R 引擎完成分析。成功返回结果 dict（含 _source="local"）；失败抛 RuntimeError。"""
    eng = _engine_dir()
    run_task = os.path.join(eng, "run_task.R")
    if not os.path.isfile(run_task):
        raise RuntimeError(
            f"本地 R 引擎缺失：{run_task}（请确认 adapters/coze_project/src/r_engine/ 完整，或设置 META_LOCAL_ENGINE_DIR）"
        )
    # 2026-08-20 设计收紧（与 coze_client 一致）：本地引擎同样只产 SVG，
    # 强制 figure.format="svg"；PNG 由本地呈现层 rendering.svg_to_png 转换。
    fig = dict(figure or {})
    fig["format"] = "svg"
    req = {"task": task, "data": data or {}, "params": params or {}, "figure": fig}
    d = tempfile.mkdtemp(prefix="ma_local_")
    try:
        inp = os.path.join(d, "input.json")
        outp = os.path.join(d, "output.json")
        with open(inp, "w", encoding="utf-8") as f:
            json.dump(req, f, ensure_ascii=False)
        p = subprocess.run(
            [_rscript(), run_task, "--input", inp, "--output", outp],
            capture_output=True, text=True, timeout=600, cwd=eng,
        )
        if not os.path.exists(outp):
            raise RuntimeError(
                f"本地 R 引擎无输出（退出码 {p.returncode}）。stderr 末尾：\n"
                + (p.stderr or "")[-800:]
            )
        with open(outp, encoding="utf-8") as f:
            res = json.load(f)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    if res.get("status") == "error":
        raise RuntimeError("本地 R 引擎返回错误：" + str(res.get("notes", ""))[:600])
    res["_source"] = "local"
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python local_engine.py <request.json>")
        sys.exit(2)
    req = json.load(open(sys.argv[1], encoding="utf-8"))
    out = run_meta(req.get("task"), req.get("data"), req.get("params"), req.get("figure"))
    print(json.dumps(out, ensure_ascii=False, indent=2)[:3000])
