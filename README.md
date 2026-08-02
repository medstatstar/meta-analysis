# meta-analysis

[🇨🇳 中文 (Chinese)](./README_zh-CN.md) | [🇺🇸 English (Current)](#)

<div align="center">
  <img src="assets/icon.svg" width="240" height="240" alt="meta-analysis logo"/>
</div>

> **Easy-to-use R-based Meta-Analysis for Clinical Researchers**
>
> You don't't need to code or memorize commands — just describe your meta-analysis needs in **plain language inside a chat**, and the skill runs the full analysis for you. Powered by R and 15+ professional R packages (metafor, meta, netmeta, gemtc, etc.), it returns results in Chinese or English depending on your OS language setting (you can force-switch via a prompt at any time). The generated R code is shown in **SAFE PREVIEW** (not executed) by default — it only computes once you confirm.

---

## 1. How to Use It in a Chat (the Core)

meta-analysis is a **conversational skill**: you simply tell the assistant what you want in natural language — no commands, no parameter names to remember. As a WorkBuddy skill it **auto-loads with no extra installation**.

Below are 6 real conversational examples ordered from simple to advanced. Each shows **"You say"** and a sketch of **"The assistant replies"**, plus how to get the actual number.

### Example 1 · Two-group binary meta (most common)
**You say:**
> Combine the OR across these 5 binary studies:
> Study A: experimental 30/100, control 20/100
> Study B: experimental 45/120, control 30/100
> ...

**Assistant replies (sketch):**
> ✅ 5 studies, random-effects (DL), OR = 1.52 (95%CI: 1.18–1.96), I² = 34%
> (Safe preview: R code shown below but not executed.)

**📌 Get the actual number:** Say **"please compute directly"** — the assistant runs R and gives the real result (see Section 4, "Safe Preview").

### Example 2 · Effect size conversion
**You say:**
> Convert Cohen's d = 0.8 to logOR

**Assistant replies (sketch):**
> ✅ d = 0.8 → logOR ≈ 1.45 (SE ≈ 0.38), based on logOR = d × π/√3

### Example 3 · Heterogeneity + subgroup
**You say:**
> I did a continuous meta with 8 studies, SMD pooled, but I² is high — I want to subgroup by region

**Assistant replies (sketch):**
> ✅ 8 studies, SMD = 0.42 (95%CI: 0.15–0.69), I² = 78%
> Subgroup by region:
> - Asia (k=4): SMD = 0.55, I² = 45%
> - Euro-US (k=4): SMD = 0.28, I² = 62%
> - Between-group Q = 4.12, p = 0.04

### Example 4 · Complex: Network meta with multiple decisions (popup menu)
**You say:**
> I want to do a network meta with 4 interventions, but I haven't decided whether to use frequentist or Bayesian, and I'm not sure if I should include dose-response

**Assistant replies (sketch):**
> 4 interventions clear. Two key choices to clarify:
>
> **① Which analysis framework?**
> - (a) Frequentist — `netmeta`, inverse-variance based, good for consistent networks
> - (b) Bayesian — `multinma` (Stan) or `gemtc` (JAGS), better for survival data / dose-response
>
> **② Include dose-response?**
> - (a) No — pure pairwise comparison network
> - (b) Yes — needs dose-effect parameters, Bayesian framework preferred
>
> **③ Can't decide?** → Say "explain the differences between these choices in detail" and the assistant explains first, then lets you decide

**📌 Note:** When you've **named the test type but are stuck on "which option / design family"**, the assistant **pops a routing menu** to confirm step by step — instead of deciding for you or dumping the full 49-test menu. The menu also offers an "explain the differences" option — when you're unsure, it explains before you decide.

### Example 5 · Vague: Not sure which model (grill-me)
**You say:**
> I want to do a meta-analysis but I'm not sure which model to use — help me figure it out

**Assistant replies (sketch):**
> Sure — let's pin down your needs first; a few key questions will locate the right model:
> 1. What type is your **primary endpoint**? — continuous (e.g. SMD) / binary (e.g. OR) / survival (HR) / single-group rate / other?
> 2. Is it a **two-group comparison or multi-group network**?
> 3. Any **special dependency structure**? — multi-arm / multi-outcome / IPD / none
>
> (After you answer, the assistant keeps probing until the model is locked, then computes — no full menu dumped on you.)

**📌 Note:** When you say "not sure which model", the assistant uses **branch-by-branch probing** to clarify your needs, instead of dumping the full menu.

### Example 6 · Systematic review workflow
**You say:**
> Help me generate a PRISMA flow diagram

**Assistant replies (sketch):**
> Sure, please provide:
> - Records identified: ___
> - Records screened: ___
> - Records excluded: ___
> - Full-text assessed: ___
> - Full-text excluded (+ reasons): ___
> - Studies included: ___
>
> User: 520, 380, 140, 80, 52(20 no data, 18 wrong pop, 14 wrong design), 28
>
> ✅ PRISMA flow diagram generated! [SVG output]

> 💡 **Tip:** Most analyses need only three things — effect size (or rate / HR) + α + power. Anything you omit is filled with sensible defaults. It's fine to be incomplete — the assistant will tell you what's missing.

---

## 2. What You Can Do — Scenario Index

Tests are grouped by **analysis purpose** (7 categories below). Each row gives the typical **clinical scenario** and a line you can **copy verbatim** under "Try saying". The same test may be reached from multiple entry points.

> The underlying R packages (metafor / meta / netmeta …) are listed in Section 5 "Advanced Reference"; ordinary users don't need to care.

### ① Pairwise Meta-Analysis
| Scenario | Try saying in chat |
|:---|:---|
| Binary (OR/RR/RD) | "Combine the OR across these 5 binary studies" |
| Continuous (SMD/MD) | "Pool the SMD of these 6 continuous studies" |
| Pre-calculated (yi+CI) | "I have effect sizes and CIs for 5 studies — draw the forest plot directly" |
| Survival (HR) | "Pool the HR across these 8 studies" |
| Correlation (r→Zr) | "Convert these 4 correlations via Fisher z then pool" |
| Single-group rate/mean | "Pool the incidence rates across these studies" |
| Generic inverse-variance | "I have yi and vi — run the meta directly" |

### ② Heterogeneity & Bias
| Scenario | Try saying in chat |
|:---|:---|
| Heterogeneity assessment | "I ran a meta, I² is very high — help me assess heterogeneity" |
| Subgroup analysis | "Run subgroup analysis by region" |
| Meta-regression | "Run meta-regression on publication year and sample size" |
| Egger test | "Check publication bias, run Egger's test" |
| Begg test | "Begg rank-correlation test" |
| Trim-and-fill | "Correct publication bias with trim-and-fill" |
| Selection model | "Assess publication bias with a selection model" |
| Sensitivity analysis | "Run leave-one-out sensitivity analysis" |
| Cumulative meta | "Run cumulative meta by publication year" |
| GOSH plot | "Plot a GOSH graph to see heterogeneity patterns" |
| Baujat diagnosis | "Make a Baujat plot to see which study contributes most heterogeneity" |
| Drapery plot | "Plot a Drapery graph to assess α robustness" |

### ③ Advanced Models
| Scenario | Try saying in chat |
|:---|:---|
| Frequentist NMA | "Run network meta with 4 interventions, use netmeta" |
| Bayesian NMA (Stan) | "Run Bayesian network meta, Stan backend" |
| Bayesian NMA (JAGS) | "Run Bayesian network meta, JAGS backend" |
| Multilevel meta | "Run 3-level meta with multiple effects within studies" |
| Multivariate meta | "Pool a meta with multiple correlated outcomes" |
| IPD meta | "I have individual patient data — run IPD meta" |
| Dose-response | "Run dose-response meta, dosresmeta" |
| Survival meta | "Pool survival data, survmeta" |
| Trial sequential analysis | "Run TSA — see how many more studies are needed" |
| Bootstrap meta | "Use Bootstrap for nonparametric DL estimation" |

### ④ Effect Size & Conversion
| Scenario | Try saying in chat |
|:---|:---|
| Mean/SD→d | "Convert mean and SD to Cohen's d" |
| t/F→d | "Convert a t value to d" |
| r→Fisher z | "Convert a correlation to Fisher z" |
| d↔logOR | "Convert d to logOR" |
| OR↔logOR | "Convert OR to logOR" |
| Batch convert | "Batch convert SMD to logOR" |
| NNT | "Calculate NNT" |

### ⑤ Visualization
| Scenario | Try saying in chat |
|:---|:---|
| Forest plot | "Draw a forest plot, lancet theme" |
| Funnel plot | "Draw a funnel plot with contour enhancement" |
| Bubble plot | "Draw a meta-regression bubble plot" |
| GOSH plot | "Plot a GOSH graph" |
| Network plot | "Draw the network meta graph" |
| League table | "Draw the NMA league table" |
| RoB traffic-light | "Draw a risk-of-bias traffic-light plot" |
| Power curve | "Draw a power curve" |
| Drapery plot | "Plot a Drapery graph" |
| Inconsistency heatmap | "Plot an NMA inconsistency heatmap" |

### ⑥ Study Quality
| Scenario | Try saying in chat |
|:---|:---|
| RoB 2.0 | "Assess risk of bias with RoB 2.0" |
| RoB 1.0 | "Assess with Cochrane RoB 1.0" |
| ROBINS-I | "Non-randomized study — use ROBINS-I" |
| GRADE | "Do a GRADE evidence-quality assessment" |
| PRISMA checklist | "PRISMA checklist" |

### ⑦ Systematic Review Workflow
| Scenario | Try saying in chat |
|:---|:---|
| PRISMA flow | "Help me generate a PRISMA flow diagram" |
| Literature screening | "Title/abstract screening, AI-assisted" |
| PDF batch download | "Batch download full texts from a DOI list (needs confirmation)" |
| Graph digitize | "Extract data from a scatter plot" |
| Missing value imputation | "Impute missing standard deviations" |

> ⚠️ **PDF batch download** connects to external networks and writes files to your local disk. Run it only on explicit user instruction, and respect copyright and access controls.

---

## 3. First-Time FAQ

**Q: I only gave effect size and study count, no other parameters — will it still compute?**
A: Yes. Most analyses need only 3 items — effect size (or rate / HR) + α + power. Omitted parts (two-sided α=0.05, 1:1 randomization, follow-up) are filled with sensible defaults; if something truly required is missing, the assistant will ask.

**Q: Is the n in the result per group or total?**
A: By default it's **per group**; paired / crossover designs report per-sequence, and survival often reports total events needed. The output always labels this clearly.

**Q: It only shows code, not the number. How do I get the actual result?**
A: Just add **"please compute directly"** or **"execute"** in the chat — the assistant will really run R and give you the number. This is the default safe design: see the code first, compute once you're sure. Execution only happens on this explicit, high-friction instruction — the skill never runs R on its own or from casual mentions of these words.

**Q: I want the reproducible R code for submission or audit — how do I ask?**
A: Say **"give me the full R code"**. The code is also shown in safe preview by default, so you can copy, modify, and re-run it yourself.

**Q: On a Chinese system, is the output in Chinese?**
A: Yes. By default the output language follows your OS language setting — Chinese on a Chinese-OS, English otherwise. This default requires no extra permission and only affects display language; you can force-switch anytime via a prompt (e.g. "用中文回复" / "switch to English").

**Q: My data is in SPSS/Excel/Stata format — what do I do?**
A: Say **"help me convert my SPSS/Excel data to CSV"** — the assistant will recommend installing `@skill:statdata-transfer` for 50+ format conversions.

---

## 4. Safe Preview

- **Default behavior:** The skill only **generates and shows the R code, but does not execute it** — you can inspect the logic first, then let it run once you're confident.
- **Trigger real computation:** In chat say **"please compute directly"** or **"execute"** → the assistant really runs R and gives the number.
- **Just see the code:** Say **"show code"** or **"preview only"** → only code, no result.
- **All computations are local** — no data is uploaded.
- **Output is for reference only** — validate before journal submission or regulatory use.

---

## 5. Advanced Reference (moved to a separate file)

CLI examples, bidirectional solving, curve mode, core formulas, system requirements, common errors, full file structure, and references for developers have been moved to **[references/ADVANCED.md](references/ADVANCED.md)**. Ordinary users don't need it; see Sections 1-4 for daily use.

---

**Version**: v1.8.0 | **License**: MIT | **Authors**: medstatstar, phoe-zip

For feature requests, bug reports, or other feedback, please contact the author directly at medstatstar@gmail.com (Wintone Zhang / 张文彤).

