# ============================================================================
# Meta-Analysis Core Engine
#  核心引擎：覆盖所有标准元分析流程
#  用户可直接调用或修改参数
# ============================================================================

# --- 0. 环境准备 ---
prepare_meta_environment <- function(advanced = TRUE) {
  #' 检查并安装所需的 R 包
  #' @param advanced 是否安装可选增强包
  
  core_pkgs <- c("metafor", "meta", "netmeta", "ggplot2", "gridExtra")
  optional_pkgs <- c("metasens", "bayesmeta", "metaviz", "robvis", "gt")
  
  all_pkgs <- if (advanced) c(core_pkgs, optional_pkgs) else core_pkgs
  
  for (pkg in all_pkgs) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      install.packages(pkg, repos = "https://cran.r-project.org")
    }
  }
  
  if (!requireNamespace("dmetar", quietly = TRUE)) {
    if (!requireNamespace("remotes", quietly = TRUE)) {
      install.packages("remotes")
    }
    remotes::install_github("MathiasHarrer/dmetar")
  }
  
  message("Meta-analysis environment ready!")
}

# --- 1. 效应量计算 ---
calculate_effect_size <- function(data, outcome_type, measure = NULL) {
  #' 计算各种效应量
  #' @param data 数据框
  #' @param outcome_type "dichotomous" 或 "continuous"
  #' @param measure 效应量类型
  
  library(metafor)
  library(meta)
  
  if (outcome_type == "dichotomous") {
    # 二分类数据：OR, RR, RD
    if (is.null(measure) || measure == "OR") {
      es <- escalc(measure = "OR",
                   ai = data$event_exp,
                   bi = data$n_exp - data$event_exp,
                   ci = data$event_ctrl,
                   di = data$n_ctrl - data$event_ctrl)
    } else if (measure == "RR") {
      es <- escalc(measure = "RR",
                   ai = data$event_exp,
                   bi = data$n_exp - data$event_exp,
                   ci = data$event_ctrl,
                   di = data$n_ctrl - data$event_ctrl)
    } else if (measure == "RD") {
      es <- escalc(measure = "RD",
                   ai = data$event_exp,
                   bi = data$n_exp - data$event_exp,
                   ci = data$event_ctrl,
                   di = data$n_ctrl - data$event_ctrl)
    } else if (measure == "PETO") {
      es <- escalc(measure = "PETO",
                   ai = data$event_exp,
                   bi = data$n_exp - data$event_exp,
                   ci = data$event_ctrl,
                   di = data$n_ctrl - data$event_ctrl)
    }
  } else if (outcome_type == "continuous") {
    # 连续型数据：SMD, MD, ROM
    if (is.null(measure) || measure == "SMD") {
      es <- escalc(measure = "SMD",
                   n1i = data$n_exp, m1i = data$mean_exp, sd1i = data$sd_exp,
                   n2i = data$n_ctrl, m2i = data$mean_ctrl, sd2i = data$sd_ctrl)
    } else if (measure == "MD") {
      es <- escalc(measure = "MD",
                   n1i = data$n_exp, m1i = data$mean_exp, sd1i = data$sd_exp,
                   n2i = data$n_ctrl, m2i = data$mean_ctrl, sd2i = data$sd_ctrl)
    } else if (measure == "ROM") {
      es <- escalc(measure = "ROM",
                   n1i = data$n_exp, m1i = data$mean_exp, sd1i = data$sd_exp,
                   n2i = data$n_ctrl, m2i = data$mean_ctrl, sd2i = data$sd_ctrl)
    }
  }
  
  return(es)
}

# --- 2. 核心元分析 ---
run_meta_analysis <- function(es_data, method = "REML", 
                              random_effects = TRUE,
                              test_type = "knha") {
  #' 执行核心元分析模型
  #' @param es_data escalc() 输出的效应量数据
  #' @param method 估计方法: "FE", "REML", "ML", "DL", "HK", "SJ", "HS"
  #' @param random_effects 是否使用随机效应模型
  #' @test_type 小样本校正 "knha" (Hartung-Knapp)
  
  library(metafor)
  
  if (random_effects) {
    method <- ifelse(method == "FE", "REML", method)
    
    res <- rma(yi = yi, vi = vi,
               data = es_data,
               method = method,
               test = test_type)
  } else {
    res <- rma(yi = yi, vi = vi,
               data = es_data,
               method = "FE")
  }
  
  # 计算预测区间
  res$prediction <- predict(res)
  
  return(res)
}

# --- 3. 异质性分析 ---
analyze_heterogeneity <- function(model_result) {
  #' 提取和解释异质性统计量
  
  stats <- list(
    I2 = model_result$I2,
    H2 = model_result$H2,
    tau2 = model_result$tau2,
    Q = model_result$QE,
    df = model_result$k - 1,
    p_Q = model_result$pval.Q
  )
  
  # 解释
  stats$interpretation <- ifelse(
    stats$I2 < 25, "低异质性",
    ifelse(stats$I2 < 50, "中等异质性",
           ifelse(stats$I2 < 75, "高异质性", "非常高异质性"))
  )
  
  return(stats)
}

