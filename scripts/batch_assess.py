#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_assess.py — meta-analysis 批量选题评估入口。

对多个候选方向批量运行 topic_assess → generate_topic_report，
横向汇总评分排序，出聚合报告。

规格格式（YAML）：
  version: 1
  entries:
    - topic: PD-1 inhibitors vs docetaxel in 2nd-line NSCLC
      year_from: 2021
      year_to: 2026
      clinical_override: 4
      picos:
        P: "NSCLC stage IV 2nd-line"
        I: "PD-1/PD-L1 inhibitors"
        C: "Docetaxel"
        O: "OS PFS ORR"

或行列表格式（.txt）：
  # topic | year_from | year_to | clinical_override
  PD-1 inhibitors vs docetaxel in 2nd-line NSCLC | 2021 | 2026 | 4
  SGLT2 inhibitors in heart failure | 2020 | | 3

SAFE PREVIEW：默认 dry-run 只打印计划；--run 才联网跑探针。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILL_ROOT, "adapters"))

# 依赖模块
try:
    import topic_assess
    from generate_topic_report import build_markdown, build_html
    _HAS_LOCAL = True
except ImportError as e:
    _HAS_LOCAL = False

try:
    import ctsearch_client
    _HAS_CTSEARCH = True
except ImportError:
    _HAS_CTSEARCH = False

try:
    import literature_probe
    _HAS_LITPROBE = True
except ImportError:
    _HAS_LITPROBE = False


def _slugify(text, max_len=48):
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text).strip("_-")
    return text[:max_len].strip("_-") or "entry"


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# spec 解析
# ---------------------------------------------------------------------------

