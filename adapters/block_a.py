# -*- coding: utf-8 -*-
"""Phase 1 · Block A 本地优先管线驱动器（方向确定与文献/数据准备）。

设计约束（对齐 contracts/pipeline_stage/v1.0.0/SPEC.md §9 / roadmap Phase 1）：

- **不依赖 coze 部署**：本模块完全本地运行，不调用 run_stage/run_meta，因此不会触发
  出站鉴权（AuthRequiredError）。A2 检索委派走本地 ct-literature（tool_card →
  execute_tool_cards 本地 subprocess），A4 红线闸本地强执。
- A1/A3 的「AI 生成大脑」在 coze 侧（尚未部署），此处提供**本地启发式兜底 + 合规信封**，
  coze 部署后可由 run_stage 无缝接管（seam 见 run_block_a 的 `use_coze` 占位）。
- 阶段序列（SPEC §9）：
    A1.topic_selection    选题闸门
    A2.literature_search  检索委派 ct-literature（tool_card）
    A3.screening          AI 筛选草稿 + 人工闸
    A4.data_extraction    提取 AI 草稿 + 🔴 extraction_review 人工核验闸
- 返回结构与 run_pipeline 同构：{done, await_human, gate, final, stages[], attachments[],
  tool_card_outputs[]}，便于上层统一消费。

依赖：coze_client（提供 CONTRACT_VERSION / STAGE_SCHEMA_ID / execute_tool_cards /
_REDLINE_GATES）。所有网络动作在 execute_tool_cards 内部，测试可 monkeypatch。
"""

import json
import os
import re
import sys
import uuid

import coze_client as cc

# A2 检索式翻译关联 ct-base 权威 kw_localize（ct-base 规范 bilingual_retrieval.md）：
# 本模块不重复实现翻译，仅在首次需要时把 ct-base/scripts 加入 sys.path 后复用。
_CT_BASE_SCRIPTS = os.path.expanduser("~/.workbuddy/skills/ct-base/scripts")

# ---- Block A 阶段 ID（SPEC §9，严格匹配 coze 端编排对齐） ----
A1 = "A1.topic_selection"
A2 = "A2.literature_search"
A3 = "A3.screening"
A4 = "A4.data_extraction"
BLOCK_A_SEQUENCE = [A1, A2, A3, A4]
BLOCK_A_TOTAL = len(BLOCK_A_SEQUENCE)


# ---------------------------------------------------------------------------
# 信封构造（本地「prompt → 合法入参」层；与 SPEC §2/§3 一致）
# ---------------------------------------------------------------------------
def build_block_a_env(topic, max_results=50, year_from=None,
                      pipeline_id=None, query_origin=None):
    """构造 Block A 初始 stage 信封（请求侧）。

    补齐 contract_version / schema / pipeline(block='A') / stage(A1) / stage_context。
    仅结构化必填校验，无领域判断。topic 经 params.topic 透传，下游 A2 复用。
    """
    env = {
        "contract_version": cc.CONTRACT_VERSION,
        "schema": cc.STAGE_SCHEMA_ID,
        "pipeline_id": pipeline_id or f"blkA-{uuid.uuid4().hex[:8]}",
        "pipeline": {"name": "block_a", "block": "A", "cfg": {}},
        "request_id": str(uuid.uuid4()),
        "task": "topic_selection",
        "params": {"topic": topic, "max": max_results},
        "stage": {
            "id": A1, "index": 0, "total": BLOCK_A_TOTAL,
            "intent": "run", "prev_stage_id": None,
        },
        "stage_context": {"human_decisions": [], "tool_card_outputs": [], "artifacts": []},
    }
    if year_from is not None:
        env["params"]["year_from"] = year_from
    if query_origin:
        env["query_origin"] = query_origin
    return env


# ---------------------------------------------------------------------------
# 阶段响应构造（与 parse_stage_response 输出同构，便于统一消费）
# ---------------------------------------------------------------------------
def _mk_stage(sid, index, status, stage_result, nha, tool_cards=None):
    nha = nha or {}
    return {
        "mode": "stage",
        "stage": {"id": sid, "index": index, "total": BLOCK_A_TOTAL, "status": status,
                  "prev_stage_id": BLOCK_A_SEQUENCE[index - 1] if index > 0 else None},
        "stage_result": stage_result,
        "next_human_action": nha,
        "tool_cards": tool_cards or [],
        "_gate_blocked": bool(
            nha.get("gate") in cc._REDLINE_GATES and nha.get("required")
        ),
    }


# ---------------------------------------------------------------------------
# A1 选题闸门（本地启发式兜底；coze 部署后由其接管双库评分 + PROSPERO 查重）
# ---------------------------------------------------------------------------
def _infer_picos(topic):
    """极简 PICOS 启发式：按常见分隔符/关键词切分，标注缺失维度。
    仅离线兜底用，精度有限，结果须人工确认。"""
    t = (topic or "").strip()
    parts = [p.strip() for p in t.replace("；", ";").replace("；", ";").split(";") if p.strip()]
    picos = {"P": None, "I": None, "C": None, "O": None, "S": None}
    for i, p in enumerate(parts[:4]):
        picos[list(picos.keys())[i]] = p
    # 关键词兜底：含「vs/对照/安慰剂」→ 推断 C
    if picos["C"] is None and any(k in t.lower() for k in ("vs", "对照", "placebo", "安慰剂")):
        picos["C"] = "（疑似含对照，待确认）"
    missing = [k for k, v in picos.items() if v is None]
    return picos, missing


def a1_topic_selection(topic, registry_probe=None):
    picos, missing = _infer_picos(topic)
    # 范围预警：过短/过长或缺失维度过多 → 提示收窄
    scope_warning = None
    if len(topic or "") < 6:
        scope_warning = "选题过短，可能检索噪声过大，建议补充 P/I/C/O 维度。"
    elif missing and len(missing) >= 3:
        scope_warning = f"PICOS 缺失维度过多（{', '.join(missing)}），建议先明确研究问题。"
    report = {
        "topic": topic,
        "picos": picos,
        "missing_dimensions": missing,
        "scope_warning": scope_warning,
        "coze_ready": False,
        "note": "本地启发式兜底；双库（Cochrane/PubMed）探针评分与 PROSPERO 查重需 coze 或 ct-registry 支持。",
    }
    # A1 查重探针：真实调 ct-registry（CT.gov 来源）已注册试验数，供选题拥挤度判断
    if registry_probe:
        report["registry_probe"] = registry_probe
        total = registry_probe.get("total")
        if total is not None:
            if total == 0:
                report["scope_warning"] = (report["scope_warning"] or "") + " 注册库未检索到相关试验，属空白/新兴方向。"
            elif total >= 200:
                report["scope_warning"] = (report["scope_warning"] or "") + f" 注册库已检索到 {total} 项相关试验，方向可能已较拥挤，建议明确差异化角度。"
    # 供工作台 A1 面板「PICOS 报告」文本框预填（editable_payload.report 的源）
    # —— 对齐 EDITABLE_KEYS["A1.topic_selection"]=["report"]，避免文本框空白。
    _rep = ["# PICOS 选题报告（本地启发式生成，请确认/修订后放行）", "",
            f"**选题**：{topic}", "",
            "| 维度 | 内容 |", "| --- | --- |"]
    for _k in ("P", "I", "C", "O", "S"):
        _rep.append(f"| {_k} | {picos.get(_k) or '（待填）'} |")
    if missing:
        _rep.append("")
        _rep.append(f"⚠️ 缺失维度：{', '.join(missing)}（本地启发式无法自动推断，请人工补全）")
    if scope_warning:
        _rep.append(f"⚠️ {scope_warning}")
    if registry_probe:
        _rep.append(f"📋 注册库探针：{registry_probe.get('status')}（total={registry_probe.get('total')}）")
    report["report"] = "\n".join(_rep)
    nha = {
        "type": "confirm",
        "prompt": f"选题闸门（本地启发式）{'+ ct-registry 查重' if registry_probe else ''}：{topic}。"
                  f"{scope_warning or '维度基本完整，请确认方向。'}",
        "required": True,
        "gate": "none",
    }
    return report, nha


# ---------------------------------------------------------------------------
# A1 查重探针：真实调 ct-registry（选题闸门补充，非阻塞）
# ---------------------------------------------------------------------------
def _read_registry_xlsx(xlsx_path, limit=5):
    """从 ct-registry 落盘的 report.xlsx「试验总表」抽取样本（登记号/标题/状态/国家/注册日期）。

    ct-registry 跑完会清理中间 json、仅保留 ./out/report.xlsx，故读 xlsx。表头为中文，按子串匹配列。
    """
    import openpyxl
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    target = "试验总表" if "试验总表" in wb.sheetnames else (wb.sheetnames[1] if len(wb.sheetnames) > 1 else None)
    if not target:
        return []
    ws = wb[target]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(c or "").strip() for c in rows[0]]
    col = {}
    for i, h in enumerate(header):
        for key, name in (("id", "登记号"), ("title", "标题"), ("status", "状态"),
                          ("country", "国家"), ("date", "注册日期")):
            if name in h and key not in col:
                col[key] = i
    sample = []
    for r in rows[1:]:
        if not any(r):
            continue
        rec = {k: (str(r[i]).strip() if i < len(r) and r[i] is not None else None) for k, i in col.items()}
        if rec.get("title") or rec.get("id"):
            sample.append(rec)
        if len(sample) >= limit:
            break
    return sample


