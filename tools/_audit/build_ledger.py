#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把子代理的逐词初判 + 属主复核改判汇成 data/sentiment_decisions.json 台账。

判准见 tools/_audit/sentiment_criteria.md。
本脚本是**汇总器**，不是真源：台账落盘后要改裁定，直接编辑
data/sentiment_decisions.json（与 core_decisions.json 同规矩），本脚本不重跑。

⚠️ 一次性脚本，**不要重跑**：它按当时的子代理初判文件整体重写
`data/sentiment_decisions.json`，而后续各轮的裁定是**直接编辑台账**落下的，
不在本脚本的输入里 ⇒ 重跑会用旧初判覆盖后续裁定，静默写坏台账。
要改裁定，直接编辑 data/sentiment_decisions.json（唯一事实源），
再跑 tools/_gen_sentiment.py 把台账落进 curation.json 的 sentiment 段。
（同类教训见记忆条目「核心层台账生成器是一次性的」。）

三处属主复核改判（覆盖子代理初判，理由见各行注释）：
  * intricate      消极的 → 中性的（三条例句全是「错综复杂/复杂」的中性描述，与 complex 同档）
  * ad hoc         消极的 → 中性的（释义只有「特别的；专门的；临时安排的」，无贬义）
  * harvest        ? → 中性的（学术常用义是「收集数据」，中性）
「?」（子代理拿不准）的处置原则：按该词在学术散文里的**主导义**定；
  主导义与次要义评价相反且势均力敌的判「争议性的」；
  其余取「中性的」（默认，即不进台账）。

书面语一档另做一道机械收口：通用英语里随手可用的普通词不算「书面语」，
  哪怕它在学术文本里出现得多（如 distribution / threshold / density / feedback）。
  留下的要么是学科专门术语，要么是公文/学术固定语块与虚词。
