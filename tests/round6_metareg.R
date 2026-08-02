suppressMessages(library(metafor)); suppressMessages(library(meta)); suppressMessages(library(ggplot2))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R")

chk <- function(tag, d, expr) {
  r <- tryCatch({ x <- force(expr); if (is.null(x$model) && is.null(x$bubble_plot)) "PASS(no-obj)" else "PASS" },
                error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%s] %s -> %s\n", tag, d, r)); invisible(NULL)
}

base_es <- function(k = 12, seed = 3) {
  set.seed(seed)
  es <- data.frame(study = paste0("S", 1:k),
    event_exp = sample(10:30, k), n_exp = rep(60, k),
    event_ctrl = sample(8:25, k), n_ctrl = rep(60, k))
  e <- calculate_effect_size(es, "dichotomous", "OR")
  e$year <- sample(2000:2020, k, replace = TRUE)
  e$quality_score <- sample(1:10, k, replace = TRUE)
  e
}

cat("========== ROUND 6: Meta-regression ==========\n")
chk("R6-1", "single numeric covariate (bubble)", {
  e <- base_es(12); run_meta_regression(e, "year") })
chk("R6-2", "two covariates", {
  e <- base_es(14); run_meta_regression(e, c("year","quality_score")) })
chk("R6-3", "three covariates", {
  e <- base_es(16); e$size <- sample(c(1,2,3),16,replace=TRUE); run_meta_regression(e, c("year","quality_score","size")) })
chk("R6-4", "covariate with SPACE in name", {
  e <- base_es(12); names(e)[names(e)=="year"] <- "pub year"; run_meta_regression(e, "pub year") })
chk("R6-5", "categorical factor covariate", {
  e <- base_es(12); e$region <- sample(c("A","B","C"),12,replace=TRUE); e$region <- as.factor(e$region); run_meta_regression(e, "region") })
chk("R6-6", "interaction term", {
  e <- base_es(16); e$region <- sample(c("A","B"),16,replace=TRUE); run_meta_regression(e, c("year","region","year:region")) })
chk("R6-7", "covariate with zero variance (constant)", {
  e <- base_es(12); e$const <- rep(5, 12); run_meta_regression(e, "const") })
chk("R6-8", "covariate is character (not factor)", {
  e <- base_es(12); e$grp <- sample(c("x","y"),12,replace=TRUE); run_meta_regression(e, "grp") })
chk("R6-9", "covariate with NA values", {
  e <- base_es(12); e$year[c(2,5)] <- NA; run_meta_regression(e, "year") })
chk("R6-10", "empty covariates list", {
  e <- base_es(12); run_meta_regression(e, character(0)) })
cat("=== DONE ===\n")
