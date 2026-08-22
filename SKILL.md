---
name: meta-analysis
cn_name: 医学Meta分析
slug: meta-analysis
displayName: 医学Meta分析 / Meta Analysis
version: 1.12.2
summary: 基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。
license: MIT
description: "基于 R 的全方位 Meta 分析技能，覆盖 RevMan 全部功能 + Stata 等价（metareg/mvmeta）+ esc + RVE + 贝叶斯 NMA（Stan/JAGS）+ 生存 Meta + TSA + 单组率 Meta + 诊断 Meta + 系统评价流程；输出森林图、漏斗图、异质性(I²)、发表偏倚、亚组分析、元回归、网络 Meta。中英双语自动切换（默认英文/中文环境切中文），所有分析提供可复现 R 代码。 / Comprehensive R-based meta-analysis skill covering RevMan 5.x + Stata equivalents (metareg/mvmeta) + esc + RVE + Bayesian NMA (Stan/JAGS) + survival meta + TSA + single-group meta + diagnostic meta + systematic review workflow; produces forest plots, funnel plots, heterogeneity (I²), publication bias, subgroup analysis, meta-regression, network meta. Auto-switches language (defaults to English, switches to Chinese in zh-* environments). All analyses ship reproducible R code."

required_commands: [Rscript, python]
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
  - "网络meta"
  - "network meta"
  - "贝叶斯meta"
  - "效应量转换"
  - "单组率meta"
  - "TSA"
  - "诊断meta"
  - "上报bug"
  - "report a bug"
  - "错误报告"
permissions:
  scope: "user-space-only"
  network: "optional"
  network_note: "Default compute path is the coze cloud R engine (requires network). A fully local R fallback (adapters/coze_project) is available ONLY if the user installs R + 14 packages locally — so network is optional only when local R is present; most end-users run via coze. Network is also touched if the user explicitly requests PDF full-text download from DOI/PMID lists (external services), which requires opt-in confirmation of the target list."
  filesystem: "writes only to the current working directory (meta_analysis/ and output/ report artifacts: generated .R scripts, .svg/.png figures, .csv tables); otherwise read-only"
  data: "no external data transmission. R package installation is never performed by this skill — if the user installs packages, that is a manual action in their own R environment."
metadata:
  {
    "openclaw": { "emoji": "📊", "icon": "assets/icon.svg" },
    "authors": ["medstatstar", "phoe-zip"],
    "version": "1.12.2",
    "license": "MIT",
    "homepage": "https://github.com/medstatstar/meta-analysis",
    "tags": ["meta-analysis", "systematic-review", "clinical-trials", "R", "biostatistics", "evidence-based-medicine", "forest-plot", "network-meta-analysis", "bayesian", "metafor", "meta", "netmeta", "gemtc", "revman", "robumeta", "clubSandwich", "esc", "dosresmeta", "mada", "metagear", "forestploter"],
  }
---

# Meta-Analysis / 医学Meta分析

> R-based comprehensive meta-analysis. Every module ships reproducible R code.

## Language / 语言

**方案 C（2026-08-20 定稿）**：coze 端 R 引擎按请求 `params.locale`（zh/en，缺省 en）直出**双语模板**——数值 + 标准 label 精确（notes/warnings/quality-gate 检查按 locale 出中/英）；**SVG 一律英文**（图内文字不受 locale 影响）；中文标签（如研究名/项目名）由**本地渲染层**替换字体显示（`rendering._fix_cjk_fonts`，Windows: Microsoft YaHei / macOS: PingFang SC / Linux: Noto Sans CJK SC，可用 `RENDERING_CJK_FONT` 覆盖）。

**本地 LLM 呈现层硬约束（必须遵守）**：
1. **数值逐字引用**：`stats`/`pooled`/`heterogeneity`/`bias` 中的数值**必须原样引用，不得改写、四舍五入或重算**；
2. **标准 label 优先原样引用**：coze 返回的双语模板叙述直接采用，不重复翻译；
3. **只做两件事**：把模板叙述组织成通顺的用户语言 + 按需补充一句解释；补充解释不得覆盖/修改模板数值。

