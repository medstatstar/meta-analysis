---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: 医学Meta分析 / Meta Analysis
version: 1.7
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。
license: MIT
description: "基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。所有分析提供可复现 R 代码。 / Comprehensive R-based meta-analysis skill covering RevMan 5.x + Stata equivalents (metareg/mvmeta) + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta. All analyses ship reproducible R code."

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

> R-based comprehensive meta-analysis. Every module ships reproducible R code. / 基于R的全方位Meta分析，所有分析提供可复现R代码。

## Purpose / 技能目的

Meta-analysis is a cornerstone of evidence-based medicine. However, existing tools carry a learning curve — users must master statistical programming or rely on statisticians. This skill lowers that barrier entirely: any clinical professional can independently conduct meta-analysis via natural-language dialogue, producing publication-ready results backed by professional R code. Every step is powered by R's specialized packages with complete reproducibility. / Meta分析是循证医学的核心技术，但现有工具使用门槛较高。本技能让临床医学工作者通过自然语言对话独立完成Meta分析，输出符合出版要求的结果，全部基于R专业软件包，100%提供可复现R代码，供用户检查和重跑。

## Language Policy / 语言策略

 - Default to English; switch to Chinese when a Chinese-language environment is detected.
 - Common modules (frontmatter `description`/`displayName`, Core Functions table, triggers, etc.) ship full English + Chinese bilingual content.
 - Document sections that are language-agnostic use bilingual headings in **English / Chinese** order (e.g., `## Core Functions / 核心功能`).
 - Complex / less commonly used modules (e.g., advanced Bayesian NMA, survmeta, dosresmeta) may temporarily be English-only.
 - 默认英文；检测到中文环境时切换为中文提示。
 - 常用模块（frontmatter `description`/`displayName`、Core Functions 表、触发词等）备英文 + 中文两套。
 - 文档标题（不区分语言者）采用「英 / 中」顺序双语（如 `## Core Functions / 核心功能`）。
 - 复杂 / 少用模块（如高级贝叶斯 NMA、survmeta、dosresmeta）可暂只英文。

## Initialization / 初始化

0. **Integrity check / 完整性自检（必做，最先执行）**: 本技能将 R 源码以 Python 模板内嵌（scripts/r_*.py + r_templates.py）以规避部分技能市场（如 SkillHub）不允许发布 .R 文件的限制；安装后 `scripts/` 下**可能暂缺 .R**。请先运行自检：
   ```bash
   bash scripts/check_integrity.sh   # 退出码 0=可用(已生成或原本齐全)
   ```
   - 若 `scripts/*.R` 齐全 → 直接通过；
   - 若缺失 → 脚本会**自动执行 `python r_templates.py` 从内嵌模板生成全部 .R**，无需用户手动下载。
   
   Do not rewrite R code by yourself; let it auto-generate when missing. / 不要自行重写 R 代码；缺失时让它自动生成即可。

1. **R env / 检查 R**: `Rscript --version` → missing → https://cran.r-project.org/
2. **Install / Install (manual)**: This skill **does NOT auto-install** R packages. Run `bash scripts/check_integrity.sh` (or pre-analysis self-check) to see missing packages; then **manually install** them in R (e.g. core packages `metafor`, `meta`, `netmeta`), or run `Rscript scripts/setup_packages.R` to view the full list.
   - Packages needed: `metafor meta dmetar netmeta ggplot2 esc clubSandwich robumeta bayesmeta multinma gemtc dosresmeta survmeta mada metagear gridExtra ggforestplot svglite`
   - ⚠️ Manual installation will connect to CRAN / GitHub and write to your R library (may execute package install hooks); please use a trusted network.
3. **Workspace**: Create `meta_analysis/` + `output/` in the current working directory (⚠️ will write files — ensure the directory is correct and you have write permission).
4. **Memory**: read `~/.workbuddy/MEMORY.md` for R config

## Interactive Guide / 交互式引导

