# Meta-Analysis 技能测试用例（从简单到复杂）

> 覆盖 Simple / Complex / Vague 三种分类，检查边界条件与潜在 bug

---

## 测试用例 1：Simple · 最小数据集二分类 Meta

**分类**：Simple
**输入**：只有 2 项研究（最小可行数据集）

```
合并这 2 项二分类研究的 OR：
研究A: 实验组 10/50, 对照组 5/50
研究B: 实验组 20/50, 对照组 10/50
```

**预期行为**：
- ✅ 生成 R 代码并进入安全预览模式
- ✅ 不自动执行（无 `--yes`）
- ✅ 正确计算 OR、CI、I²

**潜在 bug 检查**：
- [ ] **Bug #1**：当只有 2 项研究时，`analyze_publication_bias` 中 `nrow(es_data) >= 3` 条件不满足，Egger/Begg/trimfill 都不运行。确认代码不会因空结果列表崩溃。
- [ ] **Bug #2**：`rma()` 在 k=2 时 I² 计算可能返回 NA（分母为 0）。确认输出不会显示 `"NA%"`。
- [ ] **Bug #3**：`predict()` 在 k=2 时可能返回异常。确认预测区间代码不会崩溃。

---

## 测试用例 2：Simple · 连续型 SMD Meta（含缺失值）

**分类**：Simple
**输入**：连续型研究，其中 1 项研究的 SD 缺失

```
合并以下 4 项连续型研究的 SMD：
研究A: 实验组 n=30 mean=10.5 sd=2.1, 对照组 n=30 mean=9.0 sd=1.8
研究B: 实验组 n=25 mean=12.0 sd=NA, 对照组 n=25 mean=10.0 sd=2.0
研究C: 实验组 n=40 mean=11.0 sd=2.5, 对照组 n=40 mean=9.5 sd=2.2
研究D: 实验组 n=35 mean=10.8 sd=2.0, 对照组 n=35 mean=9.2 sd=1.9
```

**预期行为**：
- ✅ 检测到缺失 SD，提示用户提供或插补
- ✅ 不自动用 0 填充

**潜在 bug 检查**：
- [ ] **Bug #4**：`escalc(measure = "SMD", ...)` 收到 `sd1i = NA` 时会返回 `yi = NA, vi = NA`。确认后续 `rma()` 不会因 NA 而崩溃（metafor 默认 `na.rm = FALSE`）。
- [ ] **Bug #5**：`create_forest_plot` 中 `order(es_data$yi, decreasing = TRUE)` 在有 NA 时行为：`order(..., na.last = TRUE)` 默认把 NA 放最后，但代码未显式指定 `na.last`。确认排序不会出错。

---

## 测试用例 3：Simple · 效应量转换（边界值）

**分类**：Simple
**输入**：极端效应量值

```
把 Cohen's d = 0 转成 logOR
把 Cohen's d = 10 转成 logOR
把 OR = 0.01 转成 logOR
把 OR = 100 转成 logOR
```

**预期行为**：
- ✅ d=0 → logOR=0
- ✅ d=10 → 正常计算（虽临床不常见）
- ✅ OR=0.01 → logOR ≈ -4.605
- ✅ OR=100 → logOR ≈ 4.605

**潜在 bug 检查**：
- [ ] **Bug #6**：`esc_mean_sd` 中 `grp1sd = 0` 会导致除以零错误。确认 `calculate_effect_size` 对 SD=0 的处理。
- [ ] **Bug #7**：`run_esc_transform` 中 `from_measure = "or", to_measure = "logOR"` 的公式：代码中 `.or_to_logor` 未定义（只有 `.d_to_logor`, `.logor_to_d`, `.d_to_z`, `.z_to_d`）。**确认是否缺少 OR↔logOR 的转换函数。**

---

## 测试用例 4：Complex · 网络 Meta（多决策路由菜单）

**分类**：Complex
**输入**：多参数决策

