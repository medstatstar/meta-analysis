suppressMessages(library(metafor)); suppressMessages(library(meta))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R")

chk <- function(tag, d, expr) {
  r <- tryCatch({ force(expr); "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%s] %s -> %s\n", tag, d, r)); invisible(NULL)
}

base_es <- function(k = 10, seed = 2) {
  set.seed(seed)
  es <- data.frame(study = paste0("S", 1:k),
    event_exp = sample(10:30, k), n_exp = rep(60, k),
    event_ctrl = sample(8:25, k), n_ctrl = rep(60, k))
  e <- calculate_effect_size(es, "dichotomous", "OR")
  e$region <- sample(c("Asia", "Europe"), k, replace = TRUE)
  e
}

cat("========== ROUND 5: Subgroup analysis ==========\n")
chk("R5-1", "2 subgroups balanced", {
  e <- base_es(10); run_subgroup_analysis(e, "region") })
chk("R5-2", "3 subgroups", {
  e <- base_es(12); e$region <- sample(c("A","B","C"), 12, replace=TRUE); run_subgroup_analysis(e, "region") })
chk("R5-3", "4 subgroups", {
  e <- base_es(16); e$region <- sample(LETTERS[1:4], 16, replace=TRUE); run_subgroup_analysis(e, "region") })
chk("R5-4", "single subgroup (Bug#11 regression)", {
  e <- base_es(8); e$region <- rep("Asia", 8); run_subgroup_analysis(e, "region") })
chk("R5-5", "one subgroup has k=1", {
  e <- base_es(7); e$region <- c(rep("A",6), "B"); run_subgroup_analysis(e, "region") })
chk("R5-6", "numeric group codes", {
  e <- base_es(10); e$grp <- sample(c(1,2), 10, replace=TRUE); run_subgroup_analysis(e, "grp") })
chk("R5-7", "group_var with SPACE in name", {
  e <- base_es(10); names(e)[names(e)=="region"] <- "study region"
  run_subgroup_analysis(e, "study region") })
chk("R5-8", "NA in group_var (silent drop?)", {
  e <- base_es(10); e$region[c(3,7)] <- NA; res <- run_subgroup_analysis(e, "region")
  cat("  rows in es_data:", nrow(e), "| rows in subgroup_effects:", nrow(res$subgroup_effects), "\n") })
chk("R5-9", "group with zero variance (all same yi)", {
  e <- base_es(8); e$yi[1:4] <- 0.5; e$region <- c(rep("A",4), rep("B",4)); run_subgroup_analysis(e, "region") })
chk("R5-10", "non-existent group_var", {
  e <- base_es(10); run_subgroup_analysis(e, "nonexistent") })
cat("=== DONE ===\n")
