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

# 统一配色（与 core 森林图一致）
.MA_COL_DARK  <- "#2a3950"
.MA_COL_GREEN <- "#0f9b81"
.MA_COL_RED   <- "#c0392b"

.need_pkg <- function(pkg, feature) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf("功能【%s】需要 R 包 '%s'，当前未安装。\n请先运行: install.packages('%s')",
                 feature, pkg, pkg), call. = FALSE)
  }
}

# ============================================================================
# 1. Baujat 图 —— 异质性来源诊断（贡献 vs 影响）
# ============================================================================
plot_baujat <- function(model_result,
                        title = "Baujat Plot",
                        label = TRUE,
                        top_n = 5) {
  #' @title Baujat 图（ggplot 可编辑版）
  #' @description X 轴=对总体异质性 Q 的贡献；Y 轴=删除该研究后合并效应的变化
  #'              右上角研究 = 高贡献 + 高影响，需重点核查
  #' @param model_result rma 对象（metafor）
  #' @param top_n 高亮标注贡献最高的前 n 项研究
  library(metafor); library(ggplot2)

  # baujat() 总会绘制 base 图并返回 data.frame(x,y)；用 null 设备捕获，
  # 只取数据、避免污染当前图形设备，再用 ggplot 重画（可编辑 SVG）
  grDevices::pdf(NULL); on.exit(grDevices::dev.off(), add = TRUE)
  b <- baujat(model_result)
  df <- data.frame(x = b$x, y = b$y,
                   slab = if (!is.null(b$slab)) b$slab else rownames(b),
                   stringsAsFactors = FALSE)
  df$flag <- rank(-df$x) <= top_n         # 贡献最高的 top_n 高亮

  p <- ggplot(df, aes(x = x, y = y)) +
    geom_point(aes(color = flag), size = 3, alpha = 0.85) +
    scale_color_manual(values = c(`FALSE` = .MA_COL_DARK, `TRUE` = .MA_COL_RED),
                       guide = "none") +
    labs(x = "Contribution to overall heterogeneity (Q)",
         y = "Influence on overall result",
         title = title) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"))
  if (label) {
    p <- p + ggrepel_or_text(df[df$flag, , drop = FALSE])
  }
  attr(p, "data") <- df
  return(p)
}

# 若装了 ggrepel 用防重叠标签，否则退回普通文本
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
run_gosh <- function(model_result,
                     subsets = 10000,
                     seed = 1234) {
  #' @title 计算 GOSH（拟合所有/抽样研究子集的合并效应与 I²）
  #' @param model_result rma 对象
  #' @param subsets 子集抽样上限（研究数多时组合爆炸，需限制）
  #' @return gosh.rma 对象（含 $res: 每个子集的 estimate/I2/H2/tau2 等）
  library(metafor)
  set.seed(seed)
  g <- gosh(model_result, subsets = subsets, progbar = FALSE)
  return(g)
}

plot_gosh <- function(gosh_result,
                      x = "estimate", y = "I2",
                      title = "GOSH Plot") {
  #' @title GOSH 图（ggplot：合并效应 vs I²，密度散点）
  #' @param gosh_result run_gosh() 的输出
  #' @param x,y 绘图变量（estimate/I2/H2/tau2/QE/QEp/k）
  library(ggplot2)
  res <- as.data.frame(gosh_result$res)
  df <- data.frame(x = res[[x]], y = res[[y]])
  p <- ggplot(df, aes(x = x, y = y)) +
    geom_point(alpha = 0.08, color = .MA_COL_DARK, size = 0.6) +
    labs(x = x, y = y, title = title,
         subtitle = sprintf("%d subset models", nrow(df))) +
    theme_minimal() +
    theme(plot.title = element_text(face = "bold"))
  attr(p, "data") <- df
  return(p)
}

# ============================================================================
# 3. Drapery 图 —— 多 α 稳健性（z-value / p-value 曲线）
# ============================================================================
plot_drapery <- function(es_data,
                         labels = NULL,
                         type = "zvalue",
                         sm = "SMD",
                         title = "Drapery Plot") {
  #' @title Drapery 图（meta::drapery，base 图形，无 ggplot 替代）
  #' @description 同时展示所有 α 水平下显著性的变化，避免单一 α 截断
  #' @param es_data 含 yi, vi 的数据框（escalc/ma_analyze 的 res$data）
  #' @param type "zvalue"(默认) | "pvalue"
  #' @param sm 效应量度量标签（OR/RR/SMD/MD 等）
  .need_pkg("meta", "Drapery 图")
  m <- meta::metagen(TE = es_data$yi, seTE = sqrt(es_data$vi),
                     studlab = if (!is.null(labels)) labels else es_data$study,
                     sm = sm, common = FALSE, random = TRUE)
  meta::drapery(m, type = type, main = title,
                labels = "id", legend = TRUE)
  invisible(m)
}

