#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十轮例句批次的机械自检器（写作代理与属主共用）。

用法: python3 tools/_r60_check.py data/examples_parts/part_r60_01.json [...]

判据（与 tools/content_test.py 同口径的子集，只读、不改文件）：
  ① 每词恰 3 条 {en, zh}；en/zh 非空
  ② en 以终止标点收尾；zh 以 。！？ 收尾；zh 句首无标点
  ③ zh 无半角 , ; : " ' ；无连续空格；无占位符（TODO/待补/XXX/… 等）
  ④ zh 括号配对（）（「」《》）
  ⑤ en 含该词（允许屈折变化，词干口径与 merge_examples 一致）
  ⑥ 同词 3 条 en/zh 互不相同
  ⑦ en 里的百分数与四位年份必须在 zh 里出现
"""
import sys as _sys
_sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else __file__.rsplit('/', 1)[0])
from _console_utf8 import force_utf8_console
force_utf8_console()
import json
import re
import sys


# ---- 词形匹配：与 tools/merge_examples.py 同口径（复制而非 import：
#      merge_examples 是脚本、import 即写盘，不能当库用） ----
# 粗词干器：剥常见后缀与双写辅音（与 merge_examples.stem 一致）
_SUFFIXES = ('ations', 'ation', 'ies', 'ied', 'ing', 'ies', 'ily', 'ally',
             'ed', 'es', 'al', 'ly', 's', 'ment', 'ness', 'ion', 'ive', 'al')


def _stem(w):
    s = w.lower()
    if len(s) <= 3:
        return s
    for suf in ('ations', 'ation', 'ies', 'ied', 'ing', 'ies', 'ily', 'ally'):
        if s.endswith(suf) and len(s) - len(suf) >= 3:
            s = s[:-len(suf)]
            if suf in ('ies', 'ied'):
                s += 'y'
            break
    else:
        for suf in _SUFFIXES:
            if s.endswith(suf) and len(s) - len(suf) >= 3:
                s = s[:-len(suf)]
                break
    if len(s) >= 3 and s[-1] == s[-2] and s[-1] not in 'aeiousl':
        s = s[:-1]
    return s


def _head_stems(word):
    heads = [w for w in re.split(r'[^a-z]+', word.lower()) if w]
    out = set()
    for h in heads:
        out.add(_stem(h))
        for suf in ('s', 'es', 'ed', 'ing', 'd'):
            if h.endswith(suf) and len(h) - len(suf) >= 3:
                out.add(_stem(h[:-len(suf)]))
    return out


def _contains_word(sentence, word):
    """句中是否用了该词（允许屈折变化；多词短语按整串或顺序匹配）。"""
    heads = [w for w in re.split(r'[^a-z]+', word.lower()) if w]
    if not heads:
        return False
    toks = [t for t in re.split(r'[^a-z]+', sentence.lower()) if t]
    if not toks:
        return False
    tok_stems = [_stem(t) for t in toks]
    target = _head_stems(word)
    n = len(heads)
    for i in range(len(toks) - n + 1):
        window = tok_stems[i:i + n]
        if all(any(w == ts or ts in w or w in ts for ts in target) for w in window):
            return True
    if n == 2:
        s0, s1 = _head_stems(heads[0]), _head_stems(heads[1])

        def match(tok, stems):
            ts = _stem(tok)
            return any(ts == s or ts in s or s in ts for s in stems)
        for i in range(len(toks)):
            if not match(toks[i], s0):
                continue
            for j in range(i + 1, len(toks)):
                if match(toks[j], s1):
                    return True
    return False

PLACEHOLDERS = ["TODO", "FIXME", "XXX", "待补", "待定", "占位", "？？", "??"]
ZH_END = re.compile(r"[。！？…]+[\"」』》）)\]]*$")
EN_END = re.compile(r"[.!?]+[\"')]*$")


def check(path):
    errs = []
    data = json.load(open(path, encoding='utf-8'))
    if not isinstance(data, dict):
        return ['%s: 顶层必须是对象' % path]
    for word, arr in data.items():
        if not isinstance(arr, list) or len(arr) != 3:
            errs.append('%s: 例句数 %s（要 3）' % (word, len(arr) if isinstance(arr, list) else type(arr).__name__))
            continue
        ens, zhs = [], []
        for i, e in enumerate(arr):
            en = (e.get('en') or '').strip()
            zh = (e.get('zh') or '').strip()
            if not en or not zh:
                errs.append('%s[%d]: en/zh 有空' % (word, i))
                continue
            ens.append(en); zhs.append(zh)
            if not EN_END.search(en):
                errs.append('%s[%d]: en 未以终止标点收尾: %s' % (word, i, en))
            if not ZH_END.search(zh):
                errs.append('%s[%d]: zh 未以终止标点收尾: %s' % (word, i, zh))
            if zh[0] in '，。；：、）】」』':
                errs.append('%s[%d]: zh 句首有标点' % (word, i))
            if re.search(r'[,;:]', zh):
                errs.append('%s[%d]: zh 含半角 , ; :' % (word, i))
            if '"' in zh or "'" in zh:
                errs.append('%s[%d]: zh 含半角引号' % (word, i))
            if '  ' in zh:
                errs.append('%s[%d]: zh 含连续空格' % (word, i))
            if any(p in zh for p in PLACEHOLDERS):
                errs.append('%s[%d]: zh 含占位符' % (word, i))
            for a, b in (('（', '）'), ('「', '」'), ('《', '》')):
                if zh.count(a) != zh.count(b):
                    errs.append('%s[%d]: zh 括号不配对' % (word, i))
            if not _contains_word(en, word):
                errs.append('%s[%d]: en 未含该词: %s' % (word, i, en))
            for m in re.finditer(r'(\d+(?:\.\d+)?)\s*%', en):
                if m.group(1) not in zh:
                    errs.append('%s[%d]: 百分数 %s 未在 zh 出现' % (word, i, m.group(1)))
            for m in re.finditer(r'\b(1[89]\d{2}|20\d{2})\b', en):
                if m.group(1) not in zh:
                    errs.append('%s[%d]: 年份 %s 未在 zh 出现' % (word, i, m.group(1)))
        if len(set(ens)) != len(ens):
            errs.append('%s: 3 条 en 互不相同失败' % word)
        if len(set(zhs)) != len(zhs):
            errs.append('%s: 3 条 zh 互不相同失败' % word)
    return errs


def main():
    bad = 0
    for path in sys.argv[1:]:
        errs = check(path)
        n = len(json.load(open(path, encoding='utf-8')))
        if errs:
            bad += len(errs)
            print('FAIL %s (%d 词)' % (path, n))
            for e in errs:
                print('  -', e)
        else:
            print('OK   %s (%d 词)' % (path, n))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
