# meta-analysis

[🇨🇳 中文 (Chinese)](./README_ZH.md)

> An R-based, conversation-driven Meta-Analysis skill for WorkBuddy. Covers 100% of RevMan 5.x functionality, Stata `metareg`/`mvmeta` equivalents, effect-size conversions (`esc`), and cluster-robust variance estimation (`clubSandwich`/`robumeta`) — all with publication-ready, editable SVG graphics.

## Overview

`meta-analysis` turns natural-language requests into fully reproducible R workflows. Tell it what you want ("pool the OR", "draw a forest plot subgrouped by region", "network meta-analysis with 3 interventions") and it will: check the R environment, guide you through data input, run the right model, and emit editable vector figures plus a structured results summary.

Everything runs **locally** — no user data is uploaded to any server.

## Key Features

| Capability | Implementation (R packages) | Coverage |
|------------|------------------------------|----------|
| **Effect-size computation** | `metafor`, `meta` | 8 types auto-detected: OR/RR/RD (dichotomous), SMD/MD (continuous), HR (survival), r→Fisher's z (correlation), single-group rate/mean |
| **Fixed / Random / Mixed models** | `rma()`, `metabin()`, `metacont()` | DL, REML, ML, PM, Hartung–Knapp, FE |
| **Forest / Funnel / GOSH plots** | `metafor`, `ggplot2` | Publication-ready SVG (minimal/lancet/jama/revman/custom themes) |
| **Heterogeneity** | `metafor` | I², Cochran's Q, τ², H², Prediction Interval |
| **Publication bias** | `metafor`, `meta` | Egger regression, Begg rank, Trim-and-fill, selection models, fail-safe N |
| **Subgroup analysis** | `metafor`, `meta` | `mods = ~ factor(group) - 1`, between-group Q |
| **Meta-regression** | `metafor` | Uni/multivariate, continuous/categorical/interaction + bubble plot |
| **Network Meta-Analysis** | `netmeta`, `gemtc`, `multinma` | Consistency (node-split), SUCRA, league table, Bayesian (JAGS/Stan) |
| **Bayesian Meta-Analysis** | `bayesmeta`, `multinma`, `gemtc` | MCMC posterior, prior diagnostics |
| **Sensitivity analysis** | `metafor`, `dmetar` | Leave-one-out, cumulative, GOSH (all-subsets) |
| **Survival Meta** | `survmeta`, `ipdmeta` | Aggregate HR + KM pseudo-IPD reconstruction |
| **Single-group / Diagnostic** | `meta` (`metaprop`/`metamean`/`metainc`/`metacor`), `mada` | Proportion, mean, incidence, correlation, bivariate SROC |
| **Trial Sequential Analysis** | `metafor::tes()` | Type-I-error control, required-info size |
| **Power analysis** | `dmetar`, `meta` | Prospective sample-size planning |
| **Risk-of-Bias (RoB 1.0/2.0, ROBINS-I)** | `robvis`, `dmetar` | Traffic-light + weighted bar plots |
| **Effect-size conversion** | `esc` | d ↔ g ↔ logOR ↔ r ↔ Fisher's z, batch + Hedges' g correction |
| **Cluster-robust variance estimation** | `robumeta`, `clubSandwich` | RVE + CR2 small-sample SE (dependent/multi-arm data) |
| **Multivariate / Multilevel** | `rma.mv()`, `robumeta` | UN/CS/AR1 + compound-symmetry V-matrix |
| **Stata equivalents** | `metafor`, `robumeta` | `metareg` → `rma`+permutation; `mvmeta` → `rma.mv`+6 covariance structs |
| **Systematic-review workflow** | `metagear` | PRISMA flow, screening GUI, PDF batch, digitize, impute |

## RevMan Compatibility

The skill implements 1:1 code mappings for all RevMan 5.x analysis types (binary, continuous, generic inverse-variance, single-arm, OD ratios, etc.). Users familiar with RevMan can migrate to fully reproducible, editable R output without re-learning statistics.

## Stata Equivalents

| Stata command | R equivalent | Notes |
|---------------|--------------|-------|
| `metan` | `metabin()` / `metacont()` | Same models, richer output |
| `metareg` | `rma(..., mods = ~ x)` + permutation test | Adds Knapp–Hartung SEs |
| `mvmeta` | `rma.mv()` with `V` matrix | 6 covariance structures (UN/CS/AR1/…) |
| `metabias` | `regtest()` / `ranktest()` | Egger / Begg |
| `metaninf` | `leave1out()` | Influence diagnostics |

## Interactive Workflow

On first activation the skill presents a 7-category menu; if your initial message already contains enough detail it skips straight to analysis:

1. **Pairwise Meta** — binary / continuous / pre-computed / survival / correlation / single-group
2. **Heterogeneity & Bias** — I²/Q/τ², subgroup, meta-regression, Egger/Begg/Trim-fill, sensitivity, GOSH, Baujat, Drapery
3. **Advanced Models** — NMA, Bayesian NMA (Stan/JAGS), multilevel, multivariate, IPD, dose-response, survival, TSA, bootstrap
4. **Effect Size & Conversion** — mean/SD→d, t/F/r→d, d↔g, d↔logOR, r↔Fisher's z, OR↔logOR, batch, NNT
5. **Visualization** — forest (5 themes), funnel, bubble, GOSH, network, league table, RoB traffic-light, power curve, Drapery, inconsistency heatmap
6. **Study Quality** — RoB 1.0/2.0, ROBINS-I, GRADE, PRISMA checklist, AMSTAR-2
7. **Systematic Review Workflow** — PRISMA flow, screening GUI, PDF batch, digitize, impute, reference management

