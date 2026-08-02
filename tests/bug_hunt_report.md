# Meta-Analysis 技能 Bug 排查报告（10 案例，简单→复杂）

> 目的：设计 10 个从简单到复杂的案例，实际运行以发现潜在 bug。
> 方法：直接调用 `scripts/*.R` 中的函数；R 版本 4.5.1，metafor/netmeta/ggplot2 已安装。
> 日期：2026-08-02

---

## 一、案例设计与真实结果

| # | 复杂度 | 场景 | 实际结果 | 发现 |
|---|--------|------|----------|------|
| 1 | Simple | 2 项研究二分类 OR 合并 | ✅ PASS | k=2 边界正常（I²/predict 处理 OK） |
| 2 | Simple | 连续型 SMD 含 1 项 NA SD | ✅ PASS | `escalc` 产生 yi=NA，`rma` 自动 na.omit，仅 warning |
| 3 | Simple | 单组率 Meta（PLO） | ✅ PASS | `transform="plogis"` 森林图/漏斗图正常 |
| 4 | Complex | 3 项研究发表偏倚（Egger+Begg，trimfill 跳过） | ✅ PASS | 边界条件 `k>=3` / `k>=5` 判定正确 |
| 5 | Complex | 5 项研究连续型 SMD + 森林图/漏斗图 | ✅ PASS | `transform="none"` 经 `switch(...,identity)` fallback 正常 |
| 6 | Complex | 连续型 SMD 含 NA SD 出图 | ✅ PASS | `order(yi)` 对 NA 默认置末，不崩（仅 NaN 权重，美观问题） |
| 7 | Complex | 元回归含中文列名（发表年份/样本量） | ✅ PASS | 中文列名在 `rma(formula,...)` 中可被数据环境解析，**无 bug**（第一轮假设错误） |
| 8 | Complex | 网络 Meta 不连通（A-B 与 C-D 两子网） | ❌ FAIL → ✅ 已修复 | **Bug B**：原 `netmeta()` 抛原生错误未捕获；已用 `tryCatch` 捕获并输出双语友好提示 |
| 9 | Complex | 一键流程 `ma_analyze` + `ma_save` | ✅ PASS | 输出 5 个文件（forest/funnel × svg/png + md）正常 |
| 10 | Vague | 完全模糊需求 | N/A（设计层） | grill-me 文本菜单按 SKILL.md Triage §5.2 输出，符合预期 |

---

## 二、确认的 Bug 清单

### 🔴 Bug B（高危）— 网络 Meta 不连通时崩溃
- **位置**：`scripts/network_meta_analysis.R` → `run_frequentist_nma()`
- **触发**：用户提供的研究构成多个互不连通的子网（如 A-B 和 C-D 无共同干预）
- **当前行为**：`netmeta()` 直接抛错并终止，错误信息为英文原话
- **期望行为**：捕获错误，用双语提示用户"网络不连通"，并建议调用 `netconnection()` 识别子网
- **修复方向**：
  ```r
  run_frequentist_nma <- function(...) {
    library(netmeta)
    net <- tryCatch(
      netmeta(TE=TE, seTE=seTE, treat1=treat1, treat2=treat2, studlab=study,
              data=data, sm=sm, reference.group=reference.group,
              sep.trt=sep.trt, common=common, random=random),
      error = function(e) {
        if (grepl("sub-networks|separate", conditionMessage(e))) {
          msg <- .msg(
            "Network is disconnected — cannot fit a single network model. Run netconnection() to identify sub-networks, then analyze each connected component separately.",
            "网络不连通——无法拟合单一网络模型。请运行 netconnection() 识别子网，再分别分析每个连通分量。")
          stop(msg)
        } else stop(e)
      })
    return(net)
  }
  ```

### 🟡 Bug C（中危）— 核心脚本函数依赖外部全局 `.msg`
- **位置**：`scripts/meta_analysis_core.R`
  - `analyze_heterogeneity()`（第 169–172 行，无条件调用 `.msg`）
  - `create_forest_plot()`（第 336 行起，无条件调用 `.msg`）
  - `create_funnel_plot()`（第 382 行起，无条件调用 `.msg`）
  - `ma_analyze()`（第 463 行等错误/默认路径调用 `.msg`）
