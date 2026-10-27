# 检索策略方法学吸收:y9655980-crypto/sr-search-skill(升级项 H)

> **性质**:本文档为中文引用式改写的方法学参考;本轮**不引入代码**,仅吸收检索策略方法学与报告模板。
> **来源仓库**:https://github.com/y9655980-crypto/sr-search-skill
> **许可证**:MIT(README License 节明示,2026-10-27 读取核实)。
> **仓库形态**:Agent Skill(SKILL.md 工作流 + `scripts/mesh_lookup.py` 零第三方依赖 + references 模板 + tests);单次提交 2026-08-20,README 自述"代码与文档由 Claude 协助起草、作者审阅,已核规则逐条对照官方帮助页人工核实"。
> **读取日期**:2026-10-27(README/README.zh-CN、SKILL.md、references/db-syntax.md、references/chinese-databases.md、references/prisma-s.md、templates/strategy-appendix.md 原文)。
> **改写纪律**:以下各节均为引用式改写;`[已核]`/`[未核]` 标注纪律**原样保留**(标注含义见第 1 节开头),不得摘除标注后当已核实内容传播。

---

## 1. 多数据库检索语法对照表(含 [已核]/[未核] 标注纪律)

**来源**:`references/db-syntax.md` 与 `references/chinese-databases.md`,https://github.com/y9655980-crypto/sr-search-skill/blob/main/references/db-syntax.md · 读取日期 2026-10-27

**标注纪律(先读这段)**:`[已核]` = 源仓库于 2026-08-20 对照该库官方帮助页或官方来源核实过;`[未核]` = 通行用法、源仓库无机构权限核实,**首次使用前必须先到该库帮助页核一遍**,核实后在本地补日期改标记。凡本文档沿用 `[未核]` 的条目,同样视为未核实。

**通用原则(所有库)**:每个概念块 = 受控词行 OR 自由词行,块间 AND;逐行编号、后行引用前行(`#1 OR #2`),附录照抄;初检不加语言/年份/文献类型限定,要加就在最后一行加并单独记录;引号一律英文直引号(Word/PDF 复制来的弯引号会让 Scopus/WoS 报错)。

### 1.1 PubMed [已核 2026-08-20,来源 PubMed User Guide]

| 功能 | 写法 | 备注 |
|---|---|---|
| 主题词(默认扩展) | `"Periodontitis"[mh]` | 等价 `[MeSH Terms]`,含下位词 |
| 主题词不扩展 | `"Periodontitis"[mh:noexp]` | |
| 题名/摘要 | `periodontitis[tiab]` | 自由词主力字段 |
| 截词 | `periodont*[tiab]` | `*` 前至少 4 字符;截词关闭自动主题词映射 |
| 引号内截词 | `"periodontal disease*"[tiab]` | 官方允许 |
| 邻近 | `"uric acid periodontitis"[tiab:~5]` | 引号内所有词 N 词以内、任意顺序;仅 ti/tiab/ad |
| 引号短语 | `"attachment loss"[tiab]` | 短语不在索引时 PubMed 丢引号并给警告 |
| 日期 | `2010/01/01:2026/12/31[dp]` | |
| 排除动物 | `NOT ("Animals"[mh] NOT "Humans"[mh])` | 不要直接 `Humans[mh]`(丢未标引新文献) |

关键陷阱:字段标签与截词都会关闭 ATM(自动主题词映射),所以 `[mh]` 行必须**显式写出**;打错的字段标签(如 `[tiabb]`)PubMed **不报错**、静默丢弃走自动映射,命中可翻三倍——须逐行对照 PubMed 的 query translation 审计。

RCT 过滤器(Cochrane 高敏感度版)[未核:首次使用对照 Cochrane Handbook 技术补充原文]:`randomized controlled trial[pt] OR controlled clinical trial[pt] OR randomized[tiab] OR placebo[tiab] OR drug therapy[sh] OR randomly[tiab] OR trial[tiab] OR groups[tiab] NOT (animals[mh] NOT humans[mh])`。观察性研究无公认过滤器;用 SIGN 现成的须写明出处。

