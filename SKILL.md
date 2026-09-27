---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: Meta Analysis / 医学Meta分析
version: 2.17.0
license: MIT
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan + Stata 等价 + esc + RVE + 贝叶斯 NMA + 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta等共 23 种分析图形。所有分析提供可复现 R 代码。还可提供Meta选题方向判断 + 文献检索整理 + 筛选 + 数据提取功能。
description: "Comprehensive R-based meta-analysis skill covering RevMan + Stata equivalents + esc + RVE + Bayesian NMA + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta, for a total of 23 analysis figures. All analyses ship reproducible R code. Can also provide meta topic-direction judgment + literature retrieval and organization + screening + data-extraction functionality. / 基于 R 的全方位 Meta 分析技能，覆盖 RevMan + Stata 等价 + esc + RVE + 贝叶斯 NMA + 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta等共 23 种分析图形。所有分析提供可复现 R 代码。还可提供Meta选题方向判断 + 文献检索整理 + 筛选 + 数据提取功能。"

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
  - "上下文菜单"
  - "对话菜单"
  - "全流程菜单"
  - "flow menu"
  - "论文撰写"
  - "写稿"
  - "初稿"
  - "投稿建议"
  - "发表建议"
  - "writing advisor"
  - "manuscript"
permissions:
  scope: "user-space-only"
  network: required
  network_note: "All numerical computation runs on the coze cloud R engine; analysis params/summary stats are POSTed to coze. No local-R fallback (paid-only feature); IPD only if the user explicitly opts in."
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

### Agent operation card (copy verbatim, no variations)
```bash
# Compute track one-shot: report lands in --out-dir (user workspace); in-conversation data uses --data-json to skip file writes.
# If data comes from a file, pass --data <csv|json absolute path> (csv auto-converts to JSON before sending to coze).
python scripts/run_meta.py --query "<user original request>" --data-json '<[{"study":"S1",...}]>' --out-dir "<user workspace>/meta_analysis"
```
Read `META_HTML_REPORT=<path>` from stdout and pass directly to `present_files`; across turns, carve a subset into a new csv/json and re-issue the same command (always include `--out-dir`). Do NOT use this card for the topic track. Fallback `META_STATUS=build_failed` → re-run with `--colmap` per the hint.

### Six iron rules
1. **Execute, don't think**: when running the skill, only perform the workflow; no reasoning/trade-off/review/self-explanation; if a field is missing, ask only about that field.
2. **Zero number rewriting**: cite `stats`/`pooled`/`heterogeneity`/`bias` verbatim; no rounding/conversion/re-formatting.
3. **HTML report is the sole presentation surface**: `out['html_report']` is the final deliverable; no further processing; inline `show_widget` is deprecated, figures only appear in the HTML.
4. **Coze is the sole source of truth for computation**: all numerical analysis/computation runs on the coze R engine; the local side keeps only orchestration + send/receive and retains no compute engine. If coze is unreachable/unauthorized, raise a structured error per §6 — never fall back to local. (Consequence: without coze authorization the skill cannot compute — this is intended, as it supports paid-only features.)
5. **Call-count invariant**: compute track ≤1 call before fire (only `build_request`), ≤1 call after fire (only `present_files`); topic track ≤2; no retry loops. Cross-turn `--data-json` refill is input construction and does not count.
6. **No duplicate fire**: once `run_meta.py` is in-flight (the Bash call has been issued), **wait for the result** — do NOT re-issue the same or equivalent command. If `META_STATUS=error`, follow the structured guidance; do NOT silently retry. If `META_HTML_REPORT=...`, pass to `present_files` — done. One command, one wait, one result.

### Already automated / anti-patterns (see `references/speed-discipline.md`)
Subgroup columns auto-pass-through, column-name aliases auto-matched, artifact completeness guaranteed by `run_analysis` — the agent must not read source to verify, must not hand-assemble subgroup into request.json, must not declare "missing Q_between" each round (go straight to metareg).

**❌ Impatient duplicate fire (2026-09-17 field incident):** Re-issuing `run_meta.py` with the same `--data-json` / `--data` before the previous Bash call returns. This does NOT speed things up — it wastes coze compute, burns rate limits, and pollutes the searchlog with phantom retries. If the Bash tool has been called, the agent MUST wait for its return before taking any further compute action.

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
> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

### 2.2 Topic Selection (upstream gate, self-contained)
Trigger: no topic / feasibility check / "rejected as duplicate" / pre-PROSPERO audit → `references/topic-selection.md`. Two paths:
- **Quick** (≤30 min): 1-page decision card — 4-dim scores (clinical/feasibility/data/novelty, 0–5, any ≤2 = veto) + screen verdict.
- **Full** (5 stages + gates): PICO (`pico-guide.md`) → scoring + cross-checks R1–R6 → dedup (`dedup-search.md`) → PRISMA 2020/AMSTAR-2 (`compliance-precheck.md`) → 11-section report via `python scripts/generate_topic_report.py input.json output.md|html` (templates → `topic-report-template.md` / `prospero-mapping.md`).
- **Dedup source is gate-driven (see Topic Gating in `topic-selection.md`)**: first run `scripts/topic_gate.py`; if **ct-literature** is installed, call it directly for full 6-source retrieval (`.merged.json` as Stage-4 evidence); if not installed, AskUserQuestion → simple-analysis branch calls the **ct-search remote** (`adapters/ctsearch_client.py search --source europepmc`, no install needed); in-skill `adapters/literature_probe.py` (direct Europe PMC) is only the offline ultimate fallback. All paths return real `hit_count` + titles; novelty ranking grounded in actual literature.
  - ⛔ **Topic-track red line**: candidate ranking **must** be based on the probe's real hit counts + 4-dim score card; the LLM only paraphrases, strictly no free-form "which direction is good". Quick is ranked by the probe card; Full is reported by `generate_topic_report.py`, the LLM does not rewrite.