- **根因**：`meta_analysis_core.R` **顶部没有 `.msg` / `.MA_LANG` 定义**（grep 确认为空），所有 `.msg` 调用依赖 `network_meta_analysis.R` 加载时写入全局环境的同名函数。
- **触发**：若只 `source("scripts/meta_analysis_core.R")`（未加载 `network_meta_analysis.R`），上述函数必崩：`could not find function ".msg"`。
- **当前为何没暴露**：技能正常使用时 agent 会 source 全部脚本，`network_meta_analysis.R` 的全局 `.msg` 恰好在场。但这是**脆弱的隐式依赖**。
- **修复方向**：在 `meta_analysis_core.R` 顶部（library 之后）补一个文件级 `.msg` 定义，使该文件自包含：
  ```r
  .MA_LANG <- local({
    lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
    if (grepl("zh|cn|chs", lang)) "zh" else "en"
  })
  .msg <- function(en, zh) if (.MA_LANG == "zh") zh else en
  ```
  （与 `network_meta_analysis.R` 顶部定义一致，函数内同名局部定义优先级更高，互不冲突。）

### 🔴 Bug B（高危）— 网络 Meta 不连通时崩溃
- **状态**：✅ **已修复并验证（2026-08-02）**
- **修复位置**：`scripts/r_network_meta_analysis.py` → `run_frequentist_nma()`（重新生成 `network_meta_analysis.R`）
- **修复方式**：用 `tryCatch` 包裹 `netmeta()` 调用；`error` 分支中若匹配 `separate sub-networks|not connected|disconnected|inconsistent`，则 `stop()` 输出双语提示（中文环境："网络不连通：检测到相互独立的子网络……请合并子网络或补充桥接研究"），否则原样上抛。
- **验证**：不连通输入（A-B + C-D 两子网）现返回 `RESULT: Network is disconnected: separate sub-networks detected... VERDICT: PASS`；连通网络（A-B-C 链，`reference.group="A"`）正常输出 `treatments: A/B/C | k = 3`，tryCatch 未误伤正常路径。

### 🟡 Bug C（中危）— 核心脚本函数依赖外部全局 `.msg`
- **状态**：✅ **已修复并验证（2026-08-02）**
- **修复位置**：`scripts/r_meta_analysis_core.py` 顶部（R_SOURCE 起始处）新增文件级 `.MA_LANG` + `.msg` 定义；重新生成 `meta_analysis_core.R`。
- **修复方式**：在 `# --- 0. 环境准备 ---` 之前插入与 `network_meta_analysis.R` 一致的全局 `.msg` 定义，使核心脚本自包含。
- **验证**：仅 `source("scripts/meta_analysis_core.R")`（不加载 network 文件）后调用 `analyze_heterogeneity()` 返回 `OK (heterogeneity I2 = 0)`，不再 `could not find function ".msg"`。

---

## 三、澄清的误报（第一轮假设，本次运行推翻）

| 假设 | 实际结果 |
|------|----------|
| `transform="none"` 在 `switch` 无分支→`f=NULL`→出图崩溃 | ❌ 误报：`switch("none", exp=exp, tanh=tanh, plogis=plogis, identity)` 末尾 `identity` 充当 fallback，`f=identity`，正常 |
| 中文列名在元回归公式需反引号 | ❌ 误报：R 公式解析依赖数据环境，中文列名可直接解析，无需反引号 |
| 单亚组 `anova(btt=c(2,1))` 越界 | ✅ 已修复（上一轮 Bug #11） |
| 敏感性分析 `quality` 列 NA 致 `if(NA)` 崩溃 | ✅ 已修复（上一轮 Bug #17） |

---

## 四、测试产物

| 文件 | 说明 |
|------|------|
| `tests/test_cases.md` | 第一轮 10 案例（代码审查视角） |
| `tests/test_cases_v2.md` | 第二轮 10 案例（验证修复 + 边界） |
| `tests/test_v2_run.R` | 本次实际运行的 10 案例脚本（Case 4–10） |
| `tests/test_simple.R` / `test_quality.R` / `test_bug_fixes.R` | Bug #11/#17 验证脚本 |
| `tests/bug_hunt_report.md` | 本报告 |
| `output/` | Case 10 生成的森林图/漏斗图/汇总 md |

