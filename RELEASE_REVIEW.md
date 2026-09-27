# meta-analysis 发布评审清单（RELEASE REVIEW）

生成时间：2026-09-01
用途：发布前核查。本清单**不执行任何发布/推送**——所有解除冻结、提交、publish 动作均需用户明确确认（红线）。

---

## 0. 当前状态快照

| 项 | 值 | 来源 |
|---|---|---|
| 技能版本 | **2.3.1** | `SKILL.md` `version:` |
| 开发期冻结 | **生效中** | `adapters/DEV_POLICY.json`：`dev_period=true`、`publish_freeze=true`、`set_at=2026-08-31` |
| 代码层端点覆盖 | ct-meta2 唯一、ct-meta 禁用 | `adapters/coze_client.py` L88-90：`DEFAULT_ENDPOINT=ct-meta2`、`FALLBACK_ENDPOINT=""` |
| Git 最近提交 | v2.2.30 | `git log` |
| 未提交改动 | 大量（含本次案例库扩充全部新增） | `git status`：无暂存，多 `M` + 多 `??` |
| 案例库/模板 | 14 案例 / 11 模板，本地验证通过 | `cases/VERIFICATION_REPORT.md` |

> 注：此前口语称的"v5 部署包"即本 2.3.1 大规模重构代（manifest 版本号 2.3.1）。
>
> **⚠️ 部署面边界更正（2026-09-02 用户澄清）**：`publish_freeze` 仅冻结**技能包**发布（GitHub/SkillHub/ClawHub）。**coze 端（ct-meta2 工作流）的更新是独立部署面，不受发布冻结约束**——5 个 coze-only 形状（C07/C08/C09/C10/C13）+ NMA 网络步，只要 ct-meta2 补全 metafor/netmeta 模型即可上线可算，**无需先解除包冻结**。此前将"那 5 个形状上线"与"解除包冻结"绑定的表述是错误的，已在本清单 §2/§3/§6 更正。

---

## 1. 硬性发布封锁（解除前任何 publish 都会被拦截）

- [ ] `publish_freeze: true` → GitHub / SkillHub / ClawHub **全部冻结**，`publish_guard.py` 与 `deploy_retest` G9 拦截。
- **解除条件（单一触发）**：用户明确告知"开发期结束"。
- **解除动作**：删除 `adapters/DEV_POLICY.json`。删除后 `coze_client.py` L93-94 自动回切 `DEFAULT=ct-meta` / `FALLBACK=ct-meta2`（无需手改代码）。
- ⚠️ **发布风险点**：`DEV_POLICY.json` 当前**未被** `.gitignore`/`.clawhubignore` 排除。发布前必须删除，且切勿用 `git add adapters/` 通配把它带进包/提交。

---

## 2. 功能验证状态（14 案例 / 11 模板）— 全部可算 ✅

> 验证方式：`run_case_human.cmd_start` / `block_b.b1_meta_analysis` 经 `coze_client.run_stage_local`
> 路由到本机 R 镜像 `run_task.R`（含 meta 8.5-0 / metafor / netmeta 3.6-1 / mada），dev runner 即"coze 镜像"。
> 用户 2026-09-02 澄清：**coze 镜像代码更新不受包冻结限制**，故以下可算性独立于 `publish_freeze`。

| 分组 | 案例 | 引擎路径 | 合并效应（随机） | 状态 |
|---|---|---|---|---|
| 二分类 2×2 | C01 OR / C02 RR / C03 RD | 本地 R 镜像 metabin | C01 TE=-0.1628；C02 TE=-0.7107(I²=50%)；C03 TE=-0.0155 | ✅ |
| 连续型 | C04 MD / C05 SMD | 本地 numpy | C04 TE=-10.55；C05 TE=-1.178 | ✅ |
| 已算效应 | C06 logHR / C11 logHR | 本地 R 镜像 | C06 TE=-0.255；C11 TE=-0.274 | ✅ |
| coze-only 形状 | C07 IRR / C08 ZCOR / C09 PLOGIT / C10 MN / C13 DTA | 本地 R 镜像 metafor/mada | C07 TE=-1.2851；C08 TE=0.2244；C09 TE=-1.2665；C10 TE=6.2471；C13 DOR=1.498(SE=0.82/SP=0.99) | ✅ |
| 多臂 RCT | C14 OR | 本地 R 镜像 | TE=0.7693 | ✅ |
| 网状 Meta（对比层） | C12 | 本地 R 镜像 | pairwise TE=0.5492(k=9,I²=85%) | ✅ |
| 网状 Meta（网络层） | C12 | 本地 R netmeta（b1_nma_r） | 6 对网络估计（ACEI~安慰剂 OR=1.93 等） | ✅ |

