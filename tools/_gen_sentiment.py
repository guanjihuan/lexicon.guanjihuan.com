#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off generator: writes the "sentiment" segment into data/curation.json.

第七十轮新增的两维（感情色彩 sub / 语体色彩 reg）—— 唯一事实来源 =
**data/sentiment_decisions.json 逐词台账**（每词 {"sub":…,"reg":…,
"reason":…,"reg_reason":…}；reason 是感情色彩理由，reg_reason 是语体理由）。
本脚本把台账翻译成 curation 段，**整体覆盖** sentiment 段（与 _gen_additions/
_gen_recat/_gen_core 同规：直接手改这段会被下次重跑抹掉，要改裁定请改台账再重跑
本脚本）。

判准见 tools/_audit/sentiment_criteria.md。

台账语义：
  * 台账里有这个词 → 它的 sub/reg 就是台账写的值（显式裁定）；
  * 台账里没有这个词 → 形容词/名词/动词的 sub 取「中性的」，全库的 reg 取「中性」。
    （台账只收「有话可说」的词：带评价色彩的词 ＋ 上一轮带标签而本轮被改判的词；
      中性是正当结论，不必逐词留档。）

守卫：
  * 台账引用的词形必须存在于当前词表（已删/改名的词形直接 fail）；
  * 上一轮带非中性标签的词，**必须**在本台账里显式出现 —— 否则它会被默认值
    静默改判成「中性的」，等于有人偷偷翻案（第五十五节那种「静默换口径」的病）；
  * 每条裁定必须有 reason；带 reg 的裁定还必须有独立的 reg_reason。

Run:  python3 tools/_gen_sentiment.py
"""
import collections
import hashlib
import json
import os
import sys

# 严格 JSON 读取：重复键必须报错（标准库会静默覆盖，人写的 JSON 易踩）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json, require_curation_segments  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

SUB_VALS = ('积极的', '消极的', '争议性的', '中性的')
REG_VALS = ('学术术语', '书面语', '口语', '中性')
SUB_POS = ('形容词', '名词', '动词')

cur = load_json(D('data', 'curation.json'))
require_curation_segments(cur, ('add', 'fix'))
words = load_json(D('data', 'words.json'))
led = load_json(D('data', 'sentiment_decisions.json'))
decisions = led['decisions']

head = {w['word']: w for w in words}
extra = sorted(set(decisions) - set(head))
if extra:
    raise SystemExit('sentiment_decisions 引用失踪词形(已删/改名?): %s' % extra)

bad_sub, bad_reg, bad_reason, bad_reg_reason = [], [], [], []
for wt, d in decisions.items():
    if not isinstance(d, dict):
        raise SystemExit('台账里 %r 的值必须是对象，实际是 %s' % (wt, type(d).__name__))
    if 'sub' in d and d['sub'] not in SUB_VALS:
        bad_sub.append((wt, d['sub']))
    if 'reg' in d and d['reg'] not in REG_VALS:
        bad_reg.append((wt, d['reg']))
    if not str(d.get('reason', '')).strip():
        bad_reason.append(wt)
    # 感情与语体是两个独立判断：理由不能共用。否则改 reg 后可能留下
    # 「标签是书面语、理由却说它是统计学术语」的自相矛盾台账。
    if 'reg' in d and not str(d.get('reg_reason', '')).strip():
        bad_reg_reason.append(wt)
if bad_sub:
    raise SystemExit('台账里 sub 不合法: %s' % bad_sub)
if bad_reg:
    raise SystemExit('台账里 reg 不合法: %s' % bad_reg)
if bad_reason:
    raise SystemExit('台账缺理由(每条裁定必须一行判据说明): %s' % bad_reason)
if bad_reg_reason:
    raise SystemExit('带 reg 的裁定缺 reg_reason（语体理由必须独立于感情理由）: %s'
                     % bad_reg_reason)

# 守卫：上一轮带非中性标签的词必须在本台账里显式出现（不许静默改判）
prev_valenced = {w['word'] for w in words
                 if w.get('pos') in SUB_POS and w.get('sub') not in (None, '中性的')}
silent = sorted(prev_valenced - set(decisions))
if silent:
    raise SystemExit('这些词上一轮带非中性标签，本台账却没有显式裁定 —— '
                     '不许静默改判为「中性的」，请补裁定或改判为「中性的」并写理由: %s'
                     % silent)

# 语体维同理：撤掉术语/书面语/口语标签时，必须在台账里显式写 reg='中性'
# 并留 reg_reason；省略 reg 是「沿用默认」，不能兼任「明确降级」。
prev_registered = {w['word'] for w in words if w.get('reg') not in (None, '中性')}
silent_reg = sorted(w for w in prev_registered if 'reg' not in decisions.get(w, {}))
if silent_reg:
    raise SystemExit('这些词上一轮带语体标签，本台账却省略了 reg —— '
                     '不许静默改判为「中性」，请显式写 reg=中性 并留 reg_reason: %s'
                     % silent_reg)

seg = {}
for wt, d in decisions.items():
    e = {}
    if 'sub' in d:
        e['sub'] = d['sub']
    if 'reg' in d:
        e['reg'] = d['reg']
    seg[wt] = e
cur['sentiment'] = seg
with open(D('data', 'curation.json') + '.tmp', 'w', encoding='utf-8') as f:   # v36-④(册四十九): tmp+os.replace 原子写
    json.dump(cur, f, ensure_ascii=False, indent=1)   # 与仓库既有格式一致（四十六轮口径）
    f.write('\n')
os.replace(D('data', 'curation.json') + '.tmp', D('data', 'curation.json'))

by_sub = collections.Counter(e.get('sub') for e in seg.values() if 'sub' in e)
by_reg = collections.Counter(e.get('reg') for e in seg.values() if 'reg' in e)
print('sentiment segment rows: %d' % len(seg))
print('  sub: %s' % dict(by_sub))
print('  reg: %s' % dict(by_reg))
print('ledger sha256[:16]=%s'
      % hashlib.sha256(open(D('data', 'sentiment_decisions.json'), 'rb').read()).hexdigest()[:16])
