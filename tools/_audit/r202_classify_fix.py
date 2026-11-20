#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二百零二节:分类收口——补齐 129 条 reason-only 台账的语体裁定 + 感情色彩十处改判。

背景:
  * 177 节增补批(213 词)的补裁定给多数新词写了 reg='书面语';181/185 两轮复核时,
    其中 89 词的 reg 字段被静默删除(只剩 reason),违反 185 节自立的
    「不许静默降档」规矩。这些词的 reason 多为「XX 学科专门术语」认定,
    按判准本应归「学术术语」,却全部落到默认「中性」。
  * 判准文档(tools/_audit/sentiment_criteria.md)点名的「积极」例词 enhance
    从未落台账;另有九个与已判档词明显同型的漏判(innovation↔innovative、
    consensus↔accuracy/clarity、cohesion↔cohesive、viability↔feasibility、
    scalability↔reliability、plethora 弱贬、entangle/spiral/prolong 弱贬)。
  * statistics/modality/continuum/dichotomy/emulate/signify 等「学术惯用语」
    按 185 节口径(义项须承载专门概念)判中性;fashion/utilization/accrue
    判书面语(正式/文雅印记,非学科专门概念)。

本脚本按 tools/_audit/sentiment_criteria.md 判准逐词补/改 data/sentiment_decisions.json,
是本轮的一次性迁移留档,不要重跑。跑法: python3 tools/_audit/r202_classify_fix.py
后续修改请直接编辑唯一真源 data/sentiment_decisions.json,再跑 tools/_gen_sentiment.py。
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, 'data', 'sentiment_decisions.json')

# ============================================================ 一、语体补裁定
# 129 条 reason-only 里按义项承载专门概念、应归「学术术语」的(逐词对照本库释义):
TERM_WORDS = {
    # 统计 / 计量 / 机器学习
    'coefficient': '统计学专门术语：系数（相关系数、回归系数）',
    'confidence interval': '统计学术语：参数估计的置信区间',
    'standard deviation': '统计学术语：离散程度的标准度量',
    'standard error': '统计学术语：抽样分布的标准误',
    'covariance': '统计学术语：协方差',
    'heteroskedasticity': '计量经济学术语：异方差性',
    'autocorrelation': '统计学术语：序列自相关',
    'permutation': '统计学术语：置换检验',
    'degrees of freedom': '统计学术语：自由度',
    'chi-square': '统计学术语：卡方检验',
    'Monte Carlo': '计算统计术语：蒙特卡洛方法',
    'median': '统计学术语：中位数',
    'quartile': '统计学术语：四分位数',
    'percentile': '统计学术语：百分位数',
    'recall': '信息检索与机器学习术语：查全率/召回率',
    'confusion matrix': '机器学习术语：混淆矩阵',
    'ground truth': '机器学习术语：真值标注',
    'bootstrap': '统计学术语：自助法重抽样',
    'latent': '统计学术语：潜变量（latent variable）',
    'statistical significance': '统计学术语：统计显著性',
    'estimation': '统计学术语：参数估计',
    'inference': '统计学术语：统计推断',
    'baseline': '临床试验与实验设计术语：基线值',
    'endpoint': '临床试验术语：终点指标',
    'census': '调查方法术语：普查/全样本调查',
    # 研究设计 / 循证 / 质性方法
    'randomized controlled trial': '研究设计术语：随机对照试验',
    'scoping review': '循证方法术语：范围综述',
    'systematic review': '循证方法术语：系统综述',
    'mixed methods': '研究设计术语：混合方法',
    'quasi-experimental': '研究设计术语：准实验设计',
    'member checking': '质性研究术语：成员核验',
    'audit trail': '质性研究与审计术语：决策留痕记录',
    'fieldwork': '人类学与质性研究术语：田野调查',
    'grounded theory': '质性研究术语：扎根理论',
    'case study': '研究方法术语：个案研究',
    'literature review': '研究方法术语：文献综述',
    'peer review': '学术出版术语：同行评议',
    'preregistration': '开放科学术语：研究方案预注册',
    'CONSORT': '随机对照试验报告规范名（术语）',
    'STROBE': '观察性研究报告规范名（术语）',
    'pilot': '研究设计术语：试点/预试验',
    'retrieval': '信息检索与图书馆学术语：检索',
    # 科学哲学 / 逻辑 / 数学
    'paradigm': '科学哲学术语：范式',
    'theorem': '数学术语：定理、命题',
    'posit': '科学哲学术语：设定并主张（posit a hypothesis）',
    'induction': '逻辑学术语：归纳法',
    'validate': '方法学与测量学术语：验证、确认',
    'disaggregate': '统计与政策分析术语：分解数据',
    # 学术出版制度
    'preprint': '学术出版术语：预印本',
    'erratum': '出版术语：勘误',
    'corrigendum': '出版术语：更正启事',
    'manuscript': '学术出版术语：待评审投稿稿',
    'bibliography': '学术出版术语：文献目录',
    'dissertation': '学位制度专称：学位论文',
    'rebuttal': '同行评议术语：答辩/反驳信',
    'submission': '学术出版术语：投稿',
    # 法学 / 政策 / 经济制度对象
    'treaty': '国际法术语：国家间缔结的条约',
    'statute': '法学术语：成文法与法令',
    'jurisdiction': '法学术语：司法管辖权及范围',
    'litigation': '法学术语：诉讼程序',
    'subsidy': '公共财政术语：政府补贴',
    'taxation': '财政与政策术语：税收/税制',
    'intellectual property': '法律/政策术语：知识产权',
    'copyright': '法律术语：版权',
    'quota': '行政管理与经济术语：限额配额',
    'utility': '经济学术语：效用（utility function）',
    # 信息 / 计算技术
    'metadata': '信息管理术语：元数据',
    'ontology': '知识工程术语：本体（知识表示体系）',
    'repository': '信息管理术语：存储库/数据仓储',
    'interoperability': '信息技术术语：互操作性',
    'cybersecurity': '信息安全术语：网络安全',
    'fingerprint': '取证与计算术语：指纹/特征标记',
    'authenticate': '信息安全术语：验证身份或真伪',
    'machine learning': '计算学科术语：机器学习',
    'artificial intelligence': '计算学科术语：人工智能',
    # 公卫 / 环境 / 管理
    'exposure': '流行病学术语：暴露（于风险因素）',
    'land use': '地理与政策术语：土地利用',
    'cost-effectiveness': '卫生经济学术语：成本效果',
    'supply chain': '管理学术语：供应链',
    # 教育 / 社会学专门概念
    'pedagogy': '教育学术语：教学法与教学理论',
    'curriculum': '教育学术语：课程体系',
    'typology': '类型学术语：按共同特征所作的类型划分',
    'reciprocity': '人类学与国际法术语：互惠交换关系',
    'globalization': '社会学与国际关系术语：跨国整合',
    'framing': '传播研究术语：框架化/框定',
    # 开放科学制度
    'open access': '学术出版术语：开放获取',
    'open science': '科研政策术语：开放科学',
    'open data': '科研政策术语：开放数据',
}

