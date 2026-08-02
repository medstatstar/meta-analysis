suppressMessages(library(metafor)); suppressMessages(library(meta)); suppressMessages(library(ggplot2))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R")

pass <- function(tag, expr) {
  r <- tryCatch({ force(expr); "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%s] %s -> %s\n", tag, desc[[tag]], r))
}
desc <- new.env()
logk <- function(tag, d) { desc[[tag]] <- d }

# Helper: build a proper rma model
build_model <- function(k = 5, seed = 1) {
  set.seed(seed)
  es <- data.frame(
    study = paste0("S", 1:k),
    event_exp = sample(10:30, k), n_exp = rep(50, k),
    event_ctrl = sample(8:25, k), n_ctrl = rep(50, k))
  e <- calculate_effect_size(es, "dichotomous", "OR")
  run_meta_analysis(e)
}

cat("========== ROUND 4: Visualization (forest / funnel) ==========\n")

logk("R4-1", "forest: default transform=none, k=5"); pass("R4-1", {
  m <- build_model(5); p <- create_forest_plot(m$data, m); print(class(p)) })
logk("R4-2", "forest: transform=exp (OR)"); pass("R4-2", {
  m <- build_model(5); p <- create_forest_plot(m$data, m, transform="exp"); print(class(p)) })
logk("R4-3", "forest: transform=tanh (correlation)"); pass("R4-3", {
  m <- build_model(5); p <- create_forest_plot(m$data, m, transform="tanh"); print(class(p)) })
logk("R4-4", "forest: transform=plogis (proportion)"); pass("R4-4", {
  m <- build_model(5); p <- create_forest_plot(m$data, m, transform="plogis"); print(class(p)) })
logk("R4-5", "forest: NA in yi (one missing study)"); pass("R4-5", {
  m <- build_model(6); m$data$yi[3] <- NA; m$data$vi[3] <- NA
  p <- create_forest_plot(m$data, m); print(class(p)) })
logk("R4-6", "forest: zero variance (vi=0 -> Inf weight)"); pass("R4-6", {
  m <- build_model(5); m$data$vi[1] <- 0
  p <- create_forest_plot(m$data, m); print(class(p)) })
logk("R4-7", "forest: extreme CI (ci.ub = Inf)"); pass("R4-7", {
  m <- build_model(5); m$ci.ub <- Inf
  p <- create_forest_plot(m$data, m); print(class(p)) })
logk("R4-8", "funnel: default + regtest/ranktest"); pass("R4-8", {
  m <- build_model(7); p <- create_funnel_plot(m); print(class(p)) })
logk("R4-9", "funnel: identical SE (regtest fails, tryCatch)"); pass("R4-9", {
  m <- build_model(5); m$vi <- rep(0.04, 5)
  p <- create_funnel_plot(m); print(class(p)) })
logk("R4-10", "forest: study label contains 'Pooled'/'\u5408\u5e76'"); pass("R4-10", {
  m <- build_model(4); m$data$study[2] <- "\u5408\u5e76"
  p <- create_forest_plot(m$data, m); print(class(p)) })

# Additional probe: invalid transform
logk("R4-P1", "forest: invalid transform='log'"); pass("R4-P1", {
  m <- build_model(5); p <- create_forest_plot(m$data, m, transform="log"); print(class(p)) })

cat("\n=== DONE ===\n")
