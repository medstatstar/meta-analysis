# ============================================================================
# Network Meta-Analysis Script
#  网络 Meta 分析完整流程
#  使用 netmeta 包（频率学派）和 gemtc 包（贝叶斯）
# ============================================================================

# --- 1. 数据准备 ---
prepare_nma_data <- function(study_data, arm_data,
                             outcome_type = "binomial",
                             link = "logit") {
  #' 准备网络元分析数据
  #' @param study_data study-level data (study_id, etc.)
  #' @param arm_data arm-level data (study_id, treatment, events, total or mean, sd, n)
  
  library(netmeta)
  
  # 确保 treatment 是因子
  arm_data$treatment <- as.factor(arm_data$treatment)
  
  return(arm_data)
}

# --- 2. 频率学派 NMA ---
run_frequentist_nma <- function(data, 
                                sm = "OR",
                                reference.group = "placebo",
                                sep.trt = " vs ",
                                details.gsubgroup = FALSE) {
  #' 运行频率学派网络元分析
  
  library(netmeta)
  
  net <- netmeta(
    TE = TE,
    seTE = seTE,
    treat1 = treat1,
    treat2 = treat2,
    studlab = study,
    data = data,
    sm = sm,
    reference.group = reference.group,
    sep.trt = sep.trt,
    details.gsubgroup = details.subplots
  )
  
  return(net)
}

# --- 3. 联赛表 ---
get_league_table <- function(netmeta_result, 
                             fixed = FALSE,
                             digits = 2) {
  #' 生成联赛表（成对比较结果）
  
  random <- netleague(netmeta_result)
  fixed <- netleague(netma_result, fixed = TRUE
  
  return(list(
    random = random$random,
    fixed = fixed$fixed
  ))
}

# --- 4. 一致性检验 ---
check_consistency <- function(netmeta_result, 
                              data) {
  #' 节点拆分法检验一致性
  
  library(netmeta)
  
  net_split <- netsplit(netmeta_result)
  
  return(net_split)
}

# --- 5. 排列检验（排序） ---
rank_interventions <- function(netmeta_result,
                               small.values = "bad",
                               method = "P-score") {
  #' 计算干预措施的排序
  
  library(netmeta)
  
  rank_result <- netrank(netmeta_result,
                          small.values = small.values,
                          method = method)
  
  return(rank_result)
}

# --- 6. 网络图 ---
plot_network <- function(netmeta_result,
                         node_size = NULL,
                         edge_width = NULL,
                         plastic = FALSE,
                         thickness = "seTE") {
  #' 绘制网络图
  
  library(netmeta)
  
  netgraph(netmeta_result,
            node.size = if(is.null(node_size)) "evidence" else node_size,
            plastic = plastic,
            thickness = thickness)
}

# --- 7. SUCRA 图 ---
plot_sucra <- function(rank_result) {
  #' 排序概率图
  
  plot(rank_result)
}

# --- 8. 综合报告 ---
generate_nma_report <- function(netmeta_result,
                                league_table,
                                consistency,
                                rank_result) {
  #' 生成 NMA 结构化报告
  
  cat("================================================\n")
  cat(" Network Meta-Analysis Report\n")
  cat("================================================\n\n")
  
  cat("Number of studies:", length(unique(netmeta_result$studies$study)), "\n")
  cat("Number of treatments:", length(netmeta_result$trts), "\n")
  cat("Number of comparisons:", nrow(netmeta_result$data), "\n\n")
  
  cat("\n--- League Table (Random Effects) ---\n")
  print(league_table$random)
  
  cat("\n--- Intervention Ranking (P-score) ---\n")
  print(rank_result)
  
  return(invisible(list(
    league = league_table,
    consistency = consistency,
    ranking = rank_result
  )))
}
