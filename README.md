# meta-analysis

[🇨🇳 中文 (Chinese)](./README_zh-CN.md) | [🇺🇸 English (Current)](#)

<div align="center">
  <img src="assets/icon.svg" width="240" height="240" alt="meta-analysis logo"/>
</div>

> **Easy-to-use R-based Meta-Analysis for Clinical Researchers**
>
> You don't't need to code or memorize commands — just describe your meta-analysis needs in **plain language inside a chat**, and the skill runs the full analysis for you. Powered by R and 14 core + 2 optional professional R packages (metafor, meta, netmeta, bayesmeta, dosresmeta, mada, etc.), it returns results in Chinese or English depending on your OS language setting (you can force-switch via a prompt at any time). The generated R code is shown in **SAFE PREVIEW** (not executed) by default — it only computes once you confirm.

---

> **Outbound data disclosure (ct-base §5, mandatory)** — This skill sends your **analysis data**
> (study event counts / sample sizes / effect sizes; no personal identifiers) to the coze
> meta-analysis endpoint (`https://ct-meta.coze.site/run` by default) for cloud R computation.
> The default endpoint is pre-approved in `adapters/config.json` (`auto_approve_endpoints`);
> custom endpoints (`COZE_META_ENDPOINT`) ask for your confirmation on first use (AUTH-BLOCK),
> and are persisted to the whitelist after you approve. If not approved, the skill falls back to
> the local engine (or returns a clear "cloud analysis not used" message when no local R exists).
> Payloads are sanitized (PII stripped) before sending.
>
> **Metadata sent with the request (ct-base §5):** the request also carries `query_origin` (a SHA-256 hash of your machine hostname, used only for server-side attribution / rate-limiting — **not** your plaintext hostname) and `locale` (your OS language, for bilingual output). Neither is used to identify you personally.
>
> **Bug-report endpoint disclosure (ct-base §5 / §20.3, mandatory)** — When you confirm sending a (sanitized) error report via the in-skill bug reporter (`adapters/bug_report.py`), the skill sends **only** the 11-key whitelist envelope (skill name / version / error type / error code / engine status / your free-text `description` / locale / `query_origin` / session hash / retry count / test) to the unified bug-report endpoint `https://ct-bugreport.coze.site/run`. It sends **no analysis data and no personal identifiers** — `description` is the only free-text field and you review it before consent (hard boundary: no identifiable person/institution/subject info). The same `query_origin` + `locale` metadata above is attached. If you decline, nothing is sent; if there is no cloud call this session, the report is saved locally instead (`save_local_report`, data never leaves the machine).

## Who This Is For

meta-analysis is part of the CT-series skill family, built for three groups:

- **Clinical-trial practitioners at pharmaceutical companies** — sponsors, CROs, and medical / statistical / regulatory roles who need to pool and compare study evidence;
- **Clinicians and nurses who design, conduct, or participate in clinical research** and need meta-analysis / systematic-review support;
- **Medical students who want to learn evidence-based medicine and meta-analysis methodology in a structured way**.

## 1. How to Use It in a Chat (the Core)

meta-analysis is a **conversational skill**: you simply tell the assistant what you want in natural language — no commands, no parameter names to remember. As a WorkBuddy skill it **auto-loads with no extra installation**.

Below are 7 real conversational examples. **Example 1 is the upstream Topic Selection gate** (choose among candidate directions before running any analysis), followed by Examples 2–7 ordered from simple to advanced. Each shows **"You say"** and a sketch of **"The assistant replies"**, plus how to get the actual number.

### Example 1 · Topic selection: choose among candidate meta-analysis directions (upstream gate)
**You say:**
> I'm interested in SGLT2 inhibitors for renoprotection and cardiovascular benefit in chronic kidney disease (CKD), but I haven't decided which specific meta-analysis direction to pursue. Can you help me shortlist candidate directions?

**Assistant replies (sketch):**
> Sure — I'll use the topic-selection framework (`references/topic-selection.md`) to shortlist candidates. Here are 3 candidates (Stage 1 Gate 1: produce 1–3 directions; I won't decide for you):
>
> **Candidate ① Standard pairwise meta: SGLT2i vs placebo on major kidney endpoints in CKD**
> - Outcomes: ESRD / serum-creatinine-doubling composite (binary OR/RR) + eGFR slope (continuous SMD)
> - 4-dim quick score: clinical 4 / feasibility 4 / data 4 / novelty 3 → total 15 (recommend)
> - Meta type: standard pairwise (meta / metafor)
>
> **Candidate ② Network meta: head-to-head comparison of different SGLT2i agents**
> - ≥3 interventions (dapagliflozin / empagliflozin / canagliflozin) → frequentist NMA (netmeta)
> - 4-dim quick score: clinical 4 / feasibility 3 (needs multi-arm data) / data 3 / novelty 4 → total 14 (recommend)
> - ⚠️ Bayesian NMA is a known coze-environment limitation — use netmeta (frequentist) on the cloud
>
> **Candidate ③ Meta-regression: effect modification of SGLT2i by diabetic / non-diabetic CKD**
> - Covariate: diabetes status; effect-modification test
> - 4-dim quick score: clinical 3 / feasibility 3 / data 3 / novelty 4 → total 13 (hold, fix data first)
>
> **Suggestion**: Candidate ① has the highest feasibility — start there. For ②, confirm ≥3 interventions and note the coze Bayesian limitation. The next step can be a Full Assessment (PICO decomposition + dedup search + PRISMA/AMSTAR-2 pre-check) to produce a topic report.

