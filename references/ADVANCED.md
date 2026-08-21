# Advanced Reference / 进阶参考

> This file is for **developers and advanced users**. Ordinary users only need the [How to Use in a Chat](interactive_menu.md) section.
>
> 本文件面向**开发者与普通用户**。普通用户只需阅读[对话使用指南](interactive_menu.md)即可。

---

## 1. CLI Invocation Examples / CLI 调用示例

### Meta-analysis via Coze workflow (R engine lives there)
```bash
# From the skill side: self-test connectivity to the coze endpoint
python adapters/coze_client.py

# Inside the coze project: inspect/review required R packages
Rscript src/r_engine/setup_packages.R

# Inside the coze project: run the dispatcher directly (task routed by JSON input)
Rscript src/r_engine/run_task.R --input input.json --output output.json
```

### Direct R invocation
```r
library(metafor)
# Binary meta
res <- metabin(event.e, n.e, event.c, n.c, sm="OR", method="DL", data=my_data)
forest(res)
funnel(res)
```

---

## 2. Bidirectional Solving / 双向求解模式

When users only have partial information, the skill can solve bidirectionally:

| Given | Solve for |
|---|---|
| n, power, α, effect size → | verify power |
| power, α, effect size, n → | verify n |
| Observed I², k, n → | evaluate heterogeneity level |

---

## 3. Curve Mode /  Curve 模式

- **Power curve**: effect size → power at varying α
- **Heterogeneity curve**: I² vs. exclusion of each study (leave-one-out)
- **NMA rank curve**: distribution of each treatment's rank probability

---

## 4. Core Formulas / 核心公式推导

### 4.1 Random-effects model (DL)
```
θ̂_DL = Σ(w_i · θ_i) / Σ(w_i)
w_i = 1 / (v_i + τ̂²)
τ̂² = (Q - (k-1)) / (Σw_i - Σw_i²/Σw_i)
```

### 4.2 Effect size conversions
```
Cohen's d → logOR: logOR = d × π / √3
d → Hedges' g: g = J × d, J = 1 - 3/(4df - 1)
r → Fisher's z: z = 0.5 · ln((1+r)/(1-r))
OR → logOR: logOR = ln(OR), SE = (ln(upper) - ln(lower)) / (2 × 1.96)
```

### 4.3 Heterogeneity
```
I² = 100% × (Q - df) / Q
H² = Q / df
τ² = (Q - (k-1)) / (Σw_i - Σw_i²/Σw_i)  [DL estimator]
```

### 4.4 Bayesian NMA (Stan)
```
y_i ~ Normal(θ_i, σ_i²)
θ_i = μ + τ · η_i
η_i ~ Normal(0, 1)
```

---

## 5. System & Environment Requirements / 系统与环境要求

### R packages (mandatory)
| Package | Version | Purpose |
|---|---|---|
| metafor | ≥3.0 | Core meta-analysis (rma, escalc, forest, funnel) |
| meta | ≥5.0 | Metabin, metacont, metaprop, etc. |
| netmeta | ≥2.0 | Frequentist NMA |
| bayesmeta | ≥3.0 | Bayesian pairwise meta |
| multinma | ≥0.8 | Bayesian NMA (Stan, 可选后端) |
| gemtc | ≥2.0 | Bayesian NMA (JAGS) |
| esc | ≥0.5 | Effect size conversions |
| clubSandwich | ≥0.5 | CR2 robust SE |
| robumeta | ≥2.0 | RVE for dependent effects |
| dosresmeta | ≥2.0 | Dose-response meta |
| ~~survmeta~~ | — | 已下架，改用 metafor 逆方差合并 logHR |
| mada | ≥1.0 | Diagnostic meta |
| metagear | ≥1.0 | Systematic review workflow |
| ggplot2 | ≥3.0 | Visualization |
| gridExtra | ≥2.0 | Multi-panel plots |
| forestploter | ≥1.1 | Publication-ready forest plots (替代 ggforestplot) |
| svglite | ≥2.0 | Editable SVG export |

### Python (helper only)
- Python 3.10+ with **no third-party packages** (stdlib only)
- Anaconda recommended: `C:\Tools\anaconda3\python.exe`

### Operating System
- Windows 10/11 (primary), macOS, Linux
- 8GB+ RAM recommended for large NMA models (Stan/JAGS)

---

## 6. Common Errors & Troubleshooting / 常见错误排查

