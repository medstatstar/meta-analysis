# -*- coding: utf-8 -*-
# AUTO-GENERATED from advanced_functions.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_advanced_functions.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "advanced_functions.R"

R_SOURCE = r'''# ============================================================================
# Advanced Functions / 高级诊断图与专项 Meta 分析封装
#   目的：把此前散落在 reference .md 里的示例代码固化为可直接调用的函数，
#         减少 AI/用户自编 R 代码出错。
#   核心依赖（通常已装）：metafor, meta, ggplot2
#   可选依赖（按需安装）：dmetar/metapower(功效)、bayesmeta(贝叶斯两组)、
#                          mada(诊断准确性)、robvis(RoB 图)
# ============================================================================

# --- 双语语言检测（默认英文，中文环境切中文） ---
.MA_LANG <- local({
  lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
  if (grepl("zh|cn|chs", lang)) "zh" else "en"
})
.msg <- function(en, zh) if (.MA_LANG == "zh") zh else en

# 统一配色（与 core 森林图一致）
.MA_COL_DARK  <- "#2a3950"
.MA_COL_GREEN <- "#0f9b81"
.MA_COL_RED   <- "#c0392b"

.need_pkg <- function(pkg, feature) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf(.msg("The feature '%s' requires R package '%s', which is not installed.\nPlease install it in R, then retry.",
                      "功能「%s」需要 R 包「%s」，当前未安装。\n请在 R 中安装后重试。"),
                   feature, pkg, pkg), call. = FALSE)
  }
}

# ============================================================================
# 1. Baujat 图 —— 异质性来源诊断（贡献 vs 影响）
# ============================================================================
plot_baujat <- function(model_result, title = "Baujat Plot", label = TRUE, top_n = 5) {
  library(metafor); library(ggplot2)
  grDevices::pdf(NULL); on.exit(grDevices::dev.off(), add = TRUE)
  b <- baujat(model_result)
  df <- data.frame(x = b$x, y = b$y,
                   slab = if (!is.null(b$slab)) b$slab else rownames(b),
                   stringsAsFactors = FALSE)
  df$flag <- rank(-df$x) <= top_n
  p <- ggplot(df, aes(x = x, y = y)) +
    geom_point(aes(color = flag), size = 3, alpha = 0.85) +
    scale_color_manual(values = c(`FALSE` = .MA_COL_DARK, `TRUE` = .MA_COL_RED), guide = "none") +
    labs(x = .msg("Contribution to overall heterogeneity (Q)",
                  "对总体异质性 Q 的贡献"),
         y = .msg("Influence on overall result", "对总体结果的影响"),
         title = title) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"))
  if (label) {
    p <- p + ggrepel_or_text(df[df$flag, , drop = FALSE])
  }
  attr(p, "data") <- df
  return(p)
}

ggrepel_or_text <- function(d) {
  if (requireNamespace("ggrepel", quietly = TRUE)) {
    ggrepel::geom_text_repel(data = d, ggplot2::aes(label = slab),
                             size = 3, color = "#c0392b")
  } else {
    ggplot2::geom_text(data = d, ggplot2::aes(label = slab),
                       size = 3, color = "#c0392b", vjust = -0.8)
  }
}

# ============================================================================
# 2. GOSH 图 —— Graphical Display of Study Heterogeneity
# ============================================================================
run_gosh <- function(model_result, subsets = 10000, seed = 1234) {
  library(metafor)
  set.seed(seed)
  g <- gosh(model_result, subsets = subsets, progbar = FALSE)
  return(g)
}

plot_gosh <- function(gosh_result, x = "estimate", y = "I2", title = "GOSH Plot") {
  library(ggplot2)
  res <- as.data.frame(gosh_result$res)
  df <- data.frame(x = res[[x]], y = res[[y]])
  p <- ggplot(df, aes(x = x, y = y)) +
    geom_point(alpha = 0.08, color = .MA_COL_DARK, size = 0.6) +
    labs(x = x, y = y, title = title,
         subtitle = sprintf(.msg("%d subset models", "%d 个子集模型"), nrow(df))) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"))
  attr(p, "data") <- df
  return(p)
}

# ============================================================================
# 3. Drapery 图 —— 多 α 稳健性（z-value / p-value 曲线）
# ============================================================================
plot_drapery <- function(es_data, labels = NULL, type = "zvalue", sm = "SMD",
                         title = "Drapery Plot") {
  .need_pkg("meta", .msg("Drapery Plot", "Drapery 图"))
  m <- meta::metagen(TE = es_data$yi, seTE = sqrt(es_data$vi),
                     studlab = if (!is.null(labels)) labels else es_data$study,
                     sm = sm, common = FALSE, random = TRUE)
  meta::drapery(m, type = type, main = title, labels = "id", legend = TRUE)
  invisible(m)
}

# ============================================================================
# 4. Power 曲线 —— Meta 分析统计功效（自实现，无外部依赖）
# ============================================================================
run_power_curve <- function(effect = 0.3, n1 = 50, n2 = 50, k_range = 2:30,
                            i2 = 0.5, measure = "d", sig_level = 0.05,
                            target_power = 0.80) {
  library(ggplot2)
  
  if (measure == "d") {
    v_study <- (n1 + n2) / (n1 * n2) + effect^2 / (2 * (n1 + n2))
  } else {
    v_study <- 4 / n1 + 4 / n2
  }
  za <- qnorm(1 - sig_level / 2)
  
  power_at_k <- function(k, random = FALSE) {
    v_fixed <- v_study / k
    if (random && i2 > 0) {
      tau2 <- (i2 / (1 - i2)) * v_study
      v_use <- (v_study + tau2) / k
    } else {
      v_use <- v_fixed
    }
    se <- sqrt(v_use)
    lambda <- abs(effect) / se
    pnorm(lambda - za) + pnorm(-lambda - za)
  }
  
  df <- data.frame(
    k = rep(k_range, 2),
    model = rep(c(.msg("Fixed-effect", "固定效应"),
                  sprintf(.msg("Random-effect (I²=%.0f%%)", "随机效应（I²=%.0f%%）"), i2 * 100)),
                each = length(k_range)),
    power = c(sapply(k_range, power_at_k, random = FALSE),
              sapply(k_range, power_at_k, random = TRUE)))
  
  rand_power <- sapply(k_range, power_at_k, random = TRUE)
  k_needed <- if (any(rand_power >= target_power))
    k_range[which(rand_power >= target_power)[1]] else NA_integer_
  
  p <- ggplot(df, aes(x = k, y = power, color = model)) +
    geom_hline(yintercept = target_power, linetype = "dashed", color = "grey50") +
    geom_line(linewidth = 1) +
    geom_point(size = 1.5) +
    scale_color_manual(values = c(.MA_COL_GREEN, .MA_COL_DARK)) +
    scale_y_continuous(limits = c(0, 1), labels = scales::percent) +
    labs(x = .msg("Number of studies (k)", "研究数量（k）"),
         y = .msg("Statistical power", "统计功效"),
         title = .msg("Meta-Analysis Power Curve", "Meta 分析功效曲线"),
         subtitle = sprintf(.msg("effect=%.2f, n1=%d, n2=%d | target %.0f%% power @ k=%s",
                                 "效应=%.2f，n1=%d，n2=%d | 目标 %.0f%% 功效 @ k=%s"),
                            effect, n1, n2, target_power * 100,
                            ifelse(is.na(k_needed), ">max", k_needed)),
         color = NULL) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"), legend.position = "top")
  
  return(list(data = df, plot = p, k_needed = k_needed, v_study = v_study))
}

# ============================================================================
# 5. 贝叶斯两组 Meta —— bayesmeta（需安装 bayesmeta）
# ============================================================================
run_bayes_pairwise <- function(es_data, labels = NULL,
                               mu_prior_mean = 0, mu_prior_sd = 4,
                               tau_prior_scale = 0.5, tau_prior = "halfnormal") {
  .need_pkg("bayesmeta", .msg("Bayesian Pairwise Meta", "贝叶斯两组 Meta"))
  tp <- switch(tau_prior,
    halfnormal = function(t) bayesmeta::dhalfnormal(t, scale = tau_prior_scale),
    halfcauchy = function(t) bayesmeta::dhalfcauchy(t, scale = tau_prior_scale),
    uniform    = function(t) dunif(t, 0, tau_prior_scale * 10),
    stop(.msg("tau_prior not supported: ", "不支持的 tau_prior："), tau_prior))
  
  fit <- bayesmeta::bayesmeta(y = es_data$yi, sigma = sqrt(es_data$vi),
                              labels = if (!is.null(labels)) labels else es_data$study,
                              mu.prior = c(mean = mu_prior_mean, sd = mu_prior_sd),
                              tau.prior = tp)
  cat("================================================\n")
  cat(.msg(" Bayesian Pairwise Meta-Analysis (bayesmeta)\n",
           " 贝叶斯两组 Meta 分析（bayesmeta）\n"))
  cat("================================================\n")
  print(fit$summary)
  return(fit)
}

# ============================================================================
# 6. 诊断准确性 Meta —— mada::reitsma（双变量模型 + SROC）
# ============================================================================
run_diagnostic_meta <- function(data, cols = list(TP = "TP", FP = "FP", FN = "FN", TN = "TN")) {
  .need_pkg("mada", .msg("Diagnostic Accuracy Meta", "诊断准确性 Meta"))
  d <- data.frame(TP = data[[cols$TP]], FP = data[[cols$FP]],
                  FN = data[[cols$FN]], TN = data[[cols$TN]])
  fit <- mada::reitsma(d)
  s <- summary(fit)
  cat("================================================\n")
  cat(.msg(" Diagnostic Accuracy Meta (Reitsma bivariate)\n",
           " 诊断准确性 Meta 分析（Reitsma 双变量模型）\n"))
  cat("================================================\n")
  print(s)
  return(fit)
}

plot_sroc <- function(reitsma_fit, title = "SROC Curve") {
  .need_pkg("mada", .msg("SROC Curve", "SROC 曲线"))
  mada::plot(reitsma_fit, sroclwd = 2, main = title)
  mada::points(mada::fpr(attr(reitsma_fit, "data")), col = 1, pch = 19) -> junk
  invisible(reitsma_fit)
}

# ============================================================================
# 7. RoB 交通灯图 / 汇总图 —— robvis（需安装 robvis）
# ============================================================================
plot_rob_traffic <- function(rob_data, tool = "ROB2") {
  .need_pkg("robvis", .msg("RoB Traffic Light Plot", "RoB 风险偏倚交通灯图"))
  robvis::rob_traffic_light(data = rob_data, tool = tool)
}

plot_rob_summary <- function(rob_data, tool = "ROB2", overall = TRUE) {
  .need_pkg("robvis", .msg("RoB Summary Plot", "RoB 风险偏倚汇总图"))
  robvis::rob_summary(data = rob_data, tool = tool, overall = overall)
}

# ============================================================================
# 8. TSA / 试验序贯分析（Trial Sequential Analysis，自实现，无外部依赖）
# ============================================================================
run_tsa <- function(es_data, labels = NULL,
                    effect_type = c("continuous", "binary"),
                    d = 0.2, or = NULL, p_con = NULL, p_exp = NULL,
                    n_per_study = NULL, alpha = 0.05, power = 0.80,
                    side = c("two", "one")) {
  effect_type <- match.arg(effect_type)
  side <- match.arg(side)
  Za <- if (side == "two") qnorm(1 - alpha / 2) else qnorm(1 - alpha)
  Zb <- qnorm(power)
  
  if (effect_type == "continuous") {
    if (!is.numeric(d) || d <= 0) stop(.msg("continuous requires d>0 (expected SMD / MCID)",
                                               "连续型需 d > 0（预期 SMD / MCID）"), call. = FALSE)
    RIS_info <- (Za + Zb)^2 / d^2
    info_i   <- 1 / es_data$vi
  } else {
    if (is.null(or) || is.null(p_con) || is.null(p_exp) || is.null(n_per_study))
      stop(.msg("binary requires or, p_con, p_exp, n_per_study",
                "二分类需提供 or、p_con、p_exp、n_per_study"), call. = FALSE)
    logOR    <- log(or)
    RIS_info <- (Za + Zb)^2 * (1 / p_con + 1 / p_exp) / logOR^2
    info_i   <- n_per_study
  }
  
  k <- nrow(es_data)
  w        <- 1 / es_data$vi
  cum_w    <- cumsum(w)
  Z_cum    <- cumsum(es_data$yi * w) / sqrt(cum_w)
  I_acc    <- cumsum(info_i)
  f        <- I_acc / RIS_info
  boundary <- Za / sqrt(pmax(f, 1e-6))
  
  crossed <- any(Z_cum >= boundary)
  reached <- I_acc[k] >= RIS_info
  concl   <- if (crossed) .msg("Crossed monitoring boundary — conclusive evidence, no more studies needed",
                                 "已跨越监测边界 —— 达到确证证据，无需更多研究")
             else if (reached) .msg("Reached RIS but not crossed boundary — evidence insufficient to confirm effect",
                                     "已累积至 RIS 但未跨越边界 —— 证据不足以确认效应")
             else .msg("Accrued information below RIS — more studies needed",
                       "累积信息量未达 RIS —— 仍需更多研究")
  
  df <- data.frame(
    study     = if (!is.null(labels)) labels else 1:k,
    info_prop = f, cum_Z = Z_cum, boundary = boundary,
    stringsAsFactors = FALSE)
  
  cat("================================================\n")
  cat(.msg(" Trial Sequential Analysis (self-implemented)\n",
           " 试验序贯分析（TSA，自实现）\n"))
  cat("================================================\n")
  cat(sprintf(.msg(" Effect type     : %s\n", " 效应类型    ：%s\n"), effect_type))
  cat(sprintf(.msg(" alpha / power   : %.3f / %.2f (%s-sided)\n",
                   " α / 功效    ：%.3f / %.2f（%s 侧）\n"), alpha, power, side))
  cat(sprintf(.msg(" Required Info   : %.1f (RIS)\n", " 所需信息量  ：%.1f（RIS）\n"), RIS_info))
  cat(sprintf(.msg(" Accrued Info    : %.1f (%.1f%% of RIS)\n",
                   " 已累积信息量：%.1f（RIS 的 %.1f%%）\n"), I_acc[k], 100 * f[k]))
  cat(sprintf(.msg(" Crossed boundary: %s\n", " 是否跨越边界：%s\n"), crossed))
  cat(sprintf(.msg(" Conclusion      : %s\n", " 结论        ：%s\n"), concl))
  cat("================================================\n")
  
  p <- NULL
  if (requireNamespace("ggplot2", quietly = TRUE)) {
    fx  <- seq(0.02, max(1.2, max(f) * 1.05), length.out = 200)
    bnd <- data.frame(x = fx, y = Za / sqrt(fx))
    library(ggplot2)
    p <- ggplot() +
      geom_line(data = bnd, aes(x = x, y = y), color = .MA_COL_RED, linetype = "dashed") +
      geom_line(data = df, aes(x = info_prop, y = cum_Z), color = .MA_COL_DARK, linewidth = 1) +
      geom_point(data = df, aes(x = info_prop, y = cum_Z), color = .MA_COL_DARK, size = 2) +
      geom_hline(yintercept = 0, color = "grey70") +
      geom_vline(xintercept = 1, color = "grey70", linetype = "dotted") +
      labs(x = .msg("Information fraction (I / RIS)", "信息分数（I / RIS）"),
           y = "Z-score",
           title = .msg("Trial Sequential Analysis", "试验序贯分析（TSA）"),
           subtitle = sprintf(.msg("RIS=%.0f, accrued=%.0f%% | %s",
                                   "RIS=%.0f，已累积=%.0f%% | %s"),
                              RIS_info, 100 * f[k], concl)) +
      theme_minimal() +
      theme(plot.title = element_text(face = "bold"))
    attr(p, "data") <- df
  }
  return(list(RIS = RIS_info, accrued = I_acc[k], info_frac = f, cum_Z = df,
              crossed = crossed, reached_RIS = reached, conclusion = concl, plot = p))
}

# ============================================================================
# 9. 剂量反应 Meta —— dosresmeta（需安装 dosresmeta）
# ============================================================================
run_dose_resp <- function(yi, dose, id, data,
                          outcome = c("binary", "continuous"),
                          shape = c("linear", "quadratic"),
                          se = NULL, v = NULL, sd = NULL,
                          cases = NULL, n = NULL,
                          study_design = NULL,
                          covariance = NULL,
                          plot = TRUE) {
  .need_pkg("dosresmeta", .msg("Dose-Response Meta", "剂量反应 Meta"))
  outcome <- match.arg(outcome)
  shape   <- match.arg(shape)
  
  if (is.null(covariance))
    covariance <- if (outcome == "binary") "gl" else "smd"
  
  fml <- if (shape == "quadratic")
    as.formula(paste(yi, "~", dose, "+ I(", dose, "^2)"))
  else
    as.formula(paste(yi, "~", dose))
  
  args <- list(formula = fml, id = as.name(id), data = data, covariance = covariance)
  
  if (outcome == "binary") {
    if (is.null(cases) || is.null(n))
      stop(.msg("binary requires cases and n (event count / sample size column names)",
                "二分类需提供 cases 和 n（事件数/样本量列名）"), call. = FALSE)
    if (is.null(se) && is.null(v))
      stop(.msg("binary requires se or v (SE / variance of effect size)",
                "二分类需提供 se 或 v（效应量的标准误/方差）"), call. = FALSE)
    args$cases <- as.name(cases); args$n <- as.name(n)
    if (!is.null(se)) args$se <- as.name(se) else args$v <- as.name(v)
    if (!is.null(study_design)) {
      args$type <- if (study_design %in% names(data)) as.name(study_design) else study_design
    }
  } else {
    if (is.null(sd) || is.null(n))
      stop(.msg("continuous requires sd and n (SD / sample size column names)",
                "连续型需提供 sd 和 n（标准差/样本量列名）"), call. = FALSE)
    args$sd <- as.name(sd); args$n <- as.name(n)
  }
  
  fit <- do.call(dosresmeta::dosresmeta, args)
  cat("================================================\n")
  cat(.msg(" Dose-Response Meta (dosresmeta)\n", " 剂量反应 Meta 分析（dosresmeta）\n"))
  cat("================================================\n")
  print(summary(fit))
  
  p <- NULL
  if (plot && requireNamespace("ggplot2", quietly = TRUE)) {
    pv <- tryCatch({
      nd  <- data.frame(x = seq(min(data[[dose]]), max(data[[dose]]), length.out = 50))
      colnames(nd) <- dose
      pr  <- predict(fit, newdata = nd, xref = min(data[[dose]]), expo = FALSE)
      data.frame(dose = nd[[dose]], pred = as.numeric(pr$pred),
                 low  = as.numeric(pr$ci.lb), up = as.numeric(pr$ci.ub))
    }, error = function(e) NULL)
    if (!is.null(pv)) {
      library(ggplot2)
      p <- ggplot(pv, aes(x = dose, y = pred)) +
        geom_ribbon(aes(ymin = low, ymax = up), fill = .MA_COL_DARK, alpha = 0.15) +
        geom_line(color = .MA_COL_GREEN, linewidth = 1) +
        geom_hline(yintercept = 0, color = "grey70", linetype = "dashed") +
        labs(x = .msg("Dose", "剂量"), y = .msg("Effect (log scale)", "效应（对数尺度）"),
             title = .msg("Dose-Response Relationship", "剂量-反应关系")) +
        theme_minimal() + theme(plot.title = element_text(face = "bold"))
      attr(p, "data") <- pv
    }
  }
  return(list(fit = fit, plot = p))
}

# ============================================================================
# 10. 生存 Meta —— survmeta（需安装 survmeta；本沙盒 R4.5.1 无二进制，请本机安装）
# ============================================================================
run_surv_meta <- function(yi, vi, studlab = NULL, data,
                          method = c("DL", "PM", "REML", "ML"),
                          plot = TRUE) {
  .need_pkg("survmeta", .msg("Survival Meta", "生存 Meta"))
  method <- match.arg(method)
  fml <- as.formula(paste(yi, "~ 1"))
  fit <- survmeta::survmeta(formula = fml, var = vi, studlab = studlab,
                            data = data, method = method)
  cat("================================================\n")
  cat(.msg(" Survival Meta-Analysis (survmeta)\n", " 生存 Meta 分析（survmeta）\n"))
  cat("================================================\n")
  print(summary(fit))
  return(fit)
}

# ============================================================================
# 11/12. 贝叶斯 NMA —— multinma(Stan) / gemtc(JAGS）
# ============================================================================
run_bayes_nma_multinma <- function(prep, priors,
                                    response = c("events", "rate", "multinomial",
                                                 "continuous", "survival"),
                                    n = "n", study = "study", treatment = "treatment",
                                    distribution = c("binomial", "poisson", "normal",
                                                     "weibull"),
                                    chains = 4, iter = 4000, seed = 123) {
  .need_pkg("multinma", .msg("Bayesian NMA (multinma)", "贝叶斯 NMA（multinma）"))
  response     <- match.arg(response)
  distribution <- match.arg(distribution)
  fit <- multinma::nma(prep, response = response, n = n, study = study,
                        treatment = treatment, distribution = distribution,
                        priors = priors, chains = chains, iter = iter, seed = seed)
  print(summary(fit))
  return(fit)
}

run_bayes_nma_gemtc <- function(data.ab, treatments, studies,
                                type = "consistency",
                                link = "logit",
                                likelihood = "binomial",
                                linearModel = "random",
                                om.scale = 2.5,
                                n.adapt = 5000, n.iter = 50000, thin = 10) {
  .need_pkg("gemtc", .msg("Bayesian NMA (gemtc)", "贝叶斯 NMA（gemtc）"))
  net <- gemtc::mtc.network(data.ab = data.ab, treatments = treatments, studies = studies)
  model <- gemtc::mtc.model(net, type = type, link = link, likelihood = likelihood,
                             linearModel = linearModel, om.scale = om.scale, dic = TRUE)
  results <- gemtc::mtc.run(model, n.adapt = n.adapt, n.iter = n.iter, thin = thin)
  print(summary(results))
  return(list(network = net, model = model, results = results))
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