### 2.3 Upstream orchestration (retrieval → screening → extraction → analysis)

> **Repositioning (2026-08-30):** meta-analysis evolved from "pooling effect sizes only" into a "full-chain Meta orchestrator".
> The upstream three stages reuse existing modules and `ct-literature`; the only new capability is the **data-extraction assistant** (LLM draft + human-verification gate).

Full-chain orchestration, command list, seam pitfalls (incl. `included_records` ≠ `included`), and guard semantics → `references/upstream_orchestration.md`.

- **④′ 论文撰写辅助（writing_advisor，2026-09-17 接通 C1）:** `adapters/writing_advisor.py`（论文撰写与发表建议引擎，2026-09-14 已建）现已接入 Block C 的 `c1_draft`——注入 strengths / limitations / discussion_template / reviewer_questions / journal_fit，并消费 A2 文献集做证据接地。C1 初稿由「千字骨架」升级为「已接地、待 LLM 扩写」的真实数据长稿（方法/结果填 PRISMA 流·PICOS·数据库·RoB；参考文献由 A2 DOI 落表交 C3 核验）；叙述性 prose（背景/讨论/结论/摘要）由编排层注入 LLM 经 `c1_expand_narrative` 扩写成完整可投稿初稿。下游 C2→C3→C4 红线闸不变。

- **④″ C1 自备文献上传（2026-09-22）:** `adapters/evidence_upload.py` + 工作台 C1 节点「初稿证据来源」面板。用户在 C1 可上传**自己收集/改过的文献清单**（`.xlsx/.xls/.csv/.tsv`，中英文列名均可；或 Zotero/EndNote 导出的 `.ris/.bib`、纯文本清单）或**PDF 打包**（`.zip` 内含 PDF，或直接多个 `.pdf`），解析成与 `literature_probe.search_evidence()` **同构**的 evidence dict（`primary`/`synthesis` 两层按设计类型切分）。证据优先级：**作者自备 > A2 文献集 > Europe PMC 自动检索**（`fullflow._run_block` C 分支），上传即自动回退重跑 C1。字段只取文件里真实写着的书目事实，缺作者/年份按 `Anonymous`/`n.d.` 处理并在提示条里报数，绝不臆造。Agent 上下文可直接 `import evidence_upload; evidence_upload.collect_uploads(paths)` 拿到同一结构。

- **① Direction judgment:** this skill's `references/topic-selection.md` + `adapters/literature_probe.py`; delegate cross-database retrieval to **ct-literature** when a full evidence base is needed (see §2.2 and orchestration doc §2).
- **② Literature retrieval & curation:** 100% delegated to **ct-literature** (`ct_literature.py` + multi-source dedup), output `.merged.json` / Excel / HTML; meta only orchestrates, no reinvention.
- **③ Literature cleaning (initial screening):** ct-literature `screen_prisma.py` machine pre-screen + this skill's agent layer per-record judgment (`review_workflow.md §2`); PRISMA diagram bridged via `scripts/prisma_bridge.py`.
- **③′ Doc-type confirmation (文献类型确认, 2026-09-10 重构；同日 A2/A3 合并):** 类型是 **A2「文献集」合并表（原 A3 初筛，2026-09-10 并入 A2）的人工确认字段**，不是判定门。链路：`ct-literature classify_record()` 规则预填（**单一真源，不在本技能内写第二套判定**）→ A2 导出表「文献类型确认」列由人工确认 / 改判 / 留空 → 回传后成为决策行的**一等字段**（含 `doc_type_source` / `doc_type_changed` / `doc_type_rule` 审计字段）→ **A4 只读**。
  - **人工确认之后，全链路不再判类型。** `pdf_extractor.extract()` 原规律 R1 短路返回已删除；A4 下载前类型门、上传快速通道、缓存分支的 `excluded_review` 分支均已移除；`review_summary.excluded` 恒 `False`。A4 **100% 按 A2 裁决清单下载**，不因类型跳过任何篇目。
  - **类型仅作标注（提示词）**：`doc_type` / `type_notice` / `review_note` 供核验参考。抽取层自行探测的类型降为 `doc_type_detected`，**仅在与确认值不一致时**提示人工，绝不改变裁决。
  - **要改类型必须人工确认或人工发起**（回 A2 重传合并表）——不存在自动改判路径。
  - 保留的两处类型判断均在**人工确认之前**（A2 review-guard 预填建议）或**纯提示位**（疑似综述徽标），不构成排除。
  - 历史背景：2026-09-09 曾以 `classify_pdf` 强制甄别并排除 review/guideline/protocol；该机制已于 2026-09-10 撤销（见 `CHANGELOG.md` §2.10.0）。
