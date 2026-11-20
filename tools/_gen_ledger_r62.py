#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十二轮：给新增的 31 个学术连词／连接语块补台账裁定（core_decisions.json）。

⚠️ 一次性脚本，**不要重跑**：本脚本按 `cur['add'][-31:]` 取当批词，而 add 段尾数
会随后续增补轮前移 ⇒ 重跑会把别的批次词当成本批、断言失败或静默写坏台账
（实测教训见记忆条目「核心层台账生成器是一次性的」）。
要改某个词的裁定（verdict/reason），直接编辑 data/core_decisions.json（唯一事实源）。

判据沿用册四十一轮「仅硬证据入核」：
  core    = 承载论证功能的连词与连接标记（前提、条件、让步、限定、举例、递进）
  noncore = 基础并列连接（and/or）、收束/提示类副词短语、介词性固定语块
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'data', 'core_decisions.json')

CORE = {
    # 论证连接词：前提与条件
    "given": "前提连接词，学术论证高频",
    "on the assumption that": "前提连接语块，论证设限",
    "on condition that": "条件连接语块，论证设限",
    "in the event that": "条件连接语块，正式论证语域",
    "so long as": "条件连接语块，论证设限",
    "even when": "让步连接语块，论证设限",
    # 论证连接词：方式与限定
    "as though": "方式连接词，论证让步于假设",
    "other than": "排除对比语块，论证设限",
    "to the extent that": "程度限定连接语块",
    "in the sense that": "意义限定连接语块",
    # 连接标记：递进 / 转折 / 举例 / 论证方法
    "not only": "递进连接标记",
    "by the same token": "递进连接标记",
    "that said": "转折让步标记",
    "by analogy": "论证方法标记",
    "as a case in point": "举例论证标记",
}

NONCORE = {
    "and": "基础并列连词，不承载论证功能",
    "or": "基础选择连词，不承载论证功能",
    "except that": "排除从句连接，书面频率低",
    "in any case": "收束标记，通用",
    "on the whole": "概括标记，通用",
    "with this in mind": "提示短语，通用",
    "of note": "提示短语，通用",
    "in the meantime": "时间副词短语，通用",
    "by chance": "偶然副词短语，通用",
    "in order to": "介词性固定语块（NO_POS）",
    "in spite of": "介词性固定语块（NO_POS）",
    "on behalf of": "介词性固定语块（NO_POS）",
    "for the sake of": "介词性固定语块（NO_POS）",
    "at the expense of": "介词性固定语块（NO_POS）",
    "in lieu of": "介词性固定语块（NO_POS）",
    "by virtue of": "介词性固定语块（NO_POS）",
}


def main():
    with open(P, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']

    cur = json.load(open(os.path.join(ROOT, 'data', 'curation.json'), encoding='utf-8'))
    batch = [a['word'] for a in cur['add'][-31:]]

    missing = set(CORE) | set(NONCORE)
    missing -= set(batch)
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
