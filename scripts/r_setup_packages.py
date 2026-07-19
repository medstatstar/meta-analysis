# -*- coding: utf-8 -*-
# AUTO-GENERATED from setup_packages.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_setup_packages.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "setup_packages.R"

R_SOURCE = r'''#!/usr/bin/env Rscript
# ============================================================================
#  Meta-Analysis R Package Checker/Installer
#  用法: Rscript setup_packages.R [--advanced]
# ============================================================================

args <- commandArgs(trailingOnly = TRUE)
advanced <- "--advanced" %in% args

# --- 双语语言检测（默认英文，中文环境切中文） ---
.MA_LANG <- local({
  lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
  if (grepl("zh|cn|chs", lang)) "zh" else "en"
})
.msg <- function(en, zh) if (.MA_LANG == "zh") zh else en

cat("========================================\n")
cat(.msg(" Meta-Analysis R Package Checker/Installer\n",
         " Meta-Analysis R 包检查与安装工具\n"))
cat("========================================\n\n")

# --- 1. Check R Version ---
cat(sprintf(.msg("R version: %s\n\n", "R 版本：%s\n\n"), as.character(getRversion())))

# --- 2. Define Package Lists ---
core_pkgs <- c("metafor", "meta", "netmeta", "ggplot2", "gridExtra", "dmetar")
optional_pkgs <- c(
  "metasens",    # 敏感性分析（上限/下限法）
  "bayesmeta",   # 贝叶斯元分析
  "metaviz",     # 交互式可视化
  "robvis",      # RoB 可视化
  "gt",          # 出版级表格
  "robumeta",    # 稳健方差估计
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
    cat(sprintf(.msg("  ⚠️  missing '%s' — please install it manually in your R environment.\n",
                     "  ⚠️  缺少「%s」— 请在 R 中手动安装。\n"), pkg))
  } else {
    cat(sprintf(.msg("✓ %s (%s)\n", "✓ %s（%s）\n"), pkg, ver))
  }
}

# --- 4. Special handling for dmetar (GitHub) ---
cat(.msg("\n--- Checking dmetar (GitHub) ---\n",
         "\n--- 正在检查 dmetar（GitHub） ---\n"))
if (!requireNamespace("dmetar", quietly = TRUE)) {
  cat(.msg("  ⚠️  missing 'dmetar' (GitHub: MathiasHarrer/dmetar) — install manually in R:\n",
           "  ⚠️  缺少「dmetar」（GitHub: MathiasHarrer/dmetar）— 请在 R 中手动安装：\n"))
  cat(.msg("     > (install dmetar manually from GitHub: MathiasHarrer/dmetar)\n",
           "     > （从 GitHub 手动安装 dmetar：MathiasHarrer/dmetar）\n"))
} else {
  cat(sprintf(.msg("✓ dmetar installed\n", "✓ dmetar 已安装\n")))
}

# --- 5. Summary ---
cat(.msg("\n========================================\n",
         "\n========================================\n"))
cat(.msg(" SUMMARY\n", " 汇总\n"))
cat(.msg("========================================\n\n",
         "========================================\n\n"))

installed_count <- sum(results$installed)
total_count <- nrow(results)

cat(sprintf(.msg("Installed: %d / %d\n", "已安装：%d / %d\n"), installed_count, total_count))

if (installed_count < total_count) {
  missing <- results$package[!results$installed]
  cat(sprintf(.msg("\nMissing packages: %s\n", "\n缺少以下包：%s\n"), paste(missing, collapse = ", ")))
}

cat(.msg("\nDone! 🦞\n", "\n完成！🦞\n"))
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
