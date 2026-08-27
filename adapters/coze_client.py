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

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

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


def _endpoint() -> str:
    return os.environ.get("COZE_META_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")


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
    """方案 B（2026-08-26）：coze 端已把 figures[].svg 与 repro.r 外置 S3 并返回 url 引用，
    此处按 url 下载回填，使下游（run_analysis.render_figures / 复现脚本）契约不变
    （figures[].svg、repro['r'] 照常可用）。

    - figures[].url → 填 fig['svg']
    - repro 为 dict 且含 url、无 'r' → 填 repro['r']（r_version/packages 已内联，不受影响）
    - 超时 / 网络失败 → 保留 url 并标记 _svg_fetch_failed / _repro_fetch_failed，绝不抛错中断分析。
    - 已含内容（coze 降级内联）或不是 dict → 原样跳过。
    """
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
    return parsed


def run_meta(task: str, data: dict, params: dict | None = None,
             figure: dict | None = None, query_origin: str | None = None) -> dict:
    """调用 coze 元分析工作流，返回解析后的结果 dict。

    Args:
        task:   任务类型（pairwise_meta / nma / metareg / ... 见 coze_contract.md）
        data:   分析数据（{"rows": [...], "colmap": {...}}）
        params: 分析参数（sm / model / subgroup / reference_group ...）
        figure: 出图控制（{"plots": [...], "width": 7, "height": 5}）
        query_origin: 调用发起来源标识（sha256:<64hex>，透传写入飞书 query_origin 列，
                      取值方式与 ct-registry 参考项目一致，2026-08-19）

    Returns:
        dict: {status, stats, figures:[{type,format,svg}], warnings, notes, task}

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
    payload = {
        "task": task,
        "data": data or {},
        "params": params or {},
        "figure": fig,
    }
    if query_origin:
        payload["query_origin"] = query_origin
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
        return outer if isinstance(outer, dict) else {"status": "error", "notes": "空响应"}
    try:
        parsed = json.loads(result_str)
    except json.JSONDecodeError:
        return {"status": "error", "notes": f"coze 返回非 JSON 结果：{result_str[:500]}"}
    # 2026-08-26 方案 B：figures[].svg 与 repro.r 已在 coze 端外置 S3，按 url 回填
    # （失败则保留 url 并标记 _*_fetch_failed，下游契约不变）
    _fill_external_svgs(parsed)
    # 透出飞书写入状态（coze 端 GraphOutput 顶层字段，2026-08-19）
    if isinstance(parsed, dict):
        for _k in ("feishu_write_success", "feishu_write_time"):
            if _k in outer:
                parsed[_k] = outer[_k]
        # 仅诊断参考：coze 请求→响应往返秒数（R 计算 + 网络；非界面渲染时间）
        parsed["coze_elapsed_seconds"] = round(_elapsed, 1)
        # 端点回退提示：原地址因 token 不一致触发回退，提示用户技能已升级、地址有变
        if used_fallback:
            parsed["_coze_endpoint_notice"] = ENDPOINT_FALLBACK_NOTICE
            notes = parsed.get("notes")
            if isinstance(notes, list):
                notes.append(ENDPOINT_FALLBACK_NOTICE)
            elif notes:
                parsed["notes"] = [notes, ENDPOINT_FALLBACK_NOTICE]
            else:
                parsed["notes"] = [ENDPOINT_FALLBACK_NOTICE]
            sys.stderr.write(
                "\n[meta-analysis] 端点回退提示: " + ENDPOINT_FALLBACK_NOTICE + "\n"
            )
    return parsed


def health() -> bool:
    """探测 coze 端点**可达性**（非功能健康）。

    2026-08-19 修正：coze 自定义域名通常仅暴露 /run，/health 路由未必存在——旧实现
    探测 /health 在服务正常时也可能误报 False。现改为探测 /run：
    - 2xx / 4xx / 5xx（含 401 缺 token、405 方法不允许）均证明服务已响应 → 可达 True；
    - 仅网络层错误 / 超时 / DNS 失败 → False（真正不可达）。
    """
    ep = _endpoint().rsplit("/run", 1)[0] or DEFAULT_ENDPOINT.rsplit("/run", 1)[0]
    try:
        req = urllib.request.Request(
            ep + "/run", method="POST", data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return True  # 2xx
    except urllib.error.HTTPError:
        return True  # 4xx/5xx：服务已响应（401/404/405 均说明可达）
    except Exception:
        return False  # 网络层/超时：不可达


if __name__ == "__main__":
    # 自测：需要本地已启动 coze 服务并配置 COZE_META_ENDPOINT
    import sys
    sample = {
        "task": "pairwise_meta",
        "data": {"rows": [
            {"study": "A", "event_exp": 12, "n_exp": 100, "event_ctrl": 20, "n_ctrl": 100},
            {"study": "B", "event_exp": 8, "n_exp": 90, "event_ctrl": 15, "n_ctrl": 95},
        ]},
        "params": {"sm": "OR", "model": "REML"},
        "figure": {"plots": ["forest"]},
    }
    out = run_meta(**sample)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:2000])
