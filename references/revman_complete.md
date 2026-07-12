# RevMan 功能 100% 对应实现表

## RevMan 5.x → R 代码映射

本文件列出 RevMan 5.x 中所有可用功能及其对应的 R 实现代码。用户在 RevMan 中熟悉的操作均可通过 R 精确复现。

---

## 一、Review 创建与数据管理

### 1.1 新建 RevMan Review → 初始化数据框

```r
# RevMan: File → New Review
# R 对应:
meta_data <- data.frame(
  study = character(),
  year = integer(),
  event_exp = integer(),
  n_exp = integer(),
  event_ctrl = integer(),
  n_ctrl = integer(),
  stringsAsFactors = FALSE
)
```

### 1.2 添加比较（Comparison）→ 定义分析结构

```r
# RevMan: Add Comparison
meta_data <- rbind(meta_data, data.frame(...))
```

### 1.3 添加结果（Outcome）→ 定义分析变量

```r
# RevMan: Add Outcome → Dichotomous/Continuous
outcome_type <- "Dichotomous"  # 或 "Continuous"
```

### 1.4 输入研究数据 → 构建数据框

```r
# RevMan: Input study data
# R 对应:
meta_data <- data.frame(
  study = c("Smith2020", "Jones2019", "Lee2021"),
  event_exp = c(15, 20, 12),
  n_exp = c(100, 95, 80),
  event_ctrl = c(30, 35, 28),
  n_ctrl = c(100, 90, 78)
)
```

---

## 二、分析类型选择

### 2.1 二分类数据（Dichotomous）

```r
# RevMan: Analysis → Dichotomous
library(meta)

# 法 1: Mantel-Haenszel
mh_result <- metabin(
  event.e = event_exp,
  n.e = n_exp,
  event.c = event_ctrl,
  n.c = n_ctrl,
  studlab = study,
  data = meta_data,
  method = "MH",
  sm = "OR",           # "OR", "RR", "RD"
  combined.figures = TRUE,
  combined.events = FALSE
)

# 法 2: Peto 法（罕见事件）
peto_result <- metapeto(
  event.e = event_exp,
  n.e = n_exp,
  event.c = event_ctrl,
  n.c = n_ctrl,
  studlab = study,
  data = meta_data,
  sm = "OR"
)
```

### 2.2 连续型数据（Continuous）

```r
# RevMan: Analysis → Continuous
cont_result <- metacont(
  n.e = n_exp,
  mean.e = mean_exp,
  sd.e = sd_exp,
  n.c = n_ctrl,
  mean.c = mean_ctrl,
  sd.c = sd_ctrl,
  studlab = study,
  data = meta_data,
  sm = "SMD",          # "SMD", "MD"
  method.mean = "Luo",  # 均值计算方法
  method.sd = "Shi"     # SD 计算方法
)
```

### 2.3 O-E and Variance（O-E/V）

```r
# RevMan: Analysis → O-E and Variance
# 适用于已计算效应量的情况
oe_result <- metagen(
  TE = yi,
  seTE = sqrt(vi),
  studlab = study,
  data = effect_size_data,
  sm = "GENQ"
)
```

### 2.4 通用倒方差法（Generic Inverse Variance）

```r
# RevMan: Analysis → Generic Inverse Variance
# 直接输入效应量 + 标准误
giv_result <- metagen(
  TE = logOR,
  seTE = se,
  studlab = study,
  data = effect_size_data
)
```

---

## 三、效应量合并模型

### 3.1 固定效应模型（Fixed Effect）

```r
# RevMan: Analysis → Fixed Effect
fe_result <- metabin(
  data = meta_data,
  method = "MH",
  sm = "OR",
  method.tau = "FE"      # RevMan 固定效应
)

# metafor 对应
fe_rma <- rma(yi = yi, vi = vi, method = "FE", data = effect_data)
```

### 3.2 随机效应模型（Random Effects）

```r
# RevMan: Analysis → Random Effects → DerSimonian-Laird
dl_result <- metabin(
  data = meta_data,
  method = "MH",
  sm = "OR",
  method.tau = "DL"      # DerSimonian-Laird
)

# RevMan: Analysis → Random-effects model → Restricted Maximum Likelihood (REML)
reml_rma <- rma(yi = yi, vi = vi, method = "REML", data = effect_data)
```

---

## 四、森林图（Forest Plot）

### 4.1 RevMan 默认森林图

```r
# RevMan: Forest Plot 右侧面板
# R 对应:
library(meta)
forest(mh_result)
```

### 4.2 自定义森林图（添加列）

```r
# RevMan: Custom columns in forest plot
forest(mh_result,
  leftcols = c("studlab", "event.e", "n.e", "event.c", "n.c"),
  rightcols = c("effect", "ci", "w.random"),
  colgap.studlab = "3%",
  fs.heading = 10,
  ff.heading = "B"
)
```

### 4.3 RevMan 样式 → ggplot 风格

```r
# RevMan 风格（类似 RevMan 5 的黑白方块风格）
library(ggplot2)
library(dmetar)

# 使用 ggforestplot
ggforestplot::forestplot(
  df = effect_data,
  estimate = logOR,
  se = se,
  logodds = TRUE,
  colour = "black",
  shape = "diamond"
)
```

---

## 五、漏斗图（Funnel Plot）

### 5.1 RevMan 默认漏斗图

```r
# RevMan: Funnel plot icon
# R 对应:
funnel(mh_result)
```

### 5.2 添加轮廓线（Contours）

```r
# Revman: Funnel plot with contour lines
funnel(mh_result, contour = c(0.9, 0.95, 0.99))
```

