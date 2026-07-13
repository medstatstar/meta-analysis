# Diagnostic Test Meta-Analysis / 诊断准确性Meta分析

## phm() — Parametric Hierarchical Model / 参数层级模型

> For diagnostic test accuracy (sensitivity, specificity, DOR).

```r
library(mada)

# Data must be: study, TP, FP, FN, TN
m <- phm(
  data = df,
  precursor = "study",
  model = "ds",    # bivariate (ds) | linking (l) | index (i) | SROC (s)
  cor = FALSE      # correlation between logit(sens) and logit(spec)
)
summary(m)
plot(m)
```

### Model types / 模型类型

| Model | Function | Use |
|-------|----------|-----|
| Bivariate | `phm()` default (ds) | Summary sens & spec with correlation |
| Linking | `phm(model="l")` | Cut-off dependent accuracy |
| SROC | `rsroc()` | Summary ROC curve |
| HSROC | `hsroc()` | Hierarchical SROC (threshold + accuracy) |

### SROC curve / SROC曲线

```r
library(mada)

# Fit SROC
sroc <- rsroc(
  data = df,
  study = "study",
  sens = "sens",
  spec = "spec",
  TP = "TP", FP = "FP", FN = "FN", TN = "TN"
)

# Plot SROC with confidence region
plot(sroc)
```

---

## Data Format / 数据格式

| Required | Description |
|----------|-------------|
| study | Study identifier |
| TP | True positives |
| FP | False positives |
| FN | False negatives |
| TN | True negatives |

---

## Output Measures / 输出指标

- Sensitivity (Sens) = TP / (TP + FN)
- Specificity (Spec) = TN / (TN + FP)
- DOR (Diagnostic Odds Ratio) = (TP/FN) / (FP/TN)
- LR+ = Sens / (1-Spec)
- LR- = (1-Sens) / Spec
- AUC(SROC) = area under curve

---

## References / 引用
- Doebler P, Holling H. (2015). mada: Meta-analysis of diagnostic accuracy. R package.
- Reitsma JB, et al. (2005). Bivariate analysis of sensitivity and specificity produces informative summary measures in diagnostic reviews. *J Clin Epidemiol*, 58(10), 982-990.
- Rutter CM, Gatsonis CA. (2001). A hierarchical regression approach to meta-analysis of diagnostic test accuracy evaluations. *Stat Med*, 20(19), 2865-2884.