- 全 14 案例 **A4 数据抽取全链路通过**（红线闸正确展示抽取行，PDF→模板→字段映射无误）。
- 5 个 coze-only 形状 + NMA 网络步：**已随 coze 镜像代码更新（2026-09-02）实测可算**，不再依赖"k=0 兜底"。
- NMA 网络步修复三处（2026-09-02）：(1) `normalize_case` TPL-09 构建**全部两两对比**（C(k,2)），不再仅各活性臂 vs 参考；(2) `_NMA_R_SCRIPT` 补 UTF-8 locale 守卫，修正中文干预名（安慰剂）在 C locale 下乱码导致 `reference.group` 失配；(3) 结果抽取按输入对比(m_input)对齐估计向量后按唯一干预对去重，修正 `comparisons`(m_unique) 与 `TE.nma.random`(m_input) 长度不一致崩溃。

### 2.1 人工审核闸现状（HITL · 2026-09-02 补齐 A2/A3）

> ⚠️ **2026-09-10 事后变更（D21）**：下表的 **A3 初筛** 已并入 **A2「文献集」**
> （`A2.literature_search`），A 阶段序列为 `A1→A2→A4`，`DEFAULT_PAUSE_AT` 不再含
> `A3.screening`。本节保留 2026-09-02 当时的评审记录作历史；当前以
> `references/conversation_flow_menu.md` / `references/HANDOFF_2026-09-10.md §3` 为准。

| 闸 | 阶段 id | 类型 | 触发 / 展示 | 可跳过 | 状态 |
|---|---|---|---|---|---|
| A2 检索策略确认 | `A2.literature_search` | 🟡 软停 | `DEFAULT_PAUSE_AT` 含；展示各库条数(by_source)/检索状态/撤稿数/查询式，防沉默漏检 | 可 | ✅ 本轮**启用 + 覆盖 payload** |
| A3 初筛裁决 | `A3.screening` | 🟡 软停 | `DEFAULT_PAUSE_AT` 含；展示逐条 Include/Exclude `decisions` + 计数 summary，重点防误剔 | 可 | ✅ 本轮**升级为显式裁决** |
| A4 数据提取核验 | `A4.data_extraction` | 🔴 红线 | `extraction_review`(required)；展示抽取行 | 不可 | ✅ 既有 |
| B4 质量门 | `B4.quality_gate` | 🔴 红线 | `final_inclusion`(required) | 不可 | ✅ 既有 |
| C3 参考核验 | `C3.ref_verify` | 🔴 红线 | `reference_verification`(required) | 不可 | ✅ 既有 |
| C4 投稿前 QA | `C4.evidence_qa` | 🔴 红线 | `manuscript_approval`(required) 终闸 | 不可 | ✅ 既有 |

- 🟡 软停（A2/A3/C1）：`DEFAULT_PAUSE_AT` 控制，控制器 `_validate_decision` 允许 `skip`。
- 🔴 红线（A4/B4/C3/C4）：block 函数 emit `gate=...`，控制器 `_view` 置 `kind=gate`、选项剔除 `skip`，`_validate_decision` 强制拒 `skipped`（spec §8.2）。
- 验证：`scripts/smoke_human_gates.py` 全 PASS——A2/A3/A4 序列 + 4 红线 gate 名齐备于 `coze_client._REDLINE_GATES`。

### 2.2 工作台（Web UI · Phase 0/1，2026-09-02 落地）

> 用户需求：流程多、人工确认点多 → 做一个工作台，① 显示当前进度；② 每节点在工作台上改/确认（各节点形态不同）；③ 可行则支持回退重跑。

**可行性结论**：高度可行——`fullflow.py` 已是会话化状态机（落盘/暂停恢复/逐节点可编辑数据/审计日志），FastAPI/uvicorn 已在 `adapters/coze/.venv`（零新依赖）。工作台只是把"agent 渲染 await_human"换成网页，**红线校验原样保留**。

**落地内容（整流程一个工作台，Block A 交互最丰富）**：
- `adapters/workbench/form_schema.py`（Phase 0，纯数据）：按 `stage_id` 描述每节点表单（`object`/`dicttable`/`rowlist`/`textarea`/`json`，dotted-path 解析 ctx={nha,editable,stage}）。A2 库清单+查询式 / A3 翻转子表 / A4 2×2 / B4·C3·C4 红线条只读+批准。
- `adapters/workbench/server.py`（Phase 1）：FastAPI 包装 `run_fullflow`/`resume_fullflow`。`POST /api/start`、`GET /api/session?path=`、`POST /api/decide`，进度由 `blocks[·].envelope.stages` 重建。
- `adapters/workbench/workbench.html`：SPA——左侧进度时间轴 + 中间按 schema 渲染节点表单 + 右侧审计日志；决策按钮 approve/skip/revise/reject。
- `adapters/workbench/launch_workbench.py`：定位 coze venv python + uvicorn 起服务（`python launch_workbench.py` → http://127.0.0.1:8765）。
- `fullflow.py _view` 扩展：`await` 现含完整 `nha`（富载荷）+ `stage_result`（红线节点全字段），agent 渲染与工作台北同时受益。