### 1.2 Embase(embase.com 界面)[部分已核 2026-08-20:经图书馆指南转述官方规则]

| 功能 | 写法 | 备注 |
|---|---|---|
| Emtree 扩展 | `'periodontitis'/exp` | 单引号 |
| Emtree 不扩展 | `'periodontitis'/de` | |
| 题名/摘要/关键词 | `periodontitis:ti,ab,kw` | |
| 截词 | `periodont*:ti,ab,kw` | `*` 前至少 2 字符,建议 ≥3 |
| 邻近 | `(uric NEAR/3 acid):ti,ab,kw`;`NEXT/n` 定序 | |
| 去重 | `[embase]/lim NOT [medline]/lim` | Cochrane 不建议(丢 Embase 独有标引),用了要说明 |

Emtree 无公开 API,必须登录后在 Emtree 浏览器查;Emtree 与 MeSH 词表/层级常不一致,不能拿 MeSH 直接套。Embase Classic(1947–)与 Ovid 平台订阅年限不同,方法学里**从平台界面读**实际覆盖年限。

### 1.3 Cochrane Library(CENTRAL / CDSR)[已核 2026-08-20,官方页经图书馆指南转述核对]

| 功能 | 写法 | 备注 |
|---|---|---|
| MeSH 行 | `MeSH descriptor: [Periodontitis] explode all trees` | |
| 不扩展 | `MeSH descriptor: [Periodontitis] this term only` | |
| 自由词 | `(periodontitis OR periodontal):ti,ab,kw` | |
| 截词 | `periodont*` | **引号短语内禁用 `*`** |
| 短语+截词替代 | `(periodontal NEXT disease*)` | 官方替代写法 |
| 邻近 | `NEAR/3` | |

记录纪律:检索日期必填;显示 Issue 号(如 Issue 8 of 12, 2026)一并记;**CENTRAL 与 CDSR 分开记命中数**。适用于干预性问题;病因/观察性 MA 通常可不用。

### 1.4 Web of Science Core Collection [已核 2026-08-20,来源 Clarivate Search Rules(zendesk),经图书馆指南转述核对]

| 功能 | 写法 | 备注 |
|---|---|---|
| 主题 | `TS=(periodontitis OR periodont*)` | 题名+摘要+作者关键词+KeyWords Plus |
| 截词 | `*`(任意)、`?`(1 字符)、`$`(0–1 字符) | **`*` 前至少 3 字符** |
| 短语 | `"periodontal disease"` | 引号=精确短语,**并关闭词形还原** |
| 引号内截词 | `"periodontal disease*"` | **[未核]** |
| 邻近 | `NEAR/5` | |

WoS 无受控词表:策略 = PubMed 的 tiab 行翻译过去,借词形还原省去单复数罗列。记录勾选的索引(SCI-E/SSCI/ESCI…)与本机构订阅的回溯年限——各校不同,必须写进方法学。

### 1.5 Scopus [已核 2026-08-20,来源 Elsevier Scopus Support,经图书馆指南转述核对]

| 功能 | 写法 | 备注 |
|---|---|---|
| 题名/摘要/关键词 | `TITLE-ABS-KEY(periodontitis OR periodont*)` | |
| 松散短语 | `"periodontal disease*"` | **双引号内允许通配符**、做词形还原 |
| 精确短语 | `{periodontal disease}` | 花括号:逐字匹配、无通配符 |
| 截词 | `*`、`?` | 不能单独用;连字符/点/斜线旁的通配符被丢弃 |
| 邻近 | `W/5`(任意序)、`PRE/5`(定序) | |
| 索引词 | `INDEXTERMS(periodontitis)` | 可作受控词行 |

### 1.6 不建议作主库

