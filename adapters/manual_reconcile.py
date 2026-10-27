#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manual_reconcile.py — needs_manual.csv 导出 + manual_incoming 回传归位。

适配 meta-analysis 的 pdf_cache/ 目录结构（DOI 前缀命名，如 doi_10_1038_s41586-021-03819-2.pdf）。
从 CT-literature 的 manual_reconcile.py 裁剪，移除对 pdf_download 的深度校验依赖（meta-analysis
的 pdf_fetch.py 无 _pdf_is_valid / _pdf_meta，用简化校验替代）。
"""
import json
import os
import re
import csv

VIA = "manual_incoming"
VIA_LABEL = "手动回传(机构权限)"
VIA_TRUST = "高"

_DOI_FILENAME_RE = re.compile(r"(10\.\d{4,9})[._\- ](.+?)(?:\.pdf)?$", re.I)
_DOI_TEXT_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:", "doi.org/")


def _norm_doi(doi: str) -> str:
    d = (doi or "").strip().lower()
    for p in _DOI_PREFIXES:
        if d.startswith(p):
            d = d[len(p):]
    return d.strip().rstrip(".,;")


def _doi_from_filename(stem: str) -> str:
    m = _DOI_FILENAME_RE.search(stem)
    if not m:
        return ""
    return _norm_doi(f"{m.group(1)}/{m.group(2)}")


def _doi_from_pdf_text(path: str) -> str:
    text = ""
    try:
        try:
            from pypdf import PdfReader
            with open(path, "rb") as f:
                r = PdfReader(f)
                text = "\n".join((p.extract_text() or "") for p in r.pages[:2])
        except ImportError:
            import fitz
            with fitz.open(path) as doc:
                text = "\n".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
    except Exception:
        return ""
    m = _DOI_TEXT_RE.search(text or "")
    return _norm_doi(m.group(1)) if m else ""


def _safe_filename(doi: str) -> str:
    safe = re.sub(r"[^\w.]", "_", doi)[:80]
    return f"doi_{safe}.pdf"


# ── ① needs_manual.csv 导出 ──

def export_needs_manual(works, base_dir, log=None) -> str:
    """导出仍需手动回传的 DOI 列表。"""
    log = log or (lambda m: None)
    rows = []
    for w in works or []:
        if w.get("local_pdf_path"):
            continue
        doi = (w.get("doi") or "").strip()
        if not doi:
            continue
        note = w.get("pdf_download_note") or ""
        if note.startswith("no DOI") or "non-OA" in note or "rejected" in note:
            continue
        rows.append([
            (w.get("title") or "")[:120],
            doi,
            f"https://doi.org/{doi}",
            note or "OA/预印本/云端解码均未命中",
        ])
    if not rows:
        return ""
    try:
        path = os.path.join(base_dir, "needs_manual.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            wcsv = csv.writer(f)
            wcsv.writerow(["题名", "DOI", "深链(机构权限浏览器打开)", "失败原因"])
            wcsv.writerows(rows)
        log(f"[OK] needs_manual.csv 已生成（{len(rows)} 篇待手动回传） -> {path}")
        return os.path.abspath(path)
    except Exception as e:
        log(f"[WARN] needs_manual.csv 生成失败: {type(e).__name__}: {e}")
        return ""


# ── ② reconcile ──

def _pdf_size_kb(path):
    try:
        return round(os.path.getsize(path) / 1024, 1)
    except OSError:
        return None


def _pdf_pages(path):
    try:
        try:
            from pypdf import PdfReader
            with open(path, "rb") as f:
                return len(PdfReader(f).pages)
        except ImportError:
            import fitz
            with fitz.open(path) as doc:
                return doc.page_count
    except Exception:
        return None


def reconcile_manual(out_dir: str, works: list, log=None) -> dict:
    """扫描 <out_dir>/pdf_cache/manual_incoming/*.pdf，按 DOI 匹配并归位。"""
    log = log or (lambda m: None)
    pdf_dir = os.path.join(out_dir, "pdf_cache")
    incoming = os.path.join(pdf_dir, "manual_incoming")
    stats = {"incoming": 0, "matched": 0, "unmatched": 0, "invalid": 0, "no_doi": 0}
    if not os.path.isdir(incoming):
        return stats

    by_doi = {}
    for w in works or []:
        d = _norm_doi(w.get("doi") or "")
        if d and not w.get("local_pdf_path"):
            by_doi[d] = w

    for fn in sorted(os.listdir(incoming)):
        src = os.path.join(incoming, fn)
        if not fn.lower().endswith(".pdf") or not os.path.isfile(src):
            continue
        stats["incoming"] += 1
        try:
            with open(src, "rb") as f:
                if f.read(5) != b"%PDF-":
                    stats["invalid"] += 1
                    log(f"[reconcile] 非 PDF（疑似登录页/验证页），跳过: {fn}")
                    continue
        except OSError:
            stats["invalid"] += 1
            continue
        doi = _doi_from_filename(os.path.splitext(fn)[0]) or _doi_from_pdf_text(src)
        if not doi:
            stats["no_doi"] += 1
            log(f"[reconcile] 无法提取 DOI，原地保留: {fn}")
            continue
        w = by_doi.get(doi)
        if w is None:
            stats["unmatched"] += 1
            log(f"[reconcile] DOI 不在本轮 works 或已有 PDF，原地保留: {fn} ({doi})")
            continue
        dest = os.path.join(pdf_dir, _safe_filename(doi))
        os.replace(src, dest)
        w["local_pdf_path"] = dest
        w["pdf_via"] = VIA
        w["pdf_source_url"] = f"https://doi.org/{doi} (manual incoming)"
        w["pdf_size_kb"] = _pdf_size_kb(dest)
        w["pdf_pages"] = _pdf_pages(dest)
        w.pop("pdf_download_note", None)
        stats["matched"] += 1
        log(f"[reconcile] 归位成功（{VIA_LABEL}，信任级 {VIA_TRUST}）: {fn} -> {os.path.basename(dest)}")
    return stats


def reconcile_from_cache(out_dir: str, works_key="works", log=None) -> dict:
    """从 out_dir 下的 .merged.json 或 evidence_log.json 读 works → reconcile → 回写。"""
    log = log or (lambda m: None)
    for fn in (".merged.json", "evidence_log.json"):
        merged_path = os.path.join(out_dir, fn)
        if not os.path.isfile(merged_path):
            continue
        with open(merged_path, encoding="utf-8") as f:
            data = json.load(f)
        works = data.get(works_key) if isinstance(data, dict) else data
        if not isinstance(works, list):
            continue
        stats = reconcile_manual(out_dir, works, log=log)
        if stats.get("matched"):
            tmp = merged_path + ".reconcile.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, merged_path)
            log(f"[OK] {fn} 已回写（{stats['matched']} 篇归位）")
        return stats, merged_path
    return {}, ""


if __name__ == "__main__":
    import sys
    import tempfile
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    _td = tempfile.mkdtemp(prefix="reconcile_t_")
    _inc = os.path.join(_td, "pdf_cache", "manual_incoming")
    os.makedirs(_inc, exist_ok=True)

    def _build_minimal_pdf():
        objs = [b"<</Type/Catalog/Pages 2 0 R>>",
                b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
                b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>"]
        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for i, body in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj" % i + body + b"endobj\n"
        xref_pos = len(out)
        out += b"xref\n0 4\n0000000000 65535 f \n"
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % xref_pos
        out += b"% padding\n" * 700
        return bytes(out)

    _MIN_PDF = _build_minimal_pdf()
    with open(os.path.join(_inc, "10.1038_s41586-021-03819-2.pdf"), "wb") as f:
        f.write(_MIN_PDF)
    with open(os.path.join(_inc, "10.9999_login.pdf"), "wb") as f:
        f.write(b"<html>login required</html>")

    works = [{"doi": "10.1038/s41586-021-03819-2", "title": "T", "pdf_download_note": "failed"},
             {"doi": "10.9999/login", "title": "L"}]

    p = export_needs_manual(works, _td, log=print)
    assert p and os.path.isfile(p), "needs_manual.csv 应生成"

    st = reconcile_manual(_td, works, log=print)
    assert st["matched"] == 1 and st["invalid"] == 1, st
    assert works[0]["pdf_via"] == VIA and os.path.isfile(
        os.path.join(_td, "pdf_cache", "doi_10.1038_s41586_021_03819_2.pdf"))

    assert _doi_from_filename("10.1038_s41586-021-03819-2") == "10.1038/s41586-021-03819-2"
    assert _doi_from_filename("10.1002-hbm.12345") == "10.1002/hbm.12345"
    print("manual_reconcile selftest: ALL PASSED")
