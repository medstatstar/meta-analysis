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

# ===================== metareg (Stata) =====================
# Stata metareg 的核心功能:
#   1. 标准元回归 (REML/ML/DL/EB/HS/SJ/PM 估计)
#   2. Permutation test (metareg 标志性特性)
#   3. Bubble plot (效应量 vs 协变量，权重=1/vi)
#   4. Cumulative meta-regression (累积合并)
#   5. Knapp-Hartung 检验 (默认)
#
# R 等价实现:
#   rma(yi, vi, mods, method="", test="knha") + permutest(fit, iter=N)

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
  
  # 1. 拟合元回归模型
  fit <- rma(yi = yi, vi = vi, mods = mods, data = data,
             method = method, test = test, level = level)
  
  # 2. 输出结果
  cat("================================================\n")
  cat(" Meta-Regression (Stata metareg equivalent)\n")
  cat("================================================\n")
  print(summary(fit))
  
  cat("\nHeterogeneity:\n")
  cat(sprintf("  tau2 = %.4f | I² = %.1f%% | H² = %.2f\n",
              fit$tau2, fit$I2, fit$H2))
  
  # R² 量度（metafor 自动报告 R²）
  if (!is.null(fit$R2)) {
    cat(sprintf("  R² (heterogeneity explained): %.1f%%\n", fit$R2))
  }
  
  # 3. Permutation Test
  rnd <- NULL
  if (permute) {
    cat("\n--- Permutation Test ---\n")
    rnd <- permutest(fit, iter = nperm, progbar = TRUE)
    cat(sprintf("  Permutations: %d\n", nperm))
    cat(sprintf("  Model F-test (permuted) p-value: %.4f\n", rnd$pval))
  }
  
  # 4. Bubble Plot
  if (plot && !is.null(all.vars(mods)[1])) {
    covariate_name <- all.vars(mods)[1]
    x <- data[[covariate_name]]
    b_size <- 1 / sqrt(vi)
    
    plot(x, yi,
         cex = b_size * plot_options$cex,
         pch = plot_options$pch,
         col = plot_options$col,
         xlab = plot_options$xlab,
         ylab = plot_options$ylab,
         main = "Bubble Plot (metareg equivalent)")
    
    lines(x, fitted(fit), col = "red", lwd = 2)
    legend("topleft", legend = "Inverse variance weighted",
           bty = "n", cex = 0.8)
  }
  
  cat("\nStata metareg equivalent: COMPLETE\n")
  
  return(invisible(list(
    model = fit,
    permutest = rnd
  )))
}

# 累积元回归: 按 year 等变量逐步纳入
run_cumulative_metareg <- function(yi, vi, mods, data, sort_by = "year") {
  library(metafor)
  library(ggplot2)
  
  # 1. 按 sort_by 排序
  order_idx <- order(data[[sort_by]])
  yi_s <- yi[order_idx]
  vi_s <- vi[order_idx]
  data_s <- data[order_idx, ]
  
  # 2. 累积分析（至少 3 项研究）
  results <- list()
  for (i in 3:length(yi_s)) {
    fit_i <- rma(yi = yi_s[1:i], vi = vi_s[1:i],
                 mods = mods, data = data_s[1:i, ],
                 method = "REML", test = "knha")
    
    results[[i - 2]] <- data.frame(
      n_studies = i,
      estimate = fit_i$b[1],
      se = fit_i$se[1],
      ci_lb = fit_i$ci.lb[1],
      ci_ub = fit_i$ci.ub[1],
      pval = fit_i$pval[1],
      tau2 = fit_i$tau2
    )
  }
  
  results_df <- do.call(rbind, results)
  
  # 3. 累积森林图
  p <- ggplot(results_df,
             aes(x = seq_len(nrow(results_df)), y = estimate)) +
    geom_point(size = 3, color = "#0072B2") +
    geom_segment(aes(xend = seq_len(nrow(results_df)),
                     y = ci_lb, yend = ci_ub),
                 size = 1, color = "#0072B2") +
    geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
    geom_vline(xintercept = nrow(results_df), linetype = "dotted",
               color = "gray50") +
    labs(title = "Cumulative Meta-Regression",
         x = "Step (sorted by covariate)",
         y = "Estimated Effect Size") +
    theme_minimal()
  
  print(p)
  
  return(list(
    cumulative_results = results_df,
    plot = p
  ))
}

# ===================== mvmeta (Stata) =====================
# Stata mvmeta 的核心功能:
#   1. 多元元分析 (multiple outcomes/time points)
#   2. 研究内相关性 (within-study correlation)
#   3. 协方差结构选择 (UN/CS/HCS/AR1/ID/DIAG/FE)
#   4. REML/ML 估计
#   5. LR Test 模型比较
#
# R 等价实现:
#   rma.mv(yi, V, random = ~ outcome_type | study_id,
#          struct = "UN", method = "REML")