## Installation

1. Install **R 4.0+** (https://cran.r-project.org/).
2. Place the skill folder at `~/.workbuddy/skills/meta-analysis/`.
3. On first run the skill auto-detects and installs missing R packages (you choose *install all now* or *on demand*).

If your raw data is in a non-standard format (SPSS/Stata/SAS/Excel/Parquet/…), the skill recommends installing **`statdata-transfer`** to convert it into the required CSV columns before analysis.

## Usage

```
# In WorkBuddy chat:
"run a meta-analysis with the following data..."
"pool the OR using a random-effects model"
"draw a forest plot, subgroup by region"
"network meta-analysis with 3 interventions (A vs B, A vs placebo)"
"meta-regression: effect size ~ publication year + sample size"
"check publication bias: Egger test + trim-and-fill"
"node-split test for NMA inconsistency"
"convert Cohen's d to logOR"
```

## Output

- `analysis_complete.R` — fully reproducible R script
- Forest plot (`.svg` + `.png`)
- Funnel plot, standard & contour-enhanced (`.svg` + `.png`)
- `results_summary.md` — structured results (effect, CI, I², τ², p-values)
- CSV data backup
- R Markdown / HTML report (optional)

## Editing the SVG Graphics

The figures are emitted as editable SVG. Recommended tools:

| Tool | Type | Notes |
|------|------|-------|
| **Microsoft PowerPoint** (2016+) | Office | Drag the `.svg` in, right-click → *Convert to Shape* / *Ungroup* to edit text/colors directly |
| **Inkscape** | Free / Open-source | Full vector editing; CLI export: `inkscape in.svg --export-type=pdf --export-filename=out.pdf` |
| **Adobe Illustrator** | Paid | Journal-grade fine-tuning; native SVG/EPS |
| **Affinity Designer** | Paid (one-time) | Lightweight AI alternative |
| **Boxy SVG** | Free/Paid web app | Quick color/text/dimension tweaks |

For journal submission (TIFF/EPS/PDF), convert with Inkscape:

```bash
inkscape forest_plot.svg --export-type=eps --export-filename=forest_plot.eps
inkscape forest_plot.svg --export-type=pdf --export-filename=forest_plot.pdf
inkscape forest_plot.svg --export-type=png --export-dpi=600 --export-filename=forest_plot.tiff
```

## Directory Structure

```
meta-analysis/
├── SKILL.md                       # Main skill definition (bilingual, EN-first)
├── README.md / README_ZH.md      # This file
├── LICENSE                        # MIT
├── requirements.txt              # R package list
├── assets/
│   └── icon.svg                   # Skill logo
├── scripts/
│   ├── setup_packages.R          # Env check + package installer
│   ├── meta_analysis_core.R      # Core engine (escalc/rma/forest/funnel)
│   ├── effect_size_conversions.R # esc wrappers, d↔g, RVE
│   ├── stata_equivalents.R       # metareg / mvmeta equivalents
│   └── network_meta_analysis.R   # netmeta / gemtc / multinma
└── references/
    ├── interactive_menu.md        # Full menu tree + data-format guide
    ├── data_templates.md          # Per-type CSV templates + validation
    ├── revman_complete.md         # 1:1 RevMan → R code mappings
    ├── stata_to_r_mapping.md      # Stata metareg/mvmeta → R equivalents
    ├── advanced_analysis.md       # Multivariate / multilevel / IPD / dose-response
    ├── single_group_meta.md       # metaprop/metamean/metainc/metacor
    ├── survival_meta.md           # survmeta / KM pseudo-IPD
    ├── tsa_diagnostics.md         # tes / Baujat / Drapery / selection
    ├── diagnosis_meta.md          # mada bivariate / SROC
    ├── bayesian_nma.md            # multinma / gemtc workflows
    ├── esc_robust_meta.md         # esc conversions + RVE (robumeta/clubSandwich)
    ├── review_workflow.md         # metagear PRISMA / screening / digitize
    ├── r_packages.md              # Package inventory
    ├── citations.md               # Methodological references
    └── purpose_zh.md              # Chinese Purpose text mirror
```

## Important Notes

- R **4.0+** is required; the skill verifies this on startup.
- All analysis runs in your local R environment — **no user data is uploaded**.
- Statistical output requires interpretation in context; the skill does not replace statistical or clinical judgment.

## References

- Harrer, M., Cuijpers, P., Furukawa, T. A., & Ebert, D. D. (2021). *Doing Meta-Analysis with R: A Hands-On Guide*. Chapman and Hall/CRC.
- Viechtbauer, W. (2010). Conducting meta-analyses in R with the metafor package. *J Stat Softw*, 36(3), 1–48.
- Balduzzi, S., Rücker, G., & Schwarzer, G. (2019). How to perform a meta-analysis with R: a practical tutorial. *Evid Based Ment Health*, 22(4), 153–160.
- Rücker, G., et al. (2016). netmeta: Network Meta-Analysis using Frequentist Methods. *BMC Med Res Methodol*, 16, 1–8.
- Salanti, G. (2012). Network meta-analysis in mental health. *Evid Based Ment Health*, 15(1), 16–20.

## License

MIT License. See `LICENSE` file for details.
