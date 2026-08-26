#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
literature_probe.py — In-skill literature dedup probe for meta-analysis topic selection.

WHY THIS EXISTS
---------------
The meta-analysis skill must be **self-contained** for its core upstream gate
(topic selection / novelty dedup). It must NOT delegate every literature need
to another skill, and it must NOT fall back to "search-query templates only"
(the template-only path was the prior failure mode — it produced no real
evidence). This module runs a REAL, dependency-free probe against Europe PMC
(https://www.ebi.ac.uk/europepmc/webservices/rest/search) — the REST front-end
to MEDLINE + PubMed Central — and returns live hit counts + top titles for the
Cochrane and PubMed layers of the three-layer dedup.

PROVENANCE
----------
Field mapping and query syntax are adapted from ct-literature's verified
`adapters/fetch_europepmc.py` (Europe PMC fetcher) and its `http_utils`
retry/backoff policy. We re-implement a minimal, standalone version here so
meta-analysis has zero cross-skill import dependency and stays self-contained.
Key facts confirmed against the live API (2026-08-26):
  - Cochrane reviews live in journal "The Cochrane database of systematic reviews";
    the reliable filter restricts to that journal via
    `AND (JOURNAL:"The Cochrane database of systematic reviews")`
    (verified accurate; NOT `PUBLICATION_TYPE:"Cochrane Reviews"` which returns 0
    — the pubType value is "Systematic Review", not "Cochrane Reviews"; and NOT a
    bare quoted phrase, which overcounts papers that merely cite Cochrane).
  - Year filter field is `PUB_YEAR:[lo TO hi]`.
  - `resultType=core` is required to populate journalInfo / pubTypeList.

Zero third-party dependencies — standard library only (urllib, json, re, time,
datetime). No confidential data input; reads only public literature.
"""
import argparse
import datetime
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = "meta-analysis-skill/2.1.1"

# Cochrane Database of Systematic Reviews — restrict to the journal itself
# (verified 2026-08-26: `JOURNAL:"The Cochrane database of systematic reviews"`
# returns accurate counts; the looser quoted-phrase match overcounts because it
# also catches papers that merely *cite* Cochrane). All sample journals matched
# by this filter are true Cochrane reviews.
COCHRANE_JOURNAL_FILTER = '(JOURNAL:"The Cochrane database of systematic reviews")'
COCHRANE_JOURNAL_MARK = "cochrane database of systematic reviews"


def _get_json(url, timeout=30, max_retries=3, backoff=2.0):
    """GET `url`, parse JSON, with unified retry/backoff.

    Mirrors ct-literature http_utils policy, minimal form:
      - HTTP 429: honor `Retry-After` header; else exponential backoff.
      - 5xx / network / timeout: exponential backoff.
      - other 4xx: non-retryable, raised immediately.
    Raises RuntimeError after retries exhausted.
    """
    last = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra else backoff ** (attempt - 1)
                if attempt < max_retries:
                    time.sleep(wait)
                    continue
                last = e
                break
            if 500 <= e.code < 600:
                if attempt < max_retries:
                    time.sleep(backoff ** (attempt - 1))
                    continue
                last = e
                break
            raise  # 4xx other than 429 → non-retryable
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if attempt < max_retries:
                time.sleep(backoff ** (attempt - 1))
                continue
            last = e
            break
    raise RuntimeError("Europe PMC request failed after %d retries: %s" % (max_retries, last))


def _strip_html(s):
    if not s:
        return s
    return re.sub(r"<[^>]+>", "", s)


def _extract(rec):
    """Normalize one Europe PMC record. Field names per fetch_europepmc._extract."""
    ji = rec.get("journalInfo") or {}
    journal = (ji.get("journal") or {}).get("title")
    pmid = rec.get("pmid")
    doi = rec.get("doi")
    year = None
    if rec.get("pubYear") and str(rec.get("pubYear")).isdigit():
        year = int(rec["pubYear"])
    ftl = rec.get("fullTextUrlList") or {}
    ft_urls = ftl.get("fullTextUrl") or []
    fulltext_url = ft_urls[0].get("url") if ft_urls else None
    title = _strip_html(rec.get("title") or "")
    pub_types = (rec.get("pubTypeList") or {}).get("pubType", []) or []
    cited = rec.get("citedByCount")
    return {
        "id": rec.get("id") or pmid,
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "year": year,
        "journal": journal,
        "pub_types": pub_types,
        "cited_by_count": int(cited) if isinstance(cited, int) else 0,
        "url": fulltext_url or doi or None,
        "is_cochrane": bool(journal and COCHRANE_JOURNAL_MARK in journal.lower()),
    }


def _build_query(topic, review_type, year_from, year_to, cochrane_only):
    q = topic
    if cochrane_only:
        q += " AND " + COCHRANE_JOURNAL_FILTER
    else:
        if review_type == "meta-analysis":
            q += " AND meta-analysis"
        elif review_type == "systematic-review":
            q += " AND (systematic review OR meta-analysis)"
        elif review_type == "rct":
            q += " AND randomized controlled trial"
    if year_from or year_to:
        lo = str(year_from) if year_from else "1900"
        hi = str(year_to) if year_to else "3000"
        q += " AND (PUB_YEAR:[%s TO %s])" % (lo, hi)
    return q


def _build_ct_handoff(topic, layer, year_from=None, year_to=None):
    """Build the ct-literature command that reproduces this probe's search
    with full retrieval machinery (verify / evidence_log / merge / Excel /
    HTML / PRISMA). This is the seamless handoff from meta-analysis topic
    selection -> comprehensive literature retrieval.

    Both skills use the SAME Europe PMC journal-filter string for Cochrane,
    so the Cochrane hit counts match exactly; the only difference is depth
    (quick dedup count here vs. full records + anti-hallucination there).
    """
    _q = json.dumps(topic, ensure_ascii=False)  # double-quoted, shell-safe
    if layer == "cochrane":
        cmd = ("python scripts/ct_literature.py --topic %s --cochrane "
               "--with-europepmc --run --out-dir ./cochrane_out" % _q)
    else:
        yf = year_from if year_from else (datetime.date.today().year - 5)
        cmd = ("python scripts/ct_literature.py --topic %s --review-type "
               "systematic-review --year-from %s --with-europepmc --run "
               "--out-dir ./pubmed_out" % (_q, yf))
    return {
        "action": "run ct-literature for full retrieval",
        "command": cmd,
        "note": ("本探针只是选题去重的快速检查（真实命中数 + 前几篇标题），并非全面文献检索。"
                 "需要完整检索（反幻觉验证 / 证据溯源 / 合并去重 / Excel+HTML 报告 / PRISMA 筛选）时，"
                 "请先使用 ct-literature 技能——先 cd 到 ct-literature 技能目录再执行上面的命令。"),
        "same_filter": ("两技能使用同一 Europe PMC 期刊过滤串 "
                        '`(JOURNAL:"The Cochrane database of systematic reviews")`，'
                        "Cochrane 层计数完全一致，可无缝衔接。"),
    }


def probe(topic, layer="pubmed", review_type="systematic-review",
          year_from=None, year_to=None, max_results=10):
    """Probe one dedup layer against Europe PMC.

    Args:
        topic: free-text PICO-derived query (e.g. "PD-1 inhibitors NSCLC 2nd line").
        layer: "cochrane" (Cochrane Library via Europe PMC) or "pubmed"
               (published SR/MA on PubMed/MEDLINE).
        review_type: for pubmed layer — meta-analysis | systematic-review | rct.
        year_from / year_to: inclusive publication-year bounds (None = open).
        max_results: cap on returned work records (hit_count is always the
                     full API total, not capped).

    Returns:
        dict with keys: layer, query, hit_count (int|None), cochrane_count (int),
        works (list), error (str|None), ct_handoff (dict). On request failure,
        hit_count=None and error is set — callers degrade gracefully (do NOT
        crash the workflow).
    """
    cochrane_only = (layer == "cochrane")
    q = _build_query(topic, review_type, year_from, year_to, cochrane_only)
    collected = []
    hit_count = None
    page = 1
    per = 25
    while len(collected) < max_results:
        params = {
            "query": q,
            "format": "json",
            "resultType": "core",
            "pageSize": min(per, max_results - len(collected)),
            "page": page,
        }
        url = BASE + "?" + urllib.parse.urlencode(params)
        try:
            j = _get_json(url)
        except Exception as e:  # noqa: BLE001 - degrade, don't abort workflow
            return {"layer": layer, "query": q, "hit_count": None,
                    "cochrane_count": 0, "works": [], "error": str(e),
                    "ct_handoff": _build_ct_handoff(topic, layer, year_from, year_to)}
        if hit_count is None:
            hit_count = j.get("hitCount")
        results = (j.get("resultList") or {}).get("result", [])
        if not results:
            break
        for rec in results:
            collected.append(_extract(rec))
        if len(results) < per:
            break
        page += 1
        time.sleep(0.3)

    # For the pubmed layer, also count any Cochrane reviews that surfaced
    # (post-filter, robust against query-term variance).
    cochrane_count = sum(1 for w in collected if w.get("is_cochrane"))
    return {
        "layer": layer,
        "query": q,
        "hit_count": hit_count,
        "cochrane_count": cochrane_count,
        "works": collected[:max_results],
        "error": None,
        "ct_handoff": _build_ct_handoff(topic, layer, year_from, year_to),
    }


def dedup_probe(topic, year_from=None, year_to=None, max_results=8,
                cochrane_window_years=0):
    """Run the self-contained two-layer dedup probe (Cochrane + PubMed SR/MA).

    This is the DEFAULT Stage-4 evidence source for topic selection — it runs
    live and returns real hit counts, so the novelty ranking (R7) is grounded
    in actual literature, not templates.

    Args:
        topic: PICO-derived query string.
        year_from / year_to: bounds for the PubMed layer (default: last 5 years
                             if both None).
        max_results: top titles to return per layer.
        cochrane_window_years: if >0, restrict Cochrane layer to the last N
                               years (default 0 = no year bound on Cochrane).

    Returns:
        dict: topic, layers {cochrane, pubmed_meta}, summary (human-readable
        dedup signal), any_error (bool).
    """
    if year_from is None and year_to is None:
        year_from = datetime.date.today().year - 5
    c_year_from = None
    if cochrane_window_years and cochrane_window_years > 0:
        c_year_from = datetime.date.today().year - cochrane_window_years

    cochrane = probe(topic, layer="cochrane", year_from=c_year_from,
                     year_to=year_to, max_results=max_results)
    pubmed = probe(topic, layer="pubmed", review_type="systematic-review",
                   year_from=year_from, year_to=year_to, max_results=max_results)

    parts = []
    if cochrane.get("hit_count") is not None:
        parts.append("Cochrane: %s review(s) on this topic" % cochrane["hit_count"])
    else:
        parts.append("Cochrane: probe unavailable")
    if pubmed.get("hit_count") is not None:
        parts.append("PubMed SR/MA (last %s y): %s" % (
            (datetime.date.today().year - (year_from or datetime.date.today().year)),
            pubmed["hit_count"]))
    else:
        parts.append("PubMed SR/MA: probe unavailable")
    summary = "; ".join(parts)

    return {
        "topic": topic,
        "layers": {"cochrane": cochrane, "pubmed_meta": pubmed},
        "summary": summary,
        "any_error": bool(cochrane.get("error") or pubmed.get("error")),
        "ct_handoff": {
            "note": ("本探针只是选题去重的快速检查（真实命中数 + 前几篇标题），并非全面文献检索。"
                     "需要完整检索（反幻觉验证 / 证据溯源 / 合并去重 / Excel+HTML 报告 / PRISMA 筛选）时，"
                     "请先使用 ct-literature 技能。"),
            "same_filter": ("两技能使用同一 Europe PMC 期刊过滤串 "
                            '`(JOURNAL:"The Cochrane database of systematic reviews")`，'
                            "Cochrane 层计数完全一致，可无缝衔接。"),
            "cochrane": _build_ct_handoff(topic, "cochrane", c_year_from, year_to),
            "pubmed": _build_ct_handoff(topic, "pubmed", year_from, year_to),
            "cochrane_query": cochrane.get("query"),
            "pubmed_query": pubmed.get("query"),
        },
    }


def main():
    ap = argparse.ArgumentParser(
        description="In-skill Europe PMC dedup probe (self-contained, no other skill needed).")
    ap.add_argument("--topic", required=True, help="PICO-derived query string")
    ap.add_argument("--layer", choices=["cochrane", "pubmed", "both"], default="both")
    ap.add_argument("--review-type", default="systematic-review",
                    choices=["meta-analysis", "systematic-review", "rct"])
    ap.add_argument("--year-from", type=int)
    ap.add_argument("--year-to", type=int)
    ap.add_argument("--max", type=int, default=8)
    ap.add_argument("--out")
    args = ap.parse_args()

    if args.layer == "both":
        res = dedup_probe(args.topic, args.year_from, args.year_to, args.max)
    elif args.layer == "cochrane":
        res = probe(args.topic, layer="cochrane", year_from=args.year_from,
                    year_to=args.year_to, max_results=args.max)
    else:
        res = probe(args.topic, layer="pubmed", review_type=args.review_type,
                    year_from=args.year_from, year_to=args.year_to, max_results=args.max)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print("[OK] wrote probe result -> %s" % args.out)
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
