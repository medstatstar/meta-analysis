# -*- coding: utf-8 -*-
# AUTO-GENERATED from setup_packages.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_setup_packages.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "setup_packages.R"

R_SOURCE = r'''#!/usr/bin/env Rscript
# ============================================================================
#  Meta-Analysis R Packages Setup Script
#  用法: Rscript setup_packages.R [--advanced]
# ============================================================================

args <- commandArgs(trailingOnly = TRUE)
advanced <- "--advanced" %in% args

cat("========================================\n")
cat(" Meta-Analysis R Package Checker/Installer\n")
cat("========================================\n\n")

# --- 1. Check R Version ---
cat(sprintf("R version: %s\n\n", as.character(getRversion())))

# --- 2. Define Package Lists ---
core_pkgs <- c("metafor", "meta", "netmeta", "ggplot2", "gridExtra", "dmetar")
optional_pkgs <- c(
  "metasens",    # 敏感性分析（上限/下限法）
  "bayesmeta",   # 贝叶斯元分析
  "metaviz",     # 交互式可视化
  "robvis",      # RoB 可视化
  "gt",          # 出版级表格
  "robumta",     # 稳健方差估计
  "clubSandwich",# 稳健推断
  "metaDigitise",# 图表数字化
  "esc",         # 效应量计算辅助
  "grid",        # 基础图形
  "cowplot"      # 图形组合
)

all_pkgs <- if (advanced) c(core_pkgs, optional_pkgs) else core_pkgs

# --- 3. Check & Install ---
results <- data.frame(
  package = character(),
  installed = logical(),
  version = character(),
  stringsAsFactors = FALSE
)

for (pkg in all_pkgs) {
  is_installed <- requireNamespace(pkg, quietly = TRUE)
  ver <- if (is_installed) {
    as.character(packageVersion(pkg))
  } else {
    "NOT INSTALLED"
  }
  
  results <- rbind(results, data.frame(
    package = pkg,
    installed = is_installed,
    version = ver,
    stringsAsFactors = FALSE
  ))
  
  if (!is_installed) {
    cat(sprintf("📦 Installing %s...", pkg))
    tryCatch({
      install.packages(pkg, repos = "https://cran.r-project.org", quiet = TRUE)
      cat(" DONE ✓\n")
      results$installed[results$package == pkg] <- TRUE
      results$version[results$package == pkg] <- as.character(packageVersion(pkg))
    }, error = function(e) {
      cat(sprintf(" FAILED ✗ (%s)\n", e$message))
    })
  } else {
    cat(sprintf("✓ %s (%s)\n", pkg, ver))
  }
}

# --- 4. Special handling for dmetar (GitHub) ---
cat("\n--- Checking dmetar (GitHub) ---\n")
if (!requireNamespace("dmetar", quietly = TRUE)) {
  cat("📦 Installing dmetar from GitHub (MathiasHarrer/dmetar)...")
  tryCatch({
    if (!requireNamespace("remotes", quietly = TRUE)) {
      install.packages("remotes")
    }
    remotes::install_github("MathiasHarrer/dmetar", quiet = TRUE)
    cat(" DONE ✓\n")
  }, error = function(e) {
    cat(sprintf(" FAILED ✗ (%s)\n", e$message))
    cat("   Manual fix required: run in R\n")
    cat("   > install.packages('remotes')\n")
    cat("   > remotes::install_github('MathiasHarrer/dmetar')\n")
  })
} else {
  cat(sprintf("✓ dmetar installed\n"))
}

# --- 5. Summary ---
cat("\n========================================\n")
cat(" SUMMARY\n")
cat("========================================\n\n")

installed_count <- sum(results$installed)
total_count <- nrow(results)

cat(sprintf("Installed: %d / %d\n", installed_count, total_count))

if (installed_count < total_count) {
  missing <- results$package[!results$installed]
  cat(sprintf("\nMissing packages: %s\n", paste(missing, collapse = ", ")))
}

cat("\nDone! 🦞\n")
'''


def materialize(scripts_dir=None):
    """将本模块内嵌的 R 源码写出为 scripts/<R_FILENAME>。"""
    import os
    if scripts_dir is None:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(scripts_dir, R_FILENAME)
    with open(out, "w", encoding="utf-8") as f:
        f.write(R_SOURCE)
    return out


if __name__ == "__main__":
    print(materialize())