- **④ Data extraction [NEW]:** `scripts/extract_assist.py` generates a blank extraction sheet → agent/LLM reads full text and drafts → `validate` → human verification → `stamp --confirm`; `scripts/extraction_guard.py` blocks unverified data at the compute-track entry.
  - ⛔ **Automatic PDF value extraction is SUSPENDED (2026-09-27, user-decided)**: the workbench A4 node's auto 2×2 extraction (`pdf_extractor` path) is gated off by `features.a4_extraction=False` — A4 degrades to PDF-download-only (A3), and the three backend bypasses (`/api/upload_pdf`, `/api/upload_pdf_auto`, fastpath `data_mode="pdf"`) now return 409 while the switch is off. Do NOT offer "auto-extract numbers from PDFs" as an available capability in chat; users with data should use the raw-CSV fast path (upload their own `ai/bi/ci/di` or `te/sete` table) or the `extract_assist.py` human-verified flow below. Unfreeze = set `a4_extraction: True` in `adapters/features.py` (or `CT_FEATURE_A4_EXTRACTION=1`).
- **⑤ Meta computation:** existing `scripts/run_meta.py`; the extracted CSV passes through straight after guard verification.

> ⚠️ **The human-verification gate is a red line:** extraction accuracy in ④ is medically critical, and full-text access is restricted (paywalls) — **never auto-feed unattended**.
> Any CSV produced by `extract_assist.py` that is not `stamp --confirm`ed is blocked by `run_meta.py` (`META_STATUS=unverified_extraction`).

### 2.4 Systematic-review full-flow mode (@skill entry)

> **Trigger:** the user invokes this skill with intents such as "systematic review full flow" / "from retrieval to meta-analysis" / "systematic review workflow"
> (see frontmatter `triggers`) → enter end-to-end orchestration, not a direct jump to the compute track.

**This is meta-analysis's unified entry as an "orchestrator":** it chains direction judgment → retrieval & curation → initial screening + PRISMA → data extraction → pooled analysis into a pipeline **with human gates**. The agent executes the full playbook → `references/systematic_review_fullflow.md` (incl. Stage 0 startup confirmation, 5-stage command chain, two human gates, failure/boundary handling).

