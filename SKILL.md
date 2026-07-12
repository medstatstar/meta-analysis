---
name: meta-analysis
cn_name: 医学Meta分析
description: "Comprehensive R-based meta-analysis skill. Covers all RevMan 5.x features + Stata metareg/mvmeta equivalents + esc effect size conversions + clubSandwich/robumeta cluster-robust variance estimation. Supports random/fixed-effect models, multilevel/multivariate meta, network meta, Bayesian meta, power analysis. All analysis ships reproducible R code. / 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata metareg/mvmeta 等价实现 + esc 效应量转换 + clubSandwich/robumeta 聚类稳健方差估计，支持随机/固定效应模型、多水平/多变量元分析、网络Meta、贝叶斯Meta、功效分析，所有分析提供可复现 R 代码。"
triggers:
  - "meta分析"
  - "meta-analysis"
  - "系统评价"
  - "systematic review"
  - "森林图"
  - "forest plot"
  - "漏斗图"
  - "funnel plot"
  - "异质性"
  - "I²"
  - "发表偏倚"
  - "元回归"
  - "meta-regression"
  - "网络meta"
  - "network meta"
  - "贝叶斯meta"
  - "bayesian meta"
  - "效应量转换"
  - "esc"
  - "SMD"
  - "Hedges g"
  - "robumeta"
  - "clubSandwich"
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "version": "1.0.0",
    "license": "MIT",
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "dmetar", "netmeta", "revman", "robumeta", "clubSandwich", "esc"],
  }
---

# Meta-Analysis Skill / Meta 分析技能

> R-based comprehensive meta-analysis. All RevMan 5.x features + Stata metareg/mvmeta equivalents + esc conversions + cluster-robust RVE. Every analysis ships reproducible R code.
> 基于 R 的全方位 Meta 分析。覆盖 RevMan 全部功能 + Stata 等价 + esc 转换 + 聚类稳健方差估计。所有分析提供可复现 R 代码。

## Purpose / 技能目的

Meta-analysis is a cornerstone of evidence-based medicine, and software tools such as R and RevMan already provide robust statistical engines. However, for most clinical professionals, these tools carry a significant learning curve — users must either master statistical programming or rely on dedicated statisticians to complete an analysis. This skill is designed to lower that barrier entirely. With natural-language dialogue, any clinical professional can independently conduct a complete meta-analysis, producing publication-ready results backed by professional-grade R code. Every step is powered by R's specialized meta-analysis packages. The complete, reproducible R code is provided alongside every result, enabling users to verify, re-run, and build confidence in the accuracy of their findings.

Meta分析是医学领域中至关重要的循证医学分析技术，现有软件（如 R、RevMan 等）均可实现完善的 Meta 分析。但对于临床医生而言，这些工具均存在一定的使用门槛——需要掌握相应编程方法，或依赖专业统计人员才能完成分析。本技能的目的是让临床医学工作者通过自然语言的提示词对话方式，顺畅自如地独立完成 Meta 分析，并输出完全符合出版要求的分析结果，从而大幅提升其科研能力。整个技能完全基于 R 统计环境中的专业软件包实现 Meta 分析，且 100% 提供相应的 R 运行代码，供用户检查和重跑，确保结果准确无误。

## Initialization / 初始化

1. **R env / 检查R**: `Rscript --version` → if missing, direct to https://cran.r-project.org/
2. **Install Strategy / 安装策略**: 
   ```
   1️⃣ Install all now / 一次性全部安装（推荐）  2️⃣ Install on demand / 按需安装
   ```
   - If **1**: install `metafor meta dmetar netmeta ggplot2 esc clubSandwich robumeta bayesmeta gridExtra ggforestplot` via `install.packages()`; `dmetar` from GitHub if needed
   - If **2**: skip, install when triggered
3. **Workspace / 工作目录**: create `meta_analysis/` + `output/`
4. **Memory / 记忆**: read `~/.workbuddy/MEMORY.md` for R config

