# AGENTS.md — meta-analysis v1.12.2 (R-based Meta-Analysis Skill)

> This skill is a published skill (A-tier equivalent). Its AGENTS.md is **English-only** per ct-base §3/§4 ("SKILL.md body + references + AGENTS.md are English-only for published skills"). Compute is delegated to a coze workflow by default, with a local R fallback retained in-skill.

## Overview / 技能概述

`meta-analysis`: A conversation-driven Meta-Analysis skill for WorkBuddy. Covers 100% of RevMan 5.x functionality, Stata `metareg`/`mvmeta` equivalents, effect-size conversions (`esc`), cluster-robust variance estimation (`clubSandwich`/`robumeta`), Bayesian NMA (Stan/JAGS), survival meta, TSA, single-group meta, diagnostic meta, and systematic-review workflow.

**Execution backend (2026-08-17 split, refined 2026-08-17)**: Two-track R engine — **coze workflow is the default compute path**; a **local R fallback** is retained inside this skill.
- **coze (default)**: R engine (metafor/meta/netmeta + dispatcher `run_task.R`) runs in the coze meta-analysis workflow (`src/r_engine/` + `src/graphs/nodes/meta_analysis.py`). The skill delegates via `adapters/run_analysis.py` (→ `coze_client.run_meta`) → coze `/run`.
- **local fallback**: a byte-identical mirror of the same R engine lives at `adapters/coze_project/src/r_engine/run_task.R` (sole local source, 2026-08-19) (kept in sync with coze via `coze_contract.md`). Invoked by `adapters/local_engine.py` when coze is unreachable, or when the user explicitly requests local/offline analysis.
Numeric judgment is always R-computed (coze-side or local), never read by the LLM.

---

## Core Rules / 核心规则

### 1. Environment Detection / 环境检测
- **Coze endpoint (default path)**: confirm via `COZE_META_ENDPOINT` + `coze_client.health()`. If unreachable, the local R fallback below is used automatically.
- **Local R engine (fallback path)**: `adapters/coze_project/src/r_engine/run_task.R` requires a local R install (`Rscript --version`) + core 14 packages. Configure via `RSCRIPT_PATH` / `META_LOCAL_ENGINE_DIR`. Not auto-installed by this skill.
- **Python**: Anaconda (`C:\Tools\anaconda3\python.exe`); used for `adapters/run_analysis.py` (unified front door), `coze_client.py`, `local_engine.py`, and helper scripts. Never for meta-analysis computation directly.
- Never hardcode paths.

### 2. Code Execution / 代码执行规范
- **Default: SAFE PREVIEW (dry-run)**. The analysis plan (task/data/params/figure envelope) is shown, NOT executed unless user opts in.
- Opt-in trigger: user explicitly says "run it", "execute", or similar — NOT a `--yes` flag (natural-language dialogue mode).
- **Execution (default = coze, fallback = local)**: call the unified front door `adapters/run_analysis.run_analysis(task, data, params, figure)` with `prefer="coze"` (default). It calls coze first; on coze failure it auto-falls back to local R and tags the result `_source="local_fallback"`.
  - User explicitly requests local/offline → `prefer="local"` (skips coze entirely).
  - Result shape: `{status, stats, figures[].svg, warnings, notes, _source}`.

### 3. Language Detection / 语言检测
- Default: English.
- Auto-switch to Chinese when OS locale contains `zh`/`CN` (via `scripts/i18n.py` → `is_chinese_os()`).
- Code output (R / Python) always English; not affected by language policy.
- User-facing runtime prompts use `i18n.t(key)`.

### 4. Security Red Line / 安全红线
- **Default compute = coze, fallback = local R**: by default all R computation runs in the coze meta-analysis workflow. Only the analysis request (task/data/params/figure) is sent to the configured coze endpoint; **no IPD or raw datasets are uploaded** — summary statistics (2×2 tables, effect sizes + SEs) are the common case. When coze is unreachable, the same analysis runs **locally** via `adapters/coze_project/src/r_engine/run_task.R` (still no data leaves the machine).
- **Numeric judgment stays in R**: the R-computed numbers (pooled estimate, I², P-scores, etc.) are produced by R (coze-side or local) and returned as structured JSON; the LLM agent only parses structure, never reads or rewrites numeric conclusions.
- **No auto-install**: R packages are NOT auto-installed by this skill. The coze side installs its own; the local fallback expects a pre-installed local R + core 14 packages.
- **Network only on explicit opt-in**: PDF full-text download from DOI/PMID requires explicit user confirmation.
- `permissions` block declared in SKILL.md top-level.

