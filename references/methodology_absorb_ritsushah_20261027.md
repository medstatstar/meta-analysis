# 方法学吸收:ritsushah/systematic-review-meta-analysis-skills(升级项 C)

> **性质**:本文档为中文引用式改写的方法学参考,不引入任何统计计算代码;本技能的统计计算仍由 coze 云端 R 引擎独家承担,本文档仅补外围方法学规范。
> **来源仓库**:https://github.com/ritsushah/systematic-review-meta-analysis-skills
> **许可证**:MIT © Ritu Shah(README 徽章与 License 节明示,2026-10-27 读取核实)
> **仓库形态**:纯 prompt/SKILL.md 合集(18 个子技能),统计计算委托 R 包(metafor/meta/netmeta/gemtc)由宿主执行;仓库只含 scan_skills.py 与 pytest 校验。
> **读取日期**:2026-10-27(README 及 6 份子 SKILL.md 原文)。
> **最近推送**:2026-10-14(据评估记录 `_eval_meta_CFGH.json` 的 commits 页核实结果)。
> **改写纪律**:以下各节均为引用式改写,不逐字复制原文;每节注明来源子技能文件。

---

## 1. 预测区间(prediction interval)在随机效应 Meta 分析中的报告规范

**来源**:`skills/heterogeneity-subgroup-analyst/SKILL.md`(v1.0.0),https://github.com/ritsushah/systematic-review-meta-analysis-skills/blob/main/skills/heterogeneity-subgroup-analyst/SKILL.md · 读取日期 2026-10-27

要点(引用式改写):

1. **何时报告**:采用随机效应模型合并后,当研究数 *k* 充足时,应在报告 Q、df、p、τ²(注明合并方法 REML/DL/PM)与 I² 的同时,给出 **95% 预测区间**。预测区间回答的是"未来一项新研究的效应量有多大可能落在什么范围",与 τ²/I² 互补——I² 描述已纳入研究间变异占比,预测区间描述未纳入研究的效应分布。
2. **解读纪律**:异质性要做**临床层面**的解读,不能只报"I² 偏高"了事;预测区间过宽本身即提示效应在不同真实场景间不可迁移。
3. **亚组纪律**:只运行**方案中预先注册**的亚组比较;任何探索性切分必须标注 post hoc;禁止为凑显著性做数据挖掘;稀疏亚组(*k* < 3–4)只做叙述性比较,不做合并。
4. **DTA 特殊性**:诊断准确性 Meta 中,异质性须分别在 logit 灵敏度与 logit 特异度尺度上报告(或以 HSROC 参数形式),不得在"准确度"上算一个笼统的 I²。
5. **本技能落地提示**:coze R 引擎中 `metafor::predict.rma()`、`meta::predict()` 均可直接产出预测区间;报告模板应在异质性小节固定输出 Q/τ²/I²/95%PI 四件套,PI 在随机效应模型下默认给出(k 不足时注明"未计算,研究数不足")。

> 注:源仓库未规定预测区间的具体措辞模板;上述第 5 点为本技能侧的落地建议。

---

## 2. CINeMA:网络 Meta 分析证据可信度分级框架

**来源**:`skills/network-meta-analyst/SKILL.md`(v1.0.0),https://github.com/ritsushah/systematic-review-meta-analysis-skills/blob/main/skills/network-meta-analyst/SKILL.md · 读取日期 2026-10-27

源仓库核实到的内容(引用式改写):

1. **定位**:NMA 拟合一致性模型并产出 league table、相对效应、P-scores/SUCRA 之后,当条件可行时应做 **CINeMA 或等效的证据可信度分级**(源文件执行协议第 6 步原文要点)。
2. **前置条件**:CINeMA 属 NMA 流程的收尾环节,先决条件是网络几何已建立、传递性已评估、全局/局部不一致性(设计×治疗交互、node-splitting)已检验。
3. **硬规则**:非连通网络必须分离组件后分别处理;稀疏网络退回配对 Meta + 叙述综合;league table 任何单元格不得凭空填写。

