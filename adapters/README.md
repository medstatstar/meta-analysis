# adapters/ — 计算出口层（ct-base §16.9 架构预留）

> 本目录是 **meta-analysis 技能** 的分析计算出口层。**发布形态为 coze-only**（2026-08-19 决策）：
> 所有数值计算经 coze 元分析工作流，本地 LLM 仅做需求标准化/数据整理/结果呈现，**最终用户无需安装 R**。
> 本地引擎统一为 `adapters/coze_project/src/r_engine/`（coze 远端双向同步唯一源，2026-08-19 起技能根 `r_engine/` 已废弃删除）。

## 路由策略（2026-08-19 refined：发布 coze-only，本地兜底仅开发者用）

```
                 ┌─────────────────────────────────────────────┐
   分析请求 ──────▶│ adapters/run_analysis.py  (统一入口)         │
 (task/data/…)    │   prefer="coze"（发布形态，唯一对外路径）       │
                 └───────────────┬─────────────────────────────┘
                                 │
                  ① coze_client.run_meta ── 成功 ──▶ _source="coze"
                                 │ 失败（网络/HTTP/空响应）
                                 ▼
                  ② local_engine.run_meta（仅开发者/复现）──▶ _source="local_fallback"
```

- **发布形态**：`prefer="coze"`（默认）——最终用户路径，不依赖本地 R。
- **开发者/复现**：本地 R 引擎（`adapters/coze_project/src/r_engine/`，即镜像内引擎）供快速迭代、dryrun 回归、repro 脚本复现；`repro` 字段随每次 coze 结果返回。
- 返回值统一带 `_source` 字段标记来源。

## 文件

```
adapters/
├── run_analysis.py        # 统一前端：coze 优先（发布形态）+ 本地兜底（开发用）
├── coze_client.py         # Coze /run 客户端（主路径）：信封打包 / 响应解析
├── local_engine.py        # 本地 R 兜底（开发/复现）：subprocess 调 coze_project/src/r_engine/run_task.R
├── coze_cases/            # 3 个冒烟案例（快速自测）
├── coze_project/          # ★ coze 项目本地镜像（与 coze 远端双向同步的唯一源，2026-08-19 统一放置）
│   ├── coze_contract.md   #   接口契约（§16.7 红线：不随技能发布，已 ignore）
│   ├── src/r_engine/*.R   #   R 引擎（run_task.R 等，coze 端运行本体）
│   ├── scripts/           #   部署脚本（http_run.sh / setup.sh 等）
│   └── docker/ assets/    #   镜像/依赖清单
└── README.md              # 本文件
```

## coze 项目镜像：双向同步约定（2026-08-19 统一）

> **`adapters/coze_project/` 是 coze 远端代码在本地唯一的同步源。** 所有 coze 端代码变更都从这里进出：
> 本地改代码 → 打包部署 coze；coze 平台导出 → 覆盖回此目录。**不再使用工作区 `coze_meta_project/` 作为主镜像**（保留为历史快照）。

- **本地 → coze**：改 `adapters/coze_project/` 内文件 → `tar -czf coze_final_YYYYMMDD.tar.gz .`（在镜像目录内）→ 上传 coze 平台 → vefaas 重部署 → 线上 96 例复测。
- **coze → 本地**：coze 平台导出 project → 解包覆盖 `adapters/coze_project/` → `diff -r` 与镜像内 `src/r_engine/` 比对确认。
- **发布排除**：`adapters/coze_project/` 已加入 `.gitignore` / `.clawhubignore`，**不随技能发布**（coze_contract.md 属 §16.7 红线）。
- **一致性基准**：`adapters/coze_project/src/r_engine/` 为唯一本地引擎（技能根 `r_engine/` 已删），与 coze 远端同步。

## 配置（环境变量）

| 变量 | 说明 | 默认 |
|------|------|------|
| `COZE_META_ENDPOINT` | coze 工作流 `/run` 地址（2026-08-19 修正，旧默认 localhost 会误报不可达） | `https://ct-meta.coze.site/run` |
| `COZE_META_TOKEN` | 可选 Bearer 鉴权令牌 | 空（不带 Authorization） |
| `COZE_META_TIMEOUT` | 请求超时（秒） | `600` |
| `RSCRIPT_PATH` | 本地 `Rscript` 可执行文件路径（兜底用） | `Rscript`（依赖 PATH） |
| `META_LOCAL_ENGINE_DIR` | 本地引擎目录（含 run_task.R） | `<skill>/adapters/coze_project/src/r_engine` |

## 用法

```python
import sys; sys.path.insert(0, "adapters")
from run_analysis import run_analysis

# 默认：coze 优先，失败自动本地兜底
out = run_analysis(
    task="pairwise_meta",
    data={"rows": [{"study": "A", "event_exp": 12, "n_exp": 100,
                    "event_ctrl": 20, "n_ctrl": 100}]},
    params={"sm": "OR", "model": "REML"},
    figure={"plots": ["forest"]},
)
# out["_source"] == "coze" | "local_fallback" | "local"

# 显式本地（离线 / 用户要求）
out = run_analysis(task="pairwise_meta", data=..., prefer="local")
```

CLI 等价：`python adapters/run_analysis.py request.json [--prefer coze|local]`

## 红线

- **数值判断红线**：R 计算的数值结论（合并效应、I²、排序等）由 R 产出（coze 侧或本地），
  本层仅解析结构（status/stats/figures[].svg/warnings/notes），绝不读取或改写数值。
- **接口契约**：见 coze 项目的 `coze_contract.md`（不随技能发布，遵循 ct-base §16.7）。
  镜像内 `src/r_engine/` 是 coze 远端引擎的字节级镜像，靠该契约保持同步。
- **发布红线**：coze 接口契约 / system prompt / ops 文档一律不随技能发布（ct-base §16.7）。