# --- 4. 发表偏倚分析 ---
analyze_publication_bias <- function(es_data, model_result) {
  #' 发表偏倚综合评估
  
  library(metafor)
  
  results <- list()
  
  # Egger 回归检验
  if (nrow(es_data) >= 3) {
    egg <- regtest(model_result)
    results$egger <- list(z = egg$zval, p = egg$pval)
  }
  
  # Begg 秩相关检验
  if (nrow(es_data) >= 3) {
    beg <- ranktest(model_result)
    results$begg <- list(z = beg$zval, p = beg$pval)
  }
  
  # 剪补法
  if (nrow(es_data) >= 5)
    tf <- trimfill(model_result)
    results$trimfill <- list(
      k0 = tf$k0,
      pooled_est = tf$beta[1],
      ci_lb = tf$ci.lb,
      ci_ub = tf$ci.ub
    )
  }
  
  # 失安全系数（Rosenberg 方法）
  # 使用 meta::fsn()
  
  return(results)
}

# --- 5. 亚组分析 ---
run_subgroup_analysis <- function(es_data, group_var) {
  #' 按分组变量进行亚组分析
  
  library(metafor)
  
  # 确保分组变量是因子
  es_data[[group_var]] <- as.factor(es_data[[group_var]])
  
  # 运行无截距模型（获取各亚组合并效应）
  model <- rma(yi = yi, vi = vi,
               mods = as.formula(paste("~", group_var, "- 1")),
               data = es_data,
               method = "REML",
               test = "knha")
  
  # 组间异质性检验
  wald_test <- anova(model, btt = 2:length(unique(es_data[[group_var]])))
  
  return(list(
    model = model,
    subgroup_effects = data.frame(
      subgroup = levels(es_data[[group_var]]),
      estimate = model$beta,
      se = model$se,
      ci_lb = model$ci.lb,
      ci_ub = model$ci.ub
    ),
    between_group_Q = Wald_test$QM,
    between_group_p = Wald_test$pval
  ))
}

# --- 6. 元回归 ---
run_meta_regression <- function(es_data, covariates) {
  #' 元回归分析
  
  library(metafor)
  
  # 构建模型公式
  formula_str <- paste("yi ~", paste(covariates, collapse = " + "))
  formula <- as.formula(formula_str)
  
  model <- rma(formula,
               vi = vi,
               data = es_data,
               method = "REML",
               test = "knha")
  
  # 气泡图
  if (length(covariates) == 1) {
    bubble_plot <- bubble(model,
                          xlab = covariates[1],
                          ylab = "Effect Size",
                          cex = 1 / sqrt(es_data$vi))
  }
  
  return(list(
    model = model,
    bubble_plot = if (exists("bubble_plot")) bubble_plot else NULL
  ))
}

# --- 7. 敏感性分析 ---
run_sensitivity_analysis <- function(es_data, analysis_type = "all") {
  #' 敏感性分析综合函数
  
  library(metafor)
  
  model_reml <- rma(yi = yi, vi = vi, data = es_data, method = "REML")
  
  results <- list()
  
  if (analysis_type %in% c("all", "leave1out")) {
    # Leave-one-out
    loo <- leave1out(model_reml)
    results$leave1out <- data.frame(
      study = es_data$study,
      estimate = loo$estimate,
      se = loo$se,
      ci_lb = loo$ci.lb,
      ci_ub = loo$ci_ub,
      I2 = loo$I2
    )
  }
  
  if (analysis_type %in% c("all", "quality")) {
    # 按质量分组（如果数据中有质量变量）
    if ("quality" %inames(es_data)) {
      high_q <- es_data[es_data$quality == "low risk" | es_data$quality >= 6, ]
      if (nrow(high_q) >= 3) {
        high_q_model <- rma(yi = yi, vi = vi, data = high_q, method = "REML")
        results$high_quality <- high_q_model
      }
    }
  }
  
  if (analysis_type %in% c("all", "model_comparison")) {
    # 多种模型对比
    models <- list()
    
    models$DL <- rma(yi = yi, vi = vi, data = es_data, method = "DL")
    models$REML <- rma(yi = yi, vi = vi, data = es_data, method = "REML")
    models$ML <- rma(yi = yi, vi = vi, data = es_data, method = "ML")
    models$HK <- rma(yi = yi, vi = vi, data = es_data, method = "HK")
    models$FE <- rma(yi = yi, vi = vi, data = es_data, method = "FE")
    
    # 汇总表
    model_summary <- data.frame(
      Method = names(models),
      Estimate = sapply(models, function(m) m$beta[1]),
      CI_LB = sapply(models, function(m) m$ci.lb),
      CI_UB = sapply(models, function(m) m$ci.ub),
      tau2 = sapply(models, function(m) m$tau2),
      I2 = sapply(models, function(m) m$I2)
    )
    
    results$model_comparison <- model_summary
  }
  
  return(results)
}