**未能核实**:源仓库对该子技能的 CINeMA 仅有"框架名 + 何时做"层面的引用,未展开五个评估维度(研究内偏倚、间接性、不精确性、异质性/不相干性、报告偏倚)的具体判定规则——此细节**未能核实**,使用时应参照 CINeMA 官方应用(cinema.wizer-app.org)与 Salanti 等方法学文献,不在本文档展开。

---

## 3. 观察性研究偏倚工具选择矩阵(NOS / JBI / ROBINS-I)

**来源**:`skills/risk-of-bias-appraiser/SKILL.md`(v1.0.0),https://github.com/ritsushah/systematic-review-meta-analysis-skills/blob/main/skills/risk-of-bias-appraiser/SKILL.md · 读取日期 2026-10-27

工具—设计对应关系(源仓库原文表格,引用式改写):

| 研究设计 | 应选工具 |
|---|---|
| 诊断准确性研究 | **QUADAS-2**(本技能 diagnosis_meta 已覆盖) |
| 随机对照试验 | **RoB 2**(本技能 rob2-narrative/rob2-plot 已覆盖) |
| 非随机干预性研究 | **ROBINS-I** |
| 观察性队列 / 病例对照 | **NOS**(Newcastle-Ottawa Scale) |
| 病例报告 / 病例系列 | **JBI** 清单 |

执行纪律(引用式改写):

1. **先定设计,再选工具**:逐篇确认纳入研究的设计类型,按上表匹配工具;同一综述可多工具并用。
2. **信号问题要本地化**:按本综述主题将工具的 signaling questions 操作化(例:QUADAS-2 中"发热 ≤7 天""索引试验对参考标准设盲"),不得照抄默认文本了事。
3. **档位**:QUADAS-2/RoB 2/ROBINS-I 采用 Low / Some concerns / High 三档;NOS 计星;JBI 用 yes/no/unclear。
4. **证据底线**:无原文证据支撑时不得评 Low risk of bias;QUADAS-2 的 applicability concerns 与偏倚风险分开报告,不得混同。
5. **双人评阅与可溯性**:有条件时双人独立评阅并解决分歧;报告须写明所用工具的版本与引用出处。

**本技能落地提示**:基线对 ROBINS-I/NOS/JBI 的覆盖较薄;后续遇到非随机干预、队列/病例对照、病例系列类综述时,应按上表选择工具并在报告中注明工具版本——工具本体(ROBINS-I、NOS、JBI 清单)均为公开发表的规范文件,可直接引用其官方版本执行评估。

---

## 4. 灰文献检索 + 引文追逐(citation chasing)流程

**来源**:`skills/grey-literature-citation-chaser/SKILL.md`(v1.0.0),https://github.com/ritsushah/systematic-review-meta-analysis-skills/blob/main/skills/grey-literature-citation-chaser/SKILL.md · 读取日期 2026-10-27

流程(引用式改写,7 步):

1. **试验注册库**:检索 ClinicalTrials.gov 与 WHO ICTRP,捕捉在研/未发表研究。
2. **预印本**:方案允许时查 Europe PMC / medRxiv / bioRxiv。
3. **Google Scholar 上限纪律**:使用聚焦检索式;按方案预设上限(如前 200 条);相关性明显衰减即停。Scholar 抓取不稳定,优先人工导出或限量 API/浏览器采集。
4. **向后引文追踪**(backward):过一遍纳入研究的参考文献列表。
5. **向前引文追踪**(forward):在 Web of Science / Scholar 的 cited-by 中查纳入研究被谁引用。
6. **同标准筛选**:补充来源的全部命中,用与主检索完全相同的纳入/排除标准筛选。
7. **分源记账**:每个补充来源的命中数**单独**记入检索日志。

硬规则(引用式改写):

