"""
adapters/coze_client.py — meta-analysis 技能 → Coze 工作流 主路径客户端

设计（coze 唯一主路径）：
- 这是技能的**唯一计算路径**客户端。R 引擎（metafor/meta/netmeta + dispatcher run_task.R）
  运行在 coze 元分析工作流（src/r_engine/ + src/graphs/nodes/meta_analysis.py）。
- 本客户端把分析请求打包成信封，POST 到 coze 工作流的 /run 端点，解析返回的 JSON 结果
  （status / stats / figures[].svg / warnings / notes）。
- 数值判断由 coze 端 R 计算产出，本客户端只解析结构、绝不读取/改写数值结论。
- 接口契约见 coze 项目的 coze_contract.md（不随技能发布）。
- ⚠️ 回退已取消（2026-08-26）：coze 不可达 / 未授权时本客户端直接抛错，不再兜底本地引擎；
  原本地引擎代码保留在 `adapters/_dev/local_engine.py`（开发调试用，不随发布包分发）。

配置（环境变量）：
  COZE_META_ENDPOINT  工作流 /run 地址，默认 https://ct-meta.coze.site/run（2026-08-26 改造：
                     主工作流由 ct-meta2 互换为 ct-meta，新 token 见 adapters/coze_token.py）
  （回退）若该端点因 token 不一致返回 401/403，自动改用 FALLBACK_ENDPOINT
         （https://ct-meta2.coze.site/run，token 自动切换为 ct-meta2 专属 token）并重试；
         成功后结果附 _coze_endpoint_notice 提示。详见常量 FALLBACK_ENDPOINT。
  COZE_META_TOKEN    可选鉴权令牌（Bearer，全局覆盖所有端点）；留空则按 endpoint 取
                     adapters/coze_token.py 内嵌的公开 blob（随技能发布）
  COZE_META_TIMEOUT   请求超时秒数，默认 600

⚠️ 出站披露（ct-base §5 安全模型，全库强制）：
  本模块会把**分析数据**（研究事件数 / 样本量 / 效应量等，不含个人身份信息）POST 到
  coze 工作流端点（默认 https://ct-meta.coze.site/run）执行云端 R 计算。首次出站前
  须经用户确认（AUTH-BLOCK + 统一文案，见 _auth_gate）；确认后端点写入 config.json
  auto_approve_endpoints 白名单，后续免确认。未授权时直接抛 AuthRequiredError，
  由上层 run_analysis 转为结构化错误返回（不再兜底本地引擎）。payload 发送前经
  sanitize_payload() 脱敏。

依赖：标准库（urllib / json / os / re / sys）+ 同目录 coze_token（凭据解析，仅标准库）。
"""

import copy
import hashlib
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
import uuid

try:  # 作为包导入（adapters.coze_client）
    from .coze_token import get_token_for
except ImportError:  # 平铺模块直接运行（run_analysis 把 adapters 加入 sys.path）
    try:
        from coze_token import get_token_for
    except ImportError:
        get_token_for = None  # 极端情况：仅回退到 COZE_META_TOKEN 环境变量

# 2026-08-26 改造：主分析工作流切到 ct-meta2（新 token，aud=5v9HMQWtTSzxrEeZjI7kJJEzeMPrHXny），
# 同日后续互换：主工作流回切 ct-meta（旧 token，aud=oxwSsfwdtRRfByYIM8Xg3U4RQH5OgEjO），
# ct-meta2 降级为回退（新 token）。二者 JWT 不同，token 按 endpoint 分别解析（见 coze_token.get_token_for）。
DEFAULT_ENDPOINT = "https://ct-meta.coze.site/run"

# 回退端点：主工作流 ct-meta 因 token 不一致 / 服务地址升级而无法访问时，
# 改用 ct-meta2 重试（**token 也切换为 ct-meta2 专属 token**，而非沿用主端点 token）。
# 该端点须预先加入 config.json auto_approve_endpoints 白名单（与 ct-meta / ct-bugreport 同级）。
FALLBACK_ENDPOINT = "https://ct-meta2.coze.site/run"

# 触发回退时向用户呈现的说明（主工作流地址已切换，已自动回退到备用 coze 端点）。
ENDPOINT_FALLBACK_NOTICE = (
    "主分析工作流地址已切换，本次分析已自动回退到备用 coze 端点完成"
)

# 2026-08-29（ct-base §20.9 修订）：**删除版本号比对**——原 `EXPECTED_COZE_ENVELOPE_VERSION`
# 常量与 `_coze_version` / `_contract_version` 的比对逻辑一并移除。版本由 coze 端随发布
# 同步，本地不比对；**任何仅版本号差异（无数据内容/结构变化）一律不提示**，避免无谓打扰。
# 契约检测自此只做一件事：coze 返回的**数据内容/结构**与本地消费接口是否一致
# （见 _assess_contract）。coze 端 `_coze_version` 注入可保留，本地不再消费。

