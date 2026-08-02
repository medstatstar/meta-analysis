# Meta-Analysis 技能测试用例 v2（验证修复 + 发现新问题）

> 验证 Bug #11 和 #17 的修复效果，并检查其他边界条件

---

## 测试用例 1：单亚组分析（Bug #11 修复验证）

**输入**：
```
我有 8 项研究，按地区做亚组分析，但所有研究都来自亚洲：
研究1-8: 均为亚洲地区，二分类数据（实验组事件数/样本数，对照组事件数/样本数）
研究A: 15/50 vs 10/50
研究B: 20/60 vs 12/60
研究C: 18/55 vs 10/55
研究D: 22/58 vs 15/58
研究E: 19/52 vs 11/52
研究F: 17/48 vs 9/48
研究G: 21/56 vs 13/56
研究H: 16/50 vs 10/50
```

**预期行为**：
- ✅ 代码不崩溃（不调用 `anova(model, btt=c(2,1))`）
- ✅ 输出提示"仅一个亚组，组间比较检验已跳过"
- ✅ 正常输出合并效应和各项研究的结果

**验证点**：
- [ ] 不再报错 `Error in anova.rma(model, btt = c(2, 1))`
- [ ] 返回列表中 `between_group_Q` 和 `between_group_p` 为 NA

---

## 测试用例 2：敏感性分析 quality 列为字符型（Bug #17 修复验证）

**输入**：
```
做敏感性分析，我的 quality 列是字符型：
研究1: yi=0.5, vi=0.1, quality="low risk"
研究2: yi=0.6, vi=0.08, quality="low risk"
研究3: yi=0.4, vi=0.12, quality="high risk"
研究4: yi=0.7, vi=0.09, quality="low risk"
研究5: yi=0.3, vi=0.15, quality="unclear"
```

**预期行为**：
- ✅ 不崩溃（不出现 `if (NA)` 错误）
- ✅ 正确筛选 `quality == "low risk"` 的研究（研究1、2、4）
- ✅ 输出高质量研究子集的合并效应

**验证点**：
- [ ] `q_ok` 正确返回 `c(TRUE, TRUE, FALSE, TRUE, FALSE)`
- [ ] `high_q` 包含 3 项研究
- [ ] `rma()` 在 3 项研究上正常运行

---

## 测试用例 3：敏感性分析 quality 列为数值型（Bug #17 另一分支）

**输入**：
```
做敏感性分析，我的 quality 列是数值型（1-7）：
研究1: yi=0.5, vi=0.1, quality=6
研究2: yi=0.6, vi=0.08, quality=7
研究3: yi=0.4, vi=0.12, quality=4
研究4: yi=0.7, vi=0.09, quality=6
研究5: yi=0.3, vi=0.15, quality=5
```

**预期行为**：
- ✅ 正确筛选 `quality >= 6` 的研究（研究1、2、4）
- ✅ 输出高质量研究子集的合并效应

**验证点**：
- [ ] `q_ok` 正确返回 `c(TRUE, TRUE, FALSE, TRUE, FALSE)`
- [ ] 不报类型转换错误

---

## 测试用例 4：两组 Meta 恰好 3 项研究（发表偏倚边界）

**输入**：
```
合并这 3 项二分类研究的 OR，并做发表偏倚检验：
研究A: 15/50 vs 10/50
研究B: 20/60 vs 12/60
研究C: 18/55 vs 10/55
```

**预期行为**：
- ✅ Egger 和 Begg 测试运行（k≥3）
- [ ] trimfill 不运行（k<5）

**验证点**：
- [ ] `analyze_publication_bias` 中 `nrow(es_data) >= 3` 条件满足
- [ ] `nrow(es_data) >= 5` 条件不满足，trimfill 跳过
- [ ] 返回列表 `pub_bias` 含 `egger` 和 `begg`，无 `trimfill`

---

## 测试用例 5：两组 Meta 恰好 5 项研究（trimfill 边界）

**输入**：
```
合并这 5 项连续型研究的 SMD，并做发表偏倚检验：
研究A: n=30, mean=10.5, sd=2.1 vs n=30, mean=9.0, sd=1.8
研究B: n=25, mean=12.0, sd=2.3 vs n=25, mean=10.0, sd=2.0
研究C: n=40, mean=11.0, sd=2.5 vs n=40, mean=9.5, sd=2.2
研究D: n=35, mean=10.8, sd=2.0 vs n=35, mean=9.2, sd=1.9
研究E: n=28, mean=11.5, sd=2.4 vs n=28, mean=9.8, sd=2.1
```

**预期行为**：
- ✅ trimfill 运行（k≥5）
- ✅ 输出剪补法校正后的效应

**验证点**：
- [ ] `nrow(es_data) >= 5` 条件满足
- [ ] `trimfill(model_result)` 正常执行
- [ ] 返回 `pub_bias$trimfill` 不为 NULL

---

## 测试用例 6：连续型 SMD 含 NA（order 排序边界）

**输入**：
```
合并以下 4 项连续型研究的 SMD（其中 1 项 SD 缺失）：
研究A: n=30, mean=10.5, sd=2.1 vs n=30, mean=9.0, sd=1.8
研究B: n=25, mean=12.0, sd=NA vs n=25, mean=10.0, sd=2.0
研究C: n=40, mean=11.0, sd=2.5 vs n=40, mean=9.5, sd=2.2
研究D: n=35, mean=10.8, sd=2.0 vs n=35, mean=9.2, sd=1.9
```