- **ScienceDirect**:全文库非文摘库;布尔运算符 ≤8 个、不支持通配符 [未核];SR 中一般不单列。
- **Google Scholar**:不支持截词、256 字符上限、最多看 1000 条、不可复现、不可批量导出;PRISMA-S 允许作为**补充来源**(记录检索式、日期、筛了前多少条)。

### 1.7 中文库(CNKI / 万方 / 维普 / SinoMed)

来源:`references/chinese-databases.md`。要点多为 [未核](以各平台当前帮助页为准):

1. **SinoMed 是四个常用中文库中唯一有受控词表的**(CMeSH 中文医学主题词表,可扩展检索),对应 PubMed 的 `[mh]` 行;CNKI/万方/维普的"主题"字段是文本字段,策略 = 同义词 OR 串。
2. 四库常规检索界面**不提供截词符**,词形变化(心肌梗死/心肌梗塞、龋/龋齿/龋病、高血压/高血压病、旧称与港台译名、中英混写如 "long COVID")必须逐个列出。
3. 中文扩词来源优先级:SinoMed 主题词条目词 → 同主题已发表中文 SR 的方法学 → 全国科技名词委术语在线(termonline.cn)→ 学科教材索引。取舍:短词覆盖长词时留短词;短词歧义大时留长词;拿不准时**查全优先,留**。
4. 字段与运算符:**CNKI** 专业检索 `SU=('牙周炎'+'牙周病') AND SU=('尿酸'+'高尿酸血症')`,`+`=OR、`*`=AND、`-`=NOT,SU 主题/TI 篇名/KY 关键词/AB 摘要/FT 全文 [未核];**万方** `主题:(牙周炎 OR 牙周病) AND 主题:(尿酸 OR 痛风)`,运算符大写两侧留空格 [未核];**维普** `U` 任意字段/`M` 题名或关键词/`K` 关键词/`T` 题名/`R` 摘要 [未核];**SinoMed** 检索历史写法 `"牙周炎"[不加权:扩展]`(主题词行)、`牙周炎[常用字段:智能]`(自由词行)[未核]。
5. 记录:检索日期、勾选的子库/资源类型、匹配方式(精确/模糊);复现靠检索式文本而非结果页链接(改版即失效)。

---

## 2. MeSH 主题词 + 自由词组合策略

**来源**:`SKILL.md` 五条铁律与 Step 2–3、README 能力表,https://github.com/y9655980-crypto/sr-search-skill/blob/main/SKILL.md · 读取日期 2026-10-27

结构纪律(引用式改写):

1. **双行缺一不可**:每个概念块 = 主题词行 OR 自由词行,块间 AND。数据库有受控词表且概念有对应词时,两行都必须有;没有(新概念无 MeSH、WoS/中文库无词表)就只做自由词行,并在方法学里写明原因。只做自由词会漏掉"标题摘要没出现该词但被标引"的文献;只做主题词会漏掉未标引的新文献。
2. **MeSH 选词纪律——精确匹配,不取第一条**:MeSH 描述词须按**描述词名精确匹配**或确认查询词恰为某描述词的 Entry Term 后选用,不得取自由检索第一条(例:`Periodontitis` 自由检索第一条是下位词 `Chronic Periodontitis`;`Pain` 排第 39;`Neoplasms` 进不了前 50)。含逗号的主题词照用(`"Diabetes Mellitus, Type 2"[mh]`),自由词行里还原语序即可。
3. **扩展/不扩展的决策**:读描述词的**范围注释**对照研究定义决定——若默认扩展(explore)会带入不想要的下位词(如 `Periodontitis` 展开含根尖周炎),则改用 `[mh:noexp]` + 手选下位词;决策要有记录。
4. **多描述词并列**:一个概念可对应多个描述词(如尿酸块 = `Uric Acid` + `Hyperuricemia` + `Gout`),主题词行内 OR 并列。
5. **旧标引(Previous Indexing)**:如 `Hyperuricemia` 2002 年前标引为 `Uric Acid`——检索年限跨过换标年份时,须把旧标引词并入主题词行,否则早年文献漏检。注意旧标引词是历史标引,不是上位词。
6. **自由词扩展四步**:截词合并(`periodontit*`;注意各库 `*` 前最少字符不同)→ 拼写/形式变体(英美拼写、连字符、缩写 NIDDM/T2DM/SUA)→ 借已发表策略(1–2 篇同主题 Cochrane 优先的附录,引用出处 = PRISMA-S 第 11 条)→ 引号短语核对(不在索引的短语 PubMed 拆词并给警告)。
7. **不设词数上限、命中数只记不判**:查全优先,初检不加限定;"数多是筛选的事,不是砍词的理由"。
8. **逐行命中数记录**:策略逐行编号执行,**每行**记录命中数,填入附表 S1;这是 PRISMA-S 第 8、15 条合规的基础。

