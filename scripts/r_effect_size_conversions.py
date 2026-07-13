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

# ===================== esc 效应量包封装 =====================

run_esc_conversions <- function(data,
                                 input_type = "mean_sd",
                                 output_measure = "d",
                                 ...) {
  #' @title 统一效应量计算/转换接口
  #' @description 
  #'   基于 esc 包提供一站式效应量计算
  #'   input_type: "mean_sd", "t_test", "f_test", "cor", "or", "2x2"
  #'   output_measure: "d"(Hedges' g), "r", "or", "logor", "z"(Fisher)
  #' @param data 输入数据框（根据 input_type 格式不同）
  #' @param input_type 原始数据类型
  #' @param output_measure 目标效应量度量
  #' @param ... 额外参数（如 n, mean, sd, t, r, or, event, total 等）
  
  if (input_type == "mean_sd") {
    result <- esc_mean_sd(
      grp1m = data$mean_exp,
      grp1sd = data$sd_exp,
      grp1n = data$n_exp,
      grp2m = data$mean_ctrl,
      grp2sd = data$sd_ctrl,
      grp2n = data$n_ctrl,
      es.type = "d",              # "d" = Cohen's d (pooled SD)
      study = data$study,
      ...
    )
  } else if (input_type == "t_test") {
    result <- esc_t(
      t = data$t,
      grp1n = data$n_exp,
      grp2n = data$n_ctrl,
      es.type = "d",
      study = data$study,
      ...
    )
  } else if (input_type == "f_test") {
    result <- esc_F_stat(
      grp1n = data$n_exp,
      grp2n = data$n_ctrl,
      f = data$f_stat,
      es.type = "d",
      study = data$study,
      ...
    )
  } else if (input_type == "cor") {
    result <- esc_rcor(
      r = data$correlation,
      grp1n = data$n_exp,
      grp2n = data$n_ctrl,
      es.type = "d",
      study = data$study,
      ...
    )
  } else if (input_type == "or") {
    result <- esc_or(
      or = data$odds_ratio,
      se = data$se_or,
      es.type = "d",
      study = data$study,
      ...
    )
  } else if (input_type == "2x2") {
    result <- escalc(
      measure = "OR",
      ai = data$event_exp,
      n1i = data$n_exp,
      ci = data$event_ctrl,
      n2i = data$n_ctrl,
      data = data,
      include.yi = TRUE,
      slab = data$study,
      ...
    )
  } else if (input_type == "hr") {
    result <- escalc(
      measure = "HR",
      yi = data$ln_hr,
      sei = data$se_ln_hr,
      data = data,
      include.yi = TRUE,
      slab = data$study,
      ...
    )
  }
  
  # 输出
  output <- list()
  output$y <- result$yi        # 效应量
  output$vi <- result$vi       # 抽样方差
  
  cat("================================================\n")
  cat(" Effect Size Conversion (esc package)\n")
  cat(sprintf("  From: %s → To: %s\n", input_type, "yi + vi"))
  cat(sprintf("  Studies: %d\n", nrow(result)))
  cat(sprintf("  yi range: [%.3f, %.3f]\n",
              min(output$y), max(output$y)))
  cat("================================================\n")
  
  return(output)
}


# ===================== esc 效应量互转 =====================

