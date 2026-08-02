suppressMessages({
  library(metafor); library(meta); library(netmeta)
  library(ggplot2); library(gridExtra); library(svglite)
})
source("scripts/meta_analysis_core.R")
source("scripts/network_meta_analysis.R")

# 工具：每个用例独立 tryCatch，打印 PASS/FAIL
run_case <- function(n, desc, expr) {
  cat(sprintf("\n========== CASE %d: %s ==========\n", n, desc))
  res <- tryCatch({ expr(); "PASS" }, error = function(e) {
    cat("  >>> ERROR:", conditionMessage(e), "\n")
    "FAIL"
  })
  cat(sprintf("  [RESULT] %s\n", res))
  invisible(res)
}

# --- Case 4: k=3 二分类发表偏倚（trimfill 应跳过）---
run_case(4, "3 studies dichotomous publication bias", {
  d <- data.frame(
    study = paste0("S", 1:3),
    event_exp = c(15, 20, 18), n_exp = c(50, 60, 55),
    event_ctrl = c(10, 12, 10), n_ctrl = c(50, 60, 55))
  es <- calculate_effect_size(d, "dichotomous", "OR")
  m  <- run_meta_analysis(es)
  pb <- analyze_publication_bias(es, m)
  cat("  egger:", !is.null(pb$egger), "| begg:", !is.null(pb$begg),
      "| trimfill (should be absent):", is.null(pb$trimfill), "\n")
})

# --- Case 5: k=5 连续型 SMD + 森林图（transform='none' 陷阱）---
run_case(5, "5 studies continuous SMD + forest plot (transform=none)", {
  d <- data.frame(
    study = paste0("S", 1:5),
    n_exp = c(30,25,40,35,28), mean_exp = c(10.5,12.0,11.0,10.8,11.5), sd_exp = c(2.1,2.3,2.5,2.0,2.4),
    n_ctrl = c(30,25,40,35,28), mean_ctrl = c(9.0,10.0,9.5,9.2,9.8), sd_ctrl = c(1.8,2.0,2.2,1.9,2.1))
  res <- ma_analyze(d, "continuous", measure = "SMD")
  cat("  transform =", res$transform, "\n")
  p <- create_forest_plot(res$data, res, transform = res$transform)
  cat("  forest plot OK\n")
  pf <- create_funnel_plot(res, transform = res$transform)
  cat("  funnel plot OK\n")
})

# --- Case 6: 连续型 SMD 含 NA SD（order 边界）---
run_case(6, "continuous SMD with NA sd", {
  d <- data.frame(
    study = paste0("S", 1:4),
    n_exp = c(30,25,40,35), mean_exp = c(10.5,12.0,11.0,10.8), sd_exp = c(2.1,NA,2.5,2.0),
    n_ctrl = c(30,25,40,35), mean_ctrl = c(9.0,10.0,9.5,9.2), sd_ctrl = c(1.8,2.0,2.2,1.9))
  es <- calculate_effect_size(d, "continuous", "SMD")
  cat("  yi has NA:", any(is.na(es$yi)), "\n")
  m <- run_meta_analysis(es)
  cat("  model k (after na.omit):", m$k, "\n")
  p <- create_forest_plot(es, m, transform = "none")
  cat("  forest with NA OK\n")
})

# --- Case 7: 元回归含中文列名 ---
run_case(7, "meta-regression with Chinese column names", {
  d <- data.frame(
    study = paste0("S", 1:5),
    yi = c(0.5,0.6,0.4,0.7,0.3), vi = c(0.1,0.08,0.12,0.09,0.15),
    发表年份 = c(2018,2019,2020,2021,2022), 样本量 = c(100,120,80,150,90))
  res <- run_meta_regression(d, c("发表年份", "样本量"))
  cat("  meta-regression OK, coefs:", length(res$model$beta), "\n")
})

# --- Case 8: 网络 Meta 不连通 ---
run_case(8, "network meta disconnected (A-B vs C-D)", {
  d <- data.frame(
    study = c("St1","St2","St3","St4"),
    TE = c(0.5,0.4,-0.1,-0.05), seTE = c(0.2,0.25,0.3,0.22),
    treat1 = c("A","A","C","C"), treat2 = c("B","B","D","D"))
  net <- run_frequentist_nma(d, sm = "OR", reference.group = "A")
  cat("  netmeta ran; treatments:", paste(attr(net, "trts"), collapse = "/"), "\n")
  lt <- tryCatch(get_league_table(net), error = function(e) sprintf("league ERR: %s", conditionMessage(e)))
  cat("  league:", if (is.list(lt)) "OK" else lt, "\n")
})

# --- Case 9: 单组率 Meta ---
run_case(9, "single-group rate (PLO) meta", {
  d <- data.frame(
    study = paste0("S", 1:5),
    events = c(20,30,15,25,18), n = c(100,150,80,120,90))
  res <- ma_analyze(d, "single_proportion", measure = "PLO")
  cat("  transform =", res$transform, "\n")
  p <- create_forest_plot(res$data, res, transform = res$transform)
  cat("  forest OK\n")
  pf <- create_funnel_plot(res, transform = res$transform)
  cat("  funnel OK\n")
})

# --- Case 10: 一键出图 + 结果摘要（完整流程）---
run_case(10, "full pipeline ma_analyze + ma_save", {
  d <- data.frame(
    study = paste0("S", 1:4),
    event_exp = c(15,20,18,22), n_exp = c(50,60,55,58),
    event_ctrl = c(10,12,10,15), n_ctrl = c(50,60,55,58))
  res <- ma_analyze(d, "dichotomous", measure = "OR")
  ma_save(res, outdir = "output", prefix = "meta")
  cat("  files:", paste(list.files("output"), collapse = ", "), "\n")
})

cat("\n========== ALL CASES DONE ==========\n")