---

## 3. known-item 召回核查(已知阳性文献诊断性检验)

**来源**:`SKILL.md` Step 4、README 能力表、`scripts/mesh_lookup.py` check 子命令说明 · 读取日期 2026-10-27

方法(引用式改写,Cochrane 手册建议的步骤):

1. **准备已知集**:收集 3–10 篇确定应纳入的相关文献(来自相关综述、导师推荐等),**必须来自检索策略之外的途径**,否则是循环论证。
2. **执行核查**:将最终策略的完整检索式与已知文献 PMID 一起送检验——先验证每个 PMID 确实存在于 PubMed(把抄错的 PMID 与真漏检的分开报),再看它与策略的交集。
3. **漏检处理**:对漏检的 PMID,打开看它的 MeSH 标引与标题用词,补词后重跑;若该文献本就超出纳入范围,那是纳入标准的问题而非策略的问题,另案处理。**全部已知文献检出**才进入翻译其他库的步骤。
4. **解释边界**:核查通过只证明"不漏这几篇",不证明整体查全。该检验的定位是策略的**诊断性退出关卡**,不是查全证明。
5. **本技能落地提示**:基线 keyword_breadth.py 无此召回审计能力;人工执行时,可将已知 PMID 逐个用其标题/MeSH 反查,确认能被最终检索式命中,把漏检清单与补词记录归档进检索日志。

---

## 4. PRESS 咨询式检索策略同行评议

**来源**:`SKILL.md` Step 8(PRESS 自审 6 问)、README "Works well with"(PRESS 清单 McGowan et al. 2016)· 读取日期 2026-10-27

要点(引用式改写):

1. **定位**:PRESS(Peer Review of Electronic Search Strategies,McGowan 等 2016)是检索策略的同行评议规范;PRISMA-S 第 14 条要求**描述评审过程**——谁审(角色)、何时、用什么工具、审出什么、改了什么;一句"经 PRESS 评审"不合规。
2. **六问自审清单**(投稿前/送图书馆员前逐条过,任何一条答不上来就回对应步骤):
   ① 检索式是否对应研究问题——概念块不多不少;
   ② 布尔运算与括号层级是否正确;
   ③ 每个概念块是否都有主题词行 + 自由词行;扩展(explode)决策是否有理由;
   ④ 自由词是否覆盖拼写变体、缩写、截词;
   ⑤ 限定与过滤器的使用是否有理由且写明出处;
   ⑥ 有无拼写错误、弯引号、字段标签打错。
3. **纪律**:自审不能替代外部评议——有条件时送图书馆员/信息专家正式评议;评审日期、评审人角色、修改摘要都要进入 PRISMA-S 报告。

---

## 5. PRISMA-S 16 项报告清单 + 双语 methods 段模板 + Table S1 模板

**来源**:`references/prisma-s.md`、`templates/strategy-appendix.md` · 读取日期 2026-10-27

### 5.1 PRISMA-S 16 项——"每条要交出什么"(引用式改写;条目原文以 Rethlefsen et al. 2021, *Syst Rev* 10:39 为准)

