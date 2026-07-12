# R 包功能详解与安装指南

## 核心包对比

### 1. metafor（统计引擎，必装）

**安装**：
```r
install.packages("metafor")
```

**核心函数**：

| 函数 | 功能 | 参数要点 |
|------|------|----------|
| `escalc()` | 计算效应量 | `measure="OR"/"RR"/"SMD"/"ROM"/"IRR"/"ZCOR"` |
| `rma()` | 元分析主模型 | `method="FE"/"REML"/"HK"/"ML"/"EB"/"DL"/"SJ"/"HS"/"GENQ"/"PMM"` |
| `rma.mv()` | 多水平/多元元分析 | `random = ~ 1 | study/outcome` |
| `forest()` | 森林图（基础） | `smlab`, `xlab`, `refline` |
| `funnel()` | 漏斗图 | `yvi`, `sei` |
| `bubble()` | 元回归气泡图 | `xlim`, `ylim` |
| `regtest()` | Egger 回归检验 | `model="lm"/"rma"` |
| `ranktest()` | Begg 秩相关检验 | 非参数 |
| `trimfill()` | 剪补法 | 自动补全缺失研究 |
| `leave1out()` | 逐一剔除法 | 敏感性分析 |
| `gosh()` | GOSH 图 | 全子集诊断 |
| `fsn()` | 失安全系数 | Rosenberg/Hunter |
| `robust()` | 稳健方差估计 | 多元元分析 |

**效应量 measure 参数对照表**：

| measure | 含义 | 输入数据格式 |
|---------|------|-------------|
| `OR` | 比值比(对数) | `ai, bi, ci, di` 四格表 |
| `RR` | 风险比(对数) | `ai, bi, ci, di` |
| `RD` | 风险差 | `ai, bi, ci, di` |
| `AS` | 反正弦差 | `ai, bi, ci, di` |
| `PETO` | Peto 法 | `ai, bi, ci, di` |
| `SMD` | 标准化均值差 | `n1i, m1i, sd1i, n2i, m2i, sd2i` |
| `SMDH` | Hedges' g (小样本校正) | 同上 |
| `SMCC` | 标准化均值变化 | `n, m1i, m2i, sd1i, sd2i, ri` |
| `ROM` | 均数比对数 | 连续型 |
| `BCOR` | 二列相关 | `ri, ni` |
| `ZCOR` | Fisher's Z 转换相关 | `ri, ni` |
| `HR` | 风险比 | 生存分析 |
| `IRR` | 发生率比(对数) | `xi, ti` |

### 2. meta（RevMan 兼容，必装）

**安装**：
```r
install.packages("meta")
```

**核心函数**：

| 函数 | 功能 |
|------|------|
| `metabin()` | 二分类数据元分析 |
| `metacont()` | 连续型数据元分析 |
| `metagen()` | 通用倒方差法 |
| `metacor()` | 相关系数元分析 |
| `metaprop()` | 比例单组元分析 |
| `metarate()` | 发病率元分析 |
| `metaadd()` | 追加研究到现有分析 |
| `update.meta()` | 更新/修改分析 |
| `forest()` | RevMan 风格森林图 |
| `funnel()` | 漏斗图 |
| `metabias()` | 偏倚检验汇总 |
| `trimfill()` | 剪补法 |
| `fsn()` | 失安全系数 |
| `labbe()` | L'Abbé 图 |
| `bubble()` | 气泡图 |
| `forest.meta(addcols)` | 自定义森林图列 |

**meta 特有功能**：
- RevMan 文件导入/导出
- 自动计算效应量
- Cochrane Review 兼容输出

### 3. dmetar（辅助扩展，强烈推荐）

**安装**：
```r
# 从 GitHub 安装最新版本
if (!require("remotes")) install.packages("remotes")
remotes::install_github("MathiasHarrer/dmetar")
```

**核心函数**：

