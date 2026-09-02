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
import uuid

import coze_client as cc

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
            })
    return studies


def a2_literature_search(topic, max_results=50, year_from=None, out_dir="."):
    """构建 ct-literature tool_card → execute_tool_cards 本地执行 → 解析文献列表。

    ct-literature 真实行为：数据写入 --out-dir 文件（stdout 仅日志），故优先从
    返回 result 抽取（兼容 mock/未来 coze 形态），为空时回退读 --out-dir 文件。
    返回 (studies, tool_card_outputs, card)。skill 未安装 / 网络失败 → status=error，
    studies=[]，不抛错。
    """
    card = a2_build_tool_card(topic, max_results, year_from, out_dir=out_dir)
    outs = cc.execute_tool_cards([card], out_dir=out_dir)
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
        screened.append({
            "title": s.get("title"),
            "year": s.get("year"),
            "doi": s.get("doi"),
            "include": inc,
            "reason": reason,
            # 透传摘要片段，供人工/下载决策判断"是否真相关"
            "abstract_snippet": s.get("abstract_snippet"),
        })
    n_inc = sum(1 for s in screened if s.get("include"))
    n_exc = len(screened) - n_inc
    n_uncertain = sum(1 for s in screened
                      if not s.get("include") or "待人工" in (s.get("reason") or ""))
    nha = {
        "type": "review",
        "prompt": (f"初筛裁决（软停）：去重后 {len(screened)} 篇，启发式纳入 {n_inc} / 剔除 {n_exc}，"
                   f"其中 {n_uncertain} 篇为低置信（默认纳入或待人工核验相关性）。"
                   f"请逐条确认或翻转 Include/Exclude，重点复核剔除项以防误剔关键研究。"),
        "required": True,
        "gate": "none",
        "summary": {"n_total": len(screened), "n_include": n_inc,
                    "n_exclude": n_exc, "n_uncertain": n_uncertain},
        "decisions": [
            {"title": s.get("title"), "include": bool(s.get("include")),
             "reason": s.get("reason")}
            for s in screened
        ],
    }
    return screened, nha


def _a3_nha_from_screened(screened):
    """从（人工修订后的）screened 列表重建 A3 的 next_human_action 载荷，
    供 override_screened 路径复用（不重跑启发式，避免覆盖人工裁决）。"""
    n_inc = sum(1 for s in screened if s.get("include"))
    n_exc = len(screened) - n_inc
    n_uncertain = sum(1 for s in screened
                      if not s.get("include") or "待人工" in (s.get("reason") or ""))
    return {
        "type": "review",
        "prompt": (f"初筛裁决（软停）：去重后 {len(screened)} 篇，启发式纳入 {n_inc} / 剔除 {n_exc}，"
                   f"其中 {n_uncertain} 篇为低置信（默认纳入或待人工核验相关性）。"
                   f"请逐条确认或翻转 Include/Exclude，重点复核剔除项以防误剔关键研究。"),
        "required": True,
        "gate": "none",
        "summary": {"n_total": len(screened), "n_include": n_inc,
                    "n_exclude": n_exc, "n_uncertain": n_uncertain},
        "decisions": [
            {"title": s.get("title"), "include": bool(s.get("include")),
             "reason": s.get("reason")}
            for s in screened
        ],
    }


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


