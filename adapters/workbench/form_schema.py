"""meta-analysis 工作台：表单描述层（Phase 0，纯数据）。

按 stage_id 描述每个「人工确认节点」的渲染形态。工作台前端（workbench.html）
消费本模块产出的 schema，配合后端 /api/session 返回的 ctx
（{nha, editable, stage}）做 dotted-path 解析渲染。

设计要点：
- 软停（gate:none→kind=pause）与 🔴 红线（gate=xxx→kind=gate）两类渲染；
  红线节点数据默认只读，仅 approve/reject/revise。
- 各节点「需求不一样」：A2 看库清单+查询式、A3 翻转子表、A4 编辑 2×2、
  B4/C3/C4 红线条只读+批准。panel.kind 区分 object/dicttable/rowlist/textarea/json。
- panel.path 为 dotted-path，解析空间 = {nha, editable, stage}：
    nha      → await.next_human_action（富载荷：覆盖/逐条决策）
    editable → await.editable_payload（可编辑键子集，来自 EDITABLE_KEYS）
    stage    → await.stage_result（当前阶段完整结果，红线节点展示全字段）
- 可编辑 panel 用 revision_key 声明「改动回写进 HumanDecision.revision 的哪个键」，
  由前端在提交时收集。
"""

# 全流程阶段计划（供前端时间轴骨架；真实进度由后端按信封动态重建）
STAGE_ORDER = [
    ("A", "A1.topic_selection", "选题"),
    ("A", "A2.literature_search", "检索"),
    ("A", "A3.screening", "初筛"),
    ("A", "A4.data_extraction", "数据提取"),
    ("B", "B1.meta", "合并计算"),
    ("B", "B2.grade", "GRADE"),
    ("B", "B3.overclaim", "过度声明"),
    ("B", "B4.quality_gate", "质量门"),
    ("C", "C1.draft", "初稿"),
    ("C", "C2.ai_review", "AI 评审"),
    ("C", "C3.ref_verify", "参考核验"),
    ("C", "C4.evidence_qa", "投稿前 QA"),
]

