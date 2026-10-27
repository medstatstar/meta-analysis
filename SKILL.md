---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: Meta Analysis / 医学Meta分析
version: 2.20.3
license: MIT
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan + Stata 等价 + esc + RVE + 贝叶斯 NMA + 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta等共 23 种分析图形。所有分析提供可复现 R 代码。还可提供Meta选题方向判断 + 文献检索整理 + 筛选 + 数据提取功能。云端 R 引擎凭证随包分发，零用户侧配置。
description: "Comprehensive R-based meta-analysis skill covering RevMan + Stata equivalents + esc + RVE + Bayesian NMA + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta, for a total of 23 analysis figures. All analyses ship reproducible R code. Can also provide meta topic-direction judgment + literature retrieval and organization + screening + data-extraction functionality. The cloud R-engine credential is bundled in-package — zero user-side configuration. / 基于 R 的全方位 Meta 分析技能，覆盖 RevMan + Stata 等价 + esc + RVE + 贝叶斯 NMA + 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta等共 23 种分析图形。所有分析提供可复现 R 代码。还可提供Meta选题方向判断 + 文献检索整理 + 筛选 + 数据提取功能。云端 R 引擎凭证随包分发，零用户侧配置。"

required_commands: [python]
invocable: true

triggers:
  - "meta分析"
  - "meta-analysis"
  - "系统评价"
  - "森林图"
  - "漏斗图"
  - "异质性"
  - "发表偏倚"
  - "元回归"
  - "network meta"
  - "贝叶斯meta"
  - "效应量转换"
  - "TSA"
  - "诊断meta"
  - "full meta pipeline"
permissions:
  scope: "user-space-only"
  network: required
  network_note: "All numerical computation runs on the coze cloud R engine; analysis params/summary stats are POSTed to coze. No local-R fallback (paid-only feature); IPD only if the user explicitly opts in. The cloud-engine credential is bundled in-package — no user-side API key configuration is ever required."
  filesystem: "writes only to the current working directory (meta_analysis/ and output/ report artifacts: generated .R scripts, .svg/.png figures, .csv tables); otherwise read-only"
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "workbench_url": "https://meta.app.workbuddy.host/",
    "workbench_url_alias": "https://meta.app.workbuddy.link/",
    "workbench_domain_prefix": "meta",
    "workbench_domain_note": "Registered exception to the ct-base iron rule (2026-09-16): simplified prefix 'meta' instead of the skill name. Whitelisted, do not extend.",
    "workbench_app_id": "wbapp_hNZl928SI6wByvJt2COtcC",
    "workbench_owner_workspace": "2026-09-17-09-54-01",
    "workbench_sandbox": "a3c70e48be8f45019845b76383334bfc",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "netmeta", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear", "forestploter"],
  }
---

# Meta-Analysis

> R-based comprehensive meta-analysis. Every module ships reproducible R code.

## Language