def a4_stream(studies, screened, pdf_dir=None, max_attempts=12,
               inclusion_hints=None, email=None):
    """生成器：逐篇研究执行 A4 下载+抽取，实时 yield 进度事件（供 Phase 3 实时预览）。

    每次 yield 一个事件 dict，关键字段：
      event: start | skip | failed | deferred | downloading |
             extracted | downloaded_no_extract | done | error
      index / total / title / doi / gate / reason / url / pdf /
      n_rows / n_tworows
    失败不中断（继续处理下一篇）。末次 yield 为
      {"event": "done", "result": {<完整 a4_auto_fetch_and_extract dict>}}
    同步封装 a4_auto_fetch_and_extract 与原行为完全一致（消费至 done 取 result）。
    """
    import os
    import pdf_fetch
    if email is None:
        email = pdf_fetch.DEFAULT_EMAIL
    if pdf_dir is None:
        pdf_dir = os.path.join(os.getcwd(), "pdfs")
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

    extracted_rows = []        # 仅 2×2 结局表（ai/bi/ci/di 齐全）→ 供下游 B1 合并
    review_rows = []            # 全量抽取行（含连续量/描述性，ai=None）→ 供 A4 人工核验
    fetch_log = []
    needs_upload = []
    n_passed = n_dl = n_ext = 0
    dl_index = 0
    studies_list = [s for s in studies if isinstance(s, dict)]
    total = len(studies_list)

    def _emit(ev):
        ev.setdefault("total", total)
        return ev

    for i, s in enumerate(studies_list):
        sc = scr_by_key.get(_key(s)) or {}
        title = s.get("title") or ""
        doi = s.get("doi")
        included = sc.get("include", True)  # screened 为空（未筛）→ 宽松默认纳入
        meta = {"index": i, "total": total, "title": title, "doi": doi}
        yield _emit({"event": "start", **meta})
        if sc and not included:
            r = {"title": title, "doi": doi, "gate": "relevance_skip",
                 "reason": sc.get("reason", "未通过摘要相关性门控")}
            fetch_log.append(r)
            yield _emit({"event": "skip", **meta, **r})
            continue
        if included:
            n_passed += 1

        cand = _pick_candidate(s)
        if not cand:
            r = {"title": title, "doi": doi, "gate": "no_candidate",
                 "reason": "通过相关性门控但无下载入口（无 PMID/DOI/直链），需用户上传 PDF"}
            fetch_log.append(r); needs_upload.append(r)
            yield _emit({"event": "failed", **meta, **r})
            continue
        # 配额按「成功下载数」计（付费墙/网络失败不消耗配额），确保可下载的 OA 论文不被饿死
        if n_dl >= max_attempts:
            r = {"title": title, "doi": doi, "gate": "quota_deferred",
                 "reason": f"已达 max_attempts={max_attempts} 成功下载，其余通过门控者留待下一轮"}
            fetch_log.append(r)
            yield _emit({"event": "deferred", **meta, **r})
            continue

        url = _resolve_pdf_url(cand, email)
        pdf_path = os.path.join(pdf_dir, f"doc{dl_index + 1}.pdf")
        if not url:
            r = {"title": title, "doi": doi, "gate": "pass_no_oa",
                 "reason": "通过门控但无 OA 副本（付费墙），需用户上传 PDF"}
            fetch_log.append(r); needs_upload.append(r)
            yield _emit({"event": "failed", **meta, **r})
            continue
        yield _emit({"event": "downloading", **meta, "url": url})
        if not pdf_fetch.download(url, pdf_path) or not _is_pdf(pdf_path):
            r = {"title": title, "doi": doi, "gate": "pass_download_fail",
                 "reason": "通过门控但下载失败/非真 PDF，需用户上传 PDF"}
            fetch_log.append(r); needs_upload.append(r)
            yield _emit({"event": "failed", **meta, **r})
            continue

        dl_index += 1
        if pdf_extractor is None:
            fetch_log.append({"title": title, "doi": doi, "gate": "pass_downloaded",
                              "pdf": pdf_path, "n_rows": 0, "n_tworows": 0,
                              "n_candidates": 0,
                              "note": "PDF 已落盘，但缺 PDF 抽取库，待人工/环境补抽取"})
            needs_upload.append({"title": title, "doi": doi, "gate": "pass_downloaded",
                                 "pdf": pdf_path, "reason": "PDF 已下但需补抽取"})
            yield _emit({"event": "downloaded_no_extract", **meta, "pdf": pdf_path})
            continue

        yield _emit({"event": "extracting", **meta, "pdf": pdf_path})
        try:
            res = pdf_extractor.extract(pdf_path)
            rows = pdf_extractor.to_a4_rows(res)
        except Exception as e:  # noqa: BLE001
            r = {"title": title, "doi": doi, "gate": "extract_fail",
                 "reason": f"PDF 下载成功但抽取失败：{type(e).__name__}: {e}", "pdf": pdf_path}
            fetch_log.append(r); needs_upload.append(r)
            yield _emit({"event": "failed", **meta, **r})
            continue
        tworows = [r for r in rows if all(r.get(k) is not None for k in ("ai", "bi", "ci", "di"))]
        n_ext += len(tworows)
        n_dl += 1
        fetch_log.append({"title": title, "doi": doi, "gate": "pass_downloaded",
                          "pdf": pdf_path, "n_rows": len(rows),
                          "n_tworows": len(tworows),
                          "n_candidates": len(res["candidates"])})
        extracted_rows.extend(tworows)   # 仅 2×2：供 B1
        review_rows.extend(rows)         # 全量：供人工核验
        yield _emit({"event": "extracted", **meta, "pdf": pdf_path,
                     "n_rows": len(rows), "n_tworows": len(tworows)})

    result = {
        "extracted_rows": extracted_rows,
        "extracted_rows_review": review_rows,
        "fetch_log": fetch_log,
        "n_screened": len(studies_list),
        "n_passed": n_passed,
        "n_downloaded": n_dl,
        "n_extracted": n_ext,
        "needs_user_upload": needs_upload,
        "_dep_note": _dep_note,
    }
    yield _emit({"event": "done", "result": result})