---

## 五、修复状态（2026-08-02 已全部修复并验证）

| Bug | 严重度 | 状态 | 验证 |
|-----|--------|------|------|
| #11 单亚组 `anova` 越界 | 🔴 高 | ✅ 已修复（前轮） | `tests/test_simple.R` PASS |
| #17 敏感性 `quality` 列 NA | 🔴 高 | ✅ 已修复（前轮） | `tests/test_quality.R` PASS |
| B 网络 Meta 不连通崩溃 | 🔴 高 | ✅ 已修复 | `tests/test_bug_fixes_v2.R` PASS |
| C 核心脚本依赖外部 `.msg` | 🟡 中 | ✅ 已修复 | `tests/test_bug_fixes_v2.R` PASS |

全部 4 个高危/中危 bug 已清零。低危（Case 6 美观问题）不阻塞发布。

---

## 六、Round 3–12 十轮迭代汇总（2026-07-19 完成）

> 任务："设计从简单到复杂的十个案例，用于检查技能潜在的 bug，然后执行修复，这样重复十次"。
> 方法：每轮用 Python 生成 `.R` → `Rscript` 真实运行 10 个案例（覆盖效应量/可视化/亚组/元回归/敏感性/网络 Meta/贝叶斯/一键流程），发现 bug 即修即验。
> 结果：**10 轮全部完成，共新增发现并修复 9 个真实 bug（D/K/Q1 等）**，所有崩溃类问题清零。

### 6.1 每轮聚焦与回归统计

| Round | 聚焦场景 | PASS | ERROR | 说明 |
|-------|----------|------|-------|------|
| 3 | 效应量 + 基础合并边界 | 14 | 2 | ERROR 为合理用户输入错误/友好降级 |
| 4 | 可视化 transform 校验 | 10 | 1 | 发现 **Q1**（无效 transform 静默 NULL） |
| 5 | 亚组分析列名含空格 | 9 | 1 | 发现 **Bug D**（组变量名含空格） |
| 6 | 元回归协变量/交互项 | 9 | 1 | 发现 **Bug E/F/G**（空格列名/空列表/交互项反引号） |
| 7 | 出版偏倚 + 敏感性 | 10 | 0 | 发现 **Bug H/I**（满秩崩/leave1out 求值怪象） |
| 8 | 网络 Meta 出图 + 数据准备 | 8 | 2 | 发现 **Bug J/K**（thickness 非法/强制 treatment 列） |
| 9 | 高级函数 + 守卫降级 | 5 | 5 | 5 PASS + 5 守卫降级（未知类型友好报错） |
| 10 | 一键流程 + 未知类型 | 9 | 1 | 1 未知类型报错（已加 stop 友好提示） |
| 11 | 综合回归（前 10 轮全部案例） | — | — | 全绿，无回归 |
| 12 | 跨文件 source 自包含验证 | — | — | 仅 source 核心脚本不再崩（Bug C 生效） |

### 6.2 Round 3–12 新增 Bug 清单（均已修复并验证）