**缺口（Phase 2，规划中，本次未做）**：
- ③ 回退重跑：需新增 `_rewind(target)`（截断 target 之后 stages+decisions、复位 cursor、重跑）；A2 改查询/A3 翻转后目前为事后补丁（`_apply_revisions`），下游已按原值算完。
- `revise` 真实生效：各块需消费 `revisions_for_block` 重跑（A4 的 `extracted_rows` 已真接 B 输入，其余为补丁）。

**验证**：`scripts/smoke_workbench.py`（函数级，monkeypatch A2 避联网）全 PASS——A1→A2→A3→A4 序列 + nha/editable_payload/form_schema 解析正确 + A4 红线拒 skip；HTTP 端到端探针（真实 uvicorn）全 PASS——start→decide 全链 + A4 红线 400 拒 skip。

---

## 3. coze 镜像上线前置（独立于发布冻结，已完成）

> 用户 2026-09-02 澄清：**coze 镜像代码更新不受 `publish_freeze` 限制**。用户明确"直接更新 coze 镜像代码即可"——
> 此处"coze 镜像"即本机 R 引擎（`adapters/coze/.../run_task.R` + `block_b._NMA_R_SCRIPT`），其更新与技能包冻结解耦。

- [x] **metafor 模型覆盖（已确认）**：本地 R 镜像 `run_task.R` 含 `metarate`(IRR)/`metacor`(ZCOR)/`metaprop`(PLOGIT)/`metamean`(MN)/`metadiag`(DTA)，5 个 coze-only 形状（C07/C08/C09/C10/C13）实测可算。
- [x] **NMA 网络步（已修复并验证）**：依赖 `netmeta` 3.6-1；本地 R 镜像补充 UTF-8 locale 守卫 + 全部两两对比构造 + 长度对齐去重，C12 网络层实测 6 对估计。
- [x] **回归已跑（2026-09-02）**：`test_coze_shapes.py`（→ `scripts/smoke_coze_computable.py`）+ `smoke_offline_computable.py` 全 14 案例确认可算，无回归。
- ⚠️ **验证面说明**：dev runner 经 `run_stage_local` 路由到**本机 R 镜像**（含 metafor/netmeta），故上述验证即"coze 镜像"验证，有效。若需确认 ct-meta2 **云端**端点与本地镜像完全一致，待云端部署后另跑一次回归（与包冻结无关）。

---

## 4. Git 卫生 / 发布前步骤（本地 commit 允许，push 禁止）

- [ ] 本地提交未提交改动（`git commit` 仅写本地，合规；**不推送**）。
- [ ] 发布前确认 `DEV_POLICY.json` 已删（见 §1）。
- [ ] `request.json` / `meta_request.json` 已被 ignore（✅ 已验证，测试夹具不进包）。
- [ ] `cases/`、`scripts/`（含案例库与冒烟脚本）未被忽略（✅ 已验证 `git check-ignore` 判定为"会随包发布"）。
- [ ] 核对 CHANGELOG.md 已回写本次案例库扩充条目（218KB，最近更新 2026-09-01）。

---

## 5. 发布通道与方法

- 使用 `skill-publish` 技能：GitHub / SkillHub / ClawHub 三平台。
- ⛔ **任何 `publish` / `git push` 必须用户明确确认**（红线，不自动执行）。

---

## 6. 需用户决策（请逐项确认）

1. **是否宣布开发期结束？** → 若"是"，我删除 `DEV_POLICY.json` 并本地提交未提交改动（不推送）。
2. **coze 镜像（本机 R 引擎）metafor/netmeta 是否已就绪？** → **已就绪并实测可算**（2026-09-02）。5 个 coze-only 形状（C07/C08/C09/C10/C13）+ NMA 网络步（C12）全部可算，独立于包冻结。如需确认 ct-meta2 **云端**端点与本地镜像一致，待云端部署后跑一次回归（不与包冻结绑定）。
3. **本次发布范围**：随 2.3.1 整体发布，还是仅先发案例库增量（cases/ + scripts/ 冒烟）？
4. **发布平台**：GitHub / SkillHub / ClawHub 全部，还是先发其一？