run_mvmeta_R <- function(yi, V, study_id, outcome_type,
                         struct = "UN",
                         method = "REML",
                         test = "knha",
                         control = list()) {
  library(metafor)
  
  study_id <- factor(study_id)
  outcome_type <- factor(outcome_type)
  
  # 构建随机效应结构
  random <- ~ outcome_type | study_id
  
  # 协方差分块处理
  fit <- rma.mv(
    yi = yi,
    V = V,
    random = random,
    struct = struct,
    data = data.frame(yi = yi, study_id = study_id,
                      outcome_type = outcome_type),
    method = method,
    test = test,
    control = control
  )
  
  # 输出结果
  cat("================================================\n")
  cat(" Multivariate Meta-Analysis (Stata mvmeta equivalent)\n")
  cat("================================================\n")
  cat(sprintf(" Structure: %s\n", struct))
  cat(sprintf(" Estimation: %s\n", method))
  cat(sprintf(" Studies: %d | Outcomes: %d\n",
              nlevels(study_id), nlevels(outcome_type)))
  cat(sprintf(" Total effect sizes: %d\n", length(yi)))
  cat(sprintf(" AIC: %.2f | BIC: %.2f\n",
              fit$fit.stats[4, "REML"], fit$fit.stats[5, "REML"]))
  
  cat("\nVariance components:\n")
  if (!is.null(fit$sigma2)) {
    cat(sprintf("  sigma2: %s\n", paste(round(fit$sigma2, 4), collapse = ", ")))
    cat(sprintf("  Correlation: %.3f\n", fit$rho))
  } else {
    cat(sprintf("  tau2: %.4f\n", fit$tau2))
  }
  
  print(summary(fit))
  cat("\nStata mvmeta equivalent: COMPLETE\n")
  
  return(invisible(fit))
}

# LR Test (模型比较)
run_lrtest_mvmeta <- function(...) {
  models <- list(...)
  library(metafor)
  
  cat("================================================\n")
  cat(" Likelihood Ratio Test\n")
  cat("================================================\n")
  
  for (i in seq_along(models)) {
    for (j in seq_along(models)) {
      if (i >= j) next
      lr <- anova(models[[i]], models[[j]])
      cat(sprintf(" Model %d vs Model %d: Chi2 = %.2f, df = %d, p = %.4f\n",
                  i, j, lr$QM, lr$ddf, lr$pval))
    }
  }
}

# Cochran's Q 检验（多元版）
run_Q_test_mvmeta <- function(fit) {
  library(metafor)
  
  cat("================================================\n")
  cat(" Cochran's Q Test (Multivariate)\n")
  cat("================================================\n")
  
  Q_res <- anova(fit)
  cat(sprintf("Q = %.2f, df = %d, p = %.6f\n",
              Q_res$QM, Q_res$ddf, Q_res$pval))
  
  return(invisible(Q_res))
}

# 多元森林图
plot_mvmeta_forest <- function(fit, data, study_id_col,
                                outcome_col) {
  library(ggplot2)
  
  pred <- predict(fit)
  
  plot_data <- data.frame(
    study_id = data[[study_id_col]],
    outcome_type = data[[outcome_col]],
    yi = data$yi,
    vi = data$vi,
    estimate = pred$pred,
    ci_lb = pred$ci.lb,
    ci_ub = pred$ci.ub,
    stringsAsFactors = FALSE
  )
  
  p <- ggplot(plot_data,
              aes(x = estimate, y = study_id,
                  color = outcome_type)) +
    geom_point(size = 3) +
    geom_segment(aes(x = ci_lb, xend = ci_ub, y = study_id,
                     yend = study_id),
                 size = 1) +
    geom_vline(xintercept = 0, linetype = "dashed",
               color = "red", size = 1) +
    labs(title = "Multivariate Meta-Analysis Forest Plot",
         x = "Effect Size", y = "Study") +
    theme_minimal()
  
  return(p)
}

# ===================== 多臂研究协方差矩阵 =====================
# Stata mvmeta 自动构建 V 矩阵，R 需手动构建
# 公式: Cov(d_i, d_j) = sigma_k / n_0 + (d_i * d_j / (2 * n_total))

build_V_matrix_CS <- function(study_id, yi, vi, mean_effect = NULL, n_control = NULL) {
  studies <- unique(study_id)
  V_list <- list()
  
  for (s in studies) {
    idx <- which(study_id == s)
    k <- length(idx)
    V <- matrix(0, k, k)
    diag(V) <- vi[idx]
    
    if (k > 1) {
      mu <- if (is.null(mean_effect)) mean(yi[idx]) else mean_effect
      
      for (i in 1:k) {
        for (j in 1:k) {
          if (i != j) {
            # Cov(d_i, d_j) ≈ 1/n_control (standard approximation)
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
