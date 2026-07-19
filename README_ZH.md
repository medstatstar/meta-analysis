# meta-analysis 技能

[🇬🇧 English (英文)](./README.md)

> 基于 R 语言的对话式 Meta 分析 WorkBuddy 技能。覆盖 RevMan 5.x 全部功能、Stata `metareg`/`mvmeta` 等价实现、效应量转换（`esc`）、聚类稳健方差估计（`clubSandwich`/`robumeta`），并提供可直接编辑的出版级 SVG 矢量图。

## 概述

`meta-analysis` 把自然语言请求转化为完全可复现的 R 工作流。只需告诉它你想做什么（"合并 OR"、"画森林图并按地区亚组"、"做含 3 种干预措施的网络 Meta"），技能会：检测 R 环境 → 引导数据录入 → 运行对应模型 → 输出可编辑矢量图与结构化结果摘要。

所有分析均在**本地**运行——不上传任何用户数据。

## 🎯 核心能力

| 功能模块 | 实现方式（R 包） |
|---------|------------------|
| **效应量计算** | `metafor`, `meta` — 自动识别 8 种：OR/RR/RD（二分类）、SMD/MD（连续）、HR（生存）、r→Fisher's z（相关）、单组率/均值 |
| **随机/固定/混合效应模型** | `rma()` / `metabin()` / `metacont()` — 支持 DL/REML/ML/PM/Hartung–Knapp/FE |
| **森林图 / 漏斗图 / GOSH 图** | `metafor`, `ggplot2` — 出版级 SVG（minimal/lancet/jama/revman/custom 主题） |
| **异质性评估** | `metafor` — I²、Cochran's Q、τ²、H²、预测区间（PI） |
| **发表偏倚检验** | `metafor`, `meta` — Egger 回归、Begg 秩相关、剪补法、选择模型、失安全系数 |
| **亚组分析** | `metafor`, `meta` — `mods = ~ factor(group) - 1`，自动输出组间异质性 |
| **元回归** | `metafor` — 单/多变量，连续/分类/交互项 + bubble plot |
| **网络 Meta 分析** | `netmeta`, `gemtc`, `multinma` — 一致性（节点拆分）、SUCRA、联赛表、贝叶斯（JAGS/Stan） |
| **贝叶斯 Meta 分析** | `bayesmeta`, `multinma`, `gemtc` — MCMC 后验分布 + 先验诊断 |
| **敏感性分析** | `metafor`, `dmetar` — Leave-one-out、累积元分析、GOSH 图（所有子集诊断） |
| **生存 Meta** | `survmeta`, `ipdmeta` — 合并 HR + KM 曲线伪个体数据（pseudo-IPD）重建 |
| **单组 / 诊断 Meta** | `meta`（`metaprop`/`metamean`/`metainc`/`metacor`）、`mada` — 比例/均值/发生率/相关、双变量 SROC |
| **试验序贯分析（TSA）** | `metafor::tes()` — 控制 I 类错误、所需信息量 |
| **功效分析** | `dmetar`, `meta` — 前瞻性样本量规划 |
| **偏倚风险（RoB 1.0/2.0/ROBINS-I）** | `robvis`, `dmetar` — 交通灯图 + 加权条形图 |
| **效应量转换（esc）** | d ↔ g ↔ logOR ↔ r ↔ Fisher's z 双向批量转换 + Hedges' g 校正 |
| **聚类稳健方差估计** | RVE（`robumeta`）+ CR2 标准误校正（`clubSandwich`）— 处理多结局/多臂依赖数据 |
| **多元 / 多水平 Meta** | `rma.mv()`, `robumeta` — UN/CS/AR1 + 复合对称 V 矩阵 |
| **Stata 等价实现** | `metareg`（→ `rma` + 置换检验）、`mvmeta`（→ `rma.mv` + 6 种协方差结构） |
| **系统评价流程** | `metagear` — PRISMA 流程图、筛选 GUI、PDF 批量、图形数字化、缺失值插补 |