run_esc_transform <- function(yi, vi, 
                                from_measure = "d",
                                to_measure = "logOR",
                                ...) {
  #' @title 效应量相互转换
  #' @description 
  #'   在不同效应量度量之间单向转换
  #'   支持：d (Hedges' g) ↔ logOR ↔ r (Fisher's z)
  #'   d → logOR → z 方向使用以下公式：
  #'   logOR = d * pi / sqrt(3)
  #'   z = 0.5 * log((1+r)/(1-r))
  #' @param yi 效应量
  #' @param vi 抽样方差
  
  from <- tolower(from_measure)
  to <- tolower(to_measure)
  
  result <- list()
  
  if (from == "d" & to == "logor") {
    # Hedges' g → log Odds Ratio (Chinn 2000)
    yi_new <- yi * pi / sqrt(3)
    vi_new <- vi * pi^2 / 3
  } else if (from == "logor" & to == "d") {
    # logOR → Hedges' g
    yi_new <- yi * sqrt(3) / pi
    vi_new <- vi * 3 / (pi^2)
  } else if (from == "d" & to == "cor") {
    # Hedges' g → Pearson r (Borenstein 2009)
    a <- 1  # 等样本的近似
    r <- yi / sqrt(yi^2 + a)
    yi_new <- 0.5 * log((1 + r) / (1 - r))  # Fisher's z
    vi_new <- vi / (1 - r^2)^2
  } else if (from == "cor" & to == "d") {
    # Fisher's z → Pearson r → Hedges' g
    r <- tanh(yi)
    yi_new <- 2 * r / sqrt(1 - r^2)  # rough conversion
    vi_new <- 4 * vi / (1 - r^2)^2
  } else if (from == "logor" & to == "cor") {
    # logOR → d → r
    d <- yi * sqrt(3) / pi
    a <- 1
    r <- d / sqrt(d^2 + a)
    yi_new <- 0.5 * log((1 + r) / (1 - r))
    vi_new <- vi * 3 / pi^2 * (1 / (1 - r^2))^2
  } else if (from == "cor" & to == "logor") {
    # r → d → logOR
    d <- tanh(yi) * 2  # rough
    yi_new <- d * pi / sqrt(3)
    vi_new <- (2 * vi / (1 - tanh(yi)^2)) * pi^2 / 3
  } else {
    cat(sprintf("Conversion from %s to %s may not be supported.\n",
                from_measure, to_measure))
    return(list(yi = yi, vi = vi))
  }
  
  result$yi <- yi_new
  result$vi <- vi_new
  result$from <- from_measure
  result$to <- to_measure
  
  cat(sprintf("Converted: %s → %s | yi: [%.3f, %.3f] → [%.3f, %.3f]\n",
              from_measure, to_measure,
              min(yi), max(yi),
              min(yi_new), max(yi_new)))
  
  return(result)
}


# ===================== Cohen's d → Hedges' g 校正 =====================

correct_d_to_g <- function(d, total_n, 
                            type = "Hedges_correction") {
  #' @title Cohen's d → Hedges' g 校正
  #' @description Cohen's d 是有偏估计，需校正为 Hedges' g
  #'              Hedges' g = J(df) × Cohen's d
  #'              J(df) ≈ 1 − 3/(4df − 1)
  #' @param d Cohen's d 值（向量）
  #' @param total_n 总样本量 N（用于计算 df）
  #' @param type 校正方法："Hedges_correction"(默认), "Glass_delta"
  
  if (type == "Hedges_correction") {
    df <- total_n - 2
    J <- 1 - 3 / (4 * df - 1)
    g <- J * d
    vi_g <- J^2 * vi
        
  } else if (type == "Glass_delta") {
    # 使用对照组 SD（不同时使用合并 SD）
    g <- d
    vi_g <- vi
  }
  
  cat("================================================\n")
  cat(" Cohen's d → Hedges' g correction\n")
  cat(sprintf("  Average J correction: %.4f\n", mean(J)))
  cat(sprintf("  Mean d: %.3f → Mean g: %.3f\n", mean(d), mean(g)))
  cat("================================================\n")
  
  return(list(g = g, vi = vi_g, J = J))
}


# ===================== 漏斗图坐标 =====================
# esc 包输出可直接用于漏斗图，无需二次处理
plot_funnel_esc <- function(yi, vi, refline = 0, ...) {
  se <- sqrt(vi)
  plot(yi ~ se, pch = 19, col = "blue", cex = 1/sqrt(vi) * 2,
       xlab = "Standard Error", ylab = "Effect Size",
       main = "Funnel Plot (esc coordinates)")
  abline(v = refline, lty = 2)
  abline(a = 0, b = 0, lty = 1, col = "gray")
  # 添加 95% CI 虚线
  polygon(c(refline + 1.96*seq(0, max(se), length.out=100),
           refline - 1.96*seq(max(se), 0, length.out=100)),
          c(seq(0, max(se), length.out=100),
           seq(max(se), 0, length.out=100)),
          col = adjustcolor("gray", alpha=0.3), border = NA)
}

# ============================================================================
# 聚类 / 稳健方差估计：clubSandwich + robumeta
# ============================================================================

# ===================== robumeta 一体化 =====================

