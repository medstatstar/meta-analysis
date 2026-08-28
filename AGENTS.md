# AGENTS.md — meta-analysis v2.1.1 (R-based Meta-Analysis Skill)

> This skill is a published skill (A-tier equivalent). Its AGENTS.md is **English-only** (SKILL.md body + references + AGENTS.md are English-only for published skills). Compute is delegated to a coze workflow (coze-only); no local R engine is shipped or advertised.

## Overview / 技能概述

`meta-analysis`: A conversation-driven Meta-Analysis skill for WorkBuddy. Covers 100% of RevMan 5.x functionality, Stata `metareg`/`mvmeta` equivalents, effect-size conversions (`esc`), cluster-robust variance estimation (`clubSandwich`/`robumeta`), Bayesian NMA (Stan/JAGS), survival meta, TSA, single-group meta, diagnostic meta, and systematic-review workflow.

**Execution backend**: **coze workflow is the sole compute path**. All R computation (metafor/meta/netmeta + dispatcher `run_task.R`) runs in the coze meta-analysis workflow (`src/r_engine/` + `src/graphs/nodes/meta_analysis.py`); the skill delegates via `adapters/run_analysis.py` (→ `coze_client.run_meta`) → coze `/run`. There is **no local-R fallback** — if coze is unreachable or unauthorized, `run_analysis` returns a structured error (`{status:"error", ...}`) instead of silently computing locally. The historical local-R code lives in `adapters/_dev/local_engine.py` (git/clawhub-ignored, not published, not in the runtime path). End users need no R install.
Numeric judgment is always R-computed on the coze side, never read by the LLM.

---

## Core Rules / 核心规则

### 1. Environment Detection / 环境检测
- **Coze endpoint (sole path)**: confirm via `COZE_META_ENDPOINT` + `coze_client.health()`. This is the only compute path.
- **Python**: Anaconda (`C:\Tools\anaconda3\python.exe`); used for `adapters/run_analysis.py` (unified front door), `coze_client.py`, and helper scripts. Never for meta-analysis computation directly.
- Never hardcode paths.

### 2. Code Execution / 代码执行规范
- **Default: AUTO-EXECUTE**. Once the user describes an analysis request, call the unified front door `adapters/run_analysis.run_analysis(task, data, params, figure)` and return results — no preview-confirm gate. Before the **first outbound call each session**, give a one-time spoken disclosure of what is sent and to which endpoint (ct-base §5), then execute automatically.
- **Execution (coze only)**: `run_analysis` calls coze. On coze failure / unauthorized it returns a structured error (`{status:"error", ...}`) — no local fallback. The successful result carries `_source="coze"`.
  - Successful result shape: `{status, stats, figures[].svg, warnings, notes, _source}`.

### 3. Language Detection / 语言检测
- Default: English.
- Auto-switch to Chinese when OS locale contains `zh`/`CN` (via `scripts/i18n.py` → `is_chinese_os()`).
- Code output (R / Python) always English; not affected by language policy.
- User-facing runtime prompts use `i18n.t(key)`.

### 4. Security Red Line / 安全红线
- **Default compute = coze (only path)**: by default all R computation runs in the coze meta-analysis workflow; only the analysis request (task/data/params/figure) is sent to the configured coze endpoint — **no IPD or raw datasets are uploaded** (summary statistics are the common case). There is no local-R fallback: coze unreachable / unauthorized returns a structured error.
- **Numeric judgment stays in R**: the R-computed numbers (pooled estimate, I², P-scores, etc.) are produced by the coze-side R engine and returned as structured JSON; the LLM agent only parses structure, never reads or rewrites numeric conclusions.
- **No auto-install**: R packages are NOT auto-installed by this skill. The coze side installs its own.
- **Network only on explicit opt-in**: PDF full-text download from DOI/PMID requires explicit user confirmation.
- `permissions` block declared in SKILL.md top-level.