- **Orchestration discipline:** the upstream three stages (①②) reuse this skill + **ct-literature**; meta only orchestrates, no reinvention; the only new capability is ④ "data-extraction assistant (LLM draft + human-verification gate)".
- **Two non-skippable human gates:** Stage 3 final inclusion count (`included`, ≠ machine pre-screen's `included_records`), and Stage 4 extraction-draft verification (`extract_assist.py stamp --confirm`). Until a gate passes, the agent must not advance to the next stage.
- **Relationship to §0 two-track:** full-flow is end-to-end orchestration triggered by an explicit user intent; internally it still reuses the topic track (Stage 1) and compute track (Stage 5), and adds no new classify task class.
- **A-stage contract & type-confirmation model (2026-09-10, A2/A3 merged; 2026-09-11 menu restored to 4):** Block A = `A1 选题 → A2「文献集」(检索 + 初筛，单节点单表) → A4 数据提取`。A2 = file hand-off（**批准并下载 PDF**（触发 A4 自动落盘，本地 `pdf_dir` 优先）/ 改检索式 / 导出检查 / **传回修改后的合并表**（`apply_screening_upload` → `screened` 修订接缝接 ③））; A4 = downloads by that list 100%, **type read-only**. A2 批准后**复用检索缓存只跑下游**，不再整块重跑、不再作废 Excel。Details, environment facts, pending decisions and pitfalls → **`references/HANDOFF_2026-09-10.md`**.
- **⛔ Conversation Context Menu (CCM) — DISABLED for agent use (2026-09-27, user-decided):** the skill exposes exactly TWO execution surfaces: ① the **published web app** (`https://meta.app.workbuddy.host/`, §2.5) for menu-driven full-flow operation, and ② **plain conversation** (agent narrates the current stage/state and asks open questions in natural prose — approve / revise / rewind stated by the user in words; no rendered option menus). **Do NOT render `flow_menu.py` menus (L0 nav bar, L1 numbered option lists, or `flow_menu_widget.py` clickable widgets) in chat for any A/B/C node stop.** `scripts/flow_menu.py` + `scripts/flow_menu_widget.py` remain developer/CLI tooling and the state machine itself is unchanged — only the chat-side presentation is withdrawn. When a conversational run reaches a human gate, state where the flow stands and ask the question directly in prose, or point the user to the web app for guided operation. The sub-bullets below are kept as **archived reference** (menu design/rationale, for a future re-enable) — they must NOT be executed verbatim in chat while this banner stands.
- **Conversation context menu (CCM) — [ARCHIVED 2026-09-27, see banner above] implemented (2026-09-10):** in the full-flow track, **every stop renders a code-generated menu** (`scripts/flow_menu.py`); the LLM only relays it. L0 nav bar every turn, L1 node menu with **enumerated options** (≤3 → AskUserQuestion card, ≥4 → numbered text). Options are *derived from the state machine* — `_REDLINE_GATES` filters out `skip` on red-line nodes, `EDITABLE_KEYS` decides what is revisable — never hard-coded twice. Normative spec + acceptance evidence → **`references/conversation_flow_menu.md`**; design archive → `references/design/ccm/`.
  - `python scripts/flow_menu.py status|menu|nodes|decide|rewind|probe  [--session P] [--lang zh|en] [--json]` (verify: `python tests/test_flow_menu.py`, 182 PASS).
  - **A2 批准即出 Excel**：`decide --option 1 --apply` 于 A2（合并「文献集」节点）批准后自动落盘 `A2_文献集_<pid>.xlsx`（ct-literature `export_xlsx` 模板，**含裁决 / 理由 / 文献类型确认列**），路径回传在结果的 `artifacts`；实现见 `adapters/fullflow.py::_auto_export_on_approve` + `adapters/block_a.py::export_screening_xlsx`（失败不影响主流程）。
  - **上传入口（恢复，2026-09-11 二次裁定）**：A2 菜单 4 项——`[1] 批准并下载 PDF / [2] 改检索式 / [3] 导出检查（不改变状态）/ [4] 传回修改后的合并表`。`[4]` 识别到「裁决」列即按裁决表解析（`apply_screening_upload` → `screened` 修订），无裁决列视为文献清单整表替换；A1 仍不设上传入口（选题阶段上传表无意义）。
  - **A1 检索范围（第 3 项「改检索范围（综述 + 数据源）」）**：选题阶段可同时改两件事——① 综述纳入开关（`include_reviews`，原始研究-only ↔ 含综述类）；② **检索数据源增减**（`sources`，从可选池 `block_a.AVAILABLE_SOURCES` = OpenAlex / EuropePMC / bioRxiv / medRxiv / SemanticScholar / arXiv 中选子集，与 ct-literature `_SOURCE_DISPLAY` 单一真源一致）。**链路已实测打通**：A1 批准提交 → `run_block_a(sources=…)` → `a2_literature_search` → `a2_build_tool_card`（列表归一为逗号串写入 `params.sources`）→ `tool_mapping_meta.json` 的 `arg_map("sources"→"--sources")` → **ct-literature 新增的 `--sources` 参数**（逗号子集，覆盖各 `--with-*` 默认）。注意：`PubMed` 并入 EuropePMC、`Cochrane` 是 EuropePMC 的 journal-filter 子模式、OpenAlex 为基座不可关闭——均非独立可选源。A1 摘要「检索范围」行同步列出当前数据源。
  - **A1 可行性速览（2026-09-11 新增，第 4 项）**：选题阶段即可按需触发一次注册库探针（不跑整条检索管线），先看拥挤度 / 证据量 / 风险预警再放行 ②。agent 调 `python scripts/flow_menu.py probe --apply` → `a1_feasibility_probe` 跑 `block_a.a1_registry_check` 并写回 A1 `stage_result` 的 `registry_probe` / `feasibility`，菜单摘要随即补出「注册库探针」行。非状态机决策项，选题缺失时自动隐藏。
  - **A2 告警口径**：仅核心二源 `OpenAlex` + `EuropePMC`（`block_a.CORE_SOURCES`）决定 `search_status`；bioRxiv / arXiv / 无 key 的 Semantic Scholar 缺失**不降级、不告警**，原始 CLI 返回码留在 `coverage.cli_status` 供审计。
  - **[⛔ disabled 2026-09-27] Interactive (selectable) menu — was default in chat (2026-09-10):** render menus as clickable widgets, **not plaintext**. `python scripts/flow_menu_widget.py [--session P] [--lang zh|en] [--out FILE]` emits an HTML fragment that reuses `flow_menu.build_menu()` (single source of truth) → pass it to the Visualizer `show_widget`. Clicks only highlight + reveal the next command; the real decision still goes through `flow_menu.py decide --option N --apply`. → Do NOT call `flow_menu_widget.py` in chat anymore; chat = plain prose or the web app.
  - **Pure-arithmetic requests never see the CCM** (pooling / NMA / sensitivity stay "describe-to-run"). Operations needing visual/spatial information stay in the workbench (`/workbench` escape hatch).
  - **⚠️ Pre-flight before relaying a menu (2026-09-10, live-traffic finding):** sessions under `adapters/workbench/runs/` may predate the current contract, and the renderer will faithfully project their **stale** semantics. Verify four fields first — `await.gate` is a **gate-name string** (old format was boolean `true`), `per_doc[*]` has `doc_type_confirmed`, A2 rows have `doc_type_source`, `cursor.block` matches `stage_id`'s block. Any miss ⇒ legacy data: **never approve off it**, prefer re-running the stage with current code. Note: sessions created **before the A2/A3 merge** carry an independent `A3.screening` stage — the loader can still read its `screened`/`decisions` back, but the merged node will not re-emit A3. Two contract gaps found the same way — **D19** (A4 menu didn't expose `fetch_log`) is **fixed 2026-09-10** (`_a4_summary` now shows the `gate` distribution); **D18** (A4 `max_attempts=12` quota silently defers 45/59 with no "run next batch" entry) is **still open** → `references/conversation_flow_menu.md` §8; spec §7.1 has the detail.

### 2.5 Workbench — the HTML interactive frontend for full-flow

