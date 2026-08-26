---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: 医学Meta分析 / Meta Analysis
version: 2.1.5
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。
license: MIT
description: "基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。 / Comprehensive R-based meta-analysis skill covering RevMan 5.x + Stata equivalents (metareg/mvmeta) + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta. Auto-switches language (defaults to English, switches to Chinese in zh-* environments). All analyses ship reproducible R code."

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
  network_note: "All numerical computation runs in the coze cloud R engine (requires network). There is no local-R fallback — if coze is unreachable or unauthorized, the skill returns a structured error instead of silently computing locally. End users need no local R install. Network is also touched if the user explicitly requests PDF full-text download from DOI/PMID lists (external services), which requires opt-in confirmation of the target list."
  filesystem: "writes only to the current working directory (meta_analysis/ and output/ report artifacts: generated .R scripts, .svg/.png figures, .csv tables); otherwise read-only"
  data: "By default, analysis parameters / summary statistics (event counts, sample sizes, effect sizes) are transmitted to the coze cloud R engine for computation. Raw datasets / individual-patient records are only transmitted if the user explicitly chooses to send IPD to the cloud; otherwise processing stays local. There is no local-R fallback — if coze is unreachable or unauthorized, the skill returns a structured error. R package installation is never performed by this skill (the coze-side engine manages its own packages)."
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "version": "2.1.5",
    "license": "MIT",
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "netmeta", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear", "forestploter"],
  }
---

# Meta-Analysis

> R-based comprehensive meta-analysis. Every module ships reproducible R code.

## Language