## 📐 RevMan 对标

RevMan 5.x 全部分析类型（二分类、连续型、通用逆方差、单臂、比值比等）均已实现 1:1 代码映射。熟悉 RevMan 的用户可无缝迁移到完全可复现、可编辑的 R 输出，无需重新学习统计方法。

## 🔁 Stata 等价对照

| Stata 命令 | R 等价实现 | 说明 |
|-----------|-----------|------|
| `metan` | `metabin()` / `metacont()` | 同模型，输出更丰富 |
| `metareg` | `rma(..., mods = ~ x)` + 置换检验 | 增加 Knapp–Hartung 标准误 |
| `mvmeta` | `rma.mv()` + `V` 矩阵 | 6 种协方差结构（UN/CS/AR1/…） |
| `metabias` | `regtest()` / `ranktest()` | Egger / Begg |
| `metaninf` | `leave1out()` | 影响度诊断 |

## 🧭 交互式工作流

技能首次激活时呈现 7 大类菜单；若你的首条消息已包含足够信息，则跳过菜单直接分析：

1. **两组 Meta 分析** — 二分类 / 连续型 / 预计算 / 生存 / 相关 / 单组
2. **异质性与偏倚** — I²/Q/τ²、亚组、元回归、Egger/Begg/剪补、敏感性、GOSH、Baujat、Drapery
3. **高级模型** — NMA、贝叶斯 NMA（Stan/JAGS）、多水平、多元、IPD、剂量反应、生存、TSA、Bootstrap
4. **效应量与转换** — 均值/SD→d、t/F/r→d、d↔g、d↔logOR、r↔Fisher's z、OR↔logOR、批量、NNT
5. **可视化** — 森林图（5 主题）、漏斗图、气泡图、GOSH、网络图、联赛表、RoB 交通灯、功效曲线、Drapery、不一致性热图
6. **研究质量** — RoB 1.0/2.0、ROBINS-I、GRADE、PRISMA 检查表、AMSTAR-2
7. **系统评价流程** — PRISMA 流程图、筛选 GUI、PDF 批量、图形数字化、插补、文献管理

## 📦 安装

1. 确保已安装 **R 4.0+**（Windows 推荐：https://cran.r-project.org/bin/windows/base/）。
2. 将技能目录放置在 `~/.workbuddy/skills/meta-analysis/`。
3. 首次启动时技能自动检测并安装缺失的 R 包（可选择"全部安装"或"按需安装"）。

若原始数据为非标准格式（SPSS/Stata/SAS/Excel/Parquet/…），技能会建议安装 **`statdata-transfer`** 将其转换为所需 CSV 列后再分析。

## 🚀 使用示例

```text
"合并以下 5 项二分类研究的 OR 与 95%CI，并画森林图"
"用随机效应模型合并 5 项研究的 OR"
"画森林图，按地区做亚组分析"
"做网络Meta分析，有 3 种干预措施（A vs B，A vs 安慰剂）"
"做元回归：因变量为效应量，自变量为发表年份和样本量"
"检查发表偏倚：Egger 检验 + 剪补法"
"网状 Meta 一致性用节点拆分法"
"把 Cohen's d 转成 logOR"
```

## 📊 输出物

每次分析自动生成：
- **`analysis_complete.R`**：完整可复现的 R 脚本
- **森林图**（.svg + .png）
- **漏斗图**（标准版 + 轮廓增强版，.svg + .png）
- **`results_summary.md`**：结构化结果摘要（效应量、CI、I²、τ²、p 值）
- **数据 CSV 备份**
- **R Markdown / HTML 报告**（可选）

## 🎨 SVG 图形编辑

图形以可编辑 SVG 输出，推荐工具：