run_robumeta <- function(data,
                          effect_col = "yi",
                          study_col = "study_id",
                          effect_id_col = "effect_id",
                          rho = 0.8, ...,
                          small = TRUE,
                          output = TRUE) {
  #' @title robumeta 分析流程
  #' @description 一站式运行 robu() 并生成完整报告
  #' @param data 数据框（含研究ID、效应ID、效应量）
  #' @param effect_col 效应量列名
  #' @param study_col 研究ID列名
  #' @param effect_id_col 效应ID列名（区分研究内多结局）
  #' @param rho tau² 估计的 within-study 相关（固定或 estomega）
  #' @param small 是否启用小样本校正（Satterthwaite）
  
  library(robumeta)
  
  # 准备数据格式
  robu_data <- data.frame(
    study_id = as.factor(data[[study_col]]),
    effect_id = as.factor(data[[effect_id_col]]),
    yi = data[[effect_col]],
    stringsAsFactors = FALSE
  )
  
  # A. 基础 robu 模型 (默认 Tech2)
  cat("================================================\n")
  cat(" robumeta: Robust Variance Estimation\n")
  cat("================================================\n")
  
  robu_fit <- robu(
    formula = yi ~ 1,
    data = robu_data,
    studynum = study_id,
    var.eff.weights = NULL,    # 使用抽样方差自动估计
    rho = rho,
    small = small,
    ...
  )
  
  # B. 输出
  cat("\n--- Basic Robu Model (Pearson RVE) ---\n")
  summary(robu_fit)
  
  # C. Fisher's z transformation variant (当效应量为 OR/HR 时)
  cat("\n--- Fisher's z RVE  ---\n")
  robu_z_data <- robu_data
  robu_z_data$yi <- 0.5 * log((1 + robu_data$yi) / (1 - robu_data$yi))
  
  robu_fit_z <- robu(
    formula = yi ~ 1,
    data = robu_z_data,
    studynum = study_id,
    rho = rho,
    small = small,
    ...
  )
  summary(robu_fit_z)
  
  return(invisible(list(
    robu = robu_fit,
    robu_z = robu_fit_z,
    data = robu_data
  )))
}


# ===================== clubSandwich + metafor 联合 =====================

run_metafor_robust <- function(data,
                                effect_col = "yi",
                                vi_col = "vi",
                                study_col = "study_id",
                                effect_id_col = "effect_id",
                                cluster_col = NULL,
                                correction_type = "CR2",
                                hc_type = "HC3",
                                level = 95) {
  #' @title metafor + clubSandwich 联合稳健分析
  #' @description 
  #'   拟合多元元分析模型后，使用 clubSandwich 计算稳健标准误
  #'   支持 CR0-CR4 多种小样本校正（CR2 推荐 + HC3 常用）
  #' @param data 数据框
  #' @param effect_col 效应量列名
  #' @param vi_col 方差列名
  #' @param study_col 研究ID列名
  #' @param effect_id_col 效应ID列名
  #' @param cluster_col 聚类变量列名（默认 = study_col）
  #' @param correction_type CR校正类型: "CR0","CR1","CR2","CR3","CR4"
  #' @param hc_type 异方差一致校正: "HC0"-"HC5"
  
  library(metafor)
  library(clubSandwich)
  
  if (is.null(cluster_col)) cluster_col <- study_col
  
  # Step 1: 基础 rma.mv
  mv_fit <- rma.mv(
    yi = data[[effect_col]],
    V = diag(data[[vi_col]]),
    random = ~ 1 | data[[study_col]] / data[[effect_id_col]],
    data = data,
    method = "REML",
    test = "t"
  )
  
  # Step 2: clubSandwich 稳健方差
  cat(sprintf("\n--- clubSandwich: %s robust SE\n", correction_type))
  
  robust_vcov <- vcovCR(
    mv_fit,
    cluster = data[[cluster_col]],
    type = correction_type
  )
  
  # Step 3: 替换方差矩阵（或直接用 coef_test）
  robust_test <- coef_test(
    mv_fit,
    vcov = robust_vcov,
    test = "Naive"
  )
  
  cat("\nStandard vs Robust Comparison:\n")
  cat(sprintf("  Standard: b = %.4f, SE = %.4f, p = %.4f\n",
              mv_fit$b, mv_fit$se, mv_fit$pval))
  cat(sprintf("  Robust(%s): b = %.4f, SE = %.4f, p = %.4f\n",
              correction_type,
              robust_test$estimate,
              robust_test$SE,
              robust_test$p))
  
  return(invisible(list(
    model = mv_fit,
    robust_vcov = robust_vcov,
    robust_test = robust_test
  )))
}


