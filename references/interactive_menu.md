# Interactive Menu Tree / 交互式引导菜单

## Menu Structure / 菜单结构

| Stage | Trigger | Action |
|-------|---------|--------|
| **Level 1** | Vague prompt (e.g., "run meta-analysis") | Show 7 main categories |
| **Level 2** | Category selected | Show sub-options + data format hints |
| **Direct** | Specific prompt (e.g., "forest plot") | Skip menu → data template → run analysis |

---

## Level 1: 7 Main Categories / 主菜单（7 类）

```
What would you like to do? / 你想做什么？

1️⃣  Pairwise Meta-Analysis / 两组Meta分析
2️⃣  Heterogeneity & Bias / 异质性与偏倚
3️⃣  Advanced Models / 高级模型
4️⃣  Effect Size & Conversion / 效应量与转换
5️⃣  Visualization / 可视化
6️⃣  Study Quality / 研究质量
7️⃣  Systematic Review Workflow / 系统评价流程
```

---

## Level 2: Full Sub-Menus / 完整子菜单

### 1. Pairwise Meta-Analysis / 两组Meta分析

```
Select outcome type / 选择结局类型:
  1. Binary (OR/RR/RD)       → study, n_exp, event_exp, n_ctrl, event_ctrl
  2. Continuous (SMD/MD)     → study, n_exp, mean_exp, sd_exp, n_ctrl, mean_ctrl, sd_ctrl
  3. Pre-calculated (yi+CI)  → study, effect_type, effect_size, lower95, upper95
  4. Survival (HR/IRR)       → study, logHR, SE | HR, lower95, upper95
  5. Correlation (r→Zr)      → study, r, n
  6. Single-group rate/mean  → study, n (or n_events), [time]
  7. Generic inverse-variance → study, yi, vi

Models / 模型: FE | RE(DL/REML/HK) | MH(binary) | Peto | GLMM | PMM
```

### 2. Heterogeneity & Bias / 异质性与偏倚

```
Select analysis / 选择分析:
  1. Heterogeneity / 异质性    → I², Q, τ², H², 95% PI | needs: yi, vi
  2. Subgroup analysis / 亚组  → rma(mods=~factor-1) | needs: yi, vi + group_var
     Groups: region | design | intervention | quality | custom
  3. Meta-regression / 元回归  → rma(yi,mods=bubble) | needs: yi, vi + covariate(s)
  4. Publication bias / 发表偏倚→ Egger | Begg | Trim-fill | Selection model | fsn
     * Weightmodel (weightr) for selection model extensions
  5. Sensitivity / 敏感性       → Leave-one-out | Cumulative | Quality/sample filter
  6. GOSH plot / 所有子集诊断   → Model fit across subsets
  7. Baujat diagnosis / Baujat → Study contribution to heterogeneity (bubble)
  8. Drapery plot / α-稳健图   → Shows significance vs α simultaneously
```

### 3. Advanced Models / 高级模型

```
Select model / 选择模型:
  1. Multi-arm NMA (netmeta)  | study, treatment, outcome, [n/mean/sd]
  2. Bayesian NMA Stan(multinma) | ML-NMR population adjustment, Weibull/Gamma/logN/PEXP survival
  3. JAGS Bayesian NMA (gemtc)| mtc.network → mtc.model → mtc.run
  4. Multilevel Meta (3-level)| study_id/effect_id nesting
  5. Multivariate Meta        | study + multiple outcomes (yi₁, yi₂, vi matrix)
     Covariance: UN | CS | HCS | AR1 | ID | DIAG
  6. IPD Meta-Analysis        | patient_id, treatment, outcome, covariates (row-per-patient)
  7. Survival Meta (survmeta) | Aggregated survival data pooling
  8. Dose-Response           | study, dose, effect_size, SE (agg) + optional IPD
     Single-stage: combine agg + IPD
  9. Trial Seq. Analysis/TSA  | Controls Type I error in interim analyses
  10. Bootstrap Meta          | Non-parametric DL alternative
  11. Cluster-Robust RVE      | robu(ρ=0.8, small=TRUE) + clubSandwich CR2
```

### 4. Effect Size & Conversion / 效应量与转换

```
Select conversion / 选择转换:
  1. Mean/SD/n → Cohen's d / Hedges' g    → esc_mean_sd() + J = 1-3/(4df-1)
  2. t-statistic → Cohen's d                 → esc_t()
  3. F-statistic (df=1) → Cohen's d          → esc_F()
  4. r → Fisher's z                          → z = 0.5·ln((1+r)/(1-r))
  5. r/d/OR/HR → SMD                         → esc::esc()
  6. Cohen's d ↔ logOR                      → logOR = d·π/√3
  7. OR/CI → logOR+SE                       → SE = (upper-lower)/(2×1.96)
  8. Batch convert (SMD↔logOR↔ZCOR)          → escalc()
  9. NNT (Number Needed to Treat)            → nnt.meta() / dmetar::NNT()
```

### 5. Visualization / 可视化

```
Select chart / 选择图表:
  1. Forest plot / 森林图     → yi, vi + study labels; themes: minimal|lancet|jama|revman|custom
  2. Funnel plot / 漏斗图     → yi, vi + contour-enhanced
  3. Bubble plot / 气泡图     → yi, vi + continuous covariate (meta-regression)
  4. GOSH plot / 子集诊断图   → yi, vi heterogeneity exploration
  5. Baujat plot / 异质诊断图 → yi, vi per-study contribution
  6. Network plot / 网络图    → NMA result (treatments geometry)
  7. League table / 联赛表    → Pairwise NMA comparison matrix
  8. RoB traffic-light / 偏倚 → Risk-of-Bias summary (RoB 1.0/2.0/ROBINS-I)
  9. Power curve / 功效曲线   → Power analysis result
  10. Drapery plot / α-稳健性 → Result stability vs significance threshold
  11. Inconsistency heatmap   → NMA global inconsistency decomposition
```

