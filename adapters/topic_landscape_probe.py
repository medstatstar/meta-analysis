# -*- coding: utf-8 -*-
"""topic_landscape_probe.py — 选题证据地形实时探针（live Europe PMC）

用途（meta-analysis 技能 Topic track 的补充探针）：
  在 build_gap_probe.py 给出「窄方向 vs 宽泛父方向」比值之后，用本脚本
  进一步勘察某个临床方向的四层证据地形，避免只凭比值下结论：

    L1 缺口层   该人群是否已有 SR/MA（去重威胁）
    L2 原始层   该人群是否已有 RCT（可纳入研究数）
    L3 近邻层   与本选题最接近的已发表 Meta（须逐条比对增量）
    L4 试验层   关键 RCT 的标识与随访长度（增量证据来源）

同时可对指定 PMID/DOI 抓取摘要原文，用于判断近邻 Meta 是否已覆盖本选题。

用法
  python topic_landscape_probe.py --preset ckd-sglt2i
  python topic_landscape_probe.py --queries myquery.json
  python topic_landscape_probe.py --ids 41235415,42420866 --full

设计约束
  * 直连 Europe PMC REST，**不走 coze**（coze-only 规则只约束数值分析，
    文献探针属检索层，见 references/topic-selection.md「Topic Gating」）。
  * 不做分数判定、不做方向推荐——只产出真实 hit_count 与标题，
    由上层按 R7 规则自行排序（red line: 候选排序必须基于真实命中数）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

EPMC = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
UA = {'User-Agent': 'WorkBuddy-meta-analysis/1.0 (topic landscape probe)'}


def epmc(query: str, page_size: int = 25, result_type: str = 'core'):
    """查询 Europe PMC，返回 (hitCount, results)。"""
    url = EPMC + '?' + urllib.parse.urlencode({
        'query': query, 'format': 'json',
        'pageSize': page_size, 'resultType': result_type,
    })
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as fh:
        r = json.load(fh)
    return r.get('hitCount'), r.get('resultList', {}).get('result', [])


def journal_of(x: dict) -> str:
    j = ((x.get('journalInfo') or {}).get('journal') or {})
    return j.get('title') or ''


def show_hits(label: str, query: str, limit: int = 12, verbose: bool = True):
    try:
        hit, res = epmc(query, page_size=max(limit, 10))
    except Exception as exc:                       # 网络不可达 -> 显式报 unverified
        print('### %-26s ERROR  %s' % (label, exc))
        return None
    print('### %-26s HIT=%s' % (label, hit))
    if verbose:
        for x in res[:limit]:
            print('   | %s | %-100s | %s' % (
                x.get('pubYear'), (x.get('title') or '')[:100],
                journal_of(x)[:28]))
    print()
    return hit


def show_ids(ids: list[str]):
    """按 PMID / DOI 抓取摘要原文，用于近邻研究比对。"""
    for ident in ids:
        q = ('EXT_ID:%s' % ident) if ident.isdigit() else ('DOI:%s' % ident)
        try:
            hit, res = epmc(q, page_size=3)
        except Exception as exc:
            print('### %s ERROR %s\n' % (ident, exc))
            continue
        print('### %s  HIT=%s' % (ident, hit))
        for x in res[:2]:
            print('  TITLE  :', x.get('title'))
            print('  JOURNAL:', journal_of(x), '|', x.get('pubYear'),
                  '| PMID:', x.get('pmid'), '| DOI:', x.get('doi'))
            print('  ABSTRACT:',
                  (x.get('abstractText') or '(no abstract)')[:2500])
            print('  ' + '-' * 96)
        print()
        time.sleep(0.5)


# ---------------------------------------------------------------- presets
PRESETS = {
    'ckd-sglt2i': {
        'desc': 'SGLT2i x CKD：非糖尿病缺口 / 近邻 Meta / 关键试验',
        'layers': [
            ('L1_SRMA_nondiabetic',
             '(SGLT2 inhibitor OR dapagliflozin OR empagliflozin OR canagliflozin) '
             'AND ("non-diabetic" AND ("chronic kidney disease" OR nephropathy)) '
             'AND (PUB_TYPE:"meta-analysis" OR PUB_TYPE:"systematic review")'),
            ('L2_RCT_nondiabetic',
             '(SGLT2 inhibitor OR dapagliflozin OR empagliflozin OR canagliflozin) '
             'AND ("non-diabetic" AND ("chronic kidney disease" OR nephropathy)) '
             'AND (PUB_TYPE:"randomized controlled trial" OR PUB_TYPE:"Clinical Trial")'),
            ('L3_ethnicity_subgroups',
             '(SGLT2 inhibitor OR dapagliflozin OR empagliflozin) '
             'AND ("IgA nephropathy" OR "autosomal dominant polycystic kidney disease" '
             'OR "membranous nephropathy" OR "lupus nephritis" OR FSGS) '
             'AND (PUB_TYPE:"randomized controlled trial" OR PUB_TYPE:"Clinical Trial")'),
            ('L4_key_trials',
             '(DAPA-CKD OR EMPA-KIDNEY OR CREDENCE OR "EMPA-KIDNEY" '
             'OR "vertical" OR DELIVER OR DAPA-HF OR SOLOIST-WHF OR VERTIS) '
             'AND (PUB_TYPE:"randomized controlled trial")'),
        ],
        'ids': ['41235415', '42420866', '42145733', '39453837'],
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description='选题证据地形实时探针 (Europe PMC)')
    ap.add_argument('--preset', help='内置预设名，如 ckd-sglt2i')
    ap.add_argument('--queries', help='JSON 文件：{"label": "query", ...}')
    ap.add_argument('--ids', help='PMID（逗号分隔）或 DOI')
    ap.add_argument('--full', action='store_true', help='打印命中记录摘要原文')
    ap.add_argument('--limit', type=int, default=12, help='每层打印条数')
    ap.add_argument('--out', help='结果 JSON 输出路径')
    args = ap.parse_args()

    layers: dict[str, str] = {}
    if args.preset:
        if args.preset not in PRESETS:
            print('unknown preset: %s (available: %s)'
                  % (args.preset, ', '.join(PRESETS)), file=sys.stderr)
            return 2
        p = PRESETS[args.preset]
        layers.update(p['layers'])
        print('== preset: %s — %s ==\n' % (args.preset, p['desc']))
    if args.queries:
        with open(args.queries, encoding='utf-8') as fh:
            layers.update(json.load(fh))
    if not layers and not args.ids:
        ap.print_help()
        return 2

    result: dict[str, object] = {'preset': args.preset, 'layers': {}, 'ids': {}}

    for label, query in layers.items():
        hit = show_hits(label, query, limit=args.limit)
        result['layers'][label] = {'query': query, 'hit_count': hit}

    if args.ids:
        ids = [i.strip() for i in args.ids.split(',') if i.strip()]
        show_ids(ids)
        result['ids'] = ids

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print('[OK] wrote -> %s' % args.out)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