### 5. Reuse Shared Assets / 复用底座
- Copy shared assets from `ct-base/scripts/` and `ct-base/references/`:
  - `scripts/i18n.py`: bilingual strings single source of truth.
  - `references/language_policy.md`: bilingual policy detailed companion.
  - `references/report_template.md`: report skeleton reference.
- **Outbound calls (ct-base §16.9)**: `adapters/` is the skill's compute exit layer:
  - `adapters/run_analysis.py` — unified front door (coze-first, local-fallback).
  - `adapters/coze_client.py` — coze `/run` client (primary path).
  - `adapters/local_engine.py` — local R fallback (`adapters/coze_project/src/r_engine/run_task.R`).
- **R engine (two-track, single source of truth)**: the canonical R engine + `run_task.R` dispatcher lives in the coze project (`src/r_engine/`); a **byte-identical mirror** is kept at `adapters/coze_project/src/r_engine/` (sole local sync source) and kept in sync via `coze_contract.md`. Both tracks call the same dispatcher, so results are reproducible regardless of path.
- **Directory layout (ct-base §16.9)**: `scripts/` = pure-local Python; `adapters/` = compute exit layer; `adapters/coze_project/src/r_engine/` = local R fallback mirror (sole sync source; skill-root `r_engine/` removed 2026-08-19).

### 6. Interactive Menu / Navigation / 交互菜单
- **Triage §5.2 (ct-base §5.2)**: classify user's first message as Simple / Complex / Vague.
  - **Simple**: single, specific intent (e.g., "pool OR from these 5 studies", "convert d to logOR") → skip menu, go directly to analysis.
  - **Complex**: multi-decision / multi-parameter (e.g., "design a network meta with 3 interventions, subgroup by region, check inconsistency") → present level-1 menu with "need more explanation" entry.
  - **Vague**: unclear what user wants (e.g., "I need meta-analysis help") → grill-me style branch questions, 1–3 per round.
- Menu structure mirrors level-1 (7 categories) → level-2 (sub-menus) from SKILL.md.
- Non-exclusive menu entries per ct-base §6 guidance.

### 7. Traceability (Grounding) / 溯源硬规则 (ct-base §5.1)
- All factual/assertive claims must cite source: specific `ref-*.md` section or official guideline.
- If a claim has no verifiable source → mark `⚠️ official verify` and ask user to confirm against official text.
- Applies to: RevMan feature descriptions, Stata↔R mapping claims, statistical method recommendations.

---

## Dependencies / 依赖

### R packages (coze-side, and local-fallback if used)
```
# Core 14 (2026-08-19; esc/metagear/gridExtra/gemtc/rjags/multinma removed)
metafor meta netmeta bayesmeta dosresmeta mada robumeta clubSandwich
ggplot2 svglite forestploter jsonlite dplyr scales
# Optional 2 (guarded; missing → warning only)
ggrepel robvis
```
- **coze-side**: installed in the coze meta-analysis workflow (NOT by this skill). `bayesian_nma` (gemtc/JAGS) is a known env limitation on coze (no root); `esc` task is self-implemented (`.esc_convert`).
- **local fallback**: requires the same core 14 packages pre-installed in the user's local R. Missing-package tasks return a `check_pkg` error/warning from `run_task.R` rather than crashing.

### Python (this skill)
```
# adapters/coze_client.py + scripts/i18n.py + scripts/generate_topic_report.py
# coze_client.py depends only on stdlib (urllib/json/os); no third-party packages.
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
├── requirements.txt               # R package list
├── assets/
│   └── icon.svg                   # Skill logo
├── scripts/
│   ├── i18n.py                    # ct-base shared: bilingual helper
│   └── generate_topic_report.py   # Topic-selection report generator (pure Python)
├── adapters/                      # Compute exit layer (§16.9): coze-first + local fallback
│   ├── run_analysis.py            # Unified front door (coze-first, auto local-fallback)
│   ├── coze_client.py             # Coze /run client (primary path)
│   ├── local_engine.py            # Local R fallback (coze_project/src/r_engine/run_task.R)
│   └── README.md                  # Adapter docs
├── adapters/coze_project/          # Coze project local mirror (sole sync source; includes src/r_engine/)
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

## Changelog Sync / 变更日志同步

All version bumps and fixes must be recorded in `CHANGELOG.md`. Security-related fixes are mandatory entries.
