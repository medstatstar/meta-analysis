#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ct-base 通用工作台 UI 细节自动检查引擎（C-detail-* 机检目录）。

零第三方依赖（仅标准库）。本文件是 **ct- 家族统一底座**里的通用引擎，供所有叶技能
"随包获得副本 + 提供 wb_detail_check.rules.json 扩展" 使用——引擎本身 **零叶子硬编码**：

  - 家族级默认词表（模糊名 / 泛词 / 承诺式 / i18n 白名单）已内置于此，全家族通用；
  - 叶子特定的词表追加、i18n 白名单覆盖、以及 C-detail-scope / C-detail-dupctl 的
    选择器 / scope 取值，全部经 `<root>/scripts/wb_detail_check.rules.json` 注入；
  - 因此同一份引擎可被 ct-literature / ct-registry / meta-analysis 等任意叶技能复用，
    不需每个技能复制一份写死自己选择器的大脚本。

覆盖的检查（全部可由 rules.json 配置，无浏览器即可判定）：
  C-detail-label       模糊名扫描（FAIL）—— 红线 3
  C-detail-placeholder 占位泛词扫描（FAIL，属性）/ 空态泛词（WARN，容器）—— 红线 4
  C-detail-claim       输入语法类承诺扫描（WARN→FAIL）—— 红线 1
  C-detail-i18n-ph     单语静态占位扫描（WARN）—— 红线 4
  C-detail-scope       表单态 scope 覆盖（FAIL，rules.scope 驱动）—— 红线 2
  C-detail-dupctl      相似控件（WARN，rules.dupctl 驱动）—— 红线 2
  C-detail-emptystate  空态引导（WARN，容器扫描版）—— 红线 4

设计要点（降噪，详见 ct-base `references/workbench_ui.md` §21）：
  - claim 只盯"输入语法类承诺"（"可直接写 P:" / "支持…语法" 等后端可能不解析的
    输入格式声明），不把"会自动翻译"这类真实存在的自动行为误伤。
  - placeholder 属性扫描用泛词子串命中（高置信→FAIL）；空态容器扫描要求归一化后
    精确等于泛词（避免"暂无决策"被"暂无"误伤），且降为 WARN。
  - i18n-ph 排除"例：/例如：/如 "等示例前缀与常见单语字段（密码/备注/英文检索词），
    仅对"看起来是引导文案却单语"的占位报 WARN。
  - scope / dupctl 完全规则驱动：引擎不认识 `.picos-in` 或任何叶子的 class，全部从
    rules.json 读。

rules.json 字段（全部可选，缺省走家族默认）：
  fuzzy_labels_add:        []   追加模糊名
  placeholder_generics_add:[]  追加占位泛词
  emptystate_generics_add: []  追加空态泛词
  claim_patterns_add:      []  追加承诺式正则（字符串，引擎编译）
  i18n_whitelist_add:      []  追加单语字段白名单
  i18n_whitelist_force:    []  覆盖（而非追加）i18n 白名单
  scope: { "selectors": ["#center .picos-in", ".my-input"], "values": ["seed","result"] }
  dupctl: { "pairs": [["重新评估","确认 PICOS"]], "generic_similarity": false }
  enable: { "scope": false, "dupctl": false }   # 这两项默认关，需叶子显式开启

用法：
  python wb_detail_check.py                 # 自动定位同技能根的 workbench.html + rules.json
  python wb_detail_check.py --html <path>   # 指定文件
  python wb_detail_check.py --root <dir>    # 技能根（自动找 workbench.html 与 scripts/rules.json）
  python wb_detail_check.py --rules <path>  # 显式指定规则文件

退出码：0 = 全绿（无 FAIL）；非 0 = 存在 FAIL（用于阻断发布）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# —— 家族级默认词表（全 ct- 工作台通用；叶技能用 rules.json 扩展，不在此写死）——
DEFAULT_FUZZY_LABELS = [
    "中英对照", "高级", "更多", "设置", "其他", "自定义", "更多选项", "其它",
]
DEFAULT_PLACEHOLDER_GENERICS = [
    "待填", "to fill", "请输入", "无数据", "未填写",
]
DEFAULT_EMPTYSTATE_GENERICS = ["无数据", "待填", "未填写", "暂无"]
# 红线 1：输入语法类承诺（后端可能不解析的输入格式声明）—— 仅此类，避免误伤真实自动行为
# 注意：必须紧跟"写/Write"等输入动作，不单独用"可直接"（会误伤"可直接重试/上传"等合法指引）
DEFAULT_CLAIM_PATTERNS = [
    r"可直接写",
    r"请直接写",
    r"支持.+语法",
    r"write\s+[\"']P\s*:",
    r"写\s*[\"“]P\s*:",
]
# i18n-ph 排除：示例前缀 + 常见单语字段白名单
DEFAULT_I18N_PH_EXAMPLE_PREFIX = ("例：", "例如：", "如 ")
DEFAULT_I18N_PH_WHITELIST = ("密码", "备注", "英文检索词", "如 ")

