"""meta-analysis 工作台启动器。

用 coze venv 的 python（含 fastapi/uvicorn）起后端，自动打开浏览器。
后端 server.py 会自行把 adapters/ 加入 sys.path，因此 cwd 设为 workbench 目录即可。

用法：
  python launch_workbench.py            # 默认 127.0.0.1:8765
  python launch_workbench.py --port 9000
  python launch_workbench.py --host 0.0.0.0 --port 8765
"""
import os
import sys
import time
import argparse
import subprocess
import threading
import webbrowser

_HERE = os.path.dirname(os.path.abspath(__file__))
_VENV_PY = os.path.join(_HERE, "..", "coze", ".venv", "Scripts", "python.exe")


def _open_browser(url, delay=2.0):
    # 等 uvicorn 绑好端口后再开浏览器，避免首屏连接被拒。
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true",
                    help="不自动打开浏览器（仅启动后端）")
    args = ap.parse_args()

    venv_py = os.path.abspath(_VENV_PY)
    if not os.path.exists(venv_py):
        sys.exit(f"✗ 未找到 coze venv python：{venv_py}\n  请确认 adapters/coze/.venv 已建（含 fastapi/uvicorn）。")
    # 健康检查：fastapi 可用
    try:
        subprocess.run([venv_py, "-c", "import fastapi, uvicorn"],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError:
        sys.exit("✗ coze venv 缺少 fastapi/uvicorn，请先安装。")

    url = f"http://{args.host}:{args.port}/"
    print(f"▶ 启动 meta-analysis 工作台：{url}")
    print("  按 Ctrl+C 停止。")
    if not args.no_browser:
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    # 用 uvicorn 模块方式运行（server:app，cwd=workbench 使模块可解析）
    subprocess.run([venv_py, "-m", "uvicorn", "server:app",
                   "--host", args.host, "--port", str(args.port)],
                   cwd=_HERE)


if __name__ == "__main__":
    main()
