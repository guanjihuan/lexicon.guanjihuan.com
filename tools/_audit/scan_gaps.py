#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词汇增补轮的**族级查重扫描器**（只读、不写数据产物）。

用途：每轮扫描代理报上来的候选词，都要过这道闸才准进候选表——
库内按**词族**判重（派生形已覆盖 ⇒ 词头不算缺口），并核
`data/curation.json` 的 remove 段（刻意删过的词不重提）。

用法:
  python3 tools/_audit/scan_gaps.py candidates.json      # 候选表 → 逐条判定
  python3 tools/_audit/scan_gaps.py --words a b c         # 直接查词

判定口径（与 core_audit.py 的 fam_match 同源，避免两处口径打架）：
  * 词族命中 = 库内存在同词头，或库内某词是本词的派生形（后缀剥除后同词干）
  * 多词语块按整串精确匹配（库内已有该语块 ⇒ 不算缺口）

输出：
  [GAP]      真缺口，可进候选表
  [FAMILY]   族内已覆盖（列出命中的库内词形）
  [IN-LIB]   词头本身已在库
  [REMOVED]  在 remove 段，本库刻意删过
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = lambda *p: os.path.join(ROOT, *p)

# 常见派生后缀（与 core_audit.py SUFFIXES 同规）
SUFFIXES = ("ations", "ities", "ments", "ness", "ions", "ion", "ies",
            "ied", "ing", "ers", "ist", "ism", "ed", "es", "al", "ly", "s")
# 常见不规则复数/派生形 → 词头
IRREGULAR = {
    "analyses": "analyse", "analysis": "analyse", "hypotheses": "hypothesis",
    "theses": "thesis", "crises": "crisis", "criteria": "criterion",
    "phenomena": "phenomenon", "indices": "index", "matrices": "matrix",
    "appendices": "appendix", "formulas": "formula", "stimuli": "stimulus",
    "syntheses": "synthesis", "bases": "basis", "axes": "axis",
    "data": "datum", "formats": "format", "media": "medium",
}


def norm(w):
    return w.strip().lower()


def heads(word):
    """一个词形可能对应的全部词头（含本词、剥后缀形、不规则形）。"""
    w = norm(word)
    out = {w}
    if w in IRREGULAR:
        out.add(IRREGULAR[w])
    for suf in SUFFIXES:
        if len(w) > len(suf) + 3 and w.endswith(suf):
            stem = w[:-len(suf)]
            out.add(stem)
            out.add(stem + "e")
            if stem.endswith("i"):
                out.add(stem[:-1] + "y")
    return out


def main():
    args = sys.argv[1:]
    words = json.load(open(D('data', 'words.json'), encoding='utf-8'))
    lib = {norm(w['word']) for w in words}
    cur = json.load(open(D('data', 'curation.json'), encoding='utf-8'))
    removed = {norm(r) for r in cur.get('remove', [])}

    if args and args[0] == '--words':
        cands = args[1:]
    elif args:
        path = args[0]
        obj = json.load(open(path if os.path.isabs(path) else D('tools', '_audit', path),
                             encoding='utf-8'))
        cands = [c['word'] if isinstance(c, dict) else c
                 for c in (obj.get('candidates') if isinstance(obj, dict) else obj)]
    else:
        print(__doc__)
        return

    gaps, fams, inlib, rem = [], [], [], []
    for c in cands:
        w = norm(c)
        if w in removed:
            rem.append(c)
            continue
        if w in lib:
            inlib.append(c)
            continue
        hit = sorted(x for x in lib if x in heads(c) or heads(c) & heads(x))
        if hit:
            fams.append((c, hit[:5]))
        else:
            gaps.append(c)

    print('=== GAP %d ===' % len(gaps))
    for g in gaps:
        print('  ', g)
    print('=== FAMILY-COVERED %d ===' % len(fams))
    for c, h in fams:
        print('  %-24s ~ %s' % (c, ', '.join(h)))
    if inlib:
        print('=== IN-LIB %d ===' % len(inlib))
        for c in inlib:
            print('  ', c)
    if rem:
        print('=== REMOVED %d ===' % len(rem))
        for c in rem:
            print('  ', c)


if __name__ == '__main__':
    main()