# 扫描"可见文案"的标签（其 inner text 参与 label 模糊名检查）
LABEL_TAGS = ["label", "button", "summary", "option"]

RULES_FILENAME = "wb_detail_check.rules.json"


# ———————————————————————————————————————————————————————
# 规则加载（合并家族默认 + 叶子 rules.json）
# ———————————————————————————————————————————————————————
def load_rules(rules_path: Path | None):
    cfg = {
        "fuzzy_labels": list(DEFAULT_FUZZY_LABELS),
        "placeholder_generics": list(DEFAULT_PLACEHOLDER_GENERICS),
        "emptystate_generics": list(DEFAULT_EMPTYSTATE_GENERICS),
        "claim_patterns": list(DEFAULT_CLAIM_PATTERNS),
        "i18n_ph_example_prefix": DEFAULT_I18N_PH_EXAMPLE_PREFIX,
        "i18n_ph_whitelist": list(DEFAULT_I18N_PH_WHITELIST),
        "scope": None,          # {"selectors": [...], "values": [...]}
        "dupctl": None,         # {"pairs": [[a,b],...], "generic_similarity": bool}
        "enable_scope": False,
        "enable_dupctl": False,
    }
    if not rules_path or not rules_path.exists():
        return cfg
    try:
        raw = json.loads(rules_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("⚠ rules.json 解析失败，回退家族默认: %s" % e, file=sys.stderr)
        return cfg

    if isinstance(raw.get("fuzzy_labels_add"), list):
        cfg["fuzzy_labels"] += raw["fuzzy_labels_add"]
    if isinstance(raw.get("placeholder_generics_add"), list):
        cfg["placeholder_generics"] += raw["placeholder_generics_add"]
    if isinstance(raw.get("emptystate_generics_add"), list):
        cfg["emptystate_generics"] += raw["emptystate_generics_add"]
    if isinstance(raw.get("claim_patterns_add"), list):
        cfg["claim_patterns"] += [p for p in raw["claim_patterns_add"] if isinstance(p, str)]
    if isinstance(raw.get("i18n_whitelist_add"), list):
        cfg["i18n_ph_whitelist"] += raw["i18n_whitelist_add"]
    if isinstance(raw.get("i18n_whitelist_force"), list):
        cfg["i18n_ph_whitelist"] = list(raw["i18n_whitelist_force"])

    scope = raw.get("scope")
    if isinstance(scope, dict) and isinstance(scope.get("selectors"), list) \
            and isinstance(scope.get("values"), list):
        cfg["scope"] = scope
        cfg["enable_scope"] = bool(raw.get("enable", {}).get("scope", True))
    dupctl = raw.get("dupctl")
    if isinstance(dupctl, dict) and isinstance(dupctl.get("pairs"), list):
        cfg["dupctl"] = dupctl
        cfg["enable_dupctl"] = bool(raw.get("enable", {}).get("dupctl", True))
    return cfg


# ———————————————————————————————————————————————————————
# 通用 HTML 抽取
# ———————————————————————————————————————————————————————
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _tag_text(html: str, tag: str):
    out = []
    for m in re.finditer(r"<%s\b[^>]*>(.*?)</%s>" % (tag, tag), html, re.S | re.I):
        txt = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if txt:
            out.append(txt)
    return out


def _attr_values(html: str, attr: str):
    return [m.group(2) for m in re.finditer(r"%s\s*=\s*([\"'])(.*?)\1" % attr, html, re.S)]


def _tag_openings(html: str):
    """yield 每个标签开标签的完整字符串（含属性）。"""
    for m in re.finditer(r"<[a-zA-Z][^>]*>", html):
        yield m.group(0)


# ———————————————————————————————————————————————————————
# 检查项
# ———————————————————————————————————————————————————————
def _check_label(html: str, cfg):
    """C-detail-label：模糊名扫描（FAIL）。"""
    hits = []
    for tag in LABEL_TAGS:
        for txt in _tag_text(html, tag):
            for w in cfg["fuzzy_labels"]:
                if w in txt:
                    hits.append("%s 文案命中模糊名「%s」: %r" % (tag, w, txt[:40]))
    for v in _attr_values(html, "title"):
        for w in cfg["fuzzy_labels"]:
            if w in v:
                hits.append("title 命中模糊名「%s」: %r" % (w, v[:40]))
    return "C-detail-label", hits


def _check_placeholder_attr(html: str, cfg):
    """C-detail-placeholder（属性，FAIL）：placeholder="..." 命中泛词。"""
    hits = []
    for v in _attr_values(html, "placeholder"):
        for w in cfg["placeholder_generics"]:
            if w in v:
                hits.append("placeholder 命中泛词「%s」: %r" % (w, v[:40]))
    return "C-detail-placeholder", hits


def _check_placeholder_emptystate(html: str, cfg):
    """C-detail-placeholder（空态容器，WARN）：归一化后精确等于泛词。"""
    hits = []
    for m in re.finditer(
        r'class\s*=\s*([\"\'])([^\"\']*\b(empty|null|no-data|nodata)\b[^\"\']*)\1',
        html, re.I,
    ):
        seg = html[m.start(): m.start() + 400]
        inner = re.search(r">([^<]{0,40})<", seg)
        if not inner:
            continue
        norm = re.sub(r"[（）()\s]", "", inner.group(1))
        for w in cfg["emptystate_generics"]:
            if norm == w:
                hits.append("空态文案等于泛词「%s」: %r" % (w, inner.group(1)))
                break
    return "C-detail-placeholder(empty)", hits


def _check_claim(html: str, cfg):
    """C-detail-claim：输入语法类承诺扫描（WARN；无 claim-verified 闭环则 FAIL）。"""
    sources = []
    sources += _attr_values(html, "placeholder")
    sources += _attr_values(html, "title")
    sources += _tag_text(html, "p")
    sources += _tag_text(html, "span")
    sources += _tag_text(html, "div")
    warn_hits = []
    for s in sources:
        for pat in cfg["claim_patterns"]:
            if re.search(pat, s):
                warn_hits.append("承诺式表述 %r 命中模式 %s" % (s[:40], pat))
                break
    has_verified = "claim-verified:" in html
    return "C-detail-claim", warn_hits, (not has_verified)


def _check_i18n_placeholder(html: str, cfg):
    """C-detail-i18n-ph：单语静态占位扫描（WARN，已排除示例与常见单语字段）。"""
    warns = []
    for v in _attr_values(html, "placeholder"):
        if not re.search(r"[一-鿿]", v):
            continue
        if v.startswith(cfg["i18n_ph_example_prefix"]) or v[:2] in cfg["i18n_ph_example_prefix"]:
            continue
        if any(w in v for w in cfg["i18n_ph_whitelist"]):
            continue
        if "zh ?" in v or v.startswith("T."):
            continue
        warns.append("静态占位含中文但未走 i18n 三元/T 键: %r" % v[:40])
    return "C-detail-i18n-ph", warns


def _check_scope(html: str, cfg):
    """C-detail-scope（rules 驱动，FAIL）：收集函数覆盖的 data-scope 须含全部期望值。

    引擎不认识任何叶子 class——selectors/values 全部从 rules.json 的 scope 读。
    selectors 支持 ".class" 或 "#id" 形式（按属性子串匹配）。
    """
    scope = cfg.get("scope")
    if not scope:
        return "C-detail-scope", []
    selectors = scope.get("selectors", [])
    expected = set(scope.get("values", []))
    present = set()
    for opening in _tag_openings(html):
        cls = ""
        cm = re.search(r'class\s*=\s*[\"\']([^\"\']*)[\"\']', opening, re.I)
        if cm:
            cls = cm.group(1)
        idm = re.search(r'id\s*=\s*[\"\']([^\"\']*)[\"\']', opening, re.I)
        idv = idm.group(1) if idm else ""
        for sel in selectors:
            # 子串匹配：workbench.html 大量使用 JS 模板字面量（class="picos-in${...}"），
            # 单词切分会把 "picos-in" 拆成 "picos-in${miss" 而漏匹配；子串对模板字面量稳健。
            # 选择器由叶子在 rules.json 提供，是否过度匹配由叶子自负。
            if sel.startswith("."):
                if sel[1:] in cls:
                    break
            elif sel.startswith("#"):
                if sel[1:] in idv:
                    break
            else:
                if sel in cls:
                    break
        else:
            continue
        dsm = re.search(r'data-scope\s*=\s*[\"\']([^\"\']*)[\"\']', opening, re.I)
        if dsm:
            present.add(dsm.group(1))
    missing = expected - present
    if missing:
        return "C-detail-scope", [
            "selectors=%s 覆盖到的 data-scope=%s，缺期望值 %s"
            % (selectors, sorted(present), sorted(missing))
        ]
    return "C-detail-scope", []


def _check_dupctl(html: str, cfg):
    """C-detail-dupctl（rules 驱动，WARN）：明示的相似控件对须有 dup-verified 闭环。

    引擎不预设任何控件名——pairs 从 rules.json 的 dupctl.pairs 读（每对两个短语）。
    两短语均出现在 LABEL_TAGS 文案中、且文件无 `dup-verified:` 标记 → WARN。
    """
    dupctl = cfg.get("dupctl")
    if not dupctl:
        return "C-detail-dupctl", []
    warns = []
    all_text = []
    for tag in LABEL_TAGS:
        all_text += _tag_text(html, tag)
    corpus = " \n ".join(all_text)
    for pair in dupctl.get("pairs", []):
        if not (isinstance(pair, list) and len(pair) == 2):
            continue
        a, b = pair
        if a in corpus and b in corpus:
            if "dup-verified:" not in html:
                warns.append("相似控件对 %r / %r 均存在但未标 dup-verified:（疑似冗余/行为差异未证伪）"
                             % (a, b))
    return "C-detail-dupctl", warns


# ———————————————————————————————————————————————————————
# 主流程
# ———————————————————————————————————————————————————————
def main():
    ap = argparse.ArgumentParser(description="ct-base 通用工作台 UI 细节机检 (C-detail-*)")
    ap.add_argument("--html", help="直接指定 workbench.html 路径")
    ap.add_argument("--root", help="技能根目录（自动定位 workbench.html 与 scripts/rules.json）")
    ap.add_argument("--rules", help="显式指定 wb_detail_check.rules.json 路径")
    args = ap.parse_args()

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[1]

    html_path = None
    if args.html:
        html_path = Path(args.html)
    else:
        cands = list(root.rglob("workbench.html"))
        if not cands:
            print("✕ 未找到 workbench.html（--html 指定 或 --root 指向技能根）", file=sys.stderr)
            return 2
        html_path = cands[0]

    if not html_path.exists():
        print("✕ 文件不存在: %s" % html_path, file=sys.stderr)
        return 2

    # rules.json：显式 > 技能根 scripts/ > 无（家族默认）
    rules_path = None
    if args.rules:
        rules_path = Path(args.rules)
    else:
        cand = root / "scripts" / RULES_FILENAME
        if cand.exists():
            rules_path = cand
    cfg = load_rules(rules_path)

    html = _read(html_path)
    print("目标: %s  (%d 字符)" % (html_path, len(html)))
    if rules_path:
        print("规则: %s" % rules_path)
    else:
        print("规则: 家族默认（未找到 %s）" % RULES_FILENAME)

    fails = []   # (name, hits)
    warns = []   # (name, hits)

    name, hits = _check_label(html, cfg)
    if hits:
        fails.append((name, hits))

    name, hits = _check_placeholder_attr(html, cfg)
    if hits:
        fails.append((name, hits))

    name, hits = _check_placeholder_emptystate(html, cfg)
    if hits:
        warns.append((name, hits))

    name, hits, escalate = _check_claim(html, cfg)
    if hits:
        if escalate:
            fails.append((name, hits + ["  ↳ 无 claim-verified: 闭环，升级 FAIL"]))
        else:
            warns.append((name, hits))

    name, hits = _check_i18n_placeholder(html, cfg)
    if hits:
        warns.append((name, hits))

    if cfg["enable_scope"]:
        name, hits = _check_scope(html, cfg)
        if hits:
            fails.append((name, hits))

    if cfg["enable_dupctl"]:
        name, hits = _check_dupctl(html, cfg)
        if hits:
            warns.append((name, hits))

    print("\n--- C-detail-* 结果 ---")
    for name, hits in fails:
        print("[FAIL] %s (%d)" % (name, len(hits)))
        for h in hits:
            print("   - " + h)
    for name, hits in warns:
        print("[WARN] %s (%d)" % (name, len(hits)))
        for h in hits:
            print("   - " + h)

    if not fails and not warns:
        print("✓ C-detail-* 全绿（label / placeholder / claim / i18n-ph"
              + (" / scope" if cfg["enable_scope"] else "")
              + (" / dupctl" if cfg["enable_dupctl"] else "") + "）")

    print("\n判据：任一 FAIL = 禁止交付。本次 FAIL=%d, WARN=%d" % (len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
