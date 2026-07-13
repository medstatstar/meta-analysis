# TSA & Model Diagnostics / 诊断序贯分析与模型诊断

## tes() — Trial Sequential Analysis / 序贯分析

> Controls type I error in cumulative meta-analysis (like interim monitoring).

```r
library(metafor)

# 1. Run rma first
res <- rma(yi = yi, vi = vi, method="DL", data=df)

# 2. TSA calculation
tsa <- tes(
  res,
  sd = sd,           # standard deviation of observed effects
  k = 2,             # groups (2 = binary comparison)
  alpha = 0.05,
  power = 0.8,
  d = 0.2,           # minimal clinically important difference (SMD)
  outcome = "survival"   # timing
)

# 3. Results
summary(tsa)

# 4. TSA plot
plot(tsa)   # Z-curve with monitoring boundaries
```

### TSA interpretation / 解读
- Z-curve crosses monitoring boundary → firm efficacy (no more studies needed)
- Z-curve crosses futility boundary → ineffective
- Required Information Size (RIS) > accrued → more studies needed
- RIS = externally defined "trial size"

---

## baujat() — Heterogeneity Source / 异质性来源诊断

```r
b <- baujat(res)
print(b)
plot(b)
```

### Interpretation / 解读
- X-axis: contribution to overall heterogeneity (Q_i)
- Y-axis: influence on overall result (overall estimate change when removed)
- Studies in upper-right → high contribution + high influence → check these studies

---

## drapery() — α-Percept Drapery / α-稳健性图

```r
library(meta)
drapery(res, type = "zvalue", print = TRUE)
```

### Interpretation / 解读
- Shows how significance (z-value) changes for varying α levels simultaneously
- More robust than single-α forest plot (avoids α-cutoff dichotomy)

---

## bootmeta() — Bootstrap Meta / Bootstrap重抽样

```r
library(bootmeta)

# Non-parametric bootstrap (DL alternative with small samples)
bm <- bootmeta(res, B = 1000, worker = 4)
plot(bm)
```

- Confidence intervals via percentile bootstrap
- More robust than REML when k<10

---

## Selection Model Extensions / 选择模型扩展

```r
library(weightr)

# Weight-function model for publication bias
wt <- weightfunct(
  effect = df$yi,
  v = df$vi,
  steps = c(0.005, 0.01, 0.05, 0.1, 0.25, 0.35, 0.5, 1)
)
summary(wt)
plot(wt)
```

### Interpretation / 解读
- p-value distribution is asymmetric → publication bias
- Can adjust pooled estimate for publication bias

---

## References / 引用
- Wetterslev J, et al. (2008). Trial sequential analysis may establish when firm evidence is reached in cumulative meta-analysis. *J Clin Epidemiol*, 58(1), 6-13.
- Baujat B, et al. (2002). A graphical method for exploring heterogeneity in meta-analyses. *Stat Med*, 21(22), 2641-2652.
- Higgins JPT, Spiegelhalter DJ. (2002). Being sceptical about meta-analyses: a Bayesian perspective on triangular trials. *Stat Med*, 21(3), 417-437.
- Bootmeta CRAN package