- **English guide** → [README.md](https://github.com/medstatstar/meta-analysis/blob/main/README.md) · **中文指南** → [README_zh-CN.md](https://github.com/medstatstar/meta-analysis/blob/main/README_zh-CN.md)
- Bilingual auto-switch: the answer language follows the user's question language (English question → English answer, Chinese question → Chinese answer).

## 1. Triage — First step: classify the user's intent

On first user message, classify into one of three:

| Classification | Condition | Action |
|---|---|---|
| **Simple** | Single, specific intent (e.g., "pool OR from these 5 studies") | Reply directly, no menu |
| **Complex** | Multi-decision / multi-parameter (e.g., "network meta with 3 interventions, subgroup, check inconsistency") | Present level-1 routing menu incl. "③ Can't decide? → explain the differences between these choices" entry; full menu → `references/interactive_menu.md` |
| **Vague** | Unclear what user wants (e.g., "I need meta-analysis help") | Grill-me style branch questions, 1–3 per round; "no topic / feasibility check" → **Topic Selection** (section 2.2) |

If unsure between Simple and Complex → give short reply + optional expansion hint.

## 2. Conversation guide

### 2.1 Interactive menu
Vague → Level 1 menu (7 categories). Select → Level 2 with data-format hints. Sufficient info → skip menu, run analysis directly. Full menu tree + data formats → `references/interactive_menu.md`.
> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

### 2.2 Topic Selection (upstream gate, self-contained)
Trigger: user wants a meta-analysis but has no topic ("I want to do a meta-analysis but have no topic") / feasibility check / "rejected as a duplicate" / pre-PROSPERO audit → `references/topic-selection.md`. Two paths:
- **Quick** (≤30 min): 1-page decision card — 4-dim scores (clinical/feasibility/data/novelty, 0–5 each, 0–20, any ≤2 = veto) + screen verdict. No final go/no-go.
- **Full** (5 stages + gates): PICO (`pico-guide.md`) → scoring + cross-checks R1–R6 → dedup (`dedup-search.md`) → PRISMA 2020/AMSTAR-2 (`compliance-precheck.md`) → 11-section report via `python scripts/generate_topic_report.py input.json output.md|html` (template + PROSPERO mapping → `topic-report-template.md` / `prospero-mapping.md`).
- **Dedup is self-contained (no other skill needed)**: Stage 4 runs the in-skill Europe PMC probe `adapters/literature_probe.py` (Cochrane + PubMed layers) by **DEFAULT** — it returns real hit counts + top titles, so the novelty ranking (R7) is grounded in actual literature. No delegation to other skills; templates are only a fallback when the network is unavailable. PROSPERO / non-English DBs remain guided manual steps (no clean public API).
  - ⚠️ The probe is a **quick dedup check** (real hit counts + top titles), **not** a full retrieval. For comprehensive retrieval — anti-hallucination verification / merge-dedupe / Excel·HTML report / PRISMA screen — use the **ct-literature** skill first (same Europe PMC journal filter, consistent Cochrane counts; its `--cochrane` flag is the counterpart of this probe). The probe's JSON already emits a `ct_handoff` block with the ready-to-run commands.

## 3. Initialization & execution backend

**Execution model (coze-only)**: all numerical computation runs through the coze meta-analysis workflow (R engine on the coze side); the local LLM only normalizes the request, tidies data, and presents results + SVG figures — **end users need no R install and no local compute**. Every analysis returns a `repro` field (reproducible R script + R + package versions).

**On startup**:
1. **Backend**: default coze endpoint `https://ct-meta.coze.site/run` (overridable via `COZE_META_ENDPOINT`). Probe reachability with `coze_client.health()`.
2. **Workspace**: create `meta_analysis/` + `output/` (⚠️ writes files: reports and SVG/CSV).
3. **Memory**: read R-related config keys from `~/.workbuddy/MEMORY.md` (R config only; unrelated personal content is ignored and never sent).

Endpoint self-test, coze-side R engine & package details (developer details) → `references/ADVANCED.md` · `references/ADVANCED_zh-CN.md`.

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

### 5.1 Cross-turn Continuity (mandatory)

> **Runtime is stateless.** The coze R engine is stateless: each `run_analysis.py` call re-supplies `task` + `data` + `params`, and the engine never persists the analysis config or column mapping. Semantic drift (model / method / measure changing silently between rounds) = silently inconsistent results — the highest-risk failure mode in this prompt-driven flow.

When the user follows up across rounds (subgroup / sensitivity / meta-regression / NMA / diagnostic meta / TSA …), the prior round's analysis spec MUST be inherited losslessly — **never rely on the LLM's memory alone**.

#### Cross-turn spec (minimal unit maintained inside the conversation thread)
```
{
  "task": "forest",                       # analysis task (forest/sensitivity/subgroup/metareg/nma/diagnostic/tsa…)
  "data_path": "output/data_backup.csv",  # dataset pointer (persisted on disk; only the path is inherited across rounds, not the data body)
  "measure": "OR",                        # R sm (OR/RR/SMD/MD/HR…)
  "model": "random",                      # fixed / random
  "method": "REML",                       # estimation method (DL/REML/HE/SJ…)
  "yi": "eff", "sei": "se", "slab": "study",  # column mapping: dataset columns → effect size / SE / study label
  "byvar": "—",                           # subgroup / meta-reg variable column (— if none)
  "...": "other params passed through"    # subgroup / reference_group / k_min etc., vary by task
}
```

#### Three hard rules
1. **Echo a "Current analysis settings" block after every analysis (mandatory, placed after this round's numbers/figures):**
   `## Current analysis settings: data=output/data_backup.csv | measure=OR | model=random | method=REML | yi=eff | sei=se | slab=study | byvar=— | task=forest`
   No field may be omitted (use `—` as placeholder). This lets the LLM locate the "most recent settings block" via the `## Current analysis settings:` prefix when the user follows up.
2. **On follow-up, change only the changed fields:** the LLM MUST first locate the most recent `## Current analysis settings:` block in the conversation, read all its fields, and override only what changed (e.g. `task←subgroup / byvar←age`, `task←sensitivity`). **Column mapping (yi/sei/slab) and model/method/measure are inherited verbatim** — dropping the column mapping = effect-size mismatch = silently inconsistent results (a statistical-conclusion-level defect, the highest-risk point).
3. **Dataset is inherited by pointer, not re-transmitted:** `data_backup.csv` is already on disk. On follow-up the LLM re-reads the CSV via `data_path` (to get column names + rows); the column mapping (yi/sei/slab) is inherited from the settings block (the CSV carries only column names, no "which column is the effect size" semantic annotation, so it cannot be inferred by reading the CSV).

#### Deterministic fallback (recommended, not optional)
When worried about dropping config / column mapping, use `scripts/merge_spec.py` (bundled in this skill's `scripts/`) for a deterministic merge:
prior-round spec JSON (`prev`) + this-round partial (`cur`) via stdin → complete merged spec; state passes only through the conversation thread, never persisted.
```bash
echo '{"prev":{"task":"forest","data_path":"output/data_backup.csv","measure":"OR","model":"random","method":"REML","yi":"eff","sei":"se","slab":"study","byvar":"—"},"cur":{"task":"subgroup","byvar":"age"},"required":["task","data_path","measure","model","method","yi","sei","slab"]}' \
  | python scripts/merge_spec.py
# → merged inherits all fields, byvar overridden to age; if both prev/cur miss yi/sei/slab → missing_required error
```
Field inheritance / reset conventions when switching `task` (forest→subgroup / →metareg / →nma / →diagnostic / →tsa) → `references/interactive_menu.md` §6.4.

> Full few-shot continuity samples (with each round's echo block) → `references/interactive_menu.md` §6.

## 6. Security & scope

**Execution model**: numeric computation via the coze workflow (R engine; the LLM only normalizes requests and presents results — numbers are judged by R, never read by the LLM). **Data-exfiltration decision belongs to the user**: the skill only implements the function + transparent disclosure, never a safety/compliance gate — whether data (incl. IPD) may go to coze is the user's call.

**Outbound disclosure (global mandatory)**:
- **What is sent**: analysis data (study event counts / sample sizes / effect sizes; no personal identifiers) POSTed to the coze endpoint. Payloads are sanitized by `sanitize_payload()` (strips PII: ID numbers / phone / email) before sending.
- **Authorization**: the default endpoint is pre-approved in the whitelist (`adapters/config.json` `auto_approve_endpoints`, author-preapproved, invisible to the user); a **custom endpoint (`COZE_META_ENDPOINT`) asks for AUTH-BLOCK confirmation on first call**, then is written to the whitelist, no confirmation needed for the rest of the session. **Unauthorized does not block**: `run_analysis` returns `_source=auth_blocked` with an explicit "cloud analysis not used" message.
- **First outbound notice each session (exactly one, never repeated)** — bilingual copy (auto-switch by locale); output verbatim. EN: `I will send your analysis parameters to the cloud service https://ct-meta.coze.site/run for computation, together with a hostname hash (query_origin, used only for server-side attribution / rate-limiting, not your plaintext hostname). Please wait…`. No repeat disclosure for later outbound calls in the same session.
- **Coze failure diagnosis requires prior consent**: when coze returns failure/timeout/proxy error, **first ask the user** (bilingual, auto-switch by locale). EN: `The coze cloud service is temporarily unavailable. May I automatically diagnose the issue?`; allowed → diagnose and fix + retry; declined → deliver the local answer with a prominent warning (bilingual). EN: `Unable to reach the coze service; this answer has not been curated and should be used with caution`.

**Other boundaries**:
- PDF full-text download from external services ONLY on **explicit user instruction** (`adapters/pdf_fetch.py`, opt-in).
- **Not clinical judgment**: results require professional interpretation.
- **No literature DB search**: does not search literature databases; only downloads full text when the user provides DOI/PMID.

## 7. User-uploaded files

Two upload types, two paths:
1. **Structured data files (`.csv` / `.xlsx` / `.xls`)** → **Type 4 data template** (`references/data_templates.md`: encoding detection / zh-en column matching / missing-value detection / row-count confirmation). These are analysis data — the doc→md conversion tier does not apply; the pre-conversion transparency notice and confidentiality boundary still apply.
2. **Document / template files (`.docx` / `.pptx` / `.pdf` / `.doc`)** → convert to md/text first, then extract study data: `.docx`/`.pptx` via `scripts/office_to_md.py`; `.pdf` via the `pdf` skill (OCR for scans; prompt to install if absent — never write a custom parser); `.doc`/scanned images → prompt the user for a text version.

**🔔 Pre-conversion user notice (show before converting)** — bilingual copy (auto-switch by locale). EN: `⚠️ All uploaded documents will be converted to md format. PPT conversion can lose a lot of information (images, layout, animations, charts, etc.). We recommend converting to md yourself and checking the content first.`

**Confidentiality:** the skill **never proactively judges/blocks** upload confidentiality — documents convert and data reads as usual; whether it leaves the machine is the user's decision. Content sent to coze is disclosed on first outbound; **whether IPD and other individual data goes to the cloud is the user's call**.

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
