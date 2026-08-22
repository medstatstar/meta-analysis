# Systematic Review Workflow / 系统评价流程辅助

> Using `metagear` package for: PRISMA screening, PDF batch, data extraction, digitization.

---

## PRISMA Flow Diagram / PRISMA流程图

```r
library(metagear)

# Generate from screening counts
flow <- prisma_flow(
  database = "PubMed, Embase, Cochrane",  # database names
  identified = 520,                        # databases
  duplicates = 140,                        # removed duplicates
  screened = 380,                          # after dedup
  excluded_screen = 140,                   # excluded at title/abstract
  full_text = 80,                          # full-text sought
  excluded_full = 52,                      # excluded full-text
  included = 28,                           # final included
  reasons_no_data = 20,                    # exclusion reasons
  reasons_wrong_pop = 18,
  reasons_wrong_design = 14
)

# Export as SVG/PDF
export(flow, "prisma.svg", "SVG")
export(flow, "prisma.pdf", "PDF")
```

---

## Literature Screening GUI / 文献筛选

```r
# Title/Abstract screening with AI support
screen_titles(
  df = citation_df,
  title_column = "title",
  abstract_column = "abstract",
  reviewer_column = "reviewer",
  decision_column = "include",
  output_file = "screening_results.csv"
)
```

- Supports AI-assisted screening (GenAI)
- Dual-screening mode (2 reviewers + consensus)
- Inter-rater reliability (Cohen's kappa)

---

## PDF Batch Download / 批量PDF下载

```r
# From DOI list
retrieve_pdf(
  doi_list = df$doi,
  output_dir = "pdfs/",
  email = "your@email.com"   # for polite API usage
)

# From PMID list
retrieve_pmid(
  pmid_list = df$pmid,
  output_dir = "pdfs/"
)
```

---

## Data Digitization / 图形数字化

```r
# Extract coordinates from scatter/bar plots
coords <- extract_digit(
  figure = "plot.png",
  x_range = c(0, 10),
  y_range = c(0, 100),
  n_points = 20
)

# Plot to verify
plot(coords)
```

---

## Missing Value Imputation / 缺失值插补

```r
# Multiple imputation for unreported statistics
imp_result <- impute_ml(
  data = df,
  sd_missing = TRUE,
  n_imputations = 10
)

# Imputes: SD from CI/t/SE/r; draws from same study distribution
```

---

## AI 辅助文献筛选（Screening，2026-08-20 补实现 · agent 行为层）

> 替代 metagear 本地 GUI：由 agent 在对话中按纳入/排除标准逐条判定标题/摘要，输出结构化筛选表。**纯 agent 行为，无引擎/脚本依赖**。

**流程**：
1. 用户提供标题/摘要列表（文本、CSV、或经 `adapters/pdf_fetch.py` 收集的文献清单）。
2. agent 与用户确认纳入/排除标准（PICO 维度）。
3. 逐条判定，输出统一筛选表：

| 序号 | 标题 | 作者/年 | 判定 | 理由（对照标准） | 置信度 |
|---|---|---|---|---|---|
| 1 | ... | ... | Include / Exclude / Maybe | ... | 高/中/低 |

4. Maybe 项进入第二轮人工复核；Exclude 项须给可追溯理由。
5. 纳入清单可导出 CSV，供后续数据提取与 Meta 分析。

**规则**：
- 判定必须对照用户确认的纳入/排除标准，**不臆造标准**；标准未覆盖的维度标注"待确认"。
- 置信度低或证据边界模糊 → 一律标 Maybe，不硬判。
- 批量处理时每批 ≤50 条，防止上下文超限；分批间保持判定一致性。

---

## References / 引用

- R metagear package: https://github.com/cran/metagear
- PRISMA 2020 statement: Page MJ, et al. (2021). *BMJ*, 372, n71.