> **Positioning:** `adapters/workbench/` holds the full workbench frontend (`workbench.html`, three-column layout) + backend (`server.py`) + launcher (`launch_workbench.py`).
> **Trigger:** the user mentions "工作台" / "workbench" / "meta 全流程" etc.

**Published application (WorkBuddy Sites):** The workbench is published as a WorkBuddy online app. **When re-publishing, always reuse the existing `appId` to keep the share link stable — never create a new app.**

> 🔴 **Registered exception to the ct-base iron rule** (2026-09-16, user-decided): every other skill publishes to
> `https://<skill-name>.app.workbuddy.host/`, but this skill's link is the **simplified** `https://meta.app.workbuddy.host/`
> (`domainPrefix = meta`, not the skill name). User's words: "但名称是简化的，**这个是特例**". This is the **only**
> whitelisted exception — see ct-base `references/workbench_ui.md` §13.0.1.

| Item | Value |
|---|---|
| Share link | `https://meta.app.workbuddy.host/` (same-host alias: `https://meta.app.workbuddy.link/`) |
| domainPrefix | `meta` — **simplified, whitelisted exception** (iron rule would say `meta-analysis`) |
| appId | `wbapp_hNZl928SI6wByvJt2COtcC` |
| sandboxId | `a3c70e48be8f45019845b76383334bfc` |
| Owner workspace | `2026-09-17-09-54-01` — holds `.wbapp_hNZl928SI6wByvJt2COtcC.genie` |
| Metadata record | `adapters/workbench/app.config.json` (ct-base §16.12.1; excluded from the published package) |
| Runtime | Python (`pip install -r requirements.txt` + `python main.py`) |
| Deploy directory | `meta-workbench-app/` (staging payload: `main.py` + `adapters/` + `scripts/` + `requirements.txt`) |
| Publish toolchain | `adapters/workbench/publish-kit/` — `build_publish.py` (rebuilds the payload), `install_genie.py` (mints/installs `.wbapp_<appId>.genie` + the `applications.yaml` entry so re-publishing keeps the same share link), `check_py311.py`, `smoke_e2e.py`. **Infrastructure, not a deploy source** — excluded from every outbound artifact. |
| ⛔ Deleted 2026-09-22 | `publish/` · `publish-backup/` · `publish-backup.rar` · `publish-preclean-20260917/` — frozen historical snapshots of the skill tree (~72 MB, untracked, **zero code references**). They predated `topic_translate.py` / `evidence_upload.py` / `reasons_en`, so they *looked* deployable but would have shipped the old version. Removed after the 2026-09-22 consistency audit (P2-12). Rebuild the payload any time with `python adapters/workbench/publish-kit/build_publish.py`. |

> ⚠️ **appId 认领地**: the deploy tool only accepts an `appId` whose `.wbapp_<id>.genie` marker exists in the **current**
> workspace. This app is registered in **`2026-09-17-09-54-01`** (verified 2026-09-22: `.wbapp_hNZl928SI6wByvJt2COtcC.genie`
> lives there). The previously documented workspace `2026-09-14-14-30-18` **no longer exists** — re-publishing from any
> workspace without the marker is rejected and would force `createNewApp` → a **suffixed** domain (e.g. `meta-02857`),
> which is a deviation, not an option. If the marker workspace changes again, locate it with:
> `ls -d ~/WorkBuddy/*/ | xargs -I{} sh -c 'ls {}/.wbapp_hNZl928SI6wByvJt2COtcC.genie 2>/dev/null'`

```bash
# Re-publish (update existing app — link unchanged)
# Must run from workspace 2026-09-17-09-54-01 (where the .wbapp_*.genie marker lives)
# workbuddy_sites_deploy with appId=wbapp_hNZl928SI6wByvJt2COtcC, domainPrefix=meta
```

```bash
# Launch the workbench locally (default 127.0.0.1:8765, auto-opens the browser)
python adapters/workbench/launch_workbench.py

# Or start the backend manually
cd adapters/workbench && coze/.venv/Scripts/python.exe -m uvicorn server:app --host 127.0.0.1 --port 8765
```

After launch, open the workbench in the preview panel with `present_files(["http://127.0.0.1:8765"])`.

### Workbench capabilities added 2026-09-22 (web ⇄ agent parity)

| Capability | Web | Agent / CLI context |
|---|---|---|
| 研究主题中→英自动翻译（喂 Europe PMC） | ✅ 选题速览 & C1 自动翻译并展示检索式（`adapters/topic_translate.py`，缓存 + 多端点降级） | same engine; agent may pass `topic_en` explicitly |
| 选题可行性速览文案 | 「先帮我选题」；探针失败显示「暂不可达 + 原因 + ↻ 重试」 | `flow_menu.py ... probe` |
| 演示模式（无 B 信封直接跑 C） | ✅ 三级兜底（粘贴 → 上传 → 内置示例）；页面有常驻「⚠ 演示数据」角标 | `block_b.demo_b_env()` |
| C1 上传作者自备文献 | ✅「初稿证据来源」面板（xlsx/csv/tsv / RIS / BibTeX / txt / zip / pdf） | `adapters/evidence_upload.py collect_uploads(paths)` |
| 软停「跳过本步确认」 | ✅ (2026-09-22 恢复显示) | ✅ CLI 菜单 `skipped` |
| 节点可修订字段 | 由 `await.editable_payload`（= `fullflow.EDITABLE_KEYS`）自动渲染；无专用面板的键给通用编辑框 | CLI 修订项同样由 `EDITABLE_KEYS` 派生 |