SCHEMA = {
    "A1.topic_selection": {
        "title": "选题确认（PICOS）",
        "gate_type": "soft",
        "intro": "本地启发式生成的 PICOS 选题报告，请确认或修改后放行。",
        "panels": [
            {"label": "PICOS 报告", "kind": "textarea", "path": "editable.report",
             "editable": True, "revision_key": "report"},
        ],
    },
    "A2.literature_search": {
        "title": "检索策略与覆盖确认",
        "gate_type": "soft",
        "intro": "核对各数据库条数与检索状态：search_status≠ok 或某库缺位 = 可能沉默漏检"
                 "（无 token 静默跳库 / skill 缺失）。可修订查询式（重跑于 Phase 2 生效）。",
        "panels": [
            {"label": "检索概览", "kind": "object", "path": "nha.coverage", "fields": [
                {"path": "total", "label": "合并总数"},
                {"path": "search_status", "label": "检索状态", "alert_if_not": "ok"},
                {"path": "retracted", "label": "撤稿数"},
                {"path": "year_from", "label": "起始年"},
                {"path": "max_results", "label": "检索上限"},
            ]},
            {"label": "各数据库条数", "kind": "dicttable", "path": "nha.coverage.by_source"},
            {"label": "查询式", "kind": "textarea", "path": "nha.coverage.query",
             "editable": True, "revision_key": "query"},
        ],
    },
    "A3.screening": {
        "title": "初筛逐条裁决",
        "gate_type": "soft",
        "intro": "逐条确认或翻转 Include/Exclude，重点复核剔除项以防误剔关键研究。",
        "panels": [
            {"label": "筛选统计", "kind": "object", "path": "nha.summary", "fields": [
                {"path": "n_total", "label": "去重总数"},
                {"path": "n_include", "label": "纳入"},
                {"path": "n_exclude", "label": "剔除"},
                {"path": "n_uncertain", "label": "低置信"},
            ]},
            {"label": "逐条决策", "kind": "rowlist", "path": "nha.decisions",
             "editable": True, "revision_key": "screened", "columns": [
                {"path": "title", "label": "标题", "type": "text", "editable": False},
                {"path": "include", "label": "纳入", "type": "bool", "editable": True},
                {"path": "reason", "label": "理由", "type": "text", "editable": True},
            ]},
        ],
    },
    "A4.data_extraction": {
        "title": "数据提取核验（🔴 红线）",
        "gate_type": "redline",
        "intro": "提取数据（TE/seTE/事件数）须经人工核验放行方可进入 Block B。可修订 2×2 表后 revise。",
        "panels": [
            {"label": "提取概览", "kind": "object", "path": "stage", "fields": [
                {"path": "n_screened", "label": "初筛通过"},
                {"path": "n_downloaded", "label": "已下载全文"},
                {"path": "n_extracted", "label": "已抽取"},
                {"path": "needs_user_upload", "label": "待上传 PDF"},
            ]},
            {"label": "提取数据（2×2 / 效应量）", "kind": "rowlist",
             "path": "editable.extracted_rows", "editable": True,
             "revision_key": "extracted_rows", "columns": "auto"},
        ],
    },
    "B4.quality_gate": {
        "title": "质量门：GRADE + 过度声明（🔴 红线）",
        "gate_type": "redline",
        "intro": "GRADE 分级与过度声明检测结果须人工放行（final_inclusion）。",
        "panels": [
            {"label": "质量报告", "kind": "json", "path": "editable.report",
             "editable": True, "revision_key": "report"},
        ],
    },
    "B1.meta": {
        "title": "合并计算（B1 · 自动）",
        "gate_type": "auto",
        "intro": "R 引擎（coze ct-meta2；5 形状 + NMA 本地镜像已验证）完成合并效应量与异质性估计。"
                 "自动节点，无需人工操作，点击查看结果。",
        "panels": [
            {"label": "合并概要（pairwise）", "kind": "object", "path": "stage.pairwise", "fields": [
                {"path": "k", "label": "纳入研究数 k"},
                {"path": "effect_measure", "label": "效应量类型"},
                {"path": "engine", "label": "计算引擎"},
                {"path": "I2", "label": "异质性 I² (%)"},
                {"path": "tau2", "label": "τ²"},
                {"path": "Q", "label": "Q 统计量"},
            ]},
            {"label": "固定效应（Fixed）", "kind": "object", "path": "stage.pairwise", "fields": [
                {"path": "TE_fixed", "label": "合并效应量"},
                {"path": "ci_fixed", "label": "95% CI"},
                {"path": "p_fixed", "label": "p 值"},
            ]},
            {"label": "随机效应（Random）", "kind": "object", "path": "stage.pairwise", "fields": [
                {"path": "TE_random", "label": "合并效应量"},
                {"path": "ci_random", "label": "95% CI"},
                {"path": "p_random", "label": "p 值"},
            ]},
            {"label": "NMA 网络 meta 结果", "kind": "json", "path": "stage.nma"},
            {"label": "完整 pairwise 数据（兜底）", "kind": "json", "path": "stage.pairwise"},
        ],
    },
    "B2.grade": {
        "title": "GRADE 分级（B2 · 自动）",
        "gate_type": "auto",
        "intro": "GRADE 证据质量分级与降级理由。自动节点，无需人工操作，点击查看结果。",
        "panels": [
            {"label": "GRADE 结果", "kind": "object", "path": "stage", "fields": [
                {"path": "grade", "label": "证据等级"},
                {"path": "downgrades", "label": "降级总分"},
            ]},
            {"label": "降级理由", "kind": "json", "path": "stage.reasons"},
            {"label": "领域评级", "kind": "json", "path": "stage.domain_ratings"},
        ],
    },
    "B3.overclaim": {
        "title": "过度声明检测（B3 · 自动）",
        "gate_type": "auto",
        "intro": "基于统计量的过度声明模式扫描（被 B4/C2 复用）。自动节点，无需人工操作，点击查看命中。",
        "panels": [
            {"label": "检测概览", "kind": "object", "path": "stage", "fields": [
                {"path": "n_patterns", "label": "扫描模式数"},
                {"path": "n_hits", "label": "命中数"},
            ]},
            {"label": "命中项", "kind": "rowlist", "path": "stage.hits", "editable": False, "columns": [
                {"path": "id", "label": "ID", "type": "text", "editable": False},
                {"path": "label", "label": "模式", "type": "text", "editable": False},
                {"path": "severity", "label": "严重度", "type": "text", "editable": False},
                {"path": "evidence", "label": "佐证", "type": "text", "editable": False},
            ]},
        ],
    },
    "C1.draft": {
        "title": "初稿撰写（人工改）",
        "gate_type": "soft",
        "intro": "AI 初稿已填充 B1–B4 数字，请审阅并修改章节。",
        "panels": [
            {"label": "稿件章节", "kind": "json", "path": "editable.sections",
             "editable": True, "revision_key": "sections"},
        ],
    },
    "C2.ai_review": {
        "title": "AI 评审（C2 · 自动）",
        "gate_type": "auto",
        "intro": "对初稿全文做过度声明 AI 评审（复用 B3 检测）。自动节点，无需人工操作，点击查看命中。",
        "panels": [
            {"label": "评审概览", "kind": "object", "path": "stage", "fields": [
                {"path": "n_patterns", "label": "扫描模式数"},
                {"path": "n_hits", "label": "命中数"},
            ]},
            {"label": "命中项", "kind": "rowlist", "path": "stage.hits", "editable": False, "columns": [
                {"path": "id", "label": "ID", "type": "text", "editable": False},
                {"path": "label", "label": "模式", "type": "text", "editable": False},
                {"path": "severity", "label": "严重度", "type": "text", "editable": False},
                {"path": "evidence", "label": "佐证", "type": "text", "editable": False},
            ]},
        ],
    },
    "C3.ref_verify": {
        "title": "参考文献核验（🔴 红线）",
        "gate_type": "redline",
        "intro": "结构 / PRISMA 合规与撤稿检查须人工放行（reference_verification）。",
        "panels": [
            {"label": "核验结果", "kind": "json", "path": "stage", "editable": False},
        ],
    },
    "C4.evidence_qa": {
        "title": "投稿前 QA（🔴 红线终闸）",
        "gate_type": "redline",
        "intro": "GRADE 表 + QA 清单终检，须人工放行（manuscript_approval）。",
        "panels": [
            {"label": "QA 结果", "kind": "json", "path": "stage", "editable": False},
        ],
    },
}


