# -*- coding: utf-8 -*-
# AUTO-GENERATED from meta_analysis_core.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_meta_analysis_core.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "meta_analysis_core.R"

R_SOURCE = r'''# ============================================================================
# Meta-Analysis Core Engine
#  核心引擎：覆盖所有标准元分析流程
#  用户可直接调用或修改参数
# ============================================================================

# --- 0. 环境准备 ---
prepare_meta_environment <- function(advanced = TRUE) {
  #' 检查所需的 R 包是否已安装（不自动安装；缺失时仅提示用户手动安装）
  #' @param advanced 是否检查可选增强包
  
  .MA_LANG <- local({
    lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
    if (grepl("zh|cn|chs", lang)) "zh" else "en"
  })
  .msg <- function(en, zh) if (.MA_LANG == "zh") zh else en
  
  core_pkgs <- c("metafor", "meta", "netmeta", "ggplot2", "gridExtra", "svglite")
  optional_pkgs <- c("metasens", "bayesmeta", "metaviz", "robvis", "gt")
  
  all_pkgs <- if (advanced) c(core_pkgs, optional_pkgs) else core_pkgs
  
  missing <- c()
  for (pkg in all_pkgs) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      missing <- c(missing, pkg)
    }
  }
  
  if (length(missing) > 0) {
    cat(sprintf(.msg("  ⚠️  Missing R packages: %s\n",
                     "  ⚠️  缺少 R 包：%s\n"), paste(missing, collapse = ", ")))
    cat(.msg("    Install manually in R (the skill NEVER auto-installs packages):\n",
             "    请在 R 中手动安装（本技能绝不自动安装包）：\n"))
    cat(.msg("    > (install the missing packages manually, e.g. via your R package manager)\n",
             "    > （请手动安装缺失的包，例如通过 R 包管理器）\n"))
    stop(.msg("Missing required R packages — install them, then re-run. See README for the full list.",
              "缺少必需的 R 包 — 安装后重试。完整列表见 README。"))
  }
  
  if (!requireNamespace("dmetar", quietly = TRUE)) {
    cat(.msg("  ⚠️  'dmetar' (GitHub: MathiasHarrer/dmetar) is missing.\n",
             "  ⚠️  缺少「dmetar」（GitHub: MathiasHarrer/dmetar）。\n"))
    cat(.msg("    Install manually in R:\n",
             "    请在 R 中手动安装：\n"))
    cat(.msg("    > (install dmetar manually from GitHub: MathiasHarrer/dmetar)\n",
             "    > （从 GitHub 手动安装 dmetar：MathiasHarrer/dmetar）\n"))
  }
  
  message(.msg("Meta-analysis environment ready (all required packages present).",
               "Meta-analysis 环境就绪（所有必需包已安装）。"))
}

# --- 1. 效应量计算 ---
calculate_effect_size <- function(data, outcome_type, measure = NULL, cols = NULL) {
  #' 计算各种效应量（列名大小写不敏感）
  #' @param data 数据框
  #' @param outcome_type "dichotomous" | "continuous" | "rate" (IRR 率比)
  #' @param measure OR/RR/RD/PETO | SMD/MD/ROM | IRR
  #' @param cols 命名列表，逻辑角色 -> 实际列名

  library(metafor)
  library(meta)

  data <- as.data.frame(data)
  names(data) <- tolower(names(data))
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
    } else stop(.msg("dichotomous measure not supported: ", "不支持的二分类效应量度量："), measure)

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
    } else stop(.msg("continuous measure not supported: ", "不支持的连续型效应量度量："), measure)

  } else if (outcome_type == "rate") {
    a  <- get_col("a", "a"); b <- get_col("b", "b")
    c_ <- get_col("c", "c"); d <- get_col("d", "d")
    if (is.null(measure)) measure <- "IRR"
    if (measure == "IRR") {
      es <- escalc(measure = "IRR", x1i = a, t1i = b, x2i = c_, t2i = d)
    } else stop(.msg("rate measure not supported: ", "不支持的率比效应量度量："), measure)

  } else if (outcome_type == "correlation") {
    r <- get_col("r", "r"); n <- get_col("n", "n")
    if (is.null(measure) || measure == "ZCOR") {
      es <- escalc(measure = "ZCOR", ri = r, ni = n)
    } else stop(.msg("correlation measure not supported: ", "不支持的相关系数效应量度量："), measure)

  } else if (outcome_type == "single_proportion") {
    x <- get_col("events", "events"); n <- get_col("n", "n")
    if (is.null(measure) || measure == "PLO") {
      es <- escalc(measure = "PLO", xi = x, ni = n)
    } else if (measure == "PR") {
      es <- escalc(measure = "PR", xi = x, ni = n)
    } else stop(.msg("single_proportion measure not supported: ", "不支持的单组率效应量度量："), measure)

  } else if (outcome_type == "single_mean") {
    m <- get_col("mean", "mean"); s <- get_col("sd", "sd"); n <- get_col("n", "n")
    if (is.null(measure) || measure == "MN") {
      es <- escalc(measure = "MN", mi = m, sdi = s, ni = n)
    } else stop(.msg("single_mean measure not supported: ", "不支持的单组均值效应量度量："), measure)

  } else {
    stop(.msg("Unknown outcome_type: ", "未知的 outcome_type："), outcome_type)
  }

  extras <- setdiff(names(data), names(es))
  if (length(extras) > 0) es <- cbind(es, data[, extras, drop = FALSE])
  return(es)
}

# --- 2. 核心元分析 ---
run_meta_analysis <- function(es_data, method = "REML", 
                              random_effects = TRUE,
                              test_type = "knha") {
  library(metafor)
  if (random_effects) {
    method <- ifelse(method == "FE", "REML", method)
    res <- rma(yi = yi, vi = vi, data = es_data, method = method, test = test_type)
  } else {
    res <- rma(yi = yi, vi = vi, data = es_data, method = "FE")
  }
  res$prediction <- predict(res)
  res$method <- method
  res$random <- random_effects
  res$test_type <- test_type
  return(res)
}

# --- 3. 异质性分析 ---
analyze_heterogeneity <- function(model_result) {
  stats <- list(
    I2 = model_result$I2,
    H2 = model_result$H2,
    tau2 = model_result$tau2,
    Q = model_result$QE,
    df = model_result$k - 1,
    p_Q = if (is.null(model_result$QEp)) NA else model_result$QEp
  )
  stats$interpretation <- ifelse(
    stats$I2 < 25, .msg("low heterogeneity", "低异质性"),
    ifelse(stats$I2 < 50, .msg("moderate heterogeneity", "中等异质性"),
           ifelse(stats$I2 < 75, .msg("high heterogeneity", "高异质性"),
                  .msg("very high heterogeneity", "非常高异质性")))
  )
  return(stats)
}

# --- 4. 发表偏倚分析 ---
analyze_publication_bias <- function(es_data, model_result) {
  library(metafor)
  results <- list()
  if (nrow(es_data) >= 3) {
    egg <- regtest(model_result)
    results$egger <- list(z = egg$zval, p = egg$pval)
  }
  if (nrow(es_data) >= 3) {
    beg <- ranktest(model_result)
    results$begg <- list(z = beg$zval, p = beg$pval)
  }
  if (nrow(es_data) >= 5) {
    tf <- trimfill(model_result)
    results$trimfill <- list(k0 = tf$k0, pooled_est = tf$beta[1],
                             ci_lb = tf$ci.lb, ci_ub = tf$ci.ub)
  }
  return(results)
}

# --- 5. 亚组分析 ---
run_subgroup_analysis <- function(es_data, group_var) {
  library(metafor)
  if (!group_var %in% names(es_data))
    stop(.msg("group_var not found: ", "未找到 group_var："), group_var)
  es_data[[group_var]] <- as.factor(es_data[[group_var]])
  levels <- levels(es_data[[group_var]])
  sub <- lapply(levels, function(lv) {
    sub_dat <- es_data[es_data[[group_var]] == lv, , drop = FALSE]
    m <- rma(yi = yi, vi = vi, data = sub_dat, method = "REML", test = "knha")
    data.frame(subgroup = lv, k = m$k, estimate = m$beta[1], se = m$se,
               ci_lb = m$ci.lb, ci_ub = m$ci.ub, I2 = m$I2)
  })
  subgroup_effects <- do.call(rbind, sub)
  model <- rma(yi = yi, vi = vi, mods = as.formula(paste("~", group_var)),
               data = es_data, method = "REML", test = "knha")
  wald_test <- anova(model, btt = 2:length(levels))
  return(list(model = model, subgroup_effects = subgroup_effects,
              between_group_Q = wald_test$QM, between_group_p = wald_test$QMp))
}

# --- 6. 元回归 ---
run_meta_regression <- function(es_data, covariates) {
  library(metafor)
  library(ggplot2)
  formula_str <- paste("yi ~", paste(covariates, collapse = " + "))
  formula <- as.formula(formula_str)
  model <- rma(formula, vi = vi, data = es_data, method = "REML", test = "knha")
  bubble_plot <- NULL
  if (length(covariates) == 1) {
    cv <- es_data[[covariates[1]]]
    df <- data.frame(x = cv, y = es_data$yi,
                     lo = es_data$yi - 1.96 * sqrt(es_data$vi),
                     hi = es_data$yi + 1.96 * sqrt(es_data$vi),
                     w = 1 / sqrt(es_data$vi))
    bubble_plot <- ggplot(df, aes(x = x, y = y)) +
      geom_errorbar(aes(ymin = lo, ymax = hi), width = 0.1, color = "#2a3950", linewidth = 0.5) +
      geom_point(aes(size = w), shape = 15, color = "#2a3950") +
      scale_size(guide = "none") +
      labs(x = covariates[1], y = "Effect Size (95% CI)") +
      theme_minimal()
  }
  return(list(model = model, bubble_plot = bubble_plot))
}

# --- 7. 敏感性分析 ---
run_sensitivity_analysis <- function(es_data, analysis_type = "all") {
  library(metafor)
  model_reml <- rma(yi = yi, vi = vi, data = es_data, method = "REML")
  results <- list()
  if (analysis_type %in% c("all", "leave1out")) {
    loo <- leave1out(model_reml)
    results$leave1out <- data.frame(study = es_data$study, estimate = loo$estimate,
                                    se = loo$se, ci_lb = loo$ci.lb, ci_ub = loo$ci_ub, I2 = loo$I2)
  }
  if (analysis_type %in% c("all", "quality")) {
    if ("quality" %in% names(es_data)) {
      high_q <- es_data[es_data$quality == "low risk" | es_data$quality >= 6, ]
      if (nrow(high_q) >= 3) {
        high_q_model <- rma(yi = yi, vi = vi, data = high_q, method = "REML")
        results$high_quality <- high_q_model
      }
    }
  }
  if (analysis_type %in% c("all", "model_comparison")) {
    models <- list()
    models$DL   <- rma(yi = yi, vi = vi, data = es_data, method = "DL")
    models$REML <- rma(yi = yi, vi = vi, data = es_data, method = "REML")
    models$ML   <- rma(yi = yi, vi = vi, data = es_data, method = "ML")
    models$FE   <- rma(yi = yi, vi = vi, data = es_data, method = "FE")
    model_summary <- data.frame(
      Method = names(models),
      Estimate = sapply(models, function(m) m$beta[1]),
      CI_LB = sapply(models, function(m) m$ci.lb),
      CI_UB = sapply(models, function(m) m$ci.ub),
      tau2 = sapply(models, function(m) m$tau2),
      I2 = sapply(models, function(m) m$I2))
    results$model_comparison <- model_summary
  }
  if (analysis_type %in% c("all", "cumul")) {
    k <- nrow(es_data)
    cum_est <- cum_lb <- cum_ub <- cum_I2 <- numeric(0)
    for (i in seq_len(k)) {
      cm <- rma(yi = yi, vi = vi, data = es_data[seq_len(i), , drop = FALSE], method = "REML")
      cum_est <- c(cum_est, cm$beta[1])
      cum_lb  <- c(cum_lb, cm$ci.lb)
      cum_ub  <- c(cum_ub, cm$ci.ub)
      cum_I2  <- c(cum_I2, cm$I2)
    }
    results$cumul <- data.frame(study = es_data$study, estimate = cum_est,
                                ci_lb = cum_lb, ci_ub = cum_ub, I2 = cum_I2)
  }
  return(results)
}

# --- 8. 森林图（ggplot 可编辑版本） ---
create_forest_plot <- function(es_data, model_result, style = "revman",
                               transform = NULL, xlab = NULL, title = "Forest Plot") {
  library(ggplot2)
  themes <- list(
    revman  = list(study = "#2a3950", pooled = "#0f9b81", pshape = 23),
    classic = list(study = "#000000", pooled = "#000000", pshape = 23),
    modern  = list(study = "#1f77b4", pooled = "#ff7f0e", pshape = 18),
    lancet  = list(study = "#00468B", pooled = "#AD002A", pshape = 23),
    nejm    = list(study = "#0072B5", pooled = "#BC3C29", pshape = 18))
  th <- if (!is.null(themes[[style]])) themes[[style]] else themes[["revman"]]
  col_study  <- th$study; col_pooled <- th$pooled; pooled_shape <- th$pshape
  if (is.null(transform)) transform <- "none"
  f <- switch(transform, exp = exp, tanh = tanh, plogis = plogis, identity)
  ref <- switch(transform, exp = 1, tanh = 0, plogis = 0.5, identity = 0)
  od <- order(es_data$yi, decreasing = TRUE)
  yi <- es_data$yi[od]; vi <- es_data$vi[od]; lab <- es_data$study[od]
  w  <- (1 / vi)[od]; k  <- length(yi)
  d <- data.frame(label = c(lab, .msg("Pooled", "合并")),
                  ypos  = c((k + 1):2, 1),
                  est   = c(f(yi), f(model_result$beta[1])),
                  lo    = c(f(yi - 1.96 * sqrt(vi)), f(model_result$ci.lb)),
                  hi    = c(f(yi + 1.96 * sqrt(vi)), f(model_result$ci.ub)),
                  w     = c(w, NA))
  if (is.null(xlab))
    xlab <- switch(transform,
                   exp    = .msg("Effect Ratio (95% CI)", "效应比（95% CI）"),
                   tanh   = .msg("Correlation r (95% CI)", "相关系数 r（95% CI）"),
                   plogis = .msg("Proportion (95% CI)", "率（95% CI）"),
                   .msg("Effect Size (95% CI)", "效应量（95% CI）"))
  p <- ggplot(d, aes(y = ypos)) +
    geom_vline(xintercept = ref, linetype = "dashed", color = "grey50", linewidth = 0.6) +
    geom_errorbar(aes(xmin = lo, xmax = hi, y = ypos), orientation = "y",
                  width = 0.25, linewidth = 0.5, color = col_study) +
    geom_point(data = d[d$label != .msg("Pooled", "合并"), ], aes(x = est, size = w),
               shape = 15, color = col_study) +
    scale_size(range = c(2, 6), guide = "none") +
    geom_point(data = d[d$label == .msg("Pooled", "合并"), ], aes(x = est),
               shape = pooled_shape, fill = col_pooled, color = col_pooled, size = 5) +
    scale_y_continuous(breaks = d$ypos, labels = d$label, limits = c(0.5, k + 1.5)) +
    annotate("text", x = max(d$hi) * 1.03, y = 1,
             label = sprintf("%.2f [%.2f, %.2f]", f(model_result$beta[1]),
                             f(model_result$ci.lb), f(model_result$ci.ub)),
             hjust = 0, size = 3, fontface = "bold", color = col_pooled) +
    labs(x = xlab, y = "", title = title) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"),
          panel.grid.major.y = element_blank(),
          axis.text.y = element_text(size = 10))
  return(p)
}

# --- 9. 漏斗图 ---
create_funnel_plot <- function(model_result, style = "classic",
                               transform = NULL, title = "Funnel Plot") {
  library(ggplot2)
  library(metafor)
  if (is.null(transform)) transform <- "none"
  f <- switch(transform, exp = exp, tanh = tanh, plogis = plogis, identity)
  yi <- model_result$yi; se <- sqrt(model_result$vi)
  pooled <- model_result$beta[1]
  ref_null <- switch(transform, exp = 1, tanh = 0, plogis = 0.5, identity = 0)
  eg <- tryCatch(regtest(model_result), error = function(e) NULL)
  bg <- tryCatch(ranktest(model_result), error = function(e) NULL)
  sub <- sprintf(.msg("Egger p = %.3f, Begg p = %.3f", "Egger p = %.3f，Begg p = %.3f"),
                 ifelse(is.null(eg), NA, eg$pval),
                 ifelse(is.null(bg), NA, bg$pval))
  d <- data.frame(yi = yi, se = se, inv = 1 / se)
  p <- ggplot(d, aes(x = f(yi), y = inv)) +
    geom_vline(xintercept = f(pooled), color = "#c0392b", linetype = "dashed", linewidth = 0.8) +
    geom_vline(xintercept = ref_null, color = "grey60", linewidth = 0.4) +
    geom_segment(aes(x = f(pooled - 1.96 * se), xend = f(pooled + 1.96 * se),
                     y = inv, yend = inv), color = "#a8d5f5", linewidth = 0.3) +
    geom_point(size = 3, color = "#2a3950", alpha = 0.85) +
    labs(x = if (transform == "exp") .msg("Effect Ratio", "效应比") else .msg("Effect Size", "效应量"),
         y = .msg("Precision (1/SE)", "精度（1/SE）"), title = title, subtitle = sub) +
    theme_minimal() +
    coord_flip()
  return(p)
}

# --- 10. 结果汇总报告 ---
generate_results_summary <- function(model_result, heterogeneity,
                                     sensitivity = NULL, pub_bias = NULL,
                                     model_name = "Random-Effects (REML)") {
  .MA_LANG <- local({
    lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
    if (grepl("zh|cn|chs", lang)) "zh" else "en"
  })
  .msg <- function(en, zh) if (.MA_LANG == "zh") zh else en
  
  r <- model_result; h <- heterogeneity
  pred <- r$prediction
  pred_lo <- if (is.null(pred$cr.lb)) pred$pred - 1.96 * sqrt(pred$se^2 + r$tau2) else pred$cr.lb
  pred_hi <- if (is.null(pred$cr.ub)) pred$pred + 1.96 * sqrt(pred$se^2 + r$tau2) else pred$cr.ub

  summary_text <- paste(c(
    "========================================",
    .msg(" Meta-Analysis Results Summary", " Meta-分析结果汇总"),
    "========================================",
    "",
    paste0(.msg("Model: ", "模型："), model_name),
    paste0(.msg("K studies = ", "研究数 K = "), r$k),
    "",
    .msg("POOLED EFFECT:", "合并效应："),
    paste0("  ", .msg("Estimate: ", "估计值："), sprintf("%.3f", r$beta[1])),
    paste0("  ", .msg("95% CI: [", "95% CI：["), sprintf("%.3f", r$ci.lb), ", ", sprintf("%.3f", r$ci.ub), "]"),
    paste0("  z = ", sprintf("%.3f", r$zval), ", p = ", sprintf("%.4f", r$pval)),
    "",
    .msg("HETEROGENEITY:", "异质性："),
    paste0("  I2 = ", sprintf("%.1f", h$I2), "% (", h$interpretation, ")"),
    paste0("  tau2 = ", sprintf("%.4f", h$tau2)),
    paste0("  Q = ", sprintf("%.3f", h$Q), ", df = ", h$df, ", p = ", sprintf("%.4f", h$p_Q)),
    "",
    .msg("PREDICTION INTERVAL:", "预测区间："),
    paste0("  [", sprintf("%.3f", pred_lo), ", ", sprintf("%.3f", pred_hi), "]")
  ), collapse = "\n")
  
  if (!is.null(pub_bias)) {
    summary_text <- paste0(summary_text, "\n\n", .msg("PUBLICATION BIAS:", "发表偏倚："), "\n")
    if (!is.null(pub_bias$egger))
      summary_text <- paste0(summary_text, sprintf(
        .msg("  Egger test: z = %.3f, p = %.4f\n", "  Egger 检验：z = %.3f，p = %.4f\n"),
        pub_bias$egger$z, pub_bias$egger$p))
    if (!is.null(pub_bias$begg))
      summary_text <- paste0(summary_text, sprintf(
        .msg("  Begg test:  z = %.3f, p = %.4f\n",
             "  Begg 检验： z = %.3f，p = %.4f\n"),
        pub_bias$begg$z, pub_bias$begg$p))
  }
  return(summary_text)
}

# --- 11. 统一分析入口（推荐） ---
ma_analyze <- function(data, type, measure = NULL, cols = NULL,
                       method = "REML", test = "knha",
                       random = TRUE, label_col = NULL) {
  library(metafor)
  data <- as.data.frame(data)
  if (!is.null(label_col)) {
    lc <- tolower(label_col)
    if (lc %in% tolower(names(data))) data$study <- as.character(data[[lc]])
  }
  names(data) <- tolower(names(data))
  if (is.null(data$study))
    data$study <- paste0(.msg("Study ", "研究 "), seq_len(nrow(data)))
  
  ot <- tolower(type); transform <- "none"
  
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
    } else stop(.msg("precomp requires yi+vi / yi+se / effect+lower+upper",
                     "precomp 需提供 yi+vi / yi+se / effect+lower+upper"))
  } else if (ot == "survival") {
    names(data) <- tolower(names(data))
    if (!is.null(data$loghr) && !is.null(data$se)) {
      es <- escalc(yi = loghr, vi = se^2, data = data, measure = "HR")
    } else if (!is.null(data$hr) && !is.null(data$lower) && !is.null(data$upper)) {
      es <- escalc(yi = log(hr),
                   vi = ((log(upper) - log(lower)) / (2 * 1.96))^2,
                   data = data, measure = "HR")
    } else stop(.msg("survival requires loghr+se or hr+lower+upper",
                     "survival 需提供 loghr+se 或 hr+lower+upper"))
    transform <- "exp"
  } else if (ot == "correlation") {
    names(data) <- tolower(names(data))
    if (is.null(data$r) || is.null(data$n)) stop(.msg("correlation requires r + n",
                                                        "correlation 需提供 r + n"))
    if (is.null(measure)) measure <- "ZCOR"
    es <- calculate_effect_size(data, "correlation", measure = measure, cols = cols)
    transform <- "tanh"
  } else if (ot %in% c("single_proportion", "proportion")) {
    ot <- "single_proportion"; names(data) <- tolower(names(data))
    if (is.null(data$events) || is.null(data$n))
      stop(.msg("single_proportion requires events + n",
                "single_proportion 需提供 events + n"))
    if (is.null(measure)) measure <- "PLO"
    es <- calculate_effect_size(data, "single_proportion", measure = measure, cols = cols)
    transform <- if (measure == "PLO") "plogis" else "none"
  } else if (ot %in% c("single_mean", "mean")) {
    ot <- "single_mean"; names(data) <- tolower(names(data))
    if (is.null(data$mean) || is.null(data$sd) || is.null(data$n))
      stop(.msg("single_mean requires mean + sd + n",
                "single_mean 需提供 mean + sd + n"))
    if (is.null(measure)) measure <- "MN"
    es <- calculate_effect_size(data, "single_mean", measure = measure, cols = cols)
    transform <- "none"
  } else {
    stop(.msg("Unknown type: ", "未知类型："), type)
  }
  
  extras <- setdiff(names(data), names(es))
  if (length(extras) > 0) es <- cbind(es, data[, extras, drop = FALSE])
  es$study <- data$study
  res <- run_meta_analysis(es, method = method, random_effects = random, test_type = test)
  res$data <- es; res$outcome_type <- ot; res$measure <- measure; res$transform <- transform
  class(res) <- c("ma_result", class(res))
  return(res)
}

# --- 12. 一键出图 + 结果摘要 ---
ma_save <- function(result, outdir = ".", prefix = "meta",
                    forest_title = "Forest Plot", funnel_title = "Funnel Plot") {
  .MA_LANG <- local({
    lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
    if (grepl("zh|cn|chs", lang)) "zh" else "en"
  })
  .msg <- function(en, zh) if (.MA_LANG == "zh") zh else en
  
  library(ggplot2); library(metafor); library(svglite)
  dir.create(outdir, showWarnings = FALSE, recursive = TRUE)
  es <- result$data; trans <- result$transform
  p_f <- create_forest_plot(es, result, transform = trans, title = forest_title)
  ggsave(file.path(outdir, paste0(prefix, "_forest.svg")), p_f, width = 9, height = 5.5, dpi = 300)
  ggsave(file.path(outdir, paste0(prefix, "_forest.png")), p_f, width = 9, height = 5.5, dpi = 300)
  p_u <- create_funnel_plot(result, transform = trans, title = funnel_title)
  ggsave(file.path(outdir, paste0(prefix, "_funnel.svg")), p_u, width = 8, height = 6, dpi = 300)
  ggsave(file.path(outdir, paste0(prefix, "_funnel.png")), p_u, width = 8, height = 6, dpi = 300)
  het <- analyze_heterogeneity(result)
  pb  <- analyze_publication_bias(es, result)
  md  <- generate_results_summary(result, het, pub_bias = pb,
                                   model_name = paste0("Random-Effects (", result$method, ")"))
  writeLines(md, file.path(outdir, paste0(prefix, "_results.md")))
  cat(.msg("Saved to", "已保存到"), outdir, ":\n")
  cat(" -", prefix, .msg("_forest.svg / .png", "_forest.svg / .png"), "\n")
  cat(" -", prefix, .msg("_funnel.svg / .png", "_funnel.svg / .png"), "\n")
  cat(" -", prefix, .msg("_results.md", "_results.md"), "\n")
  invisible(list(forest = p_f, funnel = p_u, summary = md))
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
