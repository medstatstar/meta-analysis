---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: 医学Meta分析 / Meta Analysis
version: 2.0.5
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。
license: MIT
description: "基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。 / Comprehensive R-based meta-analysis skill covering RevMan 5.x + Stata equivalents (metareg/mvmeta) + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta. Auto-switches language (defaults to English, switches to Chinese in zh-* environments). All analyses ship reproducible R code."

required_commands: [Rscript, python]
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
  - "网络meta"
  - "network meta"
  - "贝叶斯meta"
  - "效应量转换"
  - "单组率meta"
  - "TSA"
  - "诊断meta"
permissions:
  scope: "user-space-only"
  network: "optional"
  network_note: "Default compute path is the coze cloud R engine (requires network). A fully local R fallback (adapters/coze_project) is available ONLY if the user installs R + 14 packages locally — so network is optional only when local R is present; most end-users run via coze. Network is also touched if the user explicitly requests PDF full-text download from DOI/PMID lists (external services), which requires opt-in confirmation of the target list."
  filesystem: "writes only to the current working directory (meta_analysis/ and output/ report artifacts: generated .R scripts, .svg/.png figures, .csv tables); otherwise read-only"
  data: "By default, analysis parameters / summary statistics (event counts, sample sizes, effect sizes) are transmitted to the coze cloud R engine for computation, with a local-R fallback when the endpoint is unavailable or the user opts for local mode. Raw datasets / individual-patient records are only transmitted if the user explicitly chooses to send IPD to the cloud; otherwise processing stays local. R package installation is never performed by this skill — if the user installs packages, that is a manual action in their own R environment."
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "version": "2.0.5",
    "license": "MIT",
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "netmeta", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear", "forestploter"],
  }
---

# Meta-Analysis