| Bug | 严重度 | 位置 | 触发 | 修复方式 | 验证 |
|-----|--------|------|------|----------|------|
| **Q1** | 🟡 中 | `create_forest_plot`/`create_funnel_plot` | `transform` 传非法值（如 `"log"`）静默 `switch` 返回 `NULL` → 出破缺图 | `valid_transforms <- c("none","exp","tanh","plogis")` 白名单 + 非法值 `stop(.msg(...))` | Round 4 PASS |
| **D** | 🔴 高 | `run_subgroup_analysis` | 组变量名含空格（`study region`）→ `as.formula(paste("~",group_var))` 解析为减法崩 | `mods = es_data[[group_var]]`（直接传向量，绕开空格列名） | Round 5 PASS |
| **E** | 🟡 中 | `run_meta_regression` | 协变量名含空格 → 公式 `unexpected symbol` | `bt()` 反引号包裹变量名 | Round 6 PASS |
| **F** | 🟡 中 | `run_meta_regression` | 空协变量列表 → `unexpected end of input` | 空列表 `stop(.msg(...))` 友好报错 | Round 6 PASS |
| **G** | 🔴 高 | `run_meta_regression` | 交互项 `year:region` 被整体反引号 → `object 'year:region' not found` | `bt()` 对 `:` 两侧分别反引号 | Round 6 PASS |
| **H** | 🔴 高 | `analyze_publication_bias` | 全相同 SE 时 `regtest` 报"模型矩阵不满秩"崩 | `regtest`/`ranktest`/`trimfill` 均 `tryCatch(...,error=function(e) NULL)`，为 NULL 则不加入 results | Round 7 PASS |
| **I** | 🔴 高 | `run_sensitivity_analysis` | `results$leave1out <- data.frame(...)` 报 `arguments imply differing number of rows: 8, 0`（`$<-` 复合赋值 + 内嵌 data.frame 含字符列的 R 求值怪象） | 拆分为先建 `loo_df <- data.frame(..., stringsAsFactors=FALSE)` 再 `results$leave1out <- loo_df`；model_comparison/cumul 同样拆分 | Round 7 PASS |
| **J** | 🟡 中 | `plot_network` | 默认 `thickness="seTE"` 对 `netgraph` 非法 → 出图崩 | 默认改 `"equal"` + `valid_thickness` 向量校验 | Round 8 PASS |
| **K** | 🔴 高 | `prepare_nma_data` | 强制 `treatment` 列（NMA 长表数据无此列）→ `replacement has 0 rows` | `if (!is.null(arm_data) && "treatment" %in% names(arm_data))` 条件判断 | Round 8 PASS |

### 6.3 修复机制要点（可复用经验）

1. **空格/特殊字符列名**：R 公式 `as.formula(paste(...))` 对含空格列名极脆弱；优先用 `data[[col]]` 直接传向量，或用 `reformulate()`/`bt()` 反引号包裹（交互项 `:` 两侧分别处理）。
2. **R `$<-` 复合赋值 + 内嵌 `data.frame` 含字符列**：会触发 `arguments imply differing number of rows` 的求值怪象；一律先建临时 `df` 再赋值。
3. **外部依赖自包含**：核心脚本顶部必须自带 `.MA_LANG` + `.msg`，不依赖其他文件加载顺序（Bug C）。
4. **防御性校验**：对所有外部输入（`transform`/`thickness`/协变量列表/网络连通性）做白名单或 `tryCatch` 守卫，失败给双语友好提示而非原生栈。

---

## 七、最终修复状态总表（截至 2026-07-19）

| Bug | 严重度 | 状态 | 轮次 |
|-----|--------|------|------|
| #11 单亚组 `anova` 越界 | 🔴 高 | ✅ 已修复 | 前轮 |
| #17 敏感性 `quality` 列 NA | 🔴 高 | ✅ 已修复 | 前轮 |
| B 网络 Meta 不连通崩溃 | 🔴 高 | ✅ 已修复 | 前轮 |
| C 核心脚本依赖外部 `.msg` | 🟡 中 | ✅ 已修复 | 前轮 |
| Q1 无效 transform 静默 NULL | 🟡 中 | ✅ 已修复 | Round 4 |
| D 亚组列名含空格 | 🔴 高 | ✅ 已修复 | Round 5 |
| E 元回归协变量空格 | 🟡 中 | ✅ 已修复 | Round 6 |
| F 空协变量列表 | 🟡 中 | ✅ 已修复 | Round 6 |
| G 交互项反引号 | 🔴 高 | ✅ 已修复 | Round 6 |
| H 出版偏倚满秩崩 | 🔴 高 | ✅ 已修复 | Round 7 |
| I leave1out 求值怪象 | 🔴 高 | ✅ 已修复 | Round 7 |
| J plot_network thickness | 🟡 中 | ✅ 已修复 | Round 8 |
| K prepare_nma_data treatment | 🔴 高 | ✅ 已修复 | Round 8 |

**13 个真实 bug 全部清零（含 8 个高危、5 个中危）。低危（Case 6 vi=0/NA 导致 NaN 权重渲染）不阻塞发布。**

### 测试产物（Round 3–12 新增）

| 文件 | 说明 |
|------|------|
| `tests/round3_effect_size.R` … `round10_onepass.R` | 10 个 Round 测试脚本 |
| `tests/bug_hunt_report.md` | 本报告（含 10 轮汇总） |
| `scripts/*.R` | 由 `scripts/*.py` 重新生成，含全部修复 |
