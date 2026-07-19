# -*- coding: utf-8 -*-
# AUTO-GENERATED from network_meta_analysis.R
# 编辑 R 逻辑请修改下面的 R_SOURCE 字符串；改完运行:
#   python r_templates.py        # 重新生成全部 scripts/*.R
#   python r_network_meta_analysis.py            # 仅重新生成本文件对应的 .R
R_FILENAME = "network_meta_analysis.R"

R_SOURCE = r'''# ============================================================================
# Network Meta-Analysis Script
#  网络 Meta 分析完整流程
#  使用 netmeta 包（频率学派）和 gemtc 包（贝叶斯）
# ============================================================================

# --- 双语语言检测（默认英文，中文环境切中文） ---
.MA_LANG <- local({
  lang <- tolower(paste(Sys.getenv("LANG"), Sys.getenv("LC_ALL"), Sys.getenv("LANGUAGE")))
  if (grepl("zh|cn|chs", lang)) "zh" else "en"
})
.msg <- function(en, zh) if (.MA_LANG == "zh") zh else en

# --- 1. 数据准备 ---
prepare_nma_data <- function(study_data, arm_data,
                             outcome_type = "binomial",
                             link = "logit") {
  library(netmeta)
  arm_data$treatment <- as.factor(arm_data$treatment)
  return(arm_data)
}

# --- 2. 频率学派 NMA ---
run_frequentist_nma <- function(data,
                                sm = "OR",
                                reference.group = "placebo",
                                sep.trt = " vs ",
                                common = FALSE,
                                random = TRUE) {
  library(netmeta)
  net <- netmeta(
    TE = TE, seTE = seTE, treat1 = treat1, treat2 = treat2, studlab = study,
    data = data, sm = sm, reference.group = reference.group,
    sep.trt = sep.trt, common = common, random = random)
  return(net)
}

# --- 3. 联赛表 ---
get_league_table <- function(netmeta_result, fixed = FALSE, digits = 2) {
  random <- netleague(netmeta_result)
  fixed <- netleague(netmeta_result, fixed = TRUE)
  return(list(random = random$random, fixed = fixed$fixed))
}

# --- 4. 一致性检验 ---
check_consistency <- function(netmeta_result, data) {
  library(netmeta)
  net_split <- netsplit(netmeta_result)
  return(net_split)
}

# --- 5. 排列检验（排序） ---
rank_interventions <- function(netmeta_result,
                               small.values = "bad",
                               method = "P-score") {
  library(netmeta)
  rank_result <- netrank(netmeta_result, small.values = small.values, method = method)
  return(rank_result)
}

# --- 6. 网络图 ---
plot_network <- function(netmeta_result,
                         node_size = NULL,
                         edge_width = NULL,
                         plastic = FALSE,
                         thickness = "seTE") {
  library(netmeta)
  netgraph(netmeta_result,
           node.size = if(is.null(node_size)) "evidence" else node_size,
           plastic = plastic, thickness = thickness)
}

# --- 7. SUCRA 图 ---
plot_sucra <- function(rank_result) {
  plot(rank_result)
}

# --- 8. 综合报告 ---
generate_nma_report <- function(netmeta_result,
                                league_table,
                                consistency,
                                rank_result) {
  cat("================================================\n")
  cat(.msg(" Network Meta-Analysis Report\n", " 网络 Meta 分析报告\n"))
  cat("================================================\n\n")
  
  cat(.msg("Number of studies:", "研究数："), length(unique(netmeta_result$studies$study)), "\n")
  cat(.msg("Number of treatments:", "干预措施数："), length(netmeta_result$trts), "\n")
  cat(.msg("Number of comparisons:", "比较数："), nrow(netmeta_result$data), "\n\n")
  
  cat(.msg("\n--- League Table (Random Effects) ---\n",
           "\n--- 联赛表（随机效应） ---\n"))
  print(league_table$random)
  
  cat(.msg("\n--- Intervention Ranking (P-score) ---\n",
           "\n--- 干预措施排序（P-score） ---\n"))
  print(rank_result)
  
  return(invisible(list(league = league_table, consistency = consistency, ranking = rank_result)))
}
'''


def materialize(scripts_dir=None):
    """将本模块内嵌的 R 源码写出为 scripts/<R_FILENAME>。"""
    import os
    if scripts_dir is None:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(scripts_dir, R_FILENAME)
    with open(out, "w", encoding="utf-8") as f:
        f.write(R_SOURCE)
    return out


if __name__ == "__main__":
    print(materialize())