| 函数 | 功能 | 依赖 |
|------|------|------|
| `RiskOfBias()` | RoB 2.0 可视化 | robvis |
| `TreatmentCoding()` | 网络 meta 编码 | netmeta |
| `SingleArmMissing()` | 单臂缺失数据处理 | meta |
| `MultiLevelMeta()` | 多水平元分析 | metafor |
| `GOSH_plot()` | GOSH 图 | metafor |
| `SubgroupAnalysis()` | 亚组分析自动化 | meta |
| `BubblePlot()` | 气泡图美化 | metafor |
| `InfluenceAnalysis()` | 影响力分析 | metafor |
| `功率分析()` | `power.analysis()` | 模拟 |

### 4. netmeta（网状meta，必装）

**安装**：
```r
install.packages("netmeta")
```

**核心函数**：

| 函数 | 功能 |
|------|------|
| `netmeta()` | 频率学派 NMA |
| `netgraph()` | 网络图 |
| `netleague()` | 联赛表 |
| `netrank()` | SUCRA/P-score 排序 |
| `netsplit()` | 节点拆分（一致性检验） |
| `netheat()` | 网络热图 |
| `netposet()` | 干预偏序 |
| `mnp()` | 多参数 NMA |

### 5. bayesmeta（贝叶斯，可选）

**安装**：
```r
install.packages("bayesmeta")
```

**核心函数**：

| 函数 | 功能 |
|------|------|
| `bayesmeta()` | 贝叶斯随机效应模型 |
| `forest.bayesmeta()` | 森林图 |
| `forestplot.bayesmeta()` | 出版级森林图 |

### 6. 可选增强包

| 包 | 用途 | 安装 |
|----|------|------|
| `metasens` | 敏感性分析（上限/下限法） | `install.packages("metasens")` |
| `ggplot2` | 高级图形 | `install.packages("ggplot2")` |
| `gridExtra` | 多图组合 | `install.packages("gridExtra")` |
| `robumta` | 稳健方差估计 | `install.packages("robumta")` |
| `clubSandwich` | 稳健推断 | `install.packages("clubSandwich")` |
| `metaviz` | 交互式可视化 | `install.packages("metaviz")` |
| `metaDigitise` | 图表数字化 | `install.packages("metaDigitise")` |
| `robvis` | RoB 可视化 | `install.packages("robvis")` |
| `gt` | 出版级表格 | `install.packages("gt")` |

---

## 安装脚本（一键安装所有推荐包）

```r
install_meta_packages <- function(advanced = TRUE) {
  core_pkgs <- c("metafor", "meta", "netmeta", "ggplot2", "gridExtra")
  if (advanced) {
    core_pkgs <- c(core_pkgs, "metasens", "bayesmeta", "metaviz", "robvis", "gt")
  }
  
  for (pkg in core_pkgs) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      install.packages(pkg, repos = "https://cran.r-project.org")
    }
  }
  
  # dmetar from GitHub
  if (!requireNamespace("dmetar", quietly = TRUE)) {
    if (!requireNamespace("remotes", quietly = TRUE)) {
      install.packages("remotes")
    }
    remotes::install_github("MathiasHarrer/dmetar")
  }
  
  message("All packages installed successfully!")
}

# 执行
install_meta_packages(advanced = TRUE)
```

---

## 诊断与故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| `rma()` 奇异拟合 | 研究数 < 3 或异质性极大 | 检查数据，考虑 Peto 法或减少协变量 |
| `metacont()` NA 值 | 输入数据缺失 | 用 `na.omit()` 清洗或插补 |
| `netmeta()` 网络不连通 | 干预措施间缺少连接 | 验证干预编码，添加共同对照组 |
| `dmetar` GitHub 失败 | 网络问题 | `options(timeout=600)` 后重试 |
| I² = 100% | 真实异质性或模型问题 | 检查数据单位一致性 |
| 漏斗图不对称 | 发表偏倚 | 用 `trimfill()` 校正 |
| `bayesmeta` 收敛失败 | 先验过于分散 | 缩小 half-normal 先验尺度 |
