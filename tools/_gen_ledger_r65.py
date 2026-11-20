#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十五轮（日常连接词批）核心层裁定的**留档副本**。

⚠️ 一次性脚本，**不要重跑**：本脚本按 `cur['add'][-34:]` 取当批词，而 add 段尾数会
随下一轮增补前移 ⇒ 重跑会把别的批次词当成本批、断言失败或静默写坏台账。
实测教训见记忆条目「核心层台账生成器是一次性的」。

**要改某个词的裁定（verdict/reason），直接编辑 `data/core_decisions.json`**（唯一事实源），
再跑 `tools/_gen_core.py` → `tools/curate.py`；本文件只作留档。
本轮 34 条裁定已由属主**直接写入台账**（core 5 / noncore 29），核心层 875 → 880（48.4%）。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'data', 'core_decisions.json')

CORE = {'needless to say': '不言而喻标记，论证高频', 'to that end': '目的论证语块，学术书面高频', 'in the context of': '语境限定语块，连接语块同族', 'in relation to': '关系限定语块，连接语块同族', 'for the purposes of': '限定语块，连接语块同族'}

NONCORE = {'it goes without saying': '日常不言而喻标记，通用', 'to put it another way': '日常改述标记，通用', 'put differently': '日常改述标记，通用', 'in simple terms': '日常通俗化标记，通用', 'as follows': '日常引出标记，通用', 'first and foremost': '论述展开短语，通用', 'last but not least': '论述展开短语，通用', 'at the same time': '日常时间/转折短语，通用', 'for that matter': '日常插话短语，通用', 'on that note': '日常插话短语，通用', 'in this vein': '日常思路延续短语，通用', 'all things considered': '日常权衡短语，通用', 'in no small measure': '日常程度强调短语，通用', 'at any cost': '日常固定短语，通用', 'as it stands': '日常状态短语，通用', 'for the time being': '日常时间短语，通用', 'in the interim': '日常时间短语，通用', 'from now on': '日常时间短语，通用', 'in no way': '日常否定短语，通用', 'to no avail': '日常固定短语，通用', 'at the outset': '日常时间短语，通用', 'anyhow': '日常连接副词，通用', 'in connection with': '介词性固定语块（NO_POS）', 'as regards': '介词性固定语块（NO_POS）', 'aside from': '介词性固定语块（NO_POS）', 'in place of': '介词性固定语块（NO_POS）', 'for the purpose of': '介词性固定语块（NO_POS）', 'in pursuit of': '介词性固定语块（NO_POS）', 'in the absence of': '介词性固定语块（NO_POS）'}


def main():
    """留档用：真要落库请先读上面的告警。"""
    led = json.load(open(P, encoding='utf-8'))
    dec = led['decisions']
    cur = json.load(open(os.path.join(ROOT, 'data', 'curation.json'), encoding='utf-8'))
    batch = [a['word'] for a in cur['add'][-34:]]
    missing = (set(CORE) | set(NONCORE)) - set(batch)
    if missing:
        raise SystemExit('本批词表已前移，本脚本不可重跑：%s' % sorted(missing))
    for w in batch:
        dec[w] = {'verdict': 'core', 'reason': CORE[w]} if w in CORE             else {'verdict': 'noncore', 'reason': NONCORE[w]}
    led['decisions'] = dec
    words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))
    n_core = sum(1 for v in dec.values() if v['verdict'] == 'core')
    led['_meta']['total'] = len(words)
    led['_meta']['final_core'] = n_core
    tmp = P + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    os.replace(tmp, P)
    print('ledger core %d / %d (%.1f%%)' % (n_core, len(words), 100.0 * n_core / len(words)))


if __name__ == '__main__':
    main()