# 正式/文雅印记（非学科专门概念）→ 书面语:
FORMAL_WORDS = {
    'utilization': 'utilize 的名词形，正式书面语用词',
    'accrue': '正式书面语：积累/自然增长',
    'fashion': '「in a systematic fashion」式的正式书面惯用语（本库义项「方式；做法」）',
}

# 通用学术词与学术惯用语 → 显式中性（185 节口径：义项须承载专门概念，宁漏勿滥）:
NEUTRAL_WORDS = {
    'study': '通用学术词：研究/研究论文，不承载学科专门概念',
    'paper': '通用学术词：（学术）文章',
    'practice': '通用学术词：实践/惯例',
    'framework': '通用学术词：框架',
    'input': '通用学术词：输入/投入',
    'task': '通用学术词：研究任务',
    'review': '通用学术词：综述/评述',
    'discussion': '通用学术词：（论文的）讨论部分',
    'behavior': '通用研究词：行为',
    'engagement': '通用研究词：参与度',
    'gender': '通用社会研究词：性别',
    'ethnicity': '通用社会研究词：族裔/民族',
    'scholarship': '通用学术词：学术研究成果',
    'standpoint': '通用学术词：立场/出发点',
    'objection': '通用论证词：反对意见/异议',
    'continuum': '学术惯用语：连续体（a continuum from X to Y），通用分析表述',
    'lens': '学术惯用语：视角（through the lens of）',
    'facet': '学术惯用语：方面/侧面',
    'landscape': '学术惯用语：（研究/政策）格局',
    'terrain': '学术惯用语：（比喻）领域',
    'strand': '学术惯用语：（论证的）一条线索',
    'thread': '学术惯用语：（论证的）线索/脉络',
    'reconstruct': '通用学术动作：重建/还原',
    'reframe': '通用学术动作：重构框架',
    'rethink': '通用学术动作：重构思路',
    'interrogate': '通用学术动作：追问/细查',
    'symmetry': '通用词：对称性',
    'privacy': '通用词：隐私',
    'platform': '通用词：平台',
    'architecture': '通用技术词：体系结构/架构',
    'intervention': '通用研究词：干预/干预措施',
    'workforce': '通用经济词：劳动力',
    'instruction': '通用教育词：教学/教学活动',
    'emulate': '通用词：效仿（本库例句均为「效仿」义，非计算仿真义）',
    'signify': '通用词：表示，意味着（本库义项与例句均为通用义，非符号学专门义）',
    'modality': '通用词：方式；表现形式（本库例句为 modalities of governance 类通用义）',
    'dichotomy': '通用分析词：二分法；一分为二',
    'statistics': '学科名/统计数据：与 methodology/analysis 同型的学科相关通用词',
}