# 并发调用保护（用户 2026-08-28 要求）：多次 coze 出站调用之间**必须间隔 ≥1 秒**，
# 防止触发 coze 端限流（实测曾因密集请求被 429 限流至次日）。
# 实现：模块级锁 + 单调时钟，串行化"间隔决策"并强制最小间隔。间隔秒数可由
# 环境变量 COZE_META_MIN_INTERVAL（浮点秒）覆写，<=0 时关闭保护。
_RATE_LIMIT_LOCK = threading.Lock()
_LAST_CALL_TS = 0.0  # time.monotonic() of the most recently dispatched coze POST


def _assess_contract(parsed: dict) -> tuple:
    """coze 响应「数据内容/结构一致性」契约检测（单一入口，ct-base §20.9 范本）。

    2026-08-28 综合定稿：把 meta-analysis 的结构漂移自适应与 ct-base 的旧机制统一到
    本函数。2026-08-29 修订（ct-base §20.9 同步）：**移除版本漂移检测**——版本号差异
    不再触发任何提醒，只有数据内容/结构与本地接口对不上时才提示。

    唯一的检测信号（自愈优先）：
      结构/数据内容漂移：识别已知字段别名并自适应归一化（quality_gate / checks /
      pooled / figures 形态），保证报告仍能渲染；映射发生时记 drift 说明。
      对无法自适应的结构缺失，仅记录告警、不臆造数据。

    ⚠️ 以下情况**一律不提示**（零噪音原则）：
      - coze 返回 `_coze_version` / `_contract_version` 与本地不同（版本由发布同步，
        本地不比对）；
      - coze 未注入版本标记；
      - 结构一致、无别名映射发生。

    Returns: (parsed, drift_notes, needs_upgrade)
      drift_notes 非空 => 已自适应或检测到不一致，交给 rendering.py 在 HTML 横幅提示升级；
      needs_upgrade 仅为机器可读标记（写回 parsed），本函数**不产生任何用户可见提示**
      （用户可见提示统一只在渲染层的 HTML 横幅，避免 stderr / notes 重复提示）。
    """
    if not isinstance(parsed, dict):
        return parsed, [], False
    notes = []
    p = parsed

    # ---- 结构漂移：已知字段别名 → 本地期望字段（仅当期望字段缺失、且别名存在时映射）----
    # 1) 质量评估块
    if not isinstance(p.get("quality_gate"), dict):
        for a in ("quality_gate_v2", "qgate", "quality", "qagate"):
            if isinstance(p.get(a), dict):
                p["quality_gate"] = p[a]
                if a in p:
                    del p[a]
                notes.append(f"coze 响应字段已变更：质量评估由 `{a}` 改为 `quality_gate`，已自动适配")
                break
    if isinstance(p.get("quality_gate"), dict):
        qg = p["quality_gate"]
        if "checks" not in qg:
            for ca in ("items", "list", "entries", "checks_list"):
                if isinstance(qg.get(ca), list):
                    qg["checks"] = qg[ca]
                    if ca in qg:
                        del qg[ca]
                    notes.append(f"coze 响应字段已变更：质量评估条目由 `{ca}` 改为 `checks`，已自动适配")
                    break

    # 2) 合并效应量
    if isinstance(p.get("stats"), dict):
        st = p["stats"]
        if not isinstance(st.get("pooled"), dict):
            for pa in ("estimate", "effect", "pooled_estimate"):
                if isinstance(st.get(pa), dict):
                    st["pooled"] = st[pa]
                    notes.append(f"coze 响应字段已变更：合并效应量由 `{pa}` 改为 `pooled`，已自动适配")
                    break

    # 3) figures 结构兜底（dict → list；图体别名 image/svg_data/base64 → svg）
    figs = p.get("figures")
    if isinstance(figs, dict):
        p["figures"] = [
            {"type": k, "svg": v} for k, v in figs.items() if isinstance(v, str)
        ]
        notes.append("coze 响应结构已变更：figures 由 dict 改为 list，已自动适配")
    elif isinstance(figs, list):
        for i, f in enumerate(figs):
            if isinstance(f, dict) and "svg" not in f and "url" not in f:
                for fa in ("image", "svg_data", "base64"):
                    if isinstance(f.get(fa), str):
                        f["svg"] = f[fa]
                        notes.append(f"coze 响应字段已变更：figures[{i}] 图体由 `{fa}` 改为 `svg`，已自动适配")
                        break

    # 原「4) 版本漂移」已于 2026-08-29 移除（ct-base §20.9 修订）：
    # coze 返回 `_coze_version` / `_contract_version` 与本地不同**不再触发提醒**——
    # 版本由 coze 端随发布同步，本地只检测数据内容/结构一致性。
    # 相关常量 EXPECTED_COZE_ENVELOPE_VERSION 已一并删除，避免死代码。

    # 去重（保持顺序）
    seen, uniq = set(), []
    for n in notes:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return p, uniq, bool(uniq)


def _endpoint() -> str:
    return os.environ.get("COZE_META_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")