```
我想做个网络 Meta，有 5 种干预措施（A/B/C/D/E），10 项研究
比较主要终点（二分类）和安全性终点（连续型）
想做频率学派和贝叶斯两种
还要做一致性检验和 SUCRA 排序
但不确定要不要做剂量反应
```

**预期行为**：
- ✅ 弹出路由菜单（Triage §5.2 Complex）
- ✅ 逐步确认：分析框架 → 结局选择 → 剂量反应
- ✅ 含"详细解释差异"入口

**潜在 bug 检查**：
- [ ] **Bug #8**：`run_frequentist_nma` 要求输入 `TE, seTE, treat1, treat2, studlab`。如果用户给的是原始事件数数据，需要先转换为效应量。确认代码是否有预处理步骤。
- [ ] **Bug #9**：当只有 5 种干预、10 项研究时，网络可能不连通（某些干预间无直接比较）。`netmeta` 会报错，确认错误处理。
- [ ] **Bug #10**：贝叶斯 NMA（`multinma`/`gemtc`）需要 Stan/JAGS 后端。如果未安装，确认错误提示清晰。

---

## 测试用例 5：Complex · 亚组分析（边界情况）

**分类**：Complex
**输入**：亚组只有 1 个水平

```
我有 8 项研究，按地区做亚组分析，但所有研究都来自亚洲
```

**预期行为**：
- ✅ 检测到只有 1 个亚组，提示无法做组间比较
- ✅ 仍输出合并效应

**潜在 bug 检查**：
- [ ] **Bug #11**：`run_subgroup_analysis` 中 `anova(model, btt = 2:length(levels))` 当只有 1 个水平时，`length(levels) = 1`，`2:1` 返回 `c(2, 1)`，会导致 `anova()` 报错。**这是确认的 bug，需要修复。**

---

## 测试用例 6：Vague · 完全模糊的需求（grill-me）

**分类**：Vague
**输入**：

```
我想做个 Meta 分析，但不确定该用哪种模型，能帮我梳理一下吗？
```

**预期行为**：
- ✅ 触发 grill-me 模式（Triage §5.2 Vague）
- ✅ 每轮问 1-3 个聚焦问题，带推荐默认
- ✅ 不甩全量菜单

**潜在 bug 检查**：
- [ ] **Bug #12**：grill-me 追问后，用户回答"二分类，两组比较，无特殊结构"。确认代码能正确映射到 `calculate_effect_size(data, "dichotomous", measure = "OR")`。
- [ ] **Bug #13**：多轮追问后，确认状态管理（上下文传递）不会丢失。

---

## 测试用例 7：Complex · 元回归（多协变量）

**分类**：Complex
**输入**：

```
做元回归，协变量是发表年份、样本量、研究质量评分（1-7）
```

**预期行为**：
- ✅ 生成 `rma(yi = yi, vi = vi, mods = ~ 发表年份 + 样本量 + 质量评分, ...)`
- ✅ 输出各协变量的回归系数和 p 值

**潜在 bug 检查**：
- [ ] **Bug #14**：`run_meta_regression` 中 `length(covariates) == 1` 时才生成气泡图。多协变量时 `bubble_plot = NULL`，确认后续代码不会尝试绘制 NULL 图。
- [ ] **Bug #15**：协变量名含中文（如 `发表年份`），`paste("yi ~", paste(covariates, collapse = " + "))` 生成的公式在 R 中可能有问题（中文列名需要反引号包裹）。确认代码处理。

---

## 测试用例 8：Complex · 敏感性分析（多种类型）

**分类**：Complex
**输入**：

```
做 leave-one-out + 累积 Meta + 模型比较（DL/REML/ML/FE）
```

**预期行为**：
- ✅ `run_sensitivity_analysis(es_data, analysis_type = "all")`
- ✅ 返回三种敏感性结果

**潜在 bug 检查**：
- [ ] **Bug #16**：`leave1out` 结果中 `loo$I2` 在某些版本中可能不存在（`leave1out` 返回的是 `data.frame`，列名可能是 `I2` 或其他）。确认列名正确。
- [ ] **Bug #17**：`quality` 列是数值型（1-7）时，`es_data$quality == "low risk"` 返回 NA（因为 NA == "low risk" 是 NA），`NA | TRUE` 是 TRUE，但 `NA | FALSE` 是 NA。`if (NA)` 会报错。**这是确认的 bug，需要修复。**

