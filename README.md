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
> 合并以下 5 项二分类研究的 OR：
> 研究A: 实验组 30/100, 对照组 20/100
> 研究B: 实验组 45/120, 对照组 30/100
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
| Binary (OR/RR/RD) | "合并这 5 项二分类研究的 OR" |
| Continuous (SMD/MD) | "合并 6 项连续型研究的 SMD" |
| Pre-calculated (yi+CI) | "我有 5 个研究的效应量和 CI，直接画森林图" |
| Survival (HR) | "合并 8 项研究的 HR" |
| Correlation (r→Zr) | "把这 4 个相关系数做 Fisher z 转换后合并" |
| Single-group rate/mean | "合并这几个研究的发病率" |
| Generic inverse-variance | "我有 yi 和 vi，直接做 Meta" |

### ② Heterogeneity & Bias
| Scenario | Try saying in chat |
|:---|:---|
| Heterogeneity assessment | "我做了 Meta，I² 很高，帮我看下异质性" |
| Subgroup analysis | "按地区做亚组分析" |
| Meta-regression | "做元回归，看发表年份和样本量的影响" |
| Egger test | "检查发表偏倚，做 Egger 检验" |
| Begg test | "Begg 秩相关检验" |
| Trim-and-fill | "用剪补法校正发表偏倚" |
| Selection model | "用 selection model 评估发表偏倚" |
| Sensitivity analysis | "做 leave-one-out 敏感性分析" |
| Cumulative meta | "按发表年份做累积 Meta" |
| GOSH plot | "画 GOSH 图看异质性模式" |
| Baujat diagnosis | "做 Baujat 图，看哪个研究贡献最大异质性" |
| Drapery plot | "画 Drapery 图评估 α 稳健性" |

### ③ Advanced Models
| Scenario | Try saying in chat |
|:---|:---|
| Frequentist NMA | "做网络 Meta，4 种干预，用 netmeta" |
| Bayesian NMA (Stan) | "做贝叶斯网络 Meta，Stan 后端" |
| Bayesian NMA (JAGS) | "做贝叶斯网络 Meta，JAGS 后端" |
| Multilevel meta | "做 3 水平 Meta，研究内多个效应" |
| Multivariate meta | "合并多个相关结局的 Meta" |
| IPD meta | "我有患者个体数据，做 IPD Meta" |
| Dose-response | "做剂量反应 Meta，dosresmeta" |
| Survival meta | "合并生存数据，survmeta" |
| Trial sequential analysis | "做 TSA，看还需要多少研究" |
| Bootstrap meta | "用 Bootstrap 做非参数 DL 估计" |

### ④ Effect Size & Conversion
| Scenario | Try saying in chat |
|:---|:---|
| Mean/SD→d | "把均值标准差转成 Cohen's d" |
| t/F→d | "把 t 值转成 d" |
| r→Fisher z | "把相关系数转成 Fisher z" |
| d↔logOR | "把 d 转成 logOR" |
| OR↔logOR | "把 OR 转成 logOR" |
| Batch convert | "批量把 SMD 转成 logOR" |
| NNT | "计算 NNT" |

### ⑤ Visualization
| Scenario | Try saying in chat |
|:---|:---|
| Forest plot | "画森林图，lancet 主题" |
| Funnel plot | "画漏斗图，带轮廓增强" |
| Bubble plot | "画元回归气泡图" |
| GOSH plot | "画 GOSH 图" |
| Network plot | "画网络 Meta 的网络图" |
| League table | "画 NMA 联赛表" |
| RoB traffic-light | "画偏倚风险交通灯图" |
| Power curve | "画功效曲线" |
| Drapery plot | "画 Drapery 图" |
| Inconsistency heatmap | "画 NMA 不一致性热图" |

### ⑥ Study Quality
| Scenario | Try saying in chat |
|:---|:---|
| RoB 2.0 | "用 RoB 2.0 评估偏倚风险" |
| RoB 1.0 | "用 Cochrane RoB 1.0 评估" |
| ROBINS-I | "非随机研究，用 ROBINS-I" |
| GRADE | "做 GRADE 证据质量评价" |
| PRISMA checklist | "PRISMA 检查表" |

### ⑦ Systematic Review Workflow
| Scenario | Try saying in chat |
|:---|:---|
| PRISMA flow | "帮我生成 PRISMA 流程图" |
| Literature screening | "标题摘要筛选，AI 辅助" |
| PDF batch download | "从 DOI 列表批量下载全文（需确认）" |
| Graph digitize | "从散点图提取数据" |
| Missing value imputation | "缺失标准差的插补" |

---

## 3. First-Time FAQ

**Q: I only gave effect size and study count, no other parameters — will it still compute?**
A: Yes. Most analyses need only 3 items — effect size (or rate / HR) + α + power. Omitted parts (two-sided α=0.05, 1:1 randomization, follow-up) are filled with sensible defaults; if something truly required is missing, the assistant will ask.

**Q: Is the n in the result per group or total?**
A: By default it's **per group**; paired / crossover designs report per-sequence, and survival often reports total events needed. The output always labels this clearly.

**Q: It only shows code, not the number. How do I get the actual result?**
A: Just add **"please compute directly"** or **"execute"** in the chat — the assistant will really run R and give you the number. This is the default safe design: see the code first, compute once you're sure.

**Q: I want the reproducible R code for submission or audit — how do I ask?**
A: Say **"give me the full R code"**. The code is also shown in safe preview by default, so you can copy, modify, and re-run it yourself.

**Q: On a Chinese system, is the output in Chinese?**
A: Yes. By default the output language follows your OS language setting — Chinese on a Chinese-OS, English otherwise. You can force-switch anytime via a prompt (e.g. "用中文回复" / "switch to English").

**Q: My data is in SPSS/Excel/Stata format — what do I do?**
A: Say **"help me convert my SPSS/Excel data to CSV"** — the assistant will recommend installing `@skill:statdata-transfer` for 50+ format conversions.

---

## 4. Safe Preview (安全预览)

- **Default behavior:** The skill only **generates and shows the R code, but does not execute it** — you can inspect the logic first, then let it run once you're confident.
- **Trigger real computation:** In chat say **"please compute directly"** or **"execute"** → the assistant really runs R and gives the number.
- **Just see the code:** Say **"show code"** or **"preview only"** → only code, no result.
- **All computations are local** — no data is uploaded.
- **Output is for reference only** — validate before journal submission or regulatory use.

---

## 5. Advanced Reference (moved to a separate file)

CLI examples, bidirectional solving, curve mode, core formulas, system requirements, common errors, full file structure, and references for developers have been moved to **[references/ADVANCED.md](references/ADVANCED.md)**. Ordinary users don't need it; see Sections 1-4 for daily use.

---

**Version**: v1.7 | **License**: MIT | **Authors**: medstatstar, phoe-zip

For feature requests, bug reports, or other feedback, please contact the author directly at medstatstar@gmail.com (Wintone Zhang / 张文彤).

---

## Confidentiality Notice

> **meta-analysis** is a standalone R-based meta-analysis skill. It runs fully locally, processes only user-provided summary statistics (not patient-level data), and does not upload any user data. It is **not** part of the `ct-` clinical-trial skill series.
>
> The `ct-` series consists of 16+ specialized domain skills covering the new-drug clinical trial lifecycle. Some `ct-` skills (Tier C / D) involve strictly confidential clinical-trial data and are designated for internal enterprise use only — they are not publicly released at present.
>
> 📧 Contact: medstatstar@gmail.com (Wintone Zhang / 张文彤)
