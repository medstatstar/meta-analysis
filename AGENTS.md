# AGENTS.md — meta-analysis v2.21.2 (R-based Meta-Analysis Skill)

> This skill is a published skill (A-tier equivalent). Its AGENTS.md is **English-only** (SKILL.md body + references + AGENTS.md are English-only for published skills). Compute is delegated to a coze workflow (coze-only); no local R engine is shipped or advertised.

## Overview / 技能概述

`meta-analysis`: A conversation-driven Meta-Analysis skill for WorkBuddy. Covers 100% of RevMan 5.x functionality, Stata `metareg`/`mvmeta` equivalents, effect-size conversions (`esc`), cluster-robust variance estimation (`clubSandwich`/`robumeta`), Bayesian NMA (Stan/JAGS), survival meta, TSA, single-group meta, diagnostic meta, and systematic-review workflow.

**Execution backend**: **coze workflow is the sole compute path**. All R computation (metafor/meta/netmeta + dispatcher `run_task.R`) runs in the coze meta-analysis workflow (`src/r_engine/` + `src/graphs/nodes/meta_analysis.py`); the skill delegates via `adapters/run_analysis.py` (→ `coze_client.run_stage`, per-stage envelope) → coze `/run`. There is **no local-R fallback** — if coze is unreachable or unauthorized, `run_analysis` returns a structured error (`{status:"error", ...}`) instead of silently computing locally. End users need no R install.
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
  - `adapters/run_analysis.py` — unified front door (coze only; → `coze_client.run_stage` per-stage envelope).
  - `adapters/coze_client.py` — coze `/run` client (sole path; `run_stage` per-stage + `run_meta` legacy fallback).
  - `adapters/literature_probe.py` — **in-skill literature dedup probe** (Europe PMC REST, `https://www.ebi.ac.uk/europepmc/webservices/rest/search`). This is a *literature-retrieval* adapter for the topic-selection Stage-4 dedup (Cochrane + PubMed layers), NOT numerical computation — it runs self-contained, by default, and does not delegate to other skills or to coze. Zero third-party deps (stdlib only).
- **R engine (single source of truth)**: the canonical R engine + `run_task.R` dispatcher lives in the coze project (`src/r_engine/`) and is mirrored at `adapters/coze/src/r_engine/` (maintenance/dev-reference only; NOT a runtime fallback, NOT published). Developer R-engine maintenance commands live in `adapters/coze/DEV.md` (git/clawhub-ignored, not published). There is no local-R reference code: the historical `adapters/_dev/local_engine.py` was deleted on 2026-09-01 per the architecture end-state principle (coze is the sole compute source of truth).
- **Directory layout**: `scripts/` = pure-local Python; `adapters/` = compute exit layer; `adapters/coze/src/r_engine/` = coze-project R engine mirror (maintenance/dev-reference only; git/clawhub-ignored); `adapters/_dev/` = dev-only reference code (git/clawhub-ignored, not published).

### 6. Published Application (WorkBuddy Sites)

The workbench is published as a WorkBuddy online app. **When re-publishing, always reuse the existing `appId` to keep the share link stable — never create a new app.**

| Item | Value |
|---|---|
| Share link | `https://meta.app.workbuddy.link/` (alias: `https://meta.app.workbuddy.host/`) |
| domainPrefix | `meta` |
| appId | `wbapp_hNZl928SI6wByvJt2COtcC` |
| sandboxId | `a3c70e48be8f45019845b76383334bfc` |
| Runtime | Python (`pip install -r requirements.txt` + `python main.py`) |
| Deploy directory | `meta-workbench-app/` (23 files: `main.py` + `adapters/` + `requirements.txt`) |

### 7. Interactive Menu / Navigation / 交互菜单
- **Triage**: classify user's first message as Simple / Complex / Vague.
  - **Simple**: single, specific intent (e.g., "pool OR from these 5 studies", "convert d to logOR") → skip menu, go directly to analysis.
  - **Complex**: multi-decision / multi-parameter (e.g., "design a network meta with 3 interventions, subgroup by region, check inconsistency") → present level-1 menu with "need more explanation" entry.
  - **Vague**: unclear what user wants (e.g., "I need meta-analysis help") → grill-me style branch questions, 1–3 per round.
