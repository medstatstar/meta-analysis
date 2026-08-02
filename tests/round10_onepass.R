suppressMessages(library(metafor)); suppressMessages(library(meta)); suppressMessages(library(ggplot2))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R"); source("scripts/advanced_functions.R")

chk <- function(tag, d, expr) {
  r <- tryCatch({ force(expr); "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%s] %s -> %s\n", tag, d, r)); invisible(NULL)
}

mk <- function(k = 10, seed = 13) {
  set.seed(seed)
  data.frame(study = paste0("S", 1:k),
    event_exp = sample(10:30, k), n_exp = rep(60, k),
    event_ctrl = sample(8:25, k), n_ctrl = rep(60, k))
}

cat("========== ROUND 10: One-click flow (ma_analyze / ma_save) ==========\n")
chk("R10-1", "ma_analyze dichotomous OR", { ma_analyze(mk(10), "dichotomous", "OR") })
chk("R10-2", "ma_analyze continuous SMD", {
  set.seed(14); d <- data.frame(study=paste0("S",1:10), n_exp=rep(30,10), mean_exp=runif(10,10,12), sd_exp=rep(2,10), n_ctrl=rep(30,10), mean_ctrl=runif(10,9,11), sd_ctrl=rep(2,10)); ma_analyze(d,"continuous","SMD") })
chk("R10-3", "ma_analyze rate IRR", {
  set.seed(15); d <- data.frame(study=paste0("S",1:10), a=sample(5:20,10), b=rep(100,10), c=sample(5:20,10), d=rep(100,10)); ma_analyze(d,"rate","IRR") })
chk("R10-4", "ma_analyze correlation ZCOR", {
  set.seed(16); d <- data.frame(study=paste0("S",1:10), r=runif(10,0.1,0.6), n=rep(50,10)); ma_analyze(d,"correlation","ZCOR") })
chk("R10-5", "ma_analyze single_proportion PLO", {
  set.seed(17); d <- data.frame(study=paste0("S",1:10), events=sample(5:20,10), n=rep(100,10)); ma_analyze(d,"single_proportion","PLO") })
chk("R10-6", "ma_analyze single_mean MN", {
  set.seed(18); d <- data.frame(study=paste0("S",1:10), mean=runif(10,10,12), sd=rep(2,10), n=rep(40,10)); ma_analyze(d,"single_mean","MN") })
chk("R10-7", "ma_analyze precomp (yi+vi)", {
  set.seed(19); d <- data.frame(study=paste0("S",1:10), yi=runif(10,0.1,0.5), vi=runif(10,0.01,0.05)); ma_analyze(d,"precomp") })
chk("R10-8", "ma_analyze with label_col", {
  d <- mk(10); names(d)[1] <- "trial"; ma_analyze(d, "dichotomous", "OR", label_col="trial") })
chk("R10-9", "ma_save (forest+funnel+summary)", {
  res <- ma_analyze(mk(10), "dichotomous", "OR"); ma_save(res, outdir = tempdir(), prefix = "test") })
chk("R10-10", "ma_analyze unknown type", {
  ma_analyze(mk(10), "UNKNOWN_XYZ") })
cat("=== DONE ===\n")
