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

## References / 引用

- R metagear package: https://github.com/cran/metagear
- PRISMA 2020 statement: Page MJ, et al. (2021). *BMJ*, 372, n71.
