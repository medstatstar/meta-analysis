#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n.py -- bilingual (EN/ZH) localization for the ct- skill library (shared base layer)

Provides:
  - is_chinese_os(): detect if the OS locale is Chinese
  - t(key, **kwargs): translate a message key to the current locale
  - set_lang(locale): manually override the locale (for testing)

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


def _current_lang():
    """Return 'zh' or 'en'."""
    return "zh" if is_chinese_os() else "en"


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
