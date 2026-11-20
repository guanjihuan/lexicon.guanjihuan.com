#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十轮：给新增的学术常用副词/连词补台账裁定（core_decisions.json）。

⚠️ 留档脚本：本脚本按**显式词表**写台账（CORE/NONCORE 字典），重跑幂等；
但会用脚本里的旧值**覆盖**台账中同名词形的现裁定——若台账后来人工改过这批词，
重跑等于回滚。裁定修改请直接编辑 data/core_decisions.json（唯一事实源），
本文件只作第六十轮的留档。

判据沿用册四十一轮「仅硬证据入核」口径：
  core    = 论证骨架词 / 连接语块 / 学术维度副词 / 方法报告副词 / 正式学术连词
  noncore = 通用高频但学术不承载论证功能者（与 generally/quickly/closely 同档）
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'data', 'core_decisions.json')

CORE = {
    # 论证骨架 / 强调权重
    "especially": "高频强调副词",
    "fundamentally": "论证骨架词，论点层面",
    "crucially": "论证骨架词",
    "importantly": "骨架副词，点名论点权重",
    "highly": "程度副词学术搭配高频",
    "thoroughly": "方法程度副词学术搭配高频",
    # 方法 / 报告副词
    "extensively": "研究范围副词学术高频",
    "systematically": "方法论副词学术骨架",
    "rigorously": "方法论副词学术骨架",
    "accurately": "方法报告副词学术骨架",
    "efficiently": "方法报告副词学术骨架",
    "reliably": "方法报告副词学术骨架",
    "genuinely": "真实性限定副词学术高频",
    "independently": "研究独立性副词学术高频",
    # 学术维度副词
    "universally": "全称限定副词学术高频",
    "globally": "全球尺度副词学术高频",
    "politically": "维度副词学术高频",
    "socially": "维度副词学术高频",
    "historically": "历史维度副词学术高频",
    "culturally": "文化维度副词学术高频",
    "technically": "维度副词学术高频",
    "theoretically": "理论层面副词学术高频",
    "mathematically": "数学层面副词学术高频",
    "logically": "逻辑层面副词学术高频",
    "economically": "维度副词学术高频",
    "critically": "批判性副词学术高频",
    # 时间 / 行为特征副词
    "previously": "AWL词族",
    "continuously": "持续性副词学术高频",
    "intermittently": "间断性副词学术高频",
    "intentionally": "意图副词学术高频",
    "voluntarily": "受试者特征副词学术高频",
    "spontaneously": "行为特征副词学术高频",
    "indefinitely": "时间范围副词学术高频",
    "temporarily": "时间范围副词学术高频",
    # 连接语块 / 正式连词
    "as well": "累加连接语块",
    "as well as": "累加连接语块高频",
    "as far as": "限定连接语块，学术常用",
    "in order that": "正式目的连词，学术书面高频",
    "lest": "正式目的连词，学术书面高频",
}

NONCORE = {
    # 通用频率 / 程度 / 时间副词
    "scarcely": "通用高频频率副词",
    "hardly": "通用高频频率副词",
    "seldom": "通用高频频率副词",
    "chiefly": "通用高频程度副词",
    "marginally": "通用高频程度副词",
    "slightly": "通用高频程度副词",
    "vastly": "通用高频程度副词",
    "infinitely": "通用高频程度副词",
    "equally": "通用高频程度副词",
    "uniquely": "通用高频程度副词",
    "nearly": "通用高频程度副词",
    "almost": "通用高频程度副词",
    "fully": "通用高频程度副词",
    "entirely": "通用高频程度副词",
    "completely": "通用高频程度副词",
    "totally": "通用高频程度副词",
    "partially": "通用高频程度副词",
    "minimally": "通用高频程度副词",
    "broadly": "概括副词，与 generally 同档",
    "successfully": "通用高频结果副词",
    "immediately": "通用高频时间副词",
    "already": "通用高频时间副词",
    "suddenly": "通用高频时间副词",
    "slowly": "通用高频时间副词",
    "beforehand": "通用高频时间副词",
    "afterwards": "通用高频时间副词",
    "once": "通用高频时间副词",
    "altogether": "通用高频程度副词",
    "certainly": "通用高频确信副词",
    "definitely": "通用高频确信副词",
    "even": "通用高频程度副词",
    "rather": "通用高频程度副词",
    "finally": "篇章收束标记",
    "at least": "数量限定语块，通用",
    "at most": "数量限定语块，通用",
    "on the contrary": "对比语块，正对为 by contrast/in contrast",
    "above all": "强调语块，通用",
    "after all": "收束语块，通用",
    # 通用连接词
    "if": "通用高频条件连词，书面正对为 provided that/unless",
    "than": "通用高频比较连词",
    "as": "通用高频连接词",
    "then": "通用高频连接副词",
    "when": "通用高频时间连词",
    "whenever": "通用高频时间连词",
    "wherever": "通用高频地点连词",
    "whichever": "通用高频选择连词",
    "whatever": "通用高频让步连词",
    "whoever": "通用高频让步连词",
    "nor": "通用高频并列连词",
    "neither": "通用高频并列连词",
    "as if": "通用方式从句连接",
    "no matter": "通用让步语块，书面正对为 regardless of",
    "even so": "通用让步语块",
    "in case": "目的语块，日常语域",
    "now that": "通用时间连词",
    "as soon as": "通用时间连接语块",
    "supposing": "假设连词，日常语域",
    "assuming": "假设连词，日常语域",
}


def main():
    with open(P, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']
    words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))
    have = {w['word'] for w in words}

    overlap = set(CORE) & set(NONCORE)
    assert not overlap, overlap
    missing = (set(CORE) | set(NONCORE)) - have
    assert not missing, '台账词形不在词表: %s' % sorted(missing)

    for w, r in CORE.items():
        dec[w] = {'verdict': 'core', 'reason': r}
    for w, r in NONCORE.items():
        dec[w] = {'verdict': 'noncore', 'reason': r}

    led['decisions'] = dec
    n_core = sum(1 for d in dec.values() if d['verdict'] == 'core')
    led['_meta']['total'] = len(words)
    led['_meta']['final_core'] = n_core
    tmp = P + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    os.replace(tmp, P)
    print('ledger: %d decisions / %d words, core=%d (%.1f%%)'
          % (len(dec), len(words), n_core, 100.0 * n_core / len(words)))


if __name__ == '__main__':
    main()