## Interactive Guide / 交互式引导

> **Design**: Vague prompt → Level 1 menu. Category selected → Level 2 sub-menu with data format hints. Sufficient info → skip to analysis.
> **设计**: 模糊提示 → Level 1 主菜单 → 选择后 Level 2 子菜单（含数据格式指引）→ 信息充足后直接分析。

```
=== Level 1: Main Category / 主菜单 ===
1️⃣  Pairwise Meta-Analysis / 两组Meta分析
2️⃣  Heterogeneity & Bias / 异质性与偏倚
3️⃣  Advanced Models / 高级模型
4️⃣  Effect Size & Conversion / 效应量与转换
5️⃣  Visualization / 可视化
6️⃣  Study Quality / 研究质量
```

```
=== Level 2: Sub-Menus (excerpt) / 子菜单（示例）===
[1] Pairwise Meta:
  1. Binary (OR/RR/RD)     → study, n_exp, event_exp, n_ctrl, event_ctrl
  2. Continuous (SMD/MD)   → study, n_exp, mean_exp, sd_exp, n_ctrl, mean_ctrl, sd_ctrl
  3. Pre-calculated (yi+CI)→ study, effect_type, effect_size, lower95, upper95

[2] Heterogeneity & Bias:
  1. Heterogeneity (I²/Q/τ²)  2. Subgroup analysis  3. Meta-regression
  4. Publication bias         5. Sensitivity         6. GOSH plot

Full menu tree with data formats → `references/interactive_menu.md`

> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.
> **其他格式？** 安装 `@skill:statdata-transfer` 转换 50+ 格式。

## Core Functions / 核心功能

| Module | R Trigger / 触发词 |
|--------|-------------------|
| Effect Size / 效应量 | `escalc()`, `esc_mean_sd()` — SMD, OR, RR, RD, HR, ROM, ZCOR |
| Pooling / 合并 | `rma()`, `metabin()` — FE, RE(DL/HK), MH, Peto |
| Forest Plot / 森林图 | `forest()` + ggplot2 (5 themes: minimal/lancet/jama/revman/custom) |
| Heterogeneity / 异质性 | I², Q, τ², 95% PI — auto-reported |
| Publication Bias / 偏倚 | `funnel()`, `regtest()`, `ranktest()`, `trimfill()`, `selmodel()` |
| Subgroup / 亚组 | `rma(mods = ~ factor - 1)` + QB test |
| Meta-Regression / 元回归 | `rma(yi, vi, mods)` + bubble plot |
| Sensitivity / 敏感性 | Leave-one-out, GOSH, quality/sample-size filter |
| Network Meta / 网络meta | `netmeta::netmeta()` — node-splitting, SUCRA, league table |
| Bayesian / 贝叶斯 | `bayesmeta::bayesmeta()` — half-normal prior, MCMC diagnostics |
| Power / 功效 | `dmetar::power.analysis()` |
| Risk of Bias / 偏倚风险 | RoB 1.0/2.0 templates + traffic-light plot |

## RevMan 1:1 Coverage / RevMan 对应

Full mapping in `references/revman_complete.md`. 详细代码见 `references/revman_complete.md`。

| RevMan | R | ✅ |
|--------|---|----|
| Dichotomous / 二分类 | `metabin()`, `rma()` | ✅ |
| Continuous / 连续型 | `metacont()`, `rma()` | ✅ |
| Forest/Funnel / 森林/漏斗 | ggplot2 + `funnel()` | ✅ |
| Subgroup / 亚组 | `rma(mods = ~ factor - 1)` | ✅ |
| Heterogeneity / 异质性 | I²/Q/τ² auto | ✅ |
| Sensitivity / 敏感性 | Leave-one-out, GOSH | ✅ |
| Pub. Bias / 发表偏倚 | Egger/Begg/Trim-fill | ✅ |
| GRADE / RoB | Structured + templates | ✅ |
| Network / 网络 | `netmeta` wrapper | ✅ |
| Bayesian / 贝叶斯 | `bayesmeta` | ✅ |

## Stata Equivalents / Stata 等价

Details in `references/stata_to_r_mapping.md`. 详见 `references/stata_to_r_mapping.md`。

| Stata | R |
|-------|---|
| `metareg` | `rma(yi, vi, mods, method="REML")` + `permutest(fit, iter=1000)` |
| `mvmeta` UN/CS/HCS/AR1/ID/DIAG | `rma.mv(yi, V, random=~outcome\|study, struct="UN"/"CS"/"HCS"/"AR1"/"ID"/"DIAG")` |
| V matrix (multi-arm) | `build_V_matrix_CS()`: Cov(dᵢ,dⱼ) = 1/n₀ + dᵢ·dⱼ/(2·N) |

## Effect Size Conversion / 效应量转换

Details in `references/esc_robust_meta.md`. 详见 `references/esc_robust_meta.md`。

| Conversion | R |
|------------|---|
| Mean/SD/n → Cohen's d / Hedges' g | `esc::esc_mean_sd()` + J = 1 − 3/(4df − 1) |
| d ↔ logOR | logOR = d·π/√3 |
| r ↔ Fisher's z | z = 0.5·ln((1+r)/(1−r)) |
| OR/CI → logOR+SE | `esc::esc_or()` |
| Batch convert | `metafor::escalc()` |

## Cluster-Robust RVE / 聚类稳健方差估计

For dependent effect sizes (multi-outcome/multi-arm). Details in `references/esc_robust_meta.md`.
处理依赖效应量。详见 `references/esc_robust_meta.md`。

| Package | Use Case |
|---------|----------|
| `robumeta::robu()` | ≥10 studies, multiple outcomes (ρ=0.8, small=TRUE) |
| `clubSandwich::vcovCR(type="CR2")` | Small-sample correction |
| `metafor::vcalc()` + `impute.vcov()` | Manual V matrix |

Workflow: dependency check → V matrix → fit (≥10: robu; <10: CR2) → robust CI + I².
流程：依赖检测 → V矩阵 → 拟合（≥10: robu；<10: CR2）→ 稳健CI + I²。

## Advanced / 高级方法

Multilevel / IPD / Bayesian / Dose-Response / GOSH / Power → `references/advanced_analysis.md`
多水平/IPD/贝叶斯/剂量反应/GOSH/功效 → `references/advanced_analysis.md`

## Security & Scope / 安全与范围

- **Local only / 仅本地**: all R runs locally, no data transmitted
- **Auto-install / 自动安装**: user-level library, no system changes
- **Not a substitute for clinical judgment / 不替代临床判断**
- **No database searching / 不执行数据库检索**

## Output / 输出

`analysis_complete.R` + forest/funnel plots (`.svg`+`.png`) + `results_summary.md` + `data_backup.csv`. All SVG — editable in Illustrator/Inkscape.
所有图形为矢量 SVG，可在 Illustrator/Inkscape 中编辑。

## Citations / 引用

R, metafor, meta, dmetar, netmeta, esc, robumeta, clubSandwich — full list in `references/citations.md`.

## References / 参考

| File | Content |
|------|---------|
| `r_packages.md` | Package details & install / 包详解与安装 |
| `revman_complete.md` | RevMan→R 1:1 code / RevMan→R 1:1 代码 |
| `stata_to_r_mapping.md` | Stata→R mapping / Stata→R 映射 |
| `esc_robust_meta.md` | esc + RVE reference / esc + 稳健方差估计 |
| `advanced_analysis.md` | Multilevel/IPD/Bayesian / 多水平/IPD/贝叶斯 |
| `data_templates.md` | Data input templates per type / 各类型数据输入模板 |
| `citations.md` | Full citations / 完整引用 |

## Project Files / 项目文件

`README.md` | `README_ZH.md` | `LICENSE` (MIT © 2025 Wintone) | `requirements.txt` | `assets/icon.svg`