**预期行为**：
- ✅ 检测到缺失 SD
- ✅ 不崩溃（`order()` 处理 NA）

**验证点**：
- [ ] `escalc()` 返回的 `yi` 含 NA
- [ ] `order(yi, decreasing = TRUE)` 不报错（NA 默认放最后）
- [ ] `rma()` 的 `na.rm` 参数处理正确

---

## 测试用例 7：元回归含中文列名

**输入**：
```
做元回归，协变量是发表年份和样本量：
研究1: yi=0.5, vi=0.1, 发表年份=2018, 样本量=100
研究2: yi=0.6, vi=0.08, 发表年份=2019, 样本量=120
研究3: yi=0.4, vi=0.12, 发表年份=2020, 样本量=80
研究4: yi=0.7, vi=0.09, 发表年份=2021, 样本量=150
研究5: yi=0.3, vi=0.15, 发表年份=2022, 样本量=90
```

**预期行为**：
- ✅ 公式正确生成
- ✅ 不报错（中文列名处理）

**验证点**：
- [ ] `formula_str` 包含正确的列名
- [ ] `rma(formula, vi = vi, data = es_data)` 能识别中文列名

---

## 测试用例 8：网络 Meta（不连通网络）

**输入**：
```
做网络 Meta，4 种干预：
研究1: A vs B
研究2: A vs B
研究3: C vs D
研究4: C vs D
```

**预期行为**：
- ✅ 检测到网络不连通
- ✅ 提示用户某些干预间无直接比较

**验证点**：
- [ ] `netmeta()` 能运行但警告网络不连通
- [ ] 代码不崩溃

---

## 测试用例 9：单组率 Meta

**输入**：
```
合并以下 5 项研究的发病率：
研究A: 事件数=20, 样本数=100
研究B: 事件数=30, 样本数=150
研究C: 事件数=15, 样本数=80
研究D: 事件数=25, 样本数=120
研究E: 事件数=18, 样本数=90
```

**预期行为**：
- ✅ 正确调用 `escalc(measure = "PLO", xi = events, ni = n)`
- ✅ 使用 `plogis` 转换绘制森林图

**验证点**：
- [ ] `transform = "plogis"`
- [ ] `create_forest_plot` 中 `f = plogis`, `ref = 0.5`

---

## 测试用例 10：一键出图 + 结果摘要（完整流程）

**输入**：
```
合并这 4 项二分类研究的 OR，并保存结果：
研究A: 15/50 vs 10/50
研究B: 20/60 vs 12/60
研究C: 18/55 vs 10/55
研究D: 22/58 vs 15/58
保存到 output/ 目录
```

**预期行为**：
- ✅ 运行完整流程：效应量计算 → 模型 → 异质性 → 发表偏倚 → 森林图 → 漏斗图 → 摘要
- ✅ 输出文件：`output/meta_forest.svg`, `output/meta_forest.png`, `output/meta_funnel.svg`, `output/meta_funnel.png`, `output/meta_results.md`

**验证点**：
- [ ] `ma_analyze()` 正确返回 `ma_result` 对象
- [ ] `ma_save()` 创建目录并保存所有文件
- [ ] `generate_results_summary()` 不因 `pub_bias$trimfill` 为 NULL 而崩溃

---

## 验证脚本

```r
# 快速验证脚本（可在 R 中运行）
source("scripts/meta_analysis_core.R")

# === 测试 1：单亚组 ===
data_sub <- data.frame(
  study = paste0("研究", 1:8),
  event_exp = c(15, 20, 18, 22, 19, 17, 21, 16),
  n_exp = c(50, 60, 55, 58, 52, 48, 56, 50),
  event_ctrl = c(10, 12, 10, 15, 11, 9, 13, 10),
  n_ctrl = c(50, 60, 55, 58, 52, 48, 56, 50),
  region = rep("亚洲", 8)
)
es <- calculate_effect_size(data_sub, "dichotomous", "OR")
res_sub <- run_subgroup_analysis(es, "region")
cat("between_group_Q:", res_sub$between_group_Q, "\n")  # 应为 NA

# === 测试 2：quality 字符型 ===
data_q <- data.frame(
  study = paste0("研究", 1:5),
  yi = c(0.5, 0.6, 0.4, 0.7, 0.3),
  vi = c(0.1, 0.08, 0.12, 0.09, 0.15),
  quality = c("low risk", "low risk", "high risk", "low risk", "unclear")
)
res_q <- run_sensitivity_analysis(data_q, "quality")
cat("high_quality exists:", !is.null(res_q$high_quality), "\n")  # 应为 TRUE

# === 测试 3：quality 数值型 ===
data_qn <- data.frame(
  study = paste0("研究", 1:5),
  yi = c(0.5, 0.6, 0.4, 0.7, 0.3),
  vi = c(0.1, 0.08, 0.12, 0.09, 0.15),
  quality = c(6, 7, 4, 6, 5)
)
res_qn <- run_sensitivity_analysis(data_qn, "quality")
cat("high_quality exists:", !is.null(res_qn$high_quality), "\n")  # 应为 TRUE
```