**Single source of truth for "what is editable at stage X"** = `adapters/fullflow.EDITABLE_KEYS`.
Both the web (`editable_payload` → generic panel) and the CLI menu derive from it — do **not** add a second list.
The workbench backend reuses the fullflow HITL state machine (red-line checks preserved verbatim); the frontend shows real-time progress and human-gate interactions across direction judgment → retrieval → screening → extraction → computation.

## 3. Initialization & execution backend

**Execution model (coze-only, absolute)**: all numerical computation runs through the coze meta-analysis workflow (R engine on coze side); local LLM only normalizes request + presents results/SVG. End users need no R install. Every analysis returns a `repro` field (R script + versions). **Coze = sole computation source of truth; the local side retains no compute engine; no coze authorization ⇒ no computation (paid-feature model) — see §0 iron rule 4.**
**On startup**: 1. Backend default `https://ct-meta.coze.site/run` (primary; fallback `https://ct-meta2.coze.site/run` on failure; override `COZE_META_ENDPOINT`); probe via `coze_client.health()`. 2. Workspace: create `meta_analysis/` + `output/`. 3. Memory: read R config from `~/.workbuddy/MEMORY.md` (R only).
Endpoint self-test / R engine details → `references/ADVANCED.md` · `references/ADVANCED_zh-CN.md`.

## 4. Core functions & API

Module → R-package/function matrix → `references/advanced_api.md` · `references/ADVANCED.md`.
**Rule (mandatory)**: any analysis MUST call existing functions — never rewrite inline. Unified entry `adapters/run_analysis.py` (default: coze). List + examples → `references/advanced_api.md`.

## 5. Output specification

**Artifacts**: `analysis_complete.R` + forest/funnel (`.svg`, inlined in HTML) + `results_summary.md` + `last_run.json` (full request+result echo, in `output/`). Per-round dataset CSV is an *input* the agent carves (e.g. `filtered_mdd.csv`); `run_analysis.py` does NOT auto-write `data_backup.csv`.

**Rendering (HTML report sole surface)**: `figures[].svg` embedded into the single-file HTML report (`run_analysis`→`out['html_report']`), opened with `present_files`. Inline `show_widget` cancelled; SVG keeps natural width (never upscale to 680px; overflow scrolls). S3 offloading is transport-only — `_coze_truncated` present → truncation warning atop report.
**LLM presentation hard constraints**: ① numbers verbatim (stats/pooled/heterogeneity/bias, no rewrite); ② figures only via HTML report.
**Quality Gate**: R-side `run_quality_gate()` → gate JSON; red (k<3 / I²>75% / missing bias check) **blocks** presentation until manual confirmation. Numeric judgment by R, never read by LLM.
figure_mode / render-timing → `references/ADVANCED.md`; inline/figure spec → `references/inline_rendering.md`.

## 5.1 Cross-turn Continuity (mandatory)

> **Runtime is stateless.** coze R engine re-supplies `task`+`data`+`params` each call, never persists config/column mapping. Semantic drift (model/method silently changing) = highest-risk failure.

#### Cross-turn spec (minimal unit maintained within the conversation thread)
```
{"task":"pairwise_meta","data_path":"<current-round csv>","measure":"OR","model":"random","method":"REML","subgroup":"—"}
```
(yi/sei/slab column mapping is already auto-derived by `build_request.py`; no explicit inheritance needed; `run_meta.py` is self-sufficient from query+data each time.)

