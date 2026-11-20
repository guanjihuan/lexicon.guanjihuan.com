#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十六轮（学术全域批）核心层裁定 — 一次性落账脚本。

⚠️ 一次性脚本，**不要重跑**：本脚本按硬编码词单落账，重跑会覆盖同词形的裁定。
落账方式与册六十五轮一致：直接编辑 `data/core_decisions.json`（唯一事实源），
本文件只作留档与执行载体。跑法：python3 tools/_ledger_r66.py --write
"""
import collections
import json
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'core_decisions.json')

CORE = {
 'journal': 'AWL 词头 JOURNAL 族,学术出版高频',
 'curriculum': 'AWL 词头 CURRICULUM 族,教育研究高频',
 'catalyst': 'AWL 词头 CATALYST 族,化学与比喻用法',
 'concede': 'AWL 词头 CONCEDE 族,让步论证报告动词',
 'deficit': 'AWL 词头 DEFICIT 族,经济与政策高频',
 'faculty': 'AWL 词头 FACULTY 族,高教语境高频',
 'inevitable': 'AWL 词头 INEVITABLE 族,论证限定高频',
 'inflation': 'AWL 词头 INFLATE 族,经济政策高频',
 'protein': 'AWL 词头 PROTEIN 族,生命科学高频',
 'subsidy': 'AWL 词头 SUBSIDY 族,政策研究高频',
 'surplus': 'AWL 词头 SURPLUS 族,经济学术高频',
 'thesis': 'AWL 词头 THESIS 族,论文写作高频',
 'confidence interval': '统计报告语块,随 AWL INTERVAL 族入核',
 'cognitive': '学术骨架命中,认知科学高频',
 'connotation': '学术骨架命中,语义讨论高频',
 'ideology': '学术骨架命中,社科核心词',
 'vague': '学术骨架命中,批评限定高频',
 'contend': '报告动词组(contend that 学术引述高频)',
 'affirm': '报告动词组(确认肯定,立场表达高频)',
}
NONCORE = {
 'rebut': '法律辩论语域,学术文本较低频',
 'allege': '新闻/法律语域为主,学术较低频',
 'purport': '低频立场动词,学术边缘',
 'signify': '通用符号化动词,频率中等',
 'presuppose': '哲学语域专用',
 'accelerate': '通用变化动词',
 'exacerbate': '通用恶化动词,频率中等',
 'aggravate': '通用恶化动词',
 'escalate': '新闻语域为主',
 'stagnate': '经济语域动词',
 'oscillate': '物理/工程域限定',
 'plummet': '新闻语域为主',
 'soar': '新闻语域为主',
 'dwindle': '通用减少动词',
 'abate': '法律/文学语域,学术较低频',
 'prolong': '通用时间动词',
 'spiral': '通用动态动词',
 'irreversible': '通用限定形容词,无机械命中',
 'obscure': '通用模糊限定',
 'opaque': '通用不透明限定',
 'superficial': '通用批评限定',
 'erroneous': '通用纠错限定',
 'flawed': '通用批评限定',
 'unfounded': '通用批评限定',
 'unwarranted': '通用批评限定',
 'tenuous': '文学化批评限定,频率中等',
 'cogent': '修辞学低频',
 'dubious': '通用怀疑限定',
 'anecdotal': '方法论限定,但频率中等',
 'decisive': '通用决定性限定',
 'fallacy': '逻辑学域限定',
 'ramification': '低频后果名词',
 'repercussion': '新闻/政治语域为主',
 'aftermath': '新闻语域为主',
 'corollary': '数学域限定',
 'precursor': '化学/医学域限定',
 'antecedent': '语法/哲学域限定',
 'drawback': '通用缺点名词',
 'pitfall': '通用误区名词',
 'shortcoming': '通用缺点名词',
 'setback': '新闻语域为主',
 'hurdle': '新闻语域为主',
 'impediment': '低频障碍名词',
 'liability': '法律/会计域限定',
 'hindsight': '通用反思名词',
 'foresight': '通用规划名词',
 'breadth': '通用范围名词',
 'manuscript': '学术出版语境,但学科负载低',
 'appendix': '论文结构词,工具性名词',
 'footnote': '论文结构词,工具性名词',
 'bibliography': '论文结构词,工具性名词',
 'symposium': '学术活动名词,低频',
 'proceedings': '出版语境名词,工具性',
 'syllabus': '教学工具词',
 'pedagogy': '教育学域限定',
 'mentor': '高教语境词,频率中等',
 'doctoral': '高教语境限定词',
 'hegemony': '批判理论专用',
 'bureaucracy': '政治学域名词',
 'marginalize': '社科批判语域',
 'stigmatize': '社科批判语域',
 'urbanization': '城市研究域名词',
 'globalization': '社科域名词',
 'citizenship': '政治学域名词',
 'electorate': '政治学域名词',
 'referendum': '政治学域名词',
 'treaty': '国际法域名词',
 'ratify': '法律语域动词',
 'statute': '法律域名词',
 'jurisdiction': '法律域名词',
 'litigation': '法律域名词',
 'tariff': '经济政策域名词',
 'monetary': '经济语域限定',
 'fiscal': '财政语域限定',
 'monopoly': '经济学域名词',
 'neural': '神经科学域限定',
 'neuron': '神经科学域名词',
 'polymer': '材料科学域名词',
 'enzyme': '生物化学域名词',
 'genome': '基因组学域名词',
 'metabolism': '生物医学域名词',
 'toxic': '通用危险限定',
 'emission': '环境科学域名词',
 'climate': '通用气候名词,领域负载低',
 'renewable': '能源语域限定',
 'semiconductor': '电子工程域名词',
 'database': '计算机工具词',
 'bandwidth': '通信工程域名词',
 'clinical': '医学域限定',
 'diagnosis': '医学域名词',
 'epidemic': '流行病学域名词',
 'pandemic': '流行病学域名词',
 'outbreak': '流行病学域名词',
 'standard deviation': '统计术语,随工具性名词降出',
 'chronic': '医学域限定',
 'acute': '医学域限定',
 'episodic': '叙事/医学域限定',
 'sustained': '通用持续限定,分词形容词',
 'intermittent': '通用间歇限定',
 'symptom': '医学域名词',
 'syndrome': '医学域名词',
 'therapy': '医学域名词',
}

NEW = """contend concede rebut affirm allege purport signify presuppose
accelerate exacerbate aggravate escalate stagnate oscillate plummet soar dwindle abate prolong spiral
inevitable irreversible vague obscure opaque superficial erroneous flawed unfounded unwarranted
tenuous cogent dubious anecdotal decisive
fallacy connotation ramification repercussion aftermath corollary precursor antecedent
drawback pitfall shortcoming setback hurdle impediment liability deficit surplus hindsight foresight breadth
journal manuscript thesis appendix footnote bibliography symposium proceedings curriculum syllabus
pedagogy faculty mentor doctoral
ideology hegemony bureaucracy marginalize stigmatize urbanization globalization citizenship electorate
referendum treaty ratify statute jurisdiction litigation tariff subsidy inflation monetary fiscal monopoly
neural neuron polymer catalyst enzyme protein genome metabolism toxic emission climate renewable
semiconductor database bandwidth
clinical diagnosis epidemic pandemic outbreak
chronic acute episodic sustained intermittent cognitive
symptom syndrome therapy""".split() + ['confidence interval', 'standard deviation']
NEWL = [w.lower() for w in NEW]


def main():
    write = '--write' in sys.argv
    led = json.load(open(P, encoding='utf-8'))
    dec = led['decisions']
    words = json.load(open(P.replace('core_decisions', 'words'), encoding='utf-8'))
    wl = {w['word'].lower() for w in words}

    allv = collections.Counter(list(CORE) + list(NONCORE))
    dups = [w for w, c in allv.items() if c > 1]
    if dups:
        raise SystemExit('dup verdicts: %s' % dups)
    unknown = [w for w in list(CORE) + list(NONCORE) if w not in wl]
    if unknown:
        raise SystemExit('not in wordlist: %s' % unknown)
    covered = set(CORE) | set(NONCORE)
    uncov = [w for w in set(NEWL) if w not in covered]
    if uncov:
        raise SystemExit('uncovered new words: %s' % sorted(uncov))
    extra = [w for w in covered if w not in NEWL]
    if extra:
        raise SystemExit('verdicts not in this batch: %s' % sorted(extra))
    print('verdict coverage OK: core %d / noncore %d / total %d'
          % (len(CORE), len(NONCORE), len(covered)))
    if not write:
        print('(dry run — pass --write to apply)')
        return
    for w, r in CORE.items():
        dec[w] = {'verdict': 'core', 'reason': r}
    for w, r in NONCORE.items():
        dec[w] = {'verdict': 'noncore', 'reason': r}
    n_core = sum(1 for v in dec.values() if v['verdict'] == 'core')
    led['_meta']['total'] = len(words)
    led['_meta']['final_core'] = n_core
    tmp = P + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    os.replace(tmp, P)
    print('LEDGER WRITTEN: core %d / %d (%.1f%%)' % (n_core, len(words), 100.0 * n_core / len(words)))


if __name__ == '__main__':
    main()