# ============================================================================
# 4. Power 曲线 —— Meta 分析统计功效（自实现，无外部依赖）
#    公式：Valentine, Pigott & Rothstein (2010); Borenstein et al. (2009, Ch.29)
# ============================================================================
run_power_curve <- function(effect = 0.3,
                            n1 = 50, n2 = 50,
                            k_range = 2:30,
                            i2 = 0.5,
                            measure = "d",
                            sig_level = 0.05,
                            target_power = 0.80) {
  #' @title Meta 分析功效曲线（power vs 研究数 k）
  #' @description 计算不同研究数量 k 下检测到既定效应的统计功效，
  #'              固定效应与随机效应（含异质性 I²）两条曲线。
  #' @param effect 预期效应量（d 或 logOR/lnRR，视 measure）
  #' @param n1,n2 每研究处理/对照组样本量
  #' @param k_range 研究数量范围（向量）
  #' @param i2 预期异质性 I²（0-1），用于随机效应功效
  #' @param measure "d"(SMD) | "logor" | "lnrr"（决定单研究方差公式）
  #' @param sig_level 双侧显著性水平
  #' @param target_power 目标功效（绘制参考线并回报所需 k）
  #' @return list(data=功效表, plot=ggplot, k_needed=达到目标功效所需研究数)
  library(ggplot2)

  # 单研究抽样方差（每研究相同的近似）
  if (measure == "d") {
    v_study <- (n1 + n2) / (n1 * n2) + effect^2 / (2 * (n1 + n2))
  } else {
    # logOR / lnRR：用 4/n 近似（等分组、事件率中等）；用户可自行传入更精确 v
    v_study <- 4 / n1 + 4 / n2
  }
  za <- qnorm(1 - sig_level / 2)

  power_at_k <- function(k, random = FALSE) {
    v_fixed <- v_study / k
    if (random && i2 > 0) {
      # 由 I² 反推 tau²：tau² = I²/(1-I²) * v_study（典型研究方差近似）
      tau2 <- (i2 / (1 - i2)) * v_study
      v_use <- (v_study + tau2) / k
    } else {
      v_use <- v_fixed
    }
    se <- sqrt(v_use)
    lambda <- abs(effect) / se
    pnorm(lambda - za) + pnorm(-lambda - za)   # 双侧功效
  }

  df <- data.frame(
    k = rep(k_range, 2),
    model = rep(c("Fixed-effect", sprintf("Random-effect (I\u00b2=%.0f%%)", i2 * 100)),
                each = length(k_range)),
    power = c(sapply(k_range, power_at_k, random = FALSE),
              sapply(k_range, power_at_k, random = TRUE))
  )

  # 达到目标功效所需研究数（随机效应，更保守）
  rand_power <- sapply(k_range, power_at_k, random = TRUE)
  k_needed <- if (any(rand_power >= target_power))
    k_range[which(rand_power >= target_power)[1]] else NA_integer_

  p <- ggplot(df, aes(x = k, y = power, color = model)) +
    geom_hline(yintercept = target_power, linetype = "dashed", color = "grey50") +
    geom_line(linewidth = 1) +
    geom_point(size = 1.5) +
    scale_color_manual(values = c(.MA_COL_GREEN, .MA_COL_DARK)) +
    scale_y_continuous(limits = c(0, 1), labels = scales::percent) +
    labs(x = "Number of studies (k)", y = "Statistical power",
         title = "Meta-Analysis Power Curve",
         subtitle = sprintf("effect=%.2f, n1=%d, n2=%d | target %.0f%% power @ k=%s",
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
run_bayes_pairwise <- function(es_data,
                               labels = NULL,
                               mu_prior_mean = 0, mu_prior_sd = 4,
                               tau_prior_scale = 0.5,
                               tau_prior = "halfnormal") {
  #' @title 贝叶斯两组 Meta 分析（bayesmeta）
  #' @description 半正态 / 半柯西 τ 先验；返回后验合并效应、τ、区间、模型对象
  #' @param es_data 含 yi, vi 的数据框
  #' @param mu_prior_mean,mu_prior_sd μ（总体效应）正态先验
  #' @param tau_prior_scale τ 先验尺度
  #' @param tau_prior "halfnormal"(默认) | "halfcauchy" | "uniform"
  .need_pkg("bayesmeta", "贝叶斯两组 Meta")
  tp <- switch(tau_prior,
    halfnormal = function(t) bayesmeta::dhalfnormal(t, scale = tau_prior_scale),
    halfcauchy = function(t) bayesmeta::dhalfcauchy(t, scale = tau_prior_scale),
    uniform    = function(t) dunif(t, 0, tau_prior_scale * 10),
    stop("tau_prior not supported: ", tau_prior))

  fit <- bayesmeta::bayesmeta(
    y = es_data$yi,
    sigma = sqrt(es_data$vi),
    labels = if (!is.null(labels)) labels else es_data$study,
    mu.prior = c(mean = mu_prior_mean, sd = mu_prior_sd),
    tau.prior = tp
  )
  cat("================================================\n")
  cat(" Bayesian Pairwise Meta-Analysis (bayesmeta)\n")
  cat("================================================\n")
  print(fit$summary)
  return(fit)
}

# ============================================================================
# 6. 诊断准确性 Meta —— mada::reitsma（双变量模型 + SROC）
# ============================================================================
run_diagnostic_meta <- function(data,
                                 cols = list(TP = "TP", FP = "FP",
                                             FN = "FN", TN = "TN")) {
  #' @title 诊断准确性 Meta（Reitsma 双变量模型）
  #' @description 输入 2x2 计数（TP/FP/FN/TN），输出合并敏感度/特异度、
  #'              相关性、AUC 与 reitsma 对象（可 plot 出 SROC）
  #' @param data 数据框（每行一研究）
  #' @param cols 列名映射（默认 TP/FP/FN/TN）
  .need_pkg("mada", "诊断准确性 Meta")
  d <- data.frame(
    TP = data[[cols$TP]], FP = data[[cols$FP]],
    FN = data[[cols$FN]], TN = data[[cols$TN]]
  )
  fit <- mada::reitsma(d)
  s <- summary(fit)
  cat("================================================\n")
  cat(" Diagnostic Accuracy Meta (Reitsma bivariate)\n")
  cat("================================================\n")
  print(s)
  return(fit)
}

plot_sroc <- function(reitsma_fit, title = "SROC Curve") {
  #' @title SROC 曲线（含各研究点、汇总点与置信/预测区域）
  .need_pkg("mada", "SROC 曲线")
  mada::plot(reitsma_fit, sroclwd = 2, main = title)
  mada::points(mada::fpr(attr(reitsma_fit, "data")),
               col = 1, pch = 19) -> junk
  invisible(reitsma_fit)
}

# ============================================================================
# 7. RoB 交通灯图 / 汇总图 —— robvis（需安装 robvis）
# ============================================================================
plot_rob_traffic <- function(rob_data, tool = "ROB2") {
  #' @title 风险偏倚交通灯图（robvis::rob_traffic_light）
  #' @param rob_data 数据框：第1列研究名，中间各域为 "Low"/"Some concerns"/"High"，
  #'                 末列 Overall（ROB2 格式）
  #' @param tool "ROB2" | "ROBINS-I" | "ROB1" | "QUADAS-2"
  .need_pkg("robvis", "RoB 交通灯图")
  robvis::rob_traffic_light(data = rob_data, tool = tool)
}

plot_rob_summary <- function(rob_data, tool = "ROB2", overall = TRUE) {
  #' @title 风险偏倚汇总条形图（robvis::rob_summary）
  .need_pkg("robvis", "RoB 汇总图")
  robvis::rob_summary(data = rob_data, tool = tool, overall = overall)
}

# ============================================================================
# 8. TSA / 试验序贯分析（Trial Sequential Analysis，自实现，无外部依赖）
#    修正原参考文档中虚构的 meta::tes() API（meta 包无 TSA 导出函数）。
#    公式：Wetterslev J, et al. (2008, 2017). Trial Sequential Analysis.
#          监测边界：O'Brien-Fleming alpha 耗费函数 z(f)=Z_{1-alpha/2}/sqrt(f)
# ============================================================================
run_tsa <- function(es_data,
                    labels = NULL,
                    effect_type = c("continuous", "binary"),
                    d = 0.2,
                    or = NULL, p_con = NULL, p_exp = NULL,
                    n_per_study = NULL,
                    alpha = 0.05,
                    power = 0.80,
                    side = c("two", "one")) {
  #' @title 试验序贯分析（TSA）
  #' @description 计算所需信息量(RIS)与 O'Brien-Fleming 监测边界，按研究累积顺序
  #'              判断何时达到"确证证据"（累积 Z 跨越边界）或"信息不足"。
  #' @param es_data 含 yi, vi 的数据框（务必按研究累积/发表时间顺序排列）
  #' @param effect_type "continuous"(默认, SMD) | "binary"(OR, 需 or/p_con/p_exp)
  #' @param d 连续型预期效应(SMD, MCID)
  #' @param or,p_con,p_exp 二分类预期 OR 与对照/试验组事件率
  #' @param n_per_study 二分类每研究样本量（累积信息量单位）
  #' @param alpha 一类错误；side="two" 时使用 alpha/2
  #' @param power 目标功效
  #' @param side "two"(默认) | "one"
  #' @return list(RIS, accrued, info_frac, cum_Z, crossed, reached_RIS, conclusion, plot)
  effect_type <- match.arg(effect_type)
  side <- match.arg(side)
  Za <- if (side == "two") qnorm(1 - alpha / 2) else qnorm(1 - alpha)
  Zb <- qnorm(power)

  if (effect_type == "continuous") {
    if (!is.numeric(d) || d <= 0) stop("连续型需 d>0（预期 SMD / MCID）", call. = FALSE)
    RIS_info <- (Za + Zb)^2 / d^2          # 信息量单位（与 1/vi 一致）
    info_i   <- 1 / es_data$vi
  } else {
    if (is.null(or) || is.null(p_con) || is.null(p_exp) || is.null(n_per_study))
      stop("二分类需提供 or, p_con, p_exp, n_per_study", call. = FALSE)
    logOR    <- log(or)
    RIS_info <- (Za + Zb)^2 * (1 / p_con + 1 / p_exp) / logOR^2   # 人数单位
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
  concl   <- if (crossed) "已跨越监测边界 —— 达到确证证据，无需更多研究"
             else if (reached) "已累积至 RIS 但未跨越边界 —— 证据不足以确认效应"
             else "累积信息量未达 RIS —— 仍需更多研究"

  df <- data.frame(
    study     = if (!is.null(labels)) labels else 1:k,
    info_prop = f,
    cum_Z     = Z_cum,
    boundary  = boundary,
    stringsAsFactors = FALSE
  )
  cat("================================================\n")
  cat(" Trial Sequential Analysis (self-implemented)\n")
  cat("================================================\n")
  cat(sprintf(" Effect type     : %s\n", effect_type))
  cat(sprintf(" alpha / power   : %.3f / %.2f (%s-sided)\n", alpha, power, side))
  cat(sprintf(" Required Info   : %.1f (RIS)\n", RIS_info))
  cat(sprintf(" Accrued Info    : %.1f (%.1f%% of RIS)\n", I_acc[k], 100 * f[k]))
  cat(sprintf(" Crossed boundary: %s\n", crossed))
  cat(sprintf(" Conclusion      : %s\n", concl))
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
      labs(x = "Information fraction (I / RIS)",
           y = "Z-score",
           title = "Trial Sequential Analysis",
           subtitle = sprintf("RIS=%.0f, accrued=%.0f%% | %s",
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
  #' @title 剂量-反应关系 Meta 分析（dosresmeta，two-stage）
  #' @description 合并剂量与效应的关系。支持线性 / 二次曲线。
  #' @param yi   效应量列名：二分类为 logRR/logOR；连续型为均数（或均数差）。
  #' @param dose 剂量列名（连续变量）。
  #' @param id   研究标识列名；data 含上述所有列的数据框。
  #' @param outcome "binary"(默认，需 cases+n，se 或 v；study_design 指定设计) | "continuous"(需 sd+n)
  #' @param shape "linear"(默认，yi~dose) | "quadratic"(yi~dose+I(dose^2))
  #' @param se/v  二分类效应量的标准误 se（推荐）或方差 v（二选一）。
  #' @param sd    连续型：各剂量水平的标准差列名（配合 n）。
  #' @param cases 二分类：各剂量水平事件数列名（配合 n）。
  #' @param n     样本量列名（二分类/连续型均需）。
  #' @param study_design 二分类研究设计：数据列名（值为 cc/ci/ir）或统一字符串 "cc"/"ci"/"ir"。
  #' @param covariance 研究内协方差近似法。缺省：二分类 "gl"，连续型 "smd"。
  #'   合法值：gl / h / md / smd / user / indep（无 "ho"）。
  #' @note 关键区分：模型形状（线/曲）由 shape 控制并写入 formula；
  #'   dosresmeta 的 type 参数专指二分类的“研究设计”(cc/ci/ir)，二者不可混淆。
  .need_pkg("dosresmeta", "剂量反应 Meta")
  outcome <- match.arg(outcome)
  shape   <- match.arg(shape)

  # 缺省协方差近似法
  if (is.null(covariance))
    covariance <- if (outcome == "binary") "gl" else "smd"

  # 模型形状 → formula（线性 / 二次曲线）
  fml <- if (shape == "quadratic")
    as.formula(paste(yi, "~", dose, "+ I(", dose, "^2)"))
  else
    as.formula(paste(yi, "~", dose))

  # dosresmeta 使用非标准评估（NSE）：列名需以符号形式传入，
  # 故用 do.call + as.name 将字符串列名转为符号，data 直接传数据框对象。
  args <- list(formula = fml, id = as.name(id), data = data,
               covariance = covariance)

  if (outcome == "binary") {
    if (is.null(cases) || is.null(n))
      stop("二分类需提供 cases 与 n（事件数/样本量列名）", call. = FALSE)
    if (is.null(se) && is.null(v))
      stop("二分类需提供 se 或 v（效应量的标准误/方差）之一", call. = FALSE)
    args$cases <- as.name(cases); args$n <- as.name(n)
    if (!is.null(se)) args$se <- as.name(se) else args$v <- as.name(v)
    # 研究设计 type：列名(cc/ci/ir) 或统一字符串
    if (!is.null(study_design)) {
      args$type <- if (study_design %in% names(data))
        as.name(study_design) else study_design
    }
  } else {  # continuous
    if (is.null(sd) || is.null(n))
      stop("连续型需提供 sd 与 n（标准差/样本量列名）", call. = FALSE)
    args$sd <- as.name(sd); args$n <- as.name(n)
  }

  fit <- do.call(dosresmeta::dosresmeta, args)
  cat("================================================\n")
  cat(" Dose-Response Meta (dosresmeta)\n")
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
        labs(x = "Dose", y = "Effect (log scale)", title = "Dose-Response Relationship") +
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
  #' @title 聚合生存数据 Meta 分析（survmeta）
  #' @description 合并各研究 log(HR) 及其方差（来自 KM 曲线 / 生存摘要）。
  #' @param yi,vi 各研究 log(HR) 与方差（字符列名）；studlab 研究标签；data 数据框
  #' @param method 合并方法（DL 默认 | PM | REML | ML）
  #' @note survmeta 不在 CRAN 当前 R 二进制源；请在本机 install.packages("survmeta")
  .need_pkg("survmeta", "生存 Meta")
  method <- match.arg(method)
  fml <- as.formula(paste(yi, "~ 1"))
  fit <- survmeta::survmeta(formula = fml, var = vi, studlab = studlab,
                            data = data, method = method)
  cat("================================================\n")
  cat(" Survival Meta-Analysis (survmeta)\n")
  cat("================================================\n")
  print(summary(fit))
  return(fit)
}

# ============================================================================
# 11/12. 贝叶斯 NMA —— multinma(Stan) / gemtc(JAGS)
#         需本机安装 Stan(cmdstanr) 或 JAGS；沙盒无法编译，仅做封装 + 语法校验
# ============================================================================
run_bayes_nma_multinma <- function(prep, priors,
                                    response = c("events", "rate", "multinomial",
                                                 "continuous", "survival"),
                                    n = "n", study = "study", treatment = "treatment",
                                    distribution = c("binomial", "poisson", "normal",
                                                     "weibull"),
                                    chains = 4, iter = 4000, seed = 123) {
  #' @title 贝叶斯网络 Meta（multinma，Stan 后端）
  #' @param prep treatment_class() / set_agd_arm() 等准备的数据对象
  #' @param priors prior_normal()/prior_halfnormal() 等（用 + 组合）
  #' @param response 结局类型；distribution 似然
  #' @note 需本机安装 cmdstanr + Stan 工具链；首次运行会编译模型（耗时）
  .need_pkg("multinma", "贝叶斯 NMA (multinma)")
  response     <- match.arg(response)
  distribution <- match.arg(distribution)
  fit <- multinma::nma(
    prep,
    response     = response,
    n            = n,
    study        = study,
    treatment    = treatment,
    distribution = distribution,
    priors       = priors,
    chains       = chains,
    iter         = iter,
    seed         = seed
  )
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
  #' @title 贝叶斯网络 Meta（gemtc，JAGS 后端）
  #' @param data.ab 臂级数据；treatments/studies 水平向量
  #' @note 需本机安装 JAGS 并 install.packages("rjags")
  .need_pkg("gemtc", "贝叶斯 NMA (gemtc)")
  net <- gemtc::mtc.network(data.ab = data.ab, treatments = treatments,
                            studies = studies)
  model <- gemtc::mtc.model(net, type = type, link = link,
                             likelihood = likelihood, linearModel = linearModel,
                             om.scale = om.scale, dic = TRUE)
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