> R-based comprehensive meta-analysis. Every module ships reproducible R code.
> **Language**: output auto-switches with the OS locale (zh / en); force-switch via prompt. See `references/language_policy.md` and the bilingual READMEs ([EN](https://github.com/medstatstar/meta-analysis/blob/main/README.md) / [ZH](https://github.com/medstatstar/meta-analysis/blob/main/README_zh-CN.md)).

## 1. Triage — First step: classify the user's intent

On first user message, classify into one of three:

| Classification | Condition | Action |
|---|---|---|
| **Simple** | Single, specific intent (e.g., "pool OR from these 5 studies") | Reply directly, no menu |
| **Complex** | Multi-decision / multi-parameter (e.g., "network meta with 3 interventions, subgroup, check inconsistency") | Present level-1 routing menu incl. "③ Can't decide? → explain the differences between these choices" entry; full menu → `references/interactive_menu.md` |
| **Vague** | Unclear what user wants (e.g., "I need meta-analysis help") | Grill-me style branch questions, 1–3 per round; "无选题/可行性评估" → **Topic Selection** (section 2.2) |

If unsure between Simple and Complex → give short reply + optional expansion hint.

## 2. Conversation guide

### 2.1 Interactive menu
Vague → Level 1 menu (7 categories). Select → Level 2 with data-format hints. Sufficient info → skip menu, run analysis directly. Full menu tree + data formats → `references/interactive_menu.md`.
> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

### 2.2 Topic Selection (upstream gate)
Trigger: user wants a meta-analysis but has no topic ("我想做 Meta 但没选题") / feasibility check / "被拒为重复了" (rejected as duplicate) / pre-PROSPERO audit → `references/topic-selection.md`. Two paths:
- **Quick** (≤30 min): 1-page decision card — 4-dim scores (clinical/feasibility/data/novelty, 0–5 each, 0–20, any ≤2 = veto) + screen verdict. No final go/no-go.
- **Full** (5 stages + gates): PICO (`pico-guide.md`) → scoring + cross-checks R1–R6 → dedup (`dedup-search.md`: PROSPERO→Cochrane→PubMed; non-English opt-in) → PRISMA 2020/AMSTAR-2 (`compliance-precheck.md`) → 11-section report via `python scripts/generate_topic_report.py input.json output.md|html` (template + PROSPERO mapping → `topic-report-template.md` / `prospero-mapping.md`).
- ⚠️ Dedup searches run ONLY on user opt-in; otherwise deliver query templates.

## 3. Initialization & execution backend

**Execution model (coze-only)**: all numerical computation runs through the coze meta-analysis workflow (R engine on the coze side); the local LLM only normalizes the request, tidies data, and presents results + SVG figures — **end users need no R install and no local compute**. Every analysis returns a `repro` field (reproducible R script + R + package versions).

**On startup**:
1. **Backend**: default coze endpoint `https://ct-meta.coze.site/run` (overridable via `COZE_META_ENDPOINT`). Probe reachability with `coze_client.health()`.
2. **Workspace**: create `meta_analysis/` + `output/` (⚠️ writes files: reports and SVG/CSV).
3. **Memory**: read R-related config keys from `~/.workbuddy/MEMORY.md` (R config only; unrelated personal content is ignored and never sent).

Local R environment, package list, endpoint self-test, etc. (developer details) → `references/ADVANCED.md` · `references/ADVANCED_zh-CN.md`.

## 4. Core functions & API

Module → R-package/function matrix (single-group / pairwise / effect-size / forest·funnel / heterogeneity / publication-bias / subgroup·meta-reg / sensitivity / Bayesian pairwise·NMA / multilevel·MV / survival / TSA / dose-response / diagnostic / RVE / RoB+GRADE / power / quality-gate) → `references/advanced_api.md` · `references/ADVANCED.md`.

**Rule (mandatory)**: any analysis MUST call existing functions — never rewrite inline. Unified entry `adapters/run_analysis.py` (default: coze). Function list + call examples → `references/advanced_api.md`.

## 5. Output specification

**Artifacts**: `analysis_complete.R` + forest/funnel (`.svg`) + `results_summary.md` + `data_backup.csv` (written to `output/`); PNG only generated in local conversion mode.

**Rendering**: all `figures[].svg` are **inlined into the conversation** and also saved to `output/` for download. Figures keep original size (no scaling); overflow → horizontal scrollbar (x pad=8, y pad_y=24). Inline-rendering standard → `references/inline_rendering.md`; SVG editing/journal-format conversion → `references/svg_editing.md`.

**LLM presentation-layer hard constraints (mandatory)**:
1. **Quote numbers verbatim**: values in `stats`/`pooled`/`heterogeneity`/`bias` MUST be cited exactly — no rewriting, rounding, or recomputation.
2. **Prefer verbatim standard labels**: adopt coze's bilingual template wording directly; do not re-translate.
3. **Do only two things**: organize the template wording into fluent user language + add one explanatory sentence as needed; the explanation must not override or alter template numbers.

**Quality Gate (human sign-off)**: before presenting pooled estimates, the R side runs `run_quality_gate()` → gate JSON; red (k<3 / I²>75% / missing bias check) **blocks** presentation — released only after manual confirmation. Numeric judgments are made by R, never read by the LLM.

figure_mode (`svg_inline` / `png_file`) and render-timing thresholds (implementation details) → `references/ADVANCED.md`.

## 6. Security & scope

**Execution model**:
- **Default**: numeric computation via the coze workflow. The skill sends an analysis request (task/data/params/figure) and retrieves structured results. Common inputs are summary statistics (2×2 tables, effect sizes + SE); user-provided individual-patient data (IPD) is also supported. Numeric judgments are made by R, never read by the LLM.
- **Data-exfiltration decision belongs to the user**: the skill **only implements the function + transparent disclosure**, **never acts as a safety/compliance gate** — whether data (incl. IPD) may be sent to coze is the user's call.

**Outbound disclosure (global mandatory)**:
- **What is sent**: analysis data (study event counts / sample sizes / effect sizes; no personal identifiers) POSTed to the coze endpoint. Payloads are sanitized by `sanitize_payload()` (strips PII: ID numbers / phone / email) before sending.
- **Authorization**: the default endpoint is pre-approved in the whitelist (`adapters/config.json` `auto_approve_endpoints`, author-preapproved, invisible to the user); a **custom endpoint (`COZE_META_ENDPOINT`) asks for AUTH-BLOCK confirmation on first call**, then is written to the whitelist, no confirmation needed for the rest of the session. **Unauthorized does not block**: `run_analysis` returns `_source=auth_blocked` with an explicit "cloud analysis not used" message.
- **First outbound notice each session (exactly one, never repeated)** — bilingual copy (auto-switch by locale); output verbatim. EN: `I will send your analysis parameters to the cloud service https://ct-meta.coze.site/run for computation, together with a hostname hash (query_origin, used only for server-side attribution / rate-limiting, not your plaintext hostname). Please wait…`. No repeat disclosure for later outbound calls in the same session.
- **Coze failure diagnosis requires prior consent**: when coze returns failure/timeout/proxy error, **first ask the user** (bilingual, auto-switch by locale). EN: `The coze cloud service is temporarily unavailable. May I automatically diagnose the issue?`; allowed → diagnose and fix + retry; declined → deliver the local answer with a prominent warning (bilingual). EN: `Unable to reach the coze service; this answer has not been curated and should be used with caution`.

**Other boundaries**:
- PDF full-text download from external services ONLY on **explicit user instruction** (`adapters/pdf_fetch.py`, opt-in).
- **Not clinical judgment**: results require professional interpretation.
- **No literature DB search**: does not search literature databases; only downloads full text when the user provides DOI/PMID.
- Analysis artifacts written to `meta_analysis/` + `output/` by default.

## 7. User-uploaded files

Two upload types, two paths:
1. **Structured data files (`.csv` / `.xlsx` / `.xls`)** → **Type 4 data template** (`references/data_templates.md`: encoding detection / zh-en column matching / missing-value detection / row-count confirmation). These are analysis data — §6.7 doc→md conversion does not apply; §6.7.2 transparency and §6.7.3 confidentiality boundaries still apply.
2. **Document / template files (`.docx` / `.pptx` / `.pdf` / `.doc`)** → convert to md/text first, then extract study data (§6.7.1 layered strategy):
   - `.docx` / `.pptx` → `python scripts/office_to_md.py <file>` (shared converter)
   - `.pdf` → environment `pdf` skill (text extraction; scanned pages need OCR); if absent → prompt the user to install it, never write a custom PDF parser
   - `.doc` (legacy OLE) → prompt to install word-reader / antiword
   - Image/scanned-only (no text layer) → prompt the user to provide a text version

**🔔 Pre-conversion user notice (§6.7.2, show before converting)** — bilingual copy (auto-switch by locale). EN: `⚠️ All uploaded documents will be converted to md format. PPT conversion can lose a lot of information (images, layout, animations, charts, etc.). We recommend converting to md yourself and checking the content first.`

**Confidentiality (§6.7.3)**: the skill **never proactively judges/blocks** upload confidentiality — documents convert and data reads as usual; whether it leaves the machine is the user's decision. Content sent to coze is disclosed on first outbound; **whether IPD and other individual data goes to the cloud is the user's call**.

**Figure format (2026-08-20 tightened)**: the engine always returns SVG (adapter forces `figure.format="svg"`, overriding even a png request); PNG is always converted by the local presentation layer.

## 8. Bug Reporting

Agent behavior only; implementation → `adapters/bug_report.py`, protocol → `references/bug_report_endpoint.md`.

- **Trigger (strong signal, max 1 proposal/session):** unexpected non-zero exit / engine or compute error / user explicitly questions the result — **and** the same operation was retried ≥1. Weak signal (repeated tuning) never triggers. Explicit user request (e.g., "report a bug") also triggers, without the once-per-session limit.
- **Two-stage confirmation:** ① propose-with-preview — show the bilingual `confirm_prompt` **with** the full sanitized report (`render_report_text`); user may add a `description` (re-render & re-show before consent) → ② on explicit consent, `send_to_endpoint` (action=report, endpoint `https://ct-bugreport.coze.site/run`). If declined, never re-propose this session.
- **Sanitization is hard:** report carries only the 11-key whitelist (skill / version / error_type / error_code / engine_status / description / locale / query_origin / session_hash / attempts / test) — never raw data or subject records. `description` is the only free-text field, **user-reviewed**; hard boundary: no identifiable person/institution/subject info. If the session had **no** cloud call, `save_local_report()` writes locally (data never leaves the machine).
- **Client-only:** send `report` only. Governance actions (get/update/download/delete) are reserved for `ct-update`; never call them here.

## 9. Meta information

**Traceability / Grounding**: all factual/assertive claims must cite source — a specific `ref-*.md` section or official guideline. An unverifiable claim → mark `⚠️ official verify` and ask the user to confirm.

**References**: full index → `references/references.md`. Key files: `interactive_menu.md`, `ADVANCED.md`/`ADVANCED_zh-CN.md`, `advanced_api.md`, `topic-selection.md`, `data_templates.md`, `svg_editing.md`. Units schema (input / output / dependency / AI autonomy / consumer units) → `references/units.md`.

**Project Files**: `README.md` | `README_zh-CN.md` | `CHANGELOG.md` | `AGENTS.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`.

**Changelog**: version/fix log → `CHANGELOG.md`.