def a1_registry_check(topic, max_results=10, workdir=None):
    """真实调 ct-registry 做选题查重探针。

    ct-registry 特性（须适配）：① 必须带 --run 才发网络（fixed_flags 已加）；② 忽略 --out-dir、
    把结果写相对 ./out 且仅保留 report.xlsx（中间 json 被清理）。故在临时 cwd 跑，再从
    <workdir>/out/report.xlsx 读样本；同时解析 stdout 日志的 `[ctgov] total=N returned=M` 取总数。
    返回 {status, total, returned, sample[], note}。失败/缺依赖优雅降级，不阻断 A1。
    """
    import os
    import re
    import tempfile
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="a1reg_")
    card = {
        "card_ref": "A1-ct-registry",
        "need_tool": "ct-registry",
        "params": {"condition": topic, "max": max_results},
        "sync": "blocking",
        "timeout_sec": 180,
    }
    outs = cc.execute_tool_cards([card], out_dir=workdir, cwd=workdir)
    probe = {"status": "error", "total": None, "returned": None, "sample": [], "note": ""}
    if not outs:
        probe["note"] = "ct-registry 无返回（映射缺失？）"
        return probe
    o = outs[0]
    probe["status"] = o.get("status")
    log = o.get("result") or ""
    if isinstance(log, str):
        m = re.search(r"\[ctgov\]\s*total=(\d+)\s*returned=(\d+)", log)
        if m:
            probe["total"] = int(m.group(1))
            probe["returned"] = int(m.group(2))
    xlsx = os.path.join(workdir, "out", "report.xlsx")
    if os.path.isfile(xlsx):
        try:
            probe["sample"] = _read_registry_xlsx(xlsx)
        except Exception as e:  # noqa: BLE001
            probe["note"] = f"xlsx 解析失败: {type(e).__name__}: {e}"
    else:
        probe["note"] = (probe["note"] or "") + " report.xlsx 未生成（可能检索无结果或 skill 异常）。"
    return probe


# ---------------------------------------------------------------------------
# A2 检索委派 ct-literature（真实本地执行，不经 coze）
# ---------------------------------------------------------------------------
def a2_build_tool_card(topic, max_results=50, year_from=None, out_dir="."):
    params = {"topic": topic, "max": max_results, "out_dir": out_dir}
    if year_from is not None:
        params["year_from"] = year_from
    return {
        "card_ref": "A2-ct-literature",
        "need_tool": "ct-literature",
        "params": params,
        "sync": "blocking",
        "timeout_sec": 120,
    }


def _extract_studies(res):
    """从 ct-literature 输出中尽力抽取文献列表（兼容多种返回形态）。"""
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for k in ("studies", "papers", "results", "records", "items", "data"):
            v = res.get(k)
            if isinstance(v, list):
                return v
        # 嵌套 data 再探一层
        d = res.get("data")
        if isinstance(d, dict):
            for k in ("studies", "papers", "results", "records", "items"):
                if isinstance(d.get(k), list):
                    return d[k]
    return []


