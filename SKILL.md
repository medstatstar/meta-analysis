---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: 医学Meta分析 / Meta Analysis
version: 2.2.22
license: MIT
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta等共 23 种分析图形。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。
description: "基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta等共 23 种分析图形。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。 / Comprehensive R-based meta-analysis skill covering RevMan 5.x + Stata equivalents (metareg/mvmeta) + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta, for a total of 23 analysis figures. Auto-switches language (defaults to English, switches to Chinese in zh-* environments). All analyses ship reproducible R code."

required_commands: [python]
invocable: true

triggers:
  - "meta分析"
  - "meta-analysis"
  - "系统评价"
  - "森林图"
  - "漏斗图"
  - "异质性"
  - "发表偏倚"
  - "元回归"
  - "network meta"
  - "贝叶斯meta"
  - "效应量转换"
  - "TSA"
  - "诊断meta"
permissions:
  scope: "user-space-only"
  network: "required (all computation via coze cloud R engine; params/summary stats sent to coze, no local-R fallback; IPD only if user opts in)"
  filesystem: "writes only to the current working directory (meta_analysis/ and output/ report artifacts: generated .R scripts, .svg/.png figures, .csv tables); otherwise read-only"
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "netmeta", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear", "forestploter"],
  }
---

# Meta-Analysis

> R-based comprehensive meta-analysis. Every module ships reproducible R code.

## Language

