# meta-analysis

[🇨🇳 中文 (Chinese)](./README_ZH.md)

## Overview

`meta-analysis` is an R-based comprehensive Meta-Analysis skill for OpenClaw/WorkBuddy. It covers 100% of RevMan functionality, Stata `metareg`/`mvmeta` equivalents, effect size conversions (`esc` package), and cluster-robust variance estimation (`clubSandwich`/`robumeta`).

## Key Features

| Feature | R Packages | Coverage |
|---------|-----------|----------|
| Fixed / Random / Mixed-Effects Models | `metafor`, `meta` | Complete |
| Dichotomous / Continuous Outcomes | `metafor`, `meta` | Complete |
| Forest Plot, Funnel Plot, GOSH | `metafor`, `ggplot2` | Publication-ready |
| Heterogeneity: I², Q, tau², PI | `metafor` | Complete |
| Publication Bias: Egger, Begg, Trim-fill | `metafor`, `meta` | Complete |
| Subgroup Analysis & Meta-Regression | `metafor` | Complete |
| Network Meta-Analysis | `netmeta`, `gemtc` | Complete |
| Bayesian Meta-Analysis | `bayesmeta` | Complete |
| Leave-one-out, Cumulative, Sensitivity | `metafor`, `dmetar` | Complete |
| Power Analysis | `dmetar | Complete |
| Risk-of-Bias (RoB 1.0/2.0) | `robvis`, `dmetar` | Complete |
| Effect Size Conversions (d ↔ logOR ↔ r) | `esc` | Complete |
| Cluster-Robust Variance Estimation | `robumeta`, `clubSandwich` | Complete |
| Multivariate/Multilevel Meta | `metafor`, `robumeta` | Complete |

## RevMan Compatibility

The skill implements 1:1 code mappings for all RevMan 5.x analysis types. Users familiar with RevMan can transition to fully reproducible R workflows.

## Installation

1. Install R 4.0+ (https://cran.r-project.org/)
2. Copy the skill folder to `~/.workbuddy/skills/meta-analysis/`
3. The skill auto-installs required R packages on first run

## Usage

```
# In WorkBuddy chat:
"帮我做meta分析，这是我的数据..."
"用随机效应模型合并OR"
"画森林图，按地区做亚组分析"
"网状meta分析，有3种干预"
"做元回归，自变量为发表年份"
```

## Output

- `analysis_complete.R` — Fully reproducible R script
- Forest plot (SVG + PNG)
- Funnel plot (SVG + PNG)
- `results_summary.md` — Structured results
- CSV data backup
- R Markdown / HTML report (optional)

## References

- Harrer, M., Cuijpers, P., Furukawa, T. A., & Ebert, D. D. (2019). *Doing Meta-Analysis with R: A Hands-On Guide*. Chapman and Hall/CRC.
- Viechtbauer, W. (2010). Conducting meta-analyses in R with the metafor package. *J Stat Softw*, 36(3), 1-48.
- Balduzzi, S., Rücker, G., & Schwarzer, G. (2019). How to perform a meta-analysis with R: a practical tutorial. *Evid Based Ment Health*, 22(4), 153-160.
- Rücker, G., et al. (2016). netmeta: Network Meta-Analysis using Frequentist Methods. *BMC Med Res Methodol*, 16, 1-8.

## License

MIT License. See `LICENSE` file for details.