# ===================== V 矩阵手动构建 =====================

build_V_matrix_manual <- function(data,
                                   study_col = "study_id",
                                   effect_col = "yi",
                                   vi_col = "vi",
                                   rho = 0.8) {
  #' @title 手动构建 V 矩阵（研究内相关结构）
  #' @description 
  #'   对于同一研究内 k 个效应量，构建 V_i 矩阵:
  #'   V_i = [SE_j × SE_k × rho]
  #'   使用复合对称结构（默认 rho=0.8）
  #' @return 矩阵列表（每个研究一个）
  
  studies <- unique(data[[study_col]])
  V_list <- list()
  se <- sqrt(data[[vi_col]])
  
  for (s in studies) {
    idx <- which(data[[study_col]] == s)
    k <- length(idx)
    
    if (k == 1) {
      V_list[[s]] <- matrix(data[[vi_col]][idx], 1, 1)
    } else {
      se_vec <- se[idx]
      V_i <- outer(se_vec, se_vec, "*") * rho
      diag(V_i) <- data[[vi_col]][idx]  # 对角线 = 原始方差
      V_list[[s]] <- V_i
    }
  }
  
  return(V_list)
}


# ===================== 聚类调整的森林图 =====================

plot_robust_forest <- function(robu_fit,
                                 se_multiplier = 1.96,
                                 studies = NULL,
                                 ...) {
  #' @title robumeta 的稳健森林图
  #' @description 使用模型拟合值绘制森林图
  #' @param robu_fit robu 拟合结果
  #' @param se_multiplier 置信区间乘数（1.96 = 95%）
  
  # 提取拟合分量
  pred <- data.frame(
    study = robu_fit$study,
    yi = robu_fit$formula,  # y 值
    se = sqrt(robu_fit$var.eff.weights),
    tau = sqrt(sum(robu_fit$tau2))
  )
  
  library(ggplot2)
  
  p <- ggplot(pred, aes(x = yi, y = study)) +
    geom_point(size = 3) +
    geom_segment(aes(x = yi - se_multiplier * se,
                     xend = yi + se_multiplier * se,
                     y = study, yend = study)) +
    geom_vline(xintercept = robu_fit$b.r,
               color = "red", linetype = "dashed") +
    labs(title = "Robust Meta-Analysis (RVE) - 95% CI",
         x = "Effect Size",
         y = "Study") +
    theme_minimal()
  
  return(p)
}


# ===================== 效应量依赖结构探索 =====================

explore_dependence <- function(data,
                                effect_col = "yi",
                                vi_col = "vi",
                                study_col = "study_id") {
  #' @title 探索效应量的依赖结构
  #' @description 
  #'   输出: 每研究平均效应量数、within-study 相关性估计、
  #'         GOSH 图适用性等
  
  library(dplyr)
  
  study_summary <- data %>%
    group_by(.data[[study_col]]) %>%
    summarise(
      k = n(),
      mean_yi = mean(.data[[effect_col]]),
      mean_vi = mean(.data[[vi_col]]),
      .groups = "drop"
    )
  
  cat("================================================\n")
  cat(" Dependence Structure Exploration\n")
  cat("================================================\n")
  cat(sprintf("Total studies: %d\n", nrow(study_summary)))
  cat(sprintf("Mean effects per study: %.2f (max = %d)\n",
              mean(study_summary$k), max(study_summary$k)))
  cat(sprintf("Studies with k > 1: %d (%.1f%%)\n",
              sum(study_summary$k > 1),
              100 * mean(study_summary$k > 1)))
  
  # 建议
  if (mean(study_summary$k) > 1.5) {
    cat("\n⚠️  High dependence detected. Recommend:\n")
    cat("  1. robumeta::robu() for RVE\n")
    cat("  2. clubSandwich CR2 correction\n")
    cat("  3. rma.mv with V matrix\n")
  } else {
    cat("\n✓ Low dependence. Standard rma() is sufficient.\n")
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
