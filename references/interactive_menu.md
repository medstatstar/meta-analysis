# Interactive Menu Tree / 交互式引导菜单

## Menu Design Rules / 菜单设计规则

| Stage | Trigger | Action |
|-------|---------|--------|
| **Level 1** | User prompt is vague (e.g., "run meta-analysis") | Show 6 main categories |
| **Level 2** | User picks a category | Show sub-options with data format hints |
| **Direct** | User gives specific request (e.g., "forest plot") | Skip menu, show data template, run analysis |

---

## Level 1: Main Categories / 主菜单

```
What would you like to do? / 你想做什么？

1️⃣  Pairwise Meta-Analysis / 两组Meta分析
2️⃣  Heterogeneity & Bias / 异质性与偏倚
3️⃣  Advanced Models / 高级模型
4️⃣  Effect Size & Conversion / 效应量与转换
5️⃣  Visualization / 可视化
6️⃣  Study Quality / 研究质量
```

---

## Level 2: Sub-Menus / 子菜单

### 1. Pairwise Meta-Analysis / 两组Meta分析

```
Select outcome type / 选择结局类型:
  1. Binary (OR/RR/RD)     → Data: study, n_exp, event_exp, n_ctrl, event_ctrl
  2. Continuous (SMD/MD)   → Data: study, n_exp, mean_exp, sd_exp, n_ctrl, mean_ctrl, sd_ctrl
  3. Pre-calculated (yi+95%CI) → Data: study, effect_type, effect_size, lower95, upper95
  4. Survival (HR/IRR)      → Data: study, logHR, SE or HR + 95%CI
  5. Correlation (r→Zr)     → Data: study, r, n

Model options:
  - Fixed-effect / 固定效应 (FE)
  - Random-effects / 随机效应 (DL / REML / HK)
  - Mantel-Haenszel / MH (binary sparse data)
  - Peto method (rare events)
```

### 2. Heterogeneity & Bias / 异质性与偏倚

```
Select analysis / 选择分析:
  1. Heterogeneity test       → I², Q, tau², H², 95% PI
  2. Subgroup analysis        → Needs: study + yi + vi + group_var
     Group by: region | design | intervention_type | quality_level | custom
  3. Meta-regression          → Needs: study + yi + vi + covariate(s)
     Covariate: year | dose | sample_size | quality_score | continuous
  4. Publication bias         → Egger | Begg | Trim-fill | Selection model
     Needs: yi + vi from pooling
  5. Sensitivity              → Leave-one-out | Cumulative | Quality filter
     Needs: yi + vi from pooling
  6. GOSH plot               → All-subsets model diagnosis
```

### 3. Advanced Models / 高级模型

```
Select model / 选择模型:
  1. Network Meta (NMA)      → Needs: multi-arm data with treatment labels
     Required: study, outcome, treatment, n/events or mean/SD
  2. Bayesian Meta            → Needs: yi + vi (from pairwise pooling)
     Prior: half-normal(0,1) for τ | user-specified
  3. Multilevel Meta          → Needs: study_id + effect_id (nested structure)
  4. Multivariate Meta        → Needs: study + multiple effect sizes (yi₁, yi₂, ...)
     Covariance struct: UN | CS | HCS | AR1 | ID | DIAG
  5. IPD Meta-Analysis       → Needs: individual patient data (row-per-patient)
  6. Dose-Response           → Needs: study + dose_level + effect_size
```

### 4. Effect Size & Conversion / 效应量与转换

```
Select conversion / 选择转换:
  1. From raw data            → Mean/SD/n → d | t-stat → d | F-stat → d | r → Zr
  2. d ↔ Hedges' g           → J = 1 − 3/(4df − 1)
  3. d ↔ logOR               → logOR = d·π/√3
  4. r ↔ Fisher's z          → z = 0.5·ln((1+r)/(1−r))
  5. OR ↔ logOR + SE        → SE = (upper95 − lower95)/(2×1.96)
  6. Batch (SMD↔logOR↔Zr)   → auto via escalc()
```

### 5. Visualization / 可视化

```
Select chart / 选择图表:
  1. Forest plot / 森林图     → yi + vi + study labels
     Themes: minimal | lancet | jama | revman | custom
  2. Funnel plot / 漏斗图     → yi + vi (asymmetry check)
  3. Bubble plot / 气泡图     → yi + vi + continuous covariate (meta-reg)
  4. GOSH plot                → yi + vi (model diagnosis)
  5. Network plot / 网络图    → NMA result (network geometry)
  6. League table / 联赛表    → NMA pairwise comparisons
  7. RoB traffic-light       → Risk-of-Bias summary
  8. Power curve / 功效曲线   → Power analysis result
```

### 6. Study Quality / 研究质量

```
Select tool / 选择工具:
  1. Risk of Bias (RoB 2.0)  → 5 domains: randomization, deviations, missing, measurement, selection
  2. RoB 1.0 (Cochrane)      → Sequence generation, allocation, blinding, incomplete, selective
  3. ROBINS-I                 → Non-randomized studies
  4. GRADE Assessment        → Evidence quality (high/moderate/low/very low)
  5. PRISMA Checklist        → Reporting checklist
```

---

## Data Format Quick Reference / 数据格式速查

| Scenario | Required Columns | Optional |
|----------|-----------------|----------|
| Binary | `study, n_exp, event_exp, n_ctrl, event_ctrl` | year, group, quality |
| Continuous | `study, n_exp, mean_exp, sd_exp, n_ctrl, mean_ctrl, sd_ctrl` | year, group, quality |
| Generic | `study, effect_type, effect_size, lower95, upper95` | year, group, quality |
| Survival | `study, logHR, SE` or `study, HR, lower95, upper95` | — |
| Correlation | `study, r, n` | — |
| Multi-arm | `study, treatment, [outcome cols]` | dose, duration |
| NMA | `study, treatment, n, events` (binary) or `study, treatment, n, mean, sd` (continuous) | — |
| IPD | One row per patient: `patient_id, study, treatment, outcome, covariates` | — |
| Multilevel | `study_id, effect_id, yi, vi` | outcome_type, time_point |
| Multivariate | `study, yi_1, yi_2, [vi matrix or cov]` | outcome_labels |
| Dose-response | `study, dose, effect_size, SE` | n_at_dose |

---

## Interactive Dialogue Examples / 对话示例

### Example 1: Vague Prompt → Menu → Analysis
```
User: 帮我做个Meta分析
LLM: Sure! What type of outcome do you have?
     1️⃣ Binary (events + n)   2️⃣ Continuous (mean±SD+n)
     3️⃣ Pre-calculated (yi+CI)  4️⃣ Upload data file

User: 1
LLM: Great! Do you have the data ready?
     Please prepare: study, n_exp, event_exp, n_ctrl, event_ctrl
     [Paste data] or [Show example] or [Upload file]

User: [pastes data]
LLM: ✅ 5 studies detected. Pooling with random-effects (REML)...
     [Runs analysis → shows forest plot + results]
```

### Example 2: Specific Prompt → Direct Analysis
```
User: 用这些数据画森林图，二分类...
LLM: ✅ Binary outcome detected (5 studies).
     Running random-effects model (REML)...
     [Directly shows R code + forest plot]
```

### Example 3: Multi-Stage Expansion
```
User: 我想做亚组分析和元回归
LLM: [Shows Level 2 menu for #2 Heterogeneity & Bias]
     1. Subgroup analysis (needs: yi + vi + group_var)
     2. Meta-regression (needs: yi + vi + covariate)
     Both need data from pairwise pooling first.
     Do you have your data ready?
```