- 灰文献/引文追逐的命中数**默认不得并入** PubMed/Embase/WoS/ScienceDirect 的主识别总数——除非方案明确合并;这正是 PRISMA 2020 流程图左路(数据库/注册库)与右路(其他方法)分流的理由。
- 补充记录须先对主去重集合去重,再进入筛选。
- 引文追逐获得的纳入研究,记录来源标记(如 `source=citation_chasing`)以保可溯。

---

## 5. 双人独立筛选与 Cohen's κ 一致性报告规范

**来源**:`skills/dual-screener/SKILL.md`(v1.0.0),https://github.com/ritsushah/systematic-review-meta-analysis-skills/blob/main/skills/dual-screener/SKILL.md · 读取日期 2026-10-27

流程(引用式改写):

1. **两阶段**:题录/摘要筛选(include / exclude / unsure 三态)→ 全文筛选(仅对 include 与 unsure)。
2. **预定义排除分类学**:全文排除必须落入方案预定义的原因分类(人群不符、索引/参考标准不符、无 2×2 或结局不可提取、设计不符、重复、语言等),每条决定**引用所违反的具体标准条目**,不允许"凭感觉"。
3. **κ 的产生与诚实性**:存在两位独立评阅者时,分歧经讨论/第三方仲裁解决,**并报告 Cohen's κ**;若实际是单人(或自动化)筛选流程,须明确标注,且**不得虚构 κ 值**——"无 kappa 就不写 kappa"。
4. **会议摘要**:按方案处理(常见做法是数据不足即排除),不得临场变通。
5. **动物/体外排除**:此类排除必须给出显式理由。

**κ 阈值与账本格式**:源仓库仅要求"有双人时报告 κ、输出 `data/screening/kappa.json`",未给出 κ 的解释阈值(如 Landis–Koch 分级)——阈值规范**未能核实**,需另行参照 McGowan 等 PRESS 文献或 Cochrane 手册确定。

---

## 6. PRISMA-DTA 流程图变体(诊断准确性综述)

**来源**:`skills/prisma-flow-reporter/SKILL.md`(v1.0.0),https://github.com/ritsushah/systematic-review-meta-analysis-skills/blob/main/skills/prisma-flow-reporter/SKILL.md · 读取日期 2026-10-27

源仓库核实到的内容(引用式改写):

1. **必备计数格**(PRISMA 2020 通用):每库识别数、去重后数、题录/摘要筛除数、全文评估数、全文排除数(带原因)、定性纳入数、定量纳入数(无 Meta 时该格为 0/N/A,不得空缺或编造)。
2. **数字对账**:流程图数字必须能从识别计数文件、筛选 CSV、提取输出**重算得出**;稿件数字与审计链不一致即失败;供应商检索未完成时保持 pending 标注,不得猜数。
3. **左右分路**:灰文献与引文追踪命中默认单独报告(对应流程图右路),不并入数据库主计数。

**未能核实**:源仓库将 PRISMA-DTA 列为该技能支持的流程图框架之一(README 与 SKILL.md 元数据),但 SKILL.md 正文未展开 DTA 专用流程图字段(如患者-索引试验-目标条件维度的分层计数)与标准 PRISMA 2020 流程图的具体差异——DTA 变体的专用字段细节**未能核实**,诊断准确性综述做流程图时应参照 PRISMA-DTA 官方声明(Salameh et al., *J Clin Epidemiol* 2021 及其配套 flow diagram)执行,本技能 diagnosis_meta.md / revman_complete.md 的既有流程可先沿用。

---

## 吸收边界(未吸收项)

- **统计计算细节**(REML 配对 MA、效应量、发表偏倚、meta 回归、NMA 模型拟合、DTA bivariate/HSROC 计算):全部与 coze 云端 R 引擎(metafor/meta/netmeta/gemtc/mada)能力重叠,一律不吸收。
- **manuscript-synthesizer**(PRISMA 合规稿件起草):与本技能 2026-10-27 会话冻结的写作模块冲突,不吸收。
- 各子技能的输出契约 CSV 路径约定(如 `output/tables/*.csv`):属其本地编排形态,与本技能的 contracts/ 体系不同构,仅作模式参考,不作硬性移植。