---

## 测试用例 9：Complex · 发表偏倚（小样本）

**分类**：Complex
**输入**：

```
3 项研究，检查发表偏倚
```

**预期行为**：
- ✅ Egger 和 Begg 测试运行（k≥3）
- [ ] trimfill 不运行（k<5），返回 NULL

**潜在 bug 检查**：
- [ ] **Bug #18**：`trimfill` 在 k<5 时跳过，但 `analyze_publication_bias` 返回的列表中 `trimfill` 为 NULL。`generate_results_summary` 中 `if (!is.null(pub_bias))` 检查的是外层列表，不是内层元素。确认 `pub_bias$trimfill` 为 NULL 时不会崩溃。
- [ ] **Bug #19**：`regtest` 和 `ranktest` 在 k=3 时可能不稳定（p 值可能 NA）。确认输出格式。

---

## 测试用例 10：Complex · 贝叶斯 NMA（高复杂度）

**分类**：Complex
**输入**：

```
做贝叶斯网络 Meta，4 种干预，Stan 后端
先验：half-normal (0, 0.5)
做一致性检验和节点拆分
```

**预期行为**：
- ✅ 检查 `multinma` 是否安装
- ✅ 生成 Stan 代码
- ✅ 输出后验分布和排序

**潜在 bug 检查**：
- [ ] **Bug #20**：`multinma` 需要 `cmdstanr` 或 `rstan`。如果未安装，确认错误提示清晰，不会导致整个技能崩溃。
- [ ] **Bug #21**：贝叶斯 NMA 计算可能耗时很长（几分钟）。确认有超时提示或进度指示。
- [ ] **Bug #22**：如果用户网络不稳定，Stan 编译可能失败。确认错误处理。

---

## 确认的 Bug 清单（代码审查 + 验证后）

| # | 位置 | 问题 | 严重程度 | 触发条件 |
|---|------|------|---------|---------|
| 11 | `run_subgroup_analysis` L220 | 单亚组时 `2:length(levels)` = `c(2,1)`，`anova(model, btt = c(2, 1))` 中 btt=2 超出模型系数范围 | 🔴 高 | 亚组只有 1 个水平 |
| 17 | `run_sensitivity_analysis` L261 | `es_data$quality >= 6` 当 quality 为字符型时返回 NA，`NA \| FALSE` = NA，导致子集选取异常 | 🔴 高 | quality 列是字符型（如 "low risk"） |
| 7  | `run_esc_transform` L68-101 | 没有直接的 OR↔logOR 转换函数，OR→logOR 需用户手动 `log(OR)` | 🟡 中 | 用户要求 OR 转 logOR |
| 15 | `run_meta_regression` L229 | 中文列名在 R 公式中可能需要反引号包裹 | 🟡 中 | 协变量含中文且 R locale 不匹配 |
| 5  | `create_forest_plot` L314 | `order(yi, decreasing = TRUE)` 未显式指定 `na.last` | 🟢 低 | yi 含 NA |
| 1  | `generate_results_summary` L393-394 | k=2 时 `predict()` 预测区间可能异常 | 🟢 低 | 仅 2 项研究 |

### 误报澄清

| # | 问题 | 结论 |
|---|------|------|
| 18 | trimfill 为 NULL 时 `generate_results_summary` 崩溃 | ❌ 误报。代码正确检查 `!is.null(pub_bias$trimfill)` |
| 16 | `loo$I2` 列不存在 | ❌ 误报。metafor 3.0+ 的 `leave1out()` 返回 `I2` 列 |
| 8  | NMA 缺少预处理步骤 | ❌ 误报。`run_frequentist_nma` 要求用户提供效应量数据，非原始数据 |

---

## 运行方式

```bash
cd meta-analysis
Rscript scripts/test_runner.R  # 如果存在
# 或手动在 R 中逐条测试
```