#### Three hard rules
1. **Echo a "当前分析设定 / Current analysis settings" block after every analysis (mandatory, after this round's numbers/figures):**
   `## 当前分析设定 / Current analysis settings: data=<csv> | measure=OR | model=random | method=REML | subgroup=— | task=pairwise_meta`
   Bilingual header (Chinese first, then English, separated by ` / `) is mandatory; field keys stay English (machine-readable for follow-up parsing). No field omitted (`—` placeholder) — lets LLM locate "most recent settings" on follow-up.
2. **On follow-up, change only the changed fields:** locate most recent `## 当前分析设定 / Current analysis settings:` block (match by either Chinese or English token), read all fields, override only what changed (e.g. `task←subgroup_analysis`, `subgroup←region`); yi/sei/slab + model/method/measure inherited verbatim — dropping column mapping = effect-size mismatch.
3. **Dataset supplied per round, not by magic pointer:** no auto `data_backup.csv`; carve subset into new csv + re-issue `run_meta.py` at it.

#### Deterministic fallback
Worried about dropping config? `scripts/merge_spec.py` (prev+cur via stdin → merged spec):
```bash
echo '{"prev":{"task":"pairwise_meta","data_path":"<csv>","measure":"OR","model":"random","method":"REML","subgroup":"—"},"cur":{"task":"subgroup_analysis","subgroup":"region"},"required":["task","data_path","measure","model","method","subgroup"]}' | python scripts/merge_spec.py
```

#### Endpoint capability boundaries (per coze `run_task.R` / `coze_contract.md` §3)
- `pairwise_meta` ✅ complete (I²/τ², Egger/Begg, funnel plot, quality gate)
- `subgroup_analysis` ✅ subgroup column **must** be passed as the param key `subgroup` (writing byvar/group/by silently fails)
- `metareg` ✅ requires effect-size columns te/sete + covariate column `params.cov` (passing only raw columns degrades to pairwise_meta)
- `nma` ✅ (≥2 arms per study); `nma_rank` ✅ (SUCRA/P-score); `survival_meta` ✅ (loghr/seloghr); `diagnostic_meta` ✅ (tp/fp/fn/tn, task name is not "diagnostic")
- **Network diagnostics + CINeMA (2026-09-14)** — `nma` / `nma_rank` / `cnma` additionally return network heterogeneity (`stats.heterogeneity`: `tau`/`tau2`/`I2`/`Q`/`df`/`p`; **previously `null`**), `stats.extra.network` (interventions / comparisons / studies / designs, plus `prop_direct` for **all three** network tasks) and `stats.extra.inconsistency` (design-by-treatment interaction test `Q`/`df`/`p` + per-comparison direct-vs-indirect differences for locating the source). ⚠️ `I2` is **always a percentage (0–100)** — netmeta's native 0–1 ratio is converted engine-side; do not convert again. ⚠️ `stats.k` / `extra.network.n_studies` / `extra.network.n_comparisons` count **unique** studies and **unique** comparison pairs (deduplicated by `studlab` / treat-pair) — **not** data rows; arm-based multi-arm studies expand to C(n,2) rows, so the old row-count reading over-reported both (self-audit fix, 2026-09-14). The interpretation layer routes network results to a dedicated branch and the quality layer assesses them with the **CINeMA six domains** (within-study bias / reporting bias / indirectness / imprecision / heterogeneity / incoherence) instead of plain GRADE — a domain short of data is reported `unclear`, **never silently treated as "no concern"**. Reading guide → `references/component_nma.md` §CINeMA.
- `rob2` ✅ (RoB2 / RoB traffic-light, self-drawn ggplot — no robvis dependency) and `rob_summary` ✅ (stacked-bar summary); `prisma_checklist` ✅ (PRISMA 2020, 27 items) and `prisma_flow` ✅ (four-stage diagram via `metagear::plot_PRISMA`); `grade` ✅ (GRADE certainty); `tsa` ✅ / `power` ✅ / `nnt` ✅ / `gosh` ✅ / `ipd_meta` ✅ / `metainc` ✅
- `cnma` ✅ **component network meta-analysis (additive model)** — built on `netmeta::netcomb()` / `discomb()`, **no extra dependency** (netmeta 3.6.1 on both local and cloud). Treatment labels encode components via `sep_comps` (single character, default `+`, e.g. `A+B`; inner spaces auto-trimmed); disconnected networks auto-route to `discomb()`. Returns component effects (`stats.extra.components`), combination effects (`stats.pooled`), the **additivity test** (`stats.extra.additivity`: `Q_diff`/`p_diff` — non-significant means the additive assumption is acceptable), the component design matrix (`stats.extra.design`) and the unidentifiable-components list (`stats.extra.unidentifiable`). **Unidentifiable components return `null`, never `0`**; degrees of freedom ≤ 0 (untestable) also yield `null` instead of a floating-point artefact. Params: `sep_comps` / `inactive` / `interaction` / `reference_group`; consumes `params.sm` (same as `nma`). Methodology, reading the additivity test, and pitfalls → `references/component_nma.md`.
- publication bias is embedded in pairwise_meta/funnel_plot; `sensitivity`/`pub_bias` are not registered tasks
- default figures adapt to the task (`build_request` requests per `figure.plots`; override via `params_extra.plots`)
> Few-shot samples → `references/interactive_menu.md` §6.

## 6. Security & scope

**Execution model**: numeric computation via coze (LLM only normalizes + presents; numbers judged by R). **Data-exfiltration decision belongs to the user** — skill implements function + transparent disclosure, never a compliance gate.

**Outbound disclosure (global mandatory)**:
- **What is sent**: analysis data (event counts / sample sizes / effect sizes; no PII) POSTed to coze; sanitized by `sanitize_payload()` (strips ID/phone/email) first.
- **Authorization**: default endpoint pre-approved in whitelist; custom `COZE_META_ENDPOINT` asks AUTH-BLOCK on first call, then whitelisted. Unauthorized → `_source=auth_blocked` with "cloud analysis not used" message.
- **First outbound notice each session (once, bilingual)**: `I will send your analysis parameters to the cloud service https://ct-meta.coze.site/run for computation, together with a hostname hash (query_origin, for attribution/rate-limiting only). Please wait…` No repeat.
- **Attribution is never empty (v2.2.28)**: every outbound call carries `query_origin` (hostname SHA-256) and a `request_id` (UUID) — generated inside `coze_client`, so direct callers (self-test entry, integration test, `deploy_retest --live`) can no longer emit blank-attribution traffic that silently bypasses rate limiting. Debug/smoke calls add a `debug:` prefix plus `_debug: true`, so they are filterable in the log table. Identical requests within `COZE_META_DEDUP_WINDOW` (default 60 s) reuse the previous result instead of calling coze again.
- **Ct-base coze contract fields (2026-09-11)**: outbound envelopes also carry `skill_version` (**top-level**, read from `SKILL.md` frontmatter `version:` — never nested inside `params`/`report`) and `params.user_language` (`zh`/`en`, a caller hint for the coze-side copy language — **single carrier in `params`**, never double-written at top level), per `ct-base/references/coze_io_contract.md §1.1/§1.2`. Both are Optional/backward-compatible. Scope note: **one logical retrieval can fan out to several coze calls** — the A2 literature leg delegates to ct-literature, which issues one `/stream_run` POST **per source** (~4–5 by default, +1 feishu-summary call; each may fall back to `/run`). That fan-out is by design (`dispatch(source=…)` is single-source, no batch envelope); the meta-analysis R-engine path is one call per stage, guarded by the 60 s dedup window.
- **Coze failure needs consent**: on failure/timeout, first ask (bilingual) `The coze cloud service is temporarily unavailable. May I automatically diagnose the issue?`; allowed → diagnose+retry; declined → deliver a textual reply explaining cloud analysis was not performed (a no-computation message — **never** run R/Python locally to substitute).

**Other boundaries**: PDF full-text download ONLY on explicit user instruction (`adapters/pdf_fetch.py`, opt-in). Not clinical judgment. No literature DB search (downloads full text only when user provides DOI/PMID). Download-entry classification (Unpaywall/Europe PMC core/OA-repo templates/publisher-page/signed-link/paywall, plus anti-scrape boundaries) → `references/pdf-download-portals.md`.
- **Data-extraction guard (red line)**: the upstream data-extraction assistant (`scripts/extract_assist.py`) is human-in-the-loop only. Any extraction CSV it produces stays `verified_by_human=NO` until a human runs `extract_assist.py stamp --confirm`; `run_meta.py` (via `scripts/extraction_guard.py`) blocks unverified extraction CSVs with `META_STATUS=unverified_extraction`. Full-text retrieval and extraction accuracy are human responsibilities — never auto-feed extracted numbers into the compute track without verification.

## 7. User-uploaded files

1. **Structured data (`.csv`/`.xlsx`/`.xls`)** → Type 4 template (`references/data_templates.md`: encoding / zh-en column match / missing-value / row-count).
2. **Document/template (`.docx`/`.pptx`/`.pdf`/`.doc`)** → convert to md first: `.docx`/`.pptx` via `scripts/office_to_md.py`; `.pdf` via `pdf` skill (OCR for scans); `.doc`/scans → ask user for text version.
**🔔 Pre-conversion notice (bilingual)**: `⚠️ All uploaded documents will be converted to md. PPT conversion can lose images/layout/animations/charts. We recommend converting yourself and checking first.`
**Confidentiality**: skill never proactively judges/blocks upload confidentiality; whether IPD goes to coze is the user's call.

## 8. Bug Reporting

Agent behavior only; implementation → `adapters/bug_report.py`, protocol → `references/bug_report_endpoint.md`.
- **Trigger (≤1 proposal/session):** unexpected non-zero exit / engine error / user questions result — **and** retried ≥1. Explicit "report a bug" also triggers (no limit).
- **Two-stage confirmation:** ① propose-with-preview (bilingual `confirm_prompt` + full sanitized report) → ② on consent `send_to_endpoint` (`https://ct-bugreport.coze.site/run`). Declined → never re-propose.
- **Sanitization hard:** 11-key whitelist only, never raw data/subject records; `description` is the only free-text field, user-reviewed. No cloud call → `save_local_report()` (stays local).

## 8.5 Deploy Retest Gate (mandatory before publish / deploy)

**Freeze check FIRST**: before any publish attempt to GitHub → SkillHub → ClawHub, run `python adapters/publish_guard.py` — exit code 2 means a dev-period publish freeze is active (`adapters/DEV_POLICY.json`) and publishing is blocked; do NOT proceed and do NOT bypass it. This check is part of the gate, not optional advice.

**Mandatory before publishing / deploying** to GitHub → SkillHub → ClawHub: run `python tests/deploy_retest.py` (`--live` to actually hit the network; publish allowed only on all-green). This gate strictly verifies that the coze response is **genuinely valid** (HTTP 200 ≠ success; it rejects `status=ok` empty shells / `NaN` / no-figure (svg/url) false greens — coze externalizes SVG to S3 `url`, so a present+reachable `url` counts as a valid figure), writes `tests/deploy_retest_report.json`, and exits non-zero on any failure to block publishing. Use `--mock` for local logic self-check (no network) and `--offline` for envelope-contract validation. Full rules and red lines → `outputs/deploy_retest_gate.md`.

## 9. Meta information

**Traceability**: all factual claims cite a `ref-*.md` section or official guideline; unverifiable → mark `⚠️ official verify`.
**References**: full index → `references/references.md`. Key: `interactive_menu.md`, `ADVANCED.md`/`ADVANCED_zh-CN.md`, `advanced_api.md`, `topic-selection.md`, `data_templates.md`, `svg_editing.md`. Units → `references/units.md`.
**Project Files**: `README.md` | `README_zh-CN.md` | `CHANGELOG.md` | `AGENTS.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`.
**Changelog**: → `CHANGELOG.md`.
