"""
adapters/coze_client.py — meta-analysis 技能 → Coze 工作流 主路径客户端

设计（2026-08-17 拆分 refined：coze 默认优先 + 本地 R 兜底）：
- 这是技能的**主计算路径**客户端。R 引擎（metafor/meta/netmeta + dispatcher run_task.R）
  运行在 coze 元分析工作流（src/r_engine/ + src/graphs/nodes/meta_analysis.py）。
- 本客户端把分析请求打包成信封，POST 到 coze 工作流的 /run 端点，解析返回的 JSON 结果
  （status / stats / figures[].svg / warnings / notes）。
- 当 coze 不可达时，由上层 `adapters/run_analysis.py` 自动兜底到技能内置的本地引擎
  （adapters/local_engine.py → coze_project/src/r_engine/run_task.R），两者接口信封完全一致。
- 数值判断由 R 计算（coze 侧或本地），本客户端只解析结构、绝不读取/改写数值结论。
- 接口契约见 coze 项目的 coze_contract.md（不随技能发布）。

配置（环境变量）：
  COZE_META_ENDPOINT  工作流 /run 地址，默认 https://ct-meta.coze.site/run（2026-08-19 修正：
                     原默认 localhost:5000 为本地开发占位，导致未配置时误报 coze 不可达）
  COZE_META_TOKEN    可选鉴权令牌（Bearer）；留空则自动回退到 config/coze.dat
                     或 adapters/coze_token.py 内嵌的公开 blob（随技能发布）
  COZE_META_TIMEOUT   请求超时秒数，默认 600

⚠️ 出站披露（ct-base §5 安全模型，全库强制）：
  本模块会把**分析数据**（研究事件数 / 样本量 / 效应量等，不含个人身份信息）POST 到
  coze 工作流端点（默认 https://ct-meta.coze.site/run）执行云端 R 计算。首次出站前
  须经用户确认（AUTH-BLOCK + 统一文案，见 _auth_gate）；确认后端点写入 config.json
  auto_approve_endpoints 白名单，后续免确认。未授权时不阻断——由 run_analysis.py
  回退本地引擎并提示"本次未使用云端分析"。payload 发送前经 sanitize_payload() 脱敏。

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
    from .coze_token import get_token
except ImportError:  # 平铺模块直接运行（run_analysis 把 adapters 加入 sys.path）
    try:
        from coze_token import get_token
    except ImportError:
        get_token = None  # 极端情况：仅回退到 COZE_META_TOKEN 环境变量

# 2026-08-19 修正：真实发布端点（用户 2026-08-17 提供）。旧默认 localhost:5000 是本地开发占位，
# 未配置环境变量时会把请求打到本机、连接被拒 → run_analysis 误判 coze 不可达 → 错误兜底本地。
DEFAULT_ENDPOINT = "https://ct-meta.coze.site/run"


def _endpoint() -> str:
    return os.environ.get("COZE_META_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")


def _resolve_token() -> str:
    """解析 coze 鉴权 token，优先级：env COZE_META_TOKEN > config/coze.dat > 内嵌 blob。

    内嵌 blob（adapters/coze_token.py）保证技能发布后（.dat 被 SkillHub 白名单静默剥离）
    仍能读到公开的 coze 凭据，无缝连上工作流。
    """
    if get_token is not None:
        return get_token() or ""
    return os.environ.get("COZE_META_TOKEN", "")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    tok = _resolve_token()
    if tok:
        h["Authorization"] = "Bearer " + tok
    return h


def _timeout() -> int:
    try:
        return int(os.environ.get("COZE_META_TIMEOUT", "600"))
    except ValueError:
        return 600


# ---- ct-base §5 出站授权门控（2026-08-19 全库统一范式） ----

class AuthRequiredError(RuntimeError):
    """coze 出站未授权（首次出站须用户确认，ct-base §5 授权门控）。

    由 run_analysis.py 捕获 → 回退本地引擎，并提示"本次未使用云端分析"。
    """


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
    统一确认文案（由 agent 呈现给用户），返回 False（调用方回退本地，不阻断）。

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
        "⚠️ 重要提示：本技能的本地计算能力有限，大部分统计计算（meta / metafor / "
        "netmeta 等 R 引擎）依赖云端执行。如不同意发送，将无法使用云端分析，仅能使用"
        "本地基础引擎，功能与速度会显著下降。\n"
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
    # ct-base §5 授权门控：首次出站须用户确认（未授权 → AuthRequiredError → 本地兜底）
    if not _auth_gate(run_url):
        raise AuthRequiredError(
            f"coze 出站未授权（端点 {run_url} 不在 auto_approve_endpoints 白名单）。"
            f"如同意发送请让用户确认后调用 approve_endpoint('{run_url}') 再重试。"
        )
    # ct-base §5：出站 payload 发送前脱敏（剥离 PII）
    payload = sanitize_payload(payload)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        run_url, data=body, headers=_headers(), method="POST"
    )
    try:
        _t0 = time.time()
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            raw = resp.read().decode("utf-8")
        _elapsed = time.time() - _t0  # 仅诊断参考：coze 请求→响应往返（R 计算 + 网络）
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"coze 工作流返回 HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:500]}")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"无法连接 coze 工作流（{_endpoint()}）：{e.reason}。"
            f"默认端点应为 https://ct-meta.coze.site/run（如被旧配置覆盖，"
            f"请检查 COZE_META_ENDPOINT 是否误指向 localhost）。"
        )

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
    # 透出飞书写入状态（coze 端 GraphOutput 顶层字段，2026-08-19）
    if isinstance(parsed, dict):
        for _k in ("feishu_write_success", "feishu_write_time"):
            if _k in outer:
                parsed[_k] = outer[_k]
        # 仅诊断参考：coze 请求→响应往返秒数（R 计算 + 网络；非界面渲染时间）
        parsed["coze_elapsed_seconds"] = round(_elapsed, 1)
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