| Error | Cause | Fix |
|---|---|---|
| `R package not found` | Missing R package | `install.packages("pkg")` |
| `Stan model compilation failed` | C++ toolchain missing | Install Rtools (Windows) or Xcode (macOS) |
| `MCMC did not converge` | Too few iterations or poor chain mixing | Increase `iter`, check `Rhat > 1.01` |
| `I² = 0%` but visible heterogeneity | Low power to detect heterogeneity | Use Q-test p-value, consider random-effects regardless |
| `Funnel plot asymmetry` | True publication bias or heterogeneity | Use Egger test, consider selection models |
| `netmeta inconsistency` | Violated transitivity assumption | Check node-split, consider meta-regression |
| `svglite output is raster` | Cairo not installed | Install Cairo R package |
| `UnicodeDecodeError` in R output | Non-UTF-8 characters | Use `cp1252` or `utf-8 + errors='replace'` |

---

## 7. Full File Structure / 完整文件结构

```
meta-analysis/
├── SKILL.md                       # Main skill definition (English body, ct-base aligned)
├── AGENTS.md                      # Self-improvement + agent rules (English)
├── CHANGELOG.md                   # Version / fix log
├── README.md                      # English user guide (top switch to README_zh-CN.md)
├── README_zh-CN.md                # Chinese user guide (top switch to README.md)
├── LICENSE                        # MIT
├── requirements.txt               # R package list
├── assets/
│   ├── icon.svg                   # Skill logo
│   └── icon.png                   # Bitmap version
├── scripts/
│   ├── i18n.py                    # ct-base shared: bilingual helper
│   └── generate_topic_report.py  # Topic-selection report generator (pure Python)
├── adapters/
│   ├── coze_client.py             # Coze workflow outbound client (envelope + parse)
│   └── README.md                  # Adapter docs
├── references/
│   ├── (R engine lives in the coze project: src/r_engine/ — see coze_contract.md)
│   ├── interactive_menu.md        # How to use in a chat (user-friendly guide)
│   ├── ADVANCED.md                # This file (developer reference)
│   ├── ADVANCED_zh-CN.md          # Chinese developer reference
│   ├── language_policy.md         # Bilingual policy (from ct-base)
│   ├── report_template.md         # Report skeleton (from ct-base)
│   ├── units.md                   # Atomic task unit index
│   ├── data_templates.md          # Per-type CSV templates + validation
│   ├── revman_complete.md         # RevMan → R 1:1 code mapping
│   ├── stata_to_r_mapping.md      # Stata metareg/mvmeta → R equivalents
│   ├── advanced_analysis.md       # Multilevel/IPD/Bayesian/Dose-Resp/Power
│   ├── single_group_meta.md       # metaprop/metamean/metainc/metacor
│   ├── survival_meta.md           # metafor + KM pseudo-IPD
│   ├── tsa_diagnostics.md         # TSA + Baujat + Drapery + selection
│   ├── diagnosis_meta.md          # mada bivariate + SROC
│   ├── bayesian_nma.md            # gemtc (主) / multinma (可选) workflows
│   ├── esc_robust_meta.md         # esc conversions + RVE
│   ├── review_workflow.md         # metagear PRISMA / screening / digitize
│   ├── r_packages.md              # Package inventory
│   ├── citations.md               # Methodological references
│   ├── references.md              # Reference list
│   ├── advanced_api.md            # Reusable API reference
│   ├── svg_editing.md             # SVG editing tools & journal format conversion
│   └── purpose_zh.md              # Chinese Purpose text mirror
```

---

## 8. References / 方法论参考文献

### Core texts
- Harrer M, Cuijpers P, Furukawa TA, Ebert DD. (2021). *Doing Meta-Analysis with R: A Hands-On Guide*. CRC Press.
- Viechtbauer W. (2010). Conducting meta-analyses in R with the metafor package. *J Stat Softw*, 36(3), 1–48.
- Balduzzi S, Rücker G, Schwarzer G. (2019). How to perform a meta-analysis with R: a practical tutorial. *Evid Based Ment Health*, 22(4), 153–160.
- Rücker G, et al. (2016). netmeta: Network Meta-Analysis using Frequentist Methods. *BMC Med Res Methodol*, 16, 1–8.
- Salanti G. (2012). Network meta-analysis in mental health. *Evid Based Ment Health*, 15(1), 16–20.

### R package citations
- metafor: `citation("metafor")`
- meta: `citation("meta")`
- netmeta: `citation("netmeta")`
- gemtc: `citation("gemtc")`
- multinma: `citation("multinma")`
- bayesmeta: `citation("bayesmeta")`
- esc: `citation("esc")`
- clubSandwich: `citation("clubSandwich")`
- robumeta: `citation("robumeta")`
- dosresmeta: `citation("dosresmeta")`
- survmeta: `citation("survmeta")`
- mada: `citation("mada")`
- metagear: `citation("metagear")`

---

**Version**: v1.7 | **License**: MIT | **Authors**: medstatstar, phoe-zip
