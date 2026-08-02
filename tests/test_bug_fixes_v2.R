suppressMessages(library(metafor))
suppressMessages(library(meta))
suppressMessages(library(netmeta))

# ============================================================================
# Bug C verification: core script must be self-contained (no external .msg)
# Source ONLY meta_analysis_core.R, then call analyze_heterogeneity
# ============================================================================
cat("=== Bug C: self-contained core script (only meta_analysis_core.R sourced) ===\n")
source("scripts/meta_analysis_core.R")
d <- data.frame(
  study = paste0("S", 1:4),
  event_exp = c(15, 20, 18, 22), n_exp = c(50, 60, 55, 58),
  event_ctrl = c(10, 12, 10, 15), n_ctrl = c(50, 60, 55, 58))
es <- calculate_effect_size(d, "dichotomous", "OR")
m <- run_meta_analysis(es)
r <- tryCatch(analyze_heterogeneity(m), error = function(e) conditionMessage(e))
if (is.character(r)) {
  cat("RESULT: ERROR ->", r, "\n")
} else {
  cat("RESULT: OK (heterogeneity I2 =", round(r$I2, 2), ")\n")
}

# ============================================================================
# Bug B verification: disconnected network must yield friendly bilingual error
# ============================================================================
cat("\n=== Bug B: disconnected network (two separate sub-networks) ===\n")
source("scripts/network_meta_analysis.R")
nma_data <- data.frame(
  study = c("Study1", "Study2"),
  treat1 = c("A", "C"),
  treat2 = c("B", "D"),
  TE = c(0.30, 0.10),
  seTE = c(0.15, 0.20),
  stringsAsFactors = FALSE)
res <- tryCatch(run_frequentist_nma(nma_data, sm = "OR"),
                error = function(e) conditionMessage(e))
cat("RESULT:", res, "\n")
if (grepl("disconnected|不连通", res)) {
  cat("VERDICT: PASS — friendly bilingual error captured\n")
} else {
  cat("VERDICT: FAIL — raw error not captured\n")
}

# Connected network sanity check (should succeed)
cat("\n=== Sanity: connected network (single chain A-B-C) ===\n")
nma_ok <- data.frame(
  study = c("S1", "S2", "S3"),
  treat1 = c("A", "B", "C"),
  treat2 = c("B", "C", "A"),
  TE = c(0.30, 0.10, 0.05),
  seTE = c(0.15, 0.20, 0.18),
  stringsAsFactors = FALSE)
res_ok <- tryCatch(run_frequentist_nma(nma_ok, sm = "OR"),
                   error = function(e) conditionMessage(e))
if (is.character(res_ok)) {
  cat("RESULT: ERROR ->", res_ok, "\n")
} else {
  cat("RESULT: OK (treatments:", paste(res_ok$trts, collapse = "/"), ")\n")
}