def _read_literature_dir(out_dir):
    """真实 ct-literature 把数据写入 --out-dir 文件（.merged.json 的 works[]，
    或各源 openalex.json/europepmc.json 的 works[]），stdout 仅日志。
    此处回退读取并归一化为 {title,year,doi,source,pmid,is_retracted,url}，去重。
    """
    import glob
    import os
    out_dir = os.path.abspath(out_dir)
    if not os.path.isdir(out_dir):
        return []
    merged = os.path.join(out_dir, ".merged.json")
    files = [merged] if os.path.isfile(merged) else sorted(glob.glob(os.path.join(out_dir, "*.json")))
    studies = []
    seen = set()
    for p in files:
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        works = data.get("works") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if not isinstance(works, list):
            continue
        for w in works:
            if not isinstance(w, dict):
                continue
            key = str(w.get("doi") or w.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            studies.append({
                "title": w.get("title"),
                "year": w.get("year") or w.get("publication_year"),
                "doi": w.get("doi"),
                "source": w.get("source"),
                "pmid": w.get("pmid"),
                "is_retracted": bool(w.get("is_retracted")),
                "url": w.get("url") or w.get("open_access_url"),
                # 检索阶段已抓回的摘要片段，透传到 A3 筛选 / 下载前相关性判断
                "abstract_snippet": w.get("abstract_snippet"),
                # ---- 人工裁决所需元数据（A3 逐条决策要凭刊名/作者/设计等判断相关性）----
                # 这些字段 ct-literature 的 work 里本来就有，此前归一化时被丢弃，
                # 导致 A3 界面只能看到标题。此处按需捞回，缺值一律 None（不臆造）。
                "journal": w.get("publication"),
                "authors": w.get("authors") if isinstance(w.get("authors"), list) else None,
                "publication_date": w.get("publication_date"),
                "volume": w.get("volume"),
                "issue": w.get("issue"),
                "page": w.get("page"),
                "study_type": w.get("study_type"),
                "type": w.get("type"),
                "cited_by_count": w.get("cited_by_count"),
                "keywords": w.get("keywords") if isinstance(w.get("keywords"), list) else None,
                "relevance_score": w.get("relevance_score"),
                "language": w.get("language"),
                "is_safety": bool(w.get("is_safety")),
            })
    return studies


def a2_literature_search(topic, max_results=50, year_from=None, out_dir=".", on_line=None):
    """构建 ct-literature tool_card → execute_tool_cards 本地执行 → 解析文献列表。

    ct-literature 真实行为：数据写入 --out-dir 文件（stdout 仅日志），故优先从
    返回 result 抽取（兼容 mock/未来 coze 形态），为空时回退读 --out-dir 文件。
    返回 (studies, tool_card_outputs, card)。skill 未安装 / 网络失败 → status=error，
    studies=[]，不抛错。

    on_line：可选回调 f(line)，实时接收 ct-literature 子进程的进度输出
    （经 execute_tool_cards 转发），供工作台底部信息栏展示；None 时行为不变。
    """
    card = a2_build_tool_card(topic, max_results, year_from, out_dir=out_dir)
    outs = cc.execute_tool_cards([card], out_dir=out_dir, on_line=on_line)
    studies = []
    if outs:
        o = outs[0]
        if o.get("status") == "ok":
            studies = _extract_studies(o.get("result") or {})
        if not studies:  # 真实 ct-literature：读 --out-dir 文件
            studies = _read_literature_dir(out_dir)
    return studies, outs, card


# ---------------------------------------------------------------------------
# A3 筛选（本地启发式：去重 + 简单纳入标记；coze 部署后由其接管 AI 筛选）
# ---------------------------------------------------------------------------
def _heuristic_include(study, inclusion_hints=None):
    """极简纳入启发式（离线兜底）：排除关键词命中则剔除；若提供纳入关键词，
    则要求标题或摘要片段命中至少一项才纳入，否则标为待人工核验。
    摘要 abstract_snippet 现已透传进 study，故此判断已具备摘要级依据。"""
    text = " ".join(str(v) for v in (study or {}).values() if isinstance(v, (str, int)))
    text = text.lower()
    exclude = ["retracted", "撤稿", "abstract only", "protocol", "letter"]
    if any(k in text for k in exclude):
        return False, "命中排除关键词（离线启发式）"
    hints = [str(h).lower() for h in (inclusion_hints or []) if h]
    if hints:
        if any(h in text for h in hints):
            return True, "标题/摘要命中纳入关键词（离线启发式）"
        return False, "未命中纳入关键词，待人工核验相关性"
    return True, "默认纳入（离线启发式，待人工确认）"


# ---------------------------------------------------------------------------
# A3 决策三态（include / exclude / uncertain）
# 后台原本只有 bool include，「低置信」靠 reason 里含「待人工」隐式表达，
# 前台无法按三态筛选。此处显式化，同时保留 include 布尔以兼容下游
# （A4 用 sc.get("include", True) 判定 → uncertain 一律 include=True，
#   维持「低置信宽松默认纳入、待人工确认」的既有语义，下游行为零变化）。
DECISION_INCLUDE = "include"
DECISION_EXCLUDE = "exclude"
DECISION_UNCERTAIN = "uncertain"


def decision_of(entry):
    """从一条 screened 记录推导三态决策（人工显式 decision 优先，否则按
    include + reason 推导）。返回 include/exclude/uncertain 之一。"""
    if not isinstance(entry, dict):
        return DECISION_UNCERTAIN
    d = entry.get("decision")
    if d in (DECISION_INCLUDE, DECISION_EXCLUDE, DECISION_UNCERTAIN):
        return d
    reason = entry.get("reason") or ""
    if "待人工" in reason:          # 未命中纳入关键词 / 默认纳入待确认
        return DECISION_UNCERTAIN
    return DECISION_INCLUDE if entry.get("include") else DECISION_EXCLUDE


# A3 逐条决策要展示的元数据字段（全部来自 ct-literature work，缺值为 None）。
# 集中定义，供 a3_screening / _a3_nha_from_screened 复用，避免两处漂移。
_A3_META_KEYS = ("journal", "authors", "publication_date", "volume", "issue",
                 "page", "study_type", "type", "cited_by_count", "keywords",
                 "relevance_score", "language", "is_safety", "pmid",
                 "abstract_snippet", "year", "doi", "source", "url",
                 "is_retracted")

# 字段别名：studies 有两条来源（coze result 直返 / _read_literature_dir 读文件），
# 同一含义的键名可能不同（如刊名 work 里叫 publication，归一化后叫 journal）。
# 按顺序取第一个非空值，保证两条路径展示一致，不会出现「有的行有刊名、有的没有」。
_A3_META_ALIASES = {
    "journal": ("journal", "publication", "venue", "journal_name"),
    "page": ("page", "pages"),
    "year": ("year", "publication_year"),
}


def _a3_meta(s):
    """从一条 study / screened 记录抽取 A3 决策所需元数据（含别名归一）。"""
    if not isinstance(s, dict):
        return {}
    out = {}
    for k in _A3_META_KEYS:
        for name in _A3_META_ALIASES.get(k, (k,)):
            v = s.get(name)
            if v is not None:
                out[k] = v
                break
    return out


def _a3_decision_row(s):
    """screened 记录 → 前台「逐条决策」一行（三态 + 元数据）。"""
    d = decision_of(s)
    row = {
        "title": s.get("title"),
        "decision": d,
        # 兼容字段：uncertain 视为宽松纳入（与既有下游语义一致）
        "include": d != DECISION_EXCLUDE,
        "reason": s.get("reason"),
    }
    row.update(_a3_meta(s))
    return row


def a3_screening(studies, inclusion_hints=None):
    seen = set()
    screened = []
    for s in studies:
        if not isinstance(s, dict):
            continue
        key = (str(s.get("doi") or s.get("title") or "").strip().lower())
        if not key or key in seen:
            continue
        seen.add(key)
        inc, reason = _heuristic_include(s, inclusion_hints)
        entry = {
            "title": s.get("title"),
            "year": s.get("year"),
            "doi": s.get("doi"),
            "include": inc,
            "reason": reason,
            # 透传摘要片段，供人工/下载决策判断"是否真相关"
            "abstract_snippet": s.get("abstract_snippet"),
        }
        # 人工裁决所需元数据：刊名/作者/卷期页/研究类型等一并留存
        # （_a3_meta 统一处理两条数据来源的键名差异，见其注释）
        entry.update(_a3_meta(s))
        screened.append(entry)
    return screened, _a3_nha_from_screened(screened)


def _a3_nha_from_screened(screened):
    """从（人工修订后的）screened 列表重建 A3 的 next_human_action 载荷，
    供 override_screened 路径复用（不重跑启发式，避免覆盖人工裁决）。

    三态口径：include / exclude / uncertain，逐条由 decision_of() 推导
    （人工显式 decision 优先）。uncertain = 待人工核验相关性。
    """
    screened = [s for s in (screened or []) if isinstance(s, dict)]
    decs = [decision_of(s) for s in screened]
    n_inc = decs.count(DECISION_INCLUDE)
    n_exc = decs.count(DECISION_EXCLUDE)
    n_uncertain = decs.count(DECISION_UNCERTAIN)
    return {
        "type": "review",
        "prompt": (f"初筛裁决（软停）：去重后 {len(screened)} 篇，"
                   f"纳入 {n_inc} / 剔除 {n_exc} / 低置信 {n_uncertain}。"
                   f"低置信需人工定夺（默认随纳入走，但请复核）。"
                   f"请逐条确认或翻转，重点复核剔除项以防误剔关键研究。"),
        "required": True,
        "gate": "none",
        "summary": {"n_total": len(screened), "n_include": n_inc,
                    "n_exclude": n_exc, "n_uncertain": n_uncertain},
        "decisions": [_a3_decision_row(s) for s in screened],
    }


# ---------------------------------------------------------------------------
# A3 裁决表 Excel 导入/导出（复用 ct-literature 既有模板，不重造）
# ---------------------------------------------------------------------------
def _match_key(doi, title):
    """归一化匹配键（单键）：DOI 优先，缺则回退归一化标题。与 ct-literature
    export_xlsx._norm_doi/_norm_title 口径一致。供导出侧单键 attach 用。"""
    if doi:
        return ("doi", str(doi).strip().lower())
    if title:
        return ("title", " ".join(str(title).strip().lower().split()))
    return None


def _match_keys(doi, title):
    """归一化匹配键（多键列表）：DOI 与标题各自独立成键。

    上传解析时 works 表可能只暴露「标题」（早期模板无 DOI 列），而基线
    decisions 带 DOI —— 两套键空间若不相交会 matched=0。改为任一键命中即
    匹配，彻底消除该问题。
    """
    keys = []
    if doi:
        keys.append(("doi", str(doi).strip().lower()))
    if title:
        keys.append(("title", " ".join(str(title).strip().lower().split())))
    return keys


_DECISION_ALIAS = {
    "纳入": "include", "包含": "include", "in": "include", "include": "include",
    "剔除": "exclude", "排除": "exclude", "ex": "exclude", "exclude": "exclude",
    "低置信": "uncertain", "不确定": "uncertain", "un": "uncertain",
    "uncertain": "uncertain",
}


def _norm_decision(v):
    """把 Excel 单元格里的裁决值归一为 include/exclude/uncertain，无法识别返回 None。"""
    if v is None:
        return None
    return _DECISION_ALIAS.get(str(v).strip())


def _hdr_idx(idx, names):
    for n in names:
        if n in idx:
            return idx[n]
    return None


def _load_merged_works(session_dir):
    """递归找 .merged.json，返回其 works[]（ct-literature 全字段底表）。"""
    session_dir = os.path.abspath(session_dir)
    import glob
    candidates = [os.path.join(session_dir, ".merged.json")]
    candidates += sorted(glob.glob(os.path.join(session_dir, "**", ".merged.json"),
                                   recursive=True))
    for p in candidates:
        if os.path.isfile(p):
            try:
                d = json.load(open(p, encoding="utf-8"))
                ws = d.get("works") or []
                if ws:
                    return ws
            except Exception:  # noqa: BLE001
                continue
    return []


def export_screening_xlsx(session_path, out_path, lang="zh"):
    """导出当前 A3 裁决表为 xlsx（ct-literature 模板 + 裁决/理由列）。

    复用 ct-literature/scripts/export_xlsx（用户指定的「原先设计好的 excel」），
    不重造模板；以底层 .merged.json 的 works 为富底表，叠加当前 A3 decisions
    的「裁决/理由」列。返回 (out_path, n_works)。
    """
    from fullflow import FullflowSession
    sess = FullflowSession.load(session_path)
    # await（含 A3 decisions）持久化在 last_view.fullflow.await（与 server.build_state 同源）
    await_blk = ((sess.data.get("last_view") or {}).get("fullflow") or {}).get("await") or {}
    if await_blk.get("stage_id") != A3:
        raise ValueError("当前不在 A3 初筛阶段，无法导出裁决表（stage_id=%s）"
                         % await_blk.get("stage_id"))
    decisions = (await_blk.get("nha") or {}).get("decisions") or []
    if not decisions:
        raise ValueError("当前会话无 A3 裁决数据（decisions 为空）")
    # 底表 works（含摘要/作者/刊名等全字段），按 doi/title 匹配 decisions
    sdir = sess.data.get("cfg", {}).get("session_dir") or os.path.dirname(session_path)
    works = _load_merged_works(sdir)
    dec_by_key = {}
    for d in decisions:
        k = _match_key(d.get("doi"), d.get("title"))
        if k:
            dec_by_key[k] = d
    ct_decisions = []
    used = set()
    for w in works:
        k = _match_key(w.get("doi"), w.get("title"))
        if k and k in dec_by_key and k not in used:
            used.add(k)
            d = dec_by_key[k]
            ct_decisions.append({
                "title": w.get("title"),
                "doi": w.get("doi"),
                "decision": d.get("decision") or decision_of(d),
                "reason": d.get("reason") or "",
            })
    # 兜底：底表为空或匹配不到时，直接以 decisions 为 works（至少能导出裁决）
    if not ct_decisions:
        ct_decisions = [{"title": d.get("title"), "doi": d.get("doi"),
                         "decision": d.get("decision") or decision_of(d),
                         "reason": d.get("reason") or ""} for d in decisions]
        works = [{"title": d.get("title"), "doi": d.get("doi")} for d in decisions]
    # 懒加载 ct-literature 导出模块（不硬依赖，跨技能复用）
    _ct = os.path.expanduser("~/.workbuddy/skills/ct-literature/scripts")
    if _ct not in sys.path:
        sys.path.insert(0, _ct)
    import export_xlsx as ex  # noqa: F401  (懒加载；import 失败即抛，由端点捕获)
    meta = {"topic": sess.data.get("topic", ""), "total": len(works)}
    # 裁决列下拉选项：中文显示标签 + 英文 internal 值，与 _DECISION_ALIAS 口径
    # 一致（parse_screening_xlsx 经 _norm_decision 归一）。双标签兼容预填英文值。
    decision_options = ["纳入", "排除", "低置信", "include", "exclude", "uncertain"]
    ex.export_workbook({"count": len(works), "works": works, "meta": meta},
                       out_path, lang=lang, decisions=ct_decisions,
                       decision_options=decision_options)
    return out_path, len(works)


def parse_screening_xlsx(xlsx_path, current_decisions):
    """解析上传的裁决表（ct-literature 模板，含裁决/理由列）。

    以 current_decisions 为基线（保留元数据），按 DOI/标题匹配覆盖「裁决/理由」。
    返回 (screened, stats)。stats: {matched, updated, unmatched, total}。
    screened 为完整决策行列表（含元数据 + include 派生），可直接喂 override_screened。
    """
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    # 优先找含「裁决」表头的 sheet
    target = None
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        try:
            hdr = next(rows)
        except StopIteration:
            continue
        if hdr and any(isinstance(h, str) and "裁决" in h for h in hdr):
            target = (hdr, rows)
            break
    if target is None and wb.worksheets:
        ws = wb.worksheets[0]
        rows = ws.iter_rows(values_only=True)
        hdr = next(rows)
        target = (hdr, rows)
    if target is None:
        raise ValueError("上传的 xlsx 无工作表")
    hdr, rows = target
    idx = {str(h).strip(): i for i, h in enumerate(hdr) if h is not None}
    i_doi = _hdr_idx(idx, ["doi", "DOI", "DOI/PMID"])
    i_title = _hdr_idx(idx, ["标题", "title", "Title"])
    i_dec = _hdr_idx(idx, ["裁决", "决策", "decision", "Decision"])
    i_reason = _hdr_idx(idx, ["理由", "reason", "Reason"])
    # 上传表：每个单元格行按 DOI/标题各生成一个匹配键（多键）→ (decision, reason)
    # 用 _match_keys 而非 _match_key：早期模板若无 DOI 列、仅标题，仍能与带 DOI
    # 的基线 decisions 命中，杜绝「两套键空间不相交 → matched=0」。
    upload_by_key = {}
    for r in rows:
        if r is None:
            continue
        doi = r[i_doi] if (i_doi is not None and i_doi < len(r)) else None
        title = r[i_title] if (i_title is not None and i_title < len(r)) else None
        dec_raw = r[i_dec] if (i_dec is not None and i_dec < len(r)) else None
        reason = r[i_reason] if (i_reason is not None and i_reason < len(r)) else None
        val = {"decision": _norm_decision(dec_raw),
               "reason": "" if reason is None else str(reason).strip()}
        for k in _match_keys(doi, title):
            upload_by_key[k] = val
    # 合并：基线（保留元数据）+ 上传覆盖裁决/理由；基线任一匹配键命中即视为匹配
    screened = []
    n_matched = n_updated = 0
    base_keys = set()
    for d in current_decisions:
        base_keys.update(_match_keys(d.get("doi"), d.get("title")))
    for d in current_decisions:
        entry = dict(d)
        hit = None
        for k in _match_keys(d.get("doi"), d.get("title")):
            if k in upload_by_key:
                hit = upload_by_key[k]
                break
        if hit is not None:
            n_matched += 1
            if hit["decision"] and hit["decision"] != entry.get("decision"):
                entry["decision"] = hit["decision"]
                n_updated += 1
            if hit["reason"]:
                entry["reason"] = hit["reason"]
        screened.append(entry)
    # 规整：补 include 派生字段（下游语义：uncertain/exclude 均按需）
    for s in screened:
        s["include"] = decision_of(s) != DECISION_EXCLUDE
    unmatched = sum(1 for k in upload_by_key if k not in base_keys)
    stats = {"matched": n_matched, "updated": n_updated,
             "unmatched": unmatched, "total": len(screened)}
    return screened, stats


def apply_screening_upload(session_path, screened):
    """把上传解析后的 screened 应用到当前会话：
    1) 更新 A3 软停快照的 decisions（前端立即可见）；
    2) 记录一条 revised 决策（sticky：后续 approved/revised 按钮经 override_screened 生效）。
    不前进流程，回到 A3 软停供复核。返回更新后的 FullflowSession。
    """
    from fullflow import FullflowSession
    sess = FullflowSession.load(session_path)
    # 工作台读取的 canonical 位置是 last_view.fullflow.await（与 build_state 同源）；
    # data["await"] 作为兼容位置一并更新，避免两处漂移。
    lv_await = (((sess.data.get("last_view") or {}).get("fullflow") or {}).get("await") or {})
    legacy_await = sess.data.get("await") or {}
    if lv_await.get("stage_id") != A3 and legacy_await.get("stage_id") != A3:
        raise ValueError("当前不在 A3 初筛阶段，无法应用 Excel 上传（stage_id=%s）"
                         % (lv_await.get("stage_id") or legacy_await.get("stage_id")))
    new_nha = _a3_nha_from_screened(screened)
    # 与 export_screening_xlsx / build_state 同源：nha 是 await 的顶层键（与 stage_result 并列）
    if lv_await:
        lv_await["nha"] = new_nha
        sess.data["last_view"]["fullflow"]["await"] = lv_await
    if legacy_await:
        legacy_await["nha"] = new_nha
        sess.data["await"] = legacy_await
    sess.record_decision({
        "stage_id": A3, "action": "revised",
        "revision": {"screened": screened},
        "note": "Excel 上传更新裁决", "decided_by": "workbench",
    })
    sess.save()
    return sess


# ---------------------------------------------------------------------------
# A4 提取 + 🔴 extraction_review 红线闸（本地强执）
# ---------------------------------------------------------------------------
def _parse_extraction(extraction_table):
    if isinstance(extraction_table, list):
        return extraction_table
    if isinstance(extraction_table, str) and extraction_table.strip():
        try:
            return json.loads(extraction_table)
        except json.JSONDecodeError:
            # 退化：按行拆分，标记待结构化
            return [{"raw": ln} for ln in extraction_table.strip().splitlines() if ln.strip()]
    return []


# ---------------------------------------------------------------------------
# A4 自动闭环辅助：A3 摘要门控 → 自动落盘 OA PDF → pdf_extractor 抽取 2×2 表
# ---------------------------------------------------------------------------
# ⚠️ 懒加载约束：pdf_extractor 依赖 fitz/pdfplumber（仅 anaconda 等含 PDF 依赖的
#    Python 有）。block_a 是共享模块，被 fullflow/run_case_human 在 managed Python 下
#    导入时不应因缺 PDF 库而整体 import 失败，故仅在此函数内局部 import。
def _pick_candidate(study):
    """返回 (kind, ident) 或 None。优先级：直链 PDF > pmid(PMC) > doi(Unpaywall) > doi(PMC-OA)。"""
    u = (study.get("url") or study.get("open_access_url") or "").strip()
    if u.lower().endswith(".pdf") or "europepmc" in u.lower() or u.rstrip("/").endswith("/pdf"):
        return ("url", u)
    if study.get("pmid"):
        return ("pmid", str(study["pmid"]))
    if study.get("doi"):
        return ("doi", str(study["doi"]))
    return None


def _resolve_pdf_url(cand, email):
    import pdf_fetch
    kind, ident = cand
    if kind == "url":
        return ident
    if kind == "pmid":
        return pdf_fetch.pmid_to_pdf(ident)
    if kind == "doi":
        return pdf_fetch.doi_to_pdf(ident, email) or pdf_fetch.doi_to_pmc_pdf(ident)
    return None


def _is_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(5).startswith(b"%PDF")
    except Exception:  # noqa: BLE001
        return False


def _derive_inclusion_hints(topic):
    """从自由文本主题派生纳入门控词（去停用词）。ANY 命中即纳入（宽松 OR 语义）。

    仅作离线启发式兜底；用户可显式传 inclusion_hints 覆盖。派生为空时返回 None
    （A3 退化为「默认全纳入 + 记录摘要」）。
    """
    import re
    stop = {"the", "a", "an", "of", "for", "in", "on", "with", "and", "or", "vs",
            "versus", "to", "from", "patients", "patient", "study", "meta",
            "analysis", "randomized", "randomised", "trial", "effect", "outcome",
            "comparison", "group", "using", "type", "adult", "adults"}
    toks = re.findall(r"[a-z0-9][a-z0-9\-]{2,}", (topic or "").lower())
    hints = sorted({t for t in toks if t not in stop})
    return hints or None


# ── A4 PDF 统一缓存目录（绝对路径，不依赖启动 cwd；a4_stream / seam_test / 工作台上传
#    端点全部共享此目录，避免「adapters/pdfs 与 workbench/pdfs 双目录并存」「从不同 cwd
#    启动落到不同目录」「docN 覆盖式命名」导致的互相覆盖与重复下载）。
A4_PDF_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_cache")


def _pdf_stem(study):
    """A4 PDF 落盘的稳定文件基名（同一文献跨轮次恒定）。

    优先用 DOI（文件名可读），无 DOI 时用标题 md5 前 10 位。稳定命名是
    「重跑不重复下载」的基础：同名文件存在且确为真 PDF 即直接复用。
    """
    import hashlib
    doi = str((study or {}).get("doi") or "").strip().lower()
    if doi:
        slug = re.sub(r"[^a-z0-9]+", "_", doi).strip("_")[:90]
        if slug:
            return "doi_" + slug
    title = str((study or {}).get("title") or "").strip().lower()
    return "t_" + (hashlib.md5(title.encode("utf-8")).hexdigest()[:10] if title else "notitle")


def _a4_cached_pdf(study, pdf_dir, cache_map=None):
    """查该文献已落盘的 PDF（跨轮次复用，避免重复下载）。

    三级查找：① cache_map（调用方由上一轮 A4 结果 per_doc 建立，可兼容旧的
    docN.pdf 命名）；② 当前稳定命名文件；③ 裸 DOI 命名（兼容旧版 /a4_stream
    未带协议前缀时落盘的 doi_<裸doi>.pdf）。命中且确为真 PDF 才复用。
    """
    key = str((study or {}).get("doi") or (study or {}).get("title") or "").strip().lower()
    if key and cache_map:
        p = cache_map.get(key)
        if p and os.path.isabs(p) and os.path.exists(p) and _is_pdf(p):
            return p
    p = os.path.join(pdf_dir, _pdf_stem(study) + ".pdf")
    if os.path.exists(p) and _is_pdf(p):
        return p
    # ③ 裸 DOI 兼容：旧版把 PDF 存为 doi_<去掉 https://doi.org/ 的裸 doi stem>
    doi = str((study or {}).get("doi") or "").strip().lower()
    if doi:
        bare = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi).strip("/")
        if bare:
            slug = re.sub(r"[^a-z0-9]+", "_", bare).strip("_")[:90]
            lp = os.path.join(pdf_dir, "doi_" + slug + ".pdf")
            if os.path.exists(lp) and _is_pdf(lp):
                return lp
    return None


