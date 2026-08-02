suppressMessages(library(metafor))
suppressMessages(library(meta))
source("scripts/meta_analysis_core.R")
source("scripts/effect_size_conversions.R")

run_case <- function(n, desc, expr) {
  r <- tryCatch({ expr; "PASS" }, error = function(e) paste("ERROR:", conditionMessage(e)))
  cat(sprintf("[%2d] %-40s -> %s\n", n, desc, r))
  invisible(NULL)
}

# 1. 二分类 OR 正常
run_case(1, "dichotomous OR", {
  d <- data.frame(study=paste0("S",1:5), event_exp=c(15,20,18,22,19), n_exp=c(50,60,55,58,52),
                  event_ctrl=c(10,12,10,15,11), n_ctrl=c(50,60,55,58,52))
  es <- calculate_effect_size(d, "dichotomous", "OR"); stopifnot(all(!is.na(es$yi)))
})

# 2. 二分类 RR
run_case(2, "dichotomous RR", {
  d <- data.frame(study=paste0("S",1:5), event_exp=c(15,20,18,22,19), n_exp=c(50,60,55,58,52),
                  event_ctrl=c(10,12,10,15,11), n_ctrl=c(50,60,55,58,52))
  es <- calculate_effect_size(d, "dichotomous", "RR"); stopifnot(all(!is.na(es$yi)))
})

# 3. 二分类 RD
run_case(3, "dichotomous RD", {
  d <- data.frame(study=paste0("S",1:5), event_exp=c(15,20,18,22,19), n_exp=c(50,60,55,58,52),
                  event_ctrl=c(10,12,10,15,11), n_ctrl=c(50,60,55,58,52))
  es <- calculate_effect_size(d, "dichotomous", "RD"); stopifnot(all(!is.na(es$yi)))
})

# 4. 二分类 PETO
run_case(4, "dichotomous PETO", {
  d <- data.frame(study=paste0("S",1:5), event_exp=c(15,20,18,22,19), n_exp=c(50,60,55,58,52),
                  event_ctrl=c(10,12,10,15,11), n_ctrl=c(50,60,55,58,52))
  es <- calculate_effect_size(d, "dichotomous", "PETO"); stopifnot(all(!is.na(es$yi)))
})

# 5. 连续 SMD
run_case(5, "continuous SMD", {
  d <- data.frame(study=paste0("S",1:5), n_exp=c(30,25,40,35,28), mean_exp=c(10.5,12,11,10.8,11.5),
                  sd_exp=c(2.1,2.3,2.5,2,2.4), n_ctrl=c(30,25,40,35,28), mean_ctrl=c(9,10,9.5,9.2,9.8),
                  sd_ctrl=c(1.8,2,2.2,1.9,2.1))
  es <- calculate_effect_size(d, "continuous", "SMD"); stopifnot(all(!is.na(es$yi)))
})

# 6. 连续 MD
run_case(6, "continuous MD", {
  d <- data.frame(study=paste0("S",1:5), n_exp=c(30,25,40,35,28), mean_exp=c(10.5,12,11,10.8,11.5),
                  sd_exp=c(2.1,2.3,2.5,2,2.4), n_ctrl=c(30,25,40,35,28), mean_ctrl=c(9,10,9.5,9.2,9.8),
                  sd_ctrl=c(1.8,2,2.2,1.9,2.1))
  es <- calculate_effect_size(d, "continuous", "MD"); stopifnot(all(!is.na(es$yi)))
})

# 7. 连续 ROM
run_case(7, "continuous ROM", {
  d <- data.frame(study=paste0("S",1:5), n_exp=c(30,25,40,35,28), mean_exp=c(10.5,12,11,10.8,11.5),
                  sd_exp=c(2.1,2.3,2.5,2,2.4), n_ctrl=c(30,25,40,35,28), mean_ctrl=c(9,10,9.5,9.2,9.8),
                  sd_ctrl=c(1.8,2,2.2,1.9,2.1))
  es <- calculate_effect_size(d, "continuous", "ROM"); stopifnot(all(!is.na(es$yi)))
})

# 8. rate IRR (列名 a/b/c/d)
run_case(8, "rate IRR (a/b/c/d cols)", {
  d <- data.frame(study=paste0("S",1:5), a=c(20,15,18,22,19), b=c(200,180,210,230,190),
                  c=c(12,10,14,15,11), d=c(200,180,210,230,190))
  es <- calculate_effect_size(d, "rate", "IRR"); stopifnot(all(!is.na(es$yi)))
})

# 9. single_proportion PLO
run_case(9, "single_proportion PLO", {
  d <- data.frame(study=paste0("S",1:5), events=c(8,12,10,15,9), n=c(50,60,55,58,52))
  es <- calculate_effect_size(d, "single_proportion", "PLO"); stopifnot(all(!is.na(es$yi)))
})

# 10. correlation ZCOR
run_case(10, "correlation ZCOR", {
  d <- data.frame(study=paste0("S",1:5), r=c(0.3,0.4,0.25,0.5,0.35), n=c(40,50,45,60,48))
  es <- calculate_effect_size(d, "correlation", "ZCOR"); stopifnot(all(!is.na(es$yi)))
})

cat("\n=== esc transformations ===\n")
# 11. d -> logOR
run_case(11, "esc d->logOR", {
  r <- run_esc_transform(c(0.5,0.3,0.8), c(0.04,0.03,0.06), "d", "logOR"); stopifnot(all(!is.na(r$yi)))
})
# 12. logOR -> d
run_case(12, "esc logOR->d", {
  r <- run_esc_transform(c(0.2,0.1,0.4), c(0.02,0.01,0.03), "logOR", "d"); stopifnot(all(!is.na(r$yi)))
})
# 13. cor -> logOR (chained)
run_case(13, "esc cor->logOR", {
  r <- run_esc_transform(c(0.3,0.4,0.25), c(0.01,0.01,0.01), "cor", "logOR"); stopifnot(all(!is.na(r$yi)))
})

cat("\n=== boundary / error-input probes ===\n")
# 14. 二分类含 0 事件（对照组全 0）
run_case(14, "dichotomous 0-event ctrl", {
  d <- data.frame(study=paste0("S",1:4), event_exp=c(15,20,18,22), n_exp=c(50,60,55,58),
                  event_ctrl=c(0,0,0,0), n_ctrl=c(50,60,55,58))
  es <- calculate_effect_size(d, "dichotomous", "OR")  # expect warning but PASS
})
# 15. rate 用 x1i/t1i 列名（潜在 bug：硬编码 a/b/c/d）
run_case(15, "rate with x1i/t1i cols", {
  d <- data.frame(study=paste0("S",1:5), x1i=c(20,15,18,22,19), t1i=c(200,180,210,230,190),
                  x2i=c(12,10,14,15,11), t2i=c(200,180,210,230,190))
  es <- calculate_effect_size(d, "rate", "IRR")
})
# 16. 未知 measure
run_case(16, "unknown measure", {
  d <- data.frame(study=paste0("S",1:5), event_exp=c(15,20,18,22,19), n_exp=c(50,60,55,58,52),
                  event_ctrl=c(10,12,10,15,11), n_ctrl=c(50,60,55,58,52))
  es <- calculate_effect_size(d, "dichotomous", "XYZ")
})
