suppressMessages(library(metafor))
source("scripts/meta_analysis_core.R")

cat("=== Test 1: Single subgroup ===\n")
data_sub <- data.frame(
  study = paste0("S", 1:8),
  event_exp = c(15, 20, 18, 22, 19, 17, 21, 16),
  n_exp = c(50, 60, 55, 58, 52, 48, 56, 50),
  event_ctrl = c(10, 12, 10, 15, 11, 9, 13, 10),
  n_ctrl = c(50, 60, 55, 58, 52, 48, 56, 50),
  region = rep("Asia", 8), stringsAsFactors = FALSE)
es <- calculate_effect_size(data_sub, "dichotomous", "OR")
res_sub <- run_subgroup_analysis(es, "region")
cat("Result:", class(res_sub), "\n")
cat("Q:", as.character(res_sub$between_group_Q), "\n")
cat("p:", as.character(res_sub$between_group_p), "\n")