def _a4_extract_pdf(pdf_path, pdf_extractor):
    """对已落盘 PDF 抽取 2x2 表。返回 (rows, tworows, n_candidates, err)。"""
    if pdf_extractor is None:
        return [], [], 0, None
    try:
        res = pdf_extractor.extract(pdf_path)
        rows = pdf_extractor.to_a4_rows(res) or []
        n_cand = len(res.get("candidates") or [])
    except Exception as e:  # noqa: BLE001
        return [], [], 0, f"{type(e).__name__}: {e}"
    tworows = [r for r in rows if all(r.get(k) is not None for k in ("ai", "bi", "ci", "di"))]
    return rows, tworows, n_cand, None


def _a4_fetch_one(cand, out_path, email, pdf_extractor):
    """单篇「解析直链 → 下载 → 抽取」（纯 IO/CPU、无共享状态 → 可并行）。

    返回 (out, events)：out 为该篇最终状态，events 为过程事件（downloading /
    extracting），由主循环按 index 顺序统一 emit。
    """
    import pdf_fetch
    evs = []
    url = _resolve_pdf_url(cand, email)
    if not url:
        return ({"event": "failed", "status": "needs_upload", "gate": "pass_no_oa",
                 "reason": "通过门控但无 OA 副本（付费墙），需用户上传 PDF",
                 "pdf": None, "rows": [], "n_rows": 0, "n_tworows": 0}, evs)
    evs.append({"event": "downloading", "url": url})
    if not pdf_fetch.download(url, out_path) or not _is_pdf(out_path):
        return ({"event": "failed", "status": "needs_upload", "gate": "pass_download_fail",
                 "reason": "通过门控但下载失败/非真 PDF，需用户上传 PDF",
                 "pdf": None, "rows": [], "n_rows": 0, "n_tworows": 0}, evs)
    if pdf_extractor is None:
        return ({"event": "downloaded_no_extract", "status": "downloaded_no_extract",
                 "gate": "pass_downloaded", "reason": "PDF 已下载，待补抽取",
                 "pdf": out_path, "rows": [], "n_rows": 0, "n_tworows": 0}, evs)
    evs.append({"event": "extracting", "pdf": out_path})
    rows, tworows, n_cand, err = _a4_extract_pdf(out_path, pdf_extractor)
    if err:
        return ({"event": "failed", "status": "needs_upload", "gate": "extract_fail",
                 "reason": f"PDF 下载成功但抽取失败：{err}",
                 "pdf": out_path, "rows": [], "n_rows": 0, "n_tworows": 0}, evs)
    return ({"event": "extracted", "status": "extracted", "gate": "pass_downloaded",
             "reason": None, "pdf": out_path, "rows": rows,
             "n_rows": len(rows), "n_tworows": len(tworows), "n_candidates": n_cand}, evs)


