#!/usr/bin/env Rscript
# DEV-ONLY: 本地 netmeta 频率学派 NMA，输出 JSON。生产路径为 coze，本脚本仅离线验证用。
# 调用: Rscript nma_engine.R --arm arm.csv --out nma_out.json [--ref REFERENCE_TREATMENT]

args <- commandArgs(trailingOnly = TRUE)
arm_file <- NULL; out_file <- NULL; ref <- NULL
i <- 1
while (i <= length(args)) {
  if (args[i] == "--arm") { arm_file <- args[i+1]; i <- i + 2 }
  else if (args[i] == "--out") { out_file <- args[i+1]; i <- i + 2 }
  else if (args[i] == "--ref") { ref <- args[i+1]; i <- i + 2 }
  else { i <- i + 1 }
}
if (is.null(arm_file) || is.null(out_file)) {
  cat("usage: nma_engine.R --arm arm.csv --out nma_out.json [--ref REFERENCE_TREATMENT]\n")
  quit(status = 1)
}

# 依赖检查：生产路径请走 coze；本地验证需 netmeta
if (!requireNamespace("netmeta", quietly = TRUE)) {
  cat("ERROR: netmeta 未安装。生产路径请走 coze；本地验证请先 install.packages('netmeta')。\n")
  quit(status = 2)
}
library(netmeta)

df <- read.csv(arm_file, stringsAsFactors = FALSE)
colnames(df) <- tolower(colnames(df))

# 参照处理：默认按字母序首个（通常为 Placebo）
if (is.null(ref)) ref <- sort(unique(df$treat))[1]

nma <- netmeta(event, n, treat, studlab = study, data = df,
               sm = "OR", reference = ref, details = TRUE)

# —— 基本参数（各干预 vs 参照）及其协方差 ——
bp <- nma$TE                       # 命名向量
cov <- nma$Cov
if (is.null(cov)) cov <- matrix(0, nrow = length(bp), ncol = length(bp),
                                dimnames = list(names(bp), names(bp)))
allt <- c(ref, names(bp))

# 任意两干预相对效应（均相对参照求差）
get_rel <- function(a, b) {
  if (a == b) return(list(OR = 1, lo = 1, hi = 1))
  ia <- if (a == ref) 0 else bp[[a]]
  ib <- if (b == ref) 0 else bp[[b]]
  va <- if (a == ref) 0 else cov[a, a]
  vb <- if (b == ref) 0 else cov[b, b]
  cab <- if (a == ref || b == ref) 0 else cov[a, b]
  d <- ia - ib
  v <- max(va + vb - 2 * cab, 0)
  se <- sqrt(v)
  lo <- d - 1.96 * se; hi <- d + 1.96 * se
  list(OR = exp(d), lo = exp(lo), hi = exp(hi))
}

jnum <- function(x) if (is.null(x) || is.na(x)) "null" else formatC(x, digits = 4, format = "f")
jstr <- function(s) paste0('"', s, '"')

# league 表（OR + 95% CI）
league_json <- "{"
fa <- TRUE
for (a in allt) {
  if (!fa) league_json <- paste0(league_json, ",")
  fa <- FALSE
  league_json <- paste0(league_json, jstr(a), ":{")
  fb <- TRUE
  for (b in allt) {
    if (a == b) next
    if (!fb) league_json <- paste0(league_json, ",")
    fb <- FALSE
    r <- get_rel(a, b)
    league_json <- paste0(league_json, jstr(b), ":{\"OR\":", jnum(r$OR),
                          ",\"lo\":", jnum(r$lo), ",\"hi\":", jnum(r$hi), "}")
  }
  league_json <- paste0(league_json, "}")
}
league_json <- paste0(league_json, "}")

# 排序（SUCRA / P-score）
rk <- netrank(nma, small.values = "bad")
sucra <- as.numeric(rk$sucra); names(sucra) <- rk$treatments
pscore <- as.numeric(rk$p.score); names(pscore) <- rk$treatments

sucra_json <- "{"
for (k in seq_along(sucra)) {
  if (k > 1) sucra_json <- paste0(sucra_json, ",")
  sucra_json <- paste0(sucra_json, jstr(names(sucra)[k]), ":", jnum(sucra[k]))
}
sucra_json <- paste0(sucra_json, "}")

rank_json <- "{"
for (k in seq_along(pscore)) {
  if (k > 1) rank_json <- paste0(rank_json, ",")
  rank_json <- paste0(rank_json, jstr(names(pscore)[k]), ":", jnum(pscore[k]))
}
rank_json <- paste0(rank_json, "}")

tau2 <- if (is.numeric(nma$tau^2)) nma$tau^2 else 0

treats_json <- paste0("[", paste(sapply(allt, jstr), collapse = ","), "]")
ref_json <- jstr(ref)

out <- paste0(
  "{\"treatments\":", treats_json,
  ",\"reference\":", ref_json,
  ",\"league\":", league_json,
  ",\"sucra\":", sucra_json,
  ",\"ranks\":", rank_json,
  ",\"tau2\":", jnum(tau2),
  ",\"message\":\"frequency NMA (netmeta) OK\"}"
)
writeLines(out, out_file)
cat("OK ->", out_file, "\n")