def schema_for(stage_id, kind=None):
    """返回某节点的渲染 schema；未知节点回退为通用只读 JSON 面板。"""
    s = SCHEMA.get(stage_id)
    if s:
        return s
    gate_type = "redline" if kind == "gate" else "soft"
    return {
        "title": stage_id or "未知节点",
        "gate_type": gate_type,
        "intro": "通用确认节点（无专门表单，展示原始数据）。",
        "panels": [
            {"label": "数据", "kind": "json", "path": "stage", "editable": False},
        ],
    }


def resolve(ctx, dotted):
    """在 ctx（{nha, editable, stage}）中解析 dotted-path。"""
    cur = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


if __name__ == "__main__":
    # 自检：每个已知 stage 都有 schema，且默认路径可解析示例 ctx
    sample = {
        "nha": {"coverage": {"total": 3, "search_status": "ok", "retracted": 0,
                             "by_source": {"PubMed": 2, "EMBASE": 1}, "query": "x", "year_from": 2010, "max_results": 50},
                "summary": {"n_total": 3, "n_include": 2, "n_exclude": 1, "n_uncertain": 0},
                "decisions": [{"title": "t", "include": True, "reason": "r"}]},
        "editable": {"report": "PICOS", "extracted_rows": [{"a": 1}], "sections": [], "screened": []},
        "stage": {"n_screened": 3, "n_downloaded": 1, "n_extracted": 1, "needs_user_upload": 0,
                  "pairwise": {"k": 5, "effect_measure": "OR", "engine": "coze", "I2": 12.0,
                               "tau2": 0.01, "Q": 4.1, "TE_fixed": 0.5, "ci_fixed": [0.2, 0.8],
                               "p_fixed": 0.01, "TE_random": 0.5, "ci_random": [0.18, 0.82],
                               "p_random": 0.01},
                  "nma": {"status": "skipped"},
                  "grade": "moderate", "downgrades": 1, "reasons": ["不一致性中等"],
                  "domain_ratings": {"inconsistency": "some"},
                  "n_patterns": 12, "n_hits": 1,
                  "hits": [{"id": "ci_cross", "label": "CI 跨零",
                            "severity": "high", "evidence": "OR 95% CI 含 1"}]},
    }
    for sid in SCHEMA:
        sc = schema_for(sid)
        assert sc["title"], sid
        for p in sc["panels"]:
            v = resolve(sample, p["path"])
            print(f"{sid:22s} panel={p['label'][:10]:10s} path={p['path']:28s} -> {'OK' if v is not None else 'MISSING'}")
    print("FORM_SCHEMA self-check done.")
