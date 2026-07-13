# Survival Meta-Analysis / 生存数据Meta分析

## survmeta — Aggregate Survival Meta / 聚合生存数据合并

```r
library(survmeta)

# life-table style data
m <- survmeta(
  study = study,
  time = time,        # time intervals
  n.risk = n_at_risk, # number at risk
  n.event = n_events, # number of events
  data = df,
  conf.level = 0.95,
  method = "DL",      # DL / PM / REML / ML
  na.rm = FALSE
)

# Kaplan-Meier derived data
m <- survmeta(
  study = study,
  time = surv_time,
  n.risk = pat Risk,
  n.event = deaths,
  data = km_data,
  method = "DL"
)
```

## KM Reconstruction (pseudo-IPD) / KM曲线重建伪IPD

```r
library(ipdmeta)

# Reconstruct patient-level data from KM curves
recon <- km2ipd(
  time = km_data$time,
  surv = km_data$surv,
  n.risk = km_data$n.risk,
  n.event = km_data$n.event,
  total_n = km_data$n_total,
  arm = "treatment"
)

# Two-step approach
ipd_pool <- ipdmeta(
  ipd = reconstructed_data,
  arms = "treatment",
  studies = "study",
  status = "status",
  data = ipd_df
)
```

---

## Data Format / 数据格式

| Type | Required | Optional |
|------|----------|----------|
| Life-table | study, time, n.risk, n.event | arm |
| KM-derived | study, time, survival_prob, n.risk | events |
| HR only | study, logHR, SE | n_events, follow-up |
| IPD | patient_id, study, treatment, time, status | age, stage, etc. |

---

## References / 引用

- Zoglauer, D. et al. (2010). survmeta: R package for survival meta-analysis.
- Riley, R. D. et al. (2017). IPD meta-analysis for survival outcomes. *Stat Med*.
- Tierney, J. F. et al. (2007). Practical methods for incorporating summary time-to-event data into meta-analysis. *Trials*.
