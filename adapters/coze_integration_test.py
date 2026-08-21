# -*- coding: utf-8 -*-
"""coze_integration_test.py — meta-analysis 技能 × coze 已部署工作流 联调测试器

端点（2026-08-17 用户提供）：https://ct-meta.coze.site/run  （已发布的 coze 工作流）
鉴权：Authorization: Bearer <token>   （token 来自 adapters/coze_token 或 env COZE_META_TOKEN）
入参（Body JSON）：{task:string, data:object, params:object, figure:object}
出参（response JSON）：{result: "<结构化结果 JSON 字符串>"}

说明：
- 这与 coze 平台 OpenAPI（api.coze.cn/v1/workflow/run，需 pat_ 令牌 + workflow_id 包装）不同；
  本端点是已发布工作流的自定义域名入口，使用用户提供的长期令牌（Bearer）直接调用即可。
- 工作流执行建议控制在 5 分钟内；本脚本单次超时设为 300s。
- 网络不可达 / 401 等会如实打印，不静默吞错。

用法：
  python coze_integration_test.py                 # 跑 coze_cases/ 下全部 *.json 案例
  python coze_integration_test.py --cases <dir>  # 指定案例目录
  python coze_integration_test.py --endpoint <url> # 覆盖端点（默认 https://ct-meta.coze.site/run）
  python coze_integration_test.py --only case1    # 只跑文件名含 case1 的案例
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request

# ---- 凭据解析（与 coze_client 同优先级：env > 内嵌 blob；本地 .dat 曾用于覆盖，发布后被剥） ----
try:
    from coze_token import get_token as _embedded_get_token
except Exception:  # 平铺运行
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from coze_token import get_token as _embedded_get_token
    except Exception:
        _embedded_get_token = None

DEFAULT_ENDPOINT = "https://ct-meta.coze.site/run"
DEFAULT_CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coze_cases")
REQUEST_TIMEOUT = 300  # 秒（coze 建议单次 5 分钟内）


def resolve_token() -> str:
    env = os.environ.get("COZE_META_TOKEN")
    if env:
        return env
    if _embedded_get_token is not None:
        return _embedded_get_token() or ""
    return ""


def _post(url: str, token: str, payload: dict) -> tuple[int, str, float]:
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            return r.status, r.read().decode("utf-8"), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore"), time.time() - t0
    except Exception as e:  # 网络层 / 超时
        return -1, repr(e), time.time() - t0


def extract_result(resp_text: str) -> dict:
    """response 可能是 {result:"<json>"} 或直接就是结构化结果对象。"""
    try:
        resp = json.loads(resp_text)
    except Exception:
        return {"_raw": resp_text[:800]}
    if isinstance(resp, dict) and "result" in resp:
        r = resp["result"]
        if isinstance(r, str):
            try:
                return json.loads(r)
            except Exception:
                return {"_result_str": r[:800]}
        if isinstance(r, dict):
            return r
        return {"_result": r}
    # 直接是结构化结果
    if isinstance(resp, dict):
        return resp
    return {"_raw": resp_text[:800]}


def run_one(url: str, token: str, envelope: dict) -> dict:
    code, raw, el = _post(url, token, envelope)
    rec = {"http_code": code, "elapsed_s": round(el, 1)}
    if code != 200:
        rec["ok"] = False
        rec["error"] = raw[:800]
        return rec
    result = extract_result(raw)
    rec["ok"] = True
    rec["result"] = result
    return rec


def summarize(name: str, rec: dict) -> str:
    bar = "=" * 64
    head = f"[{name}]  HTTP {rec.get('http_code')}  耗时 {rec.get('elapsed_s')}s"
    if not rec.get("ok"):
        return f"{bar}\n{head}\n❌ 调用失败: {rec.get('error', '')[:400]}\n{bar}"
    r = rec.get("result", {})
    if not isinstance(r, dict):
        return f"{bar}\n{head}\n结果非结构化: {str(r)[:300]}\n{bar}"
    status = r.get("status")
    lines = [head, f"status={status}  task={r.get('task')}"]
    if status == "ok":
        stats = r.get("stats") or {}
        pooled = stats.get("pooled") or {}
        het = stats.get("heterogeneity") or {}
        if pooled.get("estimate") is not None:
            unit = pooled.get("unit", "")
            lines.append(f"  合并效应={pooled.get('estimate')} "
                         f"({pooled.get('ci_low')}, {pooled.get('ci_high')}) {unit}")
        if het:
            lines.append(f"  异质性: I2={het.get('I2')}  tau2={het.get('tau2')}  "
                         f"H={het.get('H')}  Q_p={het.get('Q_p')}")
        figs = r.get("figures") or []
        if figs:
            desc = []
            for f in figs:
                svg = f.get("svg") or ""
                txt = f.get("text") or ""
                sz = len(svg) if svg else (len(txt) if txt else 0)
                kind = "svg" if svg else ("text" if txt else "?")
                desc.append(f"{f.get('type')}:{sz}B/{kind}")
            lines.append("  图形=" + ", ".join(desc))
        if r.get("warnings"):
            lines.append("  ⚠ warnings=" + "; ".join(map(str, r["warnings"])))
        notes = r.get("notes")
        if notes:
            lines.append("  notes=" + str(notes)[:800])
    else:
        lines.append("  ⚠ notes=" + str(r.get("notes", ""))[:800])
        if r.get("error"):
            lines.append("  error=" + str(r.get("error"))[:400])
    return f"{bar}\n" + "\n".join(lines) + f"\n{bar}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=DEFAULT_CASES_DIR)
    ap.add_argument("--endpoint", default=os.environ.get("COZE_META_ENDPOINT", DEFAULT_ENDPOINT))
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    token = resolve_token()
    if not token:
        print("❌ 无法解析 coze token（env COZE_META_TOKEN 与内嵌 blob 皆空）。")
        return 2
    print(f"端点: {args.endpoint}")
    print(f"token: Bearer {token[:18]}…{token[-12:]}  (len={len(token)})")

    files = sorted(glob.glob(os.path.join(args.cases, "*.json")))
    if args.only:
        files = [f for f in files if args.only in os.path.basename(f)]
    if not files:
        print(f"❌ 在 {args.cases} 下未找到案例 JSON。")
        return 2
    print(f"案例数: {len(files)}\n")

    # 读取 MANIFEST.csv（若有）：status=expected 的案例属已知环境限制，error 视为豁免（对齐 ct-base §18.5/§18.6）
    expected_names = set()
    mani = os.path.join(args.cases, "MANIFEST.csv")
    if os.path.exists(mani):
        with open(mani, encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 7 and row[6] == "expected":
                    expected_names.add(row[5])
    if expected_names:
        print(f"MANIFEST expected 豁免: {len(expected_names)} 例\n")

    fails = 0
    for fp in files:
        name = os.path.basename(fp)
        try:
            envelope = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            print(f"[{name}] ❌ 案例 JSON 解析失败: {e}")
            fails += 1
            continue
        print(f"\n>>> 运行案例 {name}  (task={envelope.get('task')})")
        rec = run_one(args.endpoint, token, envelope)
        print(summarize(name, rec))
        # 判分（对齐 ct-base §18.4）：ok / warn / None 通过；expected 案例 error 豁免
        status = rec.get("result", {}).get("status") if rec.get("ok") else None
        if not rec.get("ok") or status not in ("ok", "warn", None):
            if name in expected_names:
                print(f"  （expected 环境限制，豁免，不计失败）")
                continue
            fails += 1

    print(f"\n{'#' * 64}")
    print(f"联调完成：{len(files)} 个案例，失败 {fails} 个。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