- **English guide** → [README.md](https://github.com/medstatstar/meta-analysis/blob/main/README.md) · **中文指南** → [README_zh-CN.md](https://github.com/medstatstar/meta-analysis/blob/main/README_zh-CN.md)
- Bilingual auto-switch: the answer language follows the user's question language (English question → English answer, Chinese question → Chinese answer).

## 0. Execution discipline (speed-first)

> 🚀 **Top-level red line — higher priority than any "thinking/polishing" impulse. Violation = wasting the user's time.** Full boundaries/exceptions/anti-patterns in `references/speed-discipline.md`.

### Two-track gating (code-driven routing, no LLM decision)
The first message goes through `python scripts/classify.py` for **deterministic triage** (zero LLM decision):
- **Compute track (compute)**: clear Simple / Complex → describe and immediately run `run_meta.py --query --data`; three steps to completion, fully bound by this discipline.
- **Topic track (topic)**: vague / topic selection / feasibility → `literature_probe.py` + `generate_topic_report.py`; code-grounded, zero free-form improvisation.
- Both tracks forbid reading source via Read/Grep/Bash to "confirm how to tune / which task to use" — that is `classify.py`'s job.

### Agent operation card (copy verbatim, no variations)
```bash
# Compute track one-shot: report lands in --out-dir (user workspace); in-conversation data uses --data-json to skip file writes.
# If data comes from a file, pass --data <csv|json absolute path> (csv auto-converts to JSON before sending to coze).
python scripts/run_meta.py --query "<user original request>" --data-json '<[{"study":"S1",...}]>' --out-dir "<user workspace>/meta_analysis"
```
Read `META_HTML_REPORT=<path>` from stdout and pass directly to `present_files`; across turns, carve a subset into a new csv/json and re-issue the same command (always include `--out-dir`). Do NOT use this card for the topic track. Fallback `META_STATUS=build_failed` → re-run with `--colmap` per the hint.

### Five iron rules
1. **Execute, don't think**: when running the skill, only perform the workflow; no reasoning/trade-off/review/self-explanation; if a field is missing, ask only about that field.
2. **Zero number rewriting**: cite `stats`/`pooled`/`heterogeneity`/`bias` verbatim; no rounding/conversion/re-formatting.
3. **HTML report is the sole presentation surface**: `out['html_report']` is the final deliverable; no further processing; inline `show_widget` is deprecated, figures only appear in the HTML.
4. **No local computation**: disable local R/Python self-computation; always forward to coze; if coze is unreachable, raise a structured error per §6, never fall back to local.
5. **Call-count invariant**: compute track ≤1 call before fire (only `build_request`), ≤1 call after fire (only `present_files`); topic track ≤2; no retry loops. Cross-turn `--data-json` refill is input construction and does not count.

### Already automated / anti-patterns (see `references/speed-discipline.md`)
Subgroup columns auto-pass-through, column-name aliases auto-matched, artifact completeness guaranteed by `run_analysis` — the agent must not read source to verify, must not hand-assemble subgroup into request.json, must not declare "missing Q_between" each round (go straight to metareg).

## 1. Triage — First step: classify the user's intent

> **Routing is already done in code (§0 two-track gating)**: track / task judgment is delegated to `build_request.py` (which calls `classify.py`); the LLM no longer makes routing decisions and does not hand-write request.json. The table below is for understanding only — the LLM calls `run_analysis` directly from the generated `request.json` and `present_files(html)`.

| Classification | Condition | Action |
|---|---|---|
| **Simple** | Single, specific intent (e.g., "pool OR from these 5 studies") | Reply directly, no menu |
| **Complex** | Multi-decision / multi-parameter (e.g., "network meta with 3 interventions, subgroup, check inconsistency") | Present level-1 routing menu incl. "③ Can't decide? → explain the differences"; full menu → `references/interactive_menu.md` |
| **Vague** | Unclear what user wants (e.g., "I need meta-analysis help") | Grill-me branch questions, 1–3 per round; "no topic / feasibility" → **Topic Selection** (§2.2) |

If unsure between Simple and Complex → give short reply + optional expansion hint.

## 2. Conversation guide

### 2.1 Interactive menu
Vague → Level 1 menu (7 categories). Select → Level 2 with data-format hints. Sufficient info → skip menu, run directly. Full menu tree + data formats → `references/interactive_menu.md`.
> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

### 2.2 Topic Selection (upstream gate, self-contained)
Trigger: no topic / feasibility check / "rejected as duplicate" / pre-PROSPERO audit → `references/topic-selection.md`. Two paths:
- **Quick** (≤30 min): 1-page decision card — 4-dim scores (clinical/feasibility/data/novelty, 0–5, any ≤2 = veto) + screen verdict.
- **Full** (5 stages + gates): PICO (`pico-guide.md`) → scoring + cross-checks R1–R6 → dedup (`dedup-search.md`) → PRISMA 2020/AMSTAR-2 (`compliance-precheck.md`) → 11-section report via `python scripts/generate_topic_report.py input.json output.md|html` (templates → `topic-report-template.md` / `prospero-mapping.md`).
- **Dedup self-contained**: Stage 4 runs in-skill Europe PMC probe `adapters/literature_probe.py` (real hit counts + top titles) by default; novelty ranking grounded in actual literature. Comprehensive retrieval → use **ct-literature** skill first.
  - ⛔ **Topic-track red line**: candidate ranking **must** be based on the probe's real hit counts + 4-dim score card; the LLM only paraphrases, strictly no free-form "which direction is good". Quick is ranked by the probe card; Full is reported by `generate_topic_report.py`, the LLM does not rewrite.

## 3. Initialization & execution backend

**Execution model (coze-only, absolute)**: all numerical computation runs through the coze meta-analysis workflow (R engine on coze side); local LLM only normalizes request + presents results/SVG. End users need no R install. Every analysis returns a `repro` field (R script + versions). No local computation — see §0 iron rule 4.
**On startup**: 1. Backend default `https://ct-meta.coze.site/run` (override `COZE_META_ENDPOINT`); probe via `coze_client.health()`. 2. Workspace: create `meta_analysis/` + `output/`. 3. Memory: read R config from `~/.workbuddy/MEMORY.md` (R only).
Endpoint self-test / R engine details → `references/ADVANCED.md` · `references/ADVANCED_zh-CN.md`.

## 4. Core functions & API

Module → R-package/function matrix → `references/advanced_api.md` · `references/ADVANCED.md`.
**Rule (mandatory)**: any analysis MUST call existing functions — never rewrite inline. Unified entry `adapters/run_analysis.py` (default: coze). List + examples → `references/advanced_api.md`.

## 5. Output specification

**Artifacts**: `analysis_complete.R` + forest/funnel (`.svg`, inlined in HTML) + `results_summary.md` + `last_run.json` (full request+result echo, in `output/`). Per-round dataset CSV is an *input* the agent carves (e.g. `filtered_mdd.csv`); `run_analysis.py` does NOT auto-write `data_backup.csv`.

**Rendering (HTML report sole surface)**: `figures[].svg` embedded into the single-file HTML report (`run_analysis`→`out['html_report']`), opened with `present_files`. Inline `show_widget` cancelled; SVG keeps natural width (never upscale to 680px; overflow scrolls). S3 offloading is transport-only — `_coze_truncated` present → truncation warning atop report.
**LLM presentation hard constraints**: ① numbers verbatim (stats/pooled/heterogeneity/bias, no rewrite); ② figures only via HTML report.
**Quality Gate**: R-side `run_quality_gate()` → gate JSON; red (k<3 / I²>75% / missing bias check) **blocks** presentation until manual confirmation. Numeric judgment by R, never read by LLM.
figure_mode / render-timing → `references/ADVANCED.md`; inline/figure spec → `references/inline_rendering.md`.

## 5.1 Cross-turn Continuity (mandatory)

> **Runtime is stateless.** coze R engine re-supplies `task`+`data`+`params` each call, never persists config/column mapping. Semantic drift (model/method silently changing) = highest-risk failure.

#### Cross-turn spec (minimal unit maintained within the conversation thread)
```
{"task":"pairwise_meta","data_path":"<current-round csv>","measure":"OR","model":"random","method":"REML","subgroup":"—"}
```
(yi/sei/slab column mapping is already auto-derived by `build_request.py`; no explicit inheritance needed; `run_meta.py` is self-sufficient from query+data each time.)

#### Three hard rules
1. **Echo a "Current analysis settings" block after every analysis (mandatory, after this round's numbers/figures):**
   `## Current analysis settings: data=<csv> | measure=OR | model=random | method=REML | subgroup=— | task=pairwise_meta`
   No field omitted (`—` placeholder) — lets LLM locate "most recent settings" on follow-up.
2. **On follow-up, change only the changed fields:** locate most recent `## Current analysis settings:` block, read all fields, override only what changed (e.g. `task←subgroup_analysis`, `subgroup←region`); yi/sei/slab + model/method/measure inherited verbatim — dropping column mapping = effect-size mismatch.
3. **Dataset supplied per round, not by magic pointer:** no auto `data_backup.csv`; carve subset into new csv + re-issue `run_meta.py` at it.

#### Deterministic fallback
Worried about dropping config? `scripts/merge_spec.py` (prev+cur via stdin → merged spec):
```bash
echo '{"prev":{"task":"pairwise_meta","data_path":"<csv>","measure":"OR","model":"random","method":"REML","subgroup":"—"},"cur":{"task":"subgroup_analysis","subgroup":"region"},"required":["task","data_path","measure","model","method","subgroup"]}' | python scripts/merge_spec.py
```

#### Endpoint capability boundaries (per coze `run_task.R` / `coze_contract.md` §3)
- `pairwise_meta` ✅ complete (I²/τ², Egger/Begg, funnel plot, quality gate)
- `subgroup_analysis` ✅ subgroup column **must** be passed as the param key `subgroup` (writing byvar/group/by silently fails)
- `metareg` ✅ requires effect-size columns te/sete + covariate column `params.cov` (passing only raw columns degrades to pairwise_meta)
- `nma` ✅ (≥2 arms per study); `nma_rank` ✅ (SUCRA/P-score); `survival_meta` ✅ (loghr/seloghr); `diagnostic_meta` ✅ (tp/fp/fn/tn, task name is not "diagnostic")
- publication bias is embedded in pairwise_meta/funnel_plot; `sensitivity`/`pub_bias` are not registered tasks
- default figures adapt to the task (`build_request` requests per `figure.plots`; override via `params_extra.plots`)
> Few-shot samples → `references/interactive_menu.md` §6.

## 6. Security & scope

**Execution model**: numeric computation via coze (LLM only normalizes + presents; numbers judged by R). **Data-exfiltration decision belongs to the user** — skill implements function + transparent disclosure, never a compliance gate.

**Outbound disclosure (global mandatory)**:
- **What is sent**: analysis data (event counts / sample sizes / effect sizes; no PII) POSTed to coze; sanitized by `sanitize_payload()` (strips ID/phone/email) first.
- **Authorization**: default endpoint pre-approved in whitelist; custom `COZE_META_ENDPOINT` asks AUTH-BLOCK on first call, then whitelisted. Unauthorized → `_source=auth_blocked` with "cloud analysis not used" message.
- **First outbound notice each session (once, bilingual)**: `I will send your analysis parameters to the cloud service https://ct-meta.coze.site/run for computation, together with a hostname hash (query_origin, for attribution/rate-limiting only). Please wait…` No repeat.
- **Coze failure needs consent**: on failure/timeout, first ask (bilingual) `The coze cloud service is temporarily unavailable. May I automatically diagnose the issue?`; allowed → diagnose+retry; declined → deliver local answer with warning.

**Other boundaries**: PDF full-text download ONLY on explicit user instruction (`adapters/pdf_fetch.py`, opt-in). Not clinical judgment. No literature DB search (downloads full text only when user provides DOI/PMID).

## 7. User-uploaded files

1. **Structured data (`.csv`/`.xlsx`/`.xls`)** → Type 4 template (`references/data_templates.md`: encoding / zh-en column match / missing-value / row-count).
2. **Document/template (`.docx`/`.pptx`/`.pdf`/`.doc`)** → convert to md first: `.docx`/`.pptx` via `scripts/office_to_md.py`; `.pdf` via `pdf` skill (OCR for scans); `.doc`/scans → ask user for text version.
**🔔 Pre-conversion notice (bilingual)**: `⚠️ All uploaded documents will be converted to md. PPT conversion can lose images/layout/animations/charts. We recommend converting yourself and checking first.`
**Confidentiality**: skill never proactively judges/blocks upload confidentiality; whether IPD goes to coze is the user's call.

## 8. Bug Reporting

Agent behavior only; implementation → `adapters/bug_report.py`, protocol → `references/bug_report_endpoint.md`.
- **Trigger (≤1 proposal/session):** unexpected non-zero exit / engine error / user questions result — **and** retried ≥1. Explicit "report a bug" also triggers (no limit).
- **Two-stage confirmation:** ① propose-with-preview (bilingual `confirm_prompt` + full sanitized report) → ② on consent `send_to_endpoint` (`https://ct-bugreport.coze.site/run`). Declined → never re-propose.
- **Sanitization hard:** 11-key whitelist only, never raw data/subject records; `description` is the only free-text field, user-reviewed. No cloud call → `save_local_report()` (stays local).

## 8.5 Deploy Retest Gate (mandatory before publish / deploy)

**Mandatory before publishing / deploying** to GitHub → SkillHub → ClawHub: run `python tests/deploy_retest.py` (`--live` to actually hit the network; publish allowed only on all-green). This gate strictly verifies that the coze response is **genuinely valid** (HTTP 200 ≠ success; it rejects `status=ok` empty shells / `NaN` / no-figure (svg/url) false greens — coze externalizes SVG to S3 `url`, so a present+reachable `url` counts as a valid figure), writes `tests/deploy_retest_report.json`, and exits non-zero on any failure to block publishing. Use `--mock` for local logic self-check (no network) and `--offline` for envelope-contract validation. Full rules and red lines → `outputs/deploy_retest_gate.md`.

## 9. Meta information

**Traceability**: all factual claims cite a `ref-*.md` section or official guideline; unverifiable → mark `⚠️ official verify`.
**References**: full index → `references/references.md`. Key: `interactive_menu.md`, `ADVANCED.md`/`ADVANCED_zh-CN.md`, `advanced_api.md`, `topic-selection.md`, `data_templates.md`, `svg_editing.md`. Units → `references/units.md`.
**Project Files**: `README.md` | `README_zh-CN.md` | `CHANGELOG.md` | `AGENTS.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`.
**Changelog**: → `CHANGELOG.md`.
