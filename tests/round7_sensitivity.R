suppressMessages(library(metafor)); suppressMessages(library(meta))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R")

chk <- function(tag, d, expr) {
  r <- tryCatch({ force(expr); "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%s] %s -> %s\n", tag, d, r)); invisible(NULL)
}

build <- function(k, seed = 7) {
  set.seed(seed)
  es <- data.frame(study = paste0("S", 1:k),
    event_exp = sample(10:30, k), n_exp = rep(60, k),
    event_ctrl = sample(8:25, k), n_ctrl = rep(60, k))
  e <- calculate_effect_size(es, "dichotomous", "OR")
  m <- run_meta_analysis(e)
  list(e = e, m = m)
}

cat("========== ROUND 7: Sensitivity + Publication bias ==========\n")
# Publication bias
chk("R7-1", "pub bias k=10 (normal)", {
  b <- build(10); analyze_publication_bias(b$e, b$m) })
chk("R7-2", "pub bias k=5 (small)", {
  b <- build(5); analyze_publication_bias(b$e, b$m) })
chk("R7-3", "pub bias k=3 (minimal)", {
  b <- build(3); analyze_publication_bias(b$e, b$m) })
chk("R7-4", "pub bias: all identical SE (regtest may fail)", {
  b <- build(8); b$m$vi <- rep(0.05, 8); analyze_publication_bias(b$e, b$m) })

# Sensitivity
chk("R7-5", "sensitivity all", {
  b <- build(10); run_sensitivity_analysis(b$e, "all") })
chk("R7-6", "sensitivity leave1out", {
  b <- build(8); run_sensitivity_analysis(b$e, "leave1out") })
chk("R7-7", "sensitivity quality (character)", {
  b <- build(8); b$e$quality <- sample(c("low risk","high risk","unclear"),8,replace=TRUE)
  run_sensitivity_analysis(b$e, "quality") })
chk("R7-8", "sensitivity quality numeric <3 high", {
  b <- build(8); b$e$quality <- c(7,2,3,4,5,6,7,2)
  run_sensitivity_analysis(b$e, "quality") })
chk("R7-9", "sensitivity model_comparison", {
  b <- build(10); run_sensitivity_analysis(b$e, "model_comparison") })
chk("R7-10", "sensitivity cumul", {
  b <- build(9); run_sensitivity_analysis(b$e, "cumul") })
cat("=== DONE ===\n")
