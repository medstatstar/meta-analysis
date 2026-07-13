---
name: meta-analysis
cn_name: 医学Meta分析
description: "Comprehensive R-based meta-analysis skill. Covers RevMan 5.x + Stata metareg/mvmeta + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnosis meta + review workflow. All analysis ships reproducible R code. / 基于R的全方位Meta分析技能。覆盖RevMan全部功能+Stata等价+esc+RVE+贝叶斯NMA(Stan/JAGS)+生存Meta+TSA+单组率Meta+诊断Meta+系统评价流程，所有分析提供可复现R代码。"
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
  - "单组率meta"
  - "survmeta"
  - "TSA"
  - "诊断meta"
  - "PRISMA"
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "version": "1.5.0",
    "license": "MIT",
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "dmetar", "netmeta", "multinma", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear"],
  }
---

# Meta-Analysis Skill / Meta 分析技能

> R-based comprehensive meta-analysis. Every module ships reproducible R code. | 基于R的全方位Meta分析，所有分析提供可复现R代码。

## Purpose / 技能目的

Meta-analysis is a cornerstone of evidence-based medicine. However, existing tools carry a learning curve — users must master statistical programming or rely on statisticians. This skill lowers that barrier entirely: any clinical professional can independently conduct meta-analysis via natural-language dialogue, producing publication-ready results backed by professional R code. Every step is powered by R's specialized packages with complete reproducibility.

Meta分析是循证医学的核心技术，但现有工具使用门槛较高。本技能让临床医学工作者通过自然语言对话独立完成Meta分析，输出符合出版要求的结果，全部基于R专业软件包，100%提供可复现R代码，供用户检查和重跑。

## Initialization / 初始化

1. **R env / 检查R**: `Rscript --version` → missing → https://cran.r-project.org/
2. **Install / 安装策略**: `1️⃣ all now / 全部安装（推荐）` or `2️⃣ on demand / 按需安装`
   - Packages: `metafor meta dmetar netmeta ggplot2 esc clubSandwich robumeta bayesmeta multinma gemtc dosresmeta survmeta mada metagear gridExtra ggforestplot`
3. **Workspace**: create `meta_analysis/` + `output/`
4. **Memory**: read `~/.workbuddy/MEMORY.md` for R config

## Interactive Guide / 交互式引导

**Design**: Vague prompt → Level 1 menu (7 categories). Select → Level 2 with data format hints. Sufficient info → run analysis directly.
**设计**: 模糊提示 → Level 1主菜单(7类) → 选择后Level 2子菜单(含数据格式) → 信息充足后直接分析。

```
=== Level 1: Main / 主菜单 ===
1️⃣ Pairwise Meta / 两组Meta     4️⃣ Effect Size / 效应量转换    7️⃣ Review Workflow / 系统评价流程
2️⃣ Heterogeneity & Bias / 异质性偏倚  5️⃣ Visualization / 可视化
3️⃣ Advanced Models / 高级模型     6️⃣ Study Quality / 研究质量
```

```
=== Level 2: Sub-Menus (excerpt) / 子菜单（示例）===
[1] Pairwise: Binary(OR/RR/RD) | Continuous(SMD/MD) | Pre-calc(yi+CI) | Survival(HR/IRR) | Correlation(r→Zr)
[2] Heterogeneity: I²/Q/τ² | Subgroup | Meta-regression | Pub Bias(Egger/Begg/Trim-fill) | Sensitivity | GOSH | Baujat
[3] Advanced: Multi-arm NMA(netmeta) | Bayesian NMA Stan(multinma) | JAGS(gemtc) | Multilevel | Multivariate(UN/CS/AR1...) | IPD | Dose-Resp(one.stage) | Survival(survmeta) | TSA(tes) | Bootstrap(bootmeta)
[4] Effect Size: Mean→d | t/F/r→d | d↔Hedges'g | d↔logOR | r↔Z | OR↔logOR | Batch(escalc)
[5] Viz: Forest(5 themes) | Funnel | Bubble | GOSH | Network | League Table | RoB Traffic-light | Power Curve | Drapery
[6] Quality: RoB 1.0/2.0 | ROBINS-I | GRADE | PRISMA Checklist
[7] Workflow: PRISMA Flow | Screening GUI | PDF Batch-download | Digitize | NNT Meta

Data formats & full details → `references/interactive_menu.md`

> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion. | 其他格式？安装 `@skill:statdata-transfer`。

## Core Functions / 核心功能

| Module | R Packages & Functions |
|--------|----------------------|
| Single-Group Meta / 单组率均值 | `metaprop()` `metamean()` `metainc()` `metacor()` `metarate()` |
| Pairwise Meta / 两组Meta | `metabin()` `metacont()` `metagen()` `rma()` — FE/RE(DL/HK)/MH/Peto |
| Effect Size / 效应量 | `escalc()` `esc_mean_sd()` — SMD, OR, RR, RD, HR, ROM, ZCOR |
| Forest/Funnel / 森林漏斗 | `forest()` `funnel()` + ggplot2 (5 themes) |
| Heterogeneity / 异质性 | I², Q, τ², H², 95% PI — auto-reported |
| Publication Bias / 偏倚 | `regtest()` `ranktest()` `trimfill()` `selmodel()` |
| Subgroup & Reg / 亚组回归 | `rma(mods=~factor-1)` + `bubble()` |
| Sensitivity / 敏感性 | Leave-one-out, Cumul, GOSH, quality filter |
| Bayesian Pairwise / 贝叶斯两组 | `bayesmeta::bayesmeta()` — half-normal/JC prior |
| Bayesian NMA / 贝叶斯NMA | `multinma::nlme_nma()`(Stan) | `gemtc` (JAGS) |
| Multilevel/MV Meta / 多水平多元 | `rma.mv()` + UN/CS/HCS/AR1/ID/DIAG |
| Survival Meta / 生存Meta | `survmeta()` + KM reconstruction |
| TSA & Diagnostics | `tes()` `baujat()` `drapery()` `bootmeta()` |
| Dose-Response / 剂量反应 | `dosresmeta()` + `one.stage()` (IPD+agg) |
| Diagnosis Meta / 诊断准确性 | `mada::phm()` |
| RVE Robust / 聚类稳健 | `robumeta::robu()` `clubSandwich::vcovCR(CR2)` |
| Review Workflow / 评价流程 | `metagear`: PRISMA, screen, PDF, digitize |
| Quality / 质量 | `rob()` RoB 1.0/2.0/ROBINS-I + GRADE |
| Power / 功效 | `dmetar::power.analysis()` + subgroup power |

Full RevMan mapping → `references/revman_complete.md`
Stata equivalents → `references/stata_to_r_mapping.md`
Effect size conversions → `references/esc_robust_meta.md`
Cluster-robust workflows → `references/esc_robust_meta.md`

## Reusable API / 复用接口（强制）

> **规则：任何分析必须调用已有函数，禁止从零编写完整分析脚本。**
> When running any analysis, ALWAYS `source()` the skill scripts and call the functions below — never rewrite the full pipeline inline.

```r
# 统一入口：效应量计算 + 模型拟合，返回 ma_result 对象
source("scripts/meta_analysis_core.R")
res <- ma_analyze(data, type = "rate",            # binary|continuous|rate|precomp|survival
                  measure = "IRR",                # 自动选 OR/SMD/IRR 等
                  method = "REML", test = "knha")

