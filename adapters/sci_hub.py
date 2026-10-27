#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sci_hub.py — Sci-Hub 可选兜底连接器（**默认关闭，显式开启，后果自负**）

参考 CT-literature 的 sci_hub.py 设计。适配 meta-analysis 的数据结构
（DOI 列表输入、pdf_cache/ 目录输出）。

⚠️ 合规声明：
  1. Sci-Hub 全文多数未经版权方授权，法律风险由使用者承担。
  2. 默认关闭；仅 --use-scihub 或 META_ALLOW_SCIHUB=1 时激活。
  3. 仅作最后兜底（所有合法渠道失败后）。
  4. 机构环境（GCP/申办方项目）严禁开启。
"""
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ENABLE_ENV = "META_ALLOW_SCIHUB"
DISCLAIMER = (
    "⚠️ [Sci-Hub] 兜底已启用：Sci-Hub 全文多数未经版权方授权，存在法律与合规风险，"
    "由此产生的一切后果由使用者本人承担。机构环境（GCP/申办方项目）严禁开启。"
    "可通过 --no-scihub / 取消环境变量 %s 关闭。" % ENABLE_ENV
)

DEFAULT_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ru",
    "https://sci-hub.ee",
]

_TIMEOUT = 25

_PDF_URL_RES = [
    re.compile(r"""(?:src|href)\s*=\s*["']([^"']+?\.pdf[^"']*)["']""", re.I),
    re.compile(r"""location\.href\s*=\s*["']([^"']+?\.pdf[^"']*)["']""", re.I),
]
_PDF_URL_NEG = re.compile(r"(smpl|/graphics/|thumb|_150\.|\.jpg\.pdf)", re.I)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) meta-analysis-skill/1.10 research"


def enabled(explicit=None):
    if explicit is not None:
        return bool(explicit)
    return os.environ.get(ENABLE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _mirrors():
    raw = os.environ.get("META_SCIHUB_MIRRORS", "").strip()
    if raw:
        return [m.strip().rstrip("/") for m in raw.split(",") if m.strip()]
    return list(DEFAULT_MIRRORS)


def _fetch_html(mirror, doi):
    url = "%s/%s" % (mirror.rstrip("/"), urllib.parse.quote(doi))
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def _extract_pdf_url(html, mirror):
    for rx in _PDF_URL_RES:
        for m in rx.finditer(html):
            u = m.group(1).strip()
            if not u or _PDF_URL_NEG.search(u):
                continue
            if u.startswith("//"):
                return "https:" + u
            if u.startswith("http://") or u.startswith("https://"):
                return u
            return mirror.rstrip("/") + ("" if u.startswith("/") else "/") + u
    return None


def resolve_pdf_url(doi, log=None, politeness=2.0, disclaimer=True):
    """按 DOI 依次尝试镜像，返回 PDF 直链或 None。"""
    log = log or (lambda m: None)
    if disclaimer:
        log(DISCLAIMER)
    doi = (doi or "").strip()
    if doi.lower().startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    elif doi.lower().startswith("http://doi.org/"):
        doi = doi[len("http://doi.org/"):]
    if not doi:
        return None
    for i, mirror in enumerate(_mirrors(), 1):
        try:
            log(f"[scihub] mirror {i}/{len(_mirrors())}: {mirror} ...")
            html = _fetch_html(mirror, doi)
            u = _extract_pdf_url(html, mirror)
            if u:
                log(f"[scihub] resolved via {mirror}")
                return u
            log(f"[scihub] {mirror} 返回页面但未解析到 PDF 直链")
        except urllib.error.HTTPError as e:
            log(f"[scihub] {mirror} HTTP {e.code}")
        except Exception as e:
            log(f"[scihub] {mirror} 失败: {type(e).__name__}: {e}")
        if politeness > 0 and i < len(_mirrors()):
            time.sleep(politeness)
    return None


def download_via_scihub(doi, out_path, log=None):
    """Sci-Hub 兜底下载。返回 True 当且仅当成功落盘合法 PDF。"""
    from pdf_fetch import download
    url = resolve_pdf_url(doi, log=log)
    if not url:
        return False
    return download(url, out_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print("pdf_url =", resolve_pdf_url(sys.argv[1], log=print))
    else:
        print("Usage: python sci_hub.py <doi>")