### 5. Reuse Shared Assets / 复用底座
- Copy shared assets from `ct-base/scripts/` and `ct-base/references/`:
  - `scripts/i18n.py`: bilingual strings single source of truth.
  - `references/language_policy.md`: bilingual policy detailed companion.
  - `references/report_template.md`: report skeleton reference.
- **Outbound calls**: `adapters/` is the skill's compute exit layer:
  - `adapters/run_analysis.py` — unified front door (coze only).
  - `adapters/coze_client.py` — coze `/run` client (sole path).
  - `adapters/literature_probe.py` — **in-skill literature dedup probe** (Europe PMC REST, `https://www.ebi.ac.uk/europepmc/webservices/rest/search`). This is a *literature-retrieval* adapter for the topic-selection Stage-4 dedup (Cochrane + PubMed layers), NOT numerical computation — it runs self-contained, by default, and does not delegate to other skills or to coze. Zero third-party deps (stdlib only).
- **R engine (single source of truth)**: the canonical R engine + `run_task.R` dispatcher lives in the coze project (`src/r_engine/`) and is mirrored at `adapters/coze_project/src/r_engine/` (maintenance/dev-reference only; NOT a runtime fallback, NOT published). Developer R-engine maintenance commands live in `adapters/coze_project/DEV.md` (git/clawhub-ignored, not published). The historical `adapters/_dev/local_engine.py` is retained as a dev-only reference (git/clawhub-ignored) but is NOT invoked by the runtime.
- **Directory layout**: `scripts/` = pure-local Python; `adapters/` = compute exit layer; `adapters/coze_project/src/r_engine/` = coze-project R engine mirror (maintenance/dev-reference only; git/clawhub-ignored); `adapters/_dev/` = dev-only reference code (git/clawhub-ignored, not published).

### 6. Interactive Menu / Navigation / 交互菜单
- **Triage**: classify user's first message as Simple / Complex / Vague.
  - **Simple**: single, specific intent (e.g., "pool OR from these 5 studies", "convert d to logOR") → skip menu, go directly to analysis.
  - **Complex**: multi-decision / multi-parameter (e.g., "design a network meta with 3 interventions, subgroup by region, check inconsistency") → present level-1 menu with "need more explanation" entry.
  - **Vague**: unclear what user wants (e.g., "I need meta-analysis help") → grill-me style branch questions, 1–3 per round.
- Menu structure mirrors level-1 (7 categories) → level-2 (sub-menus) from SKILL.md.
- Non-exclusive menu entries per the global interaction-guidance rules.

### 7. Traceability (Grounding) / 溯源硬规则
- All factual/assertive claims must cite source: specific `ref-*.md` section or official guideline.
- If a claim has no verifiable source → mark `⚠️ official verify` and ask user to confirm against official text.
- Applies to: RevMan feature descriptions, Stata↔R mapping claims, statistical method recommendations.

---

## Dependencies / 依赖

### R packages (coze-side; optional for local dev/maintenance only)
```
# Core 14 (2026-08-19; esc/metagear/gridExtra/gemtc/rjags/multinma removed)
metafor meta netmeta bayesmeta dosresmeta mada robumeta clubSandwich
ggplot2 svglite forestploter jsonlite dplyr scales
# Optional 2 (guarded; missing → warning only)
ggrepel robvis
```
- **coze-side**: installed in the coze meta-analysis workflow (NOT by this skill). `bayesian_nma` (gemtc/JAGS) is a known env limitation on coze (no root); `esc` task is self-implemented (`.esc_convert`).

### Python (this skill)
```
# adapters/coze_client.py + scripts/i18n.py + scripts/generate_topic_report.py
# coze_client.py depends only on stdlib (urllib/json/os); no third-party packages.
# cairosvg: OPTIONAL, only when PNG output is requested (adapters/rendering.svg_to_png).
#           Default SVG output needs nothing. `pip install cairosvg` to enable PNG.
```

---

## Output Convention / 输出约定

Each analysis produces:
- `analysis_complete.R` — fully reproducible R script
- Forest plot (`.svg` + `.png`)
- Funnel plot, standard + contour-enhanced (`.svg` + `.png`)
- `results_summary.md` — structured results (effect, CI, I², τ², p-values)
- CSV data backup
- Optional: R Markdown / HTML report