**📌 Note:** When you have a direction but are unsure which specific meta to run, the assistant uses the topic-selection framework to produce **1–3 candidate directions + a 4-dim score + meta type**, instead of deciding for you or giving a single answer. This is the upstream gate (Topic Selection) before analysis — no R computation is invoked.

### Example 2 · Two-group binary meta (most common)
**You say:**
> Combine the OR across these 5 binary studies:
> Study A: experimental 30/100, control 20/100
> Study B: experimental 45/120, control 30/100
> ...

**Assistant replies (sketch):**
> ✅ 5 studies, random-effects (DL), OR = 1.52 (95%CI: 1.18–1.96), I² = 34%
> (Safe preview: R code shown below but not executed.)

**📌 Get the actual number:** Say **"please compute directly"** — the assistant sends the request to the cloud coze R engine and returns the real result (see Section 4, "Safe Preview").

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
> - (b) Bayesian — `gemtc` (JAGS) or `multinma` (Stan) **local only**（coze 端为已知环境限制，无 root 无法装 JAGS，云端请用 (a) netmeta）；`bayesmeta` 支持贝叶斯配对比较，本地可用
>
> **② Include dose-response?**
> - (a) No — pure pairwise comparison network
> - (b) Yes — needs dose-effect parameters, Bayesian framework preferred
>
> **③ Can't decide?** → Say "explain the differences between these choices in detail" and the assistant explains first, then lets you decide

**📌 Note:** When you've **named the test type but are stuck on "which option / design family"**, the assistant **pops a routing menu** to confirm step by step — instead of deciding for you or dumping the full 49-test menu. The menu also offers an "explain the differences" option — when you're unsure, it explains before you decide.

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

**Q: It only shows code, not the number. How do I get the actual result?**
A: Just add **"please compute directly"** or **"execute"** in the chat — the assistant sends the analysis request to the cloud coze R engine and gives you the real number. This is the default safe design: see the request first, compute once you're sure. Sending only happens on this explicit, high-friction instruction — the skill never sends the request on its own or from a casual mention of these words.

**Q: I want the reproducible R code for submission or audit — how do I ask?**
A: Say **"give me the full R code"**. The code is also shown in safe preview by default, so you can copy, modify, and re-run it yourself.

**Q: On a Chinese system, is the output in Chinese?**
A: Yes. By default the output language follows your OS language setting — Chinese on a Chinese-OS, English otherwise. This default requires no extra permission and only affects display language; you can force-switch anytime via a prompt (e.g. "用中文回复" / "switch to English").

**Q: My data is in SPSS/Excel/Stata format — what do I do?**
A: Say **"help me convert my SPSS/Excel data to CSV"** — the assistant will recommend installing `@skill:statdata-transfer` for 50+ format conversions.

---

**Q: What if my data must stay confidential?**
A: This skill sends only your **analysis parameters / summary statistics** (event counts, sample sizes, effect sizes) to the cloud coze R engine — it never touches your raw datasets or individual-patient records. If you still prefer data to stay on your machine, run the analysis **locally** (say "use local engine" / set `prefer="local"`): the same R engine runs on your computer and nothing leaves it. You can also ask for the full reproducible R code and run it yourself with your real data.

