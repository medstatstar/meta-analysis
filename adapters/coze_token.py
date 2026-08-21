# NOTE: 本文件含混淆后的 PUBLIC 共用凭据（XOR+base64）。它不是真加密，仅防目录浏览明文暴露。
# 用户授权 2026-08-17：该 coze 长期 token 随 meta-analysis 技能公开发布（调用 coze 元分析工作流）。
"""meta-analysis 公共凭据库（XOR+base64 混淆内嵌，镜像 ct-advisor 的 EMBEDDED_SECRETS 模式）。

背景（2026-08-17）：用户授权将 coze 长期 token 随技能**公开发布**，避免每次经环境变量注入，
并规避「推送 config.json 泄露 JWT」风险（token 不在 config.json 明文、也不在 memory/笔记）。

重要：
- 这是 OBFUSCATION，NOT real encryption。混淆密钥随脚本发布，持脚本者即可还原。本库只放
  **公开的、随技能发布**的共用凭据（访问 meta-analysis coze 工作流的 token），请勿用私有凭据覆盖。
- 历史方案曾把 coze token 落盘到 config/coze.dat；但 SkillHub 窄白名单打包（仅
  .svg/.py/.md/.json/.yaml/.txt/.toml/.csv）不含 .dat，发布时被静默剥离 → 已安装技能读不到
  文件、连不上 coze。故改为**统一内嵌**（EMBEDDED_SECRETS），不再依赖外部 .dat 文件。本地仍可用
  store_token() 写覆盖文件（可选，优先级介于 env 与内嵌之间）。

读取优先级（通用 get_secret）：CLI > env > 局部落盘文件 > 内嵌 blob。三者皆无回退空串。
coze token 走便捷函数 get_token()，等价于 get_secret("meta_analysis_coze", ...)。
"""
from __future__ import annotations

import base64
import os

# 单份混淆密钥（所有公开凭据共用；都是公开凭据，无横向泄露风险）。
OBFUSCATION_KEY = b"meta-analysis-coze-obf-v1-9f2c"

# 内嵌公共凭据库：name -> XOR+base64 混淆 blob。
EMBEDDED_SECRETS = {
    "meta_analysis_coze": (
        "CBw-CU8mDQgjEDk6JlcqXjQMZBwrC1kGa25wUHsJLw0uC3hTITUhSj89G0UsKC8RYyg0CmM1AERjIX9RITE9UmIlCVIhAyZYKWkAGDcMZ1ZMA1Q8QU4KK1ssBC8bBWUzGQIWFgUlQWsUDilQRw1RFkE6XGNML1sUBDwsN0YoBBEOMB5QR0lSIQA_QwsJAms8YndSLAc0OAk6LmsJACxdLEM8H2sqIS9cQz01Fn0_XR1KL181WQY3KBsuKigUNDcgQWMJCEkrRwxXKX4BWExuIAIqBwoML1cGXC44GgQmJ04aIzkvVws1L0Q5WGdDBXUPAD8ZNBstF1gEGjQCBnRRVkw_floIBERPAk8KLEABKlwcO2tYHjsrLwYNNEFTCilcXTUmCR44W04JKXYAWSseLBgvFDBdNBkwRmMZDE8sRBgLBR48W2RTCVsCOlAdAx43GzsqQBsNK38MN0gjRzZQMFcVABQJBAAXAQcYWF07Kg5fNxkKQ2I3CAIqaQgYKFcVAGNtNwctKQZAKENRQCBaM14qKXU8NzI6Zw04XmAFa25UFEAuKB0gB1xUCCYGOCI4BUEpGEoPYSwoNEY7Q2JSUVQFOB8xNHwoHiQWHDhcNkEaWBkKYl0YDlQae09wFHwpPVAGUnQjBxEqHjooRF8CDBw6XhoFI041XG5IEmsvJVYSE3kTBlVcGyYYFk5RFjkMShUrAEBBcEJKDHcZOi07UmIpBD4VICQAXlo1P0k8dzdWOWEdWlxaMHYGXzw6IhUFCTg0ChVaGlsGJis6RTUzI34yA2tXUgstBisrKRgoIQkgID05O2APKwkmRwcpNmc5ch5LHnZbCRIuG1kWKxEDOikwR08xCkwrZDYUV04sU257VGEwJw0VDBwVL1MhOAYwCkUSCTkgSQsyCV1DY1V8IwMZHxIQL0cSMVQAHREQMhVaPUpURyEIOW5bYk5IAXNOACBZO0kNBxIpIwUTNlskKwAjWg=="
    ),
}

# 局部落盘绝对路径（兼容历史：允许用户/作者用私有 key 覆盖内嵌默认值）。
DEFAULT_TOKEN_PATH = os.path.expanduser(
    "~/.workbuddy/skills/meta-analysis/config/coze.dat"
)

# coze token 的环境变量名（与 coze_client 的 COZE_META_TOKEN 一致）。
TOKEN_ENV = "COZE_META_TOKEN"


def _obf_encode(plain: str) -> str:
    """XOR 每个字节与滚动密钥，再做 URL-safe base64。"""
    data = plain.encode("utf-8")
    key = OBFUSCATION_KEY
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(xored).decode("ascii")


def _obf_decode(blob: str) -> str:
    """_obf_encode 的逆操作。"""
    data = base64.urlsafe_b64decode(blob.strip())
    key = OBFUSCATION_KEY
    plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return plain.decode("utf-8")


def default_token_path() -> str:
    return DEFAULT_TOKEN_PATH


def store_token(plain: str, token_path: str = None) -> str:
    """混淆并落盘 token（可选覆盖文件）；返回实际写入路径。"""
    path = token_path or DEFAULT_TOKEN_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    blob = _obf_encode(plain.strip())
    with open(path, "w", encoding="utf-8") as f:
        f.write(blob)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def get_secret(name: str, cli_value: str = None, env_name: str = None,
               secret_path: str = None) -> str:
    """按名字取公开凭据：CLI > env > 局部文件 > 内嵌 blob。皆无回退空串。"""
    if cli_value:
        return cli_value
    if env_name:
        env = os.environ.get(env_name)
        if env:
            return env
    if secret_path and os.path.exists(secret_path):
        try:
            with open(secret_path, encoding="utf-8") as f:
                return _obf_decode(f.read())
        except Exception:
            pass
    blob = EMBEDDED_SECRETS.get(name)
    if blob:
        try:
            return _obf_decode(blob)
        except Exception:
            return ""
    return ""


def get_token(cli_token: str = None, token_path: str = None,
              token_env: str = TOKEN_ENV) -> str:
    """coze 便捷封装：等价于 get_secret("meta_analysis_coze", ...)。"""
    return get_secret("meta_analysis_coze", cli_token, token_env,
                      token_path or DEFAULT_TOKEN_PATH)
