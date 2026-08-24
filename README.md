# meta-analysis

[🇨🇳 中文 (Chinese)](./README_zh-CN.md) | [🇺🇸 English (Current)](#)

<div align="center">
  <img src="assets/icon.svg" width="240" height="240" alt="meta-analysis logo"/>
</div>

> **Easy-to-use R-based Meta-Analysis for Clinical Researchers**
>
> You don't need to code or memorize commands — just describe your meta-analysis needs in **plain language inside a chat**, and the skill **automatically runs** the full analysis (pooling, figures, report) for you. Powered by R and 14 core + 2 optional professional R packages (metafor, meta, netmeta, bayesmeta, dosresmeta, mada, etc.), it returns results in Chinese or English depending on your OS language setting (you can force-switch via a prompt at any time). Once you describe a request, the skill **auto-executes** and returns results + figures; ask for the full reproducible R code at any time.

---

## Who This Is For

meta-analysis is part of the CT-series skill family, built for three groups:

- **Clinical-trial practitioners at pharmaceutical companies** — sponsors, CROs, and medical / statistical / regulatory roles who need to pool and compare study evidence;
- **Clinicians and nurses who design, conduct, or participate in clinical research** and need meta-analysis / systematic-review support;
- **Medical students who want to learn evidence-based medicine and meta-analysis methodology in a structured way**.

---

## 1. How to Use It in a Chat (the Core)

meta-analysis is a **conversational skill**: you simply tell the assistant what you want in natural language — no commands, no parameter names to remember. As a WorkBuddy skill it **auto-loads with no extra installation**.

Below are 7 real conversational examples. **Example 1 is the upstream Topic Selection gate** (choose among candidate directions before running any analysis), followed by Examples 2–7 ordered from simple to advanced. Each shows **"You say"** and a sketch of **"The assistant replies"**, plus how to get the actual number.

### Example 1 · Topic selection: choose among candidate meta-analysis directions (upstream gate)
**You say:**
> I'm interested in SGLT2 inhibitors for renoprotection and cardiovascular benefit in chronic kidney disease (CKD), but I haven't decided which specific meta-analysis direction to pursue. Can you help me shortlist candidate directions?

**Assistant replies (sketch):**
> Sure — I'll use the topic-selection framework (`references/topic-selection.md`). First I run a **dedup check against the primary literature (Rule R3)**, then shortlist — otherwise a saturated direction can be wrongly pushed as the top pick.
>
> **First, rule out the saturated direction**: the generic "SGLT2i vs placebo on cardiorenal composite endpoints in CKD" was already covered by ≥5–6 large meta-analyses in 2024 (e.g. BMJ Medicine 2024, 13 RCTs/29 614 pts; BMC Nephrol 2024 eGFR<60 subgroup, 17 RCTs/27 928 pts; Lancet subsidiary 2024 across the cardiometabolic spectrum, 15 trials/100 952 pts). They consistently report "no effect modification by diabetes status / baseline eGFR / UACR" — the incremental value of a routine subgroup meta is exhausted. **Do not redo the generic pairwise meta.**
>
> Re-shortlisting 3 candidates by **evidence gap + novelty** (Stage 1 Gate 1: produce 1–3 directions; I won't decide for you):
>
> **Candidate ① Dedicated meta in non-diabetic CKD (top pick)**
> - Intervention: SGLT2i vs placebo; population: **non-diabetic CKD** (isolating non-diabetic subgroups from DAPA-CKD / EMPA-KIDNEY + a few dedicated RCTs)
> - 4-dim quick score: clinical 5 / feasibility 4 / data 4 / novelty 5 → total 18 (strongly recommend)
> - Meta type: standard pairwise (meta / metafor); IPD preferred, published subgroup data acceptable
> - Basis: existing meta-analyses pool diabetic + non-diabetic together; the source papers themselves call non-diabetic CKD "still under-studied, needs more research" (Reyes-Farias, PLOS ONE 2023).
> - ⚠️ The non-diabetic subgroup is smaller — power and heterogeneity must be discussed honestly.
>
> **Candidate ② Effect of SGLT2i on renin-angiotensin-system (RAS) blocker persistence (mechanistic bridge)**
> - Outcome: RAS discontinuation/interruption (joint CREDENCE + DAPA-CKD analysis already reported −15%, PMID 37876229)
> - 4-dim quick score: clinical 4 / feasibility 3 / data 3 / novelty 5 → total 15 (recommend)
> - Meta type: standard pairwise (HR pooling); few RCTs report this endpoint — verify k ≥ 5 first
> - Value: unique clinical story ("SGLT2i keeps RAS on board"), least likely to collide with existing work.
>
> **Candidate ③ Efficacy and safety in advanced CKD (eGFR<30 / stage 4–5)**
> - Outcomes: kidney composite + eGFR slope + rare safety events
> - 4-dim quick score: clinical 5 / feasibility 3 / data 3 / novelty 4 → total 15 (recommend)
> - Meta type: standard pairwise; note CJASN 2025 (Elenjickal, 10 RCTs/4 800 eGFR<30 pts) just published — find a differentiated angle first.
>
> **Suggestion**: Start with ① (real gap, greatest clinical need, literature self-identifies the gap); ② is the most distinctive story; ③ needs differentiation from the 2025 paper. Next step can be a Full Assessment (PICO decomposition + dedup search + PRISMA/AMSTAR-2 pre-check) to produce a topic report.

**📌 Note:** When you have a direction but are unsure which specific meta to run, the assistant uses the topic-selection framework to produce **1–3 candidate directions + a 4-dim score + meta type**, instead of deciding for you or giving a single answer. This is the upstream gate (Topic Selection) before analysis — no R computation is invoked. Candidates are stratified by **evidence gap / novelty**, each backed by a primary-literature dedup check (Rule R7), so a saturated generic direction is no longer mis-pushed as the top pick.

### Example 2 · Two-group binary meta (most common)
**You say:**
> Combine the OR across these 5 binary studies:
> Study A: experimental 30/100, control 20/100
> Study B: experimental 45/120, control 30/100
> ...

**Assistant replies (sketch):**
> ✅ 5 studies, random-effects (DL), OR = 1.52 (95%CI: 1.18–1.96), I² = 34%
> (Ask for the full reproducible R code at any time.)

**📌 Auto-execution:** Once you describe the request, the assistant **auto-executes** and returns the real result; ask for the reproducible code by saying **"give me the full R code"**.

### Example 3 · Effect size conversion
**You say:**
> Convert Cohen's d = 0.8 to logOR

**Assistant replies (sketch):**
> ✅ d = 0.8 → logOR ≈ 1.45 (SE ≈ 0.38), based on logOR = d × π/√3

### Example 4 · Heterogeneity + subgroup
**You say:**
> I did a continuous meta with 8 studies, SMD pooled, but I² is high — I want to subgroup by region

**Assistant replies (sketch):**
> ✅ 8 studies, SMD = 0.42 (95%CI: 0.15–0.69), I² = 78%
> Subgroup by region:
> - Asia (k=4): SMD = 0.55, I² = 45%
> - Euro-US (k=4): SMD = 0.28, I² = 62%
> - Between-group Q = 4.12, p = 0.04

### Example 5 · Complex: Network meta with multiple decisions (popup menu)
**You say:**
> I want to do a network meta with 4 interventions, but I haven't decided whether to use frequentist or Bayesian, and I'm not sure if I should include dose-response

**Assistant replies (sketch):**
> 4 interventions clear. Two key choices to clarify:
>
> **① Which analysis framework?**
> - (a) Frequentist — `netmeta`, inverse-variance based, good for consistent networks
> - (b) Bayesian — `gemtc` (JAGS) or `multinma` (Stan) **local only** (a known coze limitation: the container has no root to install JAGS; on the cloud use (a) netmeta); `bayesmeta` supports Bayesian pairwise comparisons locally
>
> **② Include dose-response?**
> - (a) No — pure pairwise comparison network
> - (b) Yes — needs dose-effect parameters, Bayesian framework preferred
>
> **③ Can't decide?** → Say "explain the differences between these choices in detail" and the assistant explains first, then lets you decide

**📌 Note:** When you've **named the test type but are stuck on "which option / design family"**, the assistant **pops a routing menu** to confirm step by step — instead of deciding for you or dumping the full menu. The menu also offers an "explain the differences" option — when you're unsure, it explains before you decide.

### Example 6 · Vague: Not sure which model (grill-me)
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

### Example 7 · Systematic review workflow
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

> The underlying R packages (metafor / meta / netmeta …) are listed in Section 6 "Advanced Reference"; ordinary users don't need to care.

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
| Survival meta | "Pool survival HR via metafor (survmeta removed)" |
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

**Q: Does the analysis run as soon as I describe a request?**
A: Yes. Once you describe the request, the assistant **auto-executes** and returns the real numbers + figures — no extra trigger word needed. Computation runs on the cloud coze R engine (data disclosure in Section 5).

**Q: I want the reproducible R code for submission or audit — how do I ask?**
A: Say **"give me the full R code"**. Every analysis returns reproducible R code (with R and package versions), which you can copy, modify, and re-run yourself.

**Q: On a Chinese system, is the output in Chinese?**
A: Yes. By default the output language follows your OS language setting — Chinese on a Chinese-OS, English otherwise. This default requires no extra permission and only affects display language; you can force-switch anytime via a prompt (e.g. "用中文回复" / "switch to English").

**Q: My data is in SPSS/Excel/Stata format — what do I do?**
A: Say **"help me convert my SPSS/Excel data to CSV"** — the assistant will recommend installing `@skill:statdata-transfer` for 50+ format conversions.

**Q: What if my data must stay confidential?**
A: Run the whole analysis with **simulated / placeholder data**, then ask the skill for the **full reproducible R code** and run it yourself locally with your real data. The skill itself only sends your **analysis parameters / summary statistics** (event counts, sample sizes, effect sizes) to the cloud coze R engine — it **never touches your raw datasets or individual-patient records** (unless you explicitly choose to run an IPD analysis through the cloud, in which case sending IPD to the cloud is your decision).

**Q: What if I found an error in the result — how do I report it?**
A: This skill follows the standard bug-report workflow. If you suspect the result is wrong (or the engine errored), just say **"report a bug" / "上报问题" / "提交错误报告"**. The skill also **proactively asks** whether to report when it detects a likely defect (e.g. the engine errors or retries still fail) — at most **once per session**, and you can always decline. Either way, the assistant will:
1. **Propose a sanitized report** (11-field whitelist: skill / skill_version / test / error_type / error_code / engine_status / description / locale / query_origin / session_hash / attempts — **no raw input values or personal data**, except the `description` field where you decide what to disclose, e.g. the algorithm/function used and the error message);
2. **Show the full report text for your review** — you can add a problem description or correct anything before confirming;
3. **Send after your explicit confirmation** — to the unified endpoint `https://ct-bugreport.coze.site/run` (if this session called coze) or, if purely local, **save the sanitized report locally and show you the author contact** so you can email it yourself if you choose (the skill itself does not send it; data never leaves your machine unless you email it);
4. **Receive an acknowledgment** — including whether a previously submitted report from your source has already been fixed (with the fix note) or is still pending.

You stay in full control: the report is shown to you **before** anything is sent, and nothing is transmitted without your explicit "send" confirmation.

---

## 4. Execution Model

- **Auto-execution:** Once you describe a request, the skill **auto-executes** the analysis and returns real numbers + figures — no extra trigger word or confirmation needed. Computation runs on the cloud coze R engine by default.
- **Default compute path:** The skill sends the analysis request to the cloud coze R engine (`https://ct-meta.coze.site/run`) (data disclosure in Section 5).
- **Reproducible code:** Every analysis returns reproducible R code (with R + package versions); say **"give me the full R code"** to obtain it for submission or audit.
- **Outbound authorization:** The default endpoint is pre-approved and runs automatically; a custom endpoint (`COZE_META_ENDPOINT`) asks for confirmation on first use (see Section 5).
- **Output is for reference only** — validate before journal submission or regulatory use.

---

## 5. Data & Privacy

The skill sends data externally in **two** situations: ① when you describe an analysis request, the skill **auto-sends** the analysis request to execute; ② when you confirm sending an error report. **Neither sends personal identifiers.**

**5.1 Analysis request (cloud computation)**
- **What is sent:** your **analysis data** — **summary statistics** such as study event counts / sample sizes / effect sizes. No personal identifiers; payloads are sanitized before sending.
- **When:** the skill **auto-sends** after you describe a request; **before the first outbound call each session**, the skill gives you a one-time spoken disclosure of what is sent and to which endpoint (then executes automatically, without per-call confirmation).
- **Endpoint:** default `https://ct-meta.coze.site/run` (pre-approved in `adapters/config.json` `auto_approve_endpoints`). A custom endpoint (`COZE_META_ENDPOINT`) asks for confirmation on first use (AUTH-BLOCK), and is persisted to the whitelist after you approve.
- **If declined:** the skill returns a clear "cloud analysis not used" message.

**5.2 Metadata sent with the request**
Each request also carries two metadata fields (**in both the analysis request and the error report**):
- `query_origin`: a SHA-256 hash of your machine hostname, used only for server-side attribution / rate-limiting — **not** your plaintext hostname;
- `locale`: your OS language, for bilingual output.

Neither is used to identify you personally.

**5.3 Error report**
- **What is sent:** **only** the 11-key whitelist envelope (skill / skill_version / test / error_type / error_code / engine_status / description / locale / query_origin / session_hash / attempts) — **no analysis data and no personal identifiers**. `description` is the only free-text field, and you review it before consent (hard boundary: no identifiable person/institution/subject info).
- **Endpoint:** unified bug-report endpoint `https://ct-bugreport.coze.site/run`.
- **If declined:** nothing is sent; if there is no cloud call this session, the report is saved locally instead (`save_local_report`, data never leaves the machine).

> **In one sentence:** your **analysis summary data** is **auto-sent** to the cloud after you describe a request (with a one-time disclosure before the first outbound call each session); **error reports** go to the unified endpoint only after your confirmation; the two metadata fields (`query_origin` hash + `locale`) are for anonymous attribution. Raw data and individual records never leave your machine.

---

## 6. Advanced Reference (moved to a separate file)

CLI examples, bidirectional solving, curve mode, core formulas, system requirements, common errors, full file structure, and references for developers have been moved to **[references/ADVANCED.md](references/ADVANCED.md)**. Ordinary users don't need it; see Sections 1-5 for daily use.

---

**Version**: v2.0.0 | **License**: MIT | **Authors**: medstatstar, phoe-zip

For feature requests, bug reports, or other feedback, please contact the author directly at medstatstar@gmail.com (Wintone Zhang / 张文彤).

---

## Confidentiality Notice

> The CT series consists of 20+ specialized domain skills, organized into **two tiers — A, B** — by "confidential-data-exfiltration risk + whether external retrieval is needed", providing full coverage of the entire new-drug clinical trial (Clinical Trial) lifecycle.
>
> - **Tier A (non-confidential, public)**: inputs are ordinary data, run fully locally (`network=off`) or with external public retrieval (`network=public-retrieval`, e.g. ct-registry / ct-advisor); no confidential information involved. Tier A skills are published openly on GitHub.
> - **Tier B (confidential, internal)**: involve strictly confidential clinical-trial data and internal information from pharma sponsors (e.g., ct-analysis, ct-sdtm, ct-eligibility); Tier B is processed locally (`egress=none`, data never leaves the boundary) or requires approval for outbound (`egress=approval-req`, e.g. ct-eligibility). Tier B skills are designated for internal enterprise use only and are not publicly released at present.
>
> If you do have a genuine need for these confidential skills, please contact the author to request custom installation.
>
> 📧 Contact: medstatstar@gmail.com (Wintone Zhang / 张文彤)
