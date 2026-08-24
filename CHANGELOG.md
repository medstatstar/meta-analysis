# Changelog / 变更日志

All notable changes to the `meta-analysis` skill are recorded here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versioning follows [Semantic Versioning](https://semver.org/).

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

## [Unreleased] — 2026-08-15

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
