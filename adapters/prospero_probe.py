#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prospero_probe.py — PROSPERO 国际系统评价前瞻性注册库 自动检索探针。

零依赖（仅标准库 urllib），用于本地选题评估时自动核查「是否已有同类
已注册/已发表系统评价方案」，作为去重与新颖性判断的第三类真实证据
（另两类为 Europe PMC 的 Cochrane/PubMed SR-MA 命中、ClinicalTrials.gov 注册试验数）。

## 接口变更史（2026-10-25 重新实测 + 2026-10-26 故障记录）

2026-10-26 观察：站点首页（GET /prospero/）可访问（~1s，200），但检索 API
POST /PROSPERO/api/search 响应 ~43s 且返回嵌套错误信封
`{"note":{"status":"error","errormessage":{"errorcode":20000,
"errormessage":"connect ETIMEDOUT 86.188.140.222:9200"}}}` —— 即 PROSPERO 自己的
后端 Elasticsearch 连接超时（服务端基础设施故障），并非本 skill 鉴权 bug 复发。
探针已：① 识别嵌套错误信封（避免把「后端挂了」误报成「0 命中」）；
② 失败前探活官网首页，把「服务端故障」与「本机网络/代理限制」区分开并准确文案。
PROSPERO 恢复后（ES 重连）检索会自行恢复正常，无需再改代码。

2026-10-25 重新实测：

2026-09-24 记录的旧契约：
    GET https://www.crd.york.ac.uk/prospero/api/PROSPERO/search?q=<topic>
    → 恒定返回 {"status":"error","errormessage":"Error code: header value undefined"}

2026-10-25 定位到真正原因（不是「服务端故障」，是**接口改版**）：
  1. PROSPERO 官网已升级为 React SPA（bundle `main.<hash>.js`，env 版本 2.0.40），
     检索改走 **POST /PROSPERO/api/search**（JSON body），旧的 GET 端点仅剩一个
     空壳路由，任何参数都返回上面那句错误。
  2. 所有请求必须带鉴权头（由前端 axios 拦截器统一注入）：
         prospero-auth-token: base64(<毫秒时间戳>)      ← 公开检索只需这一个
         prospero-access-token: <登录 token>            ← 仅登录态接口需要
     缺 `prospero-auth-token` 时，服务端中间件读不到值，就报
     "Error code: header value undefined" —— 这正是旧版看到的「接口坏了」。
  3. 新接口参数（从前端 Nd() 反解）：
         {term, actual, line, page, nperpage, sort, sortorder, filters:[], download}
     `filters` 必须是**数组**（传 {} 会报 actual.trim is not a function 一类类型错）。
  4. 检索式语义：空格分隔 = 短语精确匹配（实测 "omega-3 depression" → 0 命中）；
     多概念必须显式写 `AND`（"omega-3 AND depression" → 236 命中）。

## 实测（2026-10-25）
    statin                      → 1796
    depression                  → 46326
    fish oil                    → 505
    omega-3 AND depression      → 236
    depression AND fish oil     → 46

## 返回结构
    [{"linenumber":1,"term":"fish oil","hits":505,
      "retvals":{"aggs":{...},"hits":{"total":{"value":505,"relation":"eq"},
        "hits":[{"_source":{"accessionnumber":"CRD42…","title":"…"}}]}}}]