def _ordered_parallel(items, workers, fn):
    """按提交顺序产出 fn 结果，内部以 workers 大小的滑动窗口并行执行。

    保证：① 并发度不超过 workers；② 输出顺序与 items 一致（前端按 index 定位
    行，乱序会让进度行跳动）。fn 须自行兜住异常，此处仅兜底跳过异常项。
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        it = iter(items)
        pending, nxt_seq, seq = {}, 0, 0
        for _ in range(workers):
            try:
                item = next(it)
            except StopIteration:
                break
            pending[nxt_seq] = ex.submit(fn, item)
            nxt_seq += 1
        while pending:
            fut = pending.pop(seq)
            try:
                res = fut.result()
            except Exception:  # noqa: BLE001 — fn 未兜住的异常不得拖垮整批
                res = None
            if res is not None:
                yield res
            try:
                item = next(it)
            except StopIteration:
                pass
            else:
                pending[nxt_seq] = ex.submit(fn, item)
                nxt_seq += 1
            seq += 1


def a4_stream(studies, screened, pdf_dir=None, max_attempts=12,
              inclusion_hints=None, email=None, workers=4, pdf_cache_map=None):
    """生成器：逐篇研究执行 A4 下载+抽取，实时 yield 进度事件（供工作台实时预览）。

    每次 yield 一个事件 dict，关键字段：
      event: start | cached | skip | failed | deferred | downloading |
             extracting | extracted | downloaded_no_extract | done | error
      index / total / title / doi / gate / reason / url / pdf / n_rows / n_tworows
    失败不中断（继续处理下一篇）。末次 yield 为
      {"event": "done", "result": {<完整 a4_auto_fetch_and_extract dict>}}。

    workers：下载/抽取并发度（默认 4）。事件仍按 index 顺序产出，前端观感与串行
    一致，整体耗时近似降为 1/workers。
    pdf_cache_map：{文献 key(doi|title 小写) → 已落盘 PDF 绝对路径}；命中即跳过
    下载、直接抽取（emit cached），实现「重跑不重复下载」。
    同步封装 a4_auto_fetch_and_extract 与原行为一致（消费至 done 取 result）。
    """
    import pdf_fetch
    if email is None:
        email = pdf_fetch.DEFAULT_EMAIL
    if pdf_dir is None:
        pdf_dir = A4_PDF_CACHE_DIR
    os.makedirs(pdf_dir, exist_ok=True)

    # study→screened 按 doi/title 对齐（二者顺序一致亦可 zip）
    def _key(s):
        return str((s or {}).get("doi") or (s or {}).get("title") or "").strip().lower()
    scr_by_key = {_key(s): s for s in screened if isinstance(s, dict)}

    # pdf_extractor 懒加载（缺 PDF 库时优雅降级：仅落盘不抽取）
    try:
        import pdf_extractor  # noqa: F401
    except Exception as e:  # noqa: BLE001
        pdf_extractor = None
        _dep_note = f"pdf_extractor 不可用（缺 fitz/pdfplumber）：{type(e).__name__}: {e}"
    else:
        _dep_note = None

    studies_list = [s for s in studies if isinstance(s, dict)]
    total = len(studies_list)

    def _emit(ev):
        ev.setdefault("total", total)
        return ev

    extracted_rows = []        # 仅 2x2 结局表（ai/bi/ci/di 齐全）→ 供下游 B1 合并
    review_rows = []           # 全量抽取行（含连续量/描述性）→ 供 A4 人工核验
    fetch_log = []
    needs_upload = []
    per_doc = [None] * total   # 逐篇分组（按 index 定位，供工作台 A4 逐篇展示）
    n_passed = n_dl = n_ext = n_fetch = 0

    # ── 阶段 1：纯本地判定（零网络）。逐篇 yield start/skip/no_candidate/deferred，
    #    将「需下载」与「可复用缓存」的篇目按 index 顺序放入 work 队列。
    work = []
    for i, s in enumerate(studies_list):
        sc = scr_by_key.get(_key(s)) or {}
        title = s.get("title") or ""
        doi = s.get("doi")
        meta = {"index": i, "total": total, "title": title, "doi": doi}
        yield _emit({"event": "start", **meta})

        if sc and not sc.get("include", True):  # screened 为空（未筛）→ 宽松默认纳入
            r = {"title": title, "doi": doi, "gate": "relevance_skip",
                 "reason": sc.get("reason", "未通过摘要相关性门控")}
            fetch_log.append(r)
            per_doc[i] = {"index": i, "title": title, "doi": doi, "status": "skip",
                          "reason": r["reason"], "pdf": None, "rows": [], "n_tworows": 0}
            yield _emit({"event": "skip", **meta, **r})
            continue
        n_passed += 1

        cand = _pick_candidate(s)
        if not cand:
            r = {"title": title, "doi": doi, "gate": "no_candidate",
                 "reason": "通过相关性门控但无下载入口（无 PMID/DOI/直链），需用户上传 PDF"}
            fetch_log.append(r); needs_upload.append(r)
            per_doc[i] = {"index": i, "title": title, "doi": doi, "status": "needs_upload",
                          "reason": r["reason"], "pdf": None, "rows": [], "n_tworows": 0}
            yield _emit({"event": "failed", **meta, **r})
            continue

        cached = _a4_cached_pdf(s, pdf_dir, pdf_cache_map)
        if cached is None:
            # 配额按「实际发起下载数」计（缓存复用不消耗；付费墙/网络失败不消耗），
            # 确保可下载的 OA 论文不被饿死
            if n_fetch >= max_attempts:
                r = {"title": title, "doi": doi, "gate": "quota_deferred",
                     "reason": f"已达 max_attempts={max_attempts} 篇实际下载，其余通过门控者留待下一轮"}
                fetch_log.append(r)
                per_doc[i] = {"index": i, "title": title, "doi": doi, "status": "deferred",
                              "reason": r["reason"], "pdf": None, "rows": [], "n_tworows": 0}
                yield _emit({"event": "deferred", **meta, **r})
                continue
            n_fetch += 1
            work.append((i, s, cand, os.path.join(pdf_dir, _pdf_stem(s) + ".pdf"), None))
        else:
            work.append((i, s, cand, cached, cached))

    # ── 阶段 2：下载 + 抽取（并发执行，按 index 顺序产出事件与结果）
    def _run(item):
        i, s, cand, out_path, cached = item
        title, doi = s.get("title") or "", s.get("doi")
        base = {"index": i, "total": total, "title": title, "doi": doi}
        try:
            if cached:
                evs = [{"event": "cached", "pdf": cached, **base}]
                if pdf_extractor is not None:
                    evs.append({"event": "extracting", "pdf": cached, **base})
                rows, tworows, n_cand, err = _a4_extract_pdf(cached, pdf_extractor)
                if pdf_extractor is None:
                    out = {"event": "downloaded_no_extract", "status": "downloaded_no_extract",
                           "gate": "pass_downloaded", "reason": "PDF 已下载，待补抽取",
                           "pdf": cached, "rows": [], "n_rows": 0, "n_tworows": 0}
                elif err:
                    out = {"event": "failed", "status": "needs_upload", "gate": "extract_fail",
                           "reason": f"PDF 已缓存但抽取失败：{err}",
                           "pdf": cached, "rows": [], "n_rows": 0, "n_tworows": 0}
                else:
                    out = {"event": "extracted", "status": "extracted", "gate": "pass_downloaded",
                           "reason": None, "pdf": cached, "rows": rows,
                           "n_rows": len(rows), "n_tworows": len(tworows),
                           "n_candidates": n_cand, "cached": True}
            else:
                out, evs = _a4_fetch_one(cand, out_path, email, pdf_extractor)
                evs = [{**e, **base} for e in evs]
        except Exception as e:  # noqa: BLE001 — 单篇异常不得拖垮整批
            out = {"event": "failed", "status": "needs_upload", "gate": "worker_error",
                   "reason": f"处理异常：{type(e).__name__}: {e}",
                   "pdf": None, "rows": [], "n_rows": 0, "n_tworows": 0}
            evs = []
        return i, out, evs

    nw = max(1, int(workers or 1))
    results = ((_run(it) for it in work) if nw == 1 else _ordered_parallel(work, nw, _run))
    for i, out, evs in results:
        s = studies_list[i]
        title, doi = s.get("title") or "", s.get("doi")
        for e in evs:
            yield _emit(dict(e))
        pdf = out.get("pdf")
        rows = out.get("rows") or []
        n_tworows = out.get("n_tworows") or 0
        if out["status"] == "extracted":
            tworows = [r for r in rows if all(r.get(k) is not None for k in ("ai", "bi", "ci", "di"))]
            n_dl += 1
            n_ext += len(tworows)
            extracted_rows.extend(tworows)
            review_rows.extend(rows)
            fetch_log.append({"title": title, "doi": doi, "gate": "pass_downloaded",
                              "pdf": pdf, "n_rows": len(rows), "n_tworows": len(tworows),
                              "n_candidates": out.get("n_candidates", 0),
                              **({"cached": True} if out.get("cached") else {})})
        elif out["status"] == "downloaded_no_extract":
            n_dl += 1
            fetch_log.append({"title": title, "doi": doi, "gate": "pass_downloaded", "pdf": pdf,
                              "n_rows": 0, "n_tworows": 0, "n_candidates": 0,
                              "note": "PDF 已落盘，但缺 PDF 抽取库，待人工/环境补抽取"})
        else:
            r = {"title": title, "doi": doi, "gate": out.get("gate", "failed"),
                 "reason": out.get("reason"), **({"pdf": pdf} if pdf else {})}
            fetch_log.append(r); needs_upload.append(r)
        per_doc[i] = {"index": i, "title": title, "doi": doi, "status": out["status"],
                      "reason": out.get("reason"), "pdf": pdf, "rows": rows,
                      "n_rows": len(rows), "n_tworows": n_tworows,
                      **({"cached": True} if out.get("cached") else {})}
        yield _emit({"event": out["event"], "index": i, "total": total, "title": title,
                     "doi": doi, "gate": out.get("gate"), "reason": out.get("reason"),
                     "pdf": pdf, "n_rows": len(rows), "n_tworows": n_tworows,
                     **({"cached": True} if out.get("cached") else {})})

    result = {
        "extracted_rows": extracted_rows,
        "extracted_rows_review": review_rows,
        "fetch_log": fetch_log,
        "per_doc": per_doc,
        "n_screened": total,
        "n_passed": n_passed,
        "n_downloaded": n_dl,
        "n_extracted": n_ext,
        "needs_user_upload": needs_upload,
        "_dep_note": _dep_note,
    }
    yield _emit({"event": "done", "result": result})


def a4_auto_fetch_and_extract(studies, screened, pdf_dir=None, max_attempts=12,
                              inclusion_hints=None, email=None, on_a4_event=None,
                              workers=4, pdf_cache_map=None):
    """A3 摘要门控 → 自动落盘 OA 全文 PDF → pdf_extractor 抽取 2×2 表（同步封装）。

    消费 a4_stream 至 done，返回完整结果 dict（与原实现行为一致）。
    on_a4_event：可选回调 f(ev)，实时转发 a4_stream 的逐篇进度事件
    （start/cached/downloading/extracting/extracted/failed/...），供工作台续跑路径实时上屏。
    workers / pdf_cache_map：透传给 a4_stream（并发度 / 已落盘 PDF 复用映射）。
    """
    last = None
    for ev in a4_stream(studies, screened, pdf_dir=pdf_dir, max_attempts=max_attempts,
                        inclusion_hints=inclusion_hints, email=email, workers=workers,
                        pdf_cache_map=pdf_cache_map):
        if on_a4_event:
            try:
                on_a4_event(ev)
            except Exception:  # noqa: BLE001 — 回调异常不得拖垮抽取
                pass
        if ev.get("event") == "done":
            last = ev["result"]
    return last


def a4_persist_result(session_path, result):
    """把 A4 预览结果（含 per_doc 逐篇分组、pdf 绝对路径、页码锚点）落盘到会话。

    供工作台「逐篇文档展示」直接读取（STATE.await.a4_result），并支持上传 PDF 后
    就地回写单篇状态。同时兼容 legacy data[\"await\"]。
    """
    from fullflow import FullflowSession
    sess = FullflowSession.load(session_path)
    ff = (sess.data.setdefault("last_view", {}) or {}).setdefault("fullflow", {}) or {}
    aw = (ff.setdefault("await", {}) or {})
    aw["a4_result"] = result
    ff["await"] = aw
    legacy = sess.data.get("await")
    if isinstance(legacy, dict):
        legacy["a4_result"] = result
        sess.data["await"] = legacy
    sess.save()
    return result


def a4_get_result(session_path):
    """读取已落盘的 A4 结果（无则返回 None）。"""
    from fullflow import FullflowSession
    sess = FullflowSession.load(session_path)
    ff = (sess.data.get("last_view") or {}).get("fullflow") or {}
    return (ff.get("await") or {}).get("a4_result")


def a4_data_extraction(screened_studies, extraction_table=None, studies=None,
                       auto_fetch=False, auto_fetch_dir=None, max_attempts=12,
                       inclusion_hints=None, pdf_email=None, on_a4_event=None,
                       workers=4, pdf_cache_map=None):
    # 🔴 红线闸：效应量/事件数等关键字段须人工核验放行方可进 Block B
    nha = {
        "type": "approve",
        "prompt": "请人工核验提取数据（TE/seTE/事件数等关键字段），批准后方可进入 Block B 计算。",
        "required": True,
        "gate": "extraction_review",
    }

    # 路径 A：用户提供提取表（演示/数据路径）→ 解析即用，绝不联网
    if extraction_table is not None:
        rows = _parse_extraction(extraction_table)
        result = {
            "extracted_rows": rows,
            "n_screened": len(screened_studies),
            "n_extracted": len(rows) if isinstance(rows, list) else 0,
            "coze_ready": False,
            "note": "提取表由用户提供（手动/演示数据），待本闸人工核验。",
        }
        return result, nha

    # 路径 B：无提取表 + 有文献 + 开启 auto_fetch → A3 门控 → 自动落盘+抽取（草稿）
    if auto_fetch and studies:
        try:
            af = a4_auto_fetch_and_extract(
                studies, screened_studies, pdf_dir=auto_fetch_dir,
                max_attempts=max_attempts, inclusion_hints=inclusion_hints,
                email=pdf_email, on_a4_event=on_a4_event,
                workers=workers, pdf_cache_map=pdf_cache_map,
            )
        except Exception as e:  # noqa: BLE001
            # 自动抓取整段失败不得拖垮 Block A；降级回离线占位并如实说明
            result = {
                "extracted_rows": [],
                "n_screened": len(screened_studies),
                "n_extracted": 0,
                "coze_ready": False,
                "note": f"A4 自动抓取异常，降级为离线占位：{type(e).__name__}: {e}",
            }
            return result, nha

        dep = af.get("_dep_note")
        result = {
            "extracted_rows": af["extracted_rows"],
            "extracted_rows_review": af["extracted_rows_review"],
            "n_screened": af["n_screened"],
            "n_passed": af["n_passed"],
            "n_downloaded": af["n_downloaded"],
            "n_extracted": af["n_extracted"],
            "needs_user_upload": af["needs_user_upload"],
            "fetch_log": af["fetch_log"],
            "coze_ready": False,
            "note": ("已由 A3 摘要门控自动下载 OA 全文并抽取 2×2 表（草稿），须经本闸人工核验放行；"
                     "付费墙/无 OA 篇目已记录待用户上传 PDF。"
                     + (f" ⚠️ {dep}" if dep else "")),
        }
        return result, nha

    # 路径 C：无提取表也未开启 auto_fetch → 离线占位（旧行为，保持兼容）
    rows = []
    result = {
        "extracted_rows": rows,
        "n_screened": len(screened_studies),
        "n_extracted": 0,
        "coze_ready": False,
        "note": "提取草稿为离线占位；coze 部署后由 AI 生成提取表并经本闸人工核验。",
    }
    return result, nha


# ---------------------------------------------------------------------------
# 人工决策判定（红线闸放行）
# ---------------------------------------------------------------------------
def _decision_approves(decision, stage_id):
    if not isinstance(decision, dict):
        return False
    return (decision.get("stage_id") == stage_id
            and str(decision.get("action", "")).lower() in ("approved", "approve"))


def _any_approve(decisions, stage_id):
    """human_decision 兼容单 dict / list（fullflow 累积凭据）；任一 approved 即 True。"""
    if isinstance(decisions, dict):
        decisions = [decisions]
    return any(_decision_approves(d, stage_id) for d in (decisions or []))


def _soft_stop(env, pid, stages, tool_card_outputs, stage, sid, pause_at, decisions):
    """P3 软停靠（fullflow HITL，spec contracts/fullflow/v0.1.0）。

    pause_at 含 sid 且未持对应 approved 凭据 → 提前软停返回
    （done=False / await_human=True / gate=None / pause=True，区别于红线闸）。
    """
    if not (pause_at and sid in pause_at) or _any_approve(decisions, sid):
        return None
    return {"pipeline_id": pid, "pipeline": env["pipeline"], "stages": stages,
            "attachments": [], "tool_card_outputs": tool_card_outputs or [],
            "done": False, "await_human": True, "gate": None, "final": stage,
            "pause": True, "human_decisions": []}


# ---------------------------------------------------------------------------
# 编排：A1 → A2 → A3 → A4（本地优先；use_coze 占位待 coze 部署后启用）
# ---------------------------------------------------------------------------
def _translate_topic_authoritative(text):
    """A2 检索式翻译（关联 ct-base 权威 kw_localize，不重复造轮子）。

    ct-base 规范（references/bilingual_retrieval.md）：中文输入 → 各源「翻译前置，
    对照表优先 + miss 外接翻译 API 兜底」。本函数复用 ct-base/scripts/kw_localize.py
    的 localize_with_fallback：先查策展双语对照表（term_map），整句未译干净时
    走 online_translate 兜底（MyMemory 无密钥，可被 CT_TRANSLATE_ONLINE=0 关闭）。

    产出干净英文 query 传给 ct-literature —— 其收到纯英文后内部 topic_translator
    原样短路（无双重翻译、前后一致），从而多源（OpenAlex + Europe PMC 等）都能
    命中。返回 strategy dict 供 A2 面板如实展示（含未译残留与翻译来源）。
    """
    strategy = {
        "raw_topic": text,
        "translated_query": text,
        "untranslated": [],
        "fully_translated": True,
        "translation_hits": [],
        "source": "same",
    }
    if not text:
        return strategy
    try:
        if _CT_BASE_SCRIPTS not in sys.path:
            sys.path.insert(0, _CT_BASE_SCRIPTS)
        import kw_localize as _k  # noqa: PLC0415  (ct-base 权威实现)
    except Exception as _e:  # noqa: BLE001  (skill 缺失/import 失败 → 原样放行，不阻断)
        strategy["translation_hits"] = ["kw_localize import 失败（ct-base 缺失？），"
                                        "按原始主题检索: %s" % _e]
        return strategy
    en, source = _k.localize_with_fallback(text, "en")
    strategy["translated_query"] = en
    strategy["source"] = source
    residual = re.findall(r"[\u4e00-\u9fff]+", en)
    if residual:
        # 仍含中文 → 未译干净（source 应为 miss 或兜底 API 亦失败），如实标注待人工补全
        strategy["untranslated"] = residual
        strategy["fully_translated"] = False
        strategy["translation_hits"] = [
            "本地对照表 miss 且外接翻译 API 未兜底成功（可用 CT_TRANSLATE_ONLINE=0 "
            "关闭联网翻译），请人工补全未译词或改用英文主题"]
    elif source == "online":
        strategy["translation_hits"] = ["本地对照表未收全 → 外接翻译 API 兜底（ct-base "
                                        "bilingual_retrieval.md 规范）"]
    elif source == "term_map":
        strategy["translation_hits"] = ["本地策展对照表（term_map）命中"]
    return strategy


def _a2_coverage_nha(studies, outs2, card, max_results, year_from, strategy=None):
    """A2 检索策略/覆盖确认 payload（软停）。

    展示各库条数、检索状态、撤稿数、原始主题、优化翻译后的检索式与未译残留，
    供人工闸确认。核心防「沉默漏检」：无 token 静默跳库 / skill 缺失返回空时，
    by_source 缺库 + search_status!=ok 即暴露；检索式展示优化翻译结果而非原始输入。
    """
    strategy = strategy or {}
    by_source = {}
    for s in studies:
        if isinstance(s, dict):
            src = s.get("source") or "unknown"
            by_source[src] = by_source.get(src, 0) + 1
    status = (outs2[0].get("status") if outs2 and isinstance(outs2[0], dict) else "n/a")
    search_ok = status == "ok"
    retracted = sum(1 for s in studies if isinstance(s, dict) and s.get("is_retracted"))
    params = (card or {}).get("params") or {}
    raw_topic = strategy.get("raw_topic") or params.get("topic")
    translated_query = strategy.get("translated_query") or params.get("topic")
    untranslated = strategy.get("untranslated") or []
    fully = strategy.get("fully_translated", True)
    bits = [f"原始主题={raw_topic!r}", f"优化检索式={translated_query!r}"]
    if year_from is not None:
        bits.append(f"year≥{year_from}")
    bits.append(f"上限={max_results}")
    src_str = "、".join(f"{k}={v}" for k, v in sorted(by_source.items())) or "无来源标注"
    prompt = (f"检索策略确认（软停）：{'; '.join(bits)} → 合并 {len(studies)} 篇（{src_str}）。"
              + (f" ⚠️ 检索状态={status}，结果可能不完整/为空，请核查检索配置。" if not search_ok else "")
              + (f" 含撤稿 {retracted} 篇。" if retracted else "")
              + ("" if fully else f" ⚠️ 检索式含未翻译词：{'、'.join(untranslated)}，建议人工补全或换英文主题。")
              + " 请确认覆盖充分，或调整查询/库后重跑。")
    coverage = {
        "total": len(studies),
        "by_source": by_source,
        "search_status": status,
        "retracted": retracted,
        "raw_topic": raw_topic,
        "query": translated_query,
        "translated_query": translated_query,
        "untranslated": untranslated,
        "fully_translated": fully,
        "translation_hits": strategy.get("translation_hits", []),
        "year_from": year_from,
        "max_results": max_results,
    }
    return {
        "type": "confirm",
        "prompt": prompt,
        "required": True,
        "gate": "none",
        "coverage": coverage,
    }


def run_block_a(topic, max_results=50, year_from=None, debug=False,
                out_dir=".", extraction_table=None, human_decision=None,
                use_coze=False, pause_at=None,
                inclusion_hints=None, auto_fetch=True, auto_fetch_dir=None,
                max_attempts=12, pdf_email=None,
                override_query=None, override_screened=None, on_line=None,
                on_a4_event=None, start_stage=None, cached_envelope=None,
                workers=4, pdf_cache_map=None):
    """本地优先 Block A 驱动器。返回与 run_pipeline 同构的 dict。

    - use_coze=False（默认）：A1/A3 走本地启发式，A2 走本地 ct-literature，A4 本地强执闸。
    - human_decision：A4 红线闸人工放行凭据 {"stage_id": A4, "action": "approved"}
      （兼容单 dict 或 list 累积凭据）。
      未提供且 A4 闸触发 → done=False / await_human=True / gate="extraction_review"。
    - pause_at：P3 软停靠集合（fullflow HITL）。算完某阶段若 sid ∈ pause_at 且未持
      对应 approved 凭据 → 提前软停（done=False / await_human=True / gate=None /
      pause=True）。默认 None = 现状行为（仅 A4 红线闸停）。
    - on_line：可选回调 f(line)，实时接收 A2 检索（ct-literature 子进程）的进度输出，
      供工作台底部信息栏展示；None = 现状行为（不转发）。
    """
    env = build_block_a_env(topic, max_results, year_from)
    pid = env["pipeline_id"]
    stages = []
    tool_card_outputs = []

    # ---- 续跑优化：start_stage="A4" 且缓存信封含 A1/A2/A3 → 跳过整块重算，
    # 直接复用已算好的早期阶段，仅跑 A4。典型场景：A3 已批准（非 revise），
    # 避免重复 A2 全库检索 + 全量下载带来的分钟级无谓等待。----
    a4_only = False
    if start_stage == "A4" and cached_envelope:
        _cid = {(s.get("stage") or {}).get("id"): s
                for s in (cached_envelope.get("stages") or [])}
        _s1, _s2, _s3 = _cid.get(A1), _cid.get(A2), _cid.get(A3)
        if _s1 and _s2 and _s3:
            _studies = (_s2.get("stage_result") or {}).get("studies") or []
            _screened = (_s3.get("stage_result") or {}).get("screened") or []
            if _studies or _screened:
                studies, screened = _studies, _screened
                stages = [_s1, _s2, _s3]
                tool_card_outputs = ((_s2.get("tool_cards") or [])
                                     + (_s3.get("tool_cards") or []))
                hints = (inclusion_hints if inclusion_hints is not None
                         else _derive_inclusion_hints(topic))
                a4_only = True

    if not a4_only:
        # A1 — 本地启发式选题 + 真实 ct-registry 查重探针（不阻塞，失败优雅降级）
        try:
            reg_probe = a1_registry_check(topic, max_results=min(max_results, 20))
        except Exception as e:  # noqa: BLE001
            reg_probe = {"status": "error", "total": None, "returned": None,
                         "sample": [], "note": f"registry 探针异常: {type(e).__name__}: {e}"}
        rep1, nha1 = a1_topic_selection(topic, registry_probe=reg_probe)
        s1 = _mk_stage(A1, 0, "await_human", rep1, nha1)
        stages.append(s1)
        _st = _soft_stop(env, pid, stages, tool_card_outputs, s1, A1, pause_at, human_decision)
        if _st:
            return _st

        # A2 — 🟡 软停靠：检索策略/覆盖确认（防沉默漏检：跳库/空结果）
        search_topic = override_query if override_query is not None else topic
        # 检索式翻译前置（关联 ct-base 权威 kw_localize，对照表 + 外接 API 兜底）：
        # 原始中文/混合主题 → 干净英文检索式，再交给 ct-literature 多库检索。
        # 展示与真实检索都用翻译后的检索式，而非原始输入——避免「部分翻译混合串 →
        # 境外库 0 命中 → 只检索了 OpenAlex」式的沉默漏检。
        strategy = _translate_topic_authoritative(search_topic)
        studies, outs2, _card2 = a2_literature_search(strategy["translated_query"], max_results,
                                                      year_from, out_dir, on_line=on_line)
        tool_card_outputs += outs2
        nha2 = _a2_coverage_nha(studies, outs2, _card2, max_results, year_from, strategy=strategy)
        s2 = _mk_stage(A2, 1, "completed",
                       {"studies": studies, "n": len(studies),
                        "coverage": nha2.get("coverage"),
                        "search_strategy": strategy}, nha2, [_card2])
        stages.append(s2)
        _st = _soft_stop(env, pid, stages, tool_card_outputs, s2, A2, pause_at, human_decision)
        if _st:
            return _st

        # A3 — 摘要级纳入门控（inclusion_hints 驱动；None 时由主题自动派生）
        hints = inclusion_hints if inclusion_hints is not None else _derive_inclusion_hints(topic)
        if override_screened is not None:
            # Phase 2 真接缝：直接使用人工修订后的逐条裁决，不重跑启发式
            screened = override_screened
            nha3 = _a3_nha_from_screened(screened)
        else:
            screened, nha3 = a3_screening(studies, inclusion_hints=hints)
        s3 = _mk_stage(A3, 2, "await_human", {"screened": screened, "n": len(screened)}, nha3)
        stages.append(s3)
        _st = _soft_stop(env, pid, stages, tool_card_outputs, s3, A3, pause_at, human_decision)
        if _st:
            return _st

    # A4 — 🔴 红线闸：A3 门控 → 自动落盘 OA PDF → 抽取 2×2 表（草稿）→ 人工核验放行
    rep4, nha4 = a4_data_extraction(
        screened, extraction_table=extraction_table, studies=studies,
        auto_fetch=auto_fetch, auto_fetch_dir=auto_fetch_dir,
        max_attempts=max_attempts, inclusion_hints=hints, pdf_email=pdf_email,
        on_a4_event=on_a4_event, workers=workers, pdf_cache_map=pdf_cache_map,
    )
    s4 = _mk_stage(A4, 3, "await_human", rep4, nha4)
    stages.append(s4)

    base = {
        "pipeline_id": pid, "pipeline": env["pipeline"],
        "stages": stages, "attachments": [], "tool_card_outputs": tool_card_outputs,
    }

    gate = (s4.get("next_human_action") or {}).get("gate")
    if s4.get("_gate_blocked"):
        if _any_approve(human_decision, A4):
            return {**base, "done": True, "await_human": False, "gate": None,
                    "final": s4, "human_decisions": [human_decision]}
        return {**base, "done": False, "await_human": True, "gate": gate, "final": s4}

    return {**base, "done": True, "await_human": False, "gate": None, "final": s4}
