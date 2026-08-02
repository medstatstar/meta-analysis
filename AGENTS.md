# AGENTS.md — meta-analysis v1.7 (R-based Meta-Analysis Skill)

> This skill is a published skill (A-tier equivalent — fully local, no external retrieval). Its AGENTS.md is **English-only** per ct-base §3/§4 ("SKILL.md body + references + AGENTS.md are English-only for published skills").

## Overview / 技能概述

`meta-analysis`: An R-based, conversation-driven Meta-Analysis skill for WorkBuddy. Covers 100% of RevMan 5.x functionality, Stata `metareg`/`mvmeta` equivalents, effect-size conversions (`esc`), cluster-robust variance estimation (`clubSandwich`/`robumeta`), Bayesian NMA (Stan/JAGS), survival meta, TSA, single-group meta, diagnostic meta, and systematic-review workflow. All analyses ship reproducible R code and editable SVG figures.

---

## Core Rules / 核心规则

### 1. Environment Detection / 环境检测
- **R**: detect via PATH or `RSCRIPT_PATH` env. Missing → recommend https://cran.r-project.org/.
- **Python**: Anaconda (`C:\Tools\anaconda3\python.exe`); use only for helper scripts (never for meta-analysis computation).
- Never hardcode paths.

### 2. Code Execution / 代码执行规范
- **Default: SAFE PREVIEW (dry-run)**. Generated R code is displayed, NOT executed unless user opts in.
- Opt-in trigger: user explicitly says "run it", "execute", or similar — NOT a `--yes` flag (natural-language dialogue mode).
- Temp files written to system temp, auto-cleaned via `r_libs.run_r()`.

### 3. Language Detection / 语言检测
- Default: English.
- Auto-switch to Chinese when OS locale contains `zh`/`CN` (via `scripts/i18n.py` → `is_chinese_os()`).
- Code output (R / Python) always English; not affected by language policy.
- User-facing runtime prompts use `i18n.t(key)`.

### 4. Security Red Line / 安全红线
- **Fully local analysis**: all computation runs in user's local R environment.
- **No auto-install**: R packages are NOT auto-installed; missing packages are listed and user installs manually.
- **No confidential data exfiltration**: all data you provide — including individual patient data (IPD) for IPD meta — is processed **locally from your own files and is never uploaded or sent anywhere**. Summary statistics (2×2 tables, effect sizes + SEs) are the common case; IPD is fully supported and handled the same local-only way. No network egress of your data occurs at any point.
- **Network only on explicit opt-in**: PDF full-text download from DOI/PMID requires explicit user confirmation.
- `permissions` block declared in SKILL.md top-level.
- Output sanitization via `r_libs.sanitize_output()`.

### 5. Reuse Shared Assets / 复用底座
- Copy shared assets from `ct-base/scripts/` and `ct-base/references/`:
  - `scripts/i18n.py`: bilingual strings single source of truth.
  - `scripts/r_libs.py`: R invocation + validation + sanitization helper.
  - `references/language_policy.md`: bilingual policy detailed companion.
  - `references/report_template.md`: report skeleton reference.
- Resolve via local-first + ct-base-fallback pattern if needed.

### 6. Interactive Menu / Navigation / 交互菜单
- **Triage §5.2 (ct-base §5.2)**: classify user's first message as Simple / Complex / Vague.
  - **Simple**: single, specific intent (e.g., "pool OR from these 5 studies", "convert d to logOR") → skip menu, go directly to analysis.
  - **Complex**: multi-decision / multi-parameter (e.g., "design a network meta with 3 interventions, subgroup by region, check inconsistency") → present level-1 menu with "need more explanation" entry.
  - **Vague**: unclear what user wants (e.g., "I need meta-analysis help") → grill-me style branch questions, 1–3 per round.
- Menu structure mirrors level-1 (7 categories) → level-2 (sub-menus) from SKILL.md.
- Non-exclusive menu entries per ct-base §6 guidance.

### 7. Traceability (Grounding) / 溯源硬规则 (ct-base §5.1)
- All factual/assertive claims must cite source: specific `ref-*.md` section or official guideline.
- If a claim has no verifiable source → mark `⚠️ official verify` and ask user to confirm against official text.
- Applies to: RevMan feature descriptions, Stata↔R mapping claims, statistical method recommendations.

---

## Dependencies / 依赖

### R packages (core)
```
metafor meta dmetar netmeta ggplot2 esc clubSandwich robumeta bayesmeta multinma gemtc dosresmeta survmeta mada metagear gridExtra ggforestplot svglite
```
- User installs manually (skill does NOT auto-install).
- `scripts/setup_packages.R` lists full commands for review.

### Python (helper only)
```
# i18n.py / r_libs.py have no third-party deps beyond stdlib
```

---

## Output Convention / 输出约定

Each analysis produces:
- `analysis_complete.R` — fully reproducible R script
- Forest plot (`.svg` + `.png`)
- Funnel plot, standard + contour-enhanced (`.svg` + `.png`)
- `results_summary.md` — structured results (effect, CI, I², τ², p-values)
- CSV data backup
- Optional: R Markdown / HTML report

SVG editing guide → `references/svg_editing.md`.

---

## Directory Structure / 目录结构

```
meta-analysis/
├── SKILL.md                       # Frontmatter + English body (published skill)
├── AGENTS.md                      # This file (self-improvement + agent rules, English)
├── CHANGELOG.md                   # Version / fix log
├── README.md                      # English (top switch to README_zh-CN.md)
├── README_zh-CN.md                # Chinese (top switch to README.md)
├── LICENSE                        # MIT
├── requirements.txt               # R package list
├── assets/
│   └── icon.svg                   # Skill logo
├── scripts/
│   ├── i18n.py                    # ct-base shared: bilingual helper
│   ├── r_libs.py                  # ct-base shared: R invocation + validation
│   ├── r_templates.py             # R code template generator (.py → .R)
│   ├── r_meta_analysis_core.py    # Core engine templates
│   ├── r_effect_size_conversions.py
│   ├── r_network_meta_analysis.py
│   ├── r_stata_equivalents.py
│   ├── r_advanced_functions.py
│   ├── r_setup_packages.py
│   └── check_integrity.sh         # Integrity self-check (auto-generate .R from .py)
├── references/
│   ├── language_policy.md         # ct-base shared: bilingual policy detail
│   ├── report_template.md         # ct-base shared: report skeleton
│   ├── interactive_menu.md
│   ├── data_templates.md
│   ├── revman_complete.md
│   ├── stata_to_r_mapping.md
│   ├── advanced_analysis.md
│   ├── single_group_meta.md
│   ├── survival_meta.md
│   ├── tsa_diagnostics.md
│   ├── diagnosis_meta.md
│   ├── bayesian_nma.md
│   ├── esc_robust_meta.md
│   ├── review_workflow.md
│   ├── r_packages.md
│   ├── citations.md
│   ├── references.md
│   ├── advanced_api.md
│   ├── svg_editing.md
│   └── purpose_zh.md
└── (runtime-generated .R files via check_integrity.sh)
```

---

## Changelog Sync / 变更日志同步

All version bumps and fixes must be recorded in `CHANGELOG.md`. Security-related fixes are mandatory entries.