Policy → `references/language_policy.md`; guides → [README.md](https://github.com/medstatstar/meta-analysis/blob/main/README.md) / [README_zh-CN.md](https://github.com/medstatstar/meta-analysis/blob/main/README_zh-CN.md)

## Triage (ct-base §5.2)

On first user message, classify into one of three:

| Classification | Condition | Action |
|---|---|---|
| **Simple** | Single, specific intent (e.g., "pool OR from these 5 studies") | Reply directly, no menu |
| **Complex** | Multi-decision / multi-parameter (e.g., "network meta with 3 interventions, subgroup, check inconsistency") | Present level-1 routing menu incl. "③ Can't decide? → explain the differences between these choices" entry; full menu → references/interactive_menu.md |
| **Vague** | Unclear what user wants (e.g., "I need meta-analysis help") | Grill-me style branch questions, 1–3 per round; "无选题/可行性评估" → **Topic Selection** (below) |

If unsure between Simple and Complex → give short reply + optional expansion hint.

## Traceability / Grounding (ct-base §5.1)

All factual/assertive claims must cite source: specific `ref-*.md` section (e.g., `§3.6`) or official guideline. If a claim has no verifiable source → mark `⚠️ official verify` and ask user to confirm against official text.

## Initialization

0. **Execution backend — 发布形态 coze-only，开发保留双轨（2026-08-19 决策）**: 对外发布形态为 **coze-only（thin client）**——所有数值计算经 coze 元分析工作流完成（R 引擎在 coze 项目 `src/r_engine/`，经 `adapters/run_analysis.py` → `coze_client` 委派），本地 LLM 只做需求标准化、数据整理、结果与 SVG 图形呈现，**最终用户无需安装 R、不本地计算**。本地引擎统一在 `adapters/coze_project/src/r_engine/`（coze 远端双向同步唯一源，技能根 `r_engine/` 已废弃删除，2026-08-19）：开发者可用 `META_LOCAL_ENGINE_DIR` 启用本地 R 快速迭代/复现。**复现性**：每次分析返回 `repro` 字段（可复现 R 脚本 + R 版本 + 包版本，见 `coze_contract.md` §4/§8）。
1. **Coze endpoint（默认路径）**: 默认端点 `https://ct-meta.coze.site/run`（2026-08-19 修正，旧默认 localhost:5000 会误报不可达）；可用 `COZE_META_ENDPOINT` 覆盖；可选 `COZE_META_TOKEN` / `COZE_META_TIMEOUT`。`python adapters/run_analysis.py` 可端到端自测（`--prefer coze|local`）；`coze_client.health()` 探测端点可达性（/run，4xx/5xx 亦视为可达）。
   - **⚠️ 出站披露（ct-base §5 全库强制）**：本技能会把**分析数据**（研究事件数 / 样本量 / 效应量等，不含个人身份信息）POST 到 coze 端点（默认 `https://ct-meta.coze.site/run`）执行云端 R 计算。默认端点已预置在 `adapters/config.json` `auto_approve_endpoints` 白名单（作者预置，用户无感）；**自定义端点（`COZE_META_ENDPOINT` 覆盖）首次调用会弹 AUTH-BLOCK 确认**（统一文案），用户确认后写入白名单（`approve_endpoint()`），本会话及后续免确认。**未授权不阻断**：`run_analysis` 自动回退本地引擎（无 R 则返回 `_source=auth_blocked` 明确提示"本次未使用云端分析"）。payload 发送前经 `sanitize_payload()` 剥离 PII（身份证/手机号/邮箱）。
   - **forward 前唯一流程通知 + 预置白名单首次出站口头披露（§5）**：默认端点已预置白名单（`adapters/config.json`，永不弹确认），但 agent 在**每会话首次实际出站前**仍须向用户发**恰好一条**简短通知（仅此一条，不得重复、不得播报内部流程 / HARD GATE / 难度标签 / fallback）：`本次将把您的分析参数发送至云端服务 https://ct-meta.coze.site/run 进行计算；同时附带主机名哈希（query_origin，仅用于服务端归因/限流，非明文主机名）。请稍候…`。同会话后续出站不再重复披露。
   - **Coze 失败诊断须先确认（§5）**：coze 返回失败/超时/代理错误时，**先问用户**"Coze 云端服务暂时不可用，是否允许我自动诊断排查？"；允许 → 诊断并修复重试；拒绝 → 交付本地答案并附显著警告"无法连接 Coze 服务，答案未经过精校，请谨慎使用"。
2. **本地 R 环境（仅开发者/复现，最终用户不需要）**: 开发者或复现场景需本机安装 R（`Rscript --version`）+ 核心 14 包：`metafor meta netmeta bayesmeta dosresmeta mada robumeta clubSandwich ggplot2 svglite forestploter jsonlite dplyr scales` + 可选 2（守卫加载，缺失仅 warning）：`ggrepel robvis`。可用 `RSCRIPT_PATH` / `META_LOCAL_ENGINE_DIR` 覆盖默认值。⚠️ 本技能**不自动安装** R 包；缺包 task 由 `run_task.R` 的 `check_pkg` 守卫返回 error/warning 而非崩溃。
   - ⚠️ 2026-08-18 清单瘦身：esc/metagear/gridExtra/gemtc/rjags/multinma 已从依赖移除（esc 自实现转换、贝叶斯 NMA 为 coze 环境限制，见 CHANGELOG 1.9.0）；dmetar 移除非必需依赖；survmeta 下架→metafor 逆方差合并；ggforestplot→forestploter。
3. **Workspace**: Create `meta_analysis/` + `output/` in current directory (⚠️ will write files — 分析报告与取回的 SVG/CSV).
4. **Memory**: read `~/.workbuddy/MEMORY.md` for R config (only R-related config keys; unrelated personal content is ignored and never sent anywhere).

## Interactive Guide

**Triage path**: Vague → Level 1 menu (7 categories). Select → Level 2 with data-format hints. Sufficient info → skip menu, run analysis directly. Full menu tree + data formats → `references/interactive_menu.md`.

> **Other formats?** Install `@skill:statdata-transfer` for 50+ format conversion.

## Topic Selection（选题评估 · upstream gate）

Trigger: "我想做 Meta 但没选题" / feasibility check / "被拒为重复了" / pre-PROSPERO audit → `references/topic-selection.md`. Two paths:

- **Quick** (≤30 min): 1-page decision card — 4-dim scores (clinical/feasibility/data/novelty, 0–5 each, 0–20, any ≤2 = veto) + screen verdict. No final go/no-go.
- **Full** (5 stages + gates): PICO (`pico-guide.md`) → scoring + cross-checks R1–R6 → dedup (`dedup-search.md`: PROSPERO→Cochrane→PubMed; non-English opt-in) → PRISMA 2020/AMSTAR-2 (`compliance-precheck.md`) → 11-section report via `python scripts/generate_topic_report.py input.json output.md|html` (template + PROSPERO mapping → `topic-report-template.md` / `prospero-mapping.md`).
- ⚠️ Dedup searches run ONLY on user opt-in; otherwise deliver query templates.

## Core Functions

Module → R-package/function matrix (single-group / pairwise / effect-size / forest·funnel / heterogeneity / publication-bias / subgroup·meta-reg / sensitivity / Bayesian pairwise·NMA / multilevel·MV / survival / TSA / dose-response / diagnostic / RVE / RoB+GRADE / power / quality-gate) → `references/advanced_api.md` · `references/ADVANCED.md`. **Rule (see Reusable API): any analysis MUST call existing functions — never rewrite inline.**

## Reusable API (Mandatory)

> **Any analysis MUST call existing functions — never rewrite the full pipeline inline.**
> 统一入口 `adapters/run_analysis.py`（`prefer="coze"` 默认：coze 优先、失败自动本地兜底；`prefer="local"` 仅本地）。
> - `adapters/coze_client.py`：coze 工作流出站调用（主路径）。
> - `adapters/local_engine.py`：本地 R 兜底引擎（`adapters/coze_project/src/r_engine/run_task.R`）。
> R 侧函数清单与调用示例见 `references/advanced_api.md`（实现位于 coze 项目 `src/r_engine/` 与本地镜像 `adapters/coze_project/src/r_engine/`，同源）。

## Security & Scope

**Execution model (default coze, local fallback)**:
- **默认**：所有数值计算经 coze 工作流完成（R 引擎在 coze 侧，`subprocess Rscript` 调用）。技能发送分析请求（task/data/params/figure）、取回结构化结果；常见输入为汇总统计量（2×2 表、效应量+SE），也支持用户提供的个体级数据（IPD，如 `ipd_meta` task）。数值判断由 R 计算，不经 LLM 读取。
- **数据出域决策归用户（2026-08-20 原则，ct-base §5）**：技能**只负责实现功能 + 透明披露**（发送前告知发送内容与目标端点），**不替用户做安全/合规拦截**——是否允许数据（含 IPD）发送至 coze 由用户自行决定；coze 平台本身可满足安全合规需求。若用户明确要求数据不出域，引导其走本地引擎（`prefer="local"` / `META_LOCAL_ENGINE_DIR`，需本机 R 环境）。
- **兜底**：当 coze 端点不可用（网络错误 / 非 2xx / 空响应）时，自动回退到本地镜像 `adapters/coze_project/src/r_engine/run_task.R` 完成相同分析；结果 `_source` 字段标记来源（`coze` / `local_fallback` / `local`）。
- **显式本地**：用户明确要求"本地分析 / 离线"时，直接走本地引擎（`prefer="local"`），不触碰 coze。
- PDF full-text download from external services ONLY on **explicit user instruction**（`adapters/pdf_fetch.py`，opt-in）。Analysis artifacts written to `meta_analysis/` + `output/` by default.

**Not clinical judgment**: Results require professional interpretation.

**No literature DB search**: Does not search literature databases; only downloads full text when user provides DOI/PMID.

## 上传文件处理 / User-Uploaded Files (ct-base §6.7)

> 全库统一规范：**ct-base §6.7**（`ct-base/docs/02-governance-redlines.md`）。两类上传、两条路径：

1. **结构化数据文件（`.csv` / `.xlsx` / `.xls`）** → 走既有 **Type 4 数据模板**（`references/data_templates.md`：编码识别 / 列名中英匹配 / 缺失值检测 / 记录数确认）。这是**分析数据**，不适用 §6.7 的文档→md 转换；但 §6.7.2 的信息透明与 §6.7.3 的保密边界同样生效（见下）。
2. **文档 / 模板类上传（`.docx` / `.pptx` / `.pdf` / `.doc`）** → 例如研究摘要 PPT、方案文档、PRISMA 流程图：**先转 md/文本再提取研究数据**（§6.7.1 分层策略）：
   - `.docx` / `.pptx` → `python scripts/office_to_md.py <file>`（共享转换器，stdlib-only，docx/pptx 单一解析器）
   - `.pdf` → 环境 `pdf` 技能（文本提取；扫描件需 OCR）；环境无该技能 → 提示用户安装，不自写 PDF 解析
   - `.doc`（OLE 老格式）→ 提示安装 word-reader / antiword
   - 图片 / 扫描件为主（无文字层）→ 提示用户提供文字版

**🔔 转换前用户提示（§6.7.2，先向用户展示再执行转换）：**
> ⚠️ 所有上传文档将转换为 **md 格式**处理；**PPT 文档转换容易丢失大量信息**（图片、版式、动画、图表等非文本元素），建议用户**最好先自行转换为 md 格式并做内容检查**后再提问，以保证关键内容不丢失。

**保密处理（§6.7.3 + 2026-08-20 原则）**：技能**不主动判断 / 拦截**上传内容的保密性——文档照常转换、数据照常读取，是否出域由用户决定。技能只负责实现功能 + 透明披露：发送至 coze 的内容（汇总统计量或用户提供的 IPD）会在首次出站时向用户披露；**IPD 等个体数据是否允许上云由用户自行决策**（coze 平台可满足安全合规需求）。若用户**明确要求数据不出域**，引导其走**本地引擎**（`prefer="local"` / `META_LOCAL_ENGINE_DIR`，需本机 R 环境），全程不触碰 coze。

**出图格式约定（2026-08-20 收紧）**：**coze / 本地引擎恒返回 SVG**（适配层强制 `figure.format="svg"`，即使调用方请求 png 也被覆写）；**PNG 一律由本地呈现层转换**——`render_figures(mode="png_file")` / `rendering.svg_to_png()`（本地 cairosvg 光栅化，coze 端零 png 路径）。

## Output

由 coze 工作流或本地引擎产出（取决于 `_source`）：`analysis_complete.R` + forest/funnel (`.svg`+`.png`) + `results_summary.md` + `data_backup.csv`。本技能经 `adapters/run_analysis.py` 取回结构化结果（含 figures[].svg）写入 `output/`；PNG 仅在本地转换模式（`png_file`）下生成。

**呈现规范（默认）**：所有 `figures[].svg` **内联渲染进对话流**（可选中/缩放/编辑，非附件），同时另存 `output/` 供下载。图**固定原尺寸不缩放**，容器装不下即出横向滚动条；**x 方向 pad=8 紧凑、y 方向 pad_y=24 上下留白**。内联渲染标准 → `references/inline_rendering.md`；**统一要求已上收 `ct-base/BASE.md §19`（docs/06-inline-rendering.md，全库强制）**。SVG 编辑与期刊格式转换 → `references/svg_editing.md`。

**出图模式选项（figure_mode，2026-08-19）**：默认 `svg_inline`（SVG 内联进对话流），可切 `png_file`（本地 cairosvg 转 PNG 文件，附件卡片，不内联 SVG）。PNG 不占 LLM 上下文、界面渲染更快，但损失可编辑文本（位图）。

```python
from adapters.run_analysis import render_figures
# 显式选择模式（agent 行为；不影响 coze 调用）
out = render_figures(out, mode="png_file", out_dir="output")
# mode='svg_inline'（默认）保留 figures[].svg 原样
```

**渲染计时与超阈值提示（2026-08-19）**：本地渲染阶段耗时 `render_elapsed_seconds` + SVG 体量 `render_svg_kb` 作代理（界面渲染无法在 agent 侧精确计时）；`> 30s` 或 `> 200KB` 自动生成 `render_hint`，阈值常量在 `adapters/run_analysis.py` 顶部；agent 须在回复体现并建议切 `figure_mode='png_file'`。

**Quality Gate (human sign-off)**: 呈现合并效应前，coze 侧 R 运行 `run_quality_gate(es_data, model, bias_result)` → gate JSON；红灯（k<3 / I²>75% / 偏倚核查缺失）**阻断**呈现 — 经 `python scripts/quality_gate.py gate.json --yes` 人工确认（ct-update upgrade A）。数值判断由 R 计算，绝不经 LLM 读取。

## Units — see `references/units.md` for the 5-field schema (input / output / dependency / AI autonomy / consumer units).

## References

Full reference-file index (file → content) → `references/references.md` (also lists package citations). Key files: `interactive_menu.md` (chat guide + menu tree), `ADVANCED.md` / `ADVANCED_zh-CN.md` (developer reference), `advanced_api.md` (reusable API), `topic-selection.md` (upstream gate), `data_templates.md` (input templates), `svg_editing.md` (journal-format conversion).

## Project Files

`README.md` | `README_zh-CN.md` | `CHANGELOG.md` | `AGENTS.md` | `LICENSE` (MIT © 2025 medstatstar) | `requirements.txt` | `assets/icon.svg`

## Changelog

Version / fix log → `CHANGELOG.md`.

## Bug Reporting (ct-base §20.3, adapter: `adapters/bug_report.py`)

- **Trigger (strong signal, max 1 proposal/session):** unexpected non-zero exit / engine or compute error / user explicitly questions the result — **and** the same operation was retried ≥1. Weak signal (just repeated tuning) never triggers.
- **Two-stage confirmation (2026-08-21):** ① propose-with-preview — show the bilingual `confirm_prompt` **together with** the full report (`render_report_text`, state "sanitized, no input data", invite a problem description; if the user adds one, re-render and re-show before consent) → ② on explicit consent, `send_to_endpoint` (auto action=report, endpoint `https://ct-bugreport.coze.site/run`, token = embedded §5 public credential). If the user declines, never re-propose this session.
- **Sanitization is hard:** the report carries only the 11-key whitelist (skill / version / error_type / error_code / engine_status / description / locale / query_origin / session_hash / attempts / test) — never raw data or subject records. `description` is the single free-text field for debugging, **user-reviewed**: write the symptom / reproduction / expected vs actual / algorithm or function used / error message; values and study design are OK. Hard boundary: no identifiable person/institution/subject info. The user reviews it in stage ① before consent; empty description omits the key. If the session had **no** cloud call, `save_local_report()` writes a local md + author email (data never leaves the machine).
- **Post-send history receipt (2026-08-22):** after a successful send, surface `confirm_thanks()` first, then `build_followup(parse_history(resp["history"]))` — which tells the user whether the bug they reported last time was fixed (`done`, with `memo`) or is still pending. The `history` is pulled server-side by `query_origin` (the endpoint returns the latest prior record for that source); first-time reporters get an empty history (no follow-up beyond the thanks).
- **Client-only:** this adapter sends `report` only. Governance actions (get/update/download/delete — pull pending, mark done, download all, clean up) are reserved for the `ct-update` skill (author side); never call them from here.

Invoke: `python adapters/bug_report.py --error-type <t> --description "<free text>" [--send]` (add `--send` only after the user confirms).