**信息来源与方法**

| # | 条目 | 要交出的东西 |
|---|---|---|
| 1 | 数据库名称 | 每库全名+平台+覆盖年限(PubMed(NLM;仅加 `medline[sb]` 才写 MEDLINE via PubMed)、Embase(via embase.com/Ovid)、CENTRAL(Issue X)、WoS CC(索引+订阅年限)、CNKI、万方、维普、SinoMed) |
| 2 | 多库同检 | 用 Ovid 等平台一次检多库时,说明哪些库被同检 |
| 3 | 试验注册库 | 检了哪些注册库(名称、日期、策略);是否必须检由 Cochrane/MECIR、方案或期刊定;没检就写明 |
| 4 | 其他在线资源 | 灰色文献(Google Scholar 前 N 条、学位论文库、会议摘要等) |
| 5 | 引文追踪 | 向前(被引)/向后(参考文献)各对哪些文献做了 |
| 6 | 联系人 | 是否联系作者/厂家要未发表数据 |
| 7 | 其他方法 | 手检期刊、相关综述纳入文献清单 |

**检索策略**

| # | 条目 | 要交出的东西 |
|---|---|---|
| 8 | **完整策略** | **每库、逐行、原样**进附录——是能复制粘贴复现的全文,不是"关键词包括…" |
| 9 | 限定 | 语言/年份/类型/人类:用了哪些、为什么、在哪一行 |
| 10 | 过滤器 | 用已发表过滤器(Cochrane RCT HSSS、SIGN)引用出处;自己改过要说明 |
| 11 | 借用策略 | 参考了哪篇综述的策略,引用 |
| 12 | 更新检索 | 投稿前是否重跑;两次日期与两次命中数 |
| 13 | **检索日期** | 每库**各自**的精确日期(不是"2026 年 8 月") |

**同行评议 / 记录管理**

| # | 条目 | 要交出的东西 |
|---|---|---|
| 14 | 策略评审 | 评审过程:谁审(角色)、何时、工具(PRESS 2015 版/McGowan 2016)、审出什么、改了什么 |
| 15 | 总记录数 | 每库命中数+合计(进 PRISMA 流程图第一格) |
| 16 | 去重 | 软件+版本、按哪些字段匹配、自动与人工步骤顺序、去重前后数量 |

### 5.2 双语 methods 方法学段落模板

模板思想(占位符引用式转写;方括号全部为占位符,逐个替换;标"如用/IF DONE"的块没做就整块删——**模板不是清单,写了没做的事是学术不端**):

> 英文骨架:We searched PubMed (NLM; inception to [DATE]), Embase (via [platform], [coverage] to [DATE]), [CENTRAL ([issue/date]),] Web of Science Core Collection ([indexes]; [coverage] to [DATE]), [Scopus,] and [N] Chinese databases ([CNKI, Wanfang, VIP, SinoMed]; inception to [DATE]). Search strategies combined controlled vocabulary ([MeSH, Emtree, CMeSH]) and free-text terms for [concept A] and [concept B], [no language or date restrictions / limits: …] (Supplementary Table S1). [Citation chasing …] [Registry searches …] [PRESS review …] Records were deduplicated in [software + version] by [fields], followed by manual checking. [Updated on [DATE].]
>
> 中文骨架:我们检索了 PubMed(建库至[日期])、Embase([平台],[起始年]至[日期])、[Cochrane CENTRAL([期号])、]Web of Science 核心合集([索引];[订阅起始年]至[日期])[、Scopus]及[N]个中文数据库([知网、万方、维普、SinoMed];建库至[日期])。检索式由主题词([MeSH、Emtree、CMeSH])与自由词组成,以[概念 A]与[概念 B]做逻辑与运算,[不限语种与年份/限定:……](完整检索式见附表 S1)。[如做:引文追溯……][如做:注册库检索……][如做:PRESS 评审……]使用[软件及版本]按[字段]去重并人工复核。[如做:检索更新于[日期]。]

