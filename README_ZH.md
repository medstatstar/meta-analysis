# meta-analysis 技能

[🇬🇧 English (英文)](./README.md)

## 概述

`meta-analysis` 是基于 R 语言的全方位 Meta 分析 WorkBuddy 技能。通过自然语言对话驱动分析全流程，覆盖 RevMan 全部功能 + Stata metareg/mvmeta 等价实现。

## 🎯 核心能力

| 功能模块 | 实现方式 |
|---------|---------|
| **效应量计算** | 二分类（OR/RR/RD）、连续型（SMD/MD）、生存数据（HR）、相关性（r）等 8 种效应量自动识别与计算 |
| **随机/固定效应模型** | rma() / metabin() / metacont()，支持 DL/REML/ML/PM/Hartung-Knapp 等 6 种估计方法 |
| **森林图 / 漏斗图** | Publication-ready SVG 矢量图，支持 Lancet/JAMA/自定义风格 |
| **异质性评估** | I²、Cochran's Q、tau²、H²、预测区间（PI） |
| **发表偏倚检验** | Egger 回归、Begg 秩相关、剪补法、选择模型、失安全系数 |
| **亚组分析** | `mods = ~ factor(group) - 1`，自动输出组间异质性 |
| **元回归** | 单/多变量元回归，支持连续/分类/交互项 + bubble plot |
| **网络 Meta 分析** | `netmeta`：一致性检验、节点拆分法、SUCRA、联赛表 |
| **贝叶斯 Meta 分析** | `bayesmeta`：MCMC 后验分布 + 先验诊断 |
| **敏感性分析** | Leave-one-out、累积元分析、GOSH 图（所有子集诊断） |
| **功效分析** | 前瞻性样本量规划 |
| **效应量转换（esc）** | d ↔ logOR ↔ Fisher's z 双向批量转换 + Hedges' g 校正 |
| **聚类稳健方差估计** | RVE（robumeta）+ CR2 标准误校正（clubSandwich）— 处理多结局/多臂依赖数据 |
| **Stata 等价实现** | `metareg`（→ rma + permutation test）、`mvmeta`（→ rma.mv + 6 种协方差结构） |
| **RevMan 对标** | RevMan 5.x 全部 12 项功能 1:1 代码映射 |

## 📦 安装

1. 确保已安装 R 4.0+（Windows 推荐：https://cran.r-project.org/bin/windows/base/）
2. 将技能目录放置在 `~/.workbuddy/skills/meta-analysis/`
3. 首次启动时技能自动检测并安装缺失的 R 包

## 🚀 使用示例

```text
"跑个Meta分析，数据如下：..."
"用随机效应模型合并 5 项研究的 OR"
"画森林图，按地区做亚组分析"
"做Meta分析，有 3 种干预措施(A: 甲药 vs 乙药; B: 甲药 vs 安慰剂)"
"做元回归：因变量为效应量，自变量为发表年份和样本量"
"检查发表偏倚：Egger 检验 + 剪补法"
"网状 Meta 一致性用节点拆分法"
```

## 📊 输出物

每次分析自动生成：
- **`analysis_complete.R`**：完整可复现的 R 脚本
- **森林图 / 漏斗图**（.svg + .png）
- **`results_summary.md`**：结构化结果摘要
- **数据 CSV 备份**
- **R Markdown / HTML 报告**（可选）

## 🔴 注意事项

- R 环境必须 4.0+，技能启动时自动检测
- 所有分析依赖本地 R 环境，不上传任何用户数据
- 统计结果需结合专业背景解读，技能不替代统计/临床判断

## 📚 引用

- Harrer M, et al. (2019). *Doing Meta-Analysis with R*. CRC Press.
- Viechtbauer W. (2010). *J Stat Softw*, 36(3), 1-48.
- Balduzzi S, et al. (2019). *Evid Based Ment Health*, 22(4), 153-160.
- Rücker G, et al. (2016). *BMC Med Res Methodol*, 16, 1-8.

## License

MIT License. See `LICENSE` file for details.