### 6. Study Quality / 研究质量

```
Select tool / 选择工具:
  1. Risk of Bias 2.0 / RoB 2.0   → 5 domains: randomization, deviations, missing, measurement, selection
  2. RoB 1.0 (Cochrane)           → Sequence, allocation, blinding, incomplete, selective
  3. ROBINS-I                     → Non-randomized studies (bias due to confounding, selection, etc.)
  4. GRADE / 证据质量             → High | Moderate | Low | Very Low
  5. PRISMA Checklist / 报告规范  → 27-item checklist for systematic reviews
  6. AMSTAR-2                     → Appraisal of systematic reviews
```

### 7. Systematic Review Workflow / 系统评价流程

> For full methods, see `references/review_workflow.md`.
> 完整方法见 `references/review_workflow.md`。

```
Select tool / 选择工具:
  1. PRISMA flow diagram / PRISMA流程图 → Auto-generate flow diagram from screening counts
  2. Literature screening GUI / 文献筛选   → Title/Abstract screen with AI assistance
  3. PDF batch download / 批量下载         → Retrieve full-text PDFs from DOI/PMID lists
  4. Graph digitize / 图形数字化             → Extract numeric data from scatter/bar plots
  5. Missing value imputation / 缺失值插补   → Multiple imputation for unreported statistics
  6. Reference management / 文献管理         → BibTeX/EndNote export
```

---

## Data Format Quick Reference / 数据格式速查

| Scenario | Required Columns | Optional |
|----------|-----------------|----------|
| Binary / 二分类 | `study, n_exp, event_exp, n_ctrl, event_ctrl` | year, group, quality |
| Continuous / 连续型 | `study, n_exp, mean_exp, sd_exp, n_ctrl, mean_ctrl, sd_ctrl` | year, group, quality |
| Generic yi+vi | `study, effect_type, effect_size, lower95, upper95` | year, group, quality |
| Survival HR | `study, logHR, SE` or `study, HR, lower95, upper95` | year, n_events |
| Correlation | `study, r, n` | year, group |
| Single-group rate | `study, n_events, n_total` | time_at_risk, year |
| Single-group mean | `study, n, mean, sd` | year, group |
| Multi-arm | `study, treatment, [outcome_cols]` | dose, duration |
| NMA (binary) | `study, treatment, n, events` | dose, duration |
| NMA (continuous) | `study, treatment, n, mean, sd` | dose, duration |
| IPD | `patient_id, study, treatment, outcome, covariates` | age, sex, stage |
| Dose-response | `study, dose, effect_size, SE` | n_at_dose, n_total |
| Multilevel | `study_id, effect_id, yi, vi` | outcome_type, time_point |
| Multivariate | `study, yi_1, yi_2, [,vi_matrix]` | outcome_labels |

---

## Dialogue Examples / 对话示例

### Example 1: Single-Group Meta
```
User: 我有几个研究的发病率，想合并
LLM: Got it! What type of single-group data?
     1. Rate/proportion (events/total)  2. Mean ± SD  3. Incidence rate (person-time)
     4. Correlation coefficient

User: 1
LLM: Preparation:
     Required: study, events, total_n
     [Paste data]

User: [data]
LLM: ✅ 8 studies, random-effects (DL) with logit transform.
     Pooled rate: 12.3% (95%CI: 8.5-17.2%), I²=72%
     [Forest plot + funnel plot]
```

### Example 2: Bayesian NMA
```
User: 我想做个贝叶斯NMA，比较有5种药的生存数据
LLM: Understood. Bayesian NMA with survival outcomes.
     1. Stan backend (multinma) - recommended for PH and non-PH
     2. JAGS backend (gemtc) - classic approach

User: 1
LLM: What survival distribution?
     1. Weibull  2. Gamma  3. Log-normal  4. Log-logistic
     5. Generalized Gamma  6. Mixture of splines

User: 1, and I have time-to-event per arm
LLM: Data format: study, treatment, n_events, either:
     - Follow-up time per arm (survival → Weibull)
     - HR + 95%CI per arm

User: [data uploaded]
LLM: ✅ Running... Stan MCMC (4 chains, 4000 iter)... Results below [NMA plot + league + rank]
```

### Example 3: TSA
```
User: 我想看下Meta分析需不需要更多研究
LLM: Trial Sequential Analysis (TSA) - monitors Type I error.
     Required: yi + vi (from your pooling), expected effect size, α, power

User: My pooled SMD=0.35, want α=0.05, power=0.80
LLM: ✅ TSA result:
     - Z-curve crossed monitoring boundary
     - Required information size: 352 (current: 280)
     - Conclusion: Borderline — may need ~2 more studies
     [TSA plot]
```

### Example 4: Systematic Review Workflow
```
User: 帮我生成PRISMA流程图
LLM: Sure, please provide:
     - Records identified: ___
     - Records screened: ___
     - Records excluded: ___
     - Full-text assessed: ___
     - Full-text excluded (+ reasons): ___
     - Studies included: ___

User: 520, 380, 140, 80, 52(20 no data, 18 wrong pop, 14 wrong design), 28
LLM: ✅ PRISMA flow diagram generated! [SVG output]
```