"""
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = lambda *p: os.path.join(ROOT, *p)
SENT = D('tools', '_audit', 'sent_batches')
REG = D('tools', '_audit', 'reg_batches')

# ---------------------------------------------------------------- 属主复核改判
OVERRIDE = {
    # 词: (档位, 理由)
    'intricate': ('中性的', '三条例句均作「错综复杂/复杂」的中性描述，与 complex 同档'),
    'ad hoc': ('中性的', '释义为「特别的；专门的；临时安排的」，本身无贬义；判据须依本库释义'),
    'harvest': ('中性的', '学术常用义是「收集（信息、数据）」，中性；「收获/成果」是次要义'),
}
# 「?」逐词处置：显式给档位者按下列理由定档，其余取默认「中性的」（不进台账）
RESOLVE = {
    'oversight': ('争议性的', '两义评价相反：监管/监督（正面）与疏忽（贬义）'),
    'anomaly': ('争议性的', '既指数据缺陷（负），也可指引人注目的发现（正），评价两极'),
    'hierarchy': ('争议性的', '层级体系（中性结构）与等级制度（批判色彩）两读并存'),
    'surplus': ('争议性的', '贸易盈余（正）与过剩/多余（负）两读并存'),
    'skew': ('消极的', '数据偏斜是需修正的数据质量问题，词义自带偏差'),
    'plethora': ('中性的', '大量/充足，学术中多为中性计数'),
    'routine': ('中性的', '惯例、例行公事，学术中作中性描述'),
    'dichotomy': ('中性的', '二分法是中性分析工具'),
    'intervention': ('中性的', '干预/介入，学术语境中性'),
    'outlier': ('中性的', '离群值是统计描述'),
    'regression': ('中性的', '学术主导义是统计回归（中性）'),
    'incidence': ('中性的', '发生率是中性频率指标'),
    'narrative': ('中性的', '叙述/叙事，中性'),
    'periphery': ('中性的', '边缘/外围，描述性'),
    'concern': ('中性的', '所涉及的问题/关切，中性'),
    'exposure': ('中性的', '暴露/接触程度，中性计量义为主'),
    'tolerance': ('中性的', '耐受性与宽容两义，主导义中性'),
    'viability': ('中性的', '可行性/生存能力，学术中是评价指标而非褒义本身'),
    'stability': ('中性的', '稳定性，中性指标'),
    'variability': ('中性的', '变异性，中性指标'),
    'reputation': ('中性的', '声誉，褒贬依附所指对象'),
    'litigation': ('中性的', '诉讼，程序性中性'),
    'tariff': ('中性的', '关税/价目表，中性制度名词'),
    'subsidy': ('中性的', '补贴，学术中作中性政策工具'),
    'syndrome': ('中性的', '综合征，医学描述性用法'),
    # 动词
    'prevail': ('中性的', '占优势/盛行，事实描述'),
    'fulfill': ('中性的', '实现/履行，达成与否由宾语决定'),
    'dictate': ('中性的', '规定/决定，中性动作'),
    'tackle': ('中性的', '对付、处理，中性动作'),
    'reconcile': ('中性的', '调和/对账，中性动作'),
    'exploit': ('中性的', '本库释义为「利用；开发；发挥」，无贬义义项'),
    'discard': ('中性的', '丢弃/排除假设，学术常规操作'),
    'intervene': ('中性的', '干涉/调停，方向由语境定'),
    'reinforce': ('中性的', '强化/进一步证实，中性描述'),
    'speculate': ('中性的', '推测/推断，中性研究动作'),
    'debunk': ('中性的', '驳斥/揭穿，纠错动作，中性'),
    'leap': ('中性的', '飞跃/跳跃，学术多用「重大进展」但词义中性'),
    'unify': ('中性的', '整合/统一，中性动作'),
    'expose': ('中性的', '暴露/使接触，中性'),
    'resolve': ('中性的', '解决/化解，中性动作'),
    'obviate': ('中性的', '排除/使无必要，中性动作'),
    'disseminate': ('中性的', '传播，中性动作'),
    'extrapolate': ('中性的', '推断，方法性动作'),
    'uncover': ('中性的', '揭露/发现，方向由宾语定'),
    'diverge': ('中性的', '出现差异/分歧，中性描述'),
    'validate': ('中性的', '验证/证实，方法性步骤'),
    'support': ('中性的', '支持/支撑/证实，中性动作'),
    'contribute': ('中性的', '贡献/促成，机制描述'),
    'consume': ('中性的', '消耗/耗费，中性'),
    'justify': ('中性的', '提供理由，中性论证动作'),
    'substantiate': ('中性的', '用证据支持，方法性动作'),
    'enable': ('中性的', '使能够/使可能，方向由宾语定'),
    'enforce': ('中性的', '执行/强制推行，中性'),
    'preclude': ('中性的', '排除可能性，中性方法性动作'),
    'escalate': ('中性的', '升级/逐步扩大，中性'),
    'spiral': ('中性的', '螺旋式上升/下降，中性描述'),
    'intensify': ('中性的', '加强/加剧，方向由宾语定'),
    'withdraw': ('中性的', '撤回/退出，学术中多为程序动作'),
    'displace': ('中性的', '取代/挤出，中性动作'),
}

# 书面语收口：通用英语里随手可用的普通词，不算「书面语」（即便学术文本里常见）
REG_DROP = {
    'amenable', 'consent', 'well-defined', 'quantify', 'conservation', 'uniform', 'sparse',
    'formula', 'metaphor', 'adverse', 'statistical', 'penalty', 'entity', 'roadmap',
    'exponential', 'fraction', 'ratio', 'snapshot', 'cumulative', 'trait', 'comparative',
    'analogy', 'interface', 'repeatable', 'statistic', 'probability', 'bias', 'distribution',
    'threshold', 'register', 'sector', 'finance', 'legal', 'contract', 'density',
    'equilibrium', 'expenditure', 'feedback', 'index', 'motivation', 'productivity',
    'provision', 'recurrence', 'reinforcement', 'simulation', 'sufficiency', 'terminology',
    'transmission', 'variability', 'welfare', 'accountable', 'observable', 'recurrent',
    'journal', 'footnote', 'inflation', 'hierarchical', 'empirical', 'protocol', 'apparatus',
    'premise', 'entity', 'diverge', 'construct', 'corpus', 'incidence', 'intervention',
    'parameter', 'saturate', 'utilize', 'hence', 'thereby', 'bias', 'sector', 'legal',
    'index', 'welfare', 'connotation', 'surplus', 'journal', 'ideology', 'notwithstanding',
    'whereby', 'regime', 'ratio', 'stringent', 'qualitative', 'sampling',
}

REASON_FIX = {}   # 若需替换子代理的理由，写在这里


def load(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    words = load(D('data', 'words.json'))
    pos_of = {w['word']: (w.get('pos') or '') for w in words}
    known = set(pos_of)

    decisions = {}

    def put(word, sub=None, reg=None, reason=''):
        if word not in known:
            raise SystemExit('台账引用了词表里没有的词：%r' % word)
        e = decisions.setdefault(word, {})
        if sub:
            e['sub'] = sub
        if reg:
            e['reg'] = reg
        if reason:
            e['reason'] = reason
        elif 'reason' not in e:
            e['reason'] = '（未留理由）'

    # ---------------------------------------------------------------- 形容词：全量四档裁定
    for n in ('adj_1', 'adj_2'):
        for r in load(os.path.join(SENT, n + '.out.json')):
            w = r['word']
            if pos_of.get(w) != '形容词':
                raise SystemExit('%r 在本批里不是形容词' % w)
            sub, reason = OVERRIDE.get(w, (r['sub'], r['reason']))
            put(w, sub=sub, reason=REASON_FIX.get(w, reason))

    # ---------------------------------------------------------------- 名词/动词：只登记带评价色彩的裁定
    for n in ('noun_1', 'noun_2', 'verb_1', 'verb_2'):
        for r in load(os.path.join(SENT, n + '.out.json')):
            w = r['word']
            sub = r['sub']
            reason = r['reason']
            if sub == '?':
                if w not in RESOLVE:
                    continue          # 默认「中性的」＝不进台账
                sub, reason = RESOLVE[w]
            if sub == '中性的':
                continue
            put(w, sub=sub, reason=REASON_FIX.get(w, reason))

    # ---------------------------------------------------------------- 语体色彩
    reg_n = 0
    for n in ('reg_1', 'reg_2', 'reg_3'):
        for r in load(os.path.join(REG, n + '.out.json')):
            w = r['word']
            if r['reg'] == '书面语' and w in REG_DROP:
                continue
            put(w, reg=r['reg'], reason=REASON_FIX.get(w, r['reason']))
            reg_n += 1

    by_sub = collections.Counter(d.get('sub') for d in decisions.values() if 'sub' in d)
    by_reg = collections.Counter(d.get('reg') for d in decisions.values() if 'reg' in d)
    print('台账条目：%d' % len(decisions))
    print('  sub：%s' % dict(by_sub))
    print('  reg：%s' % dict(by_reg))

    ledger = {
        '_meta': {
            'purpose': '第七十轮：感情色彩（褒/贬/争议/中性）与语体色彩（书面语/口语/中性）逐词裁定台账。',
            'criteria': 'tools/_audit/sentiment_criteria.md',
            'coverage': ('形容词为全量逐词裁定（438 词，四档各留一行理由）；'
                         '名词/动词只登记带评价色彩的裁定，其余取默认「中性的」；'
                         '语体色彩只登记带语域印记的词，其余取默认「中性」。'),
            'not_in_ledger': ('形容词/名词/动词未出现在本台账者，感情色彩一律取「中性的」；'
                              '全库未出现在本台账者，语体色彩一律取「中性」。'),
            'note': '本文件是手改的真源；改裁定请直接编辑这里，再跑 tools/_gen_sentiment.py 落进 curation.json。',
        },
        'decisions': decisions,
    }
    out = D('data', 'sentiment_decisions.json')
    with io.open(out + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(out + '.tmp', out)
    print('wrote %s' % out)


if __name__ == '__main__':
    main()