- **English guide** → [README.md](https://github.com/medstatstar/meta-analysis/blob/main/README.md) · **中文指南** → [README_zh-CN.md](https://github.com/medstatstar/meta-analysis/blob/main/README_zh-CN.md)
- Bilingual auto-switch: the answer language follows the user's question language (English question → English answer, Chinese question → Chinese answer).

## 0. Execution discipline (speed-first)

> 🚀 **Top-level red line — higher priority than any "thinking/polishing" impulse. Violation = wasting the user's time.** Full boundaries/exceptions/anti-patterns in `references/speed-discipline.md`.

### Two-track gating (code-driven routing, no LLM decision)
The first message goes through `python scripts/classify.py` for **deterministic triage** (zero LLM decision):
- **Compute track (compute)**: clear Simple / Complex → describe and immediately run `run_meta.py --query --data`; three steps to completion, fully bound by this discipline.
- **Topic track (topic)**: vague / topic selection / feasibility → **first run `scripts/topic_gate.py`** to route on ct-literature install status (installed → call ct-literature directly; not installed → AskUserQuestion install-vs-simple, simple = ct-search remote `adapters/ctsearch_client.py search`), then `generate_topic_report.py`; code-grounded, zero free-form improvisation.
- Both tracks forbid reading source via Read/Grep/Bash to "confirm how to tune / which task to use" — that is `classify.py`'s job.

### Agent operation card
The compute-track one-shot command card lives in `references/agent_operation_card.md` — copy it verbatim (no variations); do NOT use it for the topic track. SKILL.md itself stays CLI-free per ct-base `docs/01-spec-scaffold.md` §4 (migrated 2026-10-20, audit P2-1).

### Six iron rules
1. **Execute, don't think**: when running the skill, only perform the workflow; no reasoning/trade-off/review/self-explanation; if a field is missing, ask only about that field.
2. **Zero number rewriting**: cite `stats`/`pooled`/`heterogeneity`/`bias` verbatim; no rounding/conversion/re-formatting.
3. **HTML report is the sole presentation surface**: `out['html_report']` is the final deliverable; no further processing; inline `show_widget` is deprecated, figures only appear in the HTML.
4. **Coze is the sole source of truth for computation**: all numerical analysis/computation runs on the coze R engine; the local side keeps only orchestration + send/receive and retains no compute engine. If coze is unreachable/unauthorized, raise a structured error per §6 — never fall back to local. (Consequence: without coze authorization the skill cannot compute — this is intended, as it supports paid-only features.)
5. **Call-count invariant**: compute track ≤1 call before fire (only `build_request`), ≤1 call after fire (only `present_files`); topic track ≤2; no retry loops. Cross-turn `--data-json` refill is input construction and does not count.
6. **No duplicate fire**: once `run_meta.py` is in-flight (the Bash call has been issued), **wait for the result** — do NOT re-issue the same or equivalent command. If `META_STATUS=error`, follow the structured guidance; do NOT silently retry. If `META_HTML_REPORT=...`, pass to `present_files` — done. One command, one wait, one result.

### Already automated / anti-patterns
Subgroup columns auto-pass-through, column-name aliases auto-matched, artifact completeness guaranteed by `run_analysis` — the agent must not read source to verify, must not hand-assemble subgroup into request.json, must not declare "missing Q_between" each round.

**❌ Impatient duplicate fire (2026-09-17 field incident):** re-issuing `run_meta.py` before the previous call returns wastes coze compute and burns rate limits. Full anti-pattern list → `references/speed-discipline.md`.

## 1. Triage — First step: classify the user's intent

> **Routing is already done in code (§0 two-track gating)**: track / task judgment is delegated to `build_request.py` (which calls `classify.py`); the LLM no longer makes routing decisions and does not hand-write request.json. The table below is for understanding only — the LLM calls `run_analysis` directly from the generated `request.json` and `present_files(html)`.

| Classification | Condition | Action |
|---|---|---|
| **Simple** | Single, specific intent (e.g., "pool OR from these 5 studies") | Reply directly, no menu |
| **Complex** | Multi-decision / multi-parameter (e.g., "network meta with 3 interventions, subgroup, check inconsistency") | Present level-1 routing menu incl. "③ Can't decide? → explain the differences"; full menu → `references/interactive_menu.md` |
| **Vague** | Unclear what user wants (e.g., "I need meta-analysis help") | Grill-me branch questions, 1–3 per round; "no topic / feasibility" → **Topic Selection** (§2.2) |

If unsure between Simple and Complex → give short reply + optional expansion hint.

## 2. Conversation guide

### 2.1 Interactive menu
Vague → Level 1 menu (7 categories). Select → Level 2 with data-format hints. Sufficient info → skip menu, run directly. Full menu tree + data formats → `references/interactive_menu.md`.
> **Menu = workbench framework alignment (2026-10-27)**: menu categories mirror the published workbench's five modules (Topic Assessment / Literature Prep / Meta Analysis / Sample Size (in dev) / Manuscript). Entries with **no engine backing** (ROBINS-I, RoB traffic-light plot, inconsistency heatmap, AI screening, PDF batch download, figure digitization, missing-data imputation) are **removed** — do NOT offer them in chat and do NOT attempt the call (R engine returns `unknown_task`).
> **⛔ Manuscript/writing module DISABLED in conversation (2026-10-27, user-decided)**: Block C (C1 draft / C2 AI review / C3 ref verification / C4 evidence QA) and the local writing-advisor are workbench-surface only for now. Do NOT offer manuscript drafting / submission advice in chat; do NOT invoke `writing_advisor` (no `advise=True`). Unfreeze = restore the triggers + remove this banner.
> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

### 2.2 Topic Selection (upstream gate, self-contained)
Trigger: no topic / feasibility check / "rejected as duplicate" / pre-PROSPERO audit → `references/topic-selection.md`. Two paths:
- **Quick** (≤30 min): 1-page decision card — 4-dim scores (clinical/feasibility/data/novelty, 0–5, any ≤2 = veto) + screen verdict.
- **Full** (5 stages + gates): PICO (`pico-guide.md`) → scoring + cross-checks R1–R6 → dedup (`dedup-search.md`) → PRISMA 2020/AMSTAR-2 (`compliance-precheck.md`) → 11-section report via `python scripts/generate_topic_report.py input.json output.md|html` (templates → `topic-report-template.md` / `prospero-mapping.md`).
- **Dedup source is gate-driven (see Topic Gating in `topic-selection.md`)**: first run `scripts/topic_gate.py`; if **ct-literature** is installed, call it directly for full 6-source retrieval (`.merged.json` as Stage-4 evidence); if not installed, AskUserQuestion → simple-analysis branch calls the **ct-search remote** (`adapters/ctsearch_client.py search --source europepmc`, no install needed); in-skill `adapters/literature_probe.py` (direct Europe PMC) is only the offline ultimate fallback. All paths return real `hit_count` + titles; novelty ranking grounded in actual literature.
  - ⛔ **Topic-track red line**: candidate ranking **must** be based on the probe's real hit counts + 4-dim score card; the LLM only paraphrases, strictly no free-form "which direction is good". Quick is ranked by the probe card; Full is reported by `generate_topic_report.py`, the LLM does not rewrite.
- **检索前置一致性（2026-10-25，对齐工作台）**: the topic track must (a) collect P/I/C/O/S as **five separate structured dimensions** with concrete examples up front (not a "P:… I:…" free-text sentence — the dimension letters are labels, not part of the value), (b) **translate the Chinese topic + PICOS to English and confirm** with the user before any probe/search (Meta检索基于英文库，Europe PMC / Cochrane / PROSPERO 只索引英文), and (c) build the dedup probe keyword / report `search_strategy` from the **confirmed PICOS-derived English query** (values only, drop the `P:/I:` dimension letters) — not the raw topic alone. Detail → `topic-selection.md` "检索前置门".

### 2.3 Upstream orchestration (retrieval → screening → extraction → analysis)

> **Repositioning (2026-08-30):** meta-analysis evolved from "pooling effect sizes only" into a "full-chain Meta orchestrator".
> The upstream three stages reuse existing modules and `ct-literature`; the only new capability is the **data-extraction assistant** (LLM draft + human-verification gate).

Full-chain orchestration, command list, seam pitfalls (incl. `included_records` ≠ `included`), and guard semantics → `references/upstream_orchestration.md`.
Evidence-upload (④″) and detailed A-stage contract / type-confirmation model → `references/chat_orchestration.md`. ~~Writing-advisor (④′)~~ → **DISABLED in conversation** (see §2.1 banner, 2026-10-27).

- ⛔ **Automatic PDF value extraction is SUSPENDED (2026-09-27, user-decided)**: `features.a4_extraction=False` gates off A4 auto 2×2 extraction; three backend bypasses (`/api/upload_pdf`, `/api/upload_pdf_auto`, fastpath `data_mode="pdf"`) return 409. Do NOT offer "auto-extract numbers from PDFs" as an available capability in chat. Unfreeze = set `a4_extraction: True` in `adapters/features.py`.

> ⚠️ **The human-verification gate is a red line:** any CSV from `extract_assist.py` not `stamp --confirm`ed is blocked by `run_meta.py` (`META_STATUS=unverified_extraction`).

### 2.4 Systematic-review full-flow mode (@skill entry)

> **Trigger:** "systematic review full flow" / "from retrieval to meta-analysis" / "systematic review workflow" → end-to-end orchestration, not a direct jump to compute track.
> The agent executes the full playbook → `references/systematic_review_fullflow.md`. CCM (Conversation Context Menu) is **DISABLED** for agent use (2026-09-27) — two execution surfaces remain: ① the **published web app** and  **plain conversation** (agent narrates + asks open questions in prose). Do NOT render `flow_menu.py` menus in chat.
> Archived CCM details (menu design, A1/A2 sub-menus, pre-flight checks, contract gaps) → `references/chat_orchestration.md`.
### 2.5 Workbench — published app & local launch

> **Trigger:** "工作台" / "workbench" / "meta 全流程" etc.
> Published app metadata, share link, appId, publish toolchain, local-launch commands → `references/workbench.md`.

## 3. Initialization & execution backend

**Execution model**: coze-only, absolute. Startup: probe `coze_client.health()`, create `meta_analysis/` + `output/`, read R config from `~/.workbuddy/MEMORY.md`. Details → `references/ADVANCED.md`.

## 4. Core functions & API

Module → R-package/function matrix → `references/advanced_api.md` · `references/ADVANCED.md`.
**Rule (mandatory)**: any analysis MUST call existing functions — never rewrite inline. Unified entry `adapters/run_analysis.py` (default: coze).

## 5. Output specification

**Artifacts**: `analysis_complete.R` + forest/funnel (`.svg`, inlined in HTML) + `results_summary.md` + `last_run.json`. Per-round dataset CSV is an *input* the agent carves; `run_analysis.py` does NOT auto-write `data_backup.csv`.

**Rendering**: `figures[].svg` embedded into single-file HTML report → `present_files`. Inline `show_widget` cancelled. SVG keeps natural width. Quality Gate: R-side `run_quality_gate()` → red (k<3 / I²>75% / missing bias check) **blocks** presentation.

**Cross-turn continuity (mandatory)**: stateless runtime → echo `## 当前分析设定 / Current analysis settings` after every analysis; follow-up changes only changed fields; dataset supplied per round (no `data_backup.csv`). Full spec + merge_spec + endpoint capability boundaries → `references/cross_turn.md`.

## 6. Security & scope

**Execution model**: numeric computation via coze. **Data-exfiltration decision belongs to the user**.

**Outbound disclosure**: analysis data (no PII) POSTed to coze, sanitized by `sanitize_payload()`. Default endpoint pre-approved; custom `COZE_META_ENDPOINT` asks AUTH-BLOCK on first call. First outbound notice each session (once, bilingual). Attribution never empty (`query_origin` hostname SHA-256 + `request_id` UUID). Coze failure needs consent before diagnose+retry.

**Other boundaries**: PDF download ONLY on explicit user instruction (`adapters/pdf_fetch.py`). Data-extraction guard (red line): `extract_assist.py` CSV blocked until `stamp --confirm`.

Full security details → `references/ADVANCED.md` · `references/pdf-download-portals.md` · `references/bug_report_endpoint.md`.

## 7. User-uploaded files

1. **Structured data (`.csv`/`.xlsx`/`.xls`)** → Type 4 template (`references/data_templates.md`).
2. **Document/template (`.docx`/`.pptx`/`.pdf`/`.doc`)** → convert to md first: `.docx`/`.pptx` via `scripts/office_to_md.py`; `.pdf` via `pdf` skill.

**🔔 Pre-conversion notice**: `⚠️ All uploaded documents will be converted to md. PPT conversion can lose images/layout/animations/charts.`

Full upload spec → `references/data_templates.md`.

## 8. Bug Reporting

Agent behavior only; implementation → `adapters/bug_report.py`, protocol → `references/bug_report_endpoint.md`. Trigger ≤1 proposal/session. Two-stage confirmation (propose-with-preview → consent → send). 11-key whitelist, never raw data.

## 8.5 Deploy Retest Gate (mandatory before publish / deploy)

**Freeze check FIRST**: before any publish attempt to GitHub → SkillHub → ClawHub, run `python adapters/publish_guard.py` — exit code 2 means a dev-period publish freeze is active (`adapters/DEV_POLICY.json`) and publishing is blocked; do NOT proceed and do NOT bypass it. This check is part of the gate, not optional advice.

**Mandatory before publishing / deploying** to GitHub → SkillHub → ClawHub: run `python tests/deploy_retest.py` (`--live` to actually hit the network; publish allowed only on all-green). This gate strictly verifies that the coze response is **genuinely valid** (HTTP 200 ≠ success; it rejects `status=ok` empty shells / `NaN` / no-figure (svg/url) false greens — coze externalizes SVG to S3 `url`, so a present+reachable `url` counts as a valid figure), writes `tests/deploy_retest_report.json`, and exits non-zero on any failure to block publishing. Use `--mock` for local logic self-check (no network) and `--offline` for envelope-contract validation. Full rules and red lines → `outputs/deploy_retest_gate.md`.

## 8.6 Workbench UI 细节自检（发布前必做，对齐 ct-base §21）

> 选题界面经多轮自动检查仍反复出现细节缺陷（提示文案与后端逻辑脱节、形似冗余的按钮静默丢弃 PICOS、开关名歧义、缺失维度占位无引导）。统一规范与机检清单见 ct-base `references/workbench_ui.md` §21。本技能工作台每次改动后，除 §8.5 的 coze 回归闸门外，还须过以下 UI 细节审计：

1. **文案对照代码**：主题框 / PICOS 相关提示若声称"系统会怎么做"（如"可直接写 P:…"），必须 grep `adapters/block_a.py:_infer_picos` 等后端逻辑并实测——meta-analysis 的 `_infer_picos` 只按分号切分、**不解析 P:/I: 标签**，故主题框提示不得诱导用户写标签（结构化入口是各页「PICOS 增强」折叠块）。
2. **相似控件读 handler**：结果页「✓ 确认 PICOS 并重新评估」(`confirmPicos`) 与「↻ 重新评估」(`reassess`) 必须各自核对读取的 DOM 范围——前者读 result、后者也须读 result（旧版 `↻` 静默丢弃 result 改动，已修复）；疑似冗余前先用真实输入证伪。
3. **标签自解释**：PICOS 中文对照开关名为「显示中英文对照」（非模糊的"中英对照"）。
4. **占位给示例**：缺失维度占位用 `PICOS_EG_ZH/EN` 示例（"例：…"），非"待填"。
5. **动态 DOM 真实浏览器实测**：以上均须经 Playwright 走完整交互路径后断言真实值（缺维态占位 = 示例、红框 class 存在、切语言后仍正确），禁止仅凭静态 grep 或 jsdom 结论。

Full methodology + 机检清单（红线 / 交付闸门 / 验收） → ct-base `references/workbench_ui.md` §21。

### 8.6.1 自动检查闸门（可执行，对齐 §21 机检目录）

> §21 的主要用途是**对 bug 做自动检查**，而非仅靠人工 review。机检引擎为 **ct- 家族通用引擎**：`ct-base/scripts/wb_detail_check.py`（零叶子硬编码），meta-analysis 随包持有其**字节一致的副本** `scripts/wb_detail_check.py` + 叶子专属 `scripts/wb_detail_check.rules.json`。任一 FAIL = 禁止交付。

- **运行**：`python scripts/wb_detail_check.py`（自动定位 `workbench.html` 与同目录 `wb_detail_check.rules.json`；或 `--html <path>` / `--root <dir>` / `--rules <path>`）。注意与 §18.3 的结构闸门脚本 `wb_ui_check.py`（C1–C7，带 `--set-version`）**分属不同脚本、勿混淆/勿互相覆盖**。
- **已实现的机检（§21.3.1）**：`C-detail-label`（模糊名 FAIL）、`C-detail-placeholder`（占位泛词 FAIL / 空态泛词 WARN）、`C-detail-claim`（输入语法类承诺 WARN→FAIL）、`C-detail-i18n-ph`（单语静态占位 WARN）、`C-detail-scope`（表单态 scope 覆盖 FAIL，rules 驱动）。
- **规则驱动、零引擎改动即可复用**：引擎不认识 meta 的任何 class；`scope.selectors=[".picos-in"]`、`scope.values=["seed","result"]` 等写在 `wb_detail_check.rules.json`，`enable` 逐项开启。`C-detail-dupctl` 已实现（rules `dupctl.pairs` 驱动）但本技能暂关——待两按钮补 `dup-verified:` 闭环后再开。
- **词表分层**：家族级默认词表内置引擎顶部常量；meta 特有追加走 rules.json 的 `*_add` / `i18n_whitelist_force`。
- **回归防御**：临时重新注入「中英对照」标签 +「待填」占位 → 判 2 FAIL + 1 WARN 拦截（exit 1）；真实 `workbench.html` → 0 FAIL / 0 WARN（含 scope，exit 0）。
- **实测兜底**（脚本不覆盖项）：动态 DOM / 相似控件静默丢数据 / 空态引导 等"无信号失败"仍须 §8.6 第 5 条 Playwright 真实浏览器实测断言。

## 9. Meta information

**Traceability**: all factual claims cite a `ref-*.md` section or official guideline; unverifiable → mark `⚠️ official verify`.
**References**: full index → `references/references.md`. Key: `interactive_menu.md`, `ADVANCED.md`/`ADVANCED_zh-CN.md`, `advanced_api.md`, `topic-selection.md`, `data_templates.md`, `svg_editing.md`. Units → `references/units.md`.
**Project Files**: `README.md` | `README_zh-CN.md` | `CHANGELOG.md` | `AGENTS.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`.
**Changelog**: → `CHANGELOG.md`.
