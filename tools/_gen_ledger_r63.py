#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十三轮：给新增的 38 个学术连接词/语块补台账裁定（core_decisions.json）。

⚠️ 一次性脚本，**不要重跑**：本脚本按 `cur['add'][-38:]` 取当批词，而 add 段尾数
会随后续增补轮前移 ⇒ 重跑会把别的批次词当成本批、断言失败或静默写坏台账
（实测教训见记忆条目「核心层台账生成器是一次性的」）。
要改某个词的裁定（verdict/reason），直接编辑 data/core_decisions.json（唯一事实源）。

判据沿用册四十一轮「仅硬证据入核」：
  core    = 承载论证/篇章功能的连接词与限定标记（精确化、枚举、界定、释义引出、
            酌情限定、总体等同）
  noncore = 基础关联词、通用收束与概括短语、介词性固定语块
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'data', 'core_decisions.json')

CORE = {
    # 关联与限定连接词
    "where": "关联限定连接词，学术高频",
    # 精确化与缓称标记
    "more precisely": "精确化限定标记",
    "more specifically": "精确化限定标记",
    "to be precise": "精确化限定标记",
    "to be sure": "承认性缓称标记",
    # 论证枚举标记
    "firstly": "论证枚举标记",
    "secondly": "论证枚举标记",
    "thirdly": "论证枚举标记",
    "lastly": "论证枚举标记",
    # 界定与实质限定
    "by definition": "界定性限定标记",
    "in essence": "本质限定标记",
    "in effect": "实质等同限定标记",
    "that is to say": "释义引出标记",
    # 酌情限定语块（学术语域专属）
    "where applicable": "酌情限定语块，学术语域专属",
    "where possible": "酌情限定语块，学术语域专属",
    "as appropriate": "酌情限定语块，学术语域专属",
}

NONCORE = {
    "both": "基础关联连词，不承载论证功能",
    "presuming": "假设连词，书面频率低",
    "if applicable": "酌情限定语块，通用",
    "where necessary": "酌情限定语块，通用",
    "if necessary": "酌情限定语块，通用",
    "first of all": "论述展开短语，通用",
    "to begin with": "论述展开短语，通用",
    "in sum": "收束标记，通用",
    "in all": "总体/总量限定短语，通用",
    "as a whole": "总体限定短语，通用",
    "by and large": "概括限定短语，通用",
    "to a certain extent": "程度限定短语，通用",
    "if anything": "让步修正短语，通用",
    "so as to": "介词性固定语块（NO_POS）",
    "with the exception of": "介词性固定语块（NO_POS）",
    "subject to": "介词性固定语块（NO_POS）",
    "on account of": "介词性固定语块（NO_POS）",
    "by reason of": "介词性固定语块（NO_POS）",
    "in favor of": "介词性固定语块（NO_POS）",
    "by reference to": "介词性固定语块（NO_POS）",
    "with reference to": "介词性固定语块（NO_POS）",
    "in the wake of": "介词性固定语块（NO_POS）",
}


def main():
    with open(P, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']

    cur = json.load(open(os.path.join(ROOT, 'data', 'curation.json'), encoding='utf-8'))
    batch = [a['word'] for a in cur['add'][-38:]]

    missing = (set(CORE) | set(NONCORE)) - set(batch)
    assert not missing, '裁定表与本批词表不符: %s' % sorted(missing)

    for w in batch:
        if w in CORE:
            dec[w] = {'verdict': 'core', 'reason': CORE[w]}
        else:
            dec[w] = {'verdict': 'noncore', 'reason': NONCORE[w]}

    led['decisions'] = dec
    words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))
    n_core = sum(1 for d in dec.values() if d['verdict'] == 'core')
    led['_meta']['total'] = len(words)
    led['_meta']['final_core'] = n_core
    tmp = P + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    os.replace(tmp, P)
    print('batch %d: core %d / noncore %d; ledger core %d / %d (%.1f%%)'
          % (len(batch), len(CORE), len(NONCORE), n_core, len(words),
             100.0 * n_core / len(words)))


if __name__ == '__main__':
    main()