# 一行出图 + 摘要（森林图/漏斗图 SVG+PNG + results.md）
ma_save(res, outdir = "output", prefix = "meta")
```

Functions: `ma_analyze()`(分发) · `calculate_effect_size()` · `run_meta_analysis()` · `analyze_heterogeneity()` · `analyze_publication_bias()` · `run_subgroup_analysis()` · `run_meta_regression()` · `run_sensitivity_analysis()` · `create_forest_plot()` · `create_funnel_plot()` · `generate_results_summary()` · `ma_save()`.
Column names are case-insensitive; override mapping via `cols = list(a="A", b="B", c="C", d="D")`.

## Security & Scope / 安全与范围

**Local only / 仅本地**: all R runs on user machine. No data transmitted.
**Not clinical judgment / 不替代临床判断**: results require context.
**No DB search / 不执行检索**: literature search not included.

## Output / 输出

`analysis_complete.R` + forest/funnel (`.svg`+`.png`) + `results_summary.md` + `data_backup.csv`.

### SVG 编辑工具

| 工具 | 适用场景 | 获取方式 |
|------|----------|----------|
| **PowerPoint / Word 2016+** | 直接拖入编辑（右键→取消组合，可修改文字/颜色/形状） | 已有 Office 即可 |
| **Inkscape** | 开源矢量编辑，调整布局、导出 PDF/EPS/高DPI TIFF | [inkscape.org](https://inkscape.org/)（免费） |
| **Adobe Illustrator** | 出版级精细调整（字体、配色、图层） | Adobe 订阅 |
| **Affinity Designer** | 一次性购买，功能接近 AI | Microsoft Store |

**投稿格式转换**（Inkscape 命令行）：
```bash
# SVG → EPS（多数医学期刊要求）
inkscape input.svg --export-type=eps --export-filename=input.eps

# SVG → PDF（JAMA/The Lancet 等）
inkscape input.svg --export-type=pdf --export-filename=input.pdf

# SVG → TIFF 600dpi（NEJM/British Medical Journal 等）
inkscape input.svg --export-type=png --export-dpi=600 --export-filename=input.tiff
```

## References / 参考

| File | Content |
|------|---------|
| `interactive_menu.md` | Full Level 2 menus + data formats + dialogue examples |
| `revman_complete.md` | RevMan→R 1:1 code mapping |
| `stata_to_r_mapping.md` | Stata metareg/mvmeta→R equivalents |
| `esc_robust_meta.md` | Effect size conversions + RVE reference |
| `advanced_analysis.md` | Multilevel/IPD/Bayesian/Dose-Resp/Power |
| `single_group_meta.md` | metaprop/metamean/metainc/metacor + NNT |
| `bayesian_nma.md` | multinma (Stan) + gemtc (JAGS) full workflow |
| `survival_meta.md` | survmeta + KM pseudo-IPD reconstruction |
| `tsa_diagnostics.md` | TSA(tes) + Baujat + Drapery + Bootmeta |
| `diagnosis_meta.md` | mada::phm diagnostic SROC |
| `review_workflow.md` | metagear: PRISMA, screening, PDF batch, digitize |
| `data_templates.md` | Data input templates per type |
| `citations.md` | Full citation list |
| `r_packages.md` | Package details & installation |

## Project Files / 项目文件

`README.md` | `README_ZH.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`