# --- 8. 森林图（ggplot 可编辑版本） ---
create_forest_plot <- function(es_data, model_result,
                               style = "revman",
                               xlab = "Effect Size",
                               title = "Forest Plot") {
  #' 创建出版级森林图（ggplot2 对象，完全可编辑）
  #' @param style 风格: "revman", "lancet", "jama", "minimal"
  
  library(ggplot2)
  
  # 准备数据
  study_order <- order(es_data$yi)
  
  plot_data <- data.frame(
    study = factor(es_data$study, levels = es_data$study[study_order]),
    yi = es_data$yi,
    lower = es_data$yi - 1.95 * sqrt(es_data$vi),
    upper = es_data$yi + 1.95 * sqrt(es_data$vi),
    weight = model_result$w[study_order]
  )
  
  # 添加合并效应行
  pooled <- data.frame(
    study = "Pooled Effect",
    yi = model_result$beta[1],
    lower = model_result$ci.lb,
    upper = model_result$ci.ub,
    weight = NA
  )
  
  plot_data <- rbind(plot_data, pooled)
  
  # 风格设置
  if (style == "revman") {
    p <- ggplot(plot_data, aes(y = study)) +
      geom_vline(xintercept = 0, linetype = "dashed", color = "grey50") +
      geom_errorbarh(aes(xmin = lower, xmax = upper), height = 0.3, size = 0.5) +
      geom_point(aes(x = yi, size = weight), shape = 15) +
      scale_size(range = c(2, 6), guide = "none") +
      labs(x = xlab, y = "", title = title) +
      theme_classic() +
      theme(plot.title = element_text(face = "bold"))
  } else if (style == "minimal") {
    p <- ggplot(plot_data, aes(y = study)) +
      geom_vline(xintercept = 0, linetype = "dashed", color = "grey50") +
      geom_errorbarh(aes(xmin = lower, xmax = upper), height = 0.3, size = 0.5,
                     color = "steelblue") +
      geom_point(aes(x = yi), color = "steelblue", size = 2) +
      labs(x = xlab, y = "", title = title) +
      theme_minimal()
  }
  
  # 合并效应菱形标记（可选）
  p
  
  return(p)
}

# --- 9. 漏斗图 ---
create_funnel_plot <- function(model_result,
                               style = "classic") {
  #' 创建漏斗图（ggplot2）
  
  library(ggplot2)
  
  # 使用 metafor 默认 funnel
  # 或 ggplot2 版本（更灵活）
  
  data_es <- model_result$yi
  data_se <- sqrt(model_result$vi)
  
  plot_data <- data.frame(
    yi = data_es,
    se = data_se,
    study = rownames(model_result$data) %||% paste0("Study", seq_along(data_es))
  )
  
  # 漏斗边界
  pooled <- model_result$beta[1]
  
  p <- ggplot(plot_data, aes(x = yi, y = 1/se)) +
    geom_point(size = 3, alpha = 0.7, color = "steelblue") +
    geom_vline(xintercept = pooled, color = "red", linetype = "dashed") +
    geom_segment(aes(x = pooled - 1.96 * se, xend = pooled + 1.96 * se,
                     y = 1/se, yend = 1/se),
                 color = "grey60", alpha = 0.3) +
    labs(x = "Effect Size", y = "Precision (1/SE)",
         title = "Funnel Plot") +
    theme_minimal() +
    coord_flip()
  
  return(p)
}

# --- 10. 结果汇总报告 ---
generate_results_summary <- function(model_result, 
                                     heterogeneity,
                                     sensitivity = NULL,
                                     pub_bias = NULL,
                                     model_name = "Random-Effects (REML)") {
  #' 生成结构化结果摘要
  
  summary_text <- sprintf("
========================================
 Meta-Analysis Results Summary
========================================

Model: %s
K studies = %d

POOLED EFFECT:
  Estimate: %.3f
  95%% CI: [%.3f, %.3f]
  z = %.3f, p = %.4f

HETEROGENEITY:
  I² = %.1f%% (%s)
  τ² = %.4f
  Q = %.3f, df = %d, p = %.4f

PREDICTION INTERVAL:
  [%.3f, %.3f]

",
    model_name,
    model_result$k,
    model_result$beta[1],
    model_result$ci.lb,
    model_result$ci.ub,
    model_result$zval,
    model_result$pval,
    heterogeneity$I2,
    heterogeneity$interpretation,
    heterogeneity$tau2,
    heterogeneity$Q,
    heterogeneity$df,
    heterogeneity$p_Q,
    model_result$prediction$pred - 1.96 * sqrt(model_result$prediction$se^2 + model_result$tau2),
    model_result$prediction$pred + 1.96 * sqrt(model_result$prediction$se^2 + model_result$tau2)
  )
  
  if (!is.null(pub_bias)) {
    summary_text <- paste0(summary_text, "\nPUBLICATION BIAS:\n")
    if (!is.null(pub_bias$egger)) {
      summary_text <- paste0(summary_text, sprintf(
        "  Egger test: z = %.3f, p = %.4f\n",
        pub_bias$egger$z, pub_bias$egger$p))
    }
  }
  
  return(summary_text)
}