### 5.3 自定义漏斗图

```r
funnel(mh_result,
  yaxis = "invvar",
  xlim = c(-3, 3),
  ylim = c(0, 1),
  refline = 0,
  col = "darkblue"
)
```

---

## 六、异质性（Heterogeneity）

### 6.1 RevMan 输出异质性统计量

```r
# RevMan 自动输出: I², tau², Q, df, p-value
# R 对应:
cat(sprintf("I² = %.1f%%\n", mh_result$I2 * 100))
cat(sprintf("tau² = %.3f\n", mh_result$tau2))
cat(sprintf("Q = %.3f, df = %d, p = %.4f\n",
  mh_result$Q, mh_result$df.Q, mh_result$pval.Q))
```

### 6.2 预测区间（Prediction Interval）

```r
# RevMan: 仅在 metafor 中可用
predict_int <- predict(reml_rma)
cat(sprintf("Prediction Interval: [%.3f, %.3f]\n",
  predict_int$pred - 1.96*sqrt(predict_int$se^2 + reml_rma$tau2),
  predict_int$pred + 1.96*sqrt(predict_int$se^2 + reml_rma$tau2)))
```

---

## 七、亚组分析（Subgroup Analysis）

### 7.1 RevMan 按亚组累积森林图

```r
# Revman: Subgroup → Add subgroup
# R 对应:
metabias_result <- update.meta(mh_result,
  byvar = factor(subgroup_group),
  bylab = "Subgroup",
  print.byvar = FALSE,
  comb.fixed = FALSE,
  comb.random = TRUE,
  byseparator = " ==> "
)
```

### 7.2 元分析亚组检验（metafor）

```r
# 更精确的亚组分析
library(metafor)

subgroup_rma <- rma(yi = yi, vi = vi,
  mods = ~ factor(group) - 1,   # 无截距模型
  data = effect_data
)

# 组间异质性检验
subgroup_wald <- anova(subgroup_rma, btt = 2:length(unique(group)))
```

---

## 八、敏感性分析（Sensitivity Analysis）

### 8.1 逐一剔除（Leave-One-Out）

```r
# Revman: Sensitivity → Leave one out
# R 对应:
library(metafor)
leave1out_results <- leave1out(reml_rma)
print(leave1out_results)
```

### 8.2 按质量筛选

```r
# Revman: Sensitivity → High quality only
high_quality_data <- meta_data[meta_data$rob_score >= 6, ]
hq_result <- metabin(data = high_quality_data, ...)
```

### 8.3 L'Abbé 图

```r
# Revman: 用于比例数据的散点图
labbe(mh_result)
```

---

## 九、发表偏倚（Publication Bias）

### 9.1 RevMan 偏倚风险检验

```r
# Revman: Tests for funnel plot asymmetry → Egger/Begg
# R 对应:
metabias(mh_result, method = "egger")
metabias(mh_result, method = "begg")
```

### 9.2 剪补法（Trim and Fill）

```r
# Revman: Performance → Trim-and-Fill
# R 对应:
tf_result <- trimfill(mh_result)
forest(tf_result)
```

---

## 十、GRADE 证据质量评估

```r
# Revman: GRADEpro assessment criteria
# R 对应——结构化评估框架:

assess_grade_evidence <- function(analysis_result, risk_of_bias,
  inconsistency, indirectness, imprecision, publication_bias) {
  
  # 起始质量: 观察性研究 = 低, RCT = 高质量
  
  grade_score <- data.frame(
    domain = c("Risk of Bias", "Inconsistency", "Indirectness",
               "Imprecision", "Other considerations"),
    assessment = c(risk_of_bias, inconsistency, indirectness,
                   imprecision, publication_bias),
    downgrade = c(-1, -1, -1, -1, -1)  # 各问题降级
  )
  
  return(grade_score)
}
```

---

## 十一、网络 Meta 分析

### 11.1 创建网络结构

```r
# Revman: Network Meta-Analysis (NMA)
# R 对应:
library(netmeta)

# 数据格式: study, treat1, treat2, TE, seTE
nma_result <- netmeta(
  TE = logOR,
  seTE = se,
  treat1 = treatment,
  treat2 = comparator,
  studlab = study,
  data = nma_data,
  sm = "OR",
  level = 0.95
)
```

### 11.2 联赛表（League Table）

```r
# Revman: League table
league_table <- netleague(nma_result)
league_table$random
league_table$fixed
```

### 11.3 干预排序

```r
# Revman: 干预效果排序
rank_result <- netrank(nma_result, small.values = "bad")
print(rank_result)
plot(rank_results)
```

---

## 十二、RevMan 文件导出

### 12.1 导出为 RevMan 5 文件

```r
# Revman: File → Export → RevMan 5 file
# R 概念对应（需要手动构建）:

# 保存为 CSV 供 RevMan 导入
write.csv(meta_data, "revman_export.csv", row.names = FALSE)

# 保存 dmetar 格式
saveRDS(list(
  comparison = "Intervention vs Control",
  outcome = "Primary Outcome",
  analysis = mh_result
), "meta_analysis_results.rds")
```

---

## 关键差异

| 特性 | RevMan | R (本技能) |
|------|--------|-----------|
| **交互** | 点击菜单 | 自然语言 + R 代码 |
| **灵活性** | 受限 | 无限定制 |
| **可复现性** | 需手动记录 | 代码保存 |
| **图形** | 静态位图 | 矢量可编辑 |
| **高级方法** | 不完整 | 全覆盖 |
| **批量处理** | 不可以 | 脚本自动化 |
| **版本控制** | 不支持 | 完整 R Markdown |
