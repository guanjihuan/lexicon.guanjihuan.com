#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六十一轮：给新增的 158 个学术常用词补台账裁定（core_decisions.json）。

⚠️ 一次性脚本，**不要重跑**：本脚本按 `cur['add'][-155:]` 取当批词，而 add 段尾数
会随后续增补轮前移 ⇒ 重跑会把别的批次词当成本批、断言失败或静默写坏台账
（r65 留档副本头部有同款警示；实测教训见记忆条目「核心层台账生成器是一次性的」）。
要改某个词的裁定（verdict/reason），直接编辑 data/core_decisions.json（唯一事实源）。

判据沿用册四十一轮「仅硬证据入核」：
  core    = AWL 词族成员（客观硬证据，data/freq_refs.json 的 awl_heads）
          ∪ 学术论证动作动词（论证推进/结论落地）
          ∪ 研究方法核心名词（分析对象本身）
          ∪ 分析性形容词（限定分析口径）
  noncore = 领域专用但不承载论证功能者、通用管理/组织类词、日常描述词
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'data', 'core_decisions.json')

# ---- core：AWL 词族（硬证据，见 data/freq_refs.json 的 awl_heads） ----
AWL = {
    "administer": "AWL词族", "adopt": "AWL词族", "component": "AWL词族",
    "conceive": "AWL词族", "conform": "AWL词族", "consequence": "AWL词族",
    "consist": "AWL词族", "controversy": "AWL词族", "convey": "AWL词族",
    "deliberate": "AWL词族", "displace": "AWL词族", "duration": "AWL词族",
    "equilibrium": "AWL词族", "ethical": "AWL词族", "facility": "AWL词族",
    "feedback": "AWL词族", "formal": "AWL词族", "generation": "AWL词族",
    "hierarchy": "AWL词族", "identical": "AWL词族", "index": "AWL词族",
    "institution": "AWL词族", "integral": "AWL词族", "intensity": "AWL词族",
    "momentum": "AWL词族", "neutral": "AWL词族", "obligation": "AWL词族",
    "portray": "AWL词族", "promotion": "AWL词族", "rational": "AWL词族",
    "stress": "AWL词族", "supplement": "AWL词族", "technology": "AWL词族",
    "welfare": "AWL词族",
}

# ---- core：论证动作动词 ----
CORE_VERB = {
    "anticipate": "论证推进动词（预期）",
    "capture": "论证推进动词（捕捉现象）",
    "classify": "分析动作动词（分类）",
    "concur": "论证一致性动词",
    "dedicate": "研究投入动词",
    "depict": "论证呈现动词（刻画）",
    "emerge": "论证推进动词（结论浮现）",
    "intensify": "论证强化动词",
    "stipulate": "论证边界动词（规定条件）",
    "weaken": "论证削弱动词",
}

# ---- core：研究方法核心名词 ----
CORE_NOUN = {
    "ambiguity": "构念判读核心名词",
    "detection": "方法检出核心名词",
    "exclusion": "样本规则核心名词",
    "expectation": "研究假设核心名词",
    "identity": "构念同一性核心名词",
    "induction": "研究推理核心名词",
    "integration": "分析整合核心名词",
    "interaction": "分析对象核心名词",
    "necessity": "论证要件核心名词",
    "participation": "研究参与核心名词",
    "persistence": "研究持续性核心名词",
    "priority": "研究议程核心名词",
    "productivity": "研究产出核心名词",
    "reduction": "结果变量核心名词",
    "refinement": "方法改进核心名词",
    "selection": "样本选择核心名词",
    "separation": "分析区分核心名词",
    "simulation": "方法模拟核心名词",
    "specification": "分析设定核心名词",
    "stability": "结果稳健性核心名词",
}

# ---- core：分析性形容词 ----
CORE_ADJ = {
    "accountable": "学术问责口径限定",
    "autonomous": "研究自主性限定",
    "categorical": "数据类型限定（分类变量）",
    "conditional": "条件性限定",
    "interdependent": "构念关系限定",
    "logical": "推理结构限定",
    "measurable": "可测量性限定",
    "misleading": "解释效度限定",
    "observable": "可观测性限定",
    "paradoxical": "反常结果限定",
    "scientific": "科学性限定",
    "structural": "结构性限定",
    "technological": "技术维度限定",
    "vulnerable": "脆弱性限定",
}

