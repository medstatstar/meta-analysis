# Bayesian NMA (Network Meta-Analysis) / 贝叶斯网状Meta分析

> two major backends: **multinma (Stan)** and **gemtc (JAGS)**. Both handle consistency/inconsistency modeling.

---

## multinma — Stan Backend (NICE Preferred) / Stan后端

```r
library(multinma)

# Prepare data
prep <- treatment_class(treatment ~ study, data = nma_data)

# Prior specification
priors <- prior_normal(0, 2, parameter = "d") +  # treatment effect
          prior_halfnormal(0.5, parameter = "sd")   # heterogeneity

# Model fit
fit <- nma(
  prep,
  response = "events",
  n = "n",
  study = "study",
  treatment = "treatment",
  priors = priors,
  distribution = "binomial",
  prior = priors,
  chains = 4,
  iter = 4000,
  seed = 123
)

# Diagnostics
plot(fit)  # traceplots
summary(fit)
```

### Survival NMA (non-PH) / 生存数据NMA（非比例风险）

```r
fit_surv <- nma(
  prep,
  response = "time",
  n = "n",
  study = "study",
  treatment = "treatment",
  survival = "weibull",   # weibull | gamma | lognormal | loglogistic | gengamma |pexp
  prior = priors,
  chains = 4,
  iter = 6000
)

# Plot survival curves
plot(fit_surv, outcome = "survival")
```

### ML-NMR Population Adjustment / 人群校正

```r
fit_mlnmr <- nlme_nma(
  prep,
  response = "events",
  n = "n",
  study = "study",
  treatment = "treatment",
  mlnmr = TRUE,
  effect = "treatment:covariate",  # treatment-covariate interaction
  priors = priors,
  chains = 4,
  iter = 4000
)
```

---

## gemtc — JAGS Backend / JAGS后端

```r
library(gemtc)

# Build network
net <- mtc.network(
  data.ab = nma_data,   # arm-level data
  treatments = treatment_levels,
  studies = study_levels
)

# Define model
model <- mtc.model(
  network = net,
  type = "consistency",    # consistency | inconsistency | regression
  link = "logit",          # logit | cloglog | identity | tdistribution
  likelihood = "binomial", # binomial | normal | poisson | clnegativebin | surivival
  linearModel = "random",  # random | fixed
  om.scale = 2.5,
  dic = TRUE
)

# MCMC run
results <- mtc.run(
  model,
  n.adapt = 5000,
  n.iter = 50000,
  thin = 10
)

# Diagnostics
plot(results)
 Gelman.diag(results)
 summary(results)

# Node-split for consistency
ns <- nodesplit(net, model, results)
summary(ns)
plot(ns)
```

---

## Network Comparison / 网络结果

### League table (both packages)
```r
# multinma
league <- league_table(fit)
print(league, digits = 2)

# gemtc
league <- relative.effect(results, t1 = "placebo")
```

### SUCRA / P-scores / 排序
```r
# multinma
rank(fit, "SUCRA")
# P-scores: rank(fit, "P-score")

# gemtc
rank.probability(results, preferredDirection = -1)
```

---

## Diagnostics / 诊断

| Check | multinma | gemtc |
|-------|----------|-------|
| Convergence | R-hat, n_eff, traceplots | Gelman.digraph, traceplots |
| Inconsistency | `devdev()` node-splitting | `nodesplit()` |
| Model fit | LOOIC, WAIC | DIC |
| Funnel | `ggplot(study-specific)` | `comparison-adjusted funnel` |

---

## Data Formats / 数据格式

| Type | Required | Example |
|------|----------|---------|
| Binary arm-level | study, treatment, n, events | study A, DrugX, 100, 25 |
| Continuous arm-level | study, treatment, n, mean, sd | study A, DrugX, 50, 12.3, 2.1 |
| Survival arm-level | study, treatment, n, time, status | study A, DrugX, 80, 12.5, 1 |
| Contrast-level (change) | study, treatment, mean_diff, se, n | study A, DrugX vs PBO, 2.1, 0.5, 50 |

---

## References / 引用

- What works best depends on research question: multinma offers population adjustment; gemtc is the classic frequentist-Bayesian bridge
- multinma:抗老,



继续创建其他引用文件。
</longcat_think>
