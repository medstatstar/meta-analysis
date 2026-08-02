suppressMessages(library(metafor))
source("scripts/meta_analysis_core.R")

cat("=== Test 1: Single subgroup (Bug #11) ===\n")
data_sub <- data.frame(
  study = paste0("S", 1:8),
  event_exp = c(15, 20, 18, 22, 19, 17, 21, 16),
  n_exp = c(50, 60, 55, 58, 52, 48, 56, 50),
  event_ctrl = c(10, 12, 10, 15, 11, 9, 13, 10),
  n_ctrl = c(50, 60, 55, 58, 52, 48, 56, 50),
  region = rep("Asia", 8), stringsAsFactors = FALSE)
es <- calculate_effect_size(data_sub, "dichotomous", "OR")
res_sub <- tryCatch(run_subgroup_analysis(es, "region"), error = function(e) e)
if (inherits(res_sub, "error")) { cat("ERROR:", conditionMessage(res_sub), "\n") }
else { cat("OK | Q =", res_sub$between_group_Q, "| p =", res_sub$between_group_p, "\n") }

cat("\n=== Test 2: quality character (Bug #17) ===\n")
data_q <- data.frame(
  study = paste0("S", 1:5),
  yi = c(0.5, 0.6, 0.4, 0.7, 0.3), vi = c(0.1, 0.08, 0.12, 0.09, 0.15),
  quality = c("low risk", "low risk", "high risk", "low risk", "unclear"),
  stringsAsFactors = FALSE)
res_q <- tryCatch(run_sensitivity_analysis(data_q, "quality"), error = function(e) e)
if (inherits(res_q, "error")) { cat("ERROR:", conditionMessage(res_q), "\n") }
else { cat("OK | high_quality:", !is.null(res_q$high_quality), "\n") }

cat("\n=== Test 3: quality numeric (Bug #17) ===\n")
data_qn <- data.frame(
  study = paste0("S", 1:5),
  yi = c(0.5, 0.6, 0.4, 0.7, 0.3), vi = c(0.1, 0.08, 0.12, 0.09, 0.15),
  quality = c(6, 7, 4, 6, 5), stringsAsFactors = FALSE)
res_qn <- tryCatch(run_sensitivity_analysis(data_qn, "quality"), error = function(e) e)
if (inherits(res_qn, "error")) { cat("ERROR:", conditionMessage(res_qn), "\n") }
else { cat("OK | high_quality:", !is.null(res_qn$high_quality), "\n") }