SVG editing guide → `references/svg_editing.md`.

---

## Directory Structure / 目录结构

```
meta-analysis/
├── SKILL.md                       # Frontmatter + English body (published skill)
├── AGENTS.md                      # This file (self-improvement + agent rules, English)
├── CHANGELOG.md                   # Version / fix log
├── README.md                      # English (top switch to README_zh-CN.md)
├── README_zh-CN.md                # Chinese (top switch to README.md)
├── LICENSE                        # MIT
├── requirements.txt               # Dependency manifest (default: zero deps; cairosvg optional for PNG)
├── assets/
│   └── icon.svg                   # Skill logo
├── scripts/
│   ├── i18n.py                    # ct-base shared: bilingual helper
│   └── generate_topic_report.py   # Topic-selection report generator (pure Python)
├── adapters/                      # Compute exit layer (§16.9): coze-only
│   ├── run_analysis.py            # Unified front door (coze only)
│   ├── coze_client.py             # Coze /run client (sole path)
│   ├── _dev/                      # Dev-only reference (git/clawhub-ignored, not published)
│   │   └── local_engine.py        # Historical local-R engine; NOT invoked by runtime
│   └── README.md                  # Adapter docs
├── adapters/coze_project/          # Coze project R engine mirror (maintenance/dev-reference only; not published)
│   ├── run_task.R                 # Dispatcher (task → stats + SVG), single source with coze
│   ├── meta_analysis_core.R
│   ├── advanced_functions.R
│   ├── effect_size_conversions.R
│   ├── network_meta_analysis.R
│   ├── stata_equivalents.R
│   └── setup_packages.R
├── references/
│   ├── language_policy.md         # ct-base shared: bilingual policy detail
│   ├── report_template.md         # ct-base shared: report skeleton
│   ├── interactive_menu.md
│   ├── data_templates.md
│   ├── revman_complete.md
│   ├── stata_to_r_mapping.md
│   ├── advanced_analysis.md
│   ├── single_group_meta.md
│   ├── survival_meta.md
│   ├── tsa_diagnostics.md
│   ├── diagnosis_meta.md
│   ├── bayesian_nma.md
│   ├── esc_robust_meta.md
│   ├── review_workflow.md
│   ├── r_packages.md
│   ├── citations.md
│   ├── references.md
│   ├── advanced_api.md
│   ├── svg_editing.md
│   └── purpose_zh.md
```

---

## Decision Records / 决策记录

### DR-2026-08-28 · Figure transport: keep per-file return, do NOT bundle into one archive
- **Decision**: coze returns figures as **separate S3 objects** (`figures[].url`, one GET each, downloaded + backfilled by `coze_client._fill_external_svgs`); **do NOT** switch to "bundle all figures into one file, split locally".
- **Why rejected (bundling)**: ① 4000-char truncation was already solved by S3 externalization — unrelated to 1-vs-N files; ② figures are tiny SVGs (~14KB forest, ~112KB for 8) so the saved round-trips are negligible vs. the cost of introducing unpack coupling + single-point failure + contract alignment; ③ bundling breaks the existing "fail-one-keep-rest" robustness (`run_task.R` `.safe_fig` + `_fill_external_svgs` which only marks `_svg_fetch_failed` on a per-figure download error, never aborts).
- **Only worthwhile optimization**: parallelize `_fill_external_svgs` downloads via `concurrent.futures` (keeps isolation, collapses RTT) — local-only, no coze-side change.
- **Scope limit**: applies to small text assets (SVG/JSON < tens of KB). Re-evaluate if figures become hi-res PNG / multi-MB, or if coze S3 enforces strict billing/rate limits.
- **Canonical record**: ct-base `docs/07-coze-engine.md` §20.7.

## Changelog Sync / 变更日志同步

All version bumps and fixes must be recorded in `CHANGELOG.md`. Security-related fixes are mandatory entries.