def parse_spec_file(path):
    """解析 spec 文件，返回 entry 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml") or raw.lstrip().startswith("version:"):
        return _parse_yaml(raw)
    return _parse_linelist(raw)


def _parse_yaml(raw):
    try:
        import yaml
        doc = yaml.safe_load(raw)
    except ImportError:
        sys.stderr.write("[batch] ERROR: YAML spec 需要 PyYAML。pip install pyyaml\n")
        sys.exit(2)
    if not isinstance(doc, dict):
        raise ValueError("YAML spec 顶层必须是 mapping")
    defaults = doc.get("defaults") or {}
    raw_entries = doc.get("entries") or []
    entries = []
    for i, e in enumerate(raw_entries):
        merged = dict(defaults)
        merged.update(e)
        picos = merged.get("picos") or {}
        missing_picos = [k for k in ("P", "I", "C", "O") if not picos.get(k)]
        entries.append({
            "id": merged.get("id") or _slugify(merged.get("topic", f"entry_{i+1}")),
            "topic": merged.get("topic", ""),
            "year_from": merged.get("year_from"),
            "year_to": merged.get("year_to"),
            "picos": picos,
            "_missing_picos": missing_picos,
            "clinical_override": merged.get("clinical_override"),
            "max_results": merged.get("max_results", 50),
            "enabled": e.get("enabled", True),
            "lineno": i + 1,
        })
    return entries


def _parse_linelist(raw):
    """行列表格式：topic | year_from | year_to | clinical_override"""
    entries = []
    for lineno, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split("|")]
        topic = parts[0] if parts else ""
        try:
            year_from = int(parts[1]) if len(parts) > 1 and parts[1] else None
        except ValueError:
            year_from = None
        try:
            year_to = int(parts[2]) if len(parts) > 2 and parts[2] else None
        except ValueError:
            year_to = None
        try:
            clinical_override = int(parts[3]) if len(parts) > 3 and parts[3] else None
        except ValueError:
            clinical_override = None
        entries.append({
            "id": _slugify(topic) if topic else f"entry_{lineno}",
            "topic": topic,
            "year_from": year_from,
            "year_to": year_to,
            "picos": {},
            "_missing_picos": ["P", "I", "C", "O"],
            "clinical_override": clinical_override,
            "max_results": 50,
            "enabled": True,
            "lineno": lineno,
        })
    return entries


# ---------------------------------------------------------------------------
# 探针
# ---------------------------------------------------------------------------

def _probe_dedup(topic, year_from, year_to, max_results):
    """获取 dedup 探针数据。返回 {cochor, pubmed} 或 None。"""
    if _HAS_LITPROBE:
        try:
            nc = literature_probe.probe(topic, layer="cochor",
                                        year_from=year_from, year_to=year_to, max_results=1)
            np_ = literature_probe.probe(topic, layer="pubmed",
                                         year_from=year_from, year_to=year_to, max_results=1)
            if nc.get("hit_count") is not None or np_.get("hit_count") is not None:
                return {"cochor": nc.get("hit_count"), "pubmed": np_.get("hit_count")}
        except Exception as e:
            sys.stderr.write(f"  [probe] literature_probe 失败: {e}\n")

    if _HAS_CTSEARCH:
        try:
            res = ctsearch_client.search_literature(
                source="europepmc", keyword=topic,
                year_from=year_from, year_to=year_to,
                max_results=max_results, timeout=120)
            if not res.get("error") and res.get("total_count") is not None:
                return {"cochor": None, "pubmed": res["total_count"]}
        except Exception as e:
            sys.stderr.write(f"  [probe] ctsearch 失败: {e}\n")
    return None


# ---------------------------------------------------------------------------
# 评估 + 渲染
# ---------------------------------------------------------------------------

def _assess_entry(entry, run_mode):
    """对单个 entry 运行评估。"""
    dedup = None
    if run_mode == "run":
        dedup = _probe_dedup(entry["topic"], entry.get("year_from"),
                             entry.get("year_to"), entry.get("max_results", 50))
    return topic_assess.assess(
        topic=entry["topic"],
        picos=entry.get("picos"),
        missing=entry.get("_missing_picos"),
        dedup=dedup,
        registry=None,
        clinical_override=entry.get("clinical_override"),
    )


def _assessment_to_report_input(assessment, entry_id):
    """将 topic_assess 输出映射到 generate_topic_report 的 input JSON。"""
    picos = assessment.get("picos") or {}
    pico_for_report = {
        "P": picos.get("P", ""), "I": picos.get("I", ""),
        "C": picos.get("C", ""), "O": picos.get("O", ""),
        "search_terms": {
            "P": picos.get("P", ""), "I": picos.get("I", ""),
            "C": picos.get("C", ""), "O": picos.get("O", ""),
            "filters": "",
        },
    }
    return {
        "slug": entry_id,
        "title": assessment.get("topic", entry_id),
        "date": assessment.get("assessed_on", datetime.now().strftime("%Y-%m-%d")),
        "path": "full",
        "verdict": assessment.get("verdict_raw", assessment.get("verdict", "")),
        "background": assessment.get("note", ""),
        "pico": pico_for_report,
        "meta_type": "pairwise",
        "meta_type_rationale": "",
        "scores": assessment.get("scores", {}),
        "score_anchors": assessment.get("score_anchors", {}),
        "cross_checks": assessment.get("cross_checks", []),
        "gap": assessment.get("gap", {}),
        "dedup": assessment.get("dedup", {}),
        "search_strategy": "",
        "expected_studies": assessment.get("expected_studies", ""),
        "compliance": assessment.get("compliance", {}),
        "outcomes": [],
        "subgroups": [],
        "sensitivity": [],
        "risks": [],
        "next_actions": [],
        "prospero": assessment.get("prospero", {}),
        "evidence_tags": assessment.get("evidence_tags", {}),
        "meta": assessment.get("meta", {}),
    }


def _render_report(assessment, entry_id, out_dir, report_format):
    """渲染单个 entry 的报告。"""
    d = _assessment_to_report_input(assessment, entry_id)

    if report_format in ("md", "both"):
        md_content = build_markdown(d)
        with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
            f.write(md_content)

    if report_format in ("html", "both"):
        html_content = build_html(d)
        with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as f:
            f.write(html_content)


# ---------------------------------------------------------------------------
# 聚合
# ---------------------------------------------------------------------------

def _write_summary_md(batch_out, results):
    ok_results = [r for r in results if r["status"] == "ok"]
    ok_results.sort(key=lambda r: r.get("total_score", 0), reverse=True)
    lines = [
        "# 批量选题评估摘要",
        "",
        f"- 总计: {len(results)} · 成功: {len(ok_results)} · 失败: {len(results) - len(ok_results)}",
        "",
        "| 排名 | ID | 选题 | 总分 | 裁决 | 耗时(s) |",
        "|---|---|---|---|---|---|",
    ]
    for rank, r in enumerate(ok_results, 1):
        topic_short = r["topic"][:40] + ("..." if len(r["topic"]) > 40 else "")
        lines.append(f"| {rank} | {r['id']} | {topic_short} | {r.get('total_score', '-')}/20 | {r.get('verdict', '-')} | {r.get('elapsed_sec', '-')} |")
    lines.append("")
    with open(os.path.join(batch_out, "batch_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_manifest(batch_out, spec_file, run_mode, results):
    manifest = {
        "engine": "meta-batch-assess",
        "engine_version": "1.0.0",
        "generated_at": _now_iso(),
        "spec_file": spec_file,
        "run_mode": run_mode,
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r["status"] == "ok"),
            "error": sum(1 for r in results if r["status"] == "error"),
        },
        "ranking": [
            {"id": r["id"], "topic": r["topic"], "total": r.get("total_score"), "verdict": r.get("verdict")}
            for r in results if r["status"] == "ok"
        ],
        "entries": [
            {"id": r["id"], "topic": r["topic"], "status": r["status"], "error": r.get("error")}
            for r in results
        ],
    }
    with open(os.path.join(batch_out, "batch_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="meta-analysis 批量选题评估")
    ap.add_argument("spec_file", help="选题列表（YAML 或行列表 .txt）")
    ap.add_argument("--run", action="store_true",
                    help="联网跑探针（默认 dry-run 预览）")
    ap.add_argument("--out-dir", default="./batch_assess_out",
                    help="批量结果根目录（默认 ./batch_assess_out）")
    ap.add_argument("--max-total", type=int, default=None,
                    help="最多执行前 N 个有效 entry（配额封顶）")
    ap.add_argument("--resume", action="store_true",
                    help="跳过已完成（存在 .done 标记）的 entry，支持断点续跑")
    ap.add_argument("--report-format", choices=["md", "html", "both"], default="both",
                    help="每 entry 的报告格式（默认 both）")
    ap.add_argument("--progress", choices=["human", "json"], default="human")
    args = ap.parse_args()

    if not _HAS_LOCAL:
        sys.stderr.write("[batch] ERROR: 缺少 topic_assess / generate_topic_report 模块\n")
        sys.exit(2)

    spec_file = os.path.abspath(args.spec_file)
    if not os.path.isfile(spec_file):
        sys.stderr.write(f"[batch] ERROR: spec 文件不存在: {spec_file}\n")
        sys.exit(2)

    entries = parse_spec_file(spec_file)
    if not entries:
        sys.stderr.write("[batch] ERROR: 无有效 entry\n")
        sys.exit(2)

    batch_out = os.path.abspath(args.out_dir)
    os.makedirs(batch_out, exist_ok=True)
    run_mode = "run" if args.run else "dry-run"

    # max-total 封顶
    if args.max_total is not None:
        cnt = 0
        for e in entries:
            if not e.get("enabled", True):
                continue
            cnt += 1
            if cnt > args.max_total:
                e["_skipped_max"] = True

    executable = [e for e in entries if e.get("enabled", True) and not e.get("_skipped_max")]

    # ── Dry-run ──
    if run_mode == "dry-run":
        print(f"\n[BATCH] DRY-RUN（默认安全预览，未联网）。spec={spec_file}")
        print(f"[BATCH] entries={len(entries)} executable={len(executable)}\n")
        for e in entries:
            status = "SKIP" if e.get("_skipped_max") else ("OK" if e.get("enabled", True) else "DISABLED")
            picos_keys = list(e.get("picos", {}).keys())
            picos_info = f"picos={picos_keys}" if picos_keys else "picos=none"
            print(f"  [{status}] {e['id']}: {e['topic'][:60]}")
            print(f"         year={e.get('year_from')}-{e.get('year_to')} {picos_info} clinical={e.get('clinical_override', 'default')}")
        _write_manifest(batch_out, spec_file, run_mode, [])
        print(f"\n[BATCH] 计划已写入 {os.path.join(batch_out, 'batch_manifest.json')}")
        return 0

    # ── Run ──
    print(f"\n[BATCH] RUN 模式：开始评估 {len(executable)} 个 entry...")
    results = []
    for i, entry in enumerate(executable):
        eid = entry["id"]
        entry_out = os.path.join(batch_out, eid)
        os.makedirs(entry_out, exist_ok=True)

        # Resume
        done_marker = os.path.join(entry_out, ".done")
        if args.resume and os.path.isfile(done_marker):
            print(f"  [{i+1}/{len(executable)}] ↷ 跳过(已完成): {eid}")
            continue

        print(f"  [{i+1}/{len(executable)}] ▶ {eid}: {entry['topic'][:50]}")
        t0 = time.time()
        try:
            assessment = _assess_entry(entry, run_mode)
            _render_report(assessment, eid, entry_out, args.report_format)
            with open(done_marker, "w") as f:
                f.write(_now_iso())
            elapsed = time.time() - t0
            results.append({
                "id": eid,
                "topic": entry["topic"],
                "status": "ok",
                "elapsed_sec": round(elapsed, 1),
                "verdict": assessment.get("verdict", ""),
                "total_score": assessment.get("scores", {}).get("total", 0),
                "out_dir": entry_out,
            })
            print(f"      ✓ {elapsed:.1fs} | verdict={assessment.get('verdict')} total={assessment.get('scores', {}).get('total')}")
        except Exception as e:
            elapsed = time.time() - t0
            results.append({
                "id": eid, "topic": entry["topic"],
                "status": "error", "elapsed_sec": round(elapsed, 1),
                "error": str(e),
            })
            print(f"      ✗ {elapsed:.1fs} | ERROR: {e}")

    _write_summary_md(batch_out, results)
    _write_manifest(batch_out, spec_file, run_mode, results)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"\n[BATCH] 完成：{ok_count}/{len(executable)} 成功")
    print(f"[BATCH] 汇总 → {os.path.join(batch_out, 'batch_summary.md')}")
    print(f"[BATCH] 清单 → {os.path.join(batch_out, 'batch_manifest.json')}")
    return 0


if __name__ == "__main__":
    main()
