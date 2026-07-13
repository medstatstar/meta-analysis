# Single-Group Meta-Analysis / 单组率均值Meta分析

> One group, no control. Common in epidemiology, prevalence studies, and diagnostic cohorts.

## metaprop — Proportion Meta / 单组率合并

```r
library(meta)

# proportion meta with logit transformation
m <- metaprop(
  event = events,    # number of events
  n = total_n,       # total sample size
  studlab = study,
  data = df,
  sm = "PLOGIT",      # PLOGIT / PRAW / PASF (Freeman-Tukey double-arcsine)
  method = "DL",     # DL / SJ (Sidik-Jonkman) / ML / REML
  prediction = TRUE
)
```

| Transformation | When |
|---------------|------|
| `PLOGIT` (default) | Most proportions, avoids [0,1] boundary bias |
| `PRAW` | Large samples (n>30), proportions 30%-70% |
| `PASF` (Freeman-Tukey) | Very small or very large proportions, stabilizes variance |
| `PFT` (generalizable Freeman-Tukey) | Combines benefits |

## metamean — Single Mean Meta / 单组均值合并

```r
m <- metamean(
  n = n,
  mean = mean,
  sd = sd,
  studlab = study,
  data = df,
  sm = "SMD",        # SMD (Hedges' g within) or MD
  method = "DL",
  random = TRUE
)
```

## metainc — Incidence Rate Meta / 发病率合并（人时）

```r
m <- metainc(
  event = events,
  time = person_time,  # person-years or person-months
  studlab = study,
  data = df,
  sm = "IRLN",         # IRLN (log) | IR | IRS | IRFT (Freeman-Tukey)
  method = "DL",
  level = 0.95
)
```

## metarate — Event Rate (with person-time) / 事件发生率

```r
m <- metarate(
  event = events,
  time = time_at_risk,
  studlab = study,
  data = df,
  sm = "IRLN"
)
```

## metacor — Correlation Meta / 相关系数合并

```r
library(metacor)
m <- metacor(
  ri = r,         # correlation coefficient
  ni = n,         # sample size
  data = df,
  sm = "ZCOR"     # Fisher's z transformation (default)
)
```

## NNT Meta / 需治疗数合并

### NNT from single study
```r
library(dmetar)
# Furukawa's NNT (accounts for baseline risk)
NNT(res, sm = "RR", baseline = 0.3)
# where res is rma output
```

### NNT from network meta (multinma / gemtc)
```r
library(multinma)
# NNT from NMA relative effects
nma_nnt(nma_fit, baseline_risk = 0.3, comparison = "treatment")
```

### Traditional NNT
```r
NNT = 1 / (p_control * (1 - RR))
# or for RD:
NNT = 1 / abs(RD)
```

## Data Format / 数据格式

| Type | Required | Optional |
|------|----------|----------|
| Proportion | `study, events, total_n` | time, year, subgroup |
| Mean | `study, n, mean, sd` | year, subgroup |
| Incidence | `study, events, person_time` | year, subgroup |
| Correlation | `study, r, n` | year, subgroup |

## References
- Schwarzer G, et al. (2015). meta R package. https://cran.r-project.org/package=meta
- IntHout J, et al. (2014). The arcsine difference is the preferred method. *Res Synth Methods*, 5(4), 360-369.
