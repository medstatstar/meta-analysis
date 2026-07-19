# -*- coding: utf-8 -*-
# AUTO-GENERATED from effect_size_conversions.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_effect_size_conversions.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "effect_size_conversions.R"

R_SOURCE = r'''# ============================================================================
# 效应量转换与聚类/依赖数据的稳健方差估计
#   esc 包：效应量计算与相互转换
#   clubSandwich：聚类稳健方差估计
#   robumeta：基于 Fisher-z 的稳健方差估计
# ============================================================================

# --- 双语语言检测（默认英文，中文环境切中文） ---
.MA_LANG <- local({
  lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
  if (grepl("zh|cn|chs", lang)) "zh" else "en"
})
.msg <- function(en, zh) if (.MA_LANG == "zh") zh else en

# ===================== esc 效应量包封装 =====================

run_esc_conversions <- function(data, input_type = "mean_sd", output_measure = "d", ...) {
  if (input_type == "mean_sd") {
    result <- esc_mean_sd(grp1m = data$mean_exp, grp1sd = data$sd_exp, grp1n = data$n_exp,
                           grp2m = data$mean_ctrl, grp2sd = data$sd_ctrl, grp2n = data$n_ctrl,
                           es.type = "d", study = data$study, ...)
  } else if (input_type == "t_test") {
    result <- esc_t(t = data$t, grp1n = data$n_exp, grp2n = data$n_ctrl, es.type = "d",
                    study = data$study, ...)
  } else if (input_type == "f_test") {
    result <- esc_F_stat(grp1n = data$n_exp, grp2n = data$n_ctrl, f = data$f_stat,
                         es.type = "d", study = data$study, ...)
  } else if (input_type == "cor") {
    result <- esc_rcor(r = data$correlation, grp1n = data$n_exp, grp2n = data$n_ctrl,
                       es.type = "d", study = data$study, ...)
  } else if (input_type == "or") {
    result <- esc_or(or = data$odds_ratio, se = data$se_or, es.type = "d",
                     study = data$study, ...)
  } else if (input_type == "2x2") {
    result <- escalc(measure = "OR", ai = data$event_exp, n1i = data$n_exp,
                     ci = data$event_ctrl, n2i = data$n_ctrl, data = data,
                     include.yi = TRUE, slab = data$study, ...)
  } else if (input_type == "hr") {
    result <- escalc(measure = "HR", yi = data$ln_hr, sei = data$se_ln_hr,
                     data = data, include.yi = TRUE, slab = data$study, ...)
  }
  
  output <- list()
  output$y <- result$yi
  output$vi <- result$vi
  
  cat("================================================\n")
  cat(.msg(" Effect Size Conversion (esc package)\n", " 效应量转换（esc 包）\n"))
  cat(sprintf(.msg("  From: %s → To: %s\n", "  从：%s → 转换为：%s\n"), input_type, "yi + vi"))
  cat(sprintf(.msg("  Studies: %d\n", "  研究数：%d\n"), nrow(result)))
  cat(sprintf(.msg("  yi range: [%.3f, %.3f]\n", "  yi 范围：[%.3f, %.3f]\n"),
              min(output$y), max(output$y)))
  cat("================================================\n")
  
  return(output)
}


# ===================== esc 效应量互转 =====================

run_esc_transform <- function(yi, vi, from_measure = "d", to_measure = "logOR", a = 4, ...) {
  from <- tolower(from_measure); to <- tolower(to_measure)
  
  .d_to_logor <- function(d, vd) { list(yi = d * pi / sqrt(3), vi = vd * pi^2 / 3) }
  .logor_to_d <- function(lor, vlor) { list(yi = lor * sqrt(3) / pi, vi = vlor * 3 / pi^2) }
  .d_to_z <- function(d, vd) {
    r  <- d / sqrt(d^2 + a); vr <- a^2 * vd / (d^2 + a)^3
    z  <- atanh(r); vz <- vr / (1 - r^2)^2; list(yi = z, vi = vz)
  }
  .z_to_d <- function(z, vz) {
    r  <- tanh(z); vr <- vz * (1 - r^2)^2
    d  <- 2 * r / sqrt(1 - r^2); vd <- 4 * vr / (1 - r^2)^3; list(yi = d, vi = vd)
  }
  
  if (from == to) {
    out <- list(yi = yi, vi = vi)
  } else if (from == "d" & to == "logor") {
    out <- .d_to_logor(yi, vi)
  } else if (from == "logor" & to == "d") {
    out <- .logor_to_d(yi, vi)
  } else if (from == "d" & to == "cor") {
    out <- .d_to_z(yi, vi)
  } else if (from == "cor" & to == "d") {
    out <- .z_to_d(yi, vi)
  } else if (from == "logor" & to == "cor") {
    tmp <- .logor_to_d(yi, vi); out <- .d_to_z(tmp$yi, tmp$vi)
  } else if (from == "cor" & to == "logor") {
    tmp <- .z_to_d(yi, vi); out <- .d_to_logor(tmp$yi, tmp$vi)
  } else {
    cat(sprintf(.msg("Conversion from %s to %s not supported (use d / logor / cor).\n",
                     "不支持 %s 到 %s 的转换（请使用 d / logor / cor）。\n"),
                from_measure, to_measure))
    return(list(yi = yi, vi = vi))
  }
  
  result <- list(yi = out$yi, vi = out$vi, from = from_measure, to = to_measure)
  
  cat(sprintf(.msg("Converted: %s → %s | yi: [%.3f, %.3f] → [%.3f, %.3f]\n",
                   "转换：%s → %s | yi: [%.3f, %.3f] → [%.3f, %.3f]\n"),
              from_measure, to_measure, min(yi), max(yi), min(out$yi), max(out$yi)))
  
  return(result)
}


# ===================== Cohen's d → Hedges' g 校正 =====================

correct_d_to_g <- function(d, total_n, vi = NULL, type = "Hedges_correction") {
  df <- total_n - 2; J <- 1 - 3 / (4 * df - 1)
  
  if (is.null(vi)) {
    vi <- 4 / total_n * (1 + d^2 / 8)
    message(.msg("vi not provided, using equal-group approximation vi_d = 4/N*(1 + d^2/8)",
                 "未提供 vi，已用等分组近似 vi_d = 4/N*(1 + d²/8)"))
  }
  
  if (type == "Hedges_correction") {
    g <- J * d; vi_g <- J^2 * vi
  } else if (type == "Glass_delta") {
    g <- d; vi_g <- vi
  } else {
    stop(.msg("type not supported: ", "不支持的 type："), type)
  }
  
  cat("================================================\n")
  cat(.msg(" Cohen's d → Hedges' g correction\n", " Cohen's d → Hedges' g 校正\n"))
  cat(sprintf(.msg("  Average J correction: %.4f\n", "  平均 J 校正：%.4f\n"), mean(J)))
  cat(sprintf(.msg("  Mean d: %.3f → Mean g: %.3f\n", "  平均 d: %.3f → 平均 g: %.3f\n"),
              mean(d), mean(g)))
  cat("================================================\n")
  
  return(list(g = g, vi = vi_g, J = J))
}


# ===================== 漏斗图坐标 =====================
plot_funnel_esc <- function(yi, vi, refline = 0, ...) {
  se <- sqrt(vi)
  plot(yi ~ se, pch = 19, col = "blue", cex = 1/sqrt(vi) * 2,
       xlab = .msg("Standard Error", "标准误"), ylab = .msg("Effect Size", "效应量"),
       main = .msg("Funnel Plot (esc coordinates)", "漏斗图（esc 坐标）"))
  abline(v = refline, lty = 2)
  abline(a = 0, b = 0, lty = 1, col = "gray")
  polygon(c(refline + 1.96*seq(0, max(se), length.out=100),
           refline - 1.96*seq(max(se), 0, length.out=100)),
          c(seq(0, max(se), length.out=100), seq(max(se), 0, length.out=100)),
          col = adjustcolor("gray", alpha=0.3), border = NA)
}

# ============================================================================
# 聚类 / 稳健方差估计：clubSandwich + robumeta
# ============================================================================

# ===================== robumeta 一体化 =====================

run_robumeta <- function(data, effect_col = "yi", study_col = "study_id",
                          effect_id_col = "effect_id", rho = 0.8, ...,
                          small = TRUE, output = TRUE) {
  library(robumeta)
  
  robu_data <- data.frame(
    study_id = as.factor(data[[study_col]]),
    effect_id = as.factor(data[[effect_id_col]]),
    yi = data[[effect_col]], stringsAsFactors = FALSE)
  
  cat("================================================\n")
  cat(.msg(" robumeta: Robust Variance Estimation\n",
           " robumeta：稳健方差估计（RVE）\n"))
  cat("================================================\n")
  
  robu_fit <- robu(formula = yi ~ 1, data = robu_data, studynum = study_id,
                   var.eff.weights = NULL, rho = rho, small = small, ...)
  
  cat(.msg("\n--- Basic Robu Model (Pearson RVE) ---\n",
           "\n--- 基础 robu 模型（Pearson RVE） ---\n"))
  summary(robu_fit)
  
  cat(.msg("\n--- Fisher's z RVE  ---\n", "\n--- Fisher's z RVE  ---\n"))
  robu_z_data <- robu_data
  robu_z_data$yi <- 0.5 * log((1 + robu_data$yi) / (1 - robu_data$yi))
  robu_fit_z <- robu(formula = yi ~ 1, data = robu_z_data, studynum = study_id,
                     rho = rho, small = small, ...)
  summary(robu_fit_z)
  
  return(invisible(list(robu = robu_fit, robu_z = robu_fit_z, data = robu_data)))
}


# ===================== clubSandwich + metafor 联合 =====================

run_metafor_robust <- function(data, effect_col = "yi", vi_col = "vi",
                                study_col = "study_id", effect_id_col = "effect_id",
                                cluster_col = NULL, correction_type = "CR2",
                                hc_type = "HC3", level = 95) {
  library(metafor)
  library(clubSandwich)
  
  if (is.null(cluster_col)) cluster_col <- study_col
  
  mv_fit <- rma.mv(yi = data[[effect_col]], V = diag(data[[vi_col]]),
                   random = ~ 1 | data[[study_col]] / data[[effect_id_col]],
                   data = data, method = "REML", test = "t")
  
  cat(sprintf(.msg("\n--- clubSandwich: %s robust SE\n",
                   "\n--- clubSandwich：%s 稳健 SE\n"), correction_type))
  
  robust_vcov <- vcovCR(mv_fit, cluster = data[[cluster_col]], type = correction_type)
  robust_test <- coef_test(mv_fit, vcov = robust_vcov, test = "Naive")
  
  cat(.msg("\nStandard vs Robust Comparison:\n", "\n标准 vs 稳健比较：\n"))
  cat(sprintf(.msg("  Standard: b = %.4f, SE = %.4f, p = %.4f\n",
                   "  标准：b = %.4f，SE = %.4f，p = %.4f\n"),
              mv_fit$b, mv_fit$se, mv_fit$pval))
  cat(sprintf(.msg("  Robust(%s): b = %.4f, SE = %.4f, p = %.4f\n",
                   "  稳健（%s）：b = %.4f，SE = %.4f，p = %.4f\n"),
              correction_type, robust_test$estimate, robust_test$SE, robust_test$p))
  
  return(invisible(list(model = mv_fit, robust_vcov = robust_vcov, robust_test = robust_test)))
}


# ===================== V 矩阵手动构建 =====================

build_V_matrix_manual <- function(data, study_col = "study_id",
                                   effect_col = "yi", vi_col = "vi", rho = 0.8) {
  studies <- unique(data[[study_col]]); V_list <- list()
  se <- sqrt(data[[vi_col]])
  for (s in studies) {
    idx <- which(data[[study_col]] == s); k <- length(idx)
    if (k == 1) {
      V_list[[s]] <- matrix(data[[vi_col]][idx], 1, 1)
    } else {
      se_vec <- se[idx]
      V_i <- outer(se_vec, se_vec, "*") * rho
      diag(V_i) <- data[[vi_col]][idx]
      V_list[[s]] <- V_i
    }
  }
  return(V_list)
}


# ===================== 聚类调整的森林图 =====================

plot_robust_forest <- function(robu_fit, se_multiplier = 1.96, studies = NULL, ...) {
  pred <- data.frame(
    study = robu_fit$study, yi = robu_fit$formula,
    se = sqrt(robu_fit$var.eff.weights), tau = sqrt(sum(robu_fit$tau2)))
  library(ggplot2)
  p <- ggplot(pred, aes(x = yi, y = study)) +
    geom_point(size = 3) +
    geom_segment(aes(x = yi - se_multiplier * se, xend = yi + se_multiplier * se,
                     y = study, yend = study)) +
    geom_vline(xintercept = robu_fit$b.r, color = "red", linetype = "dashed") +
    labs(title = .msg("Robust Meta-Analysis (RVE) - 95% CI",
                      "稳健 Meta 分析（RVE）— 95% CI"),
         x = .msg("Effect Size", "效应量"), y = .msg("Study", "研究")) +
    theme_minimal()
  return(p)
}


# ===================== 效应量依赖结构探索 =====================

explore_dependence <- function(data, effect_col = "yi", vi_col = "vi",
                                study_col = "study_id") {
  library(dplyr)
  study_summary <- data %>%
    group_by(.data[[study_col]]) %>%
    summarise(k = n(), mean_yi = mean(.data[[effect_col]]),
              mean_vi = mean(.data[[vi_col]]), .groups = "drop")
  
  cat("================================================\n")
  cat(.msg(" Dependence Structure Exploration\n", " 依赖结构探索\n"))
  cat("================================================\n")
  cat(sprintf(.msg("Total studies: %d\n", "研究总数：%d\n"), nrow(study_summary)))
  cat(sprintf(.msg("Mean effects per study: %.2f (max = %d)\n",
                   "每研究平均效应量：%.2f（最大值 = %d）\n"),
              mean(study_summary$k), max(study_summary$k)))
  cat(sprintf(.msg("Studies with k > 1: %d (%.1f%%)\n",
                   "k > 1 的研究：%d（%.1f%%）\n"),
              sum(study_summary$k > 1), 100 * mean(study_summary$k > 1)))
  
  if (mean(study_summary$k) > 1.5) {
    cat(.msg("\n⚠️  High dependence detected. Recommend:\n",
             "\n⚠️ 检测到高依赖性。建议：\n"))
    cat(.msg("  1. robumeta::robu() for RVE\n", "  1. robumeta::robu()（RVE）\n"))
    cat(.msg("  2. clubSandwich CR2 correction\n", "  2. clubSandwich CR2 校正\n"))
    cat(.msg("  3. rma.mv with V matrix\n", "  3. rma.mv（含 V 矩阵）\n"))
  } else {
    cat(.msg("\n✓ Low dependence. Standard rma() is sufficient.\n",
             "\n✓ 低依赖性。标准 rma() 已足够。\n"))
  }
  
  return(invisible(study_summary))
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