"""
import base64
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

# 新契约（2026-10-25 起）；旧 GET 端点已废弃，保留常量仅供排查历史问题
API = "https://www.crd.york.ac.uk/PROSPERO/api/search"
LEGACY_API = "https://www.crd.york.ac.uk/prospero/api/PROSPERO/search"
WEB = "https://www.crd.york.ac.uk/prospero/search"
UA = "Mozilla/5.0 (meta-analysis skill probe)"

# 一次多取的样本池大小：服务端 sort 字段无效（见 _search 文档），
# 需要本地按注册年份倒序截前 N，池子太小会漏掉最新方案。上限受服务端 50 约束。
_SAMPLE_POOL = 50

# 检索式构造时丢弃的词：通用方法学词汇会把检索式拉得过宽，反而命中一堆无关综述
_STOP = {
    "the", "a", "an", "of", "and", "or", "in", "on", "for", "to", "with", "by",
    "vs", "versus", "among", "between", "after", "before",
    "study", "studies", "trial", "trials", "review", "reviews",
    "systematic", "meta", "analysis", "meta-analysis",
    "randomized", "randomised", "controlled", "rct", "patients", "adults",
}


def manual_url(topic):
    """构造 PROSPERO 高级检索一键深链（手动核查用）。"""
    return "https://www.crd.york.ac.uk/prospero/#searchadvanced?search=" + urllib.parse.quote(topic)


def _auth_headers():
    """鉴权头：base64(毫秒时间戳)。公开检索无需登录，但缺这个头服务端会直接报错。"""
    ts = str(int(time.time() * 1000))
    return {
        "Content-Type": "application/json",
        "prospero-auth-token": base64.b64encode(ts.encode("utf-8")).decode("ascii"),
        "User-Agent": UA,
        "Accept": "application/json",
    }


def _reachable(timeout=8):
    """快速探活：PROSPERO 官网首页是否可达（与检索 API 无关，只判断网络/代理层）。

    用于故障降级时给出**诚实**结论：
      · 首页可达但检索接口超时 → 是 PROSPERO 服务端故障（如后端 ES 挂了），不是我们代码回归；
      · 首页也连不上          → 本机网络 / 代理限制，与 PROSPERO 服务端无关。
    2026-10-26：此前直接把「接口超时」笼统报成「上游接口异常」，用户误以为是之前修过的
    鉴权 bug 又复发；加上探活后可明确区分。
    """
    try:
        req = urllib.request.Request(WEB, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _is_error_envelope(node):
    """PROSPERO 新版接口在后端异常时返回嵌套错误信封（非顶层），例如：
        {"note":{"status":"error","errormessage":{"errorcode":20000,
         "errormessage":"connect ETIMEDOUT 86.188.140.222:9200"}}, "hits":0, ...}
    必须把这种「后端挂了」与真正的「0 命中」区分开，否则会误报成「无同类综述」。
    """
    note = (node or {}).get("note")
    if not isinstance(note, dict):
        return None
    if note.get("status") == "error" or "errormessage" in note:
        msg = note.get("errormessage")
        if isinstance(msg, dict):
            msg = msg.get("errormessage") or msg.get("errorcode") or json.dumps(msg, ensure_ascii=False)
        return str(msg or "unknown upstream error")
    return None


def _candidate_terms(topic):
    """把主题拆成若干候选检索式，从精确到宽松（全部显式 AND）。

    空格分隔在 PROSPERO 里是短语精确匹配，长主题原样丢进去几乎必然 0 命中
    （实测 "omega-3 DHA supplementation depression" → 0）。故这里：
      ① 前 4 个实词 AND（最精确）
      ② 前 2 个实词 AND（放宽）
    不再继续降到单词 —— 单词（如 omega-3 单独 1881 命中）会把无关综述全拉进来，
    高估去重命中数比「查不到」更危险。
    """
    raw = re.sub(r"[^\w\s\-]+", " ", (topic or "").lower())
    words = [w for w in raw.split() if w and w not in _STOP and not w.isdigit()]
    # PROSPERO 索引英文。主题里夹带的中文词会让整条 AND 恒 0 命中，进而触发降级、
    # 给出「前 2 词」的虚高命中数（实测中英混排 "DHA omega-3 补充对抑郁症的疗效"
    # 会退化成 "dha AND omega 3" → 512 条，与真实 236 条严重不符）。故直接剔除。
    words = [w for w in words if re.fullmatch(r"[a-z0-9\-]+", w)]
    if not words:
        return []
    cands = []
    if len(words) >= 2:
        cands.append(" AND ".join(words[:4]))
        if len(words) > 2:
            cands.append(" AND ".join(words[:2]))
    else:
        cands.append(words[0])
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _search(term, timeout=20, nperpage=5):
    """调用新版 POST /search，返回 (hit_count, sample, normalized_term)。

    排序（2026-10-25 实测）：服务端**忽略 `sort` 字段** —— `sort=yearfirstpublished`
    / `recordid` / `_score` / `id` 返回完全相同的记录顺序，只有 `sortorder`（asc/desc）
    会改变结果。故这里仍按约定下发 `sort=yearfirstpublished&sortorder=desc`
    （上游将来支持即自动生效），同时多取一批记录在本地按年份倒序截前 N，
    保证「顶部 5 条」真的是最新注册的 5 条。
    """
    want = max(1, int(nperpage))
    pool = min(max(want, _SAMPLE_POOL), 50)      # 一次多取，供本地排序挑选
    body = json.dumps({
        "term": term,
        "actual": term,
        "line": 0,
        "page": 1,
        "nperpage": pool,
        "sort": "yearfirstpublished",
        "sortorder": "desc",
        "filters": [],          # 必须是数组；传 {} 会触发服务端类型错误
        "download": False,
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers=_auth_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode("utf-8", "replace")

    j = json.loads(data)
    node = {}
    if isinstance(j, list) and j:
        node = j[0] if isinstance(j[0], dict) else {}
    elif isinstance(j, dict):
        node = j
    # 服务端错误信封：① 顶层 {"status":"error","errormessage":…} / {"errormessage":…}；
    # ② 新版嵌套在 note 里（后端 ES 超时等）—— 必须把「后端挂了」与「0 命中」区分开。
    if node.get("status") == "error" or ("errormessage" in node and "hits" not in node):
        msg = node.get("errormessage")
        if isinstance(msg, dict):
            msg = msg.get("errormessage") or msg.get("errorcode") or json.dumps(msg, ensure_ascii=False)
        raise RuntimeError("PROSPERO API error: %s" % (msg or "unknown"))
    _env = _is_error_envelope(node)
    if _env:
        raise RuntimeError("PROSPERO API error (nested): %s" % _env)

    hits = node.get("hits")
    if not isinstance(hits, int):
        total = (((node.get("retvals") or {}).get("hits") or {}).get("total") or {})
        hits = total.get("value") if isinstance(total, dict) else None
    sample = []
    for h in (((node.get("retvals") or {}).get("hits") or {}).get("hits") or []):
        src = (h or {}).get("_source") or {}
        rid = src.get("accessionnumber") or src.get("recordid")
        # PROSPERO 的 title 带 <p> 等富文本标签，剥掉再给前端（否则会原样显示标签）
        title = re.sub(r"<[^>]+>", "", str(src.get("title") or "")).strip()
        # 年份给前端列表用（与 Cochrane/PubMed 顶部文献一致：标题 + 年份）
        year = src.get("yearfirstpublished")
        try:
            year = int(str(year)[:4]) if year else None
        except (TypeError, ValueError):
            year = None
        if rid or title:
            sample.append({"id": rid, "title": title, "year": year})
    # 本地按注册年份倒序，取最新 want 条（服务端 sort 字段无效，只能这里补）。
    # 同年内保持服务端原顺序（稳定排序）。
    sample.sort(key=lambda x: (x.get("year") or 0), reverse=True)
    return hits, sample[:want], (node.get("term") or term)


def probe(topic, timeout=20, max_sample=5):
    """自动检索 PROSPERO 是否已注册同类系统评价。

    Returns dict:
        status      : "available" | "unavailable"
        hit_count   : int | None
        sample      : [{"id":..., "title":...}, ...]
        error       : str | None   （上游原因，便于透明展示）
        source      : str | None   （"api" / "web" / None）
        query_used  : str | None   （实际生效的检索式，便于用户核对命中口径）
        manual_url  : 一键手动核查深链
        note        : 说明
    """
    out = {
        "status": "unavailable",
        "hit_count": None,
        "sample": [],
        "error": None,
        "source": None,
        "query_used": None,
        "manual_url": manual_url(topic),
        "note": "",
    }
    if not topic or not topic.strip():
        out["error"] = "empty topic"
        out["note"] = "主题为空白，无法检索 PROSPERO。"
        return out
    # PROSPERO 是英文注册库：纯中文主题不硬查（否则恒 0，会被误读成「无同类注册」）
    if not re.search(r"[A-Za-z]", topic):
        out["error"] = "no english query"
        out["note"] = ("PROSPERO 为英文注册库，当前主题无英文检索词（建议填「英文题名」后重试）；"
                       "可点 manual_url 手动核查。")
        return out

    cands = _candidate_terms(topic)
    if not cands:
        out["error"] = "no english query"
        out["note"] = ("主题中提取不到英文检索词（PROSPERO 为英文注册库）；"
                       "请在「英文题名」填写本主题英文表达后重试，或点 manual_url 手动核查。")
        return out

    # 2026-10-26：故障降级前先探活官网首页（~1s）。用于把「PROSPERO 服务端故障」
    # 与「本机网络/代理限制」区分开，避免笼统报「上游接口异常」让用户误以为旧 bug 复发。
    _host_up = _reachable()

    last_err = None
    zero_seen = False
    for term in cands:
        try:
            cnt, sample, norm = _search(term, timeout=timeout, nperpage=max_sample)
        except Exception as e:  # noqa: BLE001 - 网络/解析失败不阻断 A1
            last_err = e
            continue
        out["query_used"] = norm
        if cnt is None:
            continue
        if cnt > 0:
            out.update(status="available", hit_count=cnt, sample=sample,
                       source="api", error=None,
                       note="PROSPERO 实时检索（%s）→ %d 条已注册方案。" % (norm, cnt))
            return out
        zero_seen = True   # 精确候选 0 命中，继续放宽

    if zero_seen:
        out.update(status="available", hit_count=0, sample=[], source="api", error=None,
                   note=("PROSPERO 实时检索 0 条（已试检索式：%s）；"
                         "若主题较窄，建议用 manual_url 复核。" % " / ".join(cands)))
        return out

    # 3) 网站 SPA 兜底（通常拿不到服务端结果，仅作最后尝试）
    try:
        req = urllib.request.Request(WEB + "?q=" + urllib.parse.quote(topic),
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", "replace")
        ids = re.findall(r"CRD\d{6,}", html)
        if ids:
            out.update(status="available", hit_count=len(ids), source="web",
                       sample=[{"id": i} for i in ids[:max_sample]])
            return out
    except Exception:
        pass

    out["error"] = "api: %s" % (last_err or "no result")
    if _host_up:
        # 站点可达但检索接口无响应 —— 是 PROSPERO 服务端故障（如后端 ES 超时），
        # 非本代码回归；明确告知用户稍后重试或手动核查。
        out["note"] = ("PROSPERO 站点可访问，但检索接口（后端）暂时无响应，疑似服务端故障或维护中；"
                       "请稍后重试，或使用 manual_url 手动核查。")
    else:
        # 站点都连不上 —— 本机网络 / 代理限制，与 PROSPERO 服务端无关。
        out["note"] = ("无法连接 PROSPERO（本机网络 / 代理限制，站点不可达）；"
                       "请检查网络后使用 manual_url 手动核查。")
    return out


if __name__ == "__main__":
    import sys
    _t = sys.argv[1] if len(sys.argv) > 1 else "omega-3 AND depression"
    print(json.dumps(probe(_t), ensure_ascii=False, indent=2))
