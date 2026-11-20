#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十四轮：给新增的 34 个日常高频连词/连接词补台账裁定（core_decisions.json）。

⚠️ 一次性脚本，**不要重跑**：本脚本按 `cur['add'][-34:]` 取当批词，而 add 段尾数
会随后续增补轮前移 ⇒ 重跑会把别的批次词当成本批、断言失败或静默写坏台账
（实测教训见记忆条目「核心层台账生成器是一次性的」）。
要改某个词的裁定（verdict/reason），直接编辑 data/core_decisions.json（唯一事实源）。

判据沿用册四十一轮「仅硬证据入核」：
  core    = 承载论证/篇章功能的连接词（让步转折标记、前提连接词）
  noncore = 日常基础连接与通用话语连接词（口语性并列/时间/收束/插话类）
  介词性固定语块沿用第六十二、三轮口径：置 null 且不入核
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'data', 'core_decisions.json')

CORE = {
    "that being so": "让步转折标记",
    "all the same": "让步转折标记",
    "admittedly": "承认性让步标记",
    "considering that": "前提连接词，引导原因从句",
}

NONCORE = {
    # 日常基础连接
    "before": "日常时间连词，通用",
    "after": "日常时间连词，通用",
    "till": "日常时间连词，通用",
    "barring": "日常排除连词，通用",
    # 话语连接副词
    "still": "日常连接副词，通用",
    "well": "日常连接副词，通用",
    "anyway": "日常连接副词，通用",
    "of course": "日常连接副词，通用",
    "at any rate": "日常收束短语，通用",
    "in any event": "日常收束短语，通用",
    "on balance": "日常概括短语，通用",
    "all in all": "日常概括短语，通用",
    "in the main": "日常概括短语，通用",
    "for the most part": "日常概括短语，通用",
    "in the first place": "论述展开短语，通用",
    "at last": "日常时间连接词，通用",
    "in the end": "日常时间连接词，通用",
    "sooner or later": "日常时间连接词，通用",
    "in the long run": "日常时间连接词，通用",
    "by the way": "日常插话短语，通用",
    "by all means": "日常请求短语，通用",
    "in which case": "日常条件连接词，通用",
    "in that case": "日常条件连接词，通用",
    "in so doing": "日常指代短语，通用",
    # 介词性固定语块（NO_POS，沿用第六十二、三轮口径）
    "thanks to": "介词性固定语块（NO_POS）",
    "because of": "介词性固定语块（NO_POS）",
    "for fear that": "恐慎目的连词，书面频率低",
    "to the end that": "目的连词，书面频率低",
    "with a view to": "介词性固定语块（NO_POS）",
    "with the aim of": "介词性固定语块（NO_POS）",
}


def main():
    with open(P, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']

    cur = json.load(open(os.path.join(ROOT, 'data', 'curation.json'), encoding='utf-8'))
    batch = [a['word'] for a in cur['add'][-34:]]

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
