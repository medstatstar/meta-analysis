# ============================================================================
# Meta-Analysis Core Engine
#  核心引擎：覆盖所有标准元分析流程
#  用户可直接调用或修改参数
# ============================================================================

# --- 0. 环境准备 ---
prepare_meta_environment <- function(advanced = TRUE) {
  #' 检查并安装所需的 R 包
  #' @param advanced 是否安装可选增强包
  
  core_pkgs <- c("metafor", "meta", "netmeta", "ggplot2", "gridExtra", "svglite")
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
calculate_effect_size <- function(data, outcome_type, measure = NULL, cols = NULL) {
  #' 计算各种效应量（列名大小写不敏感）
  #' @param data 数据框
  #' @param outcome_type "dichotomous" | "continuous" | "rate" (IRR 率比)
  #' @param measure OR/RR/RD/PETO | SMD/MD/ROM | IRR
  #' @param cols 命名列表，逻辑角色 -> 实际列名，如 list(a="A", b="B", c="C", d="D")

  library(metafor)
  library(meta)

  data <- as.data.frame(data)
  names(data) <- tolower(names(data))   # 列名大小写不敏感
  get_col <- function(role, default) {
    if (!is.null(cols) && role %in% names(cols)) data[[tolower(cols[[role]])]]
    else data[[tolower(default)]]
  }

  if (outcome_type == "dichotomous") {
    a  <- get_col("event_exp", "event_exp"); n1 <- get_col("n_exp", "n_exp")
    c_ <- get_col("event_ctrl", "event_ctrl"); n2 <- get_col("n_ctrl", "n_ctrl")
    if (is.null(measure) || measure == "OR") {
      es <- escalc(measure = "OR", ai = a, bi = n1 - a, ci = c_, di = n2 - c_)
    } else if (measure == "RR") {
      es <- escalc(measure = "RR", ai = a, bi = n1 - a, ci = c_, di = n2 - c_)
    } else if (measure == "RD") {
      es <- escalc(measure = "RD", ai = a, bi = n1 - a, ci = c_, di = n2 - c_)
    } else if (measure == "PETO") {
      es <- escalc(measure = "PETO", ai = a, bi = n1 - a, ci = c_, di = n2 - c_)
    } else stop("dichotomous measure not supported: ", measure)

  } else if (outcome_type == "continuous") {
    if (is.null(measure) || measure == "SMD") {
      es <- escalc(measure = "SMD",
                   n1i = get_col("n_exp","n_exp"), m1i = get_col("mean_exp","mean_exp"),
                   sd1i = get_col("sd_exp","sd_exp"), n2i = get_col("n_ctrl","n_ctrl"),
                   m2i = get_col("mean_ctrl","mean_ctrl"), sd2i = get_col("sd_ctrl","sd_ctrl"))
    } else if (measure == "MD") {
      es <- escalc(measure = "MD",
                   n1i = get_col("n_exp","n_exp"), m1i = get_col("mean_exp","mean_exp"),
                   sd1i = get_col("sd_exp","sd_exp"), n2i = get_col("n_ctrl","n_ctrl"),
                   m2i = get_col("mean_ctrl","mean_ctrl"), sd2i = get_col("sd_ctrl","sd_ctrl"))
    } else if (measure == "ROM") {
      es <- escalc(measure = "ROM",
                   n1i = get_col("n_exp","n_exp"), m1i = get_col("mean_exp","mean_exp"),
                   sd1i = get_col("sd_exp","sd_exp"), n2i = get_col("n_ctrl","n_ctrl"),
                   m2i = get_col("mean_ctrl","mean_ctrl"), sd2i = get_col("sd_ctrl","sd_ctrl"))
    } else stop("continuous measure not supported: ", measure)

  } else if (outcome_type == "rate") {
    # 率比 (Incidence Rate Ratio): a/c=事件数, b/d=人时(分母)
    a  <- get_col("a", "a"); b <- get_col("b", "b")
    c_ <- get_col("c", "c"); d <- get_col("d", "d")
    if (is.null(measure)) measure <- "IRR"
    if (measure == "IRR") {
      es <- escalc(measure = "IRR", x1i = a, t1i = b, x2i = c_, t2i = d)
    } else stop("rate measure not supported: ", measure)

  } else if (outcome_type == "correlation") {
    # 相关系数 (Pearson r) -> Fisher z 变换
    r <- get_col("r", "r"); n <- get_col("n", "n")
    if (is.null(measure) || measure == "ZCOR") {
      es <- escalc(measure = "ZCOR", ri = r, ni = n)
    } else stop("correlation measure not supported: ", measure)

  } else if (outcome_type == "single_proportion") {
    # 单组率 (proportion)：logit 变换 (PLO) 稳健；PR 为原始比例
    x <- get_col("events", "events"); n <- get_col("n", "n")
    if (is.null(measure) || measure == "PLO") {
      es <- escalc(measure = "PLO", xi = x, ni = n)
    } else if (measure == "PR") {
      es <- escalc(measure = "PR", xi = x, ni = n)
    } else stop("single_proportion measure not supported: ", measure)

  } else if (outcome_type == "single_mean") {
    # 单组均值 (mean)
    m <- get_col("mean", "mean"); s <- get_col("sd", "sd"); n <- get_col("n", "n")
    if (is.null(measure) || measure == "MN") {
      es <- escalc(measure = "MN", mi = m, sdi = s, ni = n)
    } else stop("single_mean measure not supported: ", measure)

  } else {
    stop("Unknown outcome_type: ", outcome_type)
  }

  # 保留原始数据中的所有协变量列（供亚组/元回归/敏感性分析使用）
  extras <- setdiff(names(data), names(es))
  if (length(extras) > 0) es <- cbind(es, data[, extras, drop = FALSE])
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
  res$method <- method
  res$random <- random_effects
  res$test_type <- test_type

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
    p_Q = if (is.null(model_result$QEp)) NA else model_result$QEp
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
  if (nrow(es_data) >= 5) {
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
  #' 返回：各组独立合并效应 + 组间异质性检验（正确做法）
  
  library(metafor)
  
  if (!group_var %in% names(es_data))
    stop("group_var not found: ", group_var)
  
  # 确保分组变量是因子
  es_data[[group_var]] <- as.factor(es_data[[group_var]])
  levels <- levels(es_data[[group_var]])
  
  # 各组独立合并效应（每组单独跑 rma，最直观）
  sub <- lapply(levels, function(lv) {
    sub_dat <- es_data[es_data[[group_var]] == lv, , drop = FALSE]
    m <- rma(yi = yi, vi = vi, data = sub_dat, method = "REML", test = "knha")
    data.frame(subgroup = lv, k = m$k,
               estimate = m$beta[1], se = m$se,
               ci_lb = m$ci.lb, ci_ub = m$ci.ub, I2 = m$I2)
  })
  subgroup_effects <- do.call(rbind, sub)
  
  # 组间异质性检验：带截距模型，btt=2:k 检验“非参照组 vs 参照组”
  model <- rma(yi = yi, vi = vi,
               mods = as.formula(paste("~", group_var)),
               data = es_data,
               method = "REML",
               test = "knha")
  wald_test <- anova(model, btt = 2:length(levels))
  
  return(list(
    model = model,
    subgroup_effects = subgroup_effects,
    between_group_Q = wald_test$QM,
    between_group_p = wald_test$QMp
  ))
}

# --- 6. 元回归 ---
run_meta_regression <- function(es_data, covariates) {
  #' 元回归分析
  
  library(metafor)
  library(ggplot2)
  
  # 构建模型公式
  formula_str <- paste("yi ~", paste(covariates, collapse = " + "))
  formula <- as.formula(formula_str)
  
  model <- rma(formula,
               vi = vi,
               data = es_data,
               method = "REML",
               test = "knha")
  
  # 气泡图（手动 ggplot，避免依赖 metafor::bubble 的 rma.uni 方法）
  bubble_plot <- NULL
  if (length(covariates) == 1) {
    cv <- es_data[[covariates[1]]]
    df <- data.frame(
      x  = cv,
      y  = es_data$yi,
      lo = es_data$yi - 1.96 * sqrt(es_data$vi),
      hi = es_data$yi + 1.96 * sqrt(es_data$vi),
      w  = 1 / sqrt(es_data$vi)
    )
    bubble_plot <- ggplot(df, aes(x = x, y = y)) +
      geom_errorbar(aes(ymin = lo, ymax = hi), width = 0.1,
                    color = "#2a3950", linewidth = 0.5) +
      geom_point(aes(size = w), shape = 15, color = "#2a3950") +
      scale_size(guide = "none") +
      labs(x = covariates[1], y = "Effect Size (95% CI)") +
      theme_minimal()
  }
  
  return(list(
    model = model,
    bubble_plot = bubble_plot
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
    if ("quality" %in% names(es_data)) {
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
    
    models$DL   <- rma(yi = yi, vi = vi, data = es_data, method = "DL")
    models$REML <- rma(yi = yi, vi = vi, data = es_data, method = "REML")
    models$ML   <- rma(yi = yi, vi = vi, data = es_data, method = "ML")
    models$FE   <- rma(yi = yi, vi = vi, data = es_data, method = "FE")
    
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
  
  if (analysis_type %in% c("all", "cumul")) {
    # 累积 Meta（按数据顺序逐个加入）
    k <- nrow(es_data)
    cum_est <- cum_lb <- cum_ub <- cum_I2 <- numeric(0)
    for (i in seq_len(k)) {
      cm <- rma(yi = yi, vi = vi, data = es_data[seq_len(i), , drop = FALSE],
                method = "REML")
      cum_est <- c(cum_est, cm$beta[1])
      cum_lb  <- c(cum_lb, cm$ci.lb)
      cum_ub  <- c(cum_ub, cm$ci.ub)
      cum_I2  <- c(cum_I2, cm$I2)
    }
    results$cumul <- data.frame(
      study    = es_data$study,
      estimate = cum_est, ci_lb = cum_lb, ci_ub = cum_ub, I2 = cum_I2
    )
  }
  
  return(results)
}

# --- 8. 森林图（ggplot 可编辑版本） ---
create_forest_plot <- function(es_data, model_result,
                               style = "revman",
                               transform = NULL,
                               xlab = NULL,
                               title = "Forest Plot") {
  #' 出版级森林图（ggplot2，可编辑 SVG）。OR/RR/IRR 自动指数化显示。
  #' @param transform "exp"(参考线=1) 或 "none"(参考线=0)
  library(ggplot2)

  if (is.null(transform)) transform <- "none"
  f <- switch(transform, exp = exp, tanh = tanh, plogis = plogis, identity)
  ref <- switch(transform, exp = 1, tanh = 0, plogis = 0.5, identity = 0)

  od <- order(es_data$yi, decreasing = TRUE)
  yi <- es_data$yi[od]; vi <- es_data$vi[od]; lab <- es_data$study[od]
  w  <- (1 / vi)[od]
  k  <- length(yi)

  d <- data.frame(
    label = c(lab, "Pooled"),
    ypos  = c((k + 1):2, 1),
    est   = c(f(yi), f(model_result$beta[1])),
    lo    = c(f(yi - 1.96 * sqrt(vi)), f(model_result$ci.lb)),
    hi    = c(f(yi + 1.96 * sqrt(vi)), f(model_result$ci.ub)),
    w     = c(w, NA)
  )

  if (is.null(xlab))
    xlab <- switch(transform,
                   exp    = "Effect Ratio (95% CI)",
                   tanh   = "Correlation r (95% CI)",
                   plogis = "Proportion (95% CI)",
                   "Effect Size (95% CI)")

  p <- ggplot(d, aes(y = ypos)) +
    geom_vline(xintercept = ref, linetype = "dashed", color = "grey50", linewidth = 0.6) +
    geom_errorbar(aes(xmin = lo, xmax = hi, y = ypos), orientation = "y",
                  width = 0.25, linewidth = 0.5, color = "#2a3950") +
    geom_point(data = d[d$label != "Pooled", ], aes(x = est, size = w),
               shape = 15, color = "#2a3950") +
    scale_size(range = c(2, 6), guide = "none") +
    geom_point(data = d[d$label == "Pooled", ], aes(x = est), shape = 23,
               fill = "#0f9b81", color = "#0f9b81", size = 5) +
    scale_y_continuous(breaks = d$ypos, labels = d$label,
                       limits = c(0.5, k + 1.5)) +
    annotate("text", x = max(d$hi) * 1.03, y = 1,
             label = sprintf("%.2f [%.2f, %.2f]", f(model_result$beta[1]),
                             f(model_result$ci.lb), f(model_result$ci.ub)),
             hjust = 0, size = 3, fontface = "bold", color = "#0f9b81") +
    labs(x = xlab, y = "", title = title) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"),
          panel.grid.major.y = element_blank(),
          axis.text.y = element_text(size = 10))
  return(p)
}

# --- 9. 漏斗图 ---
create_funnel_plot <- function(model_result,
                               style = "classic",
                               transform = NULL,
                               title = "Funnel Plot") {
  #' 创建漏斗图（ggplot2）。自动指数化 + 标注 Egger/Begg。
  library(ggplot2)
  library(metafor)

  if (is.null(transform)) transform <- "none"
  f <- switch(transform, exp = exp, tanh = tanh, plogis = plogis, identity)

  yi <- model_result$yi
  se <- sqrt(model_result$vi)
  pooled <- model_result$beta[1]
  ref_null <- switch(transform, exp = 1, tanh = 0, plogis = 0.5, identity = 0)

  eg <- tryCatch(regtest(model_result), error = function(e) NULL)
  bg <- tryCatch(ranktest(model_result), error = function(e) NULL)
  sub <- sprintf("Egger p = %.3f, Begg p = %.3f",
                 ifelse(is.null(eg), NA, eg$pval),
                 ifelse(is.null(bg), NA, bg$pval))

  d <- data.frame(yi = yi, se = se, inv = 1 / se)
  p <- ggplot(d, aes(x = f(yi), y = inv)) +
    geom_vline(xintercept = f(pooled), color = "#c0392b", linetype = "dashed", linewidth = 0.8) +
    geom_vline(xintercept = ref_null, color = "grey60", linewidth = 0.4) +
    geom_segment(aes(x = f(pooled - 1.96 * se), xend = f(pooled + 1.96 * se),
                     y = inv, yend = inv), color = "#a8d5f5", linewidth = 0.3) +
    geom_point(size = 3, color = "#2a3950", alpha = 0.85) +
    labs(x = if (transform == "exp") "Effect Ratio" else "Effect Size",
         y = "Precision (1/SE)", title = title, subtitle = sub) +
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
  
  r <- model_result
  h <- heterogeneity
  pred <- r$prediction
  pred_lo <- if (is.null(pred$cr.lb)) pred$pred - 1.96 * sqrt(pred$se^2 + r$tau2) else pred$cr.lb
  pred_hi <- if (is.null(pred$cr.ub)) pred$pred + 1.96 * sqrt(pred$se^2 + r$tau2) else pred$cr.ub

  summary_text <- paste(c(
    "========================================",
    " Meta-Analysis Results Summary",
    "========================================",
    "",
    paste0("Model: ", model_name),
    paste0("K studies = ", r$k),
    "",
    "POOLED EFFECT:",
    paste0("  Estimate: ", sprintf("%.3f", r$beta[1])),
    paste0("  95% CI: [", sprintf("%.3f", r$ci.lb), ", ", sprintf("%.3f", r$ci.ub), "]"),
    paste0("  z = ", sprintf("%.3f", r$zval), ", p = ", sprintf("%.4f", r$pval)),
    "",
    "HETEROGENEITY:",
    paste0("  I2 = ", sprintf("%.1f", h$I2), "% (", h$interpretation, ")"),
    paste0("  tau2 = ", sprintf("%.4f", h$tau2)),
    paste0("  Q = ", sprintf("%.3f", h$Q), ", df = ", h$df, ", p = ", sprintf("%.4f", h$p_Q)),
    "",
    "PREDICTION INTERVAL:",
    paste0("  [", sprintf("%.3f", pred_lo), ", ", sprintf("%.3f", pred_hi), "]")
  ), collapse = "\n")
  
  if (!is.null(pub_bias)) {
    summary_text <- paste0(summary_text, "\n\nPUBLICATION BIAS:\n")
    if (!is.null(pub_bias$egger))
      summary_text <- paste0(summary_text, sprintf(
        "  Egger test: z = %.3f, p = %.4f\n",
        pub_bias$egger$z, pub_bias$egger$p))
    if (!is.null(pub_bias$begg))
      summary_text <- paste0(summary_text, sprintf(
        "  Begg test:  z = %.3f, p = %.4f\n",
        pub_bias$begg$z, pub_bias$begg$p))
  }
  
  return(summary_text)
}

# --- 11. 统一分析入口（推荐） ---
ma_analyze <- function(data, type, measure = NULL, cols = NULL,
                       method = "REML", test = "knha",
                       random = TRUE, label_col = NULL) {
  #' 统一 Meta 分析入口：效应量计算 -> 模型拟合 -> ma_result 对象
  #' @param type "binary"/"dichotomous" | "continuous" | "rate"/"irr" |
  #'             "precomp"(需 yi+vi 或 yi+se 或 effect+lower+upper) |
  #'             "survival"(需 loghr+se 或 hr+lower+upper) |
  #'             "correlation"(需 r+n, Fisher z) |
  #'             "single_proportion"/"proportion"(需 events+n) |
  #'             "single_mean"/"mean"(需 mean+sd+n)
  #' @param cols 列名映射，见 calculate_effect_size
  #' @param label_col 研究标签列名（可选）
  
  library(metafor)
  data <- as.data.frame(data)
  if (!is.null(label_col)) {
    lc <- tolower(label_col)
    if (lc %in% tolower(names(data))) data$study <- as.character(data[[lc]])
  }
  names(data) <- tolower(names(data))
  if (is.null(data$study))
    data$study <- paste0("Study ", seq_len(nrow(data)))
  
  ot <- tolower(type)
  transform <- "none"
  
  if (ot %in% c("binary", "dichotomous")) {
    ot <- "dichotomous"; if (is.null(measure)) measure <- "OR"; transform <- "exp"
    es <- calculate_effect_size(data, "dichotomous", measure = measure, cols = cols)
  } else if (ot == "continuous") {
    if (is.null(measure)) measure <- "SMD"
    es <- calculate_effect_size(data, "continuous", measure = measure, cols = cols)
  } else if (ot %in% c("rate", "irr")) {
    ot <- "rate"; if (is.null(measure)) measure <- "IRR"; transform <- "exp"
    es <- calculate_effect_size(data, "rate", measure = measure, cols = cols)
  } else if (ot == "precomp") {
    names(data) <- tolower(names(data))
    if (!is.null(data$yi) && !is.null(data$vi)) {
      es <- escalc(yi = yi, vi = vi, data = data, measure = "GEN")
    } else if (!is.null(data$yi) && !is.null(data$se)) {
      es <- escalc(yi = yi, vi = se^2, data = data, measure = "GEN")
    } else if (!is.null(data$effect) && !is.null(data$lower) && !is.null(data$upper)) {
      es <- escalc(yi = log(effect),
                   vi = ((log(upper) - log(lower)) / (2 * 1.96))^2,
                   data = data, measure = "GEN")
    } else stop("precomp 需提供 yi+vi / yi+se / effect+lower+upper")
  } else if (ot == "survival") {
    names(data) <- tolower(names(data))
    if (!is.null(data$loghr) && !is.null(data$se)) {
      es <- escalc(yi = loghr, vi = se^2, data = data, measure = "HR")
    } else if (!is.null(data$hr) && !is.null(data$lower) && !is.null(data$upper)) {
      es <- escalc(yi = log(hr),
                   vi = ((log(upper) - log(lower)) / (2 * 1.96))^2,
                   data = data, measure = "HR")
    } else stop("survival 需提供 loghr+se 或 hr+lower+upper")
    transform <- "exp"
  } else if (ot == "correlation") {
    names(data) <- tolower(names(data))
    if (is.null(data$r) || is.null(data$n)) stop("correlation 需提供 r + n")
    if (is.null(measure)) measure <- "ZCOR"
    es <- calculate_effect_size(data, "correlation", measure = measure, cols = cols)
    transform <- "tanh"
  } else if (ot %in% c("single_proportion", "proportion")) {
    ot <- "single_proportion"
    names(data) <- tolower(names(data))
    if (is.null(data$events) || is.null(data$n)) stop("single_proportion 需提供 events + n")
    if (is.null(measure)) measure <- "PLO"
    es <- calculate_effect_size(data, "single_proportion", measure = measure, cols = cols)
    transform <- if (measure == "PLO") "plogis" else "none"
  } else if (ot %in% c("single_mean", "mean")) {
    ot <- "single_mean"
    names(data) <- tolower(names(data))
    if (is.null(data$mean) || is.null(data$sd) || is.null(data$n))
      stop("single_mean 需提供 mean + sd + n")
    if (is.null(measure)) measure <- "MN"
    es <- calculate_effect_size(data, "single_mean", measure = measure, cols = cols)
    transform <- "none"
  } else {
    stop("Unknown type: ", type)
  }
  
  # 保留原始协变量列（precomp/survival 分支的 escalc 不会自动保留）
  extras <- setdiff(names(data), names(es))
  if (length(extras) > 0) es <- cbind(es, data[, extras, drop = FALSE])
  
  es$study <- data$study
  res <- run_meta_analysis(es, method = method, random_effects = random, test_type = test)
  res$data <- es
  res$outcome_type <- ot
  res$measure <- measure
  res$transform <- transform
  class(res) <- c("ma_result", class(res))
  return(res)
}

# --- 12. 一键出图 + 结果摘要 ---
ma_save <- function(result, outdir = ".", prefix = "meta",
                    forest_title = "Forest Plot",
                    funnel_title = "Funnel Plot") {
  #' 生成森林图、漏斗图（SVG + PNG）与结果摘要 MD
  library(ggplot2)
  library(metafor)
  library(svglite)
  
  dir.create(outdir, showWarnings = FALSE, recursive = TRUE)
  es <- result$data
  trans <- result$transform
  
  p_f <- create_forest_plot(es, result, transform = trans, title = forest_title)
  ggsave(file.path(outdir, paste0(prefix, "_forest.svg")), p_f,
         width = 9, height = 5.5, dpi = 300)
  ggsave(file.path(outdir, paste0(prefix, "_forest.png")), p_f,
         width = 9, height = 5.5, dpi = 300)
  
  p_u <- create_funnel_plot(result, transform = trans, title = funnel_title)
  ggsave(file.path(outdir, paste0(prefix, "_funnel.svg")), p_u,
         width = 8, height = 6, dpi = 300)
  ggsave(file.path(outdir, paste0(prefix, "_funnel.png")), p_u,
         width = 8, height = 6, dpi = 300)
  
  het <- analyze_heterogeneity(result)
  pb  <- analyze_publication_bias(es, result)
  md  <- generate_results_summary(result, het, pub_bias = pb,
                                   model_name = paste0("Random-Effects (", result$method, ")"))
  writeLines(md, file.path(outdir, paste0(prefix, "_results.md")))
  
  cat("Saved to", outdir, ":\n")
  cat(" -", prefix, "_forest.svg / .png\n")
  cat(" -", prefix, "_funnel.svg / .png\n")
  cat(" -", prefix, "_results.md\n")
  invisible(list(forest = p_f, funnel = p_u, summary = md))
}
