# -*- coding: utf-8 -*-
# AUTO-GENERATED from stata_equivalents.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_stata_equivalents.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "stata_equivalents.R"

R_SOURCE = r'''# ============================================================================
# Stata 命令的 R 等价实现
#  映射 Stata meta 分析生态到 R 生态
#  本文件提供: metareg → rma/permutest, mvmeta → rma.mv
# ============================================================================

# --- 双语语言检测（默认英文，中文环境切中文） ---
.MA_LANG <- local({
  lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
  if (grepl("zh|cn|chs", lang)) "zh" else "en"
})
.msg <- function(en, zh) if (.MA_LANG == "zh") zh else en

# ===================== metareg (Stata) =====================
run_metareg_R <- function(yi, vi, mods, data,
                          method = "REML",
                          test = "knha",
                          level = 95,
                          permute = TRUE,
                          nperm = 1000,
                          plot = TRUE,
                          plot_options = list(
                            xlab = "Covariate",
                            ylab = "Effect Size",
                            pch = 19,
                            col = "blue",
                            cex = 1.5
                          )) {
  library(metafor)
  
  fit <- rma(yi = yi, vi = vi, mods = mods, data = data,
             method = method, test = test, level = level)
  
  cat("================================================\n")
  cat(.msg(" Meta-Regression (Stata metareg equivalent)\n",
           " 元回归（等价于 Stata metareg）\n"))
  cat("================================================\n")
  print(summary(fit))
  
  cat(.msg("\nHeterogeneity:\n", "\n异质性：\n"))
  cat(sprintf(.msg("  tau2 = %.4f | I² = %.1f%% | H² = %.2f\n",
                   "  tau2 = %.4f | I² = %.1f%% | H² = %.2f\n"),
              fit$tau2, fit$I2, fit$H2))
  
  if (!is.null(fit$R2)) {
    cat(sprintf(.msg("  R² (heterogeneity explained): %.1f%%\n",
                     "  R²（解释的异质性）：%.1f%%\n"), fit$R2))
  }
  
  rnd <- NULL
  if (permute) {
    cat(.msg("\n--- Permutation Test ---\n", "\n--- 置换检验 ---\n"))
    rnd <- permutest(fit, iter = nperm, progbar = TRUE)
    cat(sprintf(.msg("  Permutations: %d\n", " 置换次数：%d\n"), nperm))
    cat(sprintf(.msg("  Model F-test (permuted) p-value: %.4f\n",
                     " 模型 F 检验（置换后）p 值：%.4f\n"), rnd$pval))
  }
  
  if (plot && !is.null(all.vars(mods)[1])) {
    covariate_name <- all.vars(mods)[1]
    x <- data[[covariate_name]]
    b_size <- 1 / sqrt(vi)
    plot(x, yi, cex = b_size * plot_options$cex, pch = plot_options$pch,
         col = plot_options$col, xlab = plot_options$xlab, ylab = plot_options$ylab,
         main = .msg("Bubble Plot (metareg equivalent)", "气泡图（等价于 metareg）"))
    lines(x, fitted(fit), col = "red", lwd = 2)
    legend("topleft", legend = .msg("Inverse variance weighted", "逆方差加权"), bty = "n", cex = 0.8)
  }
  
  cat(.msg("\nStata metareg equivalent: COMPLETE\n", "\nStata metareg 等价实现：完成\n"))
  
  return(invisible(list(model = fit, permutest = rnd)))
}

# 累积元回归: 按 year 等变量逐步纳入
run_cumulative_metareg <- function(yi, vi, mods, data, sort_by = "year") {
  library(metafor)
  library(ggplot2)
  
  order_idx <- order(data[[sort_by]])
  yi_s <- yi[order_idx]; vi_s <- vi[order_idx]; data_s <- data[order_idx, ]
  
  results <- list()
  for (i in 3:length(yi_s)) {
    fit_i <- rma(yi = yi_s[1:i], vi = vi_s[1:i],
                 mods = mods, data = data_s[1:i, ],
                 method = "REML", test = "knha")
    results[[i - 2]] <- data.frame(
      n_studies = i, estimate = fit_i$b[1], se = fit_i$se[1],
      ci_lb = fit_i$ci.lb[1], ci_ub = fit_i$ci.ub[1],
      pval = fit_i$pval[1], tau2 = fit_i$tau2)
  }
  
  results_df <- do.call(rbind, results)
  
  p <- ggplot(results_df, aes(x = seq_len(nrow(results_df)), y = estimate)) +
    geom_point(size = 3, color = "#0072B2") +
    geom_segment(aes(xend = seq_len(nrow(results_df)), y = ci_lb, yend = ci_ub),
                 size = 1, color = "#0072B2") +
    geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
    geom_vline(xintercept = nrow(results_df), linetype = "dotted", color = "gray50") +
    labs(title = .msg("Cumulative Meta-Regression", "累积元回归"),
         x = .msg("Step (sorted by covariate)", "步数（按协变量排序）"),
         y = .msg("Estimated Effect Size", "估计效应量")) +
    theme_minimal()
  
  print(p)
  
  return(list(cumulative_results = results_df, plot = p))
}

# ===================== mvmeta (Stata) =====================
run_mvmeta_R <- function(yi, V, study_id, outcome_type,
                         struct = "UN",
                         method = "REML",
                         test = "knha",
                         control = list()) {
  library(metafor)
  
  study_id <- factor(study_id); outcome_type <- factor(outcome_type)
  random <- ~ outcome_type | study_id
  
  fit <- rma.mv(yi = yi, V = V, random = random, struct = struct,
                data = data.frame(yi = yi, study_id = study_id, outcome_type = outcome_type),
                method = method, test = test, control = control)
  
  cat("================================================\n")
  cat(.msg(" Multivariate Meta-Analysis (Stata mvmeta equivalent)\n",
           " 多元元分析（等价于 Stata mvmeta）\n"))
  cat("================================================\n")
  cat(sprintf(.msg(" Structure: %s\n", " 结构：%s\n"), struct))
  cat(sprintf(.msg(" Estimation: %s\n", " 估计方法：%s\n"), method))
  cat(sprintf(.msg(" Studies: %d | Outcomes: %d\n", " 研究数：%d | 结局数：%d\n"),
              nlevels(study_id), nlevels(outcome_type)))
  cat(sprintf(.msg(" Total effect sizes: %d\n", " 总效应量数：%d\n"), length(yi)))
  cat(sprintf(.msg(" AIC: %.2f | BIC: %.2f\n", " AIC: %.2f | BIC: %.2f\n"),
              fit$fit.stats[4, "REML"], fit$fit.stats[5, "REML"]))
  
  cat(.msg("\nVariance components:\n", "\n方差成分：\n"))
  if (!is.null(fit$sigma2)) {
    cat(sprintf(.msg("  sigma2: %s\n", " sigma2：%s\n"), paste(round(fit$sigma2, 4), collapse = ", ")))
    cat(sprintf(.msg("  Correlation: %.3f\n", " 相关系数：%.3f\n"), fit$rho))
  } else {
    cat(sprintf(.msg("  tau2: %.4f\n", " tau2：%.4f\n"), fit$tau2))
  }
  
  print(summary(fit))
  cat(.msg("\nStata mvmeta equivalent: COMPLETE\n", "\nStata mvmeta 等价实现：完成\n"))
  
  return(invisible(fit))
}

# LR Test (模型比较)
run_lrtest_mvmeta <- function(...) {
  models <- list(...)
  library(metafor)
  
  cat("================================================\n")
  cat(.msg(" Likelihood Ratio Test\n", " 似然比检验\n"))
  cat("================================================\n")
  
  for (i in seq_along(models)) {
    for (j in seq_along(models)) {
      if (i >= j) next
      lr <- anova(models[[i]], models[[j]])
      cat(sprintf(.msg(" Model %d vs Model %d: Chi2 = %.2f, df = %d, p = %.4f\n",
                       " 模型 %d vs 模型 %d：Chi2 = %.2f, df = %d, p = %.4f\n"),
                  i, j, lr$QM, lr$ddf, lr$pval))
    }
  }
}

# Cochran's Q 检验（多元版）
run_Q_test_mvmeta <- function(fit) {
  library(metafor)
  
  cat("================================================\n")
  cat(.msg(" Cochran's Q Test (Multivariate)\n", " Cochran's Q 检验（多元）\n"))
  cat("================================================\n")
  
  Q_res <- anova(fit)
  cat(sprintf(.msg("Q = %.2f, df = %d, p = %.6f\n", "Q = %.2f, df = %d, p = %.6f\n"),
              Q_res$QM, Q_res$ddf, Q_res$pval))
  
  return(invisible(Q_res))
}

# 多元森林图
plot_mvmeta_forest <- function(fit, data, study_id_col, outcome_col) {
  library(ggplot2)
  pred <- predict(fit)
  plot_data <- data.frame(
    study_id = data[[study_id_col]], outcome_type = data[[outcome_col]],
    yi = data$yi, vi = data$vi, estimate = pred$pred,
    ci_lb = pred$ci.lb, ci_ub = pred$ci.ub, stringsAsFactors = FALSE)
  p <- ggplot(plot_data, aes(x = estimate, y = study_id, color = outcome_type)) +
    geom_point(size = 3) +
    geom_segment(aes(x = ci_lb, xend = ci_ub, y = study_id, yend = study_id), size = 1) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "red", size = 1) +
    labs(title = .msg("Multivariate Meta-Analysis Forest Plot", "多元 Meta 分析森林图"),
         x = .msg("Effect Size", "效应量"), y = .msg("Study", "研究")) +
    theme_minimal()
  return(p)
}

# ===================== 多臂研究协方差矩阵 =====================
build_V_matrix_CS <- function(study_id, yi, vi, mean_effect = NULL, n_control = NULL) {
  studies <- unique(study_id)
  V_list <- list()
  for (s in studies) {
    idx <- which(study_id == s); k <- length(idx)
    V <- matrix(0, k, k); diag(V) <- vi[idx]
    if (k > 1) {
      mu <- if (is.null(mean_effect)) mean(yi[idx]) else mean_effect
      for (i in 1:k) {
        for (j in 1:k) {
          if (i != j) {
            n0 <- if (!is.null(n_control)) n_control else max(k * 50, 30)
            V[i, j] <- 1 / n0
          }
        }
      }
    }
    V_list[[s]] <- V
  }
  return(V_list)
}
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