# ============================================================ 二、感情色彩改判
SUB_FIX = {
    'enhance': ('积极的', '「提高；增强；提升」，稳定指向质量改善，是对效果的正面评价（判准文档点名例词；例句均为提升质量/清晰度）'),
    'innovation': ('积极的', '「新观念；创新」，与 innovative 同型，是对新思想新方法的正面评价'),
    'consensus': ('积极的', '「一致的意见；共识」，论证达成一致的正面状态，与 accuracy/clarity 同为论证质量肯定'),
    'cohesion': ('积极的', '「连贯；衔接」，与 cohesive 同型，是文本被肯定的质量指标'),
    'viability': ('积极的', '「可行性；生存能力」，与 feasibility 同型，是方案被肯定的品质'),
    'scalability': ('积极的', '「可扩展性」，与 reliability 同型，是系统被期望具备的优良品质'),
    'entangle': ('消极的', '「缠住；使纠缠，使复杂化」，稳定指向纠缠难脱的困境（例句：缠住动物、纠缠争议）'),
    'spiral': ('消极的', '「螺旋式攀升」，例句均为债务、成本、冲突失控，稳定指向失控恶化的循环轨迹'),
    'prolong': ('消极的', '「延长，拖长」，隐含拖沓加剧（prolonged suffering），弱贬义'),
    'plethora': ('消极的', '「过多；过剩」，学术写作里 a plethora of 稳定带「过量泛滥」的弱贬义'),
}


def main():
    with io.open(LEDGER, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']

    # 守卫一:三组词必须互斥
    dup = (TERM_WORDS.keys() & FORMAL_WORDS.keys()) | \
          (TERM_WORDS.keys() & NEUTRAL_WORDS.keys()) | \
          (FORMAL_WORDS.keys() & NEUTRAL_WORDS.keys())
    if dup:
        raise SystemExit('三组词有重叠: %s' % sorted(dup))

    # 守卫二:全部词形必须在台账里且当前无 reg(本轮只处理 reason-only 孤儿)
    for w in sorted(TERM_WORDS) + sorted(FORMAL_WORDS) + sorted(NEUTRAL_WORDS):
        if w not in dec:
            raise SystemExit('台账里没有 %r,与预期不符(本轮只处理已有条目)' % w)
        if 'reg' in dec[w]:
            raise SystemExit('%r 已带 reg=%r,不该再由本脚本处理' % (w, dec[w]['reg']))

    # 守卫三:感情改判词必须当前无 sub(默认中性)且为实词
    for w in SUB_FIX:
        if 'sub' in dec.get(w, {}):
            raise SystemExit('%r 已带 sub=%r,不该再由本脚本改判' % (w, dec[w]['sub']))

    n_term = n_formal = n_neutral = n_sub = 0
    for w, why in TERM_WORDS.items():
        dec[w]['reg'] = '学术术语'
        dec[w]['reg_reason'] = '学术术语：' + why
        n_term += 1
    for w, why in FORMAL_WORDS.items():
        dec[w]['reg'] = '书面语'
        dec[w]['reg_reason'] = '书面语：' + why
        n_formal += 1
    for w, why in NEUTRAL_WORDS.items():
        dec[w]['reg'] = '中性'
        dec[w]['reg_reason'] = '语体复核（202 节收口）：' + why + '，归中性'
        n_neutral += 1
    for w, (sub, why) in SUB_FIX.items():
        e = dec.setdefault(w, {})
        e['sub'] = sub
        e['reason'] = why
        n_sub += 1

    led['_meta']['r201_note'] = (
        '第二百零二节分类收口：修复 177 节增补批 129 条 reason-only 孤儿条目的语体归属'
        '（87 学术术语 / 3 书面语 / 39 显式中性），并为 enhance 等 10 词补感情色彩裁定。'
        '逐词判据见 tools/_audit/r202_classify_fix.py。')

    tmp = LEDGER + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(tmp, LEDGER)

    print('语体补裁定: 学术术语 %d / 书面语 %d / 显式中性 %d' % (n_term, n_formal, n_neutral))
    print('感情色彩改判: %d' % n_sub)
    print('台账现共 %d 条' % len(dec))


if __name__ == '__main__':
    main()
