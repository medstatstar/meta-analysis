# Changelog / 变更日志

All notable changes to the `meta-analysis` skill are recorded here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versioning follows [Semantic Semantic Versioning](https://semver.org/).

---

## [2.9.16] — Unreleased — pdf_fetch 多通道回退上移 coze + workbench A4 批量匹配

- **workbench「数据提取核验（🔴 红线）」新增「📤 批量上传并匹配文献」**（实测反馈）：A4 面板 actions 首位新增按钮 + 折叠面板——上传 `.txt/.csv/.xlsx` 或粘贴 **DOI / PMID / 标题** 清单 → 新端点 `/api/a4_batch_match`（Europe PMC core 逐条解析；DOI/PMID 精确、标题先短语后 token-AND 近似并标 `fuzzy` 提示人工确认；去重 DOI 归一键；标注是否已在 A4 per_doc）→ 勾选后 `/api/a4_batch_add` 幂等追加为 `status=needs_upload` 待补篇（复用「补传 PDF → 抽取」通路）。纯元数据匹配，不下载正文。前端 `toggleA4Match / a4BatchMatch / a4BatchAdd`；实测 DOI/PMID/标题三类输入均命中。
- **架构（与 ct-literature v0.9.7 同规）**：`adapters/pdf_fetch.py` 的多通道/预印本回退算法一律上移 coze `publisher_pdf` 服务端（补充链 = Unpaywall → PPR bioRxiv/medRxiv → arXiv，作者级同篇校验，2026-09-06 起服务端实现）。本地 `fetch_pdf` 主路径改为：① 委托 coze（服务端含 A 路径 + 补充链）；② coze 不可用时仅本地直下降级（open_access_url / Unpaywall / PMC）；③ 本地 `_try_preprint_fallback`（PPR/arXiv）停用（保留为历史参考），不再本地实现预印本检索下载、不再为回退预取 title/authors（省 Crossref 反查）。CLI `--with-*` 开关兼容保留（自动由服务端生效）；docstring/usage 同步。

---

## [2.9.15] — 2026-09-06 — C3 真实 API 参考文献核验 + A1 选题报告可行性信号

> **目标**：C3 参考完整性核验从纯结构检查升级为真实 API 核验（CrossRef + PubMed E-utilities），防 AI 虚构/拼接参考文献（JAMA 2026-08 红线）；A1 选题报告补可行性信号（拥挤度 / 预期研究数 / 方向稀缺度）。

### Added
- **新 `adapters/ref_verify.py`**：CrossRef (`api.crossref.org/works/<DOI>`) + PubMed (`esummary.fcgi?id=<PMID>`) 双库真实核验。单条 `verify_reference()` 含双侧 DOI+PMID 交叉验证（PubMed 传回的 DOI 与传入 DOI 核对 → 防拼接幻觉）；批量 `verify_references()` 自动去重 + polite delay。撤稿文献（CrossRef type=retraction / PubMed pubtype 含 retraction）自动标 critical；作者不一致、DOI 不匹配均标 mismatch。零第三方依赖（纯 urllib + json），网络失败 status="error" 不阻塞。
- **增强 `c3_reference_verify`（block_c）**：接入 `verify_references`，每条参考真实查 CrossRef/PubMed；n_retracted / n_not_found / n_mismatch 计数 + 详细 issue 列表；撤稿/虚构/拼接任一标 critical → C3 reference_verification 红线闸阻断。

### Changed
- **增强 `a1_topic_selection`（block_a）**：报告新增 `feasibility` 结构（crowding / expected_studies / risk_alert）；拥挤度分 4 档（empty/low/moderate/high），来自 ct-registry 注册数推断；空/低方向自动给风险提示（meta 需 k≥2）；文本报告同步追加 📊 拥挤度行与 ⚠️ 风险行。

### 验证
- py_compile 全绿；合成 mock 测试 9 项全过（OK / not_found / retracted / mismatch / error / batch / c3 集成 / A1 拥挤 / A1 空方向）。

---

## [2.9.14] — 2026-09-05 — A4 逐篇剔除（不进合并）+ 抽取行治理

> **目标**：数据提取核验（A4 红线）界面允许把误纳入的文献剔除（如 review 漏网 / 抽取错源），被剔除篇的抽取行不进 Block B 合并；同时治理"综述正文被当原始研究抽取"。
> 退出标准：① per_doc 有 included 开关，剔除后卡片置灰可恢复；② approve 时剔除篇行不进 handoff.studies_for_b；③ 叙述性抽取行（他引转述）不再自动进 extracted_rows。✅ 全达成（E2E 双向实测）。

### Added
- **A4 逐篇剔除/恢复**：`per_doc[i]` 新增 `included=True`（block_a a4_stream）；`server.py` 新增 `POST /api/a4_set_doc_included`（就地更新 included + excluded_reason，重算 n_extracted/n_included_docs/n_excluded_docs）；前端每篇卡片操作区加「✕ 剔除本篇（不进合并）/ ↩ 恢复纳入」，剔除篇整卡置灰 + excl pill + 说明条（`.a4doc-excluded` 等样式）。
- **A4 approve 携带剔除态**：前端 `approveA4()` 在放行前把各 included 篇的抽取行汇总为 `revision.extracted_rows`（被剔除篇行排除）、剔除清单入 `revision.excluded` 再提交；`fullflow._extraction_input` 改用 `latest_revision`（不限 action，approved 携带 revision 亦被采用），使放行不重抽、剔除真正生效。

### Changed
- **抽取行治理（block_a a4_stream）**：`extracted_rows` 从"仅 2×2"扩为"2×2 + 来自表格模板的效应量行"（te/sete 齐全且 anchor 含 `table#`，转 TE/seTE 大写供 Block B）；叙述性行（anchor 含 `text:`，多为综述正文对他引结果的转述）**不再自动进 extracted_rows**——根治"综述抽出一堆错源效应量"。

### 诊断结论（10.3945/an.111.000893 = Adv Nutr 2012 REVIEW）
- 该 PDF 首页 RUNNING HEAD 即 "REVIEW"，Europe PMC pubType 含 `Review`/`review-article`（B1 硬信号应命中），但 ff-3770 会话中该记录来自 OpenAlex（type=article、无 abstract、pub_types 未透传）→ review-guard 三道全漏 → 进 A4。属 **ct-literature 合并归一化未透传 pub_types** — **已修复（ct-literature v0.9.6+ 见 CHANGELOG (6)）**：`fetch_europepmc._extract` 现保存 `pub_types`，`fetch_openalex._extract` 从 `type` 派生，`normalize.merge` 做 union-dedup 合并。
- 抽取 5 行全为 narrative 行（"HR (p3)"/"RR (p3)"/"farction" 等错 study 名）→ 现已被"叙述行不收"规则排除；用户在 A4 界面可进一步用「剔除」显式标出。

### 验证
- py_compile + node --check 通过；`/api/a4_set_doc_included` HTTP 实测 200（剔除持久化 + 计数 1/19）；函数级 E2E：剔除该篇 → handoff.studies_for_b=0，全保留 → =5。

---

## [2.9.13] — 2026-09-05 — 工作台 UI 视觉升级（对齐 ct-base workbench_ui 规范）

> **目标**：工作台"太简单不够美观"——按 ct-base `references/workbench_ui.md` 的视觉规范做纯 CSS 层升级，不动 JS 逻辑/类名/DOM 结构。
> 退出标准：① 深色品牌渐变顶栏 + 反色控件；② 卡片阴影层次 + 列表斑马纹 + 状态 pill 边框化；③ logo 换技能 icon 色系 SVG（禁 emoji 当图标）；④ JS 语法与 HTTP 渲染验证通过。✅ 达成。

### Changed
- **`workbench.html` 追加 ct-base 视觉层**：`--wb-*` 设计令牌（brand clinical-indigo 系）、深色渐变顶栏（`--wb-topbar-bg` + `--wb-on-topbar` 反色）、卡片圆角/阴影层次、表格斑马纹 + hover、按钮渐变主色 + hover 亮度、pill 边框化、JSON/代码块统一浅底、细窄滚动条。
- **header logo**：`🧬` emoji → 内联 SVG（技能 icon.svg 紫系同心圆 + 聚合菱形，34px），对齐 ct-base §5.2 logo 规范。
- **装饰性 emoji 清理**：logbar 标题 `🗂` 移除（ct-base §4.4 禁 emoji 当图标）。
- 业务文案内功能性指示符（✅ 状态徽标 / ⬇ 上传 / 🔗 DOI 等）保留——由 JS 模板生成，全量 SVG 化留作后续（避免大面积模板改动风险）。

### 验证
- `node --check` 抽取内联 JS 通过；HTTP GET / 返回 200 且含 `wb-brand`/`--wb-topbar-bg`/`--wb-row-alt` 等新标记；server 已重启载入。

---

## [2.9.12] — 2026-09-05 — 修复回退/交接闸 422 + A1 纳入综述开关 + PDF 入口分类模板

> **目标**：① 修复工作台「打回/回退」与块间交接（handoff_confirm）批准失效；② A1 选题页可直接决定"检索是否纳入综述"；③ 沉淀 PDF 下载入口分门别类模板。
> 退出标准：① handoff approve 不再 422、rewind 全链路 200；② A1 revision.include_reviews 覆盖 cfg 传入 A2（端到端实测 true 生效）；③ 模板覆盖 5 类框架且有代码/实测证据。

### Fixed
- **handoff_confirm 交接点 approve 422**：`server.py DecideReq.stage_id` 原为必填 `str`，而块间交接 await 的 `stage_id` 为 `null` → pydantic 422 → 交接点永远无法批准（表现为"回退后流程卡死/回退不起作用"）。改为 `Optional[str] = None`（后端 `_validate_decision` 对 handoff_confirm 本就不校验 stage_id）。
- **rewind 请求路径**：`workbench.html rejectAndRewind()` 用裸 `fetch("/api/rewind")`，未走 `apiUrl()` → file:// 打开工作台时必然失败。改用 `apiUrl("/api/rewind")`（与其余 API 调用一致）。

### Added
- **A1「是否纳入综述类文献（检索范围）」开关**：`form_schema.py` A1 新增 `kind=bool` 可编辑面板（revision_key=include_reviews）；`fullflow.py` `EDITABLE_KEYS["A1.topic_selection"]` 增 `include_reviews`、新增 `FullflowSession.latest_revision()`（读不限 action 的最新 revision）、`_run_block` A 分支用 A1 revision 的 include_reviews 覆盖 cfg；`block_a.run_block_a` 把 include_reviews 写入 A1 stage_result 作初值；前端 `renderPanel` 支持 `kind=bool`、`collectDraft` 支持独立 checkbox（整键存 true/false）。端到端实测：A1 approve + `revision.include_reviews=true` → A2 检索卡片收到 `"include_reviews": true`。
- **PDF 下载入口分类模板**：`references/pdf-download-portals.md` —— A 聚合 API（Unpaywall/Europe PMC core/OpenAlex）、B OA 仓储模板（PMC `/pdf/`、预印本 `.full.pdf`、MDPI `/pdf?version=`，后二者命中用户实例并有代码/检索数据佐证）、C 出版商文章页 DOM（pdf_cf_guard 规则）、D 签名直链（SD X-Amz 书签 + CDP 边界，2026-09-05 实测结论）、E 付费墙人工上传；附决策速查表。`SKILL.md` 边界段补引用。

### Changed
- 工作台 server 已重启载入修复（端口 8765）。

---

## [2.9.11] — 2026-09-05 — A4 下载文档列表不展示已排除篇目

> **目标**：A3 筛选裁决「排除」（review-guard / 相关性门控，status=skip）的文献不进 A4 下载文档列表，只保留需要下载/已下载/待上传的篇目，消除"已排除还显示在下载清单"的困惑。
> 退出标准：① 实时进度面板 skip 事件不上屏；② 逐篇文档展示过滤 status=skip；③ 过滤后 doc_index 仍按 per_doc 原始位置定位（后端不感知）。✅ 全部达成（JS 语法校验通过）。

### Changed
- **workbench.html `renderA4Documents()`**：`per_doc` 先过滤 `status !== "skip"`；展示编号与所有后端定位（doc_index / pdf_page / a4SaveDoc / a4ViewPage / 上传指派）改用 `d.index`（per_doc 原始位置），避免过滤后 map 位置与原始位置错位；空态区分"筛选后无需要下载" vs "尚无结果"。
- **workbench.html `renderA4Live()`（续跑实时进度）**：`skip` / `relevance_skip` 事件直接 return，不建行。
- **workbench.html `doA4Preview.addRow()`（A4 预览实时进度）**：同上，skip 事件不上屏。
- **deferred（配额延后）保留展示**：语义为"本轮配额未轮到、仍需下载"，与 skip（明确不下载）区分。

---

## [2.9.10] — 2026-09-05 — A2 源头排除综述：节省检索配额 + 避免 10.3390/ijms27114705 类困惑

> **目标**：默认从检索源头排除综述类文献（Review / Systematic Review / Meta-Analysis），节省检索配额，避免用户困惑（如 10.3390/ijms27114705 在 A3 被标记 review 但仍占用 A2 配额）。
> 退出标准：① Europe PMC / OpenAlex 双源头加 NOT review 过滤；② meta-analysis 默认 include_reviews=False；③ 前端加"包含综述"开关；④ 伞评/范围综述场景可显式开启。✅ 全部达成（代码级验证）。

### Added
- **Europe PMC 源头排除综述**：`fetch_europepmc.py` 新增 `include_reviews=True` 参数；`False` 时追加 `AND NOT (PUBLICATION_TYPE:"Review" OR PUBLICATION_TYPE:"Systematic Review" OR PUBLICATION_TYPE:"Meta-Analysis")` 过滤串；CLI 暴露 `--include-reviews/--no-include-reviews`（argparse.BooleanOptionalAction）。
- **OpenAlex 源头排除综述**：`fetch_openalex.py` 新增 `include_reviews=True` 参数；`False` 且无指定 `review_type` 时追加 `type:article` 过滤（拦截 `type:review` 条目）；CLI 同上。
- **编排层透传**：`ct_literature.run()` 新增 `include_reviews=True`，透传给两个 fetcher。
- **block_a A2 默认排除综述**：`a2_build_tool_card()` / `a2_literature_search()` / `run_block_a()` 新增 `include_reviews=False`（默认源头排除综述）；`tool_mapping_meta.json` 的 ct-literature arg_map 新增 `include_reviews` → `--include-reviews`。
- **coze_client 布尔参数透传**：`execute_tool_cards` 的 arg_map 循环识别 `include_*` / `exclude_*` 命名风格的 bool 参数，自动转为 `--no-*` 标志（BooleanOptionalAction 语义）。
- **前端开关**：`workbench.html` 启动表单新增"包含综述类文献"复选框（默认不勾选），`doStart()` 读取后写入 `opt.include_reviews`。
- **server / fullflow 透传**：`StartReq` 新增 `include_reviews: bool = False`；`api_start_stream._call` 透传给 `run_fullflow`；`run_fullflow` 写入 `cfg`；`fullflow._run_block` 透传给 `block_a.run_block_a`。

### Verified
- 编译验证：`py_compile` 全部 7 个修改文件通过。
- 语义验证：Europe PMC 过滤串语法对齐官方 search grammar（PUBLICATION_TYPE 为索引字段）；OpenAlex `type:article` 与既有 `_openalex_type_for()` 不冲突（仅在 `review_type="all"` 且 `include_reviews=False` 时生效）。

---

## [2.9.9] — 2026-09-03 — A4 续跑优化 + 逐篇下载实时进度 + 修复发起流程 TypeError（发布就绪）

> **目标**：① A3 批准后只跑 A4（不再整块重跑 A1→A4）；② A4 下载/抽取逐篇实时上屏；③ 修复 `api_start_stream` / `api_decide_stream` 因 `_call` 闭包未接收 `on_a4_event` 导致的 TypeError。
> 退出标准：A3 批准仅跑 A4（a1/a2/a3 调用计数 0）；A4 逐篇 `a4` 事件实时流出（生产实测 100s 内 31 条）；发起/决策流程零 TypeError。✅ 全部达成（生产环境端到端实测 + 单元验证）。

### Added
- **A4 续跑（A3 批准后只跑 A4）**：`fullflow._run_block` A3 已批准且无 A2/A3 修订时设 `start_stage='A4'` 并传 `cached_envelope`（含已算好的 A1/A2/A3）；`block_a.run_block_a` 新增 `start_stage`/`cached_envelope`，命中则 `a4_only=True`，复用缓存 `studies/screened`，跳过 A1/A2/A3 重算（实测调用计数 a1:a2:a3 = 0:0:0，原整块重跑约 7 分钟）。
- **A4 逐篇实时进度**：`block_a.a4_auto_fetch_and_extract` / `a4_data_extraction` 透传 `on_a4_event` 回调；`server._stream_blocking` 新增 `_make_on_a4()` 把逐篇事件推成 SSE `a4`；前端 `decide` SSE 处理新增 `a4` 分支 → `renderA4Live(ev.a4)` 逐篇进度面板（标题/状态徽章/原因即时刷新）+ `.a4live*` 样式。

### Fixed
- **发起/决策流程 TypeError（2026-09-03）**：`_stream_blocking` 向 `call(...)` 同时传 `on_line` 与 `on_a4_event`，但 `api_start_stream._call` / `api_decide_stream._call` 仅声明 `on_line=None`、不收 `on_a4_event` → 首次发起流程即抛 `TypeError: ..._call() got an unexpected keyword argument 'on_a4_event'`。两处 `_call` 增加 `on_a4_event=None` 形参并转发给 `run_fullflow` / `resume_fullflow`。`fullflow.py` 下游已全程透传，无需改动。
- **A4 面板渲染崩溃（Cannot read properties of undefined (reading 'split')）**：`renderPanel` 对无 `path` 字段的面板（a4documents/a4uploads）改 `data=ctx`；`resolve` 空/非字符串 dotted 返回 `ctx` 兜底；`form_schema.py` 自检改 `p.get('path')`。

### Verified
- 单元验证：monkeypatch `run_fullflow` / `resume_fullflow` 记录器，直接调真实 `api_start_stream` / `api_decide_stream` 端点 → 两处 `_call` 均收到 `on_a4_event`（callable）。
- 生产实测（会话 `fullflow_session_ff-753d2c8f347d`）：`start_stream` → A1 选题闸（零错误）→ approve A1 → A2 检索 75 篇 → A2 闸 → approve A2 → A3 初筛 75 篇 → A3 闸 → approve A3 → **A4-only 触发 + 100s 内 31 条逐篇 `a4` 事件实时流出，全程零 A1/A2/A3 重跑日志**。

### Notes
- 解除 2.9.8 的「开发期冻结」备注（DEV_POLICY.json 已不存在）；本次起恢复常规发布流程。
- 发布包排除：`.gitignore` / `.clawhubignore` 新增 A2/A4 运行产物（`adapters/*.json`、`lit_report.*`、`evidence_log.*`、`references.*`、`pdfs/`、`workbench/runs/` 等），测试内容不进发布包（§16）。

---

## [2.9.8] — 2026-09-01 — 数据抓取增强 port 进本体：连续型模板 + 无边框表重建 + 校验修正（开发期不发布）

> **目标**：把 seam_test 沙盒验证过的 `pdf_extractor_opt.py` 全量 port 进技能本体 `adapters/pdf_extractor.py`，并修复 port 过程暴露的保真缺陷与 opt 版固有 bug。
> 退出标准：4 篇人工 PDF（NEJM/JAMA/Nature/BMC）+ 8 篇自动 PDF 实测达标；`test_pdf_extractor.py`(16) + `test_block_b.py`(20) 离线全绿。✅ 全部达成。

### Added
- **多级降级抓取路径（用户 2026-09-01 明确）**：`parse_pdf` 逐页产出 `table_tiers`——T1 有框表（pdfplumber lines，通用）→ T2 无框表重建（PyMuPDF word 坐标，专用精细）；`extract` 逐页逐层跑模板、**命中即停**（`_review.tier`/`_review.method` 审计到行）。已评估不采用的中间层：pdfplumber text 对齐策略（把正文撕成伪表，实测 BMC 70×12 伪表）与 PyMuPDF find_tables（默认 lines 策略对无框表 0 检出）。
- **失败如实返回**：`review_summary.tier_report`（每页各层尝试与命中行数）+ `review_summary.unresolved`（scanned=无文本层需 OCR；all-tiers-no-template-hit=检出表格但模板全不命中，含 Table 标题者提示人工录入）。纯正文页不记失败（叙述通道仍扫其文本）。OCR 为预留扩展位。
- 连续型抓取模块 port：`t_cont_table`（T_CONT_BETA / T_CONT_CHANGE / T_CONT_CHANGE_CI / T_CONT_TWOARM 四形态）+ `narrative_continuous`（T_MD_CI 正文叙述）。
- 效应量模板 port：`EXTRACTION_TEMPLATES` 注册表（T_HR_CI / T_OR_CI / T_RR_CI / T_MD_CI / T_PVALUE）+ `t_effect_table`（森林表 2×2 计数列 + HR 列双源回填）。
- 无边框表重建 `_rebuild_borderless_table`：PyMuPDF word 坐标，「Table N 标题锚 + y 范围圈定 → y 相邻归并行聚类（标签词保留）→ x 中心 20pt 列聚类」；extract 主循环接入**行级 fallback**（页内全部表格模板未命中时重建后重跑一轮），重建行 `_meta.rebuild=True` 可审计。
- `_norm_path()`：Git Bash `/c/...` 路径 → Windows `C:/...`，`parse_pdf`/`_rebuild_borderless_table` 全部走规范化。

### Fixed
- **check_te_sete CI 尺度混乱（opt 版固有）**：HR/OR/RR 行 te 为 ln 值而 reported.ci 是原始尺度 → ci-asymmetric 全误判 failed。extract 调用点按 measure 对比值度量的 CI 先取 ln 再校验；MD 保持原值。JAMA failed 19→2（剩余 2 个为校验器正确拦截的可疑 interaction CI，交人工）。
- **sete 回填公式**：`0.5*(lnhi−lnlo)`（=1.96·se，错）→ `(lnhi−lnlo)/3.92`（Woolf se，与全模块约定一致）；且回填不再覆盖表格自带的报告 te/sete（`r.get(...) or` 语义）。
- **reported_summary 互证污染**：port 中误加的「正文 OR → reported_summary['*']」导致 NEJM 森林表 31 行全部 or-mismatch failed；移除（check_dichot 不再自动互证）。
- **ci-asymmetric 阈值**：1.10 → 1.25（报告值四舍五入致 ln 空间实测不对称 ≤1.12；真正取错数值实测 4.6）。
- **基线表/n(%) 表误抓**：t_continuous 加表级防御（`_BASELINE_KW` 表头且无结局词 → 跳过；表内 `n (%)` 声明 → 跳过；全表数值对 ≥80% 为整数对 → 跳过）+ 行级恰好 2 组 m±SD 才配两臂（>2 组为多臂基线表）。NEJM 基线表 14 行 + 合并用药 n(%) 4 行 + BMC 基线碎片 2 行误抓全部清除。
- **_PVAL 误抓**：`P\b`+IGNORECASE 命中 'group 30' 尾字母 p → 强制关系符 `[=<]` 必选 + pv>1 值域丢弃。
- **嵌套括号 OR/HR 句漏抓**：te→CI 锚间隔段 `[^()]{0,80}?` 禁括号，挡掉 BMC 系写法 '(odds ratio 1.71 (95% CI 0.93 to 3.16))' → 改 `.{0,80}?`（误越界由 lo≤te≤hi 校验兜底）。
- **CI 锚与 lo 间换行漏抓**：JAMA 原文 'HR, 0.83; 95% CI,\n0.76-0.92'——`[ ,:(]*` 不含 `\n` → 并列双 HR 段只抓到第二个（0.95/0.81），第一个（0.83/0.77）整行丢失 → 字符类加 `\n`。修复后 JAMA 并列双 HR 正确双抓（0.83 CI 0.76-0.92 + 0.95 CI 0.77-1.17 等均为原文真值），此前 2 个「拼接错行 failed」实为该 bug 症状，随修复消失（JAMA 终态 20 HR 全 needs_review，0 failed）。
- **无边框重建 block 选择**：正文 '(Table 1)' 引用被误当标题锚（start_bno 污染致正文全混入）→ 改「`Table N` 开头且词数 ≤15 的短 block」为锚，按 y 范围圈定表格区域。
- **tests/test_pdf_extractor.py**：`test_full_pipeline` 断言对齐现行 API（叙述 or_ci 直接成行 T_OR_CI、candidates 仅 P 值 kind='pvalue'、n_rows=3）。

### Verified（bench 12 篇：4 人工 + 8 自动）
- 效应量行：HR 73 / MD 9 / OR 2（vs port 前 opt 基准 HR 73 / MD 8 / OR 2；MD +1 来自 doc9 行级重建 fallback 增益）。
- verified 31（NEJM 森林表双源）保持不膨胀；垃圾行 142（vs 155）全为有效数据行。
- Nature 连续型 6 MD（Cystatin C/hs-CRP/PAB × Beta 列 + Changes 两来源一致）；BMC Table 1 无边框表完整重建（10 行 × 6 列，4 组 m±SD 对齐），基线表正确不产 meta 行。

### Notes
- 开发期冻结（DEV_POLICY.json）：仅本地改动，不推送 / 不发布。
- 测试 36/36 全绿（test_pdf_extractor 16 + test_block_b 20）；bench 12 篇终态 HR 73 / MD 9 / OR 2、verified 31 不膨胀。

---

## [2.9.7] — 2026-09-01 — B 阶段：Block B1 计算上云 + 删除本地双引擎（开发期不发布）

> **目标**：落实架构终态原则（coze 为唯一计算真相源，本地不保留计算引擎）。B1 pairwise 计算改走 coze R 引擎；删除本地 numpy 双引擎与 `_dev/local_engine.py` 残留。
> 退出标准：运行路径 B1 不再本地计算；`b1_pairwise_python` 降级为仅回归 oracle；`_dev/local_engine.py` 已删。`test_block_b.py`(20) + `test_pdf_extractor.py`(16) 离线全绿。

### Changed
- `adapters/block_b.py`：`b1_meta_analysis` 默认 `engine="coze"`，B1 经 `coze_client.run_stage` 发 ct-meta2 R 引擎；新增 `_build_b1_coze_env` / `_extract_coze_stats` / `_coze_stats_to_pairwise`（coze `stats` → 本地 pairwise 形状，对数尺度同构，B2/B3/B4 零行为变更）。`run_block_b` B1 显式 `engine="coze"`。
- `b1_pairwise_python` 标注为仅回归/调试 oracle（`engine="local"`），非运行路径；`engine="auto"` 移除。

### Fixed
- **单组率 `single_group_meta` 列名 bug（2026-09-01）**：coze 端 dispatcher（`adapters/coze/src/r_engine/run_task.R` `single_group_meta` 分支）硬编码读取 `df$event`（单数），而本地核心代码 `meta_analysis_core.R`、参考文档 `single_group_meta.md`、模板 `extract_assist.py` 与用户请求均使用 `events`（复数）。`.build_df()` 只 `tolower` 列名、不应用 colmap 重映射，导致 `events` 列落 else 分支调 `metamean(mean=NULL)` 报错。
  - `run_task.R`：改为经 `.col_name()` 解析 event/n 列并加 `events` 别名归一（colmap 对单组率生效，与二分类/连续分支一致）。
  - `meta_analysis_core.R`：`single_proportion`（`calculate_effect_size` + `ma_analyze`）同步兼容 `event`/`events` 两种列名。
  - 验证（Python 等价模拟）：`events`+colmap / `event`单数 / colmap `event→events` 三种输入均正确命中 `metaprop` 分支。
  - 注：measure 名 PLOGIT（coze/meta 包）vs PLO（本地 core/metafor）为两套 R 包各自合法 logit 写法，功能等价；已于同日后续修复中按别名归一统一（见下方 Fixed·measure 提示统一）。

### Fixed
- **coze 端同步核查 + `_STAGE_KEYS` 潜伏 bug 修复（2026-09-01 晚）**：用户拉取 coze 当前代码包（`project_code_4f377ea2.zip`，含 `state.py` 的 `schema→envelope_schema`+`alias="schema"`+`populate_by_name=True` 三处改名）核查死机问题。
  - 核查结论：`state.py` 改名规范干净（下游无消费 `.schema` 的代码、`contract_version` 字段兜底使 `is_legacy_request` 路由不受影响），**非死机原因**；单组率 `events` 案例在 R 核心计算实测不卡死不报错（`metaprop`+`rma.uni` 桥接正常）。**"长期死机不结束"实为 R 引擎冷启动 + 多张 SVG 出图（尤其 `influence` 多面板 7×9）在 coze 无头 Linux 环境耗时过长**（报告自承"R 引擎加载 + 出图耗时较长"），非代码死循环；建议用 `figure.plots=[]` 验证核心计算可秒级返回。
  - 潜伏 bug：`stage_envelope.py` 的 `_STAGE_KEYS` 仍含 `"schema"`，但 `state.py` 改名后 `model_dump()` 输出字段名变为 `envelope_schema`，导致"纯 per-stage 信封（只带 schema 不带 contract_version）"被 `is_legacy_request` 误判为 legacy。已修复：判定键集改为 `("contract_version","envelope_schema","schema","pipeline_id","pipeline","stage")`（同时保留 `schema` 兼容旧裸 dict）。已用 Python 等价模拟验证三场景（纯 schema / 含 contract_version / 纯 legacy）无回归。
  - 同步：`project_code_4f377ea2.zip` 与本地镜像 `adapters/coze/src/` 基本一致（仅 `meta_analysis_core.R` 不同——镜像含 2026-09-01 的 events 兼容修复、云端无，而云端不跑该文件故无影响），已将其余文件同步进镜像；`meta_analysis_core.R` 修复版保留（未被云端版覆盖）。
  - 交付：`coze_full_pkg_v2/meta_analysis_coze_full_2026-09-01_v2.zip`（含 state.py 改名 + events 修复 + `_STAGE_KEYS` 修复，33 文件，强校验通过）。

### Fixed
- **单组率 measure 提示统一（别名归一，2026-09-01 晚）**：消除 PLOGIT vs PLO 双口径文档混乱——统一为 **PLOGIT/PRAW 主口径，PLO/PR 等价别名**（logit/原始比例两包功能等价；PASF/PFT 两包实现不同，不做跨包映射）。
  - `meta_analysis_core.R` `calculate_effect_size`：`measure_up <- toupper(measure %||% "PLO")`，`PLO/PLOGIT → escalc(measure="PLO")`、`PR/PRAW → escalc(measure="PR")`，大小写不敏感，非法值显式报错。
  - `meta_analysis_core.R` `ma_analyze`：默认 measure 从 `PLO` 改为 `PLOGIT`（与 coze 端 `run_task.R` 默认口径一致），back-transform 判断改为 `toupper(measure) %in% c("PLO","PLOGIT")` 双兼容。
  - 文档统一：`references/single_group_meta.md` 加口径统一注记（PLOGIT/PRAW 主口径 + PLO/PR 等价别名 + PASF/PFT 不跨包映射）；`references/data_templates.md` 示例改 `measure="PLOGIT"`；`references/advanced_api.md` 注释改 `PLOGIT(PLO)`；`scripts/extract_assist.py` `measure_hint` 改 `PLOGIT / PRAW / PASF`。
  - 验证：纯 base R `parse()` 语法通过（19 expressions）；PLO/PLOGIT/plogit/PR/PRAW/praw 六种输入路由模拟全对、非法值正确拒绝。
  - 交付：`coze_full_pkg_v3/meta_analysis_coze_full_2026-09-01_v3.zip`（33 文件，五项强校验全过：core measure 别名统一 / core events 修复 / run_task.R events 修复 / stage_envelope envelope_schema / state.py 改名）。**注**：`run_task.R` source 本文件，measure 统一须随 v3 包部署 coze 后方在云端主路径生效。

### Fixed
- **influence 多面板图默认跳过保护（2026-09-01 晚，用户确认"确实是出图慢"）**：死机诊断为「R 引擎冷启动 + influence 7×9 多面板 SVG 出图在 coze 无头 Linux 耗时过长（k 大时分钟级）」后，给三处 influence 出图点加保护——**默认跳过 + warning 提示，确需出图须显式传 `figure.heavy_plots=true`**：
  - 主 pairwise 分支（`single_group_meta`/`pairwise_meta` 等）：`if ("influence" %in% plots) { if (isTRUE(figure$heavy_plots)) { .meta_to_rma 桥接 + .influence_plot } else { warns 追加跳过提示 } }`。
  - `rma` 桥接分支（`meta` 对象转 rma 后出图）与通用 meta 分支：同款 `heavy_plots` 保护。
  - `isTRUE()` 严格语义：仅逻辑 `TRUE` 触发，字符串/数值 `"false"`/`1` 均走跳过。
  - 验证：R `parse()` 语法通过（1416 行）；Python 复刻 `isTRUE` 语义 6 场景全过（默认跳过+warning / heavy_plots=true 出图 / 无 influence 不受影响 / 字符串/数值 heavy_plots 仍跳过 / 用户案例默认核心计算秒回）。
  - 交付：`coze_full_pkg_v4/meta_analysis_coze_full_2026-09-01_v4.zip`（33 文件；run_task.R 与镜像逐字节一致，其余 32 文件与 v3 包零差异，语义校验全过）。**注**：死机案例改用默认（不再传 `influence` 图或已由保护跳过）后核心计算应秒级返回；`figure.heavy_plots=true` 仅在确需 influence 图时显式开启。

### Fixed
- **v5 完整部署包补齐（2026-09-01 晚，用户平台提示"缺少 pyproject.toml/uv.lock/scripts/.coze/docker 等关键文件"）**：前 v1–v4 包仅打 `src/` 运行时代码，缺 coze 平台部署配套，无法直接运行/部署。重建**以 coze 项目根 `adapters/coze/` 为包根**的完整包：
  - **包含**（70 文件）：`.coze`（entrypoint `src/main.py`）、`pyproject.toml`、`uv.lock`、`docker/`（Dockerfile/build.sh/r_packages.txt/system_deps.txt/restore_r_env.sh 等 8 项）、`scripts/`（http_run.sh/setup.sh/setup_r_environment.sh/pre_deploy_check.py 等 8 项）、`src/`（33 文件，含本轮 events/measure/influence 修复）、`tests/`（14 项 R 回归）、`assets/`、`rendering.py`、`README.md`、`.gitignore`。
  - **排除**（依 ct-base 红线 + 噪音）：`coze_contract.md`（红线不打包）、`_deploy/`（嵌套旧包）、`AGENTS.md`/`DEV.md`/`REMOVED_PACKAGES.md`/`TEST_VS_PROD.md`（内部开发/过程文档）、`__pycache__`/`*.pyc`/`.venv`/`.pytest_cache`。
  - 校验：zip 完整性 OK；14 项部署关键文件全在；红线/噪音全排除（`_deploy` 命中实为 `scripts/pre_deploy_check.py` 的字符串误报，实际目录已排除）；6 项运行时修复（events/influence/measure×2/envelope_schema/state.py alias）全在。
  - 交付：`coze_full_pkg_v5/meta_analysis_coze_full_2026-09-01_v5.zip`（70 文件，完整部署形态）。

### Removed
- `adapters/_dev/local_engine.py`：本地 R 引擎残留，按原则删除（无代码 import，仅文档引用）。

### Notes
- NMA（`b1_nma_r` 本地 R）、B2 GRADE / B3 过度声明 / B4 质量门仍为本地启发式，待迁 coze（见 `contracts/migration/v0.1.0/SPEC.md` M3/M4）。
- A/C 大脑（a1/a3/a4/c1-c4）仍为本地启发式，待迁 coze（M1/M2）。
- 接入 coze 部署/发布须等「开发期结束」宣布（DEV_POLICY.json 冻结）。
- **M8 文档清扫（2026-09-01）**：`adapters/README.md` / `AGENTS.md` / `requirements.txt` 中「`local_engine.py` 保留 / 仅参考 / NOT invoked」等过期描述全部改为「已于 2026-09-01 删除，无本地回退」；迁移规格 M8 标记 ✅ DONE。
- **M7 SKILL.md 铁律更新（2026-09-01）**：§0 铁律 4 改为「Coze is the sole source of truth for computation」（唯一计算真相源 / 本地无计算引擎 / 无授权即无法计算=付费化）；§3 执行模型与 §6 失败兜底同步澄清「declined 仅文本说明未用云端分析、绝非本地计算替代」；README_zh-CN 经核查无矛盾表述；迁移规格 M7 标记 ✅ DONE。

---

## [2.5.0] — 2026-08-31 — Phase 1 Block A 本地优先管线驱动器（方向确定与文献/数据准备）

> **目标**：在不触碰 coze 部署的前提下，落地 Phase 1（Block A：A1 选题闸门 → A2 检索委派 → A3 筛选 → A4 提取核验闸）。
> 设计原则：A2 检索委派走本地 `ct-literature`（tool_card → `execute_tool_cards` 本地 subprocess），A4 🔴`extraction_review` 红线闸本地强执；
> A1/A3 的「AI 生成大脑」在 coze 侧（尚未部署），此处提供**本地启发式兜底 + 合规信封**，`use_coze` 占位待 coze 部署后无缝接管。
> 退出标准（路线图 §2 Phase 1）：选题报告/检索结果/筛选建议/提取草稿均可经 stage 信封流转 ✅；A4 闸本地强执 ✅。
> **未覆盖**：A1 双库（Cochrane/PubMed）探针评分与 PROSPERO 查重、A3 AI 筛选精度 —— 依赖 coze 或 ct-registry 部署，当前为离线启发式。

### Added
- **Block A 本地驱动器**（`adapters/block_a.py`，不调用 `run_stage`/`run_meta`，故不触发出站鉴权）：
  - `build_block_a_env(topic, ...)`：构造合规 stage 信封（`contract_version`/`schema`/`pipeline.block="A"`/`stage.id=A1`）。
  - `a1_topic_selection`：本地启发式选题闸门（PICOS 推断 + 范围预警），产出 `next_human_action(type=confirm, gate=none)`，标注 `coze_ready=False`。
  - `a2_literature_search` / `a2_build_tool_card`：构建 `ct-literature` tool_card → `execute_tool_cards` 本地执行 → `_extract_studies` 兼容多形态返回（list / `studies`/`papers`/`results`/`records`/`data.*`）。
  - `a3_screening`：本地启发式去重（by doi/title）+ 排除关键词（retracted/撤稿/abstract only/protocol/letter）标记纳入，产出 `next_human_action(type=review)`。
  - `a4_data_extraction`：解析提取表（list / JSON / 行文本退化）→ 产出 `next_human_action(type=approve, gate="extraction_review", required=True)`。
  - `run_block_a(topic, ...)`：编排 A1→A2→A3→A4，返回与 `run_pipeline` 同构的 dict（`done/await_human/gate/stages[]/tool_card_outputs[]`）；A4 闸未持 `human_decision` 批准 → `done=False/await_human=True/gate="extraction_review"`；`run_block_a(..., use_coze=...)` 预留 coze 接管 seam。
- **测试**（`adapters/tests/test_block_a.py`）：11 例全绿 —— 信封合规、A2 委派构造+解析（monkeypatch `execute_tool_cards` 模拟 ct-literature）、A3 去重/排除、A4 红线闸阻断（无决策）/放行（持 approved 决策）/错阶段拒绝、管线 stages 顺序 A1→A2→A3→A4。

### Notes
- **部署依赖**：`ct-literature` / `ct-registry` 须安装于 `~/.workbuddy/skills/<name>/scripts/ct_literature.py`（或 `ct_registry.py`，真实入口非 `run.py`；见 `tool_mapping_meta.json`）。A2 真实检索依赖本机技能就位；缺失时 `execute_tool_cards` 返回 `status=error`（草稿兜底），管线不崩。详见 [2.5.1]。
- **能力边界**：A1/A3 当前为离线启发式（精度有限，须人工确认）；A4 红线闸已强执，但提取草稿本身待 coze 部署后由 AI 生成并经本闸核验。coze 部署后即可移除 `coze_ready=False` 标记并启用 `use_coze=True`。

---

## [2.5.1] — 2026-08-31 — A2 真实检索打通（tool_mapping 修正 + 结果文件读取）

> **触发**：用户确认 ct-literature / ct-registry 本机安装就绪；实测发现 P0 写的 `tool_mapping_meta.json` 与真实 CLI 不一致，A2 实际无法检索（subprocess 找不到 `run.py`、缺 `--run`、stdout 仅日志）。

### Fixed
- **`tool_mapping_meta.json` 修正**（P0 未核真实 CLI 时臆写）：
  - 入口 `scripts/run.py` → 真实 `scripts/ct_literature.py` / `scripts/ct_registry.py`（`run.py` 不存在）。
  - `cmd` 裸 `python` → `C:/Tools/anaconda3/python.exe`（遵循 LRN-20260614-006）。
  - arg_map 错配修正：ct-literature `--query`/`--condition` → 真实 `--topic`（必填）；ct-registry `--condition`/`--country` → 真实 `--cond`/`--status`（无 `--country` 参数）。
  - 新增 `fixed_flags: ["--run"]`：ct-literature 必须带 `--run` 才发网络（否则 dry-run）；`execute_tool_cards` 现支持无条件追加开关参数。
  - 新增 `arg_map.out_dir → --out-dir`，检索结果落盘到指定目录。
- **`coze_client.execute_tool_cards` 健壮性**：
  - `skill_dir` 的 `~` 经 `os.path.expanduser` 展开（subprocess 不自动展开 ~）。
  - 新增 `_parse_tool_output`：整段 JSON 或逐行 NDJSON 均可解析（ct-literature 逐行 `print(json.dumps(rec))`），无可解析记录回退原始字符串。
- **`block_a.a2_literature_search`**：真实 ct-literature 把数据写入 `--out-dir` 文件（`.merged.json` 的 `works[]` 或各源 `openalex.json`/`europepmc.json`），stdout 仅日志；新增 `_read_literature_dir` 回退读取并归一化为 `{title,year,doi,source,pmid,is_retracted,url}` 去重。

### Added
- 真实端到端验证：`run_block_a('osimertinib NSCLC', ...)` 经本地 `ct-literature` 实拉 OpenAlex + EuropePMC 共 6 篇，A2 阶段 `n=6`，A4 🔴`extraction_review` 闸正确阻断（`done=False/await_human=True`）。

### Notes
- 本环境 `ct-literature`/`ct-registry` 已安装就绪，A2 真实检索已可用；ct-registry 的 `--cond/--status/--max/--drug` 亦已对齐（A1 查重待启用）。
- 回归：test_block_a(11)+test_pipeline_client(7)=18 passed；stage_envelope(8)；test_contract PASS。

---

## [2.5.2] — 2026-08-31 — A1 选题闸门接入真实 ct-registry 查重探针

> **触发**：用户确认 ct-literature/ct-registry 安装就绪后，按建议优先把 A1 选题闸门接到真实 ct-registry 查重（与已验证的 A2 同源、零新依赖）。

### Added
- **`block_a.a1_registry_check(topic, max_results, workdir)`**：真实调 ct-registry 做选题查重探针（CT.gov 来源，不走 WHO/CDE 共享端点配额）。返回 `{status, total, returned, sample[], note}`，`sample` 抽自 `report.xlsx`「试验总表」（登记号/标题/状态/国家/注册日期）。
- **`block_a._read_registry_xlsx(xlsx_path, limit)`**：解析 ct-registry 落盘的 `report.xlsx`（中文表头按子串匹配列；ct-registry 跑完会清理中间 json、仅保留 xlsx）。
- **`a1_topic_selection` 接入 `registry_probe`**：`total>=200` 自动追加「方向可能已较拥挤」、`total==0` 追加「空白/新兴方向」提示，写入 `scope_warning`。

### Fixed
- **`coze_client.execute_tool_cards` 新增 `cwd` 参数**：ct-registry 忽略 `--out-dir`、把结果写相对 `./out` 且仅保留 `report.xlsx`，故 A1 在临时 cwd 跑、再从 `<workdir>/out/report.xlsx` 读，避免污染工作区。
- **`tool_mapping_meta.json` ct-registry 新增 `fixed_flags: ["--run"]`**：ct-registry 与 ct-literature 同需 `--run` 才发网络（否则打 PREVIEW 不检索）——实测发现，补齐后查重才真实生效。
- `run_block_a` 调用 `a1_registry_check` 并 try/except 包裹，注册库异常/缺失时优雅降级（`coze_ready=False`、不阻断 A1）。

### Added (tests)
- `adapters/tests/test_block_a.py` 新增 5 例（共 16 passed）：A1 查重探针日志解析（total/returned/sample）、`run_block_a` 携带真实探针、`a1_topic_selection` 拥挤度/空白方向提示；`run_block_a` 系测试桩掉 `a1_registry_check` 保证离线确定性。

### Notes
- 实测 `run_block_a('osimertinib NSCLC')`：A1 经本地 ct-registry 实拉 **CT.gov total=277**、抽样 3 篇（NCT05583409 / NCT06068049 / NCT04148898），`scope_warning` 自动追加「方向可能已较拥挤」；A2 实拉 6 篇；A4 闸 `extraction_review` 正确阻断。
- 回归：test_block_a(16)+test_pipeline_client(7)=23 passed；stage_envelope(8)；test_contract PASS。

---

## [2.6.0] — 2026-08-31 — Phase 2 Block B 本地优先管线驱动器（分析结果产出：双范式 NMA + GRADE + 过度声明 + 质量门）

> **目标**：在不触碰 coze 部署的前提下，落地 Phase 2（Block B：B1 双范式 meta 分析 → B2 GRADE → B3 过度声明 → B4 质量门）。
> 设计原则：本模块完全本地运行（不调用 `run_stage`/`run_meta`，不触出站鉴权）。B1 pairwise 走纯 Python(numpy) 确定性主引擎；NMA 走**真实本地 R 引擎**（`C:/Tools/R-4.6.1/bin/Rscript.exe`，netmeta 3.6-1），R 缺失/异常优雅降级。B3 过度声明检测为单点实现，被 B4 与未来 Phase 3 C2 复用。B4 🔴`final_inclusion` 红线闸本地强执。
> 退出标准（路线图 §2 Phase 2）：B1 双范式（pairwise + NMA）可跑 ✅；B2 GRADE 降级 ✅；B3 12 模式过度声明 + 防误报 ✅；B4 质量门三重 + 红线闸阻断/放行 ✅。
> **未覆盖**：B1 贝叶斯 NMA（仅频率学派 random/common）、B2 GRADE 自动评级（κ=0.44 仅半自动，须人工确认各域）。

### Added
- **Block B 本地驱动器**（`adapters/block_b.py`，与 `run_pipeline` 同构返回 `{done,await_human,gate,final,stages[],attachments[],tool_card_outputs[]}`）：
  - `build_block_b_env(...)`：构造合规 stage 信封（`pipeline.block="B"`、`stage.id=B1`）。
  - `b1_pairwise_python(studies, effect_measure)`：逆方差加权 + DerSimonian-Laird 随机效应（固定+随机），纯 numpy 确定性；支持 2×2 表（Haldane 0.5 校正）或预计算 (TE,seTE)；输出 k/TE_fixed/se_fixed/ci_fixed/p_fixed/TE_random/se_random/ci_random/p_random/tau²/I²/Q/forest。
  - `b1_nma_r(network_studies, effect_measure, reference)`：**真实本地 R netmeta NMA**（见 Fixed 适配 netmeta 3.6-1），返回 `{status:ok, result:{model,n_treatments,treatments,tau,comparisons[]}}`；失败/缺 R/缺包 → `{status:error/skipped, reason}`（不抛）。
  - `b1_meta_analysis(...)`：编排 pairwise（python 主引擎）+ NMA（R，可选），nma=False 或缺失 network 时标记 skipped。
  - `b2_grade(pairwise, risk_of_bias, indirectness, publication_bias)`：起点 HIGH，按 5 域降级（不一致性 I²≥75→-2 / ≥50→-1 / ≥25→-0.5；不精确 k<3 或 CI 跨零→-1；偏倚风险 high→-1/moderate→-0.5；间接性/发表偏倚 serious→-1）→ High/Moderate/Low/VeryLow；标注 `coze_ready=False`（须人工确认）。
  - `_OVERCLAIM_PATTERNS`（12 模式）+ `detect_overclaims(claims_text, stats)`：单点实现，被 B4/C2 复用；辅助条件 `ci_cross`/`p_sig`/`ns`/`weak_meta`/`to_all` 防误报。
  - `b4_quality_gate(grade_report, overclaims)`：质量门三重（GRADE + 过度声明 + 人工闸），始终产出 🔴`final_inclusion` 人工闸（`required=True`）；存在 high 级过度声明或 GRADE=VeryLow → `critical=True` 阻断自动续跑。
  - `run_block_b(...)`：编排 B1→B2→B3→B4；B4 闸未持 `human_decision` 批准 → `done=False/await_human=True/gate="final_inclusion"`；持 `approved` 决策 → 放行。

### Fixed
- **`block_b._NMA_R_SCRIPT` 适配 netmeta 3.6-1（原 NMA 真实调用恒 `status=error`，Phase 2 收口阻断项）**：
  - 参数名 `Te`/`seTe` → 大写 `TE`/`seTE`（netmeta 3.6-1 不再识别小写别名）。
  - 参数 `reference` → `reference.group`（netmeta 3.6-1 已改名）。
  - NMA 结果字段由 `TE.nma`/`lower.nma` 等（旧版）改为 `.random`/`common` 两套（`TE.nma.random`/`seTE.nma.random`/`lower.nma.random`/`upper.nma.random`/`pval.nma.random`，优先 random 回退 common）。
  - `res$comparisons` 为 `"t1:t2"` 标签向量（非 data.frame），改为 `strsplit(...,":")` 拆出 t1/t2 构造比较表；`res$treatments` 在 3.6-1 为空，改为从拆分后的唯一臂标签推导。
  - 移除 `a$sm %||% "OR"`（`%||%` 来自 rlang，netmeta 命名空间未导入 → 解析报错），改为显式 `if (is.null(a$sm)) "OR" else a$sm`。
  - `reference.group` 为 NULL 时 netmeta 3.6-1 在 `== ""` 判定上崩（length zero）→ 改用 `do.call(netmeta, args)` 条件构造，仅当 `ref` 非 NULL 时加入 `reference.group`。

### Added (tests)
- `adapters/tests/test_block_b.py`：18 例（确定性、离线、monkeypatch `b1_nma_r` 验证优雅降级）+ 2 例真实 R 集成测试（`TestB1NMAReal`，R 缺失时 skip）。覆盖：信封合规、pairwise python 计算/2×2 折算/空、NMA skipped/error 降级、GRADE 高异质性降级/清洁→High、B3 12 模式命中（OC1/OC2/OC3/OC5）与防误报（OC2 CI 未跨零不误报）、B4 红线闸阻断（high 过度声明→critical）/放行/错阶段拒绝/stages 顺序 B1→B2→B3→B4。

### Notes
- 真实 R NMA 实测（`A/B/C` 三臂网络）：`status=ok`、`model=random`、`tau≈0.454`、3 条比较（A:B/A:C/B:C）均带 TE/CI/p；连续型 `MD` 在无 reference 时由 netmeta 自选参照亦通过。
- 端到端 `run_block_b(..., nma=True, network_studies=...)`：pairwise TE_random≈0.481、NMA 3 比较、GRADE=Moderate、B3 命中 OC5（亚组外推）、B4 闸人工批准后 `done=True`。
- 回归：test_block_a(16)+test_block_b(20)+test_pipeline_client(7)+stage_envelope(8)+test_contract = 全绿（共 51 passed）。

---

## [2.9.6] — 2026-08-31 — PDF 数据抓取 P1（文本型 PDF：表格模板 + 叙述正则 + 一致性校验，开发期不发布）

- 新增 `adapters/pdf_extractor.py`：fitz 页型检测 + pdfplumber（lines 策略，等效 lattice，零新依赖）。
  - 表格模板：`T_DICHOT`（2x2 n/N → ai/bi/ci/di 原始计数，臂列关键词/位置定位）、
    `T_CONTINUOUS`（行内 mean±sd 对 → te/sete，n 缺失回退行内整数）。
  - 正文通道：正则候选（dichot_counts / or_ci / md_ci，带页码锚点），零幻觉；不做臂方向推断。
  - 一致性校验：四格表重算 OR/95%CI（Woolf，1%/2% 容差）、零格/事件>总数拦截、te↔CI 对称性与
    宽度互推；CI 不匹配仍回填重算 te/sete（置信度单独降级 needs_review）。
  - 置信路由 verified / needs_review / failed；`to_a4_rows` 直通 fullflow A4 extraction_table。
- 契约 `contracts/pdf_extraction/v0.1.0/SPEC.md`（P1 范围/红线：无扫描件、无 LLM、连续来源强制人工）。
- 测试 `tests/test_pdf_extractor.py` 16 项全绿（校验数学/模板/叙述/合成 RCT PDF 端到端 → b1 冒烟）。
- P1 已知限制：无边框表、无扫描件、跨页表不合并、异形表头需人工列映射（P2）。

---

## [2.9.0] — 2026-08-31 — 本地 coze 镜像测试收口（Level 1 进程内冒烟 + 发布污染守护）

> **触发**：用户确认「可用本地 coze 镜像代码代替 coze 做测试」，并给出两条硬约束——
> (1) 测试数据真实写飞书可接受；(2) 镜像代码发布到 coze 端后必须能正常执行；
> (3)（前序红线仍生效）真实发布代码绝不受本地测试信息污染，且两者差异须白纸黑字标注。
> 目标：在不碰真实 coze 部署的前提下，用本地 `adapters/coze/` 镜像代码验证「图能跑通 + 产物可被 coze_client 解析」，且发布包字节一致。

### Added
- **本地 coze 镜像 Level 1 进程内测试驱动器**（`adapters/tests/coze_local_harness.py`，**唯一**容纳测试桩的文件，绝不写进 `src/`）：
  - 注入 `coze/src` + `adapters` 到 `sys.path`，设 `RSCRIPT_BIN=C:/Tools/R-4.6.1/bin/Rscript.exe`；`local_transport` 直接 `asyncio.run(graph.ainvoke(payload))`，零网络/零鉴权。
  - `run_stage_local` 复用 `coze_client.run_stage` 并在运行时 monkeypatch `_auth_gate = lambda *a,**k: True`（仅内存，不改盘、finally 还原），验证真实 per-stage 契约路径。
  - `smoke_test()` 跑 probe（短路）+ real（3 行 `pairwise_meta`，`sm=MD`）双路径，回传结构化报告（mode/stage_result/next_human_action）。
- **部署前污染校验**（`adapters/coze/scripts/pre_deploy_check.py`，gitignored）：
  - `_check_src_clean`：src/ 禁含 `coze_local_harness`/`local_transport`/`RSCRIPT_BIN = "C:/`/`_auth_gate = lambda`/`COZE_DEPLOY_ENV` 等测试态痕迹。
  - `_check_pyproject_faithful`：pyproject 须保留 coze 运行时依赖（pycairo/dbus-python/PyGObject，本地 `uv sync` 时曾临时移除、发布前须还原）。
  - `_check_harness_not_in_src`：harness 不得出现在 src/ 树。`main()` 退出码 0/1/2。
- **测试-生产差异标注**（`adapters/coze/TEST_VS_PROD.md`，gitignored）：6 维度差异表（运行方式/鉴权/R 路径/R 布局/飞书/S3/依赖）+ 本地 venv 构建须知 + pre_deploy_check 守住项 + 本轮抓到的真实 bug 与验证结论。
- **deploy_retest 新增 G7/G8 两道闸**：
  - G7 本地 coze 镜像冒烟（跑 `coze_local_harness.py`，probe+real 双绿且 real 须回 stage_result + next_human_action）。
  - G8 部署前污染校验（跑 `pre_deploy_check.py`，src 无测试态痕迹、pyproject 与 coze 一致）。

### Fixed
- **真实发布阻断 bug（本地镜像测试抓出）**：`meta_analysis` 节点经 `make_stage_response` 把 `stage` 序列化为 **JSON 字符串**回显，但 `FeishuSaveNodeInput.stage` 声明为 `Dict[str, Any]`，langgraph 同名字段传 str → `ValidationError` 崩溃；**该请求打到 coze 端也会崩**。修复 `adapters/coze/src/graphs/state.py`：`FeishuSaveNodeInput.stage` 放宽为 `Optional[Any]`（与「stage 字符串回显」设计一致）。复测 real 路径 `mode="stage"`、`has_stage_result=true`、EXIT=0。此为合法修复，非测试污染。

### Notes
- **R 引擎交叉验证一致**：镜像 R 引擎 `pairwise_meta` 算出 MD 合并 `0.4812 / CI[0.21,0.75] / I²=0`，与本地 `block_b` Python 引擎数值逐位吻合 —— 两套独立实现互证，镜像图在本地即可视为「coze 端等价」。
- 隔离策略：测试桩只活 `adapters/tests/coze_local_harness.py`；`adapters/coze/` 整体 gitignored；pyproject 已还原（含 pycairo/dbus-python/PyGObject）；发布代码字节一致。
- 未覆盖（仅 coze 运行时存在）：真实 workload-identity 鉴权、真实飞书/S3 写入、Linux `/tmp/r_env` R 布局。
- 回归：deploy_retest 8/8 GO（G1 66 passed / G2-G6 / G7 镜像冒烟 / G8 污染校验）。

---

## [2.9.5] — 2026-08-31 — fullflow HITL 编排器（A→B→C 可交互流水线，开发期不发布）

> **触发**：架构缺口 G1/G4 收口。设计原则（用户 2026-08-31 定）：人-AI 协作，非全自动——
> 低准确度环节随时可打断、改人工介入。spec：`contracts/fullflow/v0.1.0/SPEC.md`。

### Added
- `adapters/fullflow.py`：薄交互控制器 `run_fullflow` / `resume_fullflow` / `FullflowSession`。
  - 三档停靠：P1 块间交接确认（handoff_confirm）/ P2 红线闸（A4/B4/C3/C4，复用块层既有闸语义）/
    P3 任意阶段软停（`pause_at`）；默认停靠集 `DEFAULT_PAUSE_AT`（A1/A3/A4🔴/B4🔴/C1/C3🔴/C4🔴）。
  - 人工决策统一 schema（§6.1）：`approved / revised / skipped / rejected`；
    **红线闸拒 skipped**、rejected 停在原地重放视图、全部决策留痕会话 JSON（审计日志）。
  - revision 走输入参数降级映射（§6.3）：A4 rows → `extraction_table`（list）→ Block B studies；
    其余阶段为 stage_result 事后补丁（模块 docstring 标注限制）。
  - 会话原子落盘（tmp+rename）`fullflow_session_ff_*.json`，断点续跑 + 审计。
  - 进 B 前 `extraction_guard.check_verified` 双保险：未 `stamp --confirm` 的 CSV →
    `guard_blocked`（unverified_extraction 语义），核验后 approve 放行。
  - 红线：控制器**绝不**自动 approve；空/缺 decision 不推进；B 计算仍 coze 唯一路径。
- `block_a/b/c.py`：新增 `pause_at=None` 参数（P3 软停靠，默认 None = 现状行为逐字节兼容）
  与 `_any_approve` / `_soft_stop` 助手；红线闸凭据兼容单 dict / list 累积。
- `adapters/tests/test_fullflow.py`：9 项离线测试（向后兼容 / P3 停靠 / 红线闸+revision 接缝 /
  会话持久化+rejected / 守卫双保险 / skip 语义 ×3），全绿。

### Known limitations（v0.1）
- 续跑 = 重跑当前块（A1/A3/A4 幂等启发式；A2 检索会重复执行，成本可接受）。
- ct-literature tool_card 真实接线未验证（G5，后续单独做）；coze 端 A/C 图未部署（G3）。

---

## [2.9.4] — 2026-08-31 — 运行入口接入 per-stage 管线（run_analysis → run_stage）

> **触发**：重构核心收口——本地 Block A/B/C 驱动器与 coze 端图架构已就绪，但统一入口
> `adapters/run_analysis.py` 仍走 legacy `coze_client.run_meta`（单发式），未接入新架构。
> 本次把运行入口切到 per-stage `run_stage` 信封，使技能运行时与已部署的 ct-meta2 图、本地
> 驱动器对齐（R1 双模仍在客户端层成立：旧 per-task 信封经 run_stage 自动委派 run_meta）。

### Changed
- **`adapters/run_analysis.py`**：
  - 计算请求改构造 Block B「B1.meta_analysis」per-stage 信封（`_build_compute_stage_env`），
    经 `coze_client.run_stage` 发往 ct-meta2（开发期唯一站点，见 DEV_POLICY.json）。
  - 新增 `_normalize_stage(res)`：将 stage 信封规整为既有消费方（`scripts/run_meta.py` +
    `render_html_report`）期望的 `status/stats/figures` 形状；coze 仅回 `stage_result`（无顶层
    `result`）时从 `stage_result.result` 兜底抽取，避免下游渲染/CLI 缺字段崩溃。
  - `run_analysis(..., debug=False)` 新增 `debug` 透传（同 run_stage，隔离飞书测试流量）。
  - 旧 `run_meta` 单发路径移除；`run_stage` 是其超集，向后兼容。coze 失败/未授权仍返回
    结构化错误（`_source` = `coze_error` / `auth_blocked`），不回退本地。
  - **Fix**：`AuthRequiredError` 错误分支误用已移除的旧符号 `_coze_run.__module__`，改为
    `_coze_run_stage.__module__`（否则授权拦截分支会 `NameError` 崩溃而非返回友好提示）。

### Docs
- `AGENTS.md` / `SKILL.md`：运行路径 `run_meta` → `run_stage`（per-stage envelope）；端点默认改
  `ct-meta2.coze.site`（开发期 ct-meta 已禁用，见 DEV_POLICY.json）。

### Verified
- 真实调用 ct-meta2 端到端（debug=True 隔离飞书）：`run_analysis('pairwise_meta', rows[3], {sm:MD,model:REML}, {format:svg})`
  → `status=ok` / `mode=stage` / `source=coze` / `stats`+`figures`(森林图) 齐全 / HTML 报告生成
  / coze_elapsed≈4.3s；合并效应量与本地镜像 R 引擎一致。
- `deploy_retest` 8/9 GO（G1–G8 全绿；G9 发布冻结 NO-GO 为开发期预期）。

---

## [2.9.3] — 2026-08-31 — 真实调用 ct-meta2 端到端验证 + 修复 run_stage transport 解包 bug

> **触发**：coze 端 (ct-meta2) 已部署更新代码，用户要求真实测试。新增 `adapters/tests/coze_live_test.py`（直连 ct-meta2，debug=True 隔离飞书归因）。

### Fixed
- **`coze_client.run_stage` 真实调用崩溃**（被本地进程内测试掩盖的发布风险）：
  - 根因：`_post_run_with_fallback`（真实 HTTP transport）返回 **4 元组** `(raw, elapsed, used_fallback, final_url)`，
    而 `run_stage` 此前只 `raw, elapsed = transport(...)` 解包 2 个值 → `ValueError: too many values to unpack`。
  - 本地 `local_transport` 返回 2 元组，所以 Level-1 进程内冒烟测试从未暴露；真实出站必崩。
  - 修复：向后兼容两种形态 `raw, elapsed = _tr[0], _tr[1]`（`run_meta` 本就按 4 元组解包，无此问题）。

### Verified（真实出站到 ct-meta2）
- per-stage 信封正确往返：`mode=stage` + `stage_result` + `next_human_action`（coze 端 `schema→envelope_schema` alias 修复生效）。
- R 引擎真实执行 `pairwise_meta`：**MD 合并 = 0.4812 / 95%CI[0.2097, 0.7527] / I²=0**，与本地镜像 `block_b` Python 引擎**逐位吻合**（交叉验证）。
- coze 端 R = `4.6.1`、`meta 8.5.0 / metafor 5.0.1 / netmeta 3.6.1` 包齐全，森林图 SVG 已生成。
- `probe=True` 探测走 legacy 简化返回（status=ok、往返成功），真实分析走 stage 正常 —— 符合预期。
- **诚实标注**：`feishu_write_success` 在返回中为 `null`（coze 端未回该字段，可能 debug 模式跳过 / 凭据未配），真实飞书落库状态未能从响应确认。

---

## [2.9.2] — 2026-08-31 — 同步 coze 端 (ct-meta2) latest：Pydantic `schema` 字段冲突修复

> **触发**：用户上传 `meta_analysis_coze_latest.zip`（coze 端更新后的最新代码），要求比对差异并把需要的内容合并回本地镜像 `adapters/coze/`。

### Fixed
- **Pydantic `schema` 保留名冲突**（pyright 类型检查报错）：
  - `src/graphs/state.py` 3 处 `schema: Optional[str]` 字段重命名为 `envelope_schema`，改用 `Field(alias="schema")` 保持 JSON 序列化 / 反序列化兼容。
  - 3 个请求模型（`MetaRequest` / `GraphInput` / `MetaAnalysisNodeInput`）的 `model_config` 增加 `populate_by_name=True`，支持字段名与别名同时使用。
  - 验证：本地镜像冒烟 `real` 路径 `mode=stage` / `has_stage_result=true` / `has_next_action=true` / EXIT=0 —— 别名改动与现有信封契约向后兼容，**未破坏 per-stage 往返**。

### Added
- 合并 coze 端新增文件：`rendering.py`（SVG 内联渲染工具）、`assets/advanced_functions.R`（`run_task.R` 第 41 行 source 引用，真实在用）。

### Changed
- 同步 coze 端文档/锁文件：`AGENTS.md` / `DEV.md` / `REMOVED_PACKAGES.md` / `uv.lock` / `.gitignore`（与 coze 端 latest 逐字节一致）。

### 保留与清理
- **未丢失本地真实 bug 修复**：coze 端 `state.py` 已包含 `FeishuSaveNodeInput.stage: Optional[Any]`（修复 per-stage 请求打到 coze 的 `ValidationError` 崩溃），合并后本地镜像仍保留。
- 清理本地镜像 stray：`src/r_engine/Rplots.pdf`、`src/r_engine/_zh_extract.json`（R 跑出/孤儿，不在 coze 端）。
- 本地自有交付物保留：`TEST_VS_PROD.md` / `_deploy/` / `tests/test_stage_envelope.py` / `docker/r_packages_with_versions.csv`。

### 验证
- `pre_deploy_check.py` → EXIT=0；`deploy_retest` G7/G8 GO；全量 8/9 GO（G9 发布冻结 NO-GO 为开发期预期）。
- 最终 diff：coze 端 latest 与本地镜像 `modified: []`、`only_in_zip: []` —— 镜像现为 coze 端忠实快照。

---

## [2.9.1] — 2026-08-31 — 开发期策略：禁用 ct-meta + 冻结发布（DEV_POLICY 单源管控）

> **触发**：meta-analysis 进入架构大规模重构开发期，用户下达两条持续生效的硬约束——
> (1) 暂时禁用 ct-meta 调用，ct-meta2 为 coze 唯一调用站点；(2) 暂时禁止 meta-analysis 发布新版本。
> 两条约束持续生效，**直到用户明确告知开发期结束才取消**。故落地为「单源真相文件 + 代码读取 + 闸门拦截」三件套，便于开发结束时一键还原。

### Added
- **开发期策略单源真相**（`adapters/DEV_POLICY.json`，随技能发布包分发但仅开发期生效）：
  `{dev_period, ct_meta_disabled, publish_freeze, set_at, reason, unset_when, effects}`。
  无该文件 / `ct_meta_disabled=false` → 正常生产态（ct-meta 主 / ct-meta2 回退）。
- **`adapters/publish_guard.py`**（仅标准库）：`is_publish_frozen()` / `assert_publish_allowed(platform)` /
  `main()`（退出码 0=允许 / 2=冻结）。任何 meta-analysis 新版本发布（GitHub/SkillHub/ClawHub）前的权威拦截点。
- **deploy_retest 新增 G9「发布冻结状态（开发期）」闸**：读 `DEV_POLICY.json` 的 `publish_freeze`；
  冻结中 → **NO-GO**（明确提示删除该文件即解除）；否则 GO。本闸门只核对状态，不触碰发布动作。

### Changed
- **`adapters/coze_client.py` 端点选择改由 `DEV_POLICY.json` 动态决定**：
  新增 `_dev_ct_meta_disabled()`（读 `DEV_POLICY.json`）；开发期 → `DEFAULT_ENDPOINT=ct-meta2`、
  `FALLBACK_ENDPOINT=""`（**彻底禁用 ct-meta，无回退**）；正常态 → `ct-meta` 主 / `ct-meta2` 回退。
  原硬编码的 `DEFAULT/FALLBACK` 常量定义上移删除，统一在覆盖段按策略赋值。
  `_post_run_with_fallback` 增加 `FALLBACK_ENDPOINT` 空值守卫（`FALLBACK_ENDPOINT and ...`），
  确保开发期空回退端点绝不触发重试。
- token 无需改动：`coze_token.py` 已按 endpoint 分别内嵌 ct-meta2 / ct-meta JWT，切到 ct-meta2 自动用其专属 token。

### Notes
- **开发期还原步骤**（用户结束开发期时）：① 删除 `adapters/DEV_POLICY.json`；② 还原 `coze_client.py`
  覆盖段（`DEFAULT/FALLBACK` 回切 ct-meta/ct-meta2，删除 `_dev_ct_meta_disabled` 逻辑）——或直接
  `git checkout` 该文件；③ `config.json` 白名单可保留 ct-meta（不再被调用即无害）。还原后 G9 自动转 GO。
- **发布冻结优先级高于用户确认**：即使用户后续单独确认「发布」，开发期内仍须拒绝（G9 拦截 + 我不主动发布），
  必须待用户先明确结束开发期。这与前序「发布须用户确认」红线叠加，构成双重闸。
- **`config.json` 白名单保留 ct-meta**：仅影响 auth 授权列表，不影响调用路径（开发期 ct-meta 已无任何调用），最小化改动面。
- 验证：`coze_client.DEFAULT_ENDPOINT == ct-meta2` 且 `FALLBACK_ENDPOINT == ""`；`publish_guard.py` 退出码 2；
  `deploy_retest` 现 **8/9 GO（G9 冻结 NO-GO，符合预期）**。

---

## [2.8.0] — 2026-08-31 — Phase 4 收口：deploy_retest 全管线闸门 + §16/§20.11 红线核对

> **目标**：在 Phase 0–3 四阶段本地驱动器就绪后，落地发布前收口闸门，对齐 ct-base §16 发布前检查清单与 §20.11 coze 接口向后兼容硬约束；**不自动 push/publish**（发布属用户红线，须用户确认）。
> 设计原则：deploy_retest 离线、零网络、零出站；只做「只读核对 + 本地计算校验」，绝不发起出站请求、绝不自动改源、绝不触发 coze 部署/git push/平台 publish。

### Added
- **`adapters/deploy_retest.py`** — 部署前全管线闸门（6 道子闸门）：
  - G1 pytest 测试套件（block_a/block_b/block_c/pipeline_client/stage_envelope）→ 66 passed
  - G2 §20.11 契约向后兼容（`test_contract.py` 退出码 0 + `BACKWARD_COMPAT.md` + `coze_contract.md §9.5` R1–R5）
  - G3 信封契约：A/B/C 三驱动器返回与 `run_pipeline` 同构信封 + 阶段顺序 + 四道红线闸（extraction_review/final_inclusion/reference_verification/manuscript_approval）接线且未退化为自动放行
  - G4 §16.7 发布排除：`.gitignore`/`.clawhubignore` 均含 `adapters/coze/` 与三类 coze 接口文档
  - G5 §16.8 密钥泄漏扫描（ct-base `publish_secret_scan.py --warn-only`）：BLOCK 级才阻断
  - G6 §16.10 R 引擎公式审计：pairwise 逆方差/DL τ² 不变量 + NMA 真实本地 R(netmeta) 调用成功
  - 全 GO → 退出码 0；输出人类可读报告 + 可选 `--json` 报告（路径做 `/c/`→`C:/` 归一化）

### Fixed
- deploy_retest 末尾写 JSON 报告时 Git-Bash 风格 `/c/...` 路径在 Windows 下 `open()` 失败 → 加 `_norm_path` 归一化 + 父目录 `makedirs`；默认报告写入 `adapters/`（不在发布包外落盘）。

### 红线核对结果（逐项）
- §16.7 ✅：`adapters/coze/`、`**/coze_contract.md`、`**/coze_system_prompt_v*.md`、`**/ops.md` 双平台 ignore 齐备；`adapters/coze/` 经验证 `git ls-files` 未跟踪（不进发布包）。
- §20.11 ✅：`coze_contract.md §9.5`（R1–R5 向后兼容保证）与 `contracts/pipeline_stage/v1.0.0/BACKWARD_COMPAT.md` + `test_contract.py`（含 R1 双模 legacy 用例）齐备；`test_contract.py` 为独立脚本（`sys.exit(1)` + 打印 PASS/FAIL），按退出码判定（非 pytest 收集，故 pytest 显示 "no tests ran" 为误读）。
- §16.8 ✅ 密钥扫描：**无 BLOCK 级泄漏**；23 条 WARN 全为误报/策略允许——(a) coze JWT `aud`（受众声明，公开元数据，非签名密钥；用户已明确 coze 凭据允许发布）写入 `CHANGELOG.md` 历史记录；(b) 飞书多维表格 app_id/table_id 仅存于 `adapters/coze/coze_contract.md`（已 §16.7 排除）；(c) `covarian`/`frequent`/`build_V_` 等 R 源码变量名/文档词。跟踪文件中无任何真实私钥/云密钥形态（`sk-`/`AKIA`/`ghp_`/私钥头）。
- §16.10 ✅：pairwise 逆方差加权均值不变量（等 SE → 简单平均）+ CI=TE±1.96·SE + τ²≥0；NMA 真实本地 R `netmeta` 调用 `status=ok` 且 comparisons 非空。

### 边界 / 诚实标注
- deploy_retest 仅做离线核对；coze 端实际部署与 §12.4 实测（老请求仍含 `result`）仍待用户确认后执行。
- 发布（GitHub→SkillHub→ClawHub）属用户红线，**本版本未执行**：仅本地收口 + 闸门 GO，停在 push/publish 前。

---

## [2.7.0] — 2026-08-31 — Phase 3 Block C 本地优先管线驱动器（论文撰写与修改）

> **目标**：在不触碰 coze 部署的前提下，落地 Phase 3（Block C：C1 初稿 → C2 AI 评审 → C3 参考完整性核验 → C4 证据表+投稿前 QA）。
> 设计原则：本模块完全本地运行（不调用 `run_stage`/`run_meta`，不触出站鉴权）。C1 为本地结构化骨架生成器（数字自动填充 B1-B4）；C2 复用 `block_b.detect_overclaims`（B3 单点实现）；C3 参考完整性核验为 🔴`reference_verification` 红线（结构/PRISMA 层，真实 CrossRef/撤稿库核验待 coze 接管）；C4 含 🔴`manuscript_approval` 终闸。红线闸名严格复用 `coze_client._REDLINE_GATES`。
> 退出标准（路线图 §2 Phase 3）：初稿 + 参考核验通过 + GRADE 证据表 + QA 清单，C3/C4 双红线闸本地强执。
> **未覆盖**：C1 真实自然语言成稿（须 coze LLM 接管）、C3 真实 CrossRef/撤稿库核验（须 coze 端 + 外部 API）。

### Added
- **Block C 本地驱动器**（`adapters/block_c.py`，与 `run_pipeline` 同构返回 `{done,await_human,gate,final,stages[],attachments[],tool_card_outputs[]}`）：
  - `build_block_c_env(topic, ...)`：构造合规 stage 信封（`pipeline.block="C"`、`stage.id=C1`）。
  - `_extract_b_summary(b_env|analysis)`：从 `run_block_b` 输出信封或归一 dict 抽取 B1-B4 摘要（pairwise/nma/grade/overclaims/critical），供 C 阶段消费。
  - `c1_draft(topic, b_summary, studies, overclaim_hits)`：结构化 Markdown 初稿骨架（摘要/背景/方法/结果/讨论/结论/参考文献），B1-B4 统计量（k/合并效应/CI/p/I²/τ²/GRADE/NMA 模型）自动填充；B3 检出过度声明以「⚠️ 待核验」标注于讨论段，不擅自删改结论。
  - `c2_ai_review(manuscript, b_summary)`：复用 `block_b.detect_overclaims`（B3 单点实现），对初稿全文做过度声明评审；无 manuscript 时回退 B3 已有命中。
  - `c3_reference_verify(manuscript, sections, references)`：🔴 参考完整性核验（结构层）——必含章节（背景/方法/结果/讨论/结论）缺失→critical；提供参考时每条须有 doi/pmid、撤稿文献→critical；无参考→结构通过但 `coze_ready=False`（待 coze 接 CrossRef/撤稿库）。
  - `c4_evidence_qa(b_summary, c2_hits, c3_report)`：GRADE 证据表（来自 B2）+ 投稿前 QA 清单（统计量报告/异质性/证据表/过度声明处置/参考核验/high 过度声明已处置）；终闸 `manuscript_approval`（`required=True`），critical = C3 critical 或 C2 含 high 过度声明。
  - `run_block_c(topic, studies, b_env, analysis, references, human_decision)`：编排 C1→C2→C3→C4；红线闸解析按 C1→C4 顺序取首个未批准闸为阻断点；`human_decision` 支持单 dict 或 list[dict]（累积多闸批准，单轮即可放行 C3+C4）。

### Added (tests)
- `adapters/tests/test_block_c.py`：**15 passed**（确定性、离线、不触 coze/R）。覆盖：信封合规、C1 章节齐全+数字填充+过度声明标注、C2 复用 B3 命中 OC1/良性无命中、C3 缺章→critical/撤稿→critical/无参考→结构通过且 coze_ready=False、C4 证据表+QA 与 high 过度声明→critical、C3→C4 双红线闸阻断顺序与放行（含 list 累积批准 done=True）、错阶段决策无效、stages 顺序 C1→C2→C3→C4。

### Notes
- 端到端 A→B→C 链验证：`run_block_b(...)`（真实 R NMA，grade=Moderate）→ `run_block_c(analysis=b_env, references=None)`（双闸 list 批准）→ `done=True`、C1 初稿 872 字符/7 章节、C4 GRADE 证据表+6 项 QA。
- 回归：test_block_a(16)+test_block_b(20)+test_block_c(15)+test_pipeline_client(7)+stage_envelope(8) = **66 passed 无回归**；test_contract.py 无用例。
- 能力边界（诚实标注）：① C1 为结构化骨架生成器（本地启发式填数），真实自然语言成稿须 coze LLM 接管（`coze_ready=False`）；② C3 真实 CrossRef/撤稿库核验须 coze 端 + 外部 API，本地仅做结构/PRISMA 层；③ C2 复用 B3 规则匹配，AI 语义级润色评审待 coze。coze 部署后即可移除 `coze_ready=False` 标记并启用 `use_coze=True` seam（同 Block A/B 设计）。

---

## [2.4.0] — 2026-08-31 — Phase 0 per-stage Pipeline 客户端骨架（本地薄客户端 + coze 双模路由 R1）

> **目标**：把已确认的「本地薄客户端 + coze 编排引擎」架构（见 `meta_analysis_roadmap.md` Phase 0）
> 从规格层落到可运行骨架。契约（SPEC/双 schema/示例/`test_contract.py`）已于前序工作定稿，本版本实现两端代码。
> 退出标准（路线图 §2）：① 老 `run_meta` 请求仍返回 `result`（R1 实测通过）✅；② 新 `run_stage` 端到端
> 跑通 Block B（单阶段计算）✅；③ `test_contract.py` PASS ✅ + `test_pipeline_client.py`(7) + `test_stage_envelope.py`(8) 全绿 ✅。

### Added
- **本地 per-stage 客户端**（`adapters/coze_client.py`）：
  - `run_stage(env)`：发送 per-stage 信封；旧 per-task 信封（无管线字段）**委派 `run_meta`**（R1 双模在客户端层成立）。
  - `parse_stage_response(outer)`：解析 `stage_result`/`next_human_action`/`tool_cards`（coze 端以 JSON 字符串承载，与 `result` 同模式）+ 兼容旧 `result` 内层（R2）。
  - `execute_tool_cards(cards)`：复用 need_tool 范式——`request_upload` → 本地 `_upload_file` 经预签名 PUT 上传；`ct-*` → 查 `tool_mapping_meta.json` 构造 CLI 执行（草稿兜底）。绝不抛错中断管线。
  - `run_pipeline(initial_env)`：薄客户端编排（发→解析→执行 tool_card→回填 `stage_context`→续跑），**红线闸强执**（`gate≠none & required` 阻断自动续跑，交人工）。
  - `_upload_file` / `download_attachments`：文件双向传输（S3 预签名 PUT/GET，sha256 校验）。
  - `attach_billing(env, account_id, billing_token)` + `build_stage_payload`：`account_id`/`billing_token` 仅透传（预留接口，与 `query_origin` 独立）。
  - `_post_run_with_fallback`：抽取 run_meta / run_stage 共用的「主端点 → token 失败回退 FALLBACK_ENDPOINT」逻辑，消除重复。
- **coze 端 R1 双模路由**（`adapters/coze/`）：
  - `src/graphs/state.py`：所有 pydantic 模型加 `model_config = ConfigDict(extra="ignore")` 并新增可选字段
    `contract_version/schema/pipeline_id/pipeline/stage/stage_context/attachments/account_id/billing_token`（请求侧）
    + `GraphOutput`/`MetaAnalysisNodeOutput` 并列 `stage_result`/`next_human_action`/`tool_cards`/`stage`（str 模式，§9.1）。
  - `src/graphs/nodes/stage_envelope.py`（纯标准库，可单测）：`is_legacy_request`（R1 双模判定，兼容裸 dict 与 pydantic `model_dump`）、
    `make_stage_response`（把 R 引擎内层包成 stage 信封，R2：`result` 与 stage 字段并列）。
  - `src/graphs/nodes/meta_analysis.py`：`meta_analysis_node` 按双模路由——legacy → 仅填 `result`；stage → 填 `result` + stage 字段。**未重部署前本地侧已生效，coze 仍返旧结构（adapter 走兼容分支）。**
- **`adapters/tool_mapping_meta.json`**：Block A/C 需要的 `ct-*` 本地调用映射（`ct-literature`/`ct-registry`）；`request_upload` 为内建特殊类型不在表内。
- **测试**：`adapters/tests/test_pipeline_client.py`（7 例：R1 委派/解析/红线闸阻断/上传/下载/billing 透传）、
  `adapters/coze/tests/test_stage_envelope.py`（8 例：双模判定/字符串字段/R2/gate 映射）。

### Notes
- coze 端 `meta_analysis.py` 双模分支为**代码完成、待部署**状态（本地无 langgraph 运行环境，无法在此端到端跑；逻辑由 `stage_envelope` 单测覆盖）。部署前须按 coze_contract §12.4 用老 `run_meta` 风格请求 POST `/run` 断言仍含 `result` 且 `json.loads(result)` 含 `status`/`stats`/`figures`。
- P0 仅收口骨架；Block A/B/C 各阶段的具体逻辑（选题闸门、检索委派、GRADE、过度声明检测、初稿生成、参考核验）为 Phase 1–3 内容，经同一 `run_stage` 信封接入。

---

## [2.3.2] — 2026-08-30 — precomputed 轨 validate 字符串列误判修复

### Fixed
- **`scripts/extract_assist.py` `validate` 字符串列误判**：`precomputed` 类型的唯一 `str` 列 `effect_type`（取值如 `lnOR`/`SMD`）被旧逻辑当作数值列校验，调 `_to_num` 误报「非数值且非 NR」，导致所有 `precomputed` 轨道提取表无法通过 `validate`、卡死在计算轨入口。新增 `if kind == "str": continue` 透传分支（与协变量 `str` 透传逻辑一致），仅对 `int`/`float` 列做数值校验。`precomputed` 轨现在可正常 `validate` → `stamp --confirm` → `run_meta`。

---

## [2.3.1] — 2026-08-30 — 抽取链 P0 三修复（BCG 案例打脸：协变量/多臂/零事件）

> **触发**：用 BCG 疫苗预防结核病（Colditz 1994 经典 13 项 RCT）走完整「选题→检索→筛选→提取→合并」
> 全链路，实跑暴露出抽取链 3 个会被真实数据打脸的缺口，全部为 P0。已用真实 BCG 数据做端到端回归：
> 含协变量 + 单零单元的干净版（12 项 RCT）经 coze 复现 pooled RR=0.532 (95%CI 0.365–0.776)、I²=84.4%，
> 与教科书结论 RR≈0.58/I²≈87% 一致。

### Fixed
- **P0-1 协变量列缺失**（`scripts/extract_assist.py`）：原 binary 模板只有主结局列，纬度/分配方法等在
  提取阶段即被丢弃，亚组/元回归做不了。新增 `scaffold --covariates "latitude,allocation,vaccine_type"`
  动态追加协变量列，类型自动判定（数值型 float / 分类型 str），provenance 记录协变量 schema；
  `validate` 对协变量做类型/范围校验。
- **P0-1 协变量透传**（`scripts/build_request.py`）：CSV 中核心结局列之外的「额外列」（协变量 + arm 臂标识）
  自动透传进 coze payload；数值协变量 float 强转、分类/臂列字符串透传（`_classify_non_numeric_cols`）。
  同时修复 CSV 读取用 `utf-8-sig` 剥 BOM——否则首列 `study` 变 `\ufeffstudy`、study 值丢失（BCG v1 即已潜伏）。
- **P0-2 多臂独立性**（`scripts/extract_assist.py`）：binary/continuous schema 加可选 `arm` 臂标识列；
  `validate` 检测同一 study 多行（多臂/多对照）→ 提示独立性风险（直接全纳破坏独立性、低估 SE，建议 RVE 或按臂拆分）。
- **P0-3 零事件校验**（`scripts/extract_assist.py`）：`validate` 检测零事件单元——
  单零（一方 event=0）告警（引擎 +0.5 连续性校正可算）；**双零（两组皆 0）硬错误**（该研究 RR/OR 完全无信息，
  metafor::escalc 会抛 `invalid 'pos' value` 崩溃，实测确认）→ 须剔除或改用 `--measure RD`。
- **`references/data_templates.md`**：binary 表增补 `arm` 列、协变量列用法、零事件/多臂校验说明。
- **P0-4 抽取表 type 推断误把选填列当必填**（`scripts/extract_assist.py`）：`validate` 的 type 推断原用整张 schema 列集合（含 opt 列 `year`/`arm`）做 `issubset` 判定，导致用户按 `data_templates.md` 必填列（不含 `arm`）填表时被判「无法从列名推断 Type」。改为只匹配**非 opt 必填列**（binary 必填 = study/n_exp/event_exp/n_ctrl/event_ctrl），选填列存在与否不再影响推断；缺真正必填列仍正确拦截（rc=2）。回归 `[1b] validate ok` 由 FAIL→PASS，全回归 11/11。

---

## [2.3.0] — 2026-08-30 — 上游编排 + 数据提取助手（human-in-the-loop）

> **触发**：用户要求把 meta-analysis 从「只算合并效应量」升级为覆盖 Meta 全链路的编排器
> （方向判断 + 文献检索整理 + 文献清理 + 数据提取 → 直通计算轨）。经可行性核对，①方向判断
> 本技能已有雏形（topic-selection）、②检索去重归 ct-literature、③初筛已有
> prisma_bridge/agent 层；唯一缺且最难自动化的是「纳入研究 → Type 1/2/3 数据」这条抽取链，
> 故本次只新增「抽取助手 + 人工核验闸」，不把检索/清洗塞进本技能。
>
> **本版本已通过线上回归**：`tests/regression_live.py` 全绿（守卫拦未核验 / coze 真算出真实 RR / 本地闭环）。
> 实际发布到 GitHub / ClawHub / SkillHub **仍需用户确认后执行**（红线：推送/发布一律先停下等确认）。

### Added
- **`scripts/extract_assist.py`（数据提取助手）**：`scaffold` 按 Type 1/2/3/3b/3c/3d/3e 生成
  空白抽取表（仅含数据列，可直接喂 `run_meta.py --data`）+ 同伴 `<csv>.provenance.json`
  （`verified_by_human=NO`）；`validate` 按 `data_templates.md` schema 校验列名/数值合理性
  （event≤n、CI 方向、r∈[-1,1]、缺失标 NR）；`stamp --confirm` 在人工核验后把
  `verified_by_human` 置 YES；`types` 列出支持的 Type。纯 stdlib，对齐 scripts/ 约定。
- **`scripts/extraction_guard.py`（人工核验闸）**：`check_verified(data_path)` 检查同伴
  provenance 的 `verified_by_human`；未核验 → 拦截；无同伴文件 → 视为人工手搓 CSV 放行；
  非 CSV（内联 `--data-json`）→ 跳过。返回 `(ok, reason, status)`。
- **`run_meta.py` 接入守卫**：入口新增抽取核验闸，未核验提取 CSV 返回
  `META_STATUS=unverified_extraction` 并非零退出（exit 3）；新增 `--trust-data` 显式担责兜底
  （仅用于确认可信的存量/手搓 CSV）。
- **`references/upstream_orchestration.md`**：上游编排总文档——把方向判断(topic-selection) →
  检索去重(ct-literature) → 初筛+PRISMA(prisma_bridge) → 数据提取(extract_assist) → 计算轨
  (run_meta) 串成命令链，含接缝护栏与 `included_records≠included` 陷阱说明。
- **SKILL.md 升级定位**：summary/description 增补「上游编排」；triggers 加
  `系统综述全流程`/`从检索到meta分析`/`文献检索后做meta`/`检索→筛选→提取→合并`/`数据提取 meta`；
  新增 §2.3 Upstream orchestration；§6 增补数据提取红线（未核验禁止直灌）。
- **`references/systematic_review_fullflow.md`（全流程模式 playbook，@skill 入口）**：把
  meta-analysis 作为「编排器」的统一入口落为可执行 playbook——列出触发词、Stage 0 启动确认、
  5 阶段命令链（选题→ct-literature 检索→初筛+PRISMA→抽取助手→run_meta）、两道不可跳过的人工闸
  （Stage 3 最终 `included` 数 / Stage 4 `stamp --confirm`）、失败与边界处理。
- **SKILL.md 新增 §2.4 系统综述全流程模式**：把 full-flow 触发意图映射到
  `systematic_review_fullflow.md`，并再次声明两道人工闸与「不新增 classify 任务类」的定位。
- **triggers 扩充**：加 `系统综述全流程模式`/`系统综述流程`/`系统综述一站式`/`meta 全流程`/`全流程meta`/
  `从选题到meta分析`/`从选题到合并效应量`/`systematic review workflow`/`systematic review full pipeline`/
  `full meta pipeline`。
- **`extract_assist.py scaffold --studies-file`（纳入清单自动预填）**：新增 `--studies-file`，
  读取 Stage 3 人工确认的最终纳入清单（`.json` 数组 / `{"included":[...]}` / `{"studies":[...]}`，
  或 `.txt`/`.csv` 每行一个），自动预填 study 列；与 `--studies` 合并去重；来源记入同伴
  `.provenance.json` 的 `included_list_source` 以便溯源。缺失文件报错退出（exit 2）。
  全流程 playbook Stage 3 在人工闸确认后写 `included_studies.json`，Stage 4 用
  `--studies-file included_studies.json` 自动预填，免去手动重列研究名。
- **coze 入参 `user_language` 备用字段**：`build_request.build()` 现向 coze 入参 `params` 注入
  `user_language`（中文 `zh` / 英文 `en`），供 coze 端决定报告/图表文案语言，**属备用输入、不强制覆盖
  coze 自身判定**。支持「内容级」自动检测 + 显式覆盖：
  - **内容级判定（默认）**：未传 `--language` 时按【输入 query 文本】判定（含 CJK→zh，纯英文→en），
    解决「中文系统 + 英文输入」被 `i18n._current_lang()`（系统 locale）误判 zh 的盲区；query 为空时
    才回退系统 locale。`run_meta.py` / `build_request.py` 均新增 `--language zh|en|中文|english|...`
    入参，可显式覆盖（中英多写法归一化：中文语境→zh、英文→en、未知值原样小写透传），显式参数最高优先。
  - 不改 `i18n._current_lang()` 本身（那是全库 UI 文案按系统语言显示用的契约，跨技能共用）。
  - **2026-08-30 重构**：meta-analysis 侧不再自带 `_LANG_ALIASES` / `_normalize_language` / `detect_text_language` 三件套，改为经 `importlib` 以别名加载 ct-base 共享 `i18n`（`ctbase_i18n`），由 `ctbase_i18n.resolve_user_language(query, override)` 统一实现三级判定；单一事实来源上移 ct-base（详见 ct-base CHANGELOG 同日记）。

### Changed
- **AGENTS.md**：新增 §8 Upstream Orchestration & Extraction Guard；`scripts/` 目录结构补两条新脚本。

### Safety / 红线
- **数据提取不可无人值守直灌**：全文获取受限（付费墙）、效应量抽取精度属医学关键、系统综述要求
  双人独立抽取+仲裁。抽取环节强制 human-in-the-loop；任何 `extract_assist` 生成、未 `stamp --confirm`
  的 CSV 一律被 `run_meta` 拦截至 `META_STATUS=unverified_extraction`。

---

### A 档（并入 2.3.0）：综述流程类路由 + RoB/RoB Summary 修复 + PRISMA 投稿级

> **触发**：ct-update 对 meta-analysis 的 10 条 P1 建议中 C/D/F/G/H/I 共 5 项路由/代码
> 缺口，配合 R metagear 0.7 本地实测结论（仅取 plot_PRISMA 一个能力就够本）一次性收口。
>
> **本档随 2.3.0 一并发布**（与 B 档同属一次未发布累积）。部署/发布按 ct-base 发布规约走，
> 发布前已通过线上回归（HTTP 200 ≠ 任务成功，详见 ct-base LRN-20260817-002）。

### Added
- **classify 路由综述流程类 task（6 个）**：`scripts/classify.py` 新增 `prisma_flow` /
  `prisma_checklist` / `rob2` / `rob_summary` / `grade` / `ipd_meta` 路由。原实现
  只识别 6 个效应量 task，综述类一个不认——7 句相关请求 100% 误判为
  `pairwise_meta`。最危险的一例是「对这 12 项研究做偏倚风险评价」：句中含
  「研究」+ 数字，绕过了旧的 `has_data` 闸门，直接提交 coze 静默返回答非所问
  的合并效应量（不报错、给错答案，属最危险的一类误路由）。新路由对
  `REVIEW_TASKS` 走独立缺参判定：`prisma_flow` 缺数字 → 要 8 个筛选计数；
  `prisma_checklist` / `grade` → 纯 params 全默认跑；`rob2` / `rob_summary` 缺
  judgement 取值词 → 要 Study+D1..D5 判定表。
- **绕过「PRISMA 2020」版本号陷阱**：新增 `_has_prisma_counts` 剥离 `prisma 20xx`
  版本短语后再判数字，否则「画 PRISMA 2020 流程图」的「2020」会被当成筛选
  计数（带全 0 参数出空图）。
- **`run_task.R` 注册 `rob_summary` task**：`plot_rob_summary` 早已实现但**从未
  注册 task**，用户无从触发；现独立 task 出图，与 `rob2` 同数据契约。
- **`metagear` 0.7 重引入核心依赖**：仅取 `plot_PRISMA`（配色 `cinnamonMint`
  接近 PRISMA 2020 statement 官方推荐、纯 grid 矢量、零 GUI 依赖，coze Linux
  无头容器可直接跑）。净新增 0 个 R 包（metafor / Matrix / MASS / stringr
  均已在），安装走腾讯 CRAN 镜像 4.4 秒装完。
- **`plot_prisma_flow` 改用 metagear::plot_PRISMA 矢量直出**：返回 `draw`
  thunk，由 `.render_fig` 在 svgstring 设备开启时调用 → 纯矢量 SVG，零
  base64 栅格、零 png 包依赖。
- **结果文字模板 `references/rob2-narrative.md`**：配合 `rob2` / `rob_summary`
  产出的 traffic-light 与 summary bar，提供投稿可贴的整体/逐域/GRADE 联动
  /敏感性分析/读图说明英文段落模板。

### Changed
- **coze 本地镜像目录改名 `adapters/coze_project/` → `adapters/coze/`**：
  对齐 ct-base / ct-advisor / ct-registry / ct-samplesize 的统一约定（此前
  meta-analysis 是 ct 系列里唯一用 `coze_project` 的技能）。**纯本地镜像路径
  变更**，coze 远端目录结构不受影响，无需因本项重新部署。同步更新 9 个文件的
  路径引用：`.gitignore` / `.clawhubignore` / `AGENTS.md` / `adapters/README.md` /
  `adapters/coze/DEV.md` / `adapters/_dev/local_engine.py` / `learnings.md` /
  `references/r_packages.md` / `references/ADVANCED.md` / `ADVANCED_zh-CN.md`。
- **`plot_prisma_flow` design 参数白名单**：`design` 仅 7 个合法值
  （`classic` / `cinnamonMint` / `sunSplash` / `pomegranate` / `vintage` / `grey` /
  `greyMono`，取自 `metagear::designList`）。传非法值主动校验并回落
  `cinnamonMint`，不依赖 metagear 的 warning（它会静默回落到 `classic`）。
- **`plot_prisma_flow` 画板 7×9 英寸竖版**：匹配四阶段纵向布局（原 8×6 横版
  把图压扁）。支持 `fig_width` / `fig_height` 覆盖。
- **`plot_prisma_flow` 新增 2 个计数 + 3 个可选参数**：`other_sources` /
  `reports` 计数（与 `included` 不等时才出报告分支）、`design` / `colWidth` /
  `excludeDistance` 可选。**8 个原计数参数接口与 case40_prisma_flow.json 完全
  兼容**。
- **`grade` 分支兼容无 data**：原无条件 `df <- .build_df(data)`，空 data 时
  直接 stop；改为 `k_grade` 优先取行数，缺则回落 `params$k`。GRADE 是纯
  params 评分（5 降级 + 3 升级因素全走 params），研究数 k 仅用于 notes 文案。
- **`rob2` 分支删除 `check_pkg("robvis")` 守卫**：交通灯图自 2026-08-18 起
  已改 ggplot2 自绘，代码零调用 robvis；该守卫属**幽灵依赖**——只会在
  robvis 未装时把本可正常出图的任务拦死。`r_packages.txt` 同步把 robvis
  注释为「可不装」。

### Fixed
- **`plot_rob_traffic` / `plot_rob_summary` 列名大小写归一**：原只把 `nm`
  小写、`df` 的 names 不变，导致 `setdiff(names(df), study_col)` 对 "Study"
  列失效——Study 被当成域列混入，触发「replacement has 0 rows」。生产路径
  此前靠 `.build_df` 预先 tolower 才侥幸绕过，自身不自洽。
- **`.rob_domain_labels` 域标签映射长期失效（2026-08-20 声称修复实为假象）**：
  映射表 names 为大写 `D1..D5`，列名经归一后为小写 `d1..d5`，直接
  `labels[dom]` 全落空为 NA → 回退裸列名。改为 `labels[toupper(dom)]` 后
  三工具（ROB2 5 域 / ROB1 6 域 / ROBINS-I 7 域）的 traffic + summary 图
  全部正确显示「Randomization」等标准域标签。两张图 x 轴自此同源。
- **`plot_rob_summary` 改 robvis 风格百分比堆叠**：原 facet_wrap 分面计数
  柱图与 robvis::rob_summary 风格不同，改为 `position="fill"` +
  `coord_flip()` 的百分比堆叠横条，`scales::percent` 标 y 轴。Judgement 由
  字母序改为固定 `.ROB_LEVELS`（Low → Some concerns → High → Unclear →
  Critical），避免堆叠与图例按 High/Low/Some 乱序。
- **图标题中点 `·` (U+00B7) 在 svglite 下被注入占位字符「B7」**：traffic 与
  summary 标题改为 ` - `（更通用，字体回退无虞）。
- **`adapters/_dev/local_engine.py` 引擎路径恒不存在**：`_HERE` 指向
  `adapters/_dev/`，却直接 `join(_HERE, "coze_project", ...)` 拼出
  `adapters/_dev/coze_project/src/r_engine` —— 缺一级 `..`，本地引擎必然抛
  「缺失」。改为 `normpath(join(_HERE, "..", "coze", "src", "r_engine"))`。
  （该文件自 2026-08-26 起已不在运行路径，属潜伏 bug，非回归。）
- **「**1A 档执行**」补强：先实测后判断原则落实**：本次 4 笔早期判断
  （「metagear 不要装」「fig_* 可用」「PDF_download 可用」「impute_missingness
  可插补」）均被本地 R 4.6.1 + 腾讯镜像实测推翻——已写入
  `LRN-20260830-001/002/003`，ct-base §16 后续评估必须先做本地实测。
- **调用方约束：query_origin 发送层硬守卫（2026-08-30 实测 3 条空归因）**：
  飞书后台 08-30 仍出现 3 条 `query_origin` 为空记录（ID 3263/3270/3282，13:57/14:06/
  14:53），载荷为 `coze_contract.md` §2 示例（2 研究 A/B），判定为**裸 POST /run
  复制契约示例、body 缺 query_origin**——绕过了 2.2.28 客户端自动注入。修复（调用
  方约束，非 coze 端）：① `coze_client` 新增 `_assert_query_origin`，在 `run_meta`
  序列化出站前硬校验 `query_origin` 为 `[debug:]sha256:<64hex>`，缺失/空/非法直接
  `ValueError`（覆盖主端点与回退端点）；② `scripts/build_request.py` 的 build 产物
  `request.json` 自动注入有效 `query_origin`，即使被手 POST 也不产生空归因；③ 契约
  文档 §2 + 示例载荷（`req_test.json` / `meta_request*.json`）补 `query_origin` 占位
  并加「裸调必须带归因」显式条款。**根因在调用方、不在技能代码**——所有经
  `run_analysis` / `scripts/run_meta.py` 的路径本就带归因。

### Documentation
- **`references/review_workflow.md` 完全重写**：删 7 段**虚构 API**——
  `prisma_flow` / `export` / `screen_titles` / `retrieve_pdf` / `retrieve_pmid` /
  `extract_digit` / `impute_ml` 在 metagear 中**不存在**，是历史版本的幻觉
  文档。新结构：§0 能力边界（明确支持/不接入/转交）+ §1 PRISMA 真实可复现
  脚本 + §2 agent 行为层筛选 + §3 数据提取表模板 + §4 缺失值（如实说明
  `impute_missingness` 只返汇总表、不是插补）+ §5 引用。
- **`references/rob2-narrative.md` 新增**（见 Added 段）。
- **周边文档 metagear 条目统一修正**：`references/ADVANCED.md` /
  `ADVANCED_zh-CN.md` / `references/references.md` / `AGENTS.md` /
  `adapters/coze/AGENTS.md` / `setup_packages.R` —— 版本号统一为
  `≥0.7`、用途限定为 plot_PRISMA、移除「已移除」历史标注中的 metagear、
  补「2026-08-30 重引入」说明。

### Verified（本地，未线上回归）
- **prisma_flow 端到端 19/19 PASS**：case40_prisma_flow.json 原参数零改动
  兼容；矢量直出（零 base64 栅格）；7 个 design 全部出图；非法 design 回落
  正确；4 种边界（最简/全 0 / reports≠included / colWidth 自定义）均通过；
  缺包降级报错含包名。
- **rob2 / rob_summary 端到端 21/21 PASS**：3 工具 × 2 图共 6 张图全部出图、
  域标签全部命中、无裸 D 列名、summary y 轴含百分比。
- **路由回归 19/19 PASS**：综述流程类 12 例全正确（含「PRISMA 2020」剥离
  版本号陷阱），效应量类 7 例零回归。

### 部署注意
- **coze 端需重新部署**（`run_task.R` 的 `grade` / `rob2` / `rob_summary` /
  `prisma_flow` 分支与 `advanced_functions.R` 的多个函数均有改动）。
- **`r_packages.txt` 需补 metagear**（若镜像未预装，docker build 时会失败）。
- **部署后强制线上回归**：HTTP 200 ≠ 任务成功（见 LRN-20260817-002），
  必须实际触发各 task 并核对 SVG 字面与统计输出；建议按 `verify_meta_full.py`
  增加 `prisma_flow` / `rob2` / `grade` 三个新 case。

### Added (2026-08-30 PRISMA 检索前端桥接)
- **`scripts/prisma_bridge.py`（新）**：ct-literature `.merged.json` → meta-analysis
  `prisma_flow` 请求信封的**唯一 sanctioned 胶水**。自动填 4 字段
  （`records`=`identified_records`+`duplicates_removed` / `duplicates` / `screened` /
  `excluded_title`），其余 5 字段（`other_sources` / `assessed` / `excluded_elig` /
  `included` / `reports`）显式标 `[MANUAL]` 留空待人工补。强制打印
  「机器初筛，非人工终审」声明；`included` 绝不由机器初筛数映射（防方法学错误流程图）。
- **`references/review_workflow.md` §1.5 新增「计数来源与人工补齐」**：9 字段来源分级表
  （自动/人工/语义错位）+ 推荐工作流 + 强制声明，防 agent 过度承诺「全自动检索」。

---

## [2.2.30] — 2026-08-29 — coze 回传结构迁移 §20.8 模式 B（完整 JSON 单文件外置，删除 manifest 外置）

> 触发：ct-base §20.8 由「两种已批准模式（A manifest / B 完整 JSON 单文件）」收窄为**仅模式 B**（2026-08-29 用户拍板删除模式 A）。meta-analysis 原 coze 端实现模式 A（manifest 外置），现迁移到模式 B 以对齐单一标准；coze 端需重新部署。

### Changed（coze 端 `adapters/coze_project/src/graphs/nodes/meta_analysis.py`）
- **删除 `_externalize_to_manifest`**（含 `_collect_always` / `_collect_stats` / `_move` / `_discard_fallback` 及其 `_coze_manifest` 契约），整体替换为 §20.8 模式 B 三函数：
  - `_build_inline(out)`：内联轻量信封 = 删 `figures`/`repro`，其余字段（status/stats/warnings/notes/task）保留，恒内联 `_coze_version`。
  - `_trim_inline_to_limit(inline)`：内联超 4000 时从大到小丢 `stats` 子块直到 < 4000；**循环条件与 narrative 额度均把 `_coze_truncated` 标记自身大小计入预算**，末尾兜底逐条缩减标记，确保最终（含标记）恒 < 4000（沿用 ct-samplesize v5.3.14 的 ⑤ 修复）。meta-analysis 信封无顶层 narrative，故无 narrative 截断分支。
  - `_externalize_full(out, timeout=90)`：完整信封整体写单个 S3 文件（md5 摘要命名），内联挂 `_coze_full = {storage:"s3", url}`；S3 不可用/失败/超时降级无 `_coze_full` 的内联删减版。90s daemon 超时守护不变。
- `meta_analysis_node`：`_externalize_to_manifest` → `_externalize_full`，并在调用前注入 `out["_coze_version"]`（恒内联诊断透出，本地不再比对）。
- 常量：`_CORE_INLINE` 由 `{status,task,_coze_truncated,_coze_manifest}` 改为 `{status,task,_coze_truncated,_coze_full,_coze_version}`；新增 `_COZE_ENVELOPE_VERSION` / `_S3_URL_EXPIRE`；删除 `_EXTERNALIZE_MIN_BYTES`。

### Changed（本地 `adapters/coze_client.py`）
- 新增 `_fetch_full_json(parsed, timeout=30)`：优先经 `_coze_full` 下载完整 JSON 作分析源（含 figures/repro，零删减）；失败/无链接返回 None。
- `run_meta` 解析路径：`_fill_external_svgs(parsed)` → `full = _fetch_full_json(parsed); parsed = full if full is not None else _fill_external_svgs(parsed)`。内联删减版仅作飞书日志/老版本兼容。
- `_fill_external_svgs` 降级为**兜底**入口（仅当响应无 `_coze_full` 的旧 coze 响应才走 manifest 重组 / 旧 figures[].url·repro.url 回填），保留 `_reassemble_from_manifest` 向后兼容。
- `health()` 探测包**注入 Bearer token**：此前探测包无 token，被 coze 网关在鉴权层挡回 401、请求根本进不了 langgraph，probe 短路逻辑实际是"睡着"的（靠 401 兜底判定可达，但 probe 短路从未生效）。现经 `_resolve_token` 取 token 后挂 `Authorization` 头，probe 能越过鉴权真正进图、在 `meta_analysis` 节点短路（不调 R 引擎、不写飞书），既验证可达性又零算力零日志污染。token 解析失败 / 返回空时降级为无 token 探测（401 仍算可达，判定语义不变）。coze 端无需改动（probe 字段已于 2.2.28+ 引入）。

### Verified
- `verify_meta_full.py`（FakeS3 + file:// 全链路）**21/21 PASS**：① `_externalize_full` 内联 < 4000、无 figures/repro、含 `_coze_full`，S3 完整数据含 figures/repro 且 svg 全等；② 本地 `_fetch_full_json` 经 `_coze_full` 还原完整 JSON（figures/repro 全等、剔除 `_coze_full`）；③ 旧 `_coze_manifest` 内联 → `_fetch_full_json` 返回 None（降级旧契约）；④ S3 不可用 → 降级内联删减版（无 `_coze_full`）< 4000；⑤ 内联超 4000 → 丢 stats 子块、含标记后恒 < 4000。
- 两侧 `py_compile` 通过；coze 端已无 `_externalize_to_manifest` 残留（本地 `_reassemble_from_manifest` 仅旧响应兜底保留）。

### 部署注意
- **coze 端已改动，必须重新部署**（旧 `20260829a.zip` 不含本次模式 B 迁移）。升级包见 `meta-analysis_coze_2.2.30.zip`。

## [2.2.29] — 2026-08-29 — 契约漂移检测：移除版本号比对（对齐 ct-base §20.9 修订）

> 触发：ct-base §20.9 由「版本漂移 + 结构漂移」双信号修订为**仅数据内容/结构不一致触发**——版本号不同不再提醒。

### Changed
- **`_assess_contract` 移除版本漂移检测**：删除 `EXPECTED_COZE_ENVELOPE_VERSION` 常量与 `_coze_version` / `_contract_version` 的比对分支（原第 4 项）。版本由 coze 端随发布同步，本地不比对 —— 任何**仅版本号差异**（无数据内容/结构变化）一律不提示，避免无谓打扰。检测信号自此只剩一条：**coze 返回的数据内容/结构与本地消费接口是否一致**（字段别名自适应归一化）。
- **零噪音边界写入 docstring**：`_coze_version` 高于/低于本地、coze 未注入版本标记、结构一致且无别名映射 —— 三种情况均不提示。

### Unchanged（刻意保留，勿"顺手改回去"）
- 结构漂移自适应（`quality_gate` / `checks` / `pooled` / `figures` 别名映射）、`_needs_upgrade` / `_contract_drift` 机器标记、`rendering.py` 的 HTML 横幅唯一出口 —— 均按 ct-base §20.9 原样保留，横幅文案本就只描述"结构不一致"，无需改动。
- meta 的 coze 端本就**未注入** `_coze_version`（实测 `grep -r _coze_version adapters/coze_project/src` 无匹配），故本次是纯本地清理：**coze 端无需改动、无需重新部署**，已出的 `20260829a.zip` 不受影响。

### Verified
- `_assess_contract` 单测 9 例全通过：版本更高 / 更低 / 旧标记 / 缺标记 / 结构一致 → 全部 **零 drift**；`pooled` 别名 / `qgate` 别名 / `figures` dict→list → **触发 drift**；「版本更高 + 结构漂移」混合场景**只报结构**，断言文案不含"版本"字样。
- `py_compile` 通过；`deploy_retest --offline` / `--mock` 各 46/46 回归通过。

---

## [2.2.28] — 2026-08-29 — 归因不再为空 + 短窗幂等去重

> 触发：飞书后台发现 02:54 两条几乎同时、且 `query_origin` 均为空的 `pairwise_meta` 记录（数据完全相同，仅 `figure.plots` 差一个 `funnel`）。

### Fixed
- **空归因（主因）**：`query_origin` 此前只在 `run_analysis.py` 计算并作为参数传入；直接调 `coze_client.run_meta` 的路径（`__main__` 自测入口 / `coze_integration_test` / `deploy_retest --live` / 外部脚本）都不传 → coze 端 `state.query_origin or ""` 兜底成空串。后果不止"日志无法溯源"——**空值会绕过按 `query_origin` 计的限流**。现把计算下沉为 `coze_client._default_query_origin()`，`run_meta` 在入参为 `None` 时自动填充；`run_analysis.py` 改为复用同一函数（单一实现，消除两处逻辑漂移）。
- **调试/冒烟流量污染生产日志表**：`coze_integration_test.run_one` 与 `deploy_retest.call_one` 原为裸 POST（46 个 case 全空归因）。现统一经新增的 `with_trace()` 注入归因 + `request_id` + `_debug: true`，归因带 `debug:` 前缀——飞书归因列可直接筛出非生产流量。

### Added
- **短窗幂等去重**：对 `(task, data, params, figure)` 做 SHA-256 指纹（忽略 `request_id`/`_debug`/`query_origin` 等观测字段），`COZE_META_DEDUP_WINDOW`（默认 60s，≤0 关闭）内同指纹直接复用上次结果、不再打 coze。命中时结果附 `_dedup_hit: true` + `_dedup_original_request_id`。**仅缓存 ok/warn 结果**，失败不入缓存（避免偶发失败毒化窗口内的真实重试）；上限 32 条、按最旧淘汰；返回深拷贝，调用方互不影响。作用域为进程内（与 `_acquire_rate_limit` 同级；跨进程需文件锁，未实现）。
- **请求追踪 ID**：每次调用生成 UUID 写入 `request_id`，随结果以 `_request_id` 返回——相邻两条飞书记录可据此区分「两次独立调用」还是「一次调用的重放」。coze 端 `state.py` 未加该字段（pydantic `extra='ignore'` 静默忽略，实测不报错），故**暂不进飞书**；如需落表须改 `state.py` + `feishu_write_node` 并重新部署（发布动作，待授权）。

- **连通性探测标记 `probe`（coze 端消费 → 需重新上传部署包才生效）**：客户端 `health()` 每次启动都 POST 一次 `/run`（SKILL.md 要求启动探测），此前 coze 端照单全收 → 飞书日志表被空 `querystr` 记录污染，排查时无法与真实调用区分。现 `health()` 探测包带 `probe: true` + `debug:` 归因；coze 端 `meta_analysis` 节点识别后**直接返回探针结果、不调用 R 引擎**，`feishu_save` 节点**跳过飞书写入**。兜底：老客户端发 `{}`（无 `probe` 字段）时，靠 `data`/`params`/`figure` 三者全空的"空信封"特征识别。规则抽在 `src/graphs/nodes/_skip_rules.py`（**零第三方依赖，可本地单测**——节点模块依赖 langchain/langgraph，本地 import 不了）。
  - ⚠️ **未部署前不生效**：老 coze 端不认识 `probe` 字段（pydantic `extra='ignore'`），仍会写一条记录，但带 `debug:` 归因前缀可筛出，不再是空白归因 —— 平滑过渡，两侧独立发布互不影响。

### Removed
- **`coze_client.py` 的 `__main__` 自测入口**：删除原「硬编码 sample 调 `run_meta`」逻辑 —— 它就是飞书 08-29 两条空归因记录的来源（注释还停留在「需要本地已启动 coze 服务」的年代，端点早已换成公网，于是调试动作直接往生产日志表写记录），且与 `case1_pairwise_binary` 完全重复、无独立价值。CLI 保留 `--health` 子命令（仅探测可达性，不发起分析请求）；无参数时只打印用法、**零副作用**。冒烟改用 `python scripts/run_meta.py <request.json>`（走生产路径，自动带归因 + 去重）。

### Changed
- **调用方收敛（4 入口 → 3 入口，凭据/端点重复逻辑清零）**：`coze_integration_test` 与 `deploy_retest` 不再自建 `resolve_token` 与 `DEFAULT_ENDPOINT` 字面量，统一 `from coze_client import _resolve_token / _endpoint / DEFAULT_ENDPOINT`（保留 import 失败时的等价兜底实现）。端点从「模块导入时固化」改为**运行时**解析，与生产路径行为一致——旧写法在运行中途改 `COZE_META_ENDPOINT` 时生产生效、测试不生效。
- **`--endpoint` 默认留空**，由 `_endpoint()` 运行时读取；`deploy_retest` 报告记录**实际**端点（旧写法会把 `endpoint` 写成空字符串，事后看不出这一轮跑的是哪个端点）。
- **语义差异就地固化注释**：测试侧 `_post`（300s / 捕获 HTTPError 继续跑 / payload 原样发送）与生产侧 `_post_run`（600s / 抛异常触发端点回退 / 归一化+脱敏+强制 svg+指纹去重）的差异是**有意保留**的 —— 测试必须绕过客户端加工才能测到 coze 端真实行为（典型：`run_meta` 的 `byvar→subgroup` 归一会让「coze 只认 subgroup、byvar 静默失效」这个坑永远测不出来）。差异已写成对照表注释，避免后人误「统一」。
- 文档同步：`references/ADVANCED.md` / `ADVANCED_zh-CN.md` 的自测命令由 `python adapters/coze_client.py` 改为 `--health` + `scripts/run_meta.py`。

### Verified（mock + 真实 coze 链路）
- 归因：`sha256:<64hex>` 71 字符；`debug=True` → `debug:sha256:...`；`run_analysis` 与 `coze_client` 同源一致。
- 指纹：换 `request_id` 同指纹、换 `figure.plots` 不同指纹。
- 去重：第二次完全相同调用 **POST 次数保持 1**（`_dedup_hit=True`，复用自首次 `request_id`）；改 `figure` 后正常发起第二次；失败结果不入缓存；窗口置 0 可关闭。
- 真实链路：`python adapters/coze_client.py` 端到端 `status=ok`，统计值与飞书历史记录逐字一致（pooled logOR −0.626 / OR 0.5347，k=2，I²=0），coze 端对新增字段无 422/报错。
- 编译：`py_compile` 四个改动文件全通过。
- 收敛后回归：`python adapters/coze_client.py`（无参数）零副作用、不发请求；集成测试端点/token 解析走 `coze_client` 实现（端点 `https://ct-meta.coze.site/run`、token 739 字符）；`deploy_retest --offline` / `--mock` 各 46/46 通过；`COZE_META_ENDPOINT` 覆盖在报告中生效（`https://example.invalid/run`）；屏蔽 `coze_client` 导入后兜底分支功能完整（token 739 字符、归因与主路径同源 `sha256:b8cae3d46…`）。
- `probe` 跳过规则单测 9 例全通过：probe / 空信封 / 空信封+probe（probe 优先）/ 真实 rows 请求 / 仅 params / 仅 figure / csv_path / `{"rows":[]}` / 仅 colmap —— 前 3 例跳过，后 6 例**照常写入**（数据为空但结构完整的请求有排查价值）。
- `health()`：探测包实测 `{"probe": true, "query_origin": "debug:sha256:…"}`；端点不可达仍返回 `False`、4xx/5xx 仍视为可达 —— **判定语义未因包体变化而改变**。
- 部署包 `meta-analysis-coze_project-20260829a.zip`：70 文件 = 基准 69 + `_skip_rules.py`，内容变化 4 个（`state.py` / `meta_analysis.py` / `feishu_save_node.py` / `coze_contract.md`），无 `__pycache__`、无 `Rplots.pdf`，包内关键改动自校验通过，整包 MD5 `711446dbf3b2dd95de50482da3943cd9`。

### Fixed
- **部署包夹带 R 垃圾产物**：`src/r_engine/Rplots.pdf`（R 默认图形设备的落盘产物）此前会进部署包。打包时已排除，并同步排除 `__pycache__` / `*.pyc` / `.Rout` / `.RData` / `.Rhistory` / `.venv`。

---

## [2.2.27] — 2026-08-28 — coze 调用纪律 + 提示收敛 + 修复

### Added
- **coze 调用并发限流**：所有出站调用串行化，相邻两次间隔 ≥1s（`coze_client.py` 模块级 `threading.Lock` + 单调时钟；主端点 + 回退端点均约束；间隔可由 `COZE_META_MIN_INTERVAL` 覆写、≤0 关闭）。已写入 ct-base §20.10 全库通用标准。

### Fixed
- **classify 全角括号缺陷**：query 含全角括号（如 `region（Asia…）`）导致 subgroup 静默退化为 None；`_extract_subgroup` 前瞻断词补全 `（）`，亚组分析恢复（case5 实测 χ²=2.40, p=0.3008）。
- **质量评估版式**：`rendering.py` 质量卡由单列 `<ul>` 改为两列 `.kv`（左检查项带圆点、右着色状态词），所有案例两端对齐。

### Changed
- **coze 响应契约漂移 → 收敛到 HTML 唯一出口**：合并「版本漂移（`_coze_version`/旧 `_contract_version` 比对）」与「结构漂移（字段别名自适应）」为单入口 `_assess_contract`；检测到漂移时先自适应产出可用结果，**用户可见提示只在 HTML 报告顶部 `.banner` 出现一次**——删除 stderr 提示与 notes 污染；缺版本标记不误报。
- **端点回退提示同样收敛**：主端点 token 不一致回退备用端点时，提示仅写机器标记 `_coze_endpoint_notice` 并由 HTML 横幅渲染，不再写 stderr / 不污染 notes。
- **SKILL.md 正文翻译**：§5.1 残留中文说明按 ct-base 全英文规范译为英文（双语回显块 `当前分析设定 / Current analysis settings` 按要求保留）。

## [2.2.26] — 2026-08-28 — figures/repro 无条件外置（无论是否超 4000）

### Changed（coze 端 `meta_analysis.py::_externalize_to_manifest`）
- **figures/repro 恒外置**：不再「仅超限才外置」——**只要存在** svg 图元素 / repro.r，就**无条件**移出主返回体（原位替换为 `{storage:s3,type:block}` 引用），原值入 manifest。主返回体恒为「stats 数值 + manifest 链接」，更轻、更一致。
- **stats 子块按需外置**：figures/repro 移完后仍 > 4000，才依次把 stats 子元素从大到小移入同一 manifest，直到 < 4000。
- 契约不变：`_coze_manifest={storage:s3,url}` + manifest list `[{path,value}]`；本地 `_reassemble_from_manifest` **无需改动**。

### Verified（R 引擎 + mock HTTP server）
- 324 字符（未超限）+ 有 svg/repro → 两者**仍被无条件外置**，stats.pooled 内联，manifest 挂载；本地重组 **FULLY EQUAL=True**。
- 无 figures/repro + 未超限 → 原样、无 manifest、0 上传。
- 无 figures/repro + 超限 → stats 子块（big_str）外置为 block、k 保留、无丢弃。
- 本地/coze 衔接契约（path/占位/manifest 结构）与 2.2.25 完全一致，发布前已核验。

### 部署
- coze 端 `meta_analysis.py` → 重新上传 coze 包（`meta-analysis-coze_project-20260828e.zip`）。本地端无改动（契约未变）。

## [2.2.25] — 2026-08-28 — coze 截断收敛为「统一 manifest」方案（svg/r/stats 单文件外置）

### Changed（coze 端 `meta_analysis.py` + 本地 `coze_client.py`）
用户进一步提案的**统一 manifest 方案**取代 2.2.24 的「逐块外置 `_coze_externalized`」：

- **coze 端**：`_externalize_to_manifest()`（替代 `_externalize_figures`/`_externalize_repro`/`_trim_to_limit` 三套）。
  超 4000 时——先把 figures（含 svg）、repro（含 r 代码）移动为 `{storage:s3,type:block}` 引用，再依次把
  `stats` 下一级元素从**最大开始**移动，直到总量 < 4000；所有被移元素（含 path+原值）组成一个 list，
  **存为单个 S3 文件**，主返回体挂 `_coze_manifest={storage:s3,url}`。核心数值（pooled/heterogeneity/k/sm）始终内联。
- **本地端**：`_reassemble_from_manifest()`——GET manifest → 按 path 逐项写回 → **重组为原始 JSON**（含 svg/r/统计值），
  一次还原、零丢失。`_fill_external_svgs` 作为入口：优先走 manifest，无则回退旧契约（figures.url/repro.url/`_coze_externalized`）。
- **删旧代码**：`_externalize_figures`/`_externalize_repro`/`_trim_to_limit`/`_externalize_all_with_timeout` 及其
  `_coze_externalized` 逐块契约全部移除（用户约定：不留遗留实现）。

### Verified（单测 + mock HTTP server，含 svg/r 代码）
- 5652 字符超限体 → 外置 figures[0] 等块至 2861 字符（<4000），pooled/k 内联，manifest 挂载；
  本地重组后 **FULLY EQUAL = True**（figures[0].svg / figures[1].svg / repro.r / stats.subgroups 全部还原）。
- 未超限响应：原样返回、不产生 manifest、不上传 S3、svg/r 保持内联。
- 只移必要的块（够小就不动，如 repro 未触及）。

### 部署
- coze 端 `meta_analysis.py`（manifest 外置）→ 重新上传 coze 包（`meta-analysis-coze_project-20260828d.zip`）。
- 本地 `coze_client.py`（manifest 重组 + 兼容）→ 随技能本体发布。

## [2.2.24] — 2026-08-28 — coze 4000 截断改为「超限外置最大块」，零数据丢失

### Changed（coze 端 `meta_analysis.py` + 本地 `coze_client.py`）
用户提案的**泛化截断兜底**取代原「按优先级丢弃」：超 4000 时**不再丢数据**，而是迭代「找最大字符块 → 外置 S3 → 原位替换为 `{storage:s3,type:block,url}` 引用」，直到 < 4000，被外置路径记入 `out['_coze_externalized']=[{path,url}]`。

- **核心内联**：`status`/`task`/标记 + `stats` 容器（pooled/heterogeneity/k/sm/model…）整体永不外置，只下钻其子块（subgroups/quality_gate.checks/bias…）——关键数值始终内联可取。
- **兜底丢弃**：仅当 S3 不可用或所有可外置块已外置仍超限，才从大到小丢 stats 子字段并记 `_coze_truncated`（保 status 与最小数值核心）。
- **本地回填**：`coze_client.py` 新增 `_inflate_externalized()`（对称于 `_fill_external_svgs`），按 `_coze_externalized` 的 `{path,url}` 逐个 GET 回填还原；失败保留 url 并标 `_inflate_failed`，绝不中断分析。`run_meta` 在 `_fill_external_svgs` 末尾自动调用。

### Verified（单测 + R 4.6.1 真实数据）
- 单测：4169 字符超限体 → 外置 `stats.subgroups`、pooled/k 保持内联、回填后与原始完全相等（零丢失）。
- 真实 `_inflate_externalized` + mock HTTP server：从 url 正确还原 `stats.subgroups`，k/pooled 未动。
- R 引擎真实跑用户 7-RCT 亚组数据：figures/repro 外置后返回体 1783 字符 < 4000，`subgroups` 内联、Q_between=3.8522 完整。
- 用户案例截断根因（gate_json 冗余）已在 2.2.23 删除；本方案提供**任意胖字段**的通用兜底（不再依赖人工预判优先级）。

### 部署
- coze 端改 `meta_analysis.py`（外置逻辑）→ 需重新上传 coze 包（`meta-analysis-coze_project-20260828c.zip`）生效。
- 本地改 `coze_client.py`（回填）→ 随技能本体发布。

## [2.2.23] — 2026-08-28 — 修复亚组分析 coze 4000 截断裁掉 stats.subgroups

### Fixed（coze 端 R / Python，需重新上传 coze 部署包生效）
- **删除 `quality_gate.gate_json` 冗余**：`run_quality_gate` 不再生成 quality_gate 结构的字符串化 JSON 副本，`.quality_gate` 转发去掉 `gate_json`。该字段是 `checks/status/k/I2` 的重复，每次分析徒增 ~400 字符，是 `subgroup_analysis` 等 stats 较胖任务触发 coze 4000 字符截断、尾部裁掉 `stats.subgroups` 的主因。已 grep 确认本地渲染层无任何 `.py` 依赖 gate_json。
- **重排 `_trim_to_limit` 截断优先级**（`src/graphs/nodes/meta_analysis.py`）：亚组数值 `stats.subgroups / subgroup_test / bias` 列为高保真对象（亚组分析核心交付物），仅先丢 null 的 `notes/warnings/task` 与补充性 `stats.quality_gate`；超限时 subgroups 不再被优先丢弃。

### Verified（R 4.6.1 本地实测，非假设）
- 跑用户同款 7-RCT 按 PD-L1 分亚组案例：修复后 `stats` 序列化 979 字符、gate_json 消失，估算 coze 返回体 **~3459 < 4000**，`subgroups`（high/low 含 estimate/CI/k）完整返回。
- Python 单测：构造 4311 字符超限体，`_trim_to_limit` 丢弃顺序 `notes→warnings→task→quality_gate`，**subgroups 保留**、pooled/heterogeneity 完好。
- 注：本修复属 coze 端代码，未含在 SkillHub 2.2.22 发布包（coze_project 被 gitignore）；需重新打 coze 部署 zip 上传。

## [2.2.22] — 2026-08-28 — coze 部署复测全绿 + §8.5 门控两处修复

### Fixed（`tests/deploy_retest.py` 部署复测门控 §8.5）
- **图形 judge 只认内联 `svg` → 误杀所有图形案例**：coze 生产响应把 svg **外置为 S3 `url`**（不含内联 svg）。原规则「至少一个 figure 含有效 svg」会把图形任务全判空壳失败。改为**图形有效 = 内联 `svg` 或可达的外置 `url`**，新增 `_verify_fig_url()` GET 校验（HTTP 非 200 判死链失败，网络抖动不误杀）。
- **`_has_nan` 把 R 合法缺失标注 `"NA"` 当失败 → 误杀单组 meta / selmodel**：R 在 p 值缺省（单组无对照）、子模型 CI 缺失时输出字符串 `"NA"`，属预期缺失而非计算崩溃。改为**只拦 `NaN`/`Inf` 字面量 + 裸 NaN/Inf**，把 `"NA"` 移出失败判定。

### Verified（coze 主站点 `ct-meta` 部署后全量 `--live` 门控）
- **46/46 通过，0 失败**。确认本次 R 引擎修复已上云生效：
  - `diagnostic_meta` 现返回 sroc + **sens_forest + spec_forest**（escalc `PLO` 修复）；
  - `bayesian_pairwise` 森林图正常出图（`metafor::forest(x=)` 修复）；
  - netleague 中文映射、各方法默认图形扩充、函数化重构均随部署生效。
- 验证方法遵循 §20.2.5 / §20.6：开 `result` 字段真内容确认，不看 HTTP 200 假绿。

## [2.2.21] — 2026-08-28 — 端到端回归测试发现并修复 bayesian_pairwise 森林图 bug

### Fixed（`adapters/coze_project/src/r_engine/run_task.R`）
- **`bayesian_pairwise` 森林图不渲染（真实 bug）**：v2.2.20 新增的 bayes 森林图用
  `metafor::forest(yi = res$y, ...)`，但 **metafor 5.0.1 的 `forest()` 要求位置参数 `x`**（效应量），
  不认 `yi=` 具名参数（那是 `meta::forest` 的约定）→ 报 "argument 'x' is missing"，被 `.safe_fig`
  静默吞掉 → 返回 figures=0。改为 `metafor::forest(x = res$y, vi = res$sigma^2, ...)` 后正常出图。

### Verified（全量端到端回归，重构后引擎真实 R subprocess 跑 46 coze_cases + 4 增强 case）
- 全部 task 正确分发、`status ∈ {ok,warn}`；重构核心 task 逐项实测：
  - `metainc`（forest+funnel+radial+influence 4 图）、`survival_meta`（forest+funnel+radial 3 图 +
    **bias 正常填充** egger_p/begg_p）、`diagnostic_meta`（sroc+sens_forest+spec_forest 3 图）、
    `bayesian_pairwise`（修复后 forest 出图）。
  - 共享块 pairwise/单组/亚组/metareg/nma/留一/累积/剂量反应/TSA/power 等全部 status=ok。
- **说明**：测试框架报告的 case12/19 "NaN/NA" 与 case16 "netleague 缺失" 均为**误报**——stats 里的
  `"NA"` 是字符串（非数值 NaN，metamean 路径 p 值缺省，既有行为）；`netleague` 按设计进
  `stats.extra.league_table`（表格）而非 figure。`case38_rob2` 报 error 因本地缺 `robvis` 包
  （coze 服务端才有），非重构回归。
- 测试框架经验：`subprocess.run` 反复 spawn R 在本机触发资源耗尽崩溃、且共享 temp 文件会交叉污染；
  改为 bash 分批（每批 5 案例）+ 唯一 temp 文件后稳定。临时文件用后即清。

---

## [2.2.20] — 2026-08-28 — sens/spec 改 PLO 规范写法 + R 引擎函数化去重

### Changed（`adapters/coze_project/src/r_engine/run_task.R`）
- **`diagnostic_meta` sens/spec forest 修正 measure**：coze 直连实测 + 本地验证确认 `metafor::escalc`
  全 family（OR/SMD/PR/PLO 等）正常；`PLOD` 非合法 measure（metafor 报 Unknown measure），
  敏感度/特异度森林图改用标准的 **`escalc(measure="PLO")`**（logit 比例，xi=TP/ni=TP+FN 等），
  与 `meta_analysis_core.R` 既有 PLO 用法一致。
- **R 引擎函数化去重（纯机械提取，零行为改变）**：
  - 新增 `.safe_fig(figs, draw, type, w, h)`：收敛全库 13 处 `tryCatch(c(figs, list(.render_fig(...))))`
    出图安全包装 → 统一调用（sucra/contribution/nodesplit/egger/loo/cumulative/forest/sens/spec/influence 等）。
  - 新增 `.meta_to_rma(fit, model)`：收敛 meta 对象 → metafor::rma.uni 桥接（供 radial/influence 诊断），
    已传 rma 对象则原样返回；应用于 metainc 与共享块 influence 分支。
  - 新增 `.bias_test(fit, model, warns, plots, figs)`：收敛共享块与 survival_meta 两处 ~30 行几乎重复的
    Egger/Begg `regtest`/`ranktest` + egger_p<0.10 警告 + egger 图逻辑 → 一处定义两处调用。
  - 新增 `.quality_gate(fit, te_vec, se_vec, df, stats, bias_gate)`：收敛两处 `es_gate` 构造 +
    `run_quality_gate` 调用 + 结果回填 → 一处定义两处调用。
  - 新增 `.bayes_summary(res)`：收敛 bayesian_pairwise 分支 20+ 行 bayesmeta $summary 矩阵解析
    （兼容版本间行列方向差异）→ 一处定义一处调用。
  - 新增 `.col_name(colmap, role, default)`：列名解析（区别于 .col 的取值），dose_resp 手写 7 行
    `tolower(cm$x %||% ...)` 改用该 helper。

### Verified
- 本机 R 4.6.1 + metafor 5.0.1 实测：`escalc`（OR/SMD/PR/PLO）全部正常，**无段错误**——此前段错误
  为 Git Bash `-e` 多行引号破坏假象，非真实问题。PLO 版 sens/spec 森林图完整跑通（rma.uni 合并 + forest 绘制）。
- 冒烟测试通过：`.bias_test`（meta 对象 → rma 桥接 + bias + warns + egger 图）、`.bayes_summary`（NA 兜底）、
  `.col_name`（含 default 回退）、sens/spec PLO 森林图绘制。
- `run_task.R` Rscript `parse()` 通过；`.safe_fig` 14、`.meta_to_rma` 2、`.bias_test` 2、`.quality_gate` 2、
  `.bayes_summary` 1、`.col_name` 7 处调用确认。

### 说明
- 本次改动均为本地代码镜像 `adapters/coze_project`，**未部署到 coze 云端**（云端 `run_task.R` 仍是旧版，
  实测 `diagnostic_meta` 只返回 sroc，未含 sens_forest/spec_forest）。需在 coze 平台侧同步代码后生效。

---

## [2.2.19] — 2026-08-28 — 直接改 coze R 引擎，为单分支 task 增加默认伴侣图

### Changed（`adapters/coze_project/src/r_engine/run_task.R` + `scripts/build_request.py` + `adapters/rendering.py`）
上一版（2.2.18）核查发现 `survival_meta`/`diagnostic_meta`/`metainc`/`ipd_meta`/`bayesian_pairwise` 在 coze
R 引擎各自独立分支只渲染一种图。本次**直接改 coze 端 R 代码**（用户授权）为这些 task 补默认伴侣图：

- **`metareg`**：放宽 `run_task.R:577` 的 bubble gate（`task == "bubble_plot"` → `task %in% c("bubble_plot","metareg")`），
  让 metareg 也能渲染气泡图（meta 回归标志性图）。默认 `["forest","funnel"]` → `["forest","funnel","bubble"]`。
- **`survival_meta`**：R 分支补 `funnel` + `radial`（rma.uni 对象，引擎支持）。默认 → `["forest","funnel","radial"]`。
- **`diagnostic_meta`**：新增 `.diag_sens_forest` / `.diag_spec_forest` helper（手算 logit + 0.5 连续性校正，
  规避 escalc measure 兼容性，规避弃用依赖），补敏感度/特异度森林图。默认 → `["sroc","sens_forest","spec_forest"]`。
- **`bayesian_pairwise`**：该分支此前从未调用 `render_fig`，默认 `["forest"]` 实为空跑不出图。现用
  `res$y`/`res$sigma` 绘制个体研究森林图（metafor 已依赖），默认出图。
- **`metainc`**：补 `funnel`/`radial`/`influence`（meta 对象经 `rma.uni(fit$TE, fit$seTE)` 桥接）。默认 →
  `["forest","funnel","radial","influence"]`。
- **`ipd_meta`**：补 `funnel`/`influence`（rma.glmm 对象）。默认 → `["forest","funnel","influence"]`。

同步更新：`build_request.py` 的 `DEFAULT_PLOTS` 与 `VALID_PLOTS`（新增 `sens_forest`/`spec_forest`）、
`rendering.py` 的 `_I18N`/`type_names`（新增敏感度/特异度森林图中英文标题）。

### Verified
- `py_compile` 通过；`_default_plots_for` 输出确认（见下方表格）。
- `run_task.R` 经 Rscript `parse()` 通过；敏感度/特异度森林图 helper 在本地 R 4.6.1 + metafor 5.0.1 完整跑通
  （rma.uni 合并 + forest 绘制，敏感度 pooled=0.857 / 特异度=0.894 合理）。
- ⚠️ 说明：本机 metafor 5.0.1 经 `Rscript -e` 多行传参曾误报段错误，实为 Git Bash 引号破坏所致；
  改用临时 `.R` 文件执行全部正常，非代码问题。

---

## [2.2.18] — 2026-08-28 — 默认图形增强 + netleague 中文映射

### Added / Changed（`scripts/build_request.py` + `adapters/rendering.py`）
- **`netleague` 中文/英文标题映射补全**：`rendering.py::_I18N` 新增 `fig_netleague`（zh=网络证据表 /
  en=Network evidence table），`type_names` 取值 `netleague` → 该图在 HTML 模板中不再回退显示原始英文 type 名。
- **默认图形增强（仅动 coze 共用渲染大块内、引擎已支持的 task，不碰 R 端）**：
  - `single_group_meta`：`["forest"]` → `["forest","funnel","influence"]`（主森林图 + 漏斗图 + 影响诊断；
    baujat/radial 对 metaprop/metacor 对象不稳，不强行加）。
  - `subgroup_analysis`：`["forest"]` → `["forest","funnel","baujat","radial","trimfill","influence"]`
    （含 by-subgroup 分层森林图 + 异质性/发表偏倚/剪补/敏感性全套诊断，与 pairwise_meta 诊断集对齐）。
  - `metareg`：`["forest"]` → `["forest","funnel"]`（bubble 被锁死在 `bubble_plot` task，metareg 拿不到，
    见下方"需 R 端改动"项；此处加 funnel 作发表偏倚诊断）。
- **引擎能力核查结论**：`survival_meta`/`diagnostic_meta`/`metainc`/`ipd_meta`/`bayesian_pairwise` 在
  `run_task.R` 各自独立分支仅写了一种图的 `render_fig`（bayesian_pairwise 甚至无图），这些 task 想再加默认图
  需改 R 端，不在本次纯默认值调整范围内。

### Verified
- `py_compile` 通过；`_default_plots_for` 输出确认：single_group_meta=[forest,funnel,influence]、
  subgroup_analysis=[forest,funnel,baujat,radial,trimfill,influence]、metareg=[forest,funnel]、
  pairwise_meta(OR)=[forest,funnel,baujat,radial,labbe,trimfill]、nma=[netgraph,netleague]。
- `rendering._I18N['zh']['fig_netleague']` = 网络证据表；`['en']` = Network evidence table。

---

## [2.2.17] — 2026-08-28 — 图形默认出图与渲染健壮性修复

### Fixed（脚本 `scripts/build_request.py` + 呈现层 `adapters/rendering.py`）
- **`influence` 任务默认图不显示（核心 bug）**：旧 `DEFAULT_PLOTS["influence"] = []`，但 coze 端
  `run_task.R` 第 574 行 `if ("influence" %in% plots)` 才出影响力诊断面板——空 plots 仅返回 stats，
  面板永不显示，与注释"coze 自动渲染影响力诊断面板"不符。改为 `DEFAULT_PLOTS["influence"] = ["influence"]`，
  显式请求后 coze 正常出图；同步修正设计注释（influence 不再归入"空 plots 自渲染"组）。
- **`content_bbox` 健壮性加固（呈现层）**：原仅扫描 text/rect/line/circle/polyline。ggplot2 / 网络图
  主内容多为 `<path>`（曲线、edge），若漏扫会导致动态 viewBox 裁掉内容。新增：
  ① 解析 `<path d=...>` 绝对坐标对；② 将计算 bbox 与**原始 viewBox 取并集（union）**——既保留
  forest 负坐标溢出扩展，又保证 svglite 实际绘制区域（设备坐标恒在原 viewBox 内）不被裁。
  `build_figure_widget` 与 `svg_to_png` 两处调用均已传入原始 `vb`。

### Verified
- 审计脚本覆盖全部 23 个 coze 实际返回的 figure `type`（forest/funnel/labbe/baujat/radial/trimfill/
  influence/bubble/egger/netgraph/contribution/nodesplit/sucra/dose_resp/sroc/loo/cumulative/drapery/
  prisma_flow/gosh/tsa/power/rob2）：在 `render_html_report` 中**均以本地化标题正常显示**（无原始 type 兜底）。
- `content_bbox` 对森林图负坐标溢出（x∈[-140,644]）正确扩展；对纯 path 图形与原 viewBox 并集后不裁图。

---

## [2.2.16] — 2026-08-27 — 云端二次重建回归闭环确认（两项修复端到端生效）

### Verified（云端端到端，coze 节点用 coze_project_fixed_v2.zip 重建后）
- 用 6 研究 SMD+REML 亚组用例 POST `https://ct-meta.coze.site/run` 回归（cloud_regression_v2.json）：
  - `subgroup_test` = {Q_between=15.5055, df=1, p_between=0.0001, n_groups=2, model=random} —— 与本地 4.6.1 完全一致，**已生效**。
  - 亚组 short = -2.0473 [-2.395, -1.700]；long = -2.8913 [-3.127, -2.656]（长期降得更明显）。
  - pooled(REML) = -2.4631 [-2.875, -2.051]，p≈9.9e-32。
  - **森林图 SVG 头条闭环**：含 "Random effects model" ×3（short/long 亚组合并 + 总合并）、不含 "Common effect model"；头条数值 = -2.46（REML 合并量，非固定效应 -2.43）。问题二在云端彻底生效。
- 结论：coze_project_fixed_v2.zip 的两处修复（①森林图 `common=FALSE,random=TRUE` + 判断条件 `fit$random`；②`subgroup_test` 走 `Q.b.random` 原生槽位）在 coze 同款 R 4.6.1 + meta 8.5.0 环境下**端到端闭环**，不再需要 v1 或本地兜底。

---

## [2.2.15] — 2026-08-27 — 森林图头条二次修复：.forest_plot_theme 判断条件对齐 meta 8.5.0

### Fixed（coze 镜像 run_task.R）
- **根因（对 [2.2.14] 的纠正）**：[2.2.14] 修好了 `common/random` 形参与 `col.subgroup`，但 `.forest_plot_theme` 的分支判断条件
  `if (isTRUE(fit$comb.random))` **未同步修改**。meta 8.5.0 已弃用 `comb.random` 槽位（返回 NULL），
  故该判断恒为 FALSE → 永远走 `common=TRUE, random=FALSE` 分支，森林图头条仍画"Common effect model"（固定效应），
  与请求的 REML 随机效应口径不符、误导读图。
  ⚠️ [2.2.14] 第 19 行"头条=REML"为**误判**——当时本地验证未 grep SVG 模型名，仅依 subgroup_test 数值推断。
- **修复**：`.forest_plot_theme` 判断条件改为 `if (isTRUE(fit$random) || isTRUE(fit$comb.random))`，
  兼容 8.5.0 的 `random` 槽位（`fit$random=TRUE` 时即走 `common=FALSE, random=TRUE` 画随机效应头条）。

### Verified
- 本地 R 4.6.1 全流程跑 6 研究 SMD+REML 亚组用例：**SVG 含 "Random effects model"、不含 "Common effect model"**，证明头条修复生效。
- 云端回归（重建节点后）：`subgroup_test` 已在上一轮重建生效（Q_between=15.5055, p=0.0001, model=random）；
  森林图头条修复需**用本包（v2）再次重建 coze 节点**后方在云端生效（当前云端回归的森林图仍是 Common effect，因上一轮漏改判断条件）。

---

## [2.2.14] — 2026-08-27 — coze 镜像对齐 meta 8.5.0 破坏性变更（col.subgroup / Q.b.* 槽位）

### Fixed（coze 镜像 run_task.R + 本地验证环境升 R 4.6.1）
- **根因（部署环境 R 4.6.1 + meta 8.5.0 + metafor 5.0.1 的破坏性变更）**：历史镜像代码基于旧版 meta 假设，在 8.5.0 下行为失真：
  1. `meta::forest` 的 `col.by` 参数**已移除**（8.5.0 仅认 `col.subgroup`）→ 旧代码传 `col.by` 主题色静默失效（不报错但亚组分隔色丢失）。
  2. 亚组 `metacont/metabin` 结果对象的组间异质性槽位**更名为 `Q.b.random` / `Q.b.common`**（旧版为 `Q.between.random` 且旧版根本无该槽位）→ 历史 `subgroup_test` 主路径取 `fit$Q.between.random` 恒为 NULL，静默落兜底，与森林图 "Test for subgroup differences" 图例口径偶发不一致。
  3. （附带）`metacont(..., comb.random=)` 8.5.0 已弃用（改用 `random=`）；调用处写 `random = mm$comb.random`（值正确赋给新参数名），未触发弃用告警，无需改。
- **修复（run_task.R）**：
  - `.forest_plot_theme`：`col.by = th$by` → `col.subgroup = th$by`（3 处：comb.random / random 两分支 + tryCatch 兜底）。
  - `subgroup_analysis` 分支 `subgroup_test` 主路径：`fit$Q.between.random/.common` → `fit$Q.b.random/.common`（及 `pval.Q.b.*` / `df.Q.b.*`）；`rf` 判断改 `isTRUE(mm$random %||% mm$comb.random)` 兼容 8.5.0 的 `random` 槽位。
- **本地验证环境对齐**：旧版本地 R 4.5.1（meta 旧版）无法暴露这些槽位、也不吃 `common` 形参，验证无效；按用户要求本地验证环境升级到 R 4.6.1（与 coze 同款），实测：
  - subgroup_test 走 8.5.0 原生 `Q.b.random` 主路径 → `Q_between=15.5055, df=1, p=0.0001, model=random`，与云端此前 15.51 / <0.0001 完全对齐；
  - 森林图成功出图、无 `col.by` 告警、头条=REML（common=FALSE, random=TRUE）。

### Verified
- 本地 R 4.6.1 跑 6 研究 SMD+REML 亚组用例：subgroup_test 主路径生效、亚组 short=-2.0473 / long=-2.8913、pooled=-2.4631，全部正确；无 col.by / comb.random 告警。

---

## [2.2.13] — 2026-08-27 — 默认图形随分析方法自动适配（不再写死森林图）

### Fixed（build_request.py + coze_contract.md 文档同步；coze 镜像无需改动）
- **根因**：旧 `build_request.py` 永远发 `figure.plots=["forest"]`，且用户 plots 只能追加 `funnel`。coze 镜像 `run_task.R` dispatch **严格按 `figure.plots` 出图**，其各 task 默认图（nma→netgraph+netleague、diagnostic→sroc 等）仅在 `plots` 为空时触发——而 `plots` 永远非空 `["forest"]`，故兜底从不触发，所有 task 只落森林图。下游 HTML（`rendering.render_html_report`）只是内联 coze 返回的 `figures[]`，无硬编码，故"coze 与 HTML 都只给森林图"是同一根因的两层表现。
- **修复**：`build_request.py` 新增 `DEFAULT_PLOTS`（每 task 默认图，对齐 `coze_contract.md §3`）与 `VALID_PLOTS`（用户显式覆盖时的合法图名校验）。
  - 用户未指定 → 按 `spec.task` 取 `DEFAULT_PLOTS`（pairwise→forest+funnel、subgroup/metareg/bayesian/survival/single_group→forest、nma→netgraph+netleague、nma_rank→sucra、diagnostic→sroc、dose_resp→dose_resp、gosh→gosh 等）。
  - 用户显式 `params_extra.plots` → 采用（过滤 `VALID_PLOTS` 中的非法名；全非法则回退该 task 默认）。
- **文档同步**：`coze_contract.md §3` 三处与镜像矛盾修正——`metareg` 默认图 `bubble`→`forest`（`run_task.R:494` 的 bubble 图仅对 `task=="bubble_plot"` 生效、metareg 不发）；`nma_rank`/`dose_resp` 默认图由 `—` 补全为 `sucra`/`dose_resp`（`run_task.R` 对应分支空 plots 时即默认出此图，与代码一致）。
- **验证**：11 个分析方法默认图 + 用户覆盖（forest only / nma+contribution）+ 非法回退，共 14 用例冒烟全过（ALL_OK）。

---

## [2.2.12] — 2026-08-27 — build_request 不诚实字段清理：diagnostic_meta / survival_meta 跳过 params.sm

### Fixed（build_request.py + coze_contract.md 文档同步；coze 镜像无需改动）
- **`params.sm` 噪音字段清理**：经核对 coze 镜像 run_task.R 一手代码，`diagnostic_meta`（`mada::reitsma`，合成灵敏/特异度/SROC，不读 sm）与 `survival_meta`（`metafor::rma.uni(logHR)`，固定合 HR，不读 sm）**不消费 `params.sm`**。旧逻辑 `sm = measure_override or spec.measure or "OR"` 对所有 task 无差别写 `OR`，对这两 task 是镜像永不读的噪音字段，且 `coze_contract.md §3` 列 `sm` 为「所有 task 通用可选」会误导用户以为诊断/生存也能按 OR 换尺度。
  - 新增 `NON_SM_TASKS = {"diagnostic_meta", "survival_meta"}`；`build_request.py` 的 `params` 构造段对这两 task **跳过写 sm**，request 诚实。
  - ⚠️ **nma 仍消费 sm**（netmeta `sm` 参数，run_task.R:581 `sm <- params$sm %||% "OR"`），且连续型 nma 须显式 MD|SMD——**不剔除**，仅 diagnostic/survival 清理。
- `coze_contract.md` §3 同步：
  - `params.sm` 字段表加注「`diagnostic_meta`/`survival_meta` 不消费此字段」。
  - `nma` 行注明**消费** sm（二分类默认 OR / 连续型须显式 MD|SMD）。
  - `survival_meta` 行注明不消费 sm（HR 即效应尺度）。
  - `diagnostic_meta` 行注明不消费 sm（合成灵敏/特异度，非 OR 类）。

### Verified
- 实测 4 用例：`pairwise_meta`/`nma` → `params` 含 `sm=OR`（保留）；`diagnostic_meta`/`survival_meta` → `params` **不含 sm**（已剔除）。回归：classify + build_request import 无语法错误。

---

## [2.2.11] — 2026-08-27 — NMA 三格式自动探测：连续型/对比格式不再需 --colmap 回灌

### Fixed（build_request.py 本地修复；coze 镜像 run_task.R .nma_prep 已原生支持三种输入格式，无需改动）
- **NMA 列格式自动探测（消除 [2.2.10] Known limitation）**：`build_request.py` 对 `task=="nma"` 不再盲信 classify 固定的 arm-based 二分类列模板，改用新增 `_detect_nma_format()` 按数据实际列名自动选格式，对齐 run_task.R `.nma_prep` 与 coze_contract.md §3：
  - 对比二分类 `treat1/treat2 + event1/n1/event2/n2`
  - 对比连续 `treat1/treat2 + TE/seTE`（亦认 `te`/`sete`）
  - arm-based 二分类 `treatment + event + n`
  - arm-based 连续 `treatment + te + sete`
  - 同组（对比 / arm）内 binary 与 continuous 取「完整命中」者；均无完整命中则取命中列最多者交 LLM 兜底（exit 2，红线：有边界兜底、不破快路径）。
- 新增 `NMA_FORMATS` 列契约表 + 中/英别名（处理1/干预1/事件1/样本量1…），覆盖常见中文列名。
- `_coerce_rows` 增加 `non_numeric` 参数：对比格式的 `treat1`/`treat2` 臂标签列改为字符串透传（此前仅 `treatment`），避免 float 强转报错。
- 修正 nma 分支 `subgroup` 未初始化导致的 `UnboundLocalError`。

### Verified
- 实测 6 用例：T1 对比二分类 / T2 对比连续(TE/seTE) / T3 arm二分类(中文别名) / T4 arm连续 / T5 对比(中文别名) 全部正确探测+归一化为 coze 期望的小写规范列名；T6 无结构列正确走 `needs_llm_fallback`(exit 2)。四种格式现均无需 `--colmap` 即可直接装配 request.json。

---

## [2.2.10] — 2026-08-26 — 契约联调修复：task 名对齐 coze + build_request 列透传缺陷

### Fixed（与 coze 镜像 run_task.R / coze_contract.md §3 联调，修正一批会导致 unknown_task / 静默失效的真实 bug）
- **classify.py task 名契约断点（最致命）**：原 `network_meta` / `diagnostic` 与 coze 端点 task 白名单不符（coze 只认 `nma` / `diagnostic_meta`），NMA 与诊断 meta 会直接 `unknown_task` 失败。已改为 `nma` / `diagnostic_meta`（与 coze_contract.md §3、run_task.R dispatch 一致）。
- **classify.py 诊断 data_type 回归**：改 task 名时漏改 `if task == "diagnostic"` 守卫 → 诊断 query 错误回退 `data_type=binary`、列模板变成 `event_exp/n_exp…` 而非 `tp/fp/fn/tn`。已同步为 `if task == "diagnostic_meta"`；实测 `classify("做诊断试验meta分析")` 现返回 `task=diagnostic_meta / data_type=diagnostic / colmap=[tp,fp,fn,tn]`。
- **build_request.py 亚组变量列被丢弃（静默失效 bug）**：`_coerce_rows` 只输出 colmap 数值列，亚组变量列（如 `age`/`region`）不在 colmap 内被丢弃 → coze 收不到该列、`subgroup_analysis` 静默降级为主分析。已新增 `carry_cols` 原样透传亚组列；实测 `subgroup_analysis` 现正确携带 `params.subgroup` 对应列。
- **build_request.py 分类列被强制 float（nma 报错）**：`_coerce_rows` 对全部列 `float()` 强转，nma 的 `treatment` 臂标签列（字符串）直接报错。新增 `NON_NUMERIC_KEYS={"treatment"}` 透传字符串列；实测 arm-based 二分类 nma 数据现正常装配 `task=nma` + `treatment/event/n`。
- **classify.py nma 默认列模板错误**：nma 未单设 data_type，默认套用二分类 `event_exp/n_exp/event_ctrl/n_ctrl`（coze `.nma_prep` 不接受配对格式）。已加 `data_type="nma"` + `COLMAP["nma"]=["treatment","event","n"]`（arm-based 二分类默认；连续/对比格式走 `--colmap` 兜底）。
- **coze_client.py `byvar`→`subgroup` 兜底映射补回**：CHANGELOG `pending-2.2.1` 记录此修复但代码从未落地；`run_meta()` 现对 `params.byvar` 做 `subgroup` 归一化，兼容历史 spec，避免静默失效。

### Docs（与代码同步）
- SKILL.md §5.0 端点能力边界整段重写：以 coze_contract.md §3 + run_task.R 为准，`metareg` ✅已接线（需 `te`/`sete` + `params.cov`）、`nma`/`nma_rank`/`survival_meta`/`diagnostic_meta` ✅，删去原"metareg 未接线 / nma·diagnostic 未注册"过时错误。
- SKILL.md §5.1 + references/interactive_menu.md §6 回显块/范例：占位 task 名 `forest`→`pairwise_meta`、`subgroup`→`subgroup_analysis`；`byvar=`→`subgroup=`（§5.0 明令 byvar 静默失效）；补 `task=sensitivity` 实为未注册 task、应复用 `pairwise_meta` 做 leave-one-out 的说明。
- `pending-2.2.1` 标记已由本版落实，并更正其 `metareg 未接线` / `diagnostic 未注册` 两条与镜像实测矛盾的旧结论（`diagnostic_meta` 已注册）。

### Known limitation（本版未改，待后续）
- ~~nma 连续型 / 对比格式需 --colmap 回灌~~ → **已在 [2.2.11] 修复**：`build_request.py` `_detect_nma_format()` 按数据实际列名自动探测四种 NMA 输入格式（对比二分类/对比连续/arm二分类/arm连续），无需 `--colmap`。
- diagnostic_meta 默认 `params.sm=OR`（mada reitsma 通常忽略 sm，无害）。

### Verified
- 实测 6 用例：classify(诊断) / pairwise OR / diagnostic_meta / subgroup(age 透传) / nma(arm-based) 全部产出 task 名与列映射对齐 coze_contract.md §3 的 request.json；无 unknown_task 风险。

---

## [2.2.9] — 2026-08-27 — 长上下文保护：§0 规则 1 跨轮引用 carve-out（合法使用对话历史回填参数，不破速度纪律）

### Added（解决"严格纪律在长对话里误伤引用前文轮次"的缺口）
- **规则 1 carve-out**：「禁止深度思考」仅约束计算/呈现阶段；用户显式引用前文（"用之前的数据""和刚才一样"）时，LLM 允许回看对话历史提取既有数据/spec **用于回填 `--data-json`/参数**，但禁止据此重新推导数值或重路由。
- **延迟不变量补"跨轮回填例外"**：回看对话历史构造 `--data-json` 属构造入参、非额外工具调用，不计入火前 ≤1 次数；回填后仍是 1 次 `build_request.py`。仅放宽数据来源，不放宽计算/呈现禁令。
- **背景**：确认当前方案对长上下文交互无系统性负面影响（路由确定性 + 对话流零图形双保险），但"引用前文"轮次会被严格纪律误伤——本补丁收窄该缺口，速度内核不变。

---

## [2.2.8] — 2026-08-27 — 有边界 LLM 兜底：build_request.py 列名别名自动匹配 + needs_llm_fallback + --colmap/--measure/--model 回灌

### Added（错误触发、范围受限，不破默认快路径）
- **`COLUMN_ALIASES`**：中/英同义列名表（实验组事件数/处理组事件/trt_ev…），先自动模糊匹配，吃掉大部分"列名不符"。
- **`needs_llm_fallback`**：别名仍解析不出 → 发结构化 JSON（exit 2，含 `unresolved_columns`/`available_columns`/`partial_spec`/`hint`）。
- **回灌参数**：`--colmap`（列映射）/ `--measure` / `--model`，LLM 仅补缺映射或纠正参数后重跑；`_resolve_colmap` 优先采用 override。
- **错误分流**：列缺失走兜底路径；值非数值/缺值等用户数据错误为硬错误（exit 1），不兜底。
- **文档**：SKILL.md §0 规则 7（有边界 LLM 兜底）+ 延迟不变量补"兜底例外"；顶部红线注释同步。
- **实测**：中文列名别名匹配✅、陌生列名发 fallback✅、--colmap 回灌成功✅、非数值硬错误✅、原 4 项 OR 回归同构✅。

---

## [2.2.7] — 2026-08-27 — Phase 2 闭环：scripts/build_request.py（compute 轨 request.json 一键装配）

### Added（消灭"LLM 手写 request.json"，让延迟不变量真正可达）
- **新增 `scripts/build_request.py`**：计算轨归一化/装配脚本，**零 LLM 决策、零计算、零出网**。一次本地调用内完成：调 `classify.py` 出 spec → 校验数据列 → 装配 `run_analysis` 的 `request.json`。
  - 输入：`--query`（内部 classify）或 `--spec`；研究数据 `--data path.csv/.json` 或 `--data-json '[{...}]'`；输出 `--out request.json`。
  - 映射：`measure`→`params.sm`、`model` REM-L→REML(common:false,random:true) / MH→MH(common:true,random:false)、亚组变量→`params.subgroup`、funnel→`figure.plots`（forest 恒含）。
  - 红线：选题轨（`track==topic`）直接拒；缺列报错列名；`--data` 已给时覆盖 classify 仅凭 query 文本判的 `needs_clarify`（避免误报缺字段）。
- **§0 双轨门控 / 延迟不变量更新**：计算轨火前唯一动作显式写为一次 `build_request.py` 调用（内部含 classify），彻底取代"classify + LLM 手写 request.json = 2 次"的旧路径；§1 Triage 说明同步更新为"LLM 不再手写 request.json"。
- 实测（本地、零出网）：4 项 OR 随机效应 / 固定效应 RR / 亚组按年龄+漏斗图 / 选题轨拒 / 缺列报错——5 用例全过。
- 受影响文件：`scripts/build_request.py`（新增）、`SKILL.md`（§0 / §1）、`CHANGELOG.md`（本条）。

---

## [2.2.6] — 2026-08-26 — Phase 2 代码：scripts/classify.py 双轨路由脚本

### Added（把"火前路由犹豫"也压成代码，对齐 ct-advisor route.py）
- **新增 `scripts/classify.py`**：确定性 NL→spec 映射脚本，**零 LLM 决策、零计算、零出网**。输入用户 query，输出 `spec` JSON（`track` / `task` / `measure` / `model` / `data_type` / `params_extra` / `needs_clarify` / `missing_fields` / `colmap`）。
  - 关键词表覆盖：选题轨、数据类型（binary/continuous/diagnostic/survival/ipd）、效应量（OR/RR/RD/MD/SMD/HR）、模型（REM-L 默认 / MH）、task 覆盖（pairwise_meta/subgroup_analysis/metareg/network_meta/survival_meta/diagnostic）、plots（funnel/egger）、亚组变量抽取。
  - 判定顺序：track → task → data_type → measure → model → plots/subgroup → 数据迹象校验（`\d+/\d+` 或含数据词 + 数字；compute 轨无数据即 `needs_clarify=true`，仅回缺字段）。
  - `colmap` 给出默认列名建议（binary→`event_exp/n_exp/event_ctrl/n_ctrl` 等），agent 直接套用归一化。
- **§1 Triage 顶部加说明**：路由已由 `classify.py` 代码完成，LLM 不再决策；附表仅供理解。
- 延迟不变量兑现：计算轨 fire 前本地工具调用 ≤1 可由一次 `classify.py` 调用承担（取代此前翻 SKILL/references/adapter 的 10–20 轮火前拖拽）。
- 受影响文件：`scripts/classify.py`（新增）、`SKILL.md`（§1 说明）、`CHANGELOG.md`（本条）。

---

## [2.2.5] — 2026-08-26 — 流程控制：双轨门控 + 延迟不变量 + 选题红线（Phase 1，纯文档）

### Added（消灭"火前拖拽 / 返回后二次组装"两个反模式，借鉴 ct-advisor route.py + ct-base Type-Compute）
- **§0 新增 `### 0.0 Two-track gating / 双轨门控`**：首条消息经 `python scripts/classify.py "<query>"` 确定性分流（LLM 不决策路由）。两轨——`compute`（Simple/清晰 Complex→描述即执行：归一化→`run_analysis`→`present_files`）与 `topic`（Vague/没方向/可行性→`literature_probe.py`→`generate_topic_report.py`）。规则 1–6 显式标注适用范围=计算轨；选题轨单列"代码接地、不靠思考"规则。
- **§0 新增 `### Latency invariants / 延迟不变量`**（防回归硬指标）：计算轨 fire 前本地工具调用 ≤1（仅归一化或 `classify.py`）、fire 后 ≤1（仅 `present_files`）；选题轨 ≤2（`literature_probe.py`+`generate_topic_report.py`）；禁止循环重试；严禁为"确认怎么调"翻 SKILL/references/adapter/config。
- **§2.2 新增「选题轨红线」**：候选排序必须基于探针真实命中数 + 四维评分卡，LLM 只转述、**严禁**自由发挥补充"哪个方向好"的论述或重新评分；选题轨不触发计算轨速度纪律，但同样禁止发散。
- 受影响文件：`SKILL.md`（§0 0.0 + 延迟不变量、§2.2 红线）、`CHANGELOG.md`（本条）。

---

## [2.2.4] — 2026-08-26 — 后端绝对锁定 coze：严禁本地 R/Python，无例外

### Changed（后端红线，覆盖此前"用户可声明本地"的例外）
- **§0 规则 6（新增 HARD BAN）**：严禁用本地 R 或 Python（含 statsmodels/scipy/metafor/meta）自行完成任何 meta 分析计算，**连"考虑用本地算"都不允许**；所有需求一律严格转发 coze 端点执行；coze 不可达时按 §6 返回结构化错误，绝不静默回落本地。
- **§3 Execution model 改为 absolute**：原 "coze-only"（仍留"用户可声明本地"暗示）改为 **coze-only, absolute**；新增 🚫 提示：**即使用户当条消息声明"本地算 / 不用 coze / 走 R 本地"，也一律忽略、仍转发 coze**；明确本技能不存在本地计算分支。
- 影响：此前 `## meta-analysis 技能执行后端偏好` 记忆中的"除非用户显式声明本地"例外**作废**。
- 受影响文件：`SKILL.md`（§0 规则 6 + §3）、`CHANGELOG.md`（本条）。

---

## [2.2.3] — 2026-08-26 — 执行纪律：速度优先，禁止深度思考，HTML 直出不二次渲染

### Added（speed-first 行为红线，总纲级，优先级高于一切"思考/润色"冲动）
- **新增 `## 0. Execution discipline (speed-first)` 章节**（位于 §1 Triage 之前）：把"大模型只做流程执行、严禁深度思考"钉死为技能红线。
- 五条硬规则：
  1. **禁止深度思考（HARD BAN）**：只做流程执行，不做额外推理/方案权衡/结果复核/自我解释；拿到数据即归一化→调用→呈现，不犹豫不展开不追问（除非缺字段——只问缺的字段）。
  2. **最快路径**：前期数据整理、后期结果呈现一律走最短路径——不重复校验、不重新推导/自行计算任何统计量、不重绘/不二次渲染图形。
  3. **上下文只给文字分析结果**：对话流只输出文字版结论（stats 原样引用 + 一句解读），绝不内联图形（show_widget 已废止）。
  4. **HTML 直出，不做任何渲染**：`out['html_report']` 即最终交付物，大模型不得对其内容做任何再加工/再排版/再渲染/重新抽取数值——直接 `present_files` 打开。图形只在 HTML 中展示（原始宽度、过宽滚动）。
  5. **数字零改写**：数值必须原样引用 coze 返回的 stats，禁止四舍五入/换算/重新格式化。
- 受影响文件：`SKILL.md`（新增 §0）、`CHANGELOG.md`（本条）。`inline_rendering.md` / `rendering.py` 无需改动（既有实现已满足"不放大 + HTML 单一面"）。

---

## [2.2.2] — 2026-08-26 — 呈现层变更：取消内联 widget，图形一律走 HTML 报告（SVG 不放大）

### Changed（呈现层硬约束，skill 开发者决策）
- **取消内联 `show_widget` 渲染（原 §5 默认且强制）**：所有 `figures[].svg` 不再内联进对话流，改由 `run_analysis` 生成的聚合 HTML 报告（`out['html_report']`）统一展示，agent 用 `present_files` 打开预览。原强制内联规则（"figures must NOT be delivered merely as file cards" / 约束 #4 "Figures inline by default (mandatory)"）改为 "Figures in HTML report (mandatory)"。
- **SVG 宽度规则**：图保持自然内容宽度，**绝不放大到固定画幅**（如为 680px 容器而拉伸 504px 图）。嵌入按 `content_bbox` 算出的实际内容宽度，装不下即横向滚动。该行为由 `rendering.py` 的 `build_figure_widget` / `render_html_report` 已实现（SVG `width:{w}px`，`w = max_x - min_x`，无 680px 固定画布）；本次仅把规范对齐到既有实现，并废止此前为满足 show_widget 680px viewBox 而手动拉伸 SVG 的做法。
- 受影响文件：`SKILL.md` §5（Rendering + 约束 #4 + figure_mode 说明）、`references/inline_rendering.md`（标题与 §1/§3/§8 改为"HTML 报告唯一面 + 不放大"）。

### Verified
- 既有 `rendering.py` 无 680px 固定画布；`build_figure_widget` 输出 `width:{w}px`（w=自然内容宽）。本次仅改文案，渲染链零改动。

---

## [2.2.1] — 2026-08-26 — 契约对齐：亚组参数键 byvar→subgroup + 端点能力边界实测（已由 2.2.10 落实；metareg/diagnostic_meta 结论已更正）

### Fixed（本地契约 bug，实测发现）
- **亚组分析静默失效（契约 bug）**：SKILL.md §5.1 跨轮 spec 字段名写 `byvar`、task 名写 `subgroup`；但 coze 端点实际（2026-08-26 线上探测）只认 `subgroup_analysis` task + `subgroup` 参数键（`byvar`/`group`/`by`/`strata` 全部静默忽略，仅回主分析合并值）。修复方式双保险：
  1. `adapters/coze_client.py` `run_meta()` 在发请求前做 `byvar`→`subgroup` 兜底映射（兼容历史 spec 字段名，避免静默失效）；
  2. SKILL.md §5.1 的 spec 字段、回显块、task 切换示例全部对齐到实测契约（`byvar`→`subgroup`，`task:subgroup`→`task:subgroup_analysis`）。

### Documented（端点能力边界，实测标注，非本地可修）
- `pairwise_meta` ✅ 完整（异质性 I²/τ²、Egger/Begg、漏斗、质量门）；
- `subgroup_analysis` ✅ 正常（参数键 `subgroup`）；
- `metareg` ✅ **已接线**（2026-08-26 实测 + coze_contract.md §3 对齐）：需提供已算效应量列 `te`/`sete` + 协变量列，并以 `params.cov` 传协变量列名；仅给原始二分类/连续列会静默降级为 `pairwise_meta`。原 pending 记录"15 键均不返回 regression"系历史探测误判，已更正。
- `nma` ✅ 注册（需每研究 ≥2 臂）；
- `sensitivity` / `pub_bias` / `publication_bias` ❌ 未注册（`unknown_task`）；发表偏倚已内嵌进 `pairwise_meta` 自动算，无需单独 task。**更正**：`diagnostic` 未注册但 `diagnostic_meta` ✅ 已注册（原 pending 把两者混为一谈，已更正）；classify.py 现发 `diagnostic_meta`。

### Verified
- 线上实测：20 项 MDD RCT（OR），`subgroup_analysis`+`{"subgroup":"region"}`→ Asia/Europe/NorthAmerica 三亚组效应量正确分层；`metareg` 15 键均不返回 `regression`；`sensitivity`/`pub_bias` 返回 `unknown_task`。

---

## [2.2.0] — 2026-08-26 — 图形回归修复 + 扩充影响诊断 / 节点拆分 / 剪补法漏斗

### Fixed（coze 端图形回归，线上实测发现）
- **`.render_fig` 未打印 ggplot 对象**：原函数对 `function() .sucra_plot(rk)` / `.egger_plot()` / `.bubble_plot()` 这类「返回 ggplot」的工厂直接调用并丢弃返回值 → SVG 为空。线上实测 sucra/egger/bubble 三个图均返回 0 字节 SVG。改为捕获函数返回值、若为 ggplot 则 `print()`，基础绘图函数（forest/funnel/netgraph 等副作用绘制）不受影响。
- **NMA 贡献图静默失败**：`netmeta::netgraph(fit, contribution = TRUE, seq = TRUE)` 在 netmeta 3.6.1 不支持（`contribution` 被当图形参数忽略、`seq` 触发「argument is not interpretable as logical」），原 tryCatch 静默吞错 → `figures` 为空。改用 `.contribution_plot()`：优先原生 `netgraph(contribution=TRUE)`（新版本），否则走 `decomp.design()` 取各比较对不一致性的贡献（Q.inc.design）以 ggplot 条形图呈现，version-independent。

### Added（进一步扩充支持范围）
- **影响诊断图 `influence`**（pairwise_meta 等分支，`plots:["influence"]`）：`metafor::influence(rma_fit)` 多面板（Cook 距离 / 杠杆 / CovRatio / DFFITS / hat），7×9 SVG。
- **节点拆分图 `nodesplit`**（nma 分支，`plots:["nodesplit"]`）：`netsplit(fit)` → `forest()` 呈现局部不一致性（直接 vs 间接 vs 网络估计），netmeta 已依赖。
- **剪补法漏斗图 `trimfill`**（pairwise_meta 分支，`plots:["trimfill"]`）：`meta::trimfill(fit)` 后画漏斗，呈现发表偏倚校正后估计。
- 渲染层 `rendering.py` 双语图注补齐 `fig_influence` / `fig_nodesplit` / `fig_trimfill`，`type_names` 映射同步；现支持 **23 种** coze figure type 全图注。

### Verified
- R `parse()` 通过；本地 R 4.6.1 跑 `run_task.R` 真路径：sucra 5121 / egger 11439 / contribution 4903 / loo 8962 / cumulative 8963 / influence 43986 / nodesplit 12066 / trimfill 19967 / bubble 7017 字节 SVG 全部非空；`render_html_report` 23 种 type 双语自测 raw_hits=[] 且 missing=[]。

---

## [2.1.7] — 2026-08-26 — coze 端点重构：ct-meta2 主 / ct-meta 回退 + per-endpoint token

### Added
- **主工作流端点切换为 ct-meta2、回退 ct-meta**：`DEFAULT_ENDPOINT=https://ct-meta2.coze.site/run`（用户新 token，aud=`5v9HMQWtTSzxrEeZjI7kJJEzeMPrHXny`）；`FALLBACK_ENDPOINT=https://ct-meta.coze.site/run`（旧端点，保留旧 token，aud=`oxwSsfwdtRRfByYIM8Xg3U4RQH5OgEjO`）。
- **token 改为按端点分别解析**：`coze_token.get_token_for(endpoint)` 按 URL 映射不同工作流 JWT（ct-meta2 用新、ct-meta 用旧），不再全局共用；`_resolve_token(endpoint)` / `_headers(endpoint)` 接收端点参数，回退时用回退端点专属 token。优先级：`COZE_META_TOKEN`（全局覆盖）> 端点专属内嵌 blob > 历史默认 blob。
- **回退触发条件**：主端点因 token 不一致（401/403 + token/auth/invalid 关键字）失败时自动回退重试；回退成功结果附 `_coze_endpoint_notice` 并追加 notes「主分析工作流地址已切换，本次分析已自动回退到备用 coze 端点完成」。双端均 token 失败则抛错提示更新技能。
- `config.json` 白名单：移除 `wr65rdbc4w`，加入 `ct-meta2`（现三项：ct-meta2 / ct-meta / ct-bugreport）。

### Changed
- `coze_token.get_token` 重构为 `get_token_for(endpoint)` + `ENDPOINT_TOKEN_MAP`，支持 per-endpoint 凭据；`SKILL.md` / `README*` / `coze_integration_test.py` 同步更新旧默认端点引用。

### Verified
- 模块编译；`get_token_for("ct-meta2")`→aud=`5v9HMQWtTSzxrEeZjI7kJJEzeMPrHXny`、`get_token_for("ct-meta")`→aud=`oxwSsfwdtRRfByYIM8Xg3U4RQH5OgEjO`（二者不同）；线上探测两端点均 HTTP 200 + `unknown_task`（token 被接受）。

---

## [2.1.8] — 2026-08-26 — 聚合 HTML 报告（结果展示改进）

### Added
- **`rendering.render_html_report(out, out_dir="output")`**：把分析结果拼成单文件聚合 HTML 报告（内联 SVG 图形 + 统计结果明细表 + `<details>` 折叠可复现 R 代码），固化在**本地 agent 侧**。coze 返回体仅含 `stats`+S3 `url`，**不受 4000 截断与 S3 链接过期影响**；`_coze_truncated` 存在时报告顶部附截断告警 banner。
- 复用 `build_figure_widget`（含 content_bbox 扩展 viewBox、clip 移除、points 拆分与同名 CSS 变量），并自包含浅色主题 CSS（定义 `--color-text-primary` 等变量确保内联 SVG 区块在独立文件里正确着色）。
- `run_analysis.run_analysis` 成功分支自动调用，结果 `out['html_report']` 写入报告路径；生成失败不影响主结果（try/except 静默）。

### Changed
- `run_analysis` 顶部 import 增加 `render_html_report`。

### Verified
- 离线验证：真实森林图(8056B)+漏斗图(6321B) SVG 正确固化进单文件 HTML(17.5KB)，统计表 / 折叠 R 代码 / 截断 banner / CSS 变量解析 / `.format` 占位符清理均正确；`run_analysis` import 链编译无误。

### Fixed
- **PRISMA 流程图 `prisma_flow` 渲染崩溃（线上实测 status=error：`object 'label' not found`）**：`plot_prisma_flow`（`adapters/coze_project/src/r_engine/advanced_functions.R`）把 `label` 设在 `ggplot(df, aes(..., label = label))` 的**全局美学**里，被第 3 层 `geom_segment` 继承，而该层自己的 data.frame（x/y/xe/ye）无 `label` 列 → 渲染期报错。改为把 `label = label` 移入 `geom_text(aes(label = label))` 局部美学，`geom_segment` 不再继承 `label`。本地 R 4.6.1 复现并修复：ggsave 输出 5588 字节 SVG 正常。
- **SKILL.md `description` 与 `summary` 对齐**：`summary` 已含「等共 23 种分析图形」，`description` 中文段原缺失该表述 → 已补齐，英文段同步加「for a total of 23 analysis figures」，保留 ` / ` 双语分隔。

---

## [2.1.9] — 2026-08-26 — 新增四张图形（SUCRA / Egger / 贡献图 / 留一法·累积）并补齐 HTML 双语展示

### Added
- **SUCRA 排名图（`sucra`）**：NMA 排序图。在 `nma_rank` 分支接线 `if("sucra" %in% plots || (task=="nma_rank" && length(plots)==0))`；新增 `.sucra_plot(rk)`（ggplot 水平条形图，读 `rk$Pscore.random`/`Pscore`，零新增包）。
- **Egger 回归散点图（`egger`）**：在 `pairwise_meta`/`funnel_plot`/`trimfill`/`subgroup_analysis`/`metareg` 的偏倚块内接线 `if("egger" %in% plots)`，复用已算 `rma_fit`；新增 `.egger_plot(rma_fit)`（ggplot 散点 + `geom_smooth(lm)`，x=1/SE，y=yi/SE）。
- **NMA 贡献图（`contribution`）**：在 NMA 分支接线 `if("contribution" %in% plots)`，调用 `netmeta::netgraph(fit, contribution=TRUE, seq=TRUE)`。
- **留一法影响图（`loo`）/ 累积 Meta 图（`cumulative`）**：分别在 `leave_one_out` / `cumulative_meta` 分支接线（默认出图），用现有 `loo_df`/`cu_df` 经 `metafor::forest` 画 forest 变体。
- **HTML 双语展示补齐**：`rendering.py` 的 `_I18N`（zh/en）与 `type_names` 新增 `sucra`/`egger`/`contribution`/`loo`（`cumulative` 此前已在字典内，本次真正出图）。`locale="en"` 时对应英文 caption 生效。

### Changed
- 所有新增 `figs <- c(figs, list(.render_fig(...)))` 均用 `tryCatch(..., error=function(e) figs)` 包裹：单图出错仅静默降级、不影响其他图形与整体返回（`.render_fig` 自身无错误保护）。
- 后续发布不再带本地 R 引擎，图形一律由 coze 端 R 引擎（`adapters/coze_project/src/r_engine/`）生成，故改动落在 coze_project 代码而非本地 r_engine。

### Verified
- R 语法：`parse()` 通过 `meta_analysis_core.R` / `run_task.R` / `network_meta_analysis.R`。
- 渲染层：合成多 type figures 调 `render_html_report(locale=zh/en)`，12 项 caption 断言全 OK（含 `L'Abbe` / `Egger's` 撇号转义归一化），`type_names` 无回退到裸 type。
- **未做**：coze 容器端到端 SVG 生成（需重新部署到 ct-meta2 端点；按发布红线未自动部署）。

---

## [2.1.6] — 2026-08-26 — 图形默认内联 + 停止 SVG 精简

### Changed
- **图形默认内联（强制）**：`SKILL.md` §5 明确 `figures[].svg` **默认内联渲染进对话流**，agent 须用 `show_widget` 内联展示，不得退化为仅文件卡片/附件；S3 外置仅影响传输层，不改变内联默认行为（`coze_client._fill_external_svgs` 默认回填内联 SVG）。
- **停止 SVG 精简、原样输出**：`run_task.R` 的 `.render_fig` 移除 `minify` 形参与 `.minify_svg` 调用，直接透传 svglite 原始字符串（`.minify_svg` 保留为 DEPRECATED 死代码，不再被调用）。`coze_contract.md` §5 同步声明 `figures[].svg` 为 svglite 原始输出、不做任何 minify。
- 4000 截断防护改为完全依赖 S3 外置（传输层）+ 字段重排 + `_trim_to_limit` 兜底，不再依赖体积精简。

### Verified
- `run_task.R` 源码自洽：`.render_fig` 透传、`minify` 调用已删、`.minify_svg` 仅注释保留，无悬空引用。

---

## [2.1.5] — 2026-08-26 — README 去除内部框架注解

### Changed
- `README.md` / `README_zh-CN.md` 示例 1 段落移除面向用户的代码关联注解：
  - 删除反引号文件路径引用 `` `references/topic-selection.md` ``；
  - 删除英文代码标签 `(Topic Selection)`、`(upstream gate)`、`Stage 1 Gate 1`、`Rule R7`；
  - `Full Assessment` 代码阶段名改写为可读描述「完整选题评估 / full topic assessment」。
- 保留用户可点击的 `references/ADVANCED*.md` 导航链接（非注解，正常文档链接）。

---

## [2.1.4] — 2026-08-26 — README 示例1 校正（改为探针真实证据）

### Changed
- `README.md` / `README_zh-CN.md` **示例 1 答案重写**：原答案把「非糖尿病 CKD」列为首选（新颖性 5、总分 18，称其为真实缺口），
  与 in-skill 去重探针实测矛盾——探针显示非糖尿病 CKD（Cochrane 20 / PubMed 2402）与透析/晚期 CKD（22 / 1067）**均已高度饱和**。
  改为基于探针真实命中数的结论：首选 **IgA 肾病肾保护**（4 / 224）、次选 **净获益框架**（5 / 442）、
  条件型 **特定肾小球疾病**（FSGS 0 / 膜性 1 / ADPKD 2 / 狼疮 3）；并保留「先用 ct-literature 全量确证缺口」的提示。
- 示例 1 下方「说明」同步明确：候选方向基于**自含去重探针（Cochrane + PubMed 真实命中数）**核查（R7 规则）。
- 全文简化，未机械复制候选地图。

---

## [2.1.3] — 2026-08-26 — 探针 ↔ ct-literature 无缝对接 + 快速检索提示

### Added
- `adapters/literature_probe.py`：输出新增 `ct_handoff` 块（Cochrane / PubMed 两层的 ct-literature 复现命令
  + 原始 Europe PMC 查询串 + “快速检查 vs 全面检索”提示）；`probe()` 单层与 `dedup_probe()` 均携带该块。
- `references/dedup-search.md`：新增「快速检查 vs 全面检索（何时用 ct-literature）」段，明确本探针只是
  选题去重快速检查，全面检索先走 ct-literature，并给出可直接复制的命令。
- `SKILL.md` §2.2：选题去重 self-contained 说明补一句——“快速去重检查，非全面检索；全面检索先使用 ct-literature”。

### Changed
- 回写 **ct-literature（v0.10.1）**：新增 `--cochrane` 检索能力（Europe PMC 期刊过滤，过滤串与探针
  **完全一致**，Cochrane 计数跨技能一致），使「选题去重（meta-analysis）→ 全面检索（ct-literature）」
  形成无缝闭环。

### Verified
- meta-analysis 探针 live 测试：`ct_handoff` 命令串正确、Cochrane 查询与 ct-literature `--cochrane` 同源；
  ct-literature `--cochrane` 全链路 live 测试（NSCLC）合并 10 篇 → Cochrane 过滤后 5 篇，publication 全为
  Cochrane、`is_cochrane` 全 True；两技能 `py_compile` 通过。

## [2.1.2] — 2026-08-26 — 选题去重自包含（in-skill Europe PMC 探针）

### Added
- **`adapters/literature_probe.py`**：选题去重自包含探针（不依赖其他技能、不依赖 coze）。直接调
  Europe PMC 公开 REST（MEDLINE/PubMed，无需密钥），仅用标准库 `urllib/json/re/time/datetime`，
  字段映射与查询语法复用 ct-literature `adapters/fetch_europepmc.py`、重试/退避复刻其 `http_utils`
  （429 读 `Retry-After` + 指数退避），但**独立实现在本技能内、不 import ct-literature 包**。
  两层：`cochrane`（按 `JOURNAL:"The Cochrane database of systematic reviews"` 精准过滤，
  经验证避免短语匹配虚高）+ `pubmed`（`systematic review OR meta-analysis`，近 5 年）。
  返回真实 `hit_count` + top titles；`dedup_probe()` 一次性出 Cochrane+PubMed 双层去重信号。
- 选题（Stage 4 / R7）改为**默认真实联网、自包含**：不再默认只给模板、不再委派 ct-literature/ct-registry。
  PROSPERO 与中文库仍保留为「手动/模板」步骤（无干净公开 API，如实标注），符合「技能不假装包办一切」的边界。

### Changed
- `references/dedup-search.md`：网络说明从「从不自动检索、只给模板」翻转为「默认 in-skill 探针真实检索」；
  三层去重表重写（Layer1–2 = in-skill 实时，Layer3/中文 = 手动模板）；新增「Run the in-skill probe」段与真实输出示例。
- `references/topic-selection.md`：Stage 4 改写，明确去重自包含（Cochrane+PubMed 走探针），R7 的「真实去重筛查」落到探针。
- `SKILL.md` §2.2：选题去重标注 self-contained，移除「Dedup searches run ONLY on user opt-in; otherwise deliver query templates」。
- `adapters/README.md`：文件树补 `literature_probe.py` 并注明为选题去重自包含探针。

### Verified
- 真实联网端到端测试通过：选题「PD-1 inhibitors NSCLC second line」→ Cochrane `hit_count=36`
  （全部 `is_cochrane=True`）、PubMed SR/MA `hit_count=5358`；`py_compile` 通过。

## [2.1.1] — 2026-08-25 — 文档清理收尾 + 三平台统一发布

### Changed
- **版本号升 2.1.1**：SkillHub 已占用 2.1.0（早期发布），且 SkillHub 不允许同版本重发；为保持 GitHub / SkillHub / ClawHub 三平台版本一致，升到 2.1.1 统一发布。
- **对外文档清理收尾**（本轮发布前）：SKILL.md §5.1 跨轮连续性协议全文英文化并删除 `ct-base/references/*` 死链；`## Language` 段改为符合 ct-base skeleton 标准表述（双语指针单行 + 核心语义句 "answer language follows the user's question language"）；`references/interactive_menu.md` 与 `README_zh-CN.md` 清除同类死链。
- 版本号引用统一：SKILL frontmatter + metadata + README（中/英）+ interactive_menu/ADVANCED + bug-report 示例统一为 2.1.1。
- **文档与代码对齐（2026-08-26 收尾）**：默认计算路径统一描述为 coze（终端用户零本地依赖）；requirements.txt 改为「默认零依赖」清单（cairosvg 仅 PNG 可选，R 包降为 coze 端/开发者维护说明）；ADVANCED.md / ADVANCED_zh-CN.md / r_packages.md 的 coze 项目 R 引擎维护命令（`Rscript src/r_engine/*`）移至 `adapters/coze_project/DEV.md`（git/clawhub 忽略、不发布）；**取消本地 R 回退**——`run_analysis.py` 重写为 coze-only（coze 不可达/未授权直接返回结构化错误，不再兜底本地），原 `adapters/local_engine.py` 移至 `adapters/_dev/local_engine.py`（git/clawhub 双重忽略、不随发布包分发，仅开发调试参考，已不在运行路径）；同步更新 SKILL.md（network_note/data 改 coze-only 无回退）、AGENTS.md（Execution backend / 环境检测 / 代码执行 / 安全红线 / Outbound calls / 目录树 全部翻转）、adapters/README.md（路由图/文件清单/配置/用法清除回退）、data_templates.md（移除 `prefer="local"` 引导）；AGENTS.md / SKILL.md 版本号对齐 2.1.1。

## [2.1.0] — 2026-08-25 — 跨轮上下文交互能力完善 + 发布自包含修复（ct-base 模式 A / Type-Compute）

### Fixed / 发布自包含（P0-2）
- **`merge_spec.py` 注入发布包**：`ct-base/scripts/publish_inject.py` 的 `SHARED_ASSETS` 清单补 `scripts/merge_spec.py`，发布时注入 `meta-analysis/scripts/merge_spec.py`；SKILL.md §5.1 命令与描述改为相对路径 `scripts/merge_spec.py`（不再悬空引用 `ct-base/scripts/`，符合 AGENTS §5 发布后不假设 ct-base 存在）。
- **`ct-base/references/*` 悬空引用加注**（P1）：SKILL.md §5.1 声明"开发底座文档、发布包不含、关键规则已内联"，消除用户/审阅者困惑。
- **版本号统一**：SKILL frontmatter + metadata + README（中/英）+ interactive_menu/ADVANCED + bug-report 示例统一为 2.1.0。

### Added / 跨轮连续性协议（发布前完善，沿用 2.0.6 条目）
- **SKILL.md §5.1 升级为可操作协议**：定义跨轮 spec 字段集（task/data_path/measure/model/method/yi/sei/slab/byvar + params 透传）、回显块强制格式与位置、数据集指针继承、列映射显式继承（最高风险点：漏带 = 效应量错配 = 结论级静默不一致）、task 切换字段规则；`merge_spec.py` 从「可选」提为「推荐」并给调用范式。
- **interactive_menu.md 新增 §6 多轮连续性实战样板**：四轮 few-shot（forest→subgroup→sensitivity→metareg），每轮回显块演示「读最近块、只改变化字段、列映射零丢失」；含漏带 `yi=eff` 导致静默错配反例。
- **ct-base 回写（家族标准）**：`compute_menu.md` 补 §6.3（数据集指针继承）/ §6.4（列映射与 task 切换字段规则）；`continuity.md` §1.4 加交叉指针；`continuity_lint.py` 已验证 `meta-analysis` COMPLIANT。

### Added / 跨轮连续性协议（发布前完善）
- **SKILL.md §5.1 升级为可操作协议**：定义跨轮 spec 字段集（task/data_path/measure/model/method/yi/sei/slab/byvar + params 透传）、回显块强制格式与位置、数据集指针继承、列映射显式继承（最高风险点：漏带 = 效应量错配 = 结论级静默不一致）、task 切换字段规则；`merge_spec.py` 从「可选」提为「推荐」并给调用范式。
- **interactive_menu.md 新增 §6 多轮连续性实战样板**：四轮 few-shot（forest→subgroup→sensitivity→metareg），每轮回显块演示「读最近块、只改变化字段、列映射零丢失」；含漏带 `yi=eff` 导致静默错配反例。
- **ct-base 回写（家族标准）**：`compute_menu.md` 补 §6.3（数据集指针继承）/ §6.4（列映射与 task 切换字段规则）；`continuity.md` §1.4 加交叉指针；`continuity_lint.py` 已验证 `meta-analysis` COMPLIANT。

---

## [2.0.5] — 2026-08-24 — 发布前合规整改（ct-base §16 检查 + 文档对齐）

### Changed / 发布前整改（2026-08-24 逐项落实）
- **清理 i18n `install.*` 残留键组**：删除 `scripts/i18n.py` 中 6 个无引用的 `install.*` 键（`cmd_header` / `cran_warning` / `confirm_prompt` / `manual_alt` / `network_warning_en` / `code_header`）——它们引用已不存在的 `--run-install` 本地 R 安装参数（coze-only 形态已移除），且 `install.cran_warning` 文案"（即本技能唯一会联网的操作）"与当前默认走 coze 云端的架构严重矛盾。删除后语法校验通过（§16.8 legacy 死参数清理）。
- **版本 bump**：2.0.0 → **2.0.5**（SKILL.md frontmatter + metadata 同步），CHANGELOG 补本条目（此前正文已提"修复见 2.0.1"的 dose_resp 修复，本次统一为 2.0.5 发布）。
- **SKILL.md 文档重构（§13.3/§4 对齐）**：9 段式框架（Triage→引导→初始化→核心→输出→安全→上传→Bug→元信息）；`## Language` 精简为链接；`## Bug Reporting` 只留行为规则；正文英文化（保留运行时用户双语文案 + 触发词）。
- **README 结构重排（§13.3）**：对话示例前置、出站披露收敛为「数据与隐私」节；实测记录迁至 ADVANCED。
- **ct-base 注解清理**：对外文档（README/SKILL/AGENTS/interactive_menu）清除 `（ct-base §X）` 引用；内部技术文档（ADVANCED/units 等）保留溯源（§4 文档清理边界）。
- **安全审计披露矛盾修复（SkillSpector §16.0）**：修正 `data:` 字段"no external data transmission"、README"never touches raw datasets"、bug-report"本地保存+邮件作者"等声明与实际不符处。
- **执行模式变更（安全预览 → 自动执行，2026-08-24）**：技能从「默认展示 R 代码、需说『请直接计算』才执行」改为**自动执行**——用户描述需求后技能自动完成分析并返回结果，无需触发词。同步更新 README（中/英）顶部简介、示例注记、FAQ、原「安全预览」节（改为「执行机制」）、出站披露触发时机（改为自动发送 + 每会话首次出站前披露一次）；AGENTS.md 执行规范（AUTO-EXECUTE）；interactive_menu.md 对应节。出站授权红线不变（默认端点白名单自动执行、自定义端点首次弹确认）。
- **本地引擎改为内部备用（2026-08-24）**：本地 R 兜底引擎（`adapters/local_engine.py` + `adapters/coze_project/src/r_engine/` 镜像）**代码保留**，但**不再对外文档说明**——README（中/英）、SKILL.md、interactive_menu.md 移除全部"本地引擎 / 本地兜底 / `prefer="local"` / 数据不出域可走本地"的用户导向表述，统一呈现为纯 coze 云端执行；AGENTS.md 标注 "internal only, not advertised"。本地兜底仅作 coze 不可用时的内部备用（不向用户宣传）。

---

## [2.0.0] — 2026-08-22 — 升级为云端模式 + 补齐 bug report 接入

### Added / 云端模式全面测试（ct-update 模式 B，按功能点 2 案例扩展）
- **模式 B 联调（ct-meta.coze.site/run 线上端点）**：按"每个功能点覆盖、每 task 至少 1 标准 + 1 变体"原则，将 `adapters/coze_cases/` 从 10 例扩展至 **46 个案例**，覆盖 contract §3 全部 **24 个 task 类型**（pairwise_meta / single_group_meta / subgroup_analysis / metareg / forest_plot / funnel_plot / labbe_plot / baujat_plot / radial_plot / bubble_plot / influence / trimfill / nma / nma_rank / survival_meta / dose_resp / diagnostic_meta / bayesian_pairwise / gosh / tsa / power / rob2 / esc / prisma_flow / prisma_checklist / grade / metainc / nnt / leave_one_out / cumulative_meta / selmodel / rve_meta / multilevel_meta / multivariate_meta）+ 维度变体（locale 中英 / colmap 自定义 / 多图组合）。
- **结果**：**44/46 通过**（含 2 个预期 `warn`：Egger 检验偏倚提示，属 Quality Gate 正常非阻断输出）；**2 个失败 = dose_resp（case19 continuous / case45 binary），属 R 端 `run_dose_resp` dosresmeta NSE 集成缺陷，待修复 R 端代码**（见 Pending）。其余 44 例功能完整。

### Fixed / bug report 接入缺漏（ct-base §20.3.5）
- **问题**：`adapters/config.json` 的 `auto_approve_endpoints` 仅含 `https://ct-meta.coze.site/run`，**缺少**统一 bug-report 端点 `https://ct-bugreport.coze.site/run`，违反 §20.3.5（每个技能须将该端点列入自动批准白名单）。
- **修复**：`auto_approve_endpoints` 追加 `https://ct-bugreport.coze.site/run`。
- **已合规项确认**：`adapters/bug_report.py` 已含 §20.3.7 的 `confirm_thanks()` / `build_followup()` / `parse_history()`；SKILL.md §20.3 章节与 README §5/§20.3 出站披露均已就位。

### Pending / 待确认（非阻断，记入发布报告）
- **clawhub_security_audit MEDIUM**：SKILL.md 第 91 行 + `scripts/i18n.py` 读取 `~/.workbuddy/MEMORY.md` 用于 R config（用户已授权、仅取 R 相关键、不发送个人内容）。审计认为超出技能窄范围，建议移除或收窄。属预存在设计，改动可能影响 R 配置功能，标记待用户确认，未擅改。
- **dose_resp R 端缺陷（模式 B 抓出，2026-08-23，**已修复见 2.0.1**）**：`adapters/coze_project/src/r_engine/advanced_functions.R` 的 `run_dose_resp` 用 dosresmeta 公式法 `(cases/n) ~ dose`（LHS 表达式），触发 2.2.0 内部 bug（`unique() applies only to vectors` / `'x' must have positive length`；as.name/字符串列名均不行）。case19（continuous）与 case45（binary）失败。**非测试设计错误，是技能 R 端代码缺陷**，修复见 2.0.1（v4：预计算效应量列 + 裸列名 + 参考组 se=NA + type factor，R 4.6.1 实测通过）。

---

## [2.0.1] — 2026-08-23 — dose_resp 崩溃修复（v4：dosresmeta 官方写法，R 4.6.1 实测验证）

### Fixed / coze 端 dose_resp「死机」——R 进程 segfault（根因链完整闭环）
- **第一层根因（文件版本错位）**：`run_task.R` dose_resp 分支已改**字符串列名**，但 `advanced_functions.R` 的 `run_dose_resp` 内部仍用 **`as.name()`** 转符号 → dosresmeta 内部崩溃。本机实测 as.name 版 exit=139 Segfault（进程崩溃 → Python 侧等不到 result → coze 画布卡死）。
- **第二层根因（dosresmeta 2.2.0 正确用法，R 4.6.1 实测推翻 v2 字符串方案）**：字符串列名也会崩（`non-numeric argument to binary operator`，因 dosresmeta 对独立参数 `eval(mf.id, data)` 会把字符串当字面量）。**正确写法**：
  1. formula LHS 用**预计算效应量列**（binary: `logrr=log(cases/n)`；continuous: `yi`），不能用 `(cases/n) ~ dose` 表达式（触发 `unique() applies only to vectors` / `'x' must have positive length`）；
  2. 独立参数 id/cases/n/sd/se 传**裸列名**（写入 df 后传 `_id_f`/`_cases`/`_n`/`_se_use` 等短名列），不传字符串也不传 as.name；
  3. binary 参考剂量组（dose 最小）**se 置 NA**（Greenland-Longnecker 约定），type 转 factor；
  4. covariance: binary=`"gl"`（需 cases/n），continuous=`"md"`（需 sd/n）。
- **修复**：`run_dose_resp` 重写为 v4（预处理 df → 短名列 → 官方调用）；`run_task.R` dose_resp 分支 plot 条件对齐（plots 空也默认出图）。
- **验证（R 4.6.1 + 干净 PATH，完整复现 coze 环境）**：case45 binary `status=ok figures=1`（coef=-0.0191, p<0.0001, SVG 8535 字符）；case19 continuous `status=ok figures=1`（coef=0.0145, p<0.0001）；pairwise_meta 回归 k=5 I2=0% OR=1.221 无破坏。
- **case 数据修正**：case19/45 原"每剂量点一个研究"（S1-S5）是错误结构，dosresmeta 需**单研究×多剂量点**——已统一 id 为 S1。
- **交付**：`meta-analysis-coze-full-v4.zip`（完整工程 113 文件 + 修正 case19/45）。

---

## [1.12.2] — 2026-08-20

### Fixed / 部署环境候选列表过时（libicu76）

- **问题（2026-08-20 部署日志暴露）**：`scripts/setup.sh` 的 libicu 多候选列表为 `libicu74|libicu72|libicu71|libicu70`（注释误标"Debian13=libicu74"），但实际 **Debian 13 (trixie) 为 libicu76** → 4 次尝试全失败（`E: Unable to locate package libicu74/72/71/70`），依赖符号链接兜底（`.76 → .74`）才通过——能工作但属 ABI hack。
- **修复**：候选列表 `libicu76` 前置（trixie 直接命中，跳过无谓失败 + 免符号链接）；`libgsl28` 前置（trixie 为 28，避免先试 27 失败噪音）；注释同步修正。
- **验证**：`bash -n` 语法 OK；线上 v1.12.1 当前运行正常（兜底生效、回归 6/6），本修复随下次部署生效，无需重启线上。

### Added / README 对话示例实测（ct-base §16.6 实测闸门留痕）+ 新增「选择候选方向」示例

- **实测（2026-08-20，coze 端点 `https://ct-meta.coze.site/run`）**：按 §16.6 逐个实测两份 README 的对话示例，**7/7 通过**——计算类示例 1（OR 配对）/2（d→logOR=1.451）/3（SMD+亚组）/6（PRISMA 流程图，`prisma_flow` task 实测可用）均返回真实 `stats`+`figures`+`repro`；行为类示例 4（Complex 路由菜单）/5（Vague grill-me）与 SKILL.md Triage 一致。完整报告：`meta_readme_test/README_EXAMPLES_TEST_REPORT.md`。
- **新增示例 7（中英 README + interactive_menu.md）**：「选择候选 Meta 分析方向」——应用 `references/topic-selection.md` Stage 1 Gate 1 产出 1–3 候选方向 + 四维评分 + Meta 类型决策树，属分析前上游门控、不调用 R 计算。
- **修复（§5 / §16.6 文档-行为一致性）**：README「安全预览」§4 原「所有计算均在本地——不上传任何用户数据」为 coze-only 形态前的旧文案，与默认云端 R 引擎 + 数据出站矛盾——已改为「默认云端 coze R 引擎 + 按 §5 出站披露；本地/离线走 `prefer="local"`」；`interactive_menu.md` 开头与 §4 同步修正。
- **标记待确认（未擅改）**：README 尾部版本号 v1.9.7 滞后于 SKILL.md/CHANGELOG v1.12.2（§16.5 一致性），版本号统一属发布决策，等用户确认后统一。
- **契约枚举补充（2026-08-20）**：coze_contract.md §3 补 `prisma_flow`（四阶段流程图，params: records/duplicates/screened/excluded_title/assessed/excluded_elig/included/reports）与 `prisma_checklist`（27 项检查表，params: `done`=已完成项 id 列表）两行——实现早已存在，契约枚举滞后，现已同步。
- **更正（2026-08-20，用户确认）**：本机有 R 4.5.1（`C:/Tools/R-4.5.1/bin/Rscript.exe`，仅开发双轨使用、不在 PATH），**发布形态为 coze-only**（本地 R 只用于开发）——早前实测记录"无本地 R"为 PATH 探测误判，已更正。

### Changed / 发布前合规审计（ct-base §5 / §13 / §16，2026-08-21）

基于 `ct-base` 治理规范对 `meta-analysis` 作发布前检查与修正（coze-only 发布形态，归 ct 花名册 A 档）：

- **版本对齐（§16.5/§16.6）**：`AGENTS.md` / `README.md` / `README_zh-CN.md` / `SKILL.md` frontmatter（`metadata.version` + `version`）统一为 `1.12.2`；此前 README 尾部 v1.9.7 滞后已修正。
- **SAFE PREVIEW 双语义（§4 / Example 1 / FAQ）**：纠正 coze-only 形态前的旧表述"生成并展示 R 代码、不执行 / 说 `--yes` 才运行"——改为"生成并展示**分析请求信封**（task/data/params/figure），由自然语言触发发送（"请直接计算"）；**无 `--yes` 参数**（coze 为无状态远程引擎，发送动作由纯语言指令驱动）。两份 README 同步。
- **出站元数据披露（§5）**：两份 README 出站披露块补充 `query_origin`（主机名 SHA-256 哈希，仅服务端归因/限流，非明文主机名）+ `locale`（OS 语言，双语用）说明。
- **§13.1 保密声明块补回**：A/B 两档 CT 全系列保密声明 + 固定联系方式 `medstatstar@gmail.com` 加入两份 README 末尾（1.8.0 曾以"非 ct 技能"误删，现归 ct 花名册 A 档须含）。
- **§13.6 适用人群块**：两份 README 插入 `## Who This Is For`（药企临床试验从业者 / 医护 / 医学生）。
- **§13.10 保密数据 FAQ 块**：两份 README 插入"数据要保密怎么办"——只发汇总统计量；不出域走本地引擎 `prefer="local"`；可获可复现 R 代码。
- **§8.6 query_origin 客户端实现**：`adapters/run_analysis.py` 默认 coze 分支客户端计算 `sha256(hostname)`（71 字符 `"sha256:"`+64hex）随请求发送，coze 端不兜底生成（客户端唯一真相源）；`coze_client.run_meta(..., query_origin=...)` 签名已支持。
- **§16.1 SKILL.md 瘦身（≤200 行）**：24 行 Core Functions 表外迁 `references/advanced_api.md`（长参考外迁 remedy）+ Interactive Guide / 渲染计时冗余压缩 → **216 → 187 行**。
- **§16.8 干净包清理**：取消跟踪废弃 R 脚本（`scripts/r_*.py` + `scripts/check_integrity.sh`，为 `adapters/coze_project` 镜像的重复件）、`tests/*`（保留物理、gitignored）、`assets/icon.png`（SkillHub 窄白名单拒绝 .png、且非 live 图标）；物理删除调试产物 `Rplots.pdf`。`.gitignore` / `.clawhubignore` 补充发布排除项。
- **network 一致性（§16.6）**：frontmatter `network: optional` + 已修正 `network_note`（"有本地兜底（需本机 R）时才 optional；多数终端用户走 coze"）属可接受表述，与 README 出站披露一致。

### Changed / 发布前合规审计第二轮（bugreport 合规 + §16.9 收口 + §3 统一，2026-08-22）

因 bugreport 功能上线（ct-base §20.3），重新以 ct-base 治理规范复检并修正：

- **§20.3 bug_report.py 同步最新模板**：补齐 `confirm_thanks()` / `parse_history()` / `build_followup()` 历史回执三件套及对应 `_MSGS`（thank/done/pending 中英），`send_to_endpoint()` 现回传 `history`（与统一端点历史回执协议对齐）；保留叶子技能内嵌公共 token（`get_endpoint_token()`，§5 XOR+base64 混淆，用户授权发布）。
- **§20.3.1 触发词**：SKILL.md frontmatter `triggers` 补 `上报bug` / `report a bug` / `错误报告`；Bug Reporting 章节补「发送后历史回执」说明（`confirm_thanks()` + `build_followup(parse_history(resp["history"]))`）。
- **§5 / §13 出站披露补全**：两份 README 出站披露块新增「错误报告端点披露」——说明 bug 报告仅发 11 键脱敏信封至 `https://ct-bugreport.coze.site/run`、不含分析数据/PII、附 `query_origin`+`locale`、拒绝则不出站、无云端调用则本地保存。
- **§16.9 出站收口**：`scripts/pdf_fetch.py`（Unpaywall API 外站检索）迁出"纯本地"的 `scripts/` → 归入出站专用目录 `adapters/pdf_fetch.py`；同步更新 `SKILL.md:123` 与 `references/review_workflow.md:110` 路径引用（CHANGELOG 历史条目保留原路径）。
- **§3 frontmatter 统一**：`description` 中文部分补齐与 `summary` 一致的「中英双语自动切换（默认英文/中文环境切中文）」一句，英文部分同步补 `Auto-switches language (defaults to English, switches to Chinese in zh-* environments)`；双语文档一致性保持。
- **§16.1 SKILL.md ≤200 行**：新增触发词 +3 行 + 历史回执说明，复验仍 **≤200 行**（通过）。
- **§16.8 干净包复验**：`git archive HEAD` 重建包无 `.png/.R/.pdf/.pyc/.dat` 泄漏；`adapters/bug_report.py` / `adapters/coze_token.py` / `adapters/config.json` / `adapters/pdf_fetch.py` 均含于包内。
- **§20.3.5 端点设计文档补齐**：新增 `references/bug_report_endpoint.md`（统一报告端点协议——信封/11 键白名单/服务端分派流程/响应信封/治理与合规），示例 skill 改写 `meta-analysis`；SKILL.md Bug Reporting 章节加指针。此前审计标记缺失，本轮补建入包。

## [1.12.1] — 2026-08-20

### Fixed / UTF-8 环境防御（jsonlite toJSON 中文损坏）

- **问题（实测复现）**：Windows `LC_CTYPE=C` 时 `jsonlite::toJSON` 把 UTF-8 中文按 Latin-1 转码——"检验"→`f#`（字节 `66 23`）、产生 `\u0010e` 控制字符、NUL 截断；**R 内存中叙述正常、写出 JSON 乱码，会骗过本地验证**（coze Linux 服务器不受影响，故部署端正常而本地误判/漏判）。
- **修复（`run_task.R` 顶部）**：`try(Sys.setlocale("LC_CTYPE", "en_US.UTF-8"))` + `try(Sys.setlocale("LC_ALL", "en_US.UTF-8"))`（`en_US.UTF-8` 在 Windows R 4.2+ 自动映射为系统 UTF-8 locale，实测有效）；引擎文件 `source(..., encoding = "UTF-8")` 显式指定编码。
- **验证**：模拟 `LC_CTYPE=C` 启动 → 修复代码生效后 toJSON 中文完整（"成功合并 5 项研究（随机效应 OR）。"、"检验"无损）；真实引擎 locale=zh 输出中文 JSON 正常（无 NUL/损坏）；回归 12/12 通过。

## [1.12.0] — 2026-08-20

### Changed / 方案 C 落地：R 出双语模板 + LLM 润色 + SVG 恒英文 + 本地渲染中文

**最终方案（用户决策 2026-08-20）**：coze 端 R 引擎按请求 `locale` 参数直出双语模板（数值 + 标准 label 精确），本地 LLM 收到后只做两件事——组织通顺的用户语言 + 按需补充解释；SVG 一律英文；中文（如项目名/研究名）由本地渲染层替换字体。

| 改动 | 说明 |
|---|---|
| **locale 参数驱动双语**（`run_task.R` 入口） | `params$locale`（支持 zh/zh-CN/cn/en/en-US，缺省 en）→ `.MA_LANG` 全局切换；**不读环境变量**（coze 容器语言 ≠ 用户语言）。语言决策权在本地 LLM |
| **`.msg` 双语模板恢复** | 面向用户的叙述（notes/warns/stop/PRISMA 27 项/GRADE 理由/quality gate 检查）按 locale 出中/英双语；164 处中文硬编码叙述包入 `.msg("en","zh")` |
| **`.msg_plot`（SVG 恒英文）** | 图内文字（图标题/轴标签/图例/"Pooled"/Study 标签/PRISMA flow label 等 42 处）一律恒英文，不受 locale 影响——规避 cairosvg/字体回退的中文渲染依赖 |
| **统一语言机制** | 删除 4 个引擎文件中的 10 处 local `.MA_LANG`/`.msg` 定义（环境变量检测旧机制），统一走 global locale 驱动版 |
| **本地渲染中文**（`adapters/rendering.py`，v1.11.2 已落） | `_fix_cjk_fonts`：SVG→PNG 时把含中文的 `<text>` 字体族替换为中文字体族（Win: Microsoft YaHei / macOS: PingFang SC / Linux: Noto Sans CJK SC / `RENDERING_CJK_FONT` 可覆盖），英文图零变化 |

**验证**：locale=zh → 顶层 notes="成功合并 5 项研究（随机效应 OR）。"、quality gate msg="k=5 通过"/"建议补充剪补法（k>=5）"、SVG 无中文字符（恒英文）；locale=en → 全英文；最终回归 21/21 通过。

> ⚠️ 实现注记：本轮曾尝试"coze 端语言中性（zh2en 214 处转英文）"（方案 A 实验），因用户最终选定方案 C 且 zh2en 批量脚本存在实现缺陷（误替换 .msg 参数/引号转义），已从 v1.11.1 上传包解出干净基线重建——引擎现为"v1.11.1 全部修复 + 方案 C 双语"。

---

## [1.11.2] — 2026-08-20

### Changed / 语言与中文渲染（coze 端语言中性 + 本地渲染中文支持）

**原则（用户决策 2026-08-20）**：coze 端只负责计算、不做语言输出决策；语言转换与呈现由本地大模型完成；SVG 图内文字中文支持由本地渲染层处理。

| 改动 | 说明 |
|---|---|
| R 引擎语言中性 | `.MA_LANG` 恒 `"en"`（不再读 LANG/LC_ALL 环境变量），`.msg(en, zh)` 恒返回 en；zh 参数保留作注释参考。coze 输出稳定英文结构化结果，不受容器语言影响 |
| R 引擎 214 处中文→英文 | 引号内硬编码中文（notes/warns/stop/PRISMA 27 项/GRADE 条目/图标签/可复现脚本模板）全部替换为英文；仅行内代码注释保留中文（不影响输出）。回归 19/19 通过 |
| **本地渲染中文支持**（`adapters/rendering.py`） | 新增 `_fix_cjk_fonts()`：SVG→PNG 路径把**含中文的 `<text>`** 字体族替换为中文字体族（Windows: Microsoft YaHei / macOS: PingFang SC / Linux: Noto Sans CJK SC；可用 `RENDERING_CJK_FONT` 覆盖）；纯英文/数字 text 不动 → 英文图像素零变化 |
| 中文字体实测 | coze SVG（font-family 恒 DejaVu Sans）经 cairosvg 渲染中文 study 标签为空白；`_fix_cjk_fonts` 后中文正常（像素验证：study 区深色 0.03→0.05~0.07）；英文 SVG 经 `_fix_cjk_fonts` 返回原字符串（零变化） |

**实测证据（2026-08-20）**：coze 端 svglite 输出中文数据完整（`<text>` 含"研究一"~"研究五"），但 font-family 恒 `"DejaVu Sans"` 无中文字体回退 → cairosvg 渲染空白。替换字体族后同图中文立即正常。浏览器内联渲染依赖系统字体回退，通常正常；PNG 转换场景由 `_fix_cjk_fonts` 兜底。

---

## [1.11.1] — 2026-08-20

### Removed / 清理（ct-base §5 凭据规范对齐）

- **删除历史遗留 `config/coze.dat`**：该文件是早期「落盘混淆」方案残留。凭据已内嵌 `adapters/coze_token.py` 的 `EMBEDDED_SECRETS`（§5 第 63 行规范：公开凭据须内嵌 `.py`，任何平台不丢）；`.dat` 不在 SkillHub 窄白名单（仅 `.svg/.py/.md/.json/.yaml/.txt/.toml/.csv`），发布时被服务端**静默剥离** → 属「无法发布」的遗留文件，且代码不依赖（`coze_token.py` 内嵌链 `CLI > env > 文件 > 内嵌`，删除后自动回退内嵌）。
- **`.gitignore` / `.clawhubignore` 新增 `config/coze.dat` 兜底排除**：防止未来 `store_token()` 本地覆盖再生成后误打包；`config/` 目录现为空。
- 验证：删除后 `get_token()` 内嵌解析 OK（非空）、coze 端点 health=True，功能零影响。

---

## [1.11.0] — 2026-08-20

### Added / 实现（终审清单剩余 10 项全部清零；用户决策「全部修正实现」）

| 项 | 实现 | 验证 |
|---|---|---|
| **A1** F→d | `.esc_convert` 加 `f→d`（F=t² → d=√F·√((n1+n2)/(n1·n2))） | F=6.25/n=30 → d=0.6455 ✅ |
| **A2** NNT | 新 task `nnt`：二分类 → metabin RD 合并 → NNT=1/\|RD\| + 95%CI | NNT=14.1，CI [8.4, 43.7] ✅ |
| **A3** metacor | `single_group_meta` 加 `r/n` 形态 → meta::metacor（单组相关系数） | k=6，ZCOR=0.523 ✅ |
| **A4** quality filter | `leave_one_out` 接线 quality 列：numeric ≥阈值（默认 6）/ "low risk" 筛选重合并 → extra.high_quality | k=4，est=0.263 ✅ |
| **A5** subgroup power | `power` 加 `subgroup_effects/subgroup_k` → 各亚组功效近似 | effect 0.3/k5→0.918、0.5/k8→1.0 ✅ |
| **A6** HK 修正 | `.meta_method` 加 hakn（model ∈ hk/hakn/knha）→ metabin/metacont/metagen 传 hakn；metafor 路径加 `.rma_test`（knha） | model=HK 正常拟合 ✅ |
| **A7** 95% PI | `.extract_meta`（fit$lower/upper.predict）与 `.extract_rma`（predict() pi.lb/pi.ub）加 pooled_pi | PI [0.147, 0.423]（exp [1.158, 1.527]）✅ |
| **A9** JC prior | `run_bayes_pairwise` tau_prior 加 `jeffreys/jc`（Half-Cauchy 近似，bayesmeta 无内置槽位） | post_mean=0.2866 ✅ |
| **A10** 结构矩阵 | `multivariate_meta` 加 `structure` 参数（UN/CS/HCS/AR1/ID/DIAG → rma.mv struct） | UN 拟合 ✅ |
| **A11** 真多结局 | `multivariate_meta` 检测 outcome 列 → rma.mv(mods=~outcome−1, random=~outcome|study, struct) → by_outcome + rho | OS 0.333 / PFS 0.434，rho=0.843 ✅ |

### Regression / 回归

- 最终重跑 20 个代表用例（覆盖二分类/连续/预计算/别名/亚组/元回归/NMA/贝叶斯/TSA/功效/RoB/可视化）**20/20 通过**，零破坏。
- 引擎 task 达 **40 个**（38 + nnt + multivariate 语义升级）。

### Notes / 说明

- 终审清单（meta_doc_impl_audit.md）**全部清零**：A1–A11 已实现；B1/B2 已实现；A8 中 Digitize 按用户决策不做；B3 环境限制维持。
- 待部署（发布动作须确认）：`run_task.R`/`advanced_functions.R` 本地镜像全部改动。

## [1.10.3] — 2026-08-20

### Added / 实现（终审清单 B1/B2/A8；用户决策：Digitize 不做，IPD 走 coze）

**B1 · 效应量 + CI 输入形态（零依赖）**
- 引擎数据形态新增 `has_ci`：接受 `te + ci_low + ci_high` 列，`seTE=(ci_high−ci_low)/(2·Φ⁻¹(0.975))` 换算后走 metagen（与 te 同尺度，log 尺度给 log CI）。验证：te+CI → OR=1.405（与直接给 seTE 一致）。

**B2 · IPD Meta 真实实现（走 coze；用户原则：技能只实现功能+披露，安全决策归用户）**
- `ipd_meta` 由"安全边界提示"改为真实分析：个体行（`study/trt/event`）→ 按 study×arm 聚合 2×2 → `metafor::rma.glmm(measure="OR")` 一阶段 GLMM（核心包零新增依赖）。验证：4 研究 / 1560 个体 → OR=2.175 [1.758, 2.690] + 森林图。
- SKILL.md Security & Scope / §6.7.3 同步：删除"不传输 IPD"绝对化表述，改为「数据出域决策归用户；技能负责实现 + 透明披露；coze 可满足安全合规；用户要求不出域时提供本地路径」。

**A8 · PDF 批量下载 + Screening（Digitize 按用户决策不做）**
- 新增 `scripts/pdf_fetch.py`（stdlib-only，opt-in）：DOI → Unpaywall 开放获取全文、PMID → NCBI elink → PMC 全文；逐条独立容错、无 OA 如实报告、不绕过付费墙。验证：CLI/错误处理/假 DOI 容错通过。
- `references/review_workflow.md` 新增「AI 辅助文献筛选（Screening）」agent 行为层流程（纳入/排除判定表 + 一致性规则）。

**原则写入 ct-base（用户决策）**：`ct-base/docs/02-governance-redlines.md` §6.7.4「功能实现 vs 安全决策分离」（§5 级全库原则）——技能只实现功能 + 透明披露，不因数据敏感预设"不提供"红线；是否出域由用户决策；出站披露/确认/PII 脱敏照常；用户要求不出域时提供本地路径。

### Regression / 回归

- B1/B2 改动后重跑 18 个代表用例 **18/18 通过**（含别名 colmap、te+CI、IPD）。

### Notes / 说明

- 待部署（发布动作须确认）：`run_task.R`（has_ci + ipd_meta 真实现）+ `scripts/pdf_fetch.py` + 文档（SKILL.md/review_workflow.md/coze_contract）+ ct-base §6.7.4。
- 终审清单剩余未做：A3 metacor / A5 subgroup power / A6 HK / A7 95%PI / A9 JC prior / A10 rma.mv 结构 / A11 真多结局（另行评估）；A8 中 Digitize 明确不做；B3 环境限制维持。

## [1.10.2] — 2026-08-20

### Changed / 收紧（出图格式约定：coze 恒 SVG，PNG 本地转换）

**用户确认的设计**：图形处理时 coze 默认只发送 SVG；需要 PNG 时由本地处理。

**改动**：
- `adapters/coze_client.py` `run_meta`：payload 强制 `figure.format="svg"`（覆写任何 png 请求）——coze 端**恒返回 SVG，零 png 路径**（不再可能回 png_base64）。
- `adapters/local_engine.py` `run_meta`：同样强制 `figure.format="svg"`（一致性）。
- `SKILL.md` Output 新增「出图格式约定」说明；coze_contract.md §5 png 选项注明"适配层强制 svg"。

**验证**：
- 请求 `figure.format="png"` → coze 返回 `figures[].format=['svg','svg']`，无 png_base64 ✅
- 本地 PNG 链 `render_figures(mode="png_file")`（cairosvg 2.9.0）：forest.png 78KB / funnel.png 38KB，0.43s ✅
- 说明：PNG 转换依赖本地 cairosvg（`pip install cairosvg`）；未装时 `rendering.svg_to_png` 给出明确安装提示（原行为保留）。

### Notes / 说明

- 待部署（发布动作须确认）：改动在 `adapters/{coze_client,local_engine}.py` + 文档。

## [1.10.1] — 2026-08-20

### Fixed / 修复（W1：Quality Gate 引擎侧接线，走查发现）

**缺陷**：`run_quality_gate` 在 dispatch **零调用**——SKILL.md 声称"coze 侧 R 运行 run_quality_gate → gate JSON → 红灯阻断"，但分析响应不产出 gate JSON，红灯判定完全依赖 agent 呈现层手动执行（流程走查 W1，P3）。

**修复**（`run_task.R`）：
- 合并类分支（`pairwise_meta`/`funnel_plot`/`trimfill`/`subgroup_analysis`/`metareg` + `survival_meta`）在 stats 产出后调用 `run_quality_gate(es_data, fit, bias_gate)`，结果写入 `stats$quality_gate`（含 `gate_json` 字符串，可直接喂 `scripts/quality_gate.py [--yes]` 人工签字门）。
- 偏倚核查扩展：`metareg`（rma 对象兼容，`fit$yi/fit$se` 兜底）与 `survival_meta` 补 Egger/Begg（此前无 `stats$bias`，会让 Quality Gate 误判红灯"偏倚清单缺失"）。
- bias 映射：`stats$bias`（egger_p/begg_p）→ `bias_gate`（egger/begg 键，匹配 `run_quality_gate` 期望结构）；`trimfill` 任务附加 trimfill 键。
- `capture.output` 包裹调用以吞掉 `run_quality_gate` 的 `cat(gate_json)` 日志噪音。

**验证**（本地 R 4.5.1）：
- 三态正确：k=2 → **red**（pooled_presentable=false，k 检查红灯）；k=5（有偏倚核查）→ **yellow**（证据体较小）；k=6 survival → yellow（建议 trimfill）；fd09_a trimfill（含 trimfill 键）→ **green**。
- **闭环**：引擎产出 `gate_json` → `quality_gate.py`：red 无 `--yes` exit=2（阻断）、`--yes` exit=0（放行）。
- 回归：合并类 4 例带 gate 正常；非合并类（nma/bayesian/tsa/rob2/图）正确无 gate；状态均 ok/warn。

### Notes / 说明

- 待部署（发布动作须确认）：改动在本地镜像 `run_task.R`；部署后线上合并类响应将含 `stats.quality_gate`。
- 4 类非计算流程域走查完成：Triage / Topic Selection / 上传文件全绿，Quality Gate 本次修复后闭环。

## [1.10.0] — 2026-08-20

### Added / 新增（补齐 13 项文档-实现缺口，本地引擎验证通过）

> 背景：ct-update §18 测试盘点确认「文档声明但引擎无 task」13 项（此前均返回 `unknown_task`），本次全部补实现；用户决策「文档不降级，补齐实现」。

| 新 task | 实现 | 本地验证 |
|---|---|---|
| `leave_one_out` | metafor::leave1out（逐项剔除敏感性） | ok（k=8，含逐项 estimate/CI/I²） |
| `cumulative_meta` | metafor::cumul（累积 Meta） | ok（k=8） |
| `selmodel` | metafor::selmodel（选择模型，发表偏倚校正） | ok（estimate + LRT_p，多版本槽位 tryCatch） |
| `bootmeta` | 手写非参数 Bootstrap（B 次重采样，REML） | ok（boot_mean/sd/CI） |
| `drapery` | 复用 plot_drapery（α 稳健性图） | ok（drapery 图） |
| `rve_meta` | robumeta::robu + clubSandwich::vcovCR(CR2)（RVE 稳健方差） | ok（CI 经 reg_table 提取，含 dfs） |
| `multilevel_meta` / `multivariate_meta` | metafor::rma.mv（研究随机截距，UN 结构） | ok（k=8，n_study=4） |
| `metainc` | 双形态：两组 `meta::metainc`(IRR) / 单组 `meta::metarate`(IR) | ok（IR=0.118） |
| `grade` | 自实现简化 GRADE（5 降级 + 3 升级因素） | ok（RCT+偏倚+I²80%+事件200+偏倚可能 → Moderate） |
| `prisma_checklist` | PRISMA 2020 检查表（27 项，可传已完成项） | ok（27 项，done 可标记） |
| `prisma_flow` | PRISMA 2020 四阶段流程图（ggplot 自绘） | ok（prisma_flow 图） |
| `ipd_meta` | 安全模型边界提示（coze 形态不收 IPD，明确引导本地引擎/汇总效应量） | warn（预期，含出域提示） |

### Fixed / 修复（4 项 P2 偏差）

| P2 | 问题 | 修复 | 验证 |
|---|---|---|---|
| esc 扩展 | 仅 6 种转换；d→logOR/mean→d/t→d 返回空 | 补 `mean→d`（合并 SD）、`t→d`、`d↔logOR`（d·π/√3）、`r↔d` 公式 | d→logOR=1.451、mean→d=0.500、t→d=0.635 ✅ |
| nma_rank rank | `rk$rank` 恒 NULL（netmeta 3.6.1 无此槽位） | 改用 `ranking.random` + `Pscore.random` | rank/pscore 均返回（A/B/C P-score 0.098/0.652/0.750）✅ |
| rob2 tool | tool 参数未使用，三工具渲染相同 | 域标签按工具映射（ROB2 5 域/ROB1 6 域/ROBINS-I 7 域）+ 标题带工具名 | ROB2/ROB1/ROBINS-I 均 ok，标签差异化 ✅ |
| Forest 主题 | `figure$theme` 0 引用，5 主题纯文档承诺 | 新增 `.theme_map` + `.forest_plot_theme`（revman/default/lancet/nejm/classic 配色映射到 meta::forest col.*） | theme=lancet 正常出图 ✅ |

### Regression / 回归

- 修复后本地引擎重跑 **28 个代表性用例（含全部 P0/P1 修复项）28/28 通过**，零破坏。
- 13 新 task + 4 P2 修复全部本地 CLI 验证（R 4.5.1；robumeta 装临时库，coze 镜像已含）。

### Notes / 说明

- **待部署**：全部改动在本地镜像 `adapters/coze_project/src/r_engine/{run_task,advanced_functions}.R`；部署属发布动作，须显式确认（重打包 → 部署 → §18.6 线上回归）。
- 引擎 task 由 25 → **38 个**；文档-实现缺口 13 项清零；P2 偏差 4 项清零。
- 剩余未覆盖：Topic Selection / Quality Gate / 上传文件 / Triage 四类非计算流程域（另行走查）。

## [1.9.9] — 2026-08-20

### Fixed / 修复（ct-update §18 全功能 NL 测试发现，83 例；本地引擎验证通过，待部署）

| 缺陷 | 根因 | 修复 | 验证 |
|---|---|---|---|
| **P0-1** NMA 二分类 arm-based 全挂（`object 'TE' not found`） | `.nma_prep` arm-based 二分类分支返回 `event1/n1` 形式，dispatch 却用 netmeta `TE/seTE` 对比接口 | arm-based 二分类分支改 **Haldane 校正自算 logOR/SE**（与对比输入分支一致） | fd11_a/c 本地 ok（k=4/6，n_treat=3） |
| **P0-2** NMA 别名列名必挂（`Treatments must be different`） | `.nma_prep` 仅解析 `cm$treatment`，study/event/n 未按 colmap 解析（study 退化为单研究 → 跨研究同处理对） | study/event/n 均按 colmap 解析（`tolower(cm$study/event/n)` 兜底） | fd11_b 本地 ok（k=5，n_treat=4） |
| **P0-3** 贝叶斯配对后验提取错误（`post_mean=2, CI=[0.1,3.9]`，真后验 0.287 [0.151,0.422]） | `bayesmeta$mu` 槽位实为 `mu.prior` 参数向量 `c(mean,sd)`，`mean(res$mu)`/`quantile(res$mu)` 取到先验参数；且不同版本 `$summary` 行列方向不同 | 一律从 `$summary` 提取，兼容参数行×统计列 / 统计行×参数列两种方向 | fd14_a/b/c 本地 ok，后验 0.2866/0.2847/0.2844 ✅ |
| **P1-4** Egger/Begg 发表偏倚检验未实现（`stats.bias` 承诺缺失） | `funnel_plot`/`pairwise_meta` 等分支仅合并+画漏斗图，从未调用偏倚检验（`run_task.R` grep `regtest|ranktest` 零命中） | **补实现**：`funnel_plot`/`pairwise_meta`/`trimfill`/`subgroup_analysis` 拟合后调 `metafor::regtest()`/`ranktest()` 写入 `stats.bias`（metafor 为核心依赖，零新增安装；k≥3 才计算，tryCatch 兜底 NA；Egger p<0.10 加偏倚警告） | fd08 对称数据 p=0.547 不警告 / 不对称 p=0.029、0.0002 正确警告 ✅ |

**回归**：修复后本地引擎重跑 18 个代表性用例（二分类/连续/预计算/生存/单组率/亚组/元回归/剪补/敏感性/TSA/功效/RoB/可视化），18/18 通过，零破坏。

### Notes / 说明

- 由 `meta_test` NL 测试套件驱动（ct-update §18：60 首轮 + 23 补测 = 83 例）；用例/执行器/复现脚本待归档至 `tests/`。
- **待部署**：修复仅落地本地镜像 `adapters/coze_project/src/r_engine/run_task.R`（唯一源，无其它同步副本）；部署属发布动作，须显式确认后执行（三端同步已无 → 重打包 → 重部署 → §18.6 线上 83 例回归）。
- **未处理（另行评估）**：13 项文档声明但引擎无 task 的功能（multilevel/multivariate/IPD/cumulative/leave_one_out/selmodel/bootmeta/drapery/grade/prisma_checklist/prisma_flow/rve_meta/metainc → 均 `unknown_task`）；P2 偏差 4 项（Forest 5 主题 `figure$theme` 未消费、rob2 `tool` 参数未使用、esc 扩展转换返回空、nma_rank rank 提取 None）。

## [1.9.7] — 2026-08-19

### Added / 新增（上传文件处理对齐 ct-base §6.7）

- **SKILL.md 新增「上传文件处理 / User-Uploaded Files (ct-base §6.7)」章节**：区分两类上传——
  - **结构化数据文件（csv/xlsx/xls）**：走既有 Type 4 数据模板验证路径（`references/data_templates.md`），不适用文档→md 转换，但 §6.7.2 信息透明与 §6.7.3 保密边界生效；
  - **文档/模板类（docx/pptx/pdf/doc）**：先按 §6.7.1 分层转 md 再提取研究数据（`.docx/.pptx` → 共享转换器 `scripts/office_to_md.py`；`.pdf` → 环境 pdf 技能；`.doc` → 提示安装 word-reader/antiword；扫描件 → 提示提供文字版）；
  - **转换前必向用户展示 §6.7.2 提示**（PPT 转换丢非文本元素）；
  - **保密处理（§6.7.3）**：技能不主动拦截，coze 仅收汇总统计量（不含 IPD），用户明确要求数据不出域时引导本地引擎（`prefer="local"`）。
- **`references/data_templates.md` Type 4 补充文档上传指针**：非结构化文档不属 Type 4 范围，指引到 ct-base §6.7。
- **新增 `scripts/office_to_md.py`**（ct-base §6.7 共享件副本，stdlib-only，docx/pptx → md 单一解析器，与底座字节级一致）。
- **SKILL.md frontmatter 版本对齐**：1.8.3 → 1.9.7（消除长期漂移，与 CHANGELOG 一致）。

## [1.9.6] — 2026-08-19

### Changed / coze 端工作流调整（内部实现，细节不随发布）

- coze 端进行工作流调整（含运行日志记录机制与 skillname 更正 `meta`）。相关实现位于 `adapters/coze_project/`（Coze 远端镜像，§16.7 目录级排除、**不随技能发布**）；接口契约见镜像内 `coze_contract.md`（不发布）。本条目仅保留功能性概要，不披露内部实现细节。

## [1.9.7] — 2026-08-19

### Added / 新增（出图模式 + 渲染计时）

- **`figure_mode` 出图模式选项**（`adapters/run_analysis.py` 新增 `render_figures()`）：
  - `svg_inline`（默认）— `figures[].svg` 原样保留，agent 内联渲染
  - `png_file` — 本地 `cairosvg` 转 PNG 文件存 `out_dir/`，figures 替换为 `{type, format:"png", path}`；不占 LLM 上下文、界面渲染更快，但变位图
- **渲染计时（★ 本地渲染阶段，非 coze 计算）**：
  - `coze_client.run_meta` 仍测 coze 往返但**改名 `coze_elapsed_seconds`**（仅诊断参考）
  - `render_figures()` 新增 `render_elapsed_seconds` = 拿到 SVG → 处理 → widget/PNG 就绪的秒数（本地精确测）；界面浏览器渲染无法在 agent 侧计时，用 `render_svg_kb` 作代理
  - 阈值常量 `RENDER_SVG_THRESHOLD=30s` / `RENDER_SVG_KB_THRESHOLD=200KB`，超阈值自动生成 `render_hint`（中文），提示切 `png_file`
- **svglite 2.2.2 缺 `</g>` 修复**（`rendering.py` 新增 `_fix_xml()`）：用标签栈补齐缺失闭合（浏览器宽容但 cairosvg 严格解析失败；仅 PNG 路径使用）
- **SKILL.md Output 章节**更新：figure_mode 选项 + 渲染计时规则 + agent 必须在回复中体现 render_hint
- **inline_rendering.md §7** 新增：出图模式 + 渲染计时完整说明；坑列表补 svglite 缺闭合

### Notes / 说明

- coze 端**零改动**（png_file 是呈现层本地转换）；coze_elapsed_seconds / render_elapsed_seconds 语义分离，避免混淆"哪个时间"

## [1.9.8] — 2026-08-19

### Added / 新增（ct-base §5 coze 出站授权规范落地）

- **出站披露（§5 强制）**：SKILL.md 执行模型 + README/README_zh-CN 双份新增"数据将发送至 https://ct-meta.coze.site/run"披露声明（发送内容 = 分析数据，不含 PII）；杜绝"出站却声称零出域"
- **首次出站授权门控（§5 AUTH-BLOCK 范式）**：`coze_client.py` 新增 `_auth_gate()` / `approve_endpoint()` / `AuthRequiredError`——端点不在白名单 → stderr 输出 AUTH-BLOCK + 统一确认文案（目标服务器/发送内容/本地资料有限说明）；用户确认后写入 `adapters/config.json` `auto_approve_endpoints`（agent 绝不代写）；默认端点已**作者预置**（正常用户无感），自定义端点才弹确认
- **未授权不阻断（§5）**：`run_analysis.py` 捕获 AuthRequiredError → 优先本地兜底（notes 注明"本次未使用云端分析"）；本地不可用返回 `_source=auth_blocked` 明确提示（授权问题可解决，不抛 RuntimeError）
- **出站 payload 脱敏（§5）**：`sanitize_payload()` 发送前剥离 PII（身份证/手机号/邮箱，递归清理嵌套结构）
- **agent 行为规则（§5 出站全程确认）**：SKILL.md 新增——forward 前**恰好一条**流程通知；coze 失败**先问用户**是否允许诊断，拒绝则交付本地答案 + 显著警告

### Notes / 说明

- 凭据本就符合 §5（coze_token.py XOR+base64 混淆，README 声明非真加密）；config.json 仅含白名单（无凭据），随技能发布（作者预置设计）

---

## [1.9.5] — 2026-08-19

### Added / 新增（结果呈现规范）

- **内联渲染规范** `references/inline_rendering.md`：所有 `figures[].svg` 默认**内联渲染进对话流**（非附件），含：
  - **根因修复**：①svglite 内容超界（森林图实测 x∈[-140,644]，实际宽 785px 而 viewBox 仅声明 504px）→ `content_bbox()` 扫描内容极值动态扩展 viewBox；②**内部 clipPath 裁剪**（svglite 固定 0..504 clip 裁掉左右文字列，viewBox 扩展也无效）→ `_strip_clip()` 移除；③transform 旋转文本纳入 bbox（translate 锚点 + textLength 双向扩展）
  - **正式模块** `adapters/rendering.py`：`extract_svg` / `_strip_clip` / `content_bbox` / `build_figure_widget`（标准库零依赖，含 points 超长行拆分、px 后缀、transform 文本保守覆盖等实测处理）
  - **宽度策略**：SVG 固定实际内容宽度不缩放 + 外层 `overflow-x:auto` —— 容器装不下（含正常对话窗）即出横向滚动条；`margin:0 auto` 水平居中（窄容器自动回左对齐可滚动）；**y 方向 pad_y=24 上下留白（所有图统一）**；备选自适应模式仅在用户明确要求铺满时启用
  - 可选缩放控件（− / 适应 / ＋）
- SKILL.md `## Output` 更新：默认呈现 = 内联渲染（引用 inline_rendering.md），同时 output/ 落盘供下载/编辑
- **统一要求上收 `ct-base/BASE.md §19`**（docs/06-inline-rendering.md，全库强制）——本技能 `rendering.py` 为 §19.6 参考实现

### Notes / 说明

- 内联渲染由 agent 侧（LLM 呈现层）消费 `figures[].svg` 字符串完成，**coze 端无需改动**（返回已是标准 SVG）

---

## [1.9.4] — 2026-08-19

### Fixed / 修复（coze 端点默认值误报不可达）

**缺陷**：`adapters/coze_client.py` 的 `DEFAULT_ENDPOINT` 写死本地开发占位 `http://localhost:5000/run`；真实端点 `https://ct-meta.coze.site/run` 只记录在 `coze_integration_test.py` 注释。用户未配置 `COZE_META_ENDPOINT` 时，请求打到本机被拒 → `run_analysis` 误判 coze 不可达 → 错误回退本地（用户侧排查确认：401 仅缺 token，连接本身正常）。

**修复**：
1. `coze_client.py`：`DEFAULT_ENDPOINT` → `https://ct-meta.coze.site/run`（零配置即用）；docstring/错误提示同步。
2. `coze_client.py health()`：探测 `/health` 路由（自定义域名未必存在）→ 探测 `/run` 可达性（2xx/4xx/5xx 均视为可达，仅网络层错误判不可达）。
3. `SKILL.md` / `adapters/README.md`：默认端点描述同步。

**验证**：无环境变量下 `_endpoint()`=真实端点、`health()`=True、`run_meta` 跑通（status=ok + repro 返回）。

**补充修复（同日）**：`run_meta()` 的 URL 拼接 `_endpoint() + "/run"` 在 `COZE_META_ENDPOINT`/`DEFAULT_ENDPOINT` **已带 `/run` 后缀**时会拼成 `/run/run` → HTTP 404 `{"detail":"Not Found"}`，与 1.9.4 的默认值修复叠加后仍会误判 coze 不可达。修复：endpoint 以 `/run` 结尾时直接使用，否则自动拼接。验证：`health()`=True；真实分析（5 项 RCT pairwise_meta）经默认端点跑通，status=ok。

---

## [1.9.3] — 2026-08-19

### Changed / 变更（删除冗余 r_engine/，引擎统一到镜像）
- **技能根 `r_engine/` 删除（用户决策）**：本地引擎唯一来源 = `adapters/coze_project/src/r_engine/`（coze 远端双向同步唯一源）；本地测试/开发直接调用镜像内引擎，消除双份副本漂移风险。
- `adapters/local_engine.py` 默认 `META_LOCAL_ENGINE_DIR` 改为 `<skill>/adapters/coze_project/src/r_engine`（实测 fd01_a 通过：status=ok + repro 字段返回）。
- 文档同步：SKILL.md / AGENTS.md / adapters/README.md / coze_client.py 全部 r_engine 引用改为镜像路径；.gitignore 删除 `r_engine/*.R` 规则（目录已不存在，镜像整体已排除）。

---

## [1.9.2] — 2026-08-19

### Changed / 变更（coze 项目镜像统一到技能内）
- **镜像位置统一（用户决策）**：coze 项目本地镜像迁至 `adapters/coze_project/`（含 `coze_contract.md`、`src/r_engine/*.R`、`scripts/`、`docker/`），**作为与 coze 远端双向同步的唯一源**；不再使用工作区 `coze_meta_project/` 作为主镜像（保留为历史快照）。
- **发布排除（红线）**：`.gitignore` 重写（修正过时"Python 模板内嵌"注释）+ 新增 `.clawhubignore`——`adapters/coze_project/` 与 `r_engine/*.R` 均不随技能发布（`coze_contract.md` 属 ct-base §16.7 红线）。git archive 实测发布包 0 命中。
- **adapters/README.md**：路由策略更新为「发布 coze-only + 本地兜底仅开发者用」；新增「coze 项目镜像双向同步约定」章节（本地→coze 打包部署 / coze→本地导出覆盖 / diff 一致性基准）。
- 一致性验证：`adapters/coze_project/src/r_engine/` ≡ 技能 `r_engine/`（diff 为空）。

---

## [1.9.1] — 2026-08-19

### Changed / 变更（发布形态决策 + 复现性增强）
- **发布形态决策（用户拍板）**：对外发布 **coze-only（thin client）**——所有 R 计算经 coze 工作流，本地 LLM 仅做需求标准化/数据整理/结果呈现；**最终用户无需安装 R**。本地 `r_engine/` 保留为**开发/复现镜像**（与 coze 字节级同源，开发者经 `META_LOCAL_ENGINE_DIR` 启用）。SKILL.md Initialization 同步更新。
- **复现性（必须满足）**：每次分析输出新增 `repro` 字段 = ①可复现 R 脚本（`deparse(df)` 数据构造 + 按 task 的核心调用 + R/包版本报告，本地 R 直接 source 即可复现）②`r_version` ③`packages`（核心包版本号）。实现于 `run_task.R .repro_script()`，覆盖全部 16 个 task 分支（nma 用 `prep` 对比格式、dose_resp 用 `yi ~ dose` 公式等）。
- **coze 端版本报告**：`http_run.sh` 健康检查升级——打印 `R.version.string` + 核心 14/可选 2 包版本号（`[启动] R 版本 / 包 xxx ✅ vX.Y.Z`），下次部署日志即得基线版本。
- **coze_contract.md**：§4 出参 schema 增加 `repro` 字段说明；新增 **§8 coze 端环境版本**（R 4.6.1 实测基线 + 本地复现差异注意，以部署日志为准）。
- 96 例 dryrun 无回归（ok=87 err=0）；5 个代表案例 repro 脚本实测可执行。

---

## [1.9.0] — 2026-08-19

### Changed / 变更（coze 96 例联调闭环：依赖瘦身 + 15 处引擎修复 + 用例修正）
- **R 包清单瘦身**（单一可信源 `docker/r_packages.txt`）：核心 14（metafor/meta/netmeta/bayesmeta/dosresmeta/mada/robumeta/clubSandwich/ggplot2/svglite/forestploter/jsonlite/dplyr/scales）+ 可选 2（ggrepel/robvis）。移除：`esc`（effect_size_conversions.R 重写为 metafor::escalc + 标准公式，输出结构不变）、`metagear`/`gridExtra`（零引用）、`gemtc`/`rjags`/`multinma`（贝叶斯 NMA 后端移除，coze 容器无 root 无法装 JAGS——`bayesian_nma` 为已知环境限制，联调 MANIFEST 标记 `expected`）。
- **run_task.R 引擎修复**（96 例联调驱动，15 处）：colmap 统一小写（数据形态识别）；metaprop method 映射（meta≥8 仅 Inverse/GLMM）；metacont/metagen/metamean 移除已废弃 method 形参；method.tau 回退 "DL"；`.bubble_plot` ggplot 自实现（metafor::bubble 未导出）；influence 改 metafor::rma.uni 路径；`.nma_prep` 二分类 Haldane 校正自算 logOR（netmeta 统一对比路径）；netrank 用 `rk$rank` 提取；dose_resp 透传 cases/n/se/sd/type；bayesian_pairwise 后验稳健提取；tsa 传 data.frame；rob2 交通灯图 ggplot2 自绘（去 robvis 依赖）；esc 自实现 `.esc_convert`；`.engine_dir` 防御 `nzchar(NA)` 陷阱（source 调试场景）。
- **advanced_functions.R 修复**：run_diagnostic_meta 列名小写归一（tp/fp/fn/tn）；mada SROC 改 S3 泛型绘图；`.rob_colour` + ggplot2 自绘交通灯/汇总图。
- **用例生成器 `gen_meta_cases.py`**：dose_resp 用例修正（dosresmeta gl 法要求每 study 参考剂量组 se=0，否则 grl 崩溃——用例数据 bug）；MANIFEST.csv 新增 status 列（`expected` 豁免）。
- **`coze_contract.md`**：§6 包清单同步核心 14+可选 2；task 枚举表全量更新为实际实现。
- **`adapters/coze_integration_test.py`**：判分对齐 ct-base §18.4（ok/warn/None 通过）；新增 MANIFEST expected 豁免。
- **线上验证**：96 例联调全绿（90 ok + 3 warn[esc 近似] + 3 expected[bayesian_nma]），对比修复前 53 ok/43 error。相关标准已沉淀至 ct-base §18（BASE.md v1.1.41）。

---

## [1.8.3] — 2026-08-17

### Changed / 变更（执行后端双轨化：coze 默认优先 + 本地 R 兜底）
- **Reversed 1.8.2 "full coze transfer"**: 技能重新保留本地 R 分析能力，但默认一律优先调用 coze 工作流；
  本地分析仅作为 **coze 调用失败时的自动兜底**，或 **用户明确要求本地/离线分析** 时启用。
- 统一入口 `adapters/run_analysis.py`：`prefer="coze"`（默认）先调 coze，失败自动回退本地并标记 `_source="local_fallback"`；
  `prefer="local"` 仅本地、不触 coze。返回结果统一带 `_source` 字段（coze / local_fallback / local）。
- 新增 `adapters/local_engine.py`：subprocess 调用技能内置 `r_engine/run_task.R`（与 coze `src/r_engine/` 字节级同源，靠 `coze_contract.md` 同步）。
- 技能 `r_engine/` 重新放回（统一 dispatcher `run_task.R` + 各引擎 .R），作为本地兜底镜像（非权威副本）。
- `SKILL.md` / `AGENTS.md` / `adapters/README.md` 同步更新：双轨执行模型、环境检测、安全红线、目录结构。

---

## [1.8.0] — 2026-08-02

### Added / 新增
- **ct-base alignment**: comprehensive alignment with `ct-base` BASE.md specification.
  - Added `AGENTS.md` (English-only agent-facing rules: environment, execution, language, security, reuse, menu triage, traceability).
  - Added `CHANGELOG.md` (this file).
  - Added `references/units.md` (atomic task unit index for pipeline).
  - Added `scripts/i18n.py` (from ct-base — bilingual EN/ZH helper with auto locale detection).
  - Added `scripts/r_libs.py` (from ct-base — R invocation + validation + sanitization helper).
  - Added `references/language_policy.md` (from ct-base — detailed bilingual policy).
  - Added `references/report_template.md` (from ct-base — report skeleton reference).

### Changed / 变更
- **SKILL.md**: frontmatter enriched with `required_commands: [Rscript, python]`. Body remains English-only agent-facing.
- **README files**: renamed `README_ZH.md` → `README_zh-CN.md` per ct-base naming convention.
- **Language detection**: migrated to `i18n.py`'s unified `is_chinese_os()` (covers env vars + Windows API + Python locale fallback).
- **User menus & README (UI polish)**: SKILL.md Triage §5.2 now explicitly lists the "③ Can't decide? → explain the differences between these choices" routing-menu entry; README Complex popup-menu / Vague grill-me examples made more human-friendly so carbon-based users find it easier to use.

### Fixed / 修复
- Removed stale `README_ZH.md` references across SKILL.md, README.md, README_zh-CN.md.
- **English README untranslated Chinese**: translated all residual Chinese in `README.md` (Example 1 "You say", Scenario Index "Try saying" tables, §4 title) to English; synced version string to `1.8.0` in both READMEs.
- **Security-audit doc alignment** (SkillSpector 10 Medium/Low findings — all documentation-consistency, no malicious code):
  - Removed the `Confidentiality Notice` block from `README.md` — eliminates the "summary stats only" vs "supports IPD patient-level data" trust-boundary contradiction, and also complies with the earlier user instruction that non-`ct-` skills omit confidentiality statements (the zh-CN README never had it).
  - Added PDF-batch-download warnings (network access / local write / copyright) in both READMEs (§7).
  - Clarified the high-friction trigger rule in both READMEs' FAQ: code runs only when you explicitly say "execute"/"请直接计算"; casual mentions do not trigger execution.
  - Clarified the language-switch note: default follows OS locale and only affects display language, no extra authorization needed.
  - Tightened `SKILL.md` Memory-read scope note: "(R config keys only; no personal info is read or sent)".
- **ClawHub display-name fix**: republished with a clean top-level directory name `meta-analysis` so the ClawHub page title shows the correct skill name instead of the previous temp publish-folder name "Meta Analysis Strip V180".

---

## [1.8.1] — 2026-08-02

### Fixed / 修复
- **ClawHub display-name fix**: republished with a clean top-level directory name `meta-analysis`, correcting the ClawHub page title that wrongly showed "Meta Analysis Strip V180" (caused by the previous temp publish-folder name, which ClawHub used as the display name fallback).
- **Carries the v1.8.0 GitHub documentation-alignment to the marketplaces**: English README residual Chinese fully translated; `Confidentiality Notice` removed (resolves IPD-vs-summary-stats trust-boundary contradiction, complies with the non-`ct` no-confidentiality rule); added PDF-batch-download warnings, high-friction trigger clarification, and language-switch note in both READMEs; tightened `SKILL.md` Memory-read scope note.

---

## [Unreleased] — 2026-08-15（遗留未发版条目，定版时与上方 A 档一并处理）

### Changed / 变更
- **Architecture restructure (ct-base §16.9 / future Coze workflow prep)**: all R-software-invoking code moved out of `scripts/` into a dedicated **`r_engine/`** folder (templates `r_*.py` + generated `*.R` + `r_libs.py` + `check_integrity.sh`). `scripts/` now holds only pure-local Python (`i18n.py`, `generate_topic_report.py`, example JSON). A reserved **`adapters/`** folder documents the future unified Coze workflow call layer (see `adapters/README.md`; `ct-samplesize`-style backend selection planned). All references updated: `SKILL.md`, `AGENTS.md`, `references/*.md` (`source("r_engine/*.R")`), `tests/*.R`, `.gitignore` (`r_engine/*.R`). `r_libs.py` gained a sys.path bootstrap to keep importing `scripts/i18n.py`. `check_integrity.sh` multi-line `_msg` quoting fixed (pre-existing latent bug, surfaced by bash strict mode).

### Added / 新增
- **Quality Gate (human sign-off + R red-light, ct-update upgrade A)**: numeric trustworthiness hardening inspired by O0000-code/meta-analysis-skill. New R function `run_quality_gate(es_data, model, bias_result)` (r_engine/meta_analysis_core.py) computes red/yellow/green flags **in R** (never LLM-read): k<3 red, I²>75% red → pooled estimate NOT presented, publication-bias checklist (Egger/Begg) missing → red; zero-dependency hand-written JSON output. New `scripts/quality_gate.py` consumes the gate JSON as the human sign-off gate: red → blocked (exit 2), `--yes` records human sign-off (exit 0), yellow → warn (exit 1), green → pass. SKILL.md Output section documents the gate; SKILL.md kept at 199 lines.
- **Topic Selection module（选题评估 · upstream gate）** — reference-designed from the public `meta-analysis-topic-selector` skill (ClawHub @wenhan9739), adapted to this skill's local-first architecture:
  - Dual path entry: **Quick** (≤30 min, 1-page decision card) / **Full** (5-stage workflow with decision gates).
  - Four-dimension scoring model (clinical value / methodological feasibility / data availability / novelty, 0–5 each, total 0–20, any ≤2 = veto).
  - Cross-check rules R1–R6 (automatically detected internal contradictions force re-review).
  - PICO/PECO operational decomposition (`references/pico-guide.md`).
  - Three-layer dedup search (PROSPERO → Cochrane → PubMed; non-English opt-in) + near-duplicate judgment matrix + increment statement (`references/dedup-search.md`).
  - PRISMA 2020 (11 key items) + AMSTAR-2 (7 critical domains) topic-stage pre-check (`references/compliance-precheck.md`).
  - Meta-type decision tree (pairwise / NMA / IPD / dose-response / DTA / single-group…).
  - 11-section topic report via `scripts/generate_topic_report.py` (JSON → Markdown/HTML, stdlib only) + manual template (`references/topic-report-template.md`) + PROSPERO field mapping (`references/prospero-mapping.md`).
  - New references: `topic-selection.md`, `pico-guide.md`, `dedup-search.md`, `compliance-precheck.md`, `topic-report-template.md`, `prospero-mapping.md`; example input `scripts/topic_report.example.json`.
  - `SKILL.md`: Level-1 menu gains `0️⃣ Topic Selection`, Triage Vague row routes "无选题/可行性评估" to the module, References table updated (SKILL.md kept at 200 lines).
- **ct-update competitor registration (2026-08-15)**: added `meta-analysis-topic-selector` (★★★★★) and `meta-analysis-journal-selector` (★★★★) (ClawHub @wenhan9739) to the meta-analysis competitor list with seed keywords.

### Changed / 变更
- `SKILL.md`: Language section compressed; Initialization integrity-check block inlined; Level-1/Level-2 menus reformatted to fit the new entry while keeping ≤200 lines.

---

## [1.8.3] — 2026-08-02

### Fixed / 修复
- **IPD trust-boundary contradiction (SkillSpector finding)**: rewrote `AGENTS.md` §4 security red-line — the old line stated "no patient-level data" while the skill advertises IPD meta. New wording clarifies that **all data you provide, including IPD, is processed locally from your own files and never uploaded or sent anywhere**; IPD is fully supported and handled the same local-only way. This closes the real source of the "summary stats vs IPD" divergence finding (the earlier `README.md` Confidentiality Notice removal addressed a duplicate copy of the same phrase).

---

## [1.7.0] — 2026-08-01

### Added / 新增
- Full bilingual auto-switch: default English, auto-switch to Chinese on `zh-*` locale (`.msg(en, zh)` pattern in R files + Python i18n).
- `permissions` block declaration in SKILL.md frontmatter.
- `references/svg_editing.md` — SVG editing tools & journal format conversion guide.
- `references/advanced_api.md` — reusable API reference for TSA / dose-response / survival / Bayesian NMA wrappers.

### Changed / 变更
- Effect size conversion module (`esc`) expanded: d ↔ g ↔ logOR ↔ r ↔ Fisher's z, batch mode + Hedges' g correction.

---

## [1.6.0] — 2026-07-25

### Added / 新增
- Bayesian NMA: `multinma` (Stan) + `gemtc` (JAGS) full workflows.
- TSA: self-implemented `run_tsa()` with O'Brien-Fleming boundaries.
- Survival meta: `survmeta` wrapper + KM pseudo-IPD reconstruction.
- Dose-response: `dosresmeta` wrapper.

---

## [1.5.0] — 2026-07-15

### Added / 新增
- Initial public release on GitHub / ClawHub / SkillHub.
- Full RevMan 5.x 1:1 code mapping.
- Stata `metareg` / `mvmeta` equivalents.
- Network meta: `netmeta` + `gemtc` + `multinma`.
- Single-group meta: `metaprop` / `metamean` / `metainc` / `metacor`.
- Diagnostic meta: `mada::reitsma` bivariate + SROC.

---

## [1.0.0] — 2026-06-01

### Added / 新增
- Initial version. Core pairwise meta-analysis with `metafor` / `meta`.
