#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_fetch.py — 文献全文 PDF 批量下载（DOI / PMID → 开放获取全文）

对应 SKILL.md Review Workflow「PDF Batch-download」功能（2026-08-20 补实现）。
⚠️ **opt-in 功能**：仅在用户明确要求（给出 DOI/PMID 列表并确认下载）时由 agent 调用。

数据源（免费、无密钥）：
  - DOI  → Unpaywall API（https://api.unpaywall.org/v2/<doi>?email=<EMAIL>），取
          best_oa_location.url_for_pdf；无 OA 副本则如实报告（不绕过付费墙）。
  - PMID → NCBI E-utilities elink（pubmed→pmc）+ PMC 全文 PDF 直链。

用法：
  python pdf_fetch.py doi 10.1016/j.jclinepi.2024.01.001 10.1136/bmj-2023-076058
  python pdf_fetch.py pmid 38268826 37849447
  python pdf_fetch.py doi --input list.txt --out pdfs/        # 从文件读（每行一个 ID）
  python pdf_fetch.py doi --email you@example.com 10.xxxx/yy  # 指定 Unpaywall email

输出：下载的 PDF 保存到 out_dir（默认 ./pdfs/），stdout 打印清单（含失败原因）。

纯标准库（urllib），零第三方依赖。网络失败不阻塞，逐条独立重试。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

DEFAULT_EMAIL = "meta-analysis@example.com"  # Unpaywall 要求合法 email，可 --email 覆盖


def _get(url: str, timeout: int = 30, retries: int = 2) -> bytes:
    """GET 带重试（跳过系统代理残留：Windows ProxyError → 直连）。"""
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meta-analysis-skill/1.10"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 429):
                time.sleep(1)
                last = f"HTTP {e.code}"
                continue
            raise
        except Exception as e:  # URLError / ProxyError 等
            last = f"{type(e).__name__}: {e}"
            time.sleep(0.5)
    raise RuntimeError(str(last))


def doi_to_pdf(doi: str, email: str) -> str | None:
    """Unpaywall：返回可下载 PDF URL；无 OA 副本返回 None。"""
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={urllib.parse.quote(email)}"
    try:
        raw = _get(url)
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Unpaywall 查询失败: {e}")
    if not data.get("is_oa"):
        return None
    loc = data.get("best_oa_location") or {}
    pdf = loc.get("url_for_pdf") or loc.get("url")
    return pdf


def pmid_to_pdf(pmid: str) -> str | None:
    """PMID → PMC 全文 PDF 直链（经 NCBI elink）。"""
    elink = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
             f"?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json")
    try:
        data = json.loads(_get(elink).decode("utf-8"))
        links = data.get("linksets", [{}])[0].get("linksetdbs", [])
        pmc_ids = []
        for lsdb in links:
            pmc_ids.extend(lsdb.get("links", []))
        if not pmc_ids:
            return None
        pmcid = pmc_ids[0]
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    except Exception:
        return None


def _sanitize(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", name)[:80] or "download"


def download(url: str, out_path: str) -> bool:
    try:
        data = _get(url, timeout=60)
        with open(out_path, "wb") as f:
            f.write(data)
        return len(data) > 1000  # 粗略校验：PDF 至少 ~1KB
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="DOI/PMID → 开放获取全文 PDF 批量下载（opt-in）")
    ap.add_argument("idtype", choices=["doi", "pmid"], help="ID 类型")
    ap.add_argument("ids", nargs="*", help="DOI 或 PMID（也可 --input 文件逐行读取）")
    ap.add_argument("--input", help="从文件逐行读取 ID（每行一个）")
    ap.add_argument("--out", default="pdfs", help="输出目录（默认 ./pdfs）")
    ap.add_argument("--email", default=DEFAULT_EMAIL, help="Unpaywall 查询邮箱")
    a = ap.parse_args()

    ids = list(a.ids)
    if a.input:
        with open(a.input, encoding="utf-8") as f:
            ids += [ln.strip() for ln in f if ln.strip()]
    if not ids:
        ap.error("请提供至少一个 ID（或 --input 文件）")
    os.makedirs(a.out, exist_ok=True)

    print(f"== 开始下载 {len(ids)} 篇全文（{a.idtype}，目标 {a.out}）==")
    ok, fail = 0, 0
    for i, ident in enumerate(ids, 1):
        try:
            pdf_url = doi_to_pdf(ident, a.email) if a.idtype == "doi" else pmid_to_pdf(ident)
            if not pdf_url:
                print(f"[{i}/{len(ids)}] {ident}  → 无开放获取全文（跳过）")
                fail += 1
                continue
            out = os.path.join(a.out, f"{_sanitize(ident)}.pdf")
            if download(pdf_url, out):
                print(f"[{i}/{len(ids)}] {ident}  → OK  {out}")
                ok += 1
            else:
                print(f"[{i}/{len(ids)}] {ident}  → 下载失败或文件过小（{pdf_url}）")
                fail += 1
        except Exception as e:
            print(f"[{i}/{len(ids)}] {ident}  → 错误: {e}")
            fail += 1
    print(f"== 完成：成功 {ok} / 失败 {fail} ==")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
