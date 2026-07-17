# Survival Meta-Analysis / 生存数据Meta分析

## run_surv_meta() — Combine Survival Effects (logHR) / 合并生存效应量（logHR）

> ⚠️ **环境限制**：`survmeta` 在本沙盒的 R 4.5.1 上无二进制/源码可装（CRAN 无对应版本），
> 因此封装 `run_surv_meta()` 仅做**语法校验 + 友好提示**，需在**本机**安装 survmeta 后运行。
> 安装后请以本机 `?survmeta::survmeta` 的实际签名为准。
>
> 📌 **最稳妥的生存 Meta 做法**：把各研究的 **logHR 与其方差** 提取出来，直接用通用
> 逆方差法（`metafor::rma` / `meta::metagen`）合并 —— 这也是绝大多数系统评价的标准路径，
> 无需依赖 survmeta。

```r
source("scripts/advanced_functions.R")

# 数据：每研究一行，loghr=log(HR)，v=logHR 的方差（= (log上限-log下限)/(2*1.96) 的平方）
sm <- run_surv_meta(
  yi = "loghr", vi = "v", studlab = "study", data = hr_df,
  method = "REML"      # DL / PM / REML / ML
)

# ---- 通用替代（推荐，无需 survmeta）：逆方差合并 logHR ----
library(meta)
mg <- metagen(TE = loghr, seTE = sqrt(v), studlab = study, data = hr_df,
              sm = "HR", method.tau = "REML")
summary(mg)          # 输出即为合并 HR 及 95%CI
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