def _acquire_rate_limit() -> None:
    """并发调用保护：确保相邻两次 coze POST 之间**至少间隔 1 秒**（可由
    COZE_META_MIN_INTERVAL 覆写），避免触发 coze 端限流（429）。

    用模块级锁串行化"间隔决策"，仅在决策期间持锁（含必要的 sleep 占位），
    网络请求本身在锁释放后发出——既保证 ≥1s 间距，又不把网络延迟锁在临界区内。

    作用域：同一 Python 进程内的多线程并发（本技能典型调用场景）。跨进程并发
    需另加文件锁，当前未实现（如需多进程同时调用 coze，再扩展）。
    """
    try:
        interval = float(os.environ.get("COZE_META_MIN_INTERVAL", "1.0"))
    except (TypeError, ValueError):
        interval = 1.0
    if interval <= 0:
        return
    global _LAST_CALL_TS
    with _RATE_LIMIT_LOCK:
        now = time.monotonic()
        wait = interval - (now - _LAST_CALL_TS)
        if wait > 0:
            time.sleep(wait)
            now = time.monotonic()
        _LAST_CALL_TS = now


# --------------------------------------------------------------------------
# 归因标识（query_origin）— 2026-08-29 修复
# --------------------------------------------------------------------------
# 原设计把 query_origin 的计算放在 run_analysis.py，再作为参数传进 run_meta；
# 直接调用本模块的路径（__main__ 自测 / coze_integration_test / deploy_retest
# --live / 外部脚本）都不传 → coze 端 `state.query_origin or ""` 兜底成空串 →
# 飞书归因列空白，且**绕过了按 query_origin 计的限流**。现下沉到本模块：
# 任何调用路径都自动带上归因，无法为空。
def _default_query_origin(debug: bool = False) -> str:
    """主机名 SHA-256 作为调用发起来源标识（"sha256:" + 64hex）。

    debug=True 时前缀 "debug:"——调试/冒烟流量在飞书归因列可直接筛出，
    不与真实用户流量混计（2026-08-29：排查发现自测调用污染了生产日志表）。
    """
    try:
        host = socket.gethostname() or "unknown"
    except Exception:  # noqa: BLE001
        host = "unknown"
    digest = hashlib.sha256(host.encode("utf-8")).hexdigest()
    return ("debug:sha256:" if debug else "sha256:") + digest


# --------------------------------------------------------------------------
# 请求指纹 + 短窗幂等去重 — 2026-08-29 新增
# --------------------------------------------------------------------------
# 背景：一次调试中同一份数据被连续调用两次（仅 figure.plots 不同），coze 端无
# 去重、客户端只有 ≥1s 节流 → 算力翻倍、飞书记录翻倍、限流计数失真。现对
# (task, data, params, figure) 做指纹，窗口内同指纹直接复用上次结果（不发请求）。
# 作用域：进程内（与 _acquire_rate_limit 同级）；跨进程需文件锁，暂未实现。
_DEDUP_LOCK = threading.Lock()
_DEDUP_CACHE: dict = {}  # fingerprint -> (monotonic_ts, result_dict)
_DEDUP_MAX_ENTRIES = 32


def _dedup_window() -> float:
    """去重窗口秒数（COZE_META_DEDUP_WINDOW 覆写，默认 60；<=0 关闭去重）。"""
    try:
        return float(os.environ.get("COZE_META_DEDUP_WINDOW", "60.0"))
    except (TypeError, ValueError):
        return 60.0


