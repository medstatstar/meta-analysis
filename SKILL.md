---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: 医学Meta分析 / Meta Analysis
version: 1.8.0
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。
license: MIT
description: "基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。所有分析提供可复现 R 代码。 / Comprehensive R-based meta-analysis skill covering RevMan 5.x + Stata equivalents (metareg/mvmeta) + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta. All analyses ship reproducible R code."

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
  network_note: "R package installation is a MANUAL user step — the skill NEVER downloads or installs packages at runtime. Network is touched ONLY if the user explicitly requests PDF full-text download from DOI/PMID lists (external services), which requires opt-in confirmation of the target list."
  filesystem: "writes only to the current working directory (meta_analysis/ and output/ report artifacts: generated .R scripts, .svg/.png figures, .csv tables); otherwise read-only"
  data: "no external data transmission. R package installation is never performed by this skill — if the user installs packages, that is a manual action in their own R environment."
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "version": "1.7",
    "license": "MIT",
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "dmetar", "netmeta", "multinma", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear"],
  }
---

# Meta-Analysis / 医学Meta分析

> R-based comprehensive meta-analysis. Every module ships reproducible R code.

## Language / 语言

- This skill is **English-default**; auto-switches to Chinese when OS locale is `zh-*`.
- Detailed language policy → `references/language_policy.md`.
- Chinese user guide → [README_zh-CN.md](https://github.com/medstatstar/meta-analysis/blob/main/README_zh-CN.md)
- English user guide → [README.md](https://github.com/medstatstar/meta-analysis/blob/main/README.md)

## Triage (ct-base §5.2)

On first user message, classify into one of three:

| Classification | Condition | Action |
|---|---|---|
| **Simple** | Single, specific intent (e.g., "pool OR from these 5 studies") | Reply directly, no menu |
| **Complex** | Multi-decision / multi-parameter (e.g., "network meta with 3 interventions, subgroup, check inconsistency") | Present level-1 routing menu incl. "③ Can't decide? → explain the differences between these choices" entry; full menu → references/interactive_menu.md |
| **Vague** | Unclear what user wants (e.g., "I need meta-analysis help") | Grill-me style branch questions, 1–3 per round |

If unsure between Simple and Complex → give short reply + optional expansion hint.

## Traceability / Grounding (ct-base §5.1)

All factual/assertive claims must cite source: specific `ref-*.md` section (e.g., `§3.6`) or official guideline. If a claim has no verifiable source → mark `⚠️ official verify` and ask user to confirm against official text.

## Initialization

0. **Integrity check**: R source code is embedded as Python templates (scripts/r_*.py + r_templates.py) to comply with marketplace restrictions on .R files. On first use, run:
   ```bash
   bash scripts/check_integrity.sh   # exit 0 = ready
   ```
   - If `scripts/*.R` exists → ready; if missing → script auto-runs `python r_templates.py` to generate from templates.
1. **R env**: `Rscript --version` → missing → https://cran.r-project.org/
2. **Install (manual)**: This skill **does NOT auto-install** R packages. Run `bash scripts/check_integrity.sh` or pre-analysis self-check to see missing packages; then **manually install** in R, or `Rscript scripts/setup_packages.R` to view full list.
   - Packages: `metafor meta dmetar netmeta ggplot2 esc clubSandwich robumeta bayesmeta multinma gemtc dosresmeta survmeta mada metagear gridExtra ggforestplot svglite`
   - ⚠️ Manual install connects to CRAN; use trusted network.
3. **Workspace**: Create `meta_analysis/` + `output/` in current directory (⚠️ will write files).
4. **Memory**: read `~/.workbuddy/MEMORY.md` for R config.

## Interactive Guide

**Triage path**: Vague → Level 1 menu (7 categories). Select → Level 2 with data-format hints. Sufficient info → skip menu, run analysis directly.

```
=== Level 1: Main ===
1️⃣ Pairwise Meta     4️⃣ Effect Size      7️⃣ Review Workflow
2️⃣ Heterogeneity & Bias  5️⃣ Visualization
3️⃣ Advanced Models   6️⃣ Study Quality
```

```
=== Level 2: Sub-Menus (excerpt) ===
[1] Pairwise: Binary(OR/RR/RD) | Continuous(SMD/MD) | Pre-calc(yi+CI) | Survival(HR/IRR) | Correlation(r→Zr)
[2] Heterogeneity: I²/Q/τ² | Subgroup | Meta-regression | Pub Bias(Egger/Begg/Trim-fill) | Sensitivity | GOSH | Baujat
[3] Advanced: Multi-arm NMA(netmeta) | Bayesian NMA Stan(multinma) | JAGS(gemtc) | Multilevel | Multivariate | IPD | Dose-Resp(dosresmeta) | Survival(survmeta) | TSA | Bootstrap
[4] Effect Size: Mean→d | t/F/r→d | d↔Hedges'g | d↔logOR | r↔Z | OR↔logOR | Batch
[5] Viz: Forest(5 themes) | Funnel | Bubble | GOSH | Network | League Table | RoB Traffic-light | Power Curve | Drapery
[6] Quality: RoB 1.0/2.0 | ROBINS-I | GRADE | PRISMA Checklist
[7] Workflow: PRISMA Flow | Screening GUI | PDF Batch-download (⚠️ opt-in) | Digitize | NNT Meta
```

Data formats & full details → `references/interactive_menu.md`

> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

## Core Functions

| Module | R Packages & Functions |
|--------|----------------------|
| Single-Group Meta | `metaprop()` `metamean()` `metainc()` `metacor()` `metarate()` |
| Pairwise Meta | `metabin()` `metacont()` `metagen()` `rma()` — FE/RE(DL/HK)/MH/Peto |
| Effect Size | `escalc()` `esc_mean_sd()` — SMD, OR, RR, RD, HR, ROM, ZCOR |
| Forest/Funnel | `forest()` `funnel()` + ggplot2 (5 themes) |
| Heterogeneity | I², Q, τ², H², 95% PI — auto-reported |
| Publication Bias | `regtest()` `ranktest()` `trimfill()` `selmodel()` |
| Subgroup & Reg | `rma(mods=~factor-1)` + `bubble()` |
| Sensitivity | Leave-one-out, Cumul, GOSH, quality filter |
| Bayesian Pairwise | `bayesmeta::bayesmeta()` — half-normal/JC prior |
| Bayesian NMA | `run_bayes_nma_multinma()`(Stan) · `run_bayes_nma_gemtc()`(JAGS) |
| Multilevel/MV Meta | `rma.mv()` + UN/CS/HCS/AR1/ID/DIAG |
| Survival Meta | `run_surv_meta()` — survmeta wrapper |
| TSA & Diagnostics | `run_tsa()` · `baujat()` `drapery()` `bootmeta()` |
| Dose-Response | `run_dose_resp()` — dosresmeta wrapper |
| Diagnosis Meta | `mada::reitsma()` bivariate + SROC |
| RVE Robust | `robumeta::robu()` `clubSandwich::vcovCR(CR2)` |
| Review Workflow | `metagear`: PRISMA, screen, PDF, digitize |
| Quality | `rob()` RoB 1.0/2.0/ROBINS-I + GRADE |
| Power | `run_power_curve()` + subgroup power |

## Reusable API (Mandatory)

> **Any analysis MUST call existing functions — never rewrite the full pipeline inline.** Full function list + calling examples → `references/advanced_api.md`.

## Security & Scope

**Execution model**: R analysis runs locally; skill **does NOT auto-install R packages** (missing → list + prompt manual install). PDF full-text download from external services ONLY on **explicit user instruction**. Analysis artifacts written to `meta_analysis/` + `output/` by default.

**Not clinical judgment**: Results require professional interpretation.

**No literature DB search**: Does not search literature databases; only downloads full text when user provides DOI/PMID.

## Output

`analysis_complete.R` + forest/funnel (`.svg`+`.png`) + `results_summary.md` + `data_backup.csv`.

Output figures as editable SVG; editing + journal format conversion → `references/svg_editing.md`.

## Units

See `references/units.md` for the full 5-field schema (input / output / dependency / AI autonomy / consumer units).

## References

| File | Content |
|------|---------|
| `interactive_menu.md` | How to use in a chat (user-friendly guide, 5 conversation examples) |
| `ADVANCED.md` | Advanced reference (CLI, formulas, troubleshooting, full file structure) |
| `ADVANCED_zh-CN.md` | Advanced reference (Chinese version) |
| `revman_complete.md` | RevMan→R 1:1 code mapping |
| `stata_to_r_mapping.md` | Stata metareg/mvmeta→R equivalents |
| `esc_robust_meta.md` | Effect size conversions + RVE reference |
| `advanced_analysis.md` | Multilevel/IPD/Bayesian/Dose-Resp/Power |
| `single_group_meta.md` | metaprop/metamean/metainc/metacor + NNT |
| `bayesian_nma.md` | multinma (Stan) + gemtc (JAGS) full workflow |
| `survival_meta.md` | survmeta + KM pseudo-IPD reconstruction |
| `tsa_diagnostics.md` | TSA + Baujat + Drapery + Bootmeta |
| `diagnosis_meta.md` | mada::reitsma bivariate + SROC |
| `review_workflow.md` | metagear: PRISMA, screening, PDF batch, digitize |
| `data_templates.md` | Data input templates per type |
| `citations.md` | Full citation list |
| `r_packages.md` | Package details & installation |
| `advanced_api.md` | Reusable API reference |
| `svg_editing.md` | SVG editing tools & journal format conversion |
| `units.md` | Atomic task unit index (pipeline) |
| `language_policy.md` | Bilingual policy detailed companion |
| `report_template.md` | Report skeleton reference |

## Project Files

`README.md` | `README_zh-CN.md` | `CHANGELOG.md` | `AGENTS.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`

## Changelog

Version / fix log → `CHANGELOG.md`.
