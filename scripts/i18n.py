#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n.py -- bilingual (EN/ZH) localization for the ct- skill library (shared base layer)

Provides:
  - is_chinese_os(): detect if the OS locale is Chinese (system-level; drives local UI prompts)
  - t(key, **kwargs): translate a message key to the current locale
  - set_lang(locale): manually override the locale (process scope, for testing)
  - set_lang_session(locale): persist language for the current conversation (writes data/.lang_session)
  - set_lang_permanent(locale): persist language across sessions (writes config.json `language`)
  - _current_lang(): resolve 'zh'/'en' via chain: process override → session → config.json → OS locale
  - detect_text_language(text): content-level detection (zh/en/None) by INPUT TEXT, NOT OS locale
  - resolve_user_language(query, override): build the coze `user_language` backup param (3-tier priority)

Rules (per ~/.workbuddy/MEMORY.md "双语语言策略"):
  - Default: English
  - Auto-switch to Chinese when OS locale contains zh/CN
  - Code output (R/Python) is NOT affected by language policy

Usage:
  from i18n import t
  print(t("error.rscript_not_found"))
  print(t("info.result_saved", path="/tmp/x.json"))

Bilingual data lives in i18n_messages.json (same directory) -- see that file
for all EN/ZH strings. This module holds only detection + lookup logic.
"""

import os
import sys
import json


# ═══════════════════════════════════════════════════════════════════════════
# Locale detection / 系统语言检测
# ═══════════════════════════════════════════════════════════════════════════

_OVERRIDE_LANG = None


def set_lang(locale_code):
    """Manually override language (for testing). Pass None to reset to auto-detect."""
    global _OVERRIDE_LANG
    _OVERRIDE_LANG = locale_code


def is_chinese_os():
    """Detect if the OS is Chinese (zh-CN, zh-TW, zh-HK, etc.).

    Detection order:
      1. Environment variables: LANGUAGE / LC_ALL / LC_MESSAGES / LANG
      2. Windows API: GetLocaleInfoW + registry (LocaleName)
      3. Python locale module: getdefaultlocale()
    """
    global _OVERRIDE_LANG
    if _OVERRIDE_LANG is not None:
        return _OVERRIDE_LANG == "zh"

    # 1. Check environment variables
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val.lower().startswith("zh"):
            return True

    # 2. Windows-specific detection
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            ctypes.windll.kernel32.GetLocaleInfoW(0x0400, 0x00000005, buf, 85)
            if buf.value.lower().startswith("zh"):
                return True
        except Exception:
            pass

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Control Panel\International"
            )
            locale_name = winreg.QueryValueEx(key, "LocaleName")[0]
            winreg.CloseKey(key)
            if locale_name.lower().startswith("zh"):
                return True
        except Exception:
            pass

    # 3. Python locale module fallback
    try:
        import locale
        loc = locale.getdefaultlocale()[0]
        if loc and loc.lower().startswith("zh"):
            return True
    except Exception:
        pass

    return False


# ═══════════════════════════════════════════════════════════════
# Language persistence / 语言持久化（session / permanent 两层）
# ═══════════════════════════════════════════════════════════════
#
# 解析链（最高 → 最低），由 _current_lang() 实现，亦见 scripts/switch_lang.py：
#   process override (set_lang) → session file (data/.lang_session)
#       → config.json `language` (set_lang_permanent) → OS locale
# 注：config.json 仅由用户经 CLI（switch_lang.py --permanent）触发、本模块执行读取；
# agent 不得直接改写 config.json（见 AGENTS.md 红线）。

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SESSION_FILE = os.path.join(_SKILL_ROOT, "data", ".lang_session")
_CONFIG_PATH = os.path.join(_SKILL_ROOT, "config.json")


def _normalize_lang_code(locale):
    """Map switch_lang.py input (zh-CN/en/...) → internal 'zh'/'en'."""
    return "zh" if str(locale).lower().startswith("zh") else "en"


def _read_session_lang():
    """Read session-scope language from data/.lang_session (this conversation)."""
    try:
        with open(_SESSION_FILE, encoding="utf-8") as _f:
            val = _f.read().strip()
        return val if val in ("zh", "en") else None
    except OSError:
        return None


def _read_config_lang():
    """Read persistent language from config.json `language` (cross-session)."""
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as _f:
            data = json.load(_f)
        val = data.get("language")
        return val if val in ("zh", "en") else None
    except (OSError, ValueError):
        return None


def _current_lang():
    """Return 'zh' or 'en' via resolution chain:
    process override → session file → config.json `language` → OS locale.
    """
    if _OVERRIDE_LANG is not None:
        return "zh" if _OVERRIDE_LANG == "zh" else "en"
    s = _read_session_lang()
    if s:
        return s
    c = _read_config_lang()
    if c:
        return c
    return "zh" if is_chinese_os() else "en"


def set_lang_session(locale):
    """Persist language for the current conversation only (session scope).

    Writes `data/.lang_session`; pass None to clear. Does not touch the
    process override (_OVERRIDE_LANG) — that stays the highest-priority layer.
    """
    try:
        if locale is None:
            if os.path.exists(_SESSION_FILE):
                os.remove(_SESSION_FILE)
            return
        norm = _normalize_lang_code(locale)
        os.makedirs(os.path.dirname(_SESSION_FILE), exist_ok=True)
        with open(_SESSION_FILE, "w", encoding="utf-8") as _f:
            _f.write(norm)
    except OSError:
        pass


def set_lang_permanent(locale):
    """Persist language across sessions by writing config.json `language`.

    Invoked by the user via `scripts/switch_lang.py --permanent`; this module
    only performs the file write (does not hand-edit config.json elsewhere).
    """
    norm = _normalize_lang_code(locale)
    try:
        data = {}
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, encoding="utf-8") as _f:
                data = json.load(_f)
        data["language"] = norm
        with open(_CONFIG_PATH, "w", encoding="utf-8") as _f:
            json.dump(data, _f, ensure_ascii=False, indent=2)
            _f.write("\n")
    except (OSError, ValueError):
        pass


# ═══════════════════════════════════════════════════════════════════════════
# Content-level language detection / 内容级语言检测（用户【输入文本】，非系统 locale）
# ═══════════════════════════════════════════════════════════════════════════
#
# 痛点：is_chinese_os() / _current_lang() 只检测【系统语言】，中文系统恒返 zh。
# 当用户在中文系统里输入【英文 query】（如 "BCG vaccine meta analysis"）时，若按系统
# locale 决定 coze 端报告语言，会误判为 zh —— 这是"中文环境 + 英文输入"的判定盲区。
# 解决：对【用户输入文本】做内容级检测（含中文→zh，纯英文→en），与系统 locale 解耦。
# 与 is_chinese_os() 职责分离：本组函数决定"coze 计算端报告/图表语言"，前者决定"本地
# 运行期 UI 提示语言"（仍遵循 language_policy.md 的"默认英文、中文环境自动切中文"）。

import re as _re

# CJK 扫描范围：基本汉字(4E00-9FFF) + 扩展 A(3400-4DBF) + 兼容汉字(F900-FAFF)
#              + CJK 标点(3000-303F) + 全角字符(FF00-FFEF)
_CJK_RE = _re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")

# 语言多写法归一化表：中文语境→zh，英文→en，未知值原样小写透传（coze 可据自身逻辑解释）
_LANG_ALIASES = {
    "zh": "zh", "chinese": "zh", "中文": "zh", "cn": "zh", "zh-cn": "zh",
    "zh_cn": "zh", "zh-tw": "zh", "zh_tw": "zh", "zh-hk": "zh", "zh_hk": "zh",
    "en": "en", "english": "en", "英语": "en", "eng": "en",
}


def _normalize_language(value):
    """User language → normalized code.

    - None/空 → 回退 i18n._current_lang()（系统 locale）。
    - 已知别名（中文/英语/chinese/cn…） → zh / en。
    - 未知值 → 原样小写透传（coze 可据自身逻辑解释，保证可扩展）。
    """
    if not value:
        return _current_lang()
    key = (value or "").strip().lower()
    return _LANG_ALIASES.get(key, key)


def detect_text_language(text):
    """按【输入文本内容】判定语言（内容级），而非系统 locale。

    Returns 'zh' / 'en' / None。
      - 无 CJK 字符 → 'en'
      - 含 CJK（中文占比≥5% 或中文字符≥2） → 'zh'
      - 空文本 → None（调用方回退到系统 locale）

    混合文本（"做 meta analysis"）按中文占比判定：偶有单字英文混排仍判 zh，
    纯英文混极少中文判 en。属"备用"输入，coze 端有自身判定时可忽略。
    """
    if not text or not text.strip():
        return None
    letters = _re.sub(r"\s+", "", text)
    if not letters:
        return None
    cjk = len(_CJK_RE.findall(text))
    if cjk == 0:
        return "en"
    ratio = cjk / len(letters)
    return "zh" if (ratio >= 0.05 or cjk >= 2) else "en"


def resolve_user_language(query="", override=None):
    """构造 coze 计算端请求用的 `user_language` 备用入参（归一化 zh/en）。

    三级优先级：
      1. 显式 `override`（如 `--language en`）—— 最高；
      2. 否则按【输入 query 文本】做内容级检测（中文系统+英文输入→'en'，
         不被系统 locale 误判 zh）；
      3. query 为空时回退系统 locale（i18n._current_lang()）。

    返回归一化 'zh' / 'en'。这是【备用提示】供 coze 端决定报告/图表文案语言，
    coze 可忽略；不覆盖 i18n 的运行期 UI 提示（后者仍按库策略走系统 locale）。
    """
    if override:
        return _normalize_language(override)
    text_lang = detect_text_language(query if query else "")
    return text_lang if text_lang else _normalize_language(None)


# ═══════════════════════════════════════════════════════════════════════════
# Message dictionary / 消息字典 —— 数据外置到 i18n_messages.json（EN/ZH 成对）
# ═══════════════════════════════════════════════════════════════════════════

# 外部双语数据文件（与本模块同目录），全库面向用户 EN/ZH 字符串的唯一来源。
# 新增/修改文案请在 i18n_messages.json 中操作，切勿在消费脚本内硬编码中英文。
# / External bilingual data file (same dir). Single source of truth for all
# user-facing EN/ZH strings. Edit i18n_messages.json, never hard-code in callers.
#
# 分区索引（与 JSON 内 key 前缀对应）：
#   generic / exec / info / error / validation —— 全库通用消息（i18n_messages.json）
#   install / header.r_code / header.install_cmd / error.rscript_* / error.r_timeout
#       —— R 软件相关消息，单独放 i18n_r_messages.json（可选扩展，仅真正调用 R 的技能
#          vendor 并携带此文件；纯 Python 技能不携带时自动跳过，见下方加载逻辑）
#   xlsx.*          —— ct-registry Excel 报告框架标签
#   xlsx.safety.*   —— ct-safety FAERS Excel 报告标签
#   kw_gate.*       —— ct-registry 关键字体系确认菜单
#   auth.*          —— 首次出站授权 / 依赖缺失 / 网络错误 / 回退本地等一次性提示（底座预置标准词条）
# 注：原始数据值（CDE 中文状态、中文适应症、反应 PT 等）一律不翻译，仅翻译 UI 框架标签。

_HERE = os.path.dirname(os.path.abspath(__file__))
_MSG_PATH = os.path.join(_HERE, "i18n_messages.json")

try:
    with open(_MSG_PATH, encoding="utf-8") as _f:
        _MESSAGES = json.load(_f)
except (OSError, ValueError):
    # 离线兜底：文件缺失/损坏也不让模块崩溃；缺的 key 由 t() 回退为 key 本身。
    _MESSAGES = {}

# 可选 R 扩展消息（i18n_r_messages.json）：仅真正调用 R 的技能 vendor 并携带此文件；
# 纯 Python 技能（如 ct-literature）不携带时自动跳过，行为与旧版一致（向后兼容）。
_R_MSG_PATH = os.path.join(_HERE, "i18n_r_messages.json")
try:
    with open(_R_MSG_PATH, encoding="utf-8") as _f:
        _MESSAGES.update(json.load(_f))
except (OSError, ValueError):
    pass

# 可选技能级扩展消息（i18n_skill_messages.json，2026-08-28 新增）：承载技能**专有**词条
# （如 ct-samplesize 的 label.* / r_header.* / error.* 统计词条）。这些词条是叶子技能自带的
# 统计领域文案，**不应**上移到 ct-base 通用 i18n_messages.json（否则污染共享底座、破坏
# §16.8「叶子是底座子集」）；由技能 vendor 携带本文件。底座 i18n.py 自身不携带时自动跳过
# （向后兼容，对其它 ct- 技能零影响）。
_SKILL_MSG_PATH = os.path.join(_HERE, "i18n_skill_messages.json")
try:
    with open(_SKILL_MSG_PATH, encoding="utf-8") as _f:
        _MESSAGES.update(json.load(_f))
except (OSError, ValueError):
    pass


def t(key, **kwargs):
    """Translate a message key to the current locale.

    Args:
        key: message identifier in i18n_messages.json
        **kwargs: format placeholders (e.g., path="/tmp/x.json")

    Returns:
        Localized string. Falls back to the key itself if not found.
    """
    lang = _current_lang()
    entry = _MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(lang, entry.get("en", key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# Back-compatible alias
_ = t