def _dedup_fingerprint(payload: dict) -> str:
    """对请求体（task/data/params/figure）做稳定指纹。

    只取四个业务字段，忽略 request_id / _debug / query_origin 等观测字段——
    否则同一分析换个 request_id 就绕过去重。
    """
    core = {k: payload.get(k) for k in ("task", "data", "params", "figure")}
    blob = json.dumps(core, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _dedup_lookup(fp: str) -> dict | None:
    """命中窗口内同指纹的历史结果则返回其深拷贝（不发出网络请求），否则 None。"""
    if _dedup_window() <= 0:
        return None
    with _DEDUP_LOCK:
        hit = _DEDUP_CACHE.get(fp)
        if not hit:
            return None
        ts, cached = hit
        if (time.monotonic() - ts) > _dedup_window():
            _DEDUP_CACHE.pop(fp, None)
            return None
        return copy.deepcopy(cached)


def _dedup_store(fp: str, result: dict) -> None:
    """仅缓存成功结果（status=ok/warn）。

    失败不缓存——否则一次偶发失败会毒化整个窗口，后续真实重试全被短路。
    """
    if _dedup_window() <= 0:
        return
    if not isinstance(result, dict) or result.get("status") not in ("ok", "warn"):
        return
    with _DEDUP_LOCK:
        if len(_DEDUP_CACHE) >= _DEDUP_MAX_ENTRIES and fp not in _DEDUP_CACHE:
            oldest = min(_DEDUP_CACHE.items(), key=lambda kv: kv[1][0])[0]
            _DEDUP_CACHE.pop(oldest, None)
        _DEDUP_CACHE[fp] = (time.monotonic(), copy.deepcopy(result))


def _resolve_token(endpoint: str = "") -> str:
    """按端点解析 coze 鉴权 token，优先级：env COZE_META_TOKEN(全局) >
    endpoint 专属内嵌 blob > 历史默认 blob。

    2026-08-26 改造：主工作流 ct-meta 与回退端点 ct-meta2 使用不同的工作流 JWT，
    故 token 按 endpoint 分别解析（coze_token.get_token_for）。
    """
    if get_token_for is not None:
        return get_token_for(endpoint) or ""
    return os.environ.get("COZE_META_TOKEN", "")


def _headers(endpoint: str = "") -> dict:
    h = {"Content-Type": "application/json"}
    tok = _resolve_token(endpoint)
    if tok:
        h["Authorization"] = "Bearer " + tok
    return h


def _timeout() -> int:
    try:
        return int(os.environ.get("COZE_META_TIMEOUT", "600"))
    except ValueError:
        return 600


def _is_token_error(code: int, body: str) -> bool:
    """判定 coze 返回是否为 token 不一致 / 鉴权失败（401/403 + token/auth/invalid 关键字）。

    仅在此类错误时触发端点回退（FALLBACK_ENDPOINT），避免掩盖其他 4xx/5xx。
    """
    if code not in (400, 401, 403):
        return False
    t = (body or "").lower()
    return any(k in t for k in ("token", "unauthor", "forbidden", "invalid", "auth"))


def _post_run(run_url: str, body: bytes, headers: dict, timeout: int):
    """POST 到 coze /run 端点，返回 (raw_text, elapsed_seconds)。

    HTTPError → 抛 _CozeHttpError（带 code/body，供 token 错误判定）；
    网络层 URLError → 抛 RuntimeError（不可达，不触发回退）。
    """
    req = urllib.request.Request(run_url, data=body, headers=headers, method="POST")
    _t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise _CozeHttpError(
            e.code,
            e.read().decode("utf-8", "ignore")[:1000],
            f"coze 工作流返回 HTTP {e.code}",
        )
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"无法连接 coze 工作流（{run_url}）：{e.reason}。"
            f"默认端点应为 https://ct-meta.coze.site/run（如被旧配置覆盖，"
            f"请检查 COZE_META_ENDPOINT 是否误指向 localhost）。"
        )
    return raw, time.time() - _t0


# ---- ct-base §5 出站授权门控（2026-08-19 全库统一范式） ----

class AuthRequiredError(RuntimeError):
    """coze 出站未授权（首次出站须用户确认，ct-base §5 授权门控）。

    由 run_analysis.py 捕获 → 转为结构化错误返回（不再兜底本地引擎）。
    """


class _CozeHttpError(RuntimeError):
    """coze 工作流返回 HTTP 错误，携带 code/body 供调用方判断是否为 token 鉴权失败。"""

    def __init__(self, code: int, body: str, message: str):
        super().__init__(message)
        self.code = code
        self.body = body


def _config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _load_config() -> dict:
    try:
        with open(_config_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict) -> None:
    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def approve_endpoint(endpoint: str) -> None:
    """用户确认后，将端点写入 auto_approve_endpoints 白名单（ct-base §5）。

    ⚠️ 仅可在**用户明确同意**后调用（agent 引导但绝不代决）；已预置端点
    （如技能作者默认放行的 coze 端点）不受影响。返回 True 表示本次调用免确认。
    """
    cfg = _load_config()
    approved = cfg.setdefault("auto_approve_endpoints", [])
    if endpoint not in approved:
        approved.append(endpoint)
        _save_config(cfg)


def _auth_gate(endpoint: str) -> bool:
    """出站授权门控：端点已在白名单 → True；否则 stderr 输出 AUTH-BLOCK +
    统一确认文案（由 agent 呈现给用户），返回 False（调用方转结构化错误，不阻断流程）。

    §5 统一文案（中文，按技能名/端点/发送内容适配；禁止出现内部术语）。
    """
    approved = _load_config().get("auto_approve_endpoints", [])
    if endpoint in approved:
        return True
    sys.stderr.write(
        "\nAUTH-BLOCK: outbound not approved yet\n"
        "⚠️ [meta-analysis] 需要把您的分析数据发送到外部服务器进行计算：\n"
        f"目标服务器：{endpoint}\n"
        "发送内容：您的分析数据（研究事件数 / 样本量 / 效应量等，不含任何个人身份信息）\n"
        "⚠️ 重要提示：本技能所有统计计算（meta / metafor / netmeta 等 R 引擎）"
        "均依赖云端 coze 执行。如不同意发送，将无法完成分析。\n"
        "是否允许本次发送？确认后本会话内不再重复询问。\n"
    )
    return False