def a4_auto_fetch_and_extract(studies, screened, pdf_dir=None, max_attempts=12,
                              inclusion_hints=None, email=None):
    """A3 摘要门控 → 自动落盘 OA 全文 PDF → pdf_extractor 抽取 2×2 表（同步封装）。

    消费 a4_stream 至 done，返回完整结果 dict（与原实现行为一致）。
    返回 dict：extracted_rows（A4 草案，pdf_extractor.to_a4_rows 形状）/
    fetch_log（每篇门控分类）/ n_screened/n_passed/n_downloaded/n_extracted/
    needs_user_upload（通过门控但付费墙下不到、需人工上传 PDF 的篇目）。

    语义（对齐 HITL「人工下载前核验相关性」+「能下载的先下、其余用户上传」）：
      - A3 未通过（relevance_skip）→ 不下载，待人工核验
      - 通过门控但无下载入口（no_candidate）→ 需用户上传
      - 通过门控 + 无 OA 副本/下载失败（pass_no_oa/pass_download_fail）→ 需用户上传
      - 通过门控 + 真下载成功（pass_downloaded）→ 抽取四格表行并入草案
      - 已达 max_attempts 成功下载数（quota_deferred）→ 其余通过门控者留待下一轮
        （注：max_attempts 统计「成功下载数」，付费墙/网络失败不消耗配额，避免可下 OA 论文被饿死）
    """
    last = None
    for ev in a4_stream(studies, screened, pdf_dir=pdf_dir, max_attempts=max_attempts,
                        inclusion_hints=inclusion_hints, email=email):
        if ev.get("event") == "done":
            last = ev["result"]
    return last


def a4_data_extraction(screened_studies, extraction_table=None, studies=None,
                       auto_fetch=False, auto_fetch_dir=None, max_attempts=12,
                       inclusion_hints=None, pdf_email=None):
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
                email=pdf_email,
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
def _a2_coverage_nha(studies, outs2, card, max_results, year_from):
    """A2 检索策略/覆盖确认 payload（软停）。

    展示各库条数、检索状态、撤稿数、查询式，供人工闸确认。核心防「沉默漏检」：
    无 token 静默跳库 / skill 缺失返回空时，by_source 缺库 + search_status!=ok 即暴露。
    """
    by_source = {}
    for s in studies:
        if isinstance(s, dict):
            src = s.get("source") or "unknown"
            by_source[src] = by_source.get(src, 0) + 1
    status = (outs2[0].get("status") if outs2 and isinstance(outs2[0], dict) else "n/a")
    search_ok = status == "ok"
    retracted = sum(1 for s in studies if isinstance(s, dict) and s.get("is_retracted"))
    params = (card or {}).get("params") or {}
    bits = [f"查询={params.get('topic')!r}"]
    if year_from is not None:
        bits.append(f"year≥{year_from}")
    bits.append(f"上限={max_results}")
    src_str = "、".join(f"{k}={v}" for k, v in sorted(by_source.items())) or "无来源标注"
    prompt = (f"检索策略确认（软停）：{'; '.join(bits)} → 合并 {len(studies)} 篇（{src_str}）。"
              + (f" ⚠️ 检索状态={status}，结果可能不完整/为空，请核查检索配置。" if not search_ok else "")
              + (f" 含撤稿 {retracted} 篇。" if retracted else "")
              + " 请确认覆盖充分，或调整查询/库后重跑。")
    coverage = {
        "total": len(studies),
        "by_source": by_source,
        "search_status": status,
        "retracted": retracted,
        "query": params.get("topic"),
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
                override_query=None, override_screened=None):
    """本地优先 Block A 驱动器。返回与 run_pipeline 同构的 dict。

    - use_coze=False（默认）：A1/A3 走本地启发式，A2 走本地 ct-literature，A4 本地强执闸。
    - human_decision：A4 红线闸人工放行凭据 {"stage_id": A4, "action": "approved"}
      （兼容单 dict 或 list 累积凭据）。
      未提供且 A4 闸触发 → done=False / await_human=True / gate="extraction_review"。
    - pause_at：P3 软停靠集合（fullflow HITL）。算完某阶段若 sid ∈ pause_at 且未持
      对应 approved 凭据 → 提前软停（done=False / await_human=True / gate=None /
      pause=True）。默认 None = 现状行为（仅 A4 红线闸停）。
    """
    env = build_block_a_env(topic, max_results, year_from)
    pid = env["pipeline_id"]
    stages = []
    tool_card_outputs = []

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
    studies, outs2, _card2 = a2_literature_search(search_topic, max_results, year_from, out_dir)
    tool_card_outputs += outs2
    nha2 = _a2_coverage_nha(studies, outs2, _card2, max_results, year_from)
    s2 = _mk_stage(A2, 1, "completed",
                   {"studies": studies, "n": len(studies),
                    "coverage": nha2.get("coverage")}, nha2, [_card2])
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
