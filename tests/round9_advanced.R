suppressMessages(library(metafor)); suppressMessages(library(meta)); suppressMessages(library(ggplot2))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R"); source("scripts/advanced_functions.R")

chk <- function(tag, d, expr, expect = "PASS") {
  r <- tryCatch({ force(expr); "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  ok <- (r == expect)
  cat(sprintf("[%s] %s -> %s %s\n", tag, d, r, if (ok) "" else paste("(expected", expect, ")")))
  invisible(NULL)
}

build_model <- function(k = 10, seed = 11) {
  set.seed(seed)
  es <- data.frame(study = paste0("S", 1:k),
    event_exp = sample(10:30, k), n_exp = rep(60, k),
    event_ctrl = sample(8:25, k), n_ctrl = rep(60, k))
  e <- calculate_effect_size(es, "dichotomous", "OR")
  run_meta_analysis(e)
}

cat("========== ROUND 9: Advanced / Bayesian ==========\n")
# Available (no optional pkg)
chk("R9-1", "plot_baujat (available)", { m <- build_model(10); plot_baujat(m) })
chk("R9-2", "run_gosh + plot_gosh (available)", {
  m <- build_model(12); g <- run_gosh(m); plot_gosh(g) })
chk("R9-3", "plot_drapery (available)", { m <- build_model(10); plot_drapery(m$data) })

# Bayesian guards (packages NOT installed -> friendly error expected)
chk("R9-4", "run_bayes_pairwise guard", {
  m <- build_model(10); run_bayes_pairwise(m$data) }, expect = "ERROR")
chk("R9-5", "run_bayes_nma_multinma guard", {
  run_bayes_nma_multinma(NULL) }, expect = "ERROR")
chk("R9-6", "run_bayes_nma_gemtc guard", {
  run_bayes_nma_gemtc(NULL, NULL, NULL) }, expect = "ERROR")
chk("R9-7", "run_diagnostic_meta guard", {
  run_diagnostic_meta(data.frame(TP=1,FP=1,FN=1,TN=1)) }, expect = "ERROR")

# Other optional-pkg advanced functions -> friendly guard expected
chk("R9-8", "run_power_curve", { run_power_curve() }, expect = "ERROR")
chk("R9-9", "run_tsa guard", {
  m <- build_model(10); run_tsa(m$data) }, expect = "ERROR")
chk("R9-10", "run_surv_meta guard", {
  run_surv_meta(0.3, 0.04, data=data.frame(study="a")) }, expect = "ERROR")
cat("=== DONE ===\n")