def sanitize_payload(payload: dict) -> dict:
    """出站 payload 发送前脱敏（ct-base §5）：剥离 PII（身份证 / 手机号 / 邮箱）。

    meta-analysis 数据通常是研究级汇总（事件数/样本量），但兜底清理任何可能混入的
    个人标识字段值（递归遍历字符串值）。绝不回显 token / payload 明文。
    """
    id_card = re.compile(r"\b\d{17}[\dXx]\b")
    phone = re.compile(r"\b1[3-9]\d{9}\b")
    email = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")

    def _clean(v):
        if isinstance(v, str):
            v = id_card.sub("[ID-CARD]", v)
            v = phone.sub("[PHONE]", v)
            v = email.sub("[EMAIL]", v)
            return v
        if isinstance(v, dict):
            return {k: _clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_clean(x) for x in v]
        return v

    return _clean(payload)


def _fill_external_svgs(parsed: dict, timeout: int = 30) -> dict:
    """coze 返回体重组**兜底**入口（2026-08-28 manifest 方案重构，2026-08-29 起降级为 fallback）。

    主路径已迁移到 §20.8 模式 B：本地 `run_meta` 优先经 `_coze_full` 下载完整 JSON；
    仅当响应**无** `_coze_full`（老 coze 响应）时才调用本函数。

    若响应含 `_coze_manifest`（老 manifest 方案 coze 响应）：GET manifest → 逐 path 写回原值 →
    重组为原始 JSON（含 svg/r 代码/统计值）。

    **旧契约**：无 `_coze_manifest` 时走 figures[].url→svg、repro.url→r、`_coze_externalized` 逐块回填。

    - 超时 / 网络失败 → 保留引用并标记 _*_fetch_failed，绝不抛错中断分析。
    """
    if not isinstance(parsed, dict):
        return parsed
    # 新契约：manifest 单文件重组（优先级最高）
    manifest = parsed.get("_coze_manifest")
    if isinstance(manifest, dict) and manifest.get("storage") == "s3" and manifest.get("url"):
        return _reassemble_from_manifest(parsed, manifest, timeout=timeout)
    # 旧契约（向后兼容）：figures[].url / repro.url / _coze_externalized 逐项回填
    return _fill_external_svgs_legacy(parsed, timeout=timeout)