**Design / 设计**: Vague prompt → Level 1 menu (7 categories). Select → Level 2 with data format hints. Sufficient info → run analysis directly. / 模糊提示 → Level 1主菜单(7类) → 选择后Level 2子菜单(含数据格式) → 信息充足后直接分析。

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
[3] Advanced: Multi-arm NMA(netmeta) | Bayesian NMA Stan(multinma) | JAGS(gemtc) | Multilevel | Multivariate(UN/CS/AR1...) | IPD | Dose-Resp(dosresmeta) | Survival(survmeta) | TSA(run_tsa 自实现) | Bootstrap(bootmeta)
[4] Effect Size: Mean→d | t/F/r→d | d↔Hedges'g | d↔logOR | r↔Z | OR↔logOR | Batch(escalc)
[5] Viz: Forest(5 themes) | Funnel | Bubble | GOSH | Network | League Table | RoB Traffic-light | Power Curve | Drapery
[6] Quality: RoB 1.0/2.0 | ROBINS-I | GRADE | PRISMA Checklist
[7] Workflow: PRISMA Flow | Screening GUI | PDF Batch-download (⚠️ 需联网从外部服务获取全文，请确认版权/授权) | Digitize | NNT Meta
```

Data formats & full details → `references/interactive_menu.md`

> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion. / 其他格式？安装 `@skill:statdata-transfer`。

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
| Bayesian NMA / 贝叶斯NMA | `run_bayes_nma_multinma()`(Stan) · `run_bayes_nma_gemtc()`(JAGS) — 封装 multinma/gemtc |
| Multilevel/MV Meta / 多水平多元 | `rma.mv()` + UN/CS/HCS/AR1/ID/DIAG |
| Survival Meta / 生存Meta | `run_surv_meta()` — 封装 survmeta（HR/logHR 合并） |
| TSA & Diagnostics | `run_tsa()`(自实现,O'Brien-Fleming 边界) · `baujat()` `drapery()` `bootmeta()` |
| Dose-Response / 剂量反应 | `run_dose_resp()` — 封装 dosresmeta（连续 smd / 二分类 gl） |
| Diagnosis Meta / 诊断准确性 | `mada::reitsma()` bivariate + SROC |
| RVE Robust / 聚类稳健 | `robumeta::robu()` `clubSandwich::vcovCR(CR2)` |
| Review Workflow / 评价流程 | `metagear`: PRISMA, screen, PDF, digitize |
| Quality / 质量 | `rob()` RoB 1.0/2.0/ROBINS-I + GRADE |
| Power / 功效 | `run_power_curve()`(自实现,无依赖) + subgroup power |

## Reusable API / 复用接口（强制）

> **任何分析必须调用已有函数，禁止从零编写完整分析脚本。** 完整函数清单、调用示例与重依赖封装（TSA / 剂量反应 / 生存 Meta / 贝叶斯 NMA）见 `references/advanced_api.md`。
> Rule: never rewrite the full pipeline inline — `source()` the skill scripts and call the functions. Full API reference → `references/advanced_api.md`.

## Security & Scope / 安全与范围

**Execution model / 运行模型**: R analysis runs on your local machine; this skill **does NOT auto-install R packages** (when missing, it only lists package names and prompts manual installation — you decide whether to connect to the network and install). It downloads full-text PDFs from external services ONLY on your **explicit instruction** (network involved — please confirm copyright/authorization yourself). Analysis artifacts are written to the `meta_analysis/` and `output/` directories in your current workspace by default.
**Not clinical judgment / 不替代临床判断**: Results must be interpreted in conjunction with professional background.
**No literature DB search / 不检索文献库**: This skill does not include literature database search; it only downloads full text on demand when you provide a DOI/PMID.

## Output / 输出

`analysis_complete.R` + forest/funnel (`.svg`+`.png`) + `results_summary.md` + `data_backup.csv`.

Output figures as editable SVG; editing methods and journal format conversion (EPS/PDF/TIFF) → `references/svg_editing.md`. / 图形以可编辑 SVG 输出；编辑方式与期刊格式转换（EPS/PDF/TIFF）见 `references/svg_editing.md`。

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
| `tsa_diagnostics.md` | TSA(run_tsa 自实现) + Baujat + Drapery + Bootmeta |
| `diagnosis_meta.md` | mada::reitsma bivariate + SROC |
| `review_workflow.md` | metagear: PRISMA, screening, PDF batch, digitize |
| `data_templates.md` | Data input templates per type |
| `citations.md` | Full citation list |
| `r_packages.md` | Package details & installation |
| `advanced_api.md` | 复用接口（强制）+ 重依赖封装：TSA / 剂量反应 / 生存 / Bayesian NMA |
| `svg_editing.md` | SVG editing tools & journal format conversion |

## Project Files / 项目文件

`README.md` | `README_ZH.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`