- Menu structure mirrors level-1 (7 categories) → level-2 (sub-menus) from SKILL.md.
- Non-exclusive menu entries per the global interaction-guidance rules.
- **Framework alignment & pruning (2026-10-27)**: menu categories mirror the published workbench's five modules; entries without engine backing (ROBINS-I, RoB traffic-light plot, inconsistency heatmap, AI screening, PDF batch download, figure digitization, missing-data imputation) are removed — never offer them in chat (R engine returns `unknown_task`). **Manuscript/writing module (Block C + writing-advisor) is DISABLED in conversation** — workbench surface only; do not invoke `writing_advisor` (no `advise=True`). Detail → `references/interactive_menu.md` §2 banners.

### 7. Traceability (Grounding) / 溯源硬规则
- All factual/assertive claims must cite source: specific `ref-*.md` section or official guideline.
- If a claim has no verifiable source → mark `⚠️ official verify` and ask user to confirm against official text.
- Applies to: RevMan feature descriptions, Stata↔R mapping claims, statistical method recommendations.

---

## Dependencies / 依赖

### R packages (coze-side; optional for local dev/maintenance only)
```
# Core 15 (2026-08-19 baseline + 2026-08-30 metagear re-introduced for plot_PRISMA; esc/gridExtra/gemtc/rjags/multinma still removed)
metafor meta netmeta bayesmeta dosresmeta mada robumeta clubSandwich metagear
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
│   ├── generate_topic_report.py   # Topic-selection report generator (pure Python)
│   ├── extract_assist.py          # Data-extraction assistant: scaffold/validate/stamp (human-in-the-loop)
│   └── extraction_guard.py        # Extraction verify gate, called by run_meta.py (blocks unverified CSV)
├── adapters/                      # Compute exit layer (§16.9): coze-only
│   ├── run_analysis.py            # Unified front door (coze only)
│   ├── coze_client.py             # Coze /run client (sole path)
│   ├── pdf_extractor.py           # PDF data extraction (v0.4.1, table + narrative templates)
│   ├── literature_probe.py        # In-skill Europe PMC dedup probe (zero deps)
│   ├── _dev/                      # Dev-only reference dir (git/clawhub-ignored, not published)
│   └── README.md                  # Adapter docs
├── adapters/coze/          # Coze project R engine mirror (maintenance/dev-reference only; not published)
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
- **Canonical record**: ct-base `docs/10-coze-engine.md` §20.7.

## 8. Upstream Orchestration & Extraction Guard / 上游编排与抽取守卫

- **Positioning (2026-08-30)**: meta-analysis is now an *orchestrator* covering the full Meta pipeline, not just the compute track. Upstream stages reuse existing modules and delegate retrieval to `ct-literature`:
  - ① Topic-direction judgment → `references/topic-selection.md` + `adapters/literature_probe.py` (in-skill Europe PMC probe); comprehensive retrieval delegated to **ct-literature**.
  - ② Literature retrieval/dedup → **ct-literature** (`ct_literature.py`, 6-source merge+dedup); meta-analysis only orchestrates.
  - ③ Screening/cleaning → `ct-literature` `screen_prisma.py` (machine) + agent-layer title/abstract judgment (`review_workflow.md §2`); PRISMA via `scripts/prisma_bridge.py`.
  - ④ **Data extraction (new)** → `scripts/extract_assist.py` (scaffold/validate/stamp) + `scripts/extraction_guard.py` + `adapters/pdf_extractor.py` (table + narrative templates, v0.4.1).
  - ⑤ Compute → existing `scripts/run_meta.py` (coze-only).
- **Extraction assistant (human-in-the-loop, never auto-feed)**: `extract_assist.py` writes a clean Type 1/2/3 CSV plus a sidecar `<csv>.provenance.json` with `verified_by_human=NO`. The agent/LLM reads full texts (OA or user-uploaded PDF→md) and proposes rows; `validate` checks schema/numeric sanity/NR markers; `stamp --confirm` sets `verified_by_human=YES` only after human review (source page/table recorded). Any unreported value → `NR`, never fabricated.
- **Extraction guard (red line)**: `extraction_guard.check_verified(data_path)` is called at the top of `run_meta.py` (before `build`). If a companion `.provenance.json` exists with `verified_by_human=False` → blocks with `META_STATUS=unverified_extraction` (exit 3). No companion → treated as a trusted hand-made CSV (allowed, with a note). `run_meta --trust-data` bypasses the guard (explicit user responsibility, only for confirmed-valid legacy/curated CSVs).
- **Seam trap (do not automate)**: `ct-literature`'s `included_records` (machine screen pass) ≠ `included` (human final). `prisma_bridge.py` forces `included`/`assessed`/`excluded_elig` as `[MANUAL]`; never map machine screen counts directly into the compute track.
- **PDF data extraction** (`adapters/pdf_extractor.py` v0.4.1, 2026-09-14): table + narrative templates for extracting meta-analysis data from PDFs. Templates: T_DICHOT, T_CONTINUOUS, T_EFFECT_TABLE, T_CONT_TABLE, T_FOREST_TABLE, T_META_TABLE, T_POOLED_EFFECT, T_SUBGROUP_EFFECT, T_OR_CI, T_HR_CI, T_RR_CI. Benchmarked on 78 real PDFs from `adapters/pdf_cache`. Human-in-the-loop review gate via `extract_assist.py`.
- **Full-flow mode entry (`@skill` trigger)**: when the user invokes meta-analysis with a full-flow intent (`系统综述全流程` / `systematic review workflow` / `从检索到meta分析` / etc., see SKILL.md `triggers`), follow `references/systematic_review_fullflow.md` — a 5-stage playbook (Stage 0 launch gate → ① topic → ② ct-literature retrieval → ③ screening+PRISMA → ④ extraction → ⑤ compute) with two non-skippable human gates (Stage 3 final `included` count, Stage 4 `stamp --confirm`). It does NOT add a new `classify.py` task class; it sequences the existing topic + compute tracks.

## Deploy Retest Gate (mandatory before publish / deploy)

**Freeze check FIRST**: before any publish attempt to GitHub → SkillHub → ClawHub, run `python adapters/publish_guard.py` — exit code 2 means a dev-period publish freeze is active (`adapters/DEV_POLICY.json`) and publishing is blocked; do NOT proceed and do NOT bypass it. This check is part of the gate, not optional advice.

**Mandatory before publishing / deploying** to GitHub → SkillHub → ClawHub: run `python tests/deploy_retest.py` (`--live` to actually hit the network; publish allowed only on all-green). This gate strictly verifies that the coze response is **genuinely valid** (HTTP 200 ≠ success; it rejects `status=ok` empty shells / `NaN` / no-figure (svg/url) false greens — coze externalizes SVG to S3 `url`, so a present+reachable `url` counts as a valid figure), writes `tests/deploy_retest_report.json`, and exits non-zero on any failure to block publishing. Use `--mock` for local logic self-check (no network) and `--offline` for envelope-contract validation. Full rules and red lines → `outputs/deploy_retest_gate.md`.

## Workbench UI Detail Self-Check (mandatory before publish; aligns ct-base §21)

> The topic-assessment UI has repeatedly shown detail defects even after multiple automated checks (copy drifting from backend logic, a seemingly redundant button silently dropping PICOS, ambiguous toggle names, missing-dimension placeholders with no guidance). The unified spec and machine-check list live in ct-base `references/workbench_ui.md` §21. After every change to this skill's workbench, in addition to the coze regression gate (SKILL.md §8.5), run the following UI detail audit:

1. **Copy vs. code**: if a topic-box / PICOS hint claims "what the system will do" (e.g. "you can write `P:…` directly"), grep the backend logic (`adapters/block_a.py:_infer_picos` etc.) and verify live — meta-analysis `_infer_picos` only splits on semicolons and does **not** parse `P:/I:` labels, so the topic-box hint must not invite users to write labels (the structured entry point is each page's "PICOS enhancement" collapsible block).
2. **Similar controls → read the handler**: the result-page "✓ Confirm PICOS and re-assess" (`confirmPicos`) and "↻ Re-assess" (`reassess`) must each be checked against the DOM range they read — the former reads `result`, and the latter must also read `result` (an old `↻` silently dropped `result` edits; already fixed); before declaring one redundant, disprove it with real input.
3. **Self-explanatory labels**: the PICOS bilingual toggle is named "显示中英文对照" (not the vague "中英对照").
4. **Placeholders give examples**: missing-dimension placeholders use the `PICOS_EG_ZH/EN` examples ("e.g. …"), never a bare "to be filled".
5. **Dynamic-DOM live browser test**: all of the above must be asserted on real values after a full Playwright interaction path (missing-dimension placeholder = example, red-border class present, still correct after switching language); never rely on static grep or jsdom alone.

Full methodology + machine-check list (red lines / delivery gates / acceptance) → ct-base `references/workbench_ui.md` §21.

### Automated detail-check gate (executable; aligns §21 machine-check catalog)

> The main purpose of §21 is **automated bug checking**, not human review alone. The machine-check engine is the **ct-family shared engine**: `ct-base/scripts/wb_detail_check.py` (zero leaf hard-coding); meta-analysis ships a **byte-identical copy** `scripts/wb_detail_check.py` plus a leaf-specific `scripts/wb_detail_check.rules.json`. Any FAIL = delivery forbidden.

- **Run**: `python scripts/wb_detail_check.py` (auto-locates `workbench.html` and the co-located `wb_detail_check.rules.json`; or `--html <path>` / `--root <dir>` / `--rules <path>`). Note this is a **different script** from the §18.3 structural gate `wb_ui_check.py` (C1–C7, with `--set-version`) — do not confuse or overwrite one with the other.
- **Implemented checks (§21.3.1)**: `C-detail-label` (vague name → FAIL), `C-detail-placeholder` (generic placeholder → FAIL / empty-state generic word → WARN), `C-detail-claim` (input-syntax promise WARN→FAIL), `C-detail-i18n-ph` (single-language static placeholder → WARN), `C-detail-scope` (form-state scope coverage → FAIL, rules-driven).
- **Rule-driven, reusable with zero engine change**: the engine knows none of meta's classes; `scope.selectors=[".picos-in"]`, `scope.values=["seed","result"]` etc. live in `wb_detail_check.rules.json`, enabled item by item. `C-detail-dupctl` is implemented (driven by rules `dupctl.pairs`) but currently off for this skill — enable once the two buttons gain the `dup-verified:` loop.
- **Layered word lists**: family-level default word lists are built into the engine's top constants; meta-specific additions go through rules.json `*_add` / `i18n_whitelist_force`.
- **Regression defense**: temporarily re-inject the "中英对照" label + a "待填" placeholder → 2 FAIL + 1 WARN block (exit 1); real `workbench.html` → 0 FAIL / 0 WARN (incl. scope, exit 0).
- **Live-test fallback** (items the script does not cover): dynamic DOM / similar controls silently dropping data / empty-state guidance — these "no-signal failures" still require the §8.6 item 5 Playwright live-browser assertion.

## Standard QA

> ⚠️ **Migrated to the unified test framework** (2026-10-29): meta-analysis's `tests/qa/` directory has been cleaned up. Testing is now handled by the CT-family unified `ctqa` framework (at `ct-base/testing/ctqa/`), configured in `ctqa.config.json`, entry point `python -m ctqa run --skill meta-analysis`. Implemented layers: **W0** (static analysis, incl. `wb_detail_check.rules.json` rule-driven checks) and **P3** (prompt fidelity, incl. `build_stage_payload` shallow-copy guard, outbound-envelope redaction, parameterized `sample_builder` sampling). Full spec → ct-base `references/workbench_ui.md` §23.

meta-analysis uses the ctqa framework's W0 + P3 two-layer automated tests as the **standard regression gate before publish / after refactor**:

- **W0 static layer**: `wb_detail_check.py` engine + `wb_detail_check.rules.json` rule-driven — covers UI details (label names / placeholder text / input-syntax promises / scope coverage, etc.).
- **P3 prompt-fidelity layer**: offline replica of the outbound pipeline, covering placeholder/literal leakage, literature truncation, k self-consistency, i18n structure, and `build_stage_payload` not mutating the caller's env (a real-bug sentinel; coze_client fixed 2026-10-28).

> Historical value: P3 caught and located a real bug — `coze_client.build_stage_payload` shallow copy + `.pop` (the multi-stage pipeline lost `sm` normalization from stage 2 on, so the R engine fell back to default OR / errored) — fixed 2026-10-28.

## Changelog Sync / 变更日志同步

All version bumps and fixes must be recorded in `CHANGELOG.md`. Security-related fixes are mandatory entries.