def _fetch_full_json(parsed, timeout=30):
    """优先经 `_coze_full` 下载完整 JSON（2026-08-29 §20.8 模式 B 落点）。

    coze 端把完整信封（含 figures/repro）整体写为单个 S3 文件并内联 `_coze_full` 链接；
    本地收到内联删减版后，**优先**下载完整 JSON 作分析源（零删减、含 figures/repro）。
    下载失败 / 无 `_coze_full` 链接 → 返回 None（调用方降级到 `_fill_external_svgs` 旧契约：
    manifest 重组 + 旧 figures[].url / repro.url 回填），保持对老 coze 响应向后兼容。
    """
    if not isinstance(parsed, dict):
        return None
    full = parsed.get("_coze_full")
    if not (isinstance(full, dict) and full.get("storage") == "s3" and full.get("url")):
        return None
    try:
        with urllib.request.urlopen(full["url"], timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        parsed["_full_fetch_failed"] = True
        return None
    if not isinstance(data, dict):
        parsed["_full_fetch_failed"] = True
        return None
    # 完整数据本身不带 _coze_full（那是内联信封的链接），移除以防下游误用。
    data.pop("_coze_full", None)
    return data


def _reassemble_from_manifest(parsed: dict, manifest: dict, timeout: int = 30) -> dict:
    """按 manifest 重组原始 JSON（2026-08-28，用户提案）：
    coze 端把超 4000 的最大块（figures/repro/stats 子块）统一移进单个 S3 manifest 文件，
    manifest 为 [{path, value}, ...]，主返回体挂 `_coze_manifest = {storage:"s3", url}`。
    此处 GET manifest → 按 path 写回 value → 重组为原始 JSON。

    - path 支持 `figures[i]`（列表下标）与 `stats.xxx` 点路径。
    - 写回时若该位置当前仍是 {storage:"s3",type:"block"} 引用（未被本地改动）才覆盖。
    - 超时 / 网络失败 → 保留 manifest 引用并在主返回体标 _manifest_failed，绝不抛错中断。
    - 重组完成后移除 `_coze_manifest`（下游见到的即原始结构）。
    """
    url = manifest.get("url")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            manifest_list = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        parsed["_manifest_failed"] = True
        return parsed
    if not isinstance(manifest_list, list):
        parsed["_manifest_failed"] = True
        return parsed

    def _resolve_target(root, path):
        """返回 (容器, key) 或 (list, idx) 以便写回；找不到返回 None。"""
        if path.startswith("figures["):
            # figures[i]
            m = path[8:-1]
            if not m.isdigit():
                return None
            idx = int(m)
            figs = root.get("figures")
            if not isinstance(figs, list) or idx >= len(figs):
                return None
            return figs, idx
        # stats.a.b 点路径
        parts = path.split(".")
        node = root
        for p in parts[:-1]:
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        if not isinstance(node, dict) or parts[-1] not in node:
            return None
        return node, parts[-1]

    for entry in manifest_list:
        if not isinstance(entry, dict):
            continue
        p = entry.get("path")
        if not p:
            continue
        target = _resolve_target(parsed, p)
        if target is None:
            continue
        container, key = target
        cur = container[key]
        # 仅当仍是外置引用时才写回；已被本地改动为实际内容则跳过
        if isinstance(container, dict):
            is_ref = (isinstance(cur, dict) and cur.get("storage") == "s3"
                      and cur.get("type") == "block")
            if is_ref:
                container[key] = entry.get("value")
        else:  # list
            if isinstance(cur, dict) and cur.get("storage") == "s3" and cur.get("type") == "block":
                container[key] = entry.get("value")
    # 重组完成，移除 manifest 引用（下游见原始结构）
    parsed.pop("_coze_manifest", None)
    return parsed


def _fill_external_svgs_legacy(parsed: dict, timeout: int = 30) -> dict:
    """旧契约（2026-08-28 起仅向后兼容）：figures[].url→svg、repro.url→r、_coze_externalized 逐块回填。"""
    if not isinstance(parsed, dict):
        return parsed
    figs = parsed.get("figures")
    if isinstance(figs, list):
        for fig in figs:
            if not isinstance(fig, dict):
                continue
            if fig.get("url") and not fig.get("svg"):
                try:
                    with urllib.request.urlopen(fig["url"], timeout=timeout) as r:
                        fig["svg"] = r.read().decode("utf-8")
                except Exception:  # noqa: BLE001
                    fig["_svg_fetch_failed"] = True
    repro = parsed.get("repro")
    if isinstance(repro, dict) and repro.get("url") and not repro.get("r"):
        try:
            with urllib.request.urlopen(repro["url"], timeout=timeout) as r:
                repro["r"] = r.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            repro["_repro_fetch_failed"] = True
    # 旧契约的 stats 逐块回填
    refs = parsed.get("_coze_externalized")
    if isinstance(refs, list):
        _inflate_externalized(parsed, refs, timeout=timeout)
    return parsed


def _inflate_externalized(parsed: dict, refs: list | None = None, timeout: int = 30) -> dict:
    """（旧契约，2026-08-28 起仅向后兼容）回填 _coze_externalized 逐块外置的引用。"""
    if not isinstance(parsed, dict):
        return parsed
    if refs is None:
        refs = parsed.get("_coze_externalized")
    if not isinstance(refs, list):
        return parsed

    def _get_ref_node(node, parts):
        cur = node
        for p in parts[:-1]:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        if not isinstance(cur, dict) or parts[-1] not in cur:
            return None
        return cur, parts[-1]

    for ref in refs:
        path = ref.get("path")
        url = ref.get("url")
        if not path or not url:
            continue
        loc = _get_ref_node(parsed, path.split("."))
        if loc is None:
            continue
        node, key = loc
        cur_val = node.get(key)
        if not (isinstance(cur_val, dict) and cur_val.get("storage") == "s3"
                and cur_val.get("type") == "block"):
            continue
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                raw = r.read().decode("utf-8")
            val = json.loads(raw)
            node[key] = val
        except Exception:  # noqa: BLE001
            if not isinstance(cur_val, dict):
                cur_val = {"storage": "s3", "type": "block", "url": url}
            cur_val["_inflate_failed"] = True
            node[key] = cur_val
    return parsed


def run_meta(task: str, data: dict, params: dict | None = None,
             figure: dict | None = None, query_origin: str | None = None,
             debug: bool = False) -> dict:
    """调用 coze 元分析工作流，返回解析后的结果 dict。

    Args:
        task:   任务类型（pairwise_meta / nma / metareg / ... 见 coze_contract.md）
        data:   分析数据（{"rows": [...], "colmap": {...}}）
        params: 分析参数（sm / model / subgroup / reference_group ...）
        figure: 出图控制（{"plots": [...], "width": 7, "height": 5}）
        query_origin: 调用发起来源标识（sha256:<64hex>，透传写入飞书 query_origin 列，
                      取值方式与 ct-registry 参考项目一致，2026-08-19）。
                      **留空时由本函数自动生成**（主机名 SHA-256，2026-08-29 修复：
                      空归因会让调用绕过按 query_origin 计的限流，且飞书日志无法溯源）。
        debug:   调试/冒烟标记（默认 False）。True 时 payload 附 `_debug: true`，
                  归因标识加 "debug:" 前缀，便于在飞书日志里把非生产流量筛出来。

    Returns:
        dict: {status, stats, figures:[{type,format,svg}], warnings, notes, task}
        另附观测字段：
          `_request_id`                本次请求 UUID（每次调用都不同）
          `_dedup_hit` / `_dedup_original_request_id`
                                       命中短窗去重时出现（结果复用自哪次请求）

    Raises:
        RuntimeError: coze 端点不可用或返回非 2xx。
    """
    # 2026-08-20 设计收紧（用户确认）：coze 端**永远只返回 SVG**——
    # 无论调用方是否请求 png，都强制 format="svg"；PNG 需求一律由本地呈现层
    # rendering.svg_to_png() / run_analysis.render_figures(mode="png_file") 转换
    # （coze 端零 png 路径，避免 png_base64 占用带宽/上下文）。
    fig = dict(figure or {})
    fig["format"] = "svg"
    # 兼容性兜底（2026-08-26 契约实测）：历史 spec 可能用 `byvar` 字段名，
    # coze 端点只认 `subgroup`（`byvar`/`group`/`by` 静默失效）；此处归一化，避免静默失效。
    if params and "byvar" in params:
        params = {**params, "subgroup": params.pop("byvar")}
    # 归因标识（2026-08-29）：未显式传入时自动生成 —— 任何调用路径都不再产生空归因。
    origin = query_origin or _default_query_origin(debug=debug)
    # 请求追踪 ID（2026-08-29）：飞书两条相邻记录无法区分"两次独立调用"还是
    # "一次调用的重放"，现每次调用带 UUID，随结果一并返回，便于事后对账。
    request_id = str(uuid.uuid4())
    payload = {
        "task": task,
        "data": data or {},
        "params": params or {},
        "figure": fig,
        "query_origin": origin,
        "request_id": request_id,
    }
    if debug:
        payload["_debug"] = True
    # 短窗幂等去重（2026-08-29）：窗口内完全相同的请求直接复用上次结果，
    # 不再打 coze —— 避免误双击 / 调试连跑把算力与飞书日志翻倍。
    fp = _dedup_fingerprint(payload)
    cached = _dedup_lookup(fp)
    if cached is not None:
        original_rid = cached.get("_request_id", "")
        cached["_dedup_hit"] = True
        cached["_dedup_original_request_id"] = original_rid
        cached["_request_id"] = request_id
        return cached
    # 2026-08-19 修复：DEFAULT_ENDPOINT/COZE_META_ENDPOINT 可能已带 /run 后缀
    # （旧逻辑无条件再拼 /run → 请求打到 /run/run → 404 Not Found）
    ep = _endpoint()
    run_url = ep if ep.endswith("/run") else ep + "/run"
    # ct-base §5 授权门控：首次出站须用户确认（未授权 → AuthRequiredError → 结构化错误）
    if not _auth_gate(run_url):
        raise AuthRequiredError(
            f"coze 出站未授权（端点 {run_url} 不在 auto_approve_endpoints 白名单）。"
            f"如同意发送请让用户确认后调用 approve_endpoint('{run_url}') 再重试。"
        )
    # ct-base §5：出站 payload 发送前脱敏（剥离 PII）
    payload = sanitize_payload(payload)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = _headers(ep)
    used_fallback = False

    # 主端点请求；token 不一致（401/403 + token 关键字）则回退 FALLBACK_ENDPOINT
    # （**回退端点使用自身专属 token**，见 _headers(fb_url)）
    try:
        _acquire_rate_limit()  # 并发保护：相邻 coze 调用至少间隔 1 秒
        raw, _elapsed = _post_run(run_url, body, headers, _timeout())
    except _CozeHttpError as e:
        if _is_token_error(e.code, e.body) and ep != FALLBACK_ENDPOINT:
            fb_url = FALLBACK_ENDPOINT if FALLBACK_ENDPOINT.endswith("/run") else FALLBACK_ENDPOINT + "/run"
            fb_headers = _headers(fb_url)
            if not _auth_gate(fb_url):
                raise AuthRequiredError(
                    f"coze 回退端点未授权（{fb_url} 不在 auto_approve_endpoints 白名单）。"
                )
            try:
                _acquire_rate_limit()  # 并发保护同样覆盖回退端点
                raw, _elapsed = _post_run(fb_url, body, fb_headers, _timeout())
                used_fallback = True
                run_url = fb_url
            except _CozeHttpError as e2:
                # 回退仍 token 失败：附升级提示后抛出，提示用户更新技能
                raise RuntimeError(
                    f"coze 主端点与回退端点均因 token 不一致失败（{e2.code}）。"
                    f"{ENDPOINT_FALLBACK_NOTICE}"
                )
        else:
            raise
    except RuntimeError:
        raise

    outer = json.loads(raw)
    # /run 返回 GlobalState（GraphOutput.result = R 引擎 JSON 字符串）
    result_str = outer.get("result") if isinstance(outer, dict) else None
    if not result_str:
        # 兼容直接返回结构化结果的情况
        fallback = outer if isinstance(outer, dict) else {"status": "error", "notes": "空响应"}
        fallback.setdefault("_request_id", request_id)
        return fallback
    try:
        parsed = json.loads(result_str)
    except json.JSONDecodeError:
        return {"status": "error",
                "notes": f"coze 返回非 JSON 结果：{result_str[:500]}",
                "_request_id": request_id}
    # 2026-08-29 §20.8 模式 B：优先经 `_coze_full` 下载完整 JSON（含 figures/repro，零删减）
    # 作分析源；下载失败 / 无链接降级旧契约（_fill_external_svgs：manifest 重组 +
    # 旧 figures[].url / repro.url 回填），保持对老 coze 响应向后兼容。
    full = _fetch_full_json(parsed, timeout=30)
    if full is not None:
        parsed = full
    else:
        _fill_external_svgs(parsed)
    # 契约漂移检测 + 自适应（coze 响应结构与本地技能"对不上"时，自动归一化；
    # 用户可见提示统一只在 rendering.py 的 HTML 横幅，此处不写 stderr / 不污染 notes）
    if isinstance(parsed, dict):
        parsed, _drift_notes, _needs_upgrade = _assess_contract(parsed)
        if _drift_notes:
            parsed["_contract_drift"] = _drift_notes
            parsed["_needs_upgrade"] = _needs_upgrade
    # 透出飞书写入状态（coze 端 GraphOutput 顶层字段，2026-08-19）
    if isinstance(parsed, dict):
        for _k in ("feishu_write_success", "feishu_write_time"):
            if _k in outer:
                parsed[_k] = outer[_k]
        # 仅诊断参考：coze 请求→响应往返秒数（R 计算 + 网络；非界面渲染时间）
        parsed["coze_elapsed_seconds"] = round(_elapsed, 1)
        # 端点回退提示：原地址因 token 不一致触发回退，提示用户技能已升级、地址有变。
        # 用户可见提示统一只在 rendering.py 的 HTML 横幅（由 _coze_endpoint_notice 驱动），
        # 此处不写 stderr / 不污染 notes。
        if used_fallback:
            parsed["_coze_endpoint_notice"] = ENDPOINT_FALLBACK_NOTICE
        parsed["_request_id"] = request_id
    # 仅成功结果入去重缓存（失败不缓存，避免偶发失败毒化窗口内后续真实重试）
    _dedup_store(fp, parsed)
    return parsed


def health() -> bool:
    """探测 coze 端点**可达性**（非功能健康）。

    2026-08-19 修正：coze 自定义域名通常仅暴露 /run，/health 路由未必存在——旧实现
    探测 /health 在服务正常时也可能误报 False。现改为探测 /run：
    - 2xx / 4xx / 5xx（含 401 缺 token、405 方法不允许）均证明服务已响应 → 可达 True；
    - 仅网络层错误 / 超时 / DNS 失败 → False（真正不可达）。
    """
    ep = _endpoint().rsplit("/run", 1)[0] or DEFAULT_ENDPOINT.rsplit("/run", 1)[0]
    # 2026-08-29：探测包带 `probe` 标记 + 调试归因，不再发空信封 `{}`。
    #   - 新 coze 端（已部署）：识别 probe → 跳过 R 计算与飞书写入，日志表零污染；
    #   - 旧 coze 端（未部署）：不认识该字段（pydantic extra='ignore'）→ 仍会写一条，
    #     但至少带 `debug:` 归因前缀可筛出，不再是空白归因。
    # 2026-08-29（补）：带上 Bearer token，使 probe 能越过网关鉴权真正进 langgraph。
    #   不带 token 时请求被网关在鉴权层挡回（401），根本进不了图，probe 短路是"睡着"的；
    #   带 token 后 coze 端会在 meta_analysis 节点直接短路、不调 R 引擎、不写飞书，
    #   既验证可达性，又零算力零日志污染。token 解析失败时退化为无 token 探测（401 仍算可达）。
    try:
        probe_body = json.dumps(
            {"probe": True, "query_origin": _default_query_origin(debug=True)},
            ensure_ascii=False,
        ).encode("utf-8")
    except Exception:  # noqa: BLE001 — 极端情况下退化为最简探测包，探测本身不应失败
        probe_body = b'{"probe": true}'
    headers = {"Content-Type": "application/json"}
    try:
        tok = _resolve_token(ep)
        if tok:
            headers["Authorization"] = "Bearer " + tok
    except Exception:  # noqa: BLE001 — token 解析失败不应阻断探测
        pass
    try:
        req = urllib.request.Request(
            ep + "/run", method="POST", data=probe_body, headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return True  # 2xx
    except urllib.error.HTTPError:
        return True  # 4xx/5xx：服务已响应（401/404/405 均说明可达）
    except Exception:
        return False  # 网络层/超时：不可达


if __name__ == "__main__":
    # 2026-08-29：删除原「硬编码 sample 调 run_meta」的自测入口。
    # 它是飞书 08-29 两条空归因 pairwise_meta 记录的来源 —— 注释还停留在
    # 「需要本地已启动 coze 服务」的年代，端点早已换成公网，于是**调试动作直接
    # 往生产日志表写记录**。且它与 case1_pairwise_binary 完全重复、无独立价值。
    # 现自测方式（都不再裸调 run_meta）：
    #   python adapters/coze_client.py --health    仅探测端点可达性，不发起分析请求
    #   python scripts/run_meta.py <request.json>  走生产路径冒烟（自动带归因 + 去重）
    if "--health" in sys.argv:
        print("coze endpoint reachable:", health())
    else:
        print("用法:\n"
              "  python adapters/coze_client.py --health     探测 coze 端点可达性\n"
              "  python scripts/run_meta.py <request.json>   走生产路径冒烟（推荐）")