关键措辞陷阱:脚本/直连 E-utilities 检索的是**整个 PubMed**(含 PMC 作者稿、出版商直送、1946 年前 OLDMEDLINE);只有检索式加了 `medline[sb]` 才能写 "MEDLINE (via PubMed)",否则写 PubMed。

### 5.3 Supplementary Table S1(完整检索策略表)+ 两路检索日志模板

结构(引用式改写):

- **表头**:研究问题、PECO/PICO(打 ✔ 标明哪些概念块进了检索式——通常只有 P 和 E/I)、最后检索日期、检索者、PRESS 评审记录(或"未做")。
- **每库一个小节**(S1.1 PubMed … S1.9 SinoMed),列结构固定为三列:`#` 行号 | `Search line` 检索行原文 | `Records` 命中数;小节标题写平台、覆盖年限、检索日期。
- 每个概念块内:主题词行、自由词行、`#1 OR #2` 合并行;块间 `AND` 行;末尾按需加动物排除行、限定行(单独记录)。
- **SinoMed 小节必须体现主题词行 + 自由词行**双行结构;CENTRAL 与 CDSR 命中数分开记。
- **检索日志按 PRISMA 2020 流程图两路分表**:
  - A 路(数据库与注册库/流程图左路):列 = Database | Platform | Coverage | Date searched | Records | Notes(限定/过滤器);末行 A 小计(含去重后数)。
  - B 路(其他方法/流程图右路):向后引文追踪、向前引文追踪、网站/组织/灰色文献、联系作者,各记日期与记录数;末行 B 小计。
  - 两路**分别小计、不得合成一个总数**。

---

## 6. 八步工作流(检索策略总流程,供编排参考)

**来源**:`SKILL.md` · 读取日期 2026-10-27

定范围(PECO、按问题类型选库——干预性 RCT 至少 MEDLINE+Embase+CENTRAL;观察性 MEDLINE+Embase+WoS(±Scopus);要中文文献加 CNKI+万方+维普+SinoMed)→ 抽概念(去动作词/修饰词,通常 O 不进检索式)→ 主题词(精确匹配选词+扩展决策)→ 自由词(截词/变体/借词/短语核对)→ PubMed 跑数 + known-item 召回核查(全检出才放行)→ 逐库翻译到其他英文库 → 中文库(SinoMed 双行,其余自由词)→ PRISMA-S 报告 + PRESS 自审。

---

## 7. 附注:可选薄检索脚本(本轮不实现,仅留档)

**来源**:`scripts/mesh_lookup.py`(经 README 与 SKILL.md 用法描述核实)· 读取日期 2026-10-27

- 该脚本为 **stdlib-only**(Python ≥3.8,零第三方依赖),MIT 许可;四个子命令:`mesh`(经 `"<词>"[MeSH Terms]` 字段限定查 NCBI E-utilities,仅描述词名/Entry Term 精确匹配时自动选定,防"第一条"陷阱,输出树号/上位词/范围注释/Entry Terms)、`count`(发送前按白名单校验字段标签,再对照 PubMed query translation 审计——抓静默丢标签)、`run`(逐行执行编号策略,打印带 Records 列的附录表,解析失败退出码 2、有审计警告退出码 1)、`check`(known-item 召回核查,先验 PMID 存在再算漏检,漏检退出码 1)。网络路径:直连 → `SR_SEARCH_PROXY` → 系统代理逐段回退,仅对瞬态错误有界重试。
- **纪律判定**:该脚本属检索编排(NCBI E-utilities 直接 HTTP),**不触碰 coze 统计红线**;后续升级若引入,定位为"可选薄检索辅助脚本"。本轮按文档先行原则**不实现、不引入代码**,仅在此留档备查。
- 备选搭配工具(源 README 提及):Polyglot Search Translator(PubMed 行翻译到各库)、Yale MeSH Analyzer(看已知文献的标引补漏)。
