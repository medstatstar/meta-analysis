suppressMessages(library(metafor))
source("scripts/meta_analysis_core.R")

cat("=== Test 2: quality character (Bug #17) ===\n")
data_q <- data.frame(
  study = paste0("S", 1:5),
  yi = c(0.5, 0.6, 0.4, 0.7, 0.3),
  vi = c(0.1, 0.08, 0.12, 0.09, 0.15),
  quality = c("low risk", "low risk", "high risk", "low risk", "unclear"),
  stringsAsFactors = FALSE)
res_q <- run_sensitivity_analysis(data_q, "quality")
cat("Result:", class(res_q), "\n")
cat("high_quality exists:", !is.null(res_q$high_quality), "\n")

cat("\n=== Test 3: quality numeric (Bug #17) ===\n")
data_qn <- data.frame(
  study = paste0("S", 1:5),
  yi = c(0.5, 0.6, 0.4, 0.7, 0.3),
  vi = c(0.1, 0.08, 0.12, 0.09, 0.15),
  quality = c(6, 7, 4, 6, 5),
  stringsAsFactors = FALSE)
res_qn <- run_sensitivity_analysis(data_qn, "quality")
cat("Result:", class(res_qn), "\n")
cat("high_quality exists:", !is.null(res_qn$high_quality), "\n")