**Q: What if I found an error in the result — how do I report it?**
A: This skill follows the ct-base §20.3 bug-report workflow. If you suspect the result is wrong (or the engine errored), just say **"report a bug" / "上报问题" / "提交错误报告"**. The skill also **proactively asks** whether to report when it detects a likely defect (e.g. the engine errors or retries still fail) — at most **once per session**, and you can always decline. Either way, the assistant will:
1. **Propose a sanitized report** (11-field whitelist: skill / skill_version / test / error_type / error_code / engine_status / description / locale / query_origin / session_hash / attempts — **no raw input values or personal data**, except the `description` field where you decide what to disclose, e.g. the algorithm/function used and the error message);
2. **Show the full report text for your review** — you can add a problem description or correct anything before confirming;
3. **Send after your explicit confirmation** — to the unified endpoint `https://ct-bugreport.coze.site/run` (if this session called coze) or saved locally + emailed to the author (if purely local, data never leaves your machine);
4. **Receive an acknowledgment** — including whether a previously submitted report from your source has already been fixed (with the fix note) or is still pending.

You stay in full control: the report is shown to you **before** anything is sent, and nothing is transmitted without your explicit "send" confirmation.

## 4. Safe Preview

- **Default behavior:** The skill only **builds and shows the analysis request (the task / data / params / figure envelope), but does not send it** — you can inspect the plan first, then let it run once you're confident.
- **Trigger real computation:** In chat say **"please compute directly"** or **"execute"** → the assistant sends the request envelope to the cloud coze R engine, which computes and returns the real numbers. (No `--yes` flag — sending is driven entirely by this plain-language instruction; the skill never sends the request on its own or from a casual mention of these words.)
- **Just see the code:** Say **"show code"** or **"preview only"** → only the request envelope, no result.
- **Default compute path:** By default the skill sends the analysis request to the cloud coze R engine (`https://ct-meta.coze.site/run`); analysis data is sent per the "Outbound data disclosure (ct-base §5)" block above. For local / offline analysis, use the local engine (`prefer="local"`). Safe preview only controls whether the request is sent — it is independent of where computation runs.
- **Output is for reference only** — validate before journal submission or regulatory use.

---

## Example Test Records (§16.6 gate)

> Tested 2026-08-20 per ct-base §16.6, one example at a time: **7/7 passed**. Computation examples 2/3/4/7 returned real `stats` + `figures` + `repro` from the coze endpoint (`https://ct-meta.coze.site/run`); behavioral examples 1/5/6 were verified against SKILL.md Triage (§5.2) and `references/topic-selection.md` / `references/interactive_menu.md`. Full report: `meta_readme_test/README_EXAMPLES_TEST_REPORT.md`.

| Example | Type | Status |
|---|---|---|
| 1 Candidate-direction selection / 5 Network-meta routing menu / 6 Vague grill-me | Behavior (topic / routing) | ✅ Passed |
| 2 Binary OR pairwise / 3 Effect-size conversion / 4 SMD+subgroup / 7 PRISMA flow | Computation (coze) | ✅ Passed |

## 5. Advanced Reference (moved to a separate file)

CLI examples, bidirectional solving, curve mode, core formulas, system requirements, common errors, full file structure, and references for developers have been moved to **[references/ADVANCED.md](references/ADVANCED.md)**. Ordinary users don't need it; see Sections 1-4 for daily use.

---

**Version**: v2.0.0 | **License**: MIT | **Authors**: medstatstar, phoe-zip

For feature requests, bug reports, or other feedback, please contact the author directly at medstatstar@gmail.com (Wintone Zhang / 张文彤).

---

## Confidentiality Notice

> The CT series consists of 20+ specialized domain skills, organized into **two tiers — A, B (the former C/D tiers are merged into confidential Tier B)** — by "confidential-data-exfiltration risk + whether external retrieval is needed", providing full coverage of the entire new-drug clinical trial (Clinical Trial) lifecycle.
>
> - **Tier A / B (non-confidential)**: run fully locally using only ordinary data; Tier B may need external public retrieval but involves no confidential information. These skills are published openly on GitHub.
> - **Tier B (confidential, formerly C/D)**: involve strictly confidential clinical-trial data and internal information from pharma sponsors (e.g., ct-analysis, ct-sdtm); Tier B is processed locally and never leaves the boundary, or additionally requires policy approval. These skills are designated for internal enterprise use only and are not publicly released at present.
>
> If you do have a genuine need for these confidential skills, please contact the author to request custom installation.
>
> 📧 Contact: medstatstar@gmail.com (Wintone Zhang / 张文彤)

