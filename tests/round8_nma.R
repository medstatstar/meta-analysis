suppressMessages(library(metafor)); suppressMessages(library(meta)); suppressMessages(library(netmeta))
source("scripts/meta_analysis_core.R"); source("scripts/network_meta_analysis.R")

chk <- function(tag, d, expr) {
  r <- tryCatch({ force(expr); "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%s] %s -> %s\n", tag, d, r)); invisible(NULL)
}

connected <- data.frame(
  study = c("S1","S2","S3","S4","S5"),
  treat1 = c("A","B","A","C","B"),
  treat2 = c("B","C","C","A","A"),
  TE = c(0.30,0.20,0.10,0.25,0.15),
  seTE = c(0.15,0.18,0.16,0.14,0.17), stringsAsFactors=FALSE)
disconnected <- data.frame(
  study = c("S1","S2","S3","S4"),
  treat1 = c("A","B","C","D"),
  treat2 = c("B","A","D","C"),
  TE = c(0.3,0.2,0.25,0.15),
  seTE = c(0.15,0.18,0.16,0.17), stringsAsFactors=FALSE)

cat("========== ROUND 8: Network Meta-Analysis ==========\n")
chk("R8-1", "connected network (3 trt)", {
  net <- run_frequentist_nma(connected, reference.group="A"); net })
chk("R8-2", "disconnected (Bug B regression)", {
  run_frequentist_nma(disconnected, reference.group="A") })
chk("R8-3", "league table", {
  net <- run_frequentist_nma(connected, reference.group="A"); get_league_table(net) })
chk("R8-4", "consistency (netsplit)", {
  net <- run_frequentist_nma(connected, reference.group="A"); check_consistency(net, connected) })
chk("R8-5", "rank interventions (P-score)", {
  net <- run_frequentist_nma(connected, reference.group="A"); rank_interventions(net) })
chk("R8-6", "plot_network (netgraph)", {
  net <- run_frequentist_nma(connected, reference.group="A"); plot_network(net); "rendered" })
chk("R8-7", "plot_sucra", {
  net <- run_frequentist_nma(connected, reference.group="A"); rk <- rank_interventions(net); plot_sucra(rk); "rendered" })
chk("R8-8", "prepare_nma_data", {
  prepare_nma_data(NULL, connected) })
chk("R8-9", "reference.group not in data", {
  run_frequentist_nma(connected, reference.group="placebo") })
chk("R8-10", "4-treatment connected network", {
  d4 <- data.frame(study=paste0("S",1:6), treat1=c("A","B","C","A","B","C"),
    treat2=c("B","C","D","C","D","A"), TE=c(0.3,0.2,0.25,0.1,0.15,0.22),
    seTE=c(0.15,0.18,0.16,0.14,0.17,0.19), stringsAsFactors=FALSE)
  run_frequentist_nma(d4, reference.group="A") })
cat("=== DONE ===\n")
