#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""search_cache.py — meta-analysis 检索结果本地长期缓存（source+query 维度，24h TTL）

WHY / 设计动机（参考 ct-literature/adapters/search_cache.py）：
  meta-analysis 的 search_literature() 走 ct-search.coze.site 端点，每次出站
  耗云端配额。选题阶段同一 topic 会反复跑探针（调参 / 重渲报告 / 候选方向对比），
  短期去重（_dedup_*，300s 窗口）只防 burst 重试，跨运行不生效。本模块按
  (source, keyword, year_from, year_to, max_results) 联合键持久化成功结果，
  TTL 内直接复用（默认 24h），省 Coze 配额 + 提速。

行为约定：
  - 只缓存「无 error 字段 + works 非空」的 payload；失败一律不缓存。
  - TTL 默认 24h；环境变量 META_CACHE_TTL（秒）或 CLI --cache-ttl 可覆盖；
    环境变量 META_NO_CACHE=1 整体停用。
  - 跨进程安全：落盘用 tmp + os.replace，读每次重读文件。
  - 容量兜底：条目数超 _MAX_ENTRIES 时先清过期、再按 cached_at 淘汰最旧。
  - 与 _dedup_* 互补：_dedup 防 300s 内 burst 重试（内存+磁盘），本模块防
    跨运行重复检索（磁盘，24h）。两层可叠加，_dedup 命中时不触盘。
"""
import hashlib
import json
import os
import tempfile
import time

DEFAULT_TTL = 24 * 3600
_SCHEMA = "v1"
_MAX_ENTRIES = 200

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".search_cache")
CACHE_DIR = os.environ.get("META_CACHE_DIR", _DEFAULT_DIR)
CACHE_FILE = os.path.join(CACHE_DIR, "entries.json")


def _ttl(ttl=None):
    if ttl is not None and int(ttl) > 0:
        return int(ttl)
    try:
        return max(1, int(os.environ.get("META_CACHE_TTL", "") or DEFAULT_TTL))
    except (TypeError, ValueError):
        return DEFAULT_TTL


def disabled():
    return os.environ.get("META_NO_CACHE", "").strip().lower() in ("1", "true", "yes", "on")


def cache_key(source, keyword, year_from=None, year_to=None, max_results=50):
    payload = [
        _SCHEMA,
        str(source or ""),
        str(keyword or "").strip().lower(),
        "" if year_from is None else str(year_from),
        "" if year_to is None else str(year_to),
        int(max_results or 0),
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def load(cache_file=None, key=None, ttl=None):
    if disabled():
        return None
    cf = cache_file or CACHE_FILE
    try:
        if not os.path.exists(cf):
            return None
        with open(cf, "r", encoding="utf-8") as f:
            data = json.load(f)
        if _SCHEMA != data.get("schema"):
            return None
        entry = (data.get("entries") or {}).get(key)
        if not isinstance(entry, dict):
            return None
        if time.time() - float(entry.get("cached_at", 0)) > _ttl(ttl):
            return None
        p = entry.get("payload")
        if not isinstance(p, dict) or p.get("error") or not p.get("works"):
            return None
        return json.loads(json.dumps(p, ensure_ascii=False))
    except Exception:
        return None


def save(cache_file=None, key=None, payload=None):
    if disabled():
        return False
    if not isinstance(payload, dict) or payload.get("error") or not payload.get("works"):
        return False
    cf = cache_file or CACHE_FILE
    try:
        data = {"schema": _SCHEMA, "entries": {}}
        if os.path.exists(cf):
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and isinstance(loaded.get("entries"), dict):
                    data = loaded
                    data.setdefault("schema", _SCHEMA)
            except Exception:
                pass
        entries = data["entries"]
        # 容量兜底
        if len(entries) >= _MAX_ENTRIES:
            now = time.time()
            t = _ttl()
            entries = {k: v for k, v in entries.items()
                       if isinstance(v, dict) and now - float(v.get("cached_at", 0)) <= t}
            if len(entries) >= _MAX_ENTRIES:
                keep = sorted(entries.items(),
                              key=lambda kv: float(kv[1].get("cached_at", 0)),
                              reverse=True)[:_MAX_ENTRIES - 1]
                entries = dict(keep)
            data["entries"] = entries
        entries[key] = {"cached_at": time.time(), "payload": payload}
        # 原子写
        d = os.path.dirname(os.path.abspath(cf))
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, cf)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    _f = os.path.join(tempfile.gettempdir(), "_meta_cache_selftest.json")
    for p in (_f,):
        if os.path.exists(p):
            os.unlink(p)
    k = cache_key("europepmc", "PD-1 NSCLC", year_from=2020, max_results=10)
    payload = {"source": "europepmc", "works": [{"title": "t"}], "count": 1, "error": None}
    assert save(_f, k, payload) is True
    assert load(_f, k) == payload, "TTL 内应命中"
    assert load(_f, "no-such-key") is None, "未知键不命中"
    assert save(_f, "k2", {"error": "boom"}) is False, "error payload 不写"
    assert save(_f, "k3", {"works": []}) is False, "空 works 不写"
    os.environ["META_NO_CACHE"] = "1"
    assert load(_f, k) is None, "停用后不读"
    assert save(_f, k, payload) is False, "停用后不写"
    os.environ["META_NO_CACHE"] = "0"
    assert load(_f, k) == payload, "恢复后命中"
    os.unlink(_f)
    print("search_cache selftest: ALL PASSED")