| 工具 | 类型 | 说明 |
|------|------|------|
| **Microsoft PowerPoint（2016+）** | Office | 直接拖入 `.svg`，右键 → **转换为形状** / **取消组合** 即可编辑文字与配色 |
| **Inkscape** | 免费/开源 | 完整矢量编辑；命令行导出：`inkscape in.svg --export-type=pdf --export-filename=out.pdf` |
| **Adobe Illustrator** | 付费 | 出版级精修，原生支持 SVG/EPS |
| **Affinity Designer** | 付费（一次性） | 轻量 AI 替代品 |
| **Boxy SVG** | 免费/付费 在线 | 快速改色/文字/尺寸 |

投稿格式转换（TIFF/EPS/PDF）可用 Inkscape：

```bash
inkscape forest_plot.svg --export-type=eps --export-filename=forest_plot.eps
inkscape forest_plot.svg --export-type=pdf --export-filename=forest_plot.pdf
inkscape forest_plot.svg --export-type=png --export-dpi=600 --export-filename=forest_plot.tiff
```

## 📁 目录结构

```
meta-analysis/
├── SKILL.md                       # 技能主定义（中英双语，英文在前）
├── README.md / README_ZH.md      # 本文件
├── LICENSE                        # MIT
├── requirements.txt              # R 包清单
├── assets/
│   └── icon.svg                   # 技能 Logo
├── scripts/
│   ├── setup_packages.R          # 环境检测 + 包安装器
│   ├── meta_analysis_core.R      # 核心引擎（escalc/rma/forest/funnel）
│   ├── effect_size_conversions.R # esc 封装、d↔g、RVE
│   ├── stata_equivalents.R       # metareg / mvmeta 等价实现
│   └── network_meta_analysis.R   # netmeta / gemtc / multinma
└── references/
    ├── interactive_menu.md        # 完整菜单树 + 数据格式指引
    ├── data_templates.md          # 分类型 CSV 模板 + 校验
    ├── revman_complete.md         # RevMan → R 1:1 代码映射
    ├── stata_to_r_mapping.md      # Stata metareg/mvmeta → R 等价实现
    ├── advanced_analysis.md       # 多元/多水平/IPD/剂量反应
    ├── single_group_meta.md       # metaprop/metamean/metainc/metacor
    ├── survival_meta.md           # survmeta / KM 伪个体数据
    ├── tsa_diagnostics.md         # tes / Baujat / Drapery / 选择模型
    ├── diagnosis_meta.md          # mada 双变量 / SROC
    ├── bayesian_nma.md            # multinma / gemtc 工作流
    ├── esc_robust_meta.md         # esc 转换 + RVE（robumeta/clubSandwich）
    ├── review_workflow.md         # metagear PRISMA / 筛选 / 数字化
    ├── r_packages.md              # 包清单
    ├── citations.md               # 方法学引用
    └── purpose_zh.md              # 中文 Purpose 文本镜像
```

## 🔴 注意事项

- R 环境必须 **4.0+**，技能启动时自动检测
- 所有分析依赖本地 R 环境，**不上传任何用户数据**
- 统计结果需结合专业背景解读，技能不替代统计/临床判断

## 📚 引用

- Harrer M, Cuijpers P, Furukawa TA, Ebert DD. (2021). *Doing Meta-Analysis with R: A Hands-On Guide*. CRC Press.
- Viechtbauer W. (2010). Conducting meta-analyses in R with the metafor package. *J Stat Softw*, 36(3), 1–48.
- Balduzzi S, Rücker G, Schwarzer G. (2019). How to perform a meta-analysis with R: a practical tutorial. *Evid Based Ment Health*, 22(4), 153–160.
- Rücker G, et al. (2016). netmeta: Network Meta-Analysis using Frequentist Methods. *BMC Med Res Methodol*, 16, 1–8.
- Salanti G. (2012). Network meta-analysis in mental health. *Evid Based Ment Health*, 15(1), 16–20.

## License

MIT License. See `LICENSE` file for details.