# ---- noncore：逐词理由（通用学术书面词，学术不承载论证功能） ----
NONCORE = {
    # 通用管理/组织/事务类名词
    "expenditure": "通用支出名词",
    "extension": "通用延伸名词",
    "friction": "通用摩擦名词",
    "inspection": "通用检查名词",
    "orientation": "通用导向名词",
    "partition": "通用划分名词",
    "partnership": "通用合作类名词",
    "practitioner": "通用从业者名词",
    "profile": "通用概况名词",
    "projection": "通用预测名词",
    "provision": "通用供给名词",
    "qualification": "通用资格名词",
    "quota": "通用配额名词",
    "recurrence": "通用重现名词",
    "remedy": "通用补救名词",
    "reputation": "通用声誉名词",
    "reservation": "通用保留名词",
    "restriction": "通用限制名词",
    "retrieval": "通用检索名词",
    "revision": "通用修订名词",
    "severity": "通用程度名词",
    "sufficiency": "通用充分性名词",
    "supervision": "通用监督名词",
    "survival": "通用生存名词",
    "tactic": "通用策略名词",
    "tendency": "通用倾向名词",
    "terminology": "通用术语名词",
    "tolerance": "通用容忍名词",
    "transformation": "通用转型名词",
    "transmission": "通用传递名词",
    "typology": "类型学专门名词",
        "utilization": "通用利用名词",
    "variability": "通用变异名词",
    "variation": "通用变异名词",
    "viability": "通用可行性名词",
    "vitality": "通用活力名词",
    "volatility": "通用波动性名词",
    "realism": "通用立场名词",
    "reciprocity": "通用互惠名词",
    "recommendation": "通用建议类名词",
    "reinforcement": "通用强化名词",
    "initiative": "通用主动性名词",
    # 领域专用但不承载论证功能
    "ecology": "生态学领域名词",
    "epidemiology": "流行病学领域名词",
    "latency": "技术领域名词",
    "manifestation": "通用表现名词",
    "maturity": "通用成熟度名词",
    "modality": "技术领域名词",
    "motivation": "通用动机名词",
    "neutrality": "通用中立名词",
        "rigor": "通用严谨性名词",
    "proficiency": "通用能力水平名词",
    "density": "通用密度名词",
    "depth": "通用深度名词",
    "consumption": "通用消耗名词",
    "construction": "通用建构名词",
    "cooperation": "通用合作名词",
    # 通用描述动词
    "advise": "通用建议动词",
    "affiliate": "通用隶属动词",
    "authenticate": "技术领域动词",
    "cultivate": "通用培养动词",
    # 通用描述形容词
    "accessible": "通用可达性限定",
    "apparent": "通用明显性限定",
    "authentic": "通用真实性限定",
    "beneficial": "通用褒义限定",
    "characteristic": "通用特征限定",
    "collective": "通用集合限定",
    "finite": "数学域限定",
    "hypothetical": "通用假设限定",
    "innovative": "通用创新限定",
    "productive": "通用多产限定",
    "questionable": "通用可疑限定",
    "realistic": "通用现实限定",
    "recurrent": "通用重复限定",
    "reputable": "通用声望限定",
    "selective": "通用选择性限定",
}


def main():
    with open(P, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']

    core = {}
    core.update(AWL)
    core.update(CORE_VERB)
    core.update(CORE_NOUN)
    core.update(CORE_ADJ)

    cur = json.load(open(os.path.join(ROOT, 'data', 'curation.json'), encoding='utf-8'))
    batch = [a['word'] for a in cur['add'][-155:]]

    noncore = {}
    # 本轮撤回的三个词（与既往 remove 段裁定冲突：nomenclature 第八轮、
    # integral/universality 第一轮）：从台账里一并撤掉，防台账出现孤儿词形
    for w in ("nomenclature", "universality", "integral"):
        dec.pop(w, None)

    for w in batch:
        if w in core:
            continue
        r = NONCORE.get(w, '')
        if not r:
            r = '通用学术书面词，学术不承载论证功能'
        noncore[w] = r

    for w in batch:
        if w in core:
            dec[w] = {'verdict': 'core', 'reason': core[w]}
        else:
            dec[w] = {'verdict': 'noncore', 'reason': noncore[w]}

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
          % (len(batch), len(core), len(noncore), n_core, len(words),
             100.0 * n_core / len(words)))


if __name__ == '__main__':
    main()
