#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第七十轮并发增补批（213 词）逐词补裁定，并入 data/sentiment_decisions.json。

⚠️ 一次性脚本，**不要重跑**：它整体重写 `data/sentiment_decisions.json`，
而后续各轮的裁定是**直接编辑台账**落下的，不在本脚本的输入里 ⇒ 重跑会用
旧稿覆盖后续裁定，静默写坏台账。要改裁定，直接编辑
data/sentiment_decisions.json（唯一事实源），再跑 tools/_gen_sentiment.py
落进 curation.json 的 sentiment 段。
（同类教训见记忆条目「核心层台账生成器是一次性的」。）

并发窗口在第七十轮同时补了 213 个词（形容词 48 / 名词 120 / 动词 32 / 副词 13）。
新增词不在主批判定范围内，若不补裁定，它们会落到默认值上：
  * 感情色彩 → 「中性的」（形容词/名词/动词）
  * 语体色彩 → 「中性」
其中确有一批带明确褒贬的词（sound/credible/narrow/inconsistent…）与一批学科术语
（ethnography/heteroskedasticity/CONSORT…），不补就等于让它们默认中性——
这正是本轮要消灭的「兜底堆」。

本脚本把逐词裁定直接写进台账（台账是手改的真源，本脚本是这次补裁定的留档）。
跑法：python3 tools/_audit/r70_new_decisions.py
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

# 词: (sub, reg, 理由)   sub/reg 为 None 表示该维取默认（中性）
NEW = {
    # ---------------------------------------------------------- 形容词 48
    'sound': ('积极的', None, '「可靠的；严谨的」（sound reasoning）在学术中是对论证质量的褒扬'),
    'credible': ('积极的', None, '「可信的；有信誉的」，可信性是学术证据的正面品质'),
    'convincing': ('积极的', None, '「有说服力的；令人信服的」，对论证力量的褒扬'),
    'germane': ('积极的', None, '「切题的；贴切的」，切题是写作的正面品质'),
    'incisive': ('积极的', None, '「尖锐的；切入要害的」，是对分析透彻性的褒扬'),
    'penetrating': ('积极的', None, '「有洞察力的；透彻的」，正面评价'),
    'judicious': ('积极的', None, '「明智的；审慎的」，褒义'),
    'prudent': ('积极的', None, '「谨慎的；审慎的」，褒义'),
    'astute': ('积极的', None, '「精明的；敏锐的」，褒义'),
    'apt': ('积极的', None, '「恰当的；切题的」，褒义'),
    'landmark': ('积极的', None, '「里程碑式的；划时代的」，褒义'),
    'unbiased': ('积极的', None, '「无偏的」，无偏是统计量的正面品质'),
    'unambiguous': ('积极的', None, '「明确的；不含糊的」，与「含糊」相对，是优良品质'),
    'desirable': ('积极的', None, '「可取的；合乎需要的」，褒义'),
    'narrow': ('消极的', None, '「狭窄的；局限的」（a narrow scope/focus），学术语域指覆盖面受限，含贬义'),
    'inconsistent': ('消极的', None, '「不一致的；自相矛盾的」，是方法与结论层面的缺陷'),
    'conflicting': ('消极的', None, '「相互冲突的；抵触的」，证据层面的冲突是待解的问题'),
    'inconclusive': ('消极的', None, '「不确定的；无定论的」，结论不充分是不理想的结果'),
    'insufficient': ('消极的', None, '「不足的；不充分的」（insufficient evidence/power），是缺陷'),
    'persistent': ('争议性的', None, '「持续存在的；顽固的」两义评价相反：持续的不平等（负）与坚持不懈（正）'),
    'contested': ('争议性的', None, '「有争议的；被争夺的」，评价两极且本身即争议'),
    'disputed': ('争议性的', None, '「有争议的；受到质疑的」，评价两极'),
    'contentious': ('争议性的', None, '「有争议的；易引起争执的」，评价两极'),
    'epistemological': (None, '书面语', '认识论/知识论的专门术语'),
    'ontological': (None, '书面语', '本体论的专门术语'),
    'axiomatic': (None, '书面语', '公理化的专门术语'),
    'abductive': (None, '书面语', '溯因推理的专门术语'),
    'purposive': (None, '书面语', '目的性抽样的方法学术语'),
    'quasi-experimental': (None, '书面语', '准实验设计的专门术语'),
    'latent': (None, '书面语', '潜在变量的统计学术语'),
    # ---------------------------------------------------------- 动词 32
    'confer': ('积极的', None, '「授予；带来」（confer an advantage），义项本身是给予好处'),
    'bolster': ('积极的', None, '「支持；增强」（bolster the argument），加固正面一侧'),
    'uphold': ('积极的', None, '「维持；支持；维护」（uphold standards/principles），维护正义与规范'),
    'circumvent': ('消极的', None, '「规避；绕过」，绕开规则本身带贬义'),
    'curtail': ('消极的', None, '「削减；限制」，缩减自由与花费的方向'),
    'curb': ('消极的', None, '「抑制；约束」，约束住不良增长'),
    'thwart': ('消极的', None, '「阻挠；使受挫」，义项自带贬义'),
    'hamper': ('消极的', None, '「妨碍；阻碍」，方向为负'),
    'halt': ('消极的', None, '「使停止；终止」，进程被叫停是不利结果'),
    'erode': ('消极的', None, '「侵蚀；逐步削弱」（erode confidence），削弱方向'),
    'corrode': ('消极的', None, '「腐蚀；（比喻）损害」，损害方向'),
    'overstate': ('消极的', None, '「夸大；言过其实」，学术写作里的明确硬伤'),
    'appraise': (None, '书面语', '评价/鉴定的正式学术动词'),
    'subsume': (None, '书面语', '归类/统摄的逻辑学术语'),
    'delimit': (None, '书面语', '划定研究边界的学术动作，正式书面语'),
    'demarcate': (None, '书面语', '划界/区分的学术动作，正式书面语'),
    'reconstruct': (None, '书面语', '重建/还原的学术动作'),
    'reiterate': (None, '书面语', '重申，正式书面语'),
    'permeate': (None, '书面语', '渗透/弥漫，正式书面语'),
    'pervade': (None, '书面语', '遍及/充斥，正式书面语'),
    'preempt': (None, '书面语', '先发制人，正式书面语'),
    'situate': (None, '书面语', '把…置于框架中，学术动作'),
    'reframe': (None, '书面语', '重构框架，学术动作'),
    'rethink': (None, '书面语', '重构思路，学术动作'),
    'interrogate': (None, '书面语', '追问/细查，学术动作'),
    'accrue': (None, '书面语', '积累/产生，正式书面语'),
    'bootstrap': (None, '书面语', '自助法重抽样的统计学术语'),
    # ---------------------------------------------------------- 名词 120
    'boon': ('积极的', None, '「裨益；福音」（a boon to researchers），义项本身是益处'),
    'hindrance': ('消极的', None, '「妨碍；阻碍」（a hindrance to progress），义项自带贬义'),
    'mismatch': ('消极的', None, '「错配；不匹配」，是待解决的错位'),
    'inconsistency': ('消极的', None, '「不一致；矛盾」，是缺陷'),
    'conflict': ('消极的', None, '「冲突；抵触」（a conflict between theory and evidence），对立状态'),
    'barrier': ('消极的', None, '「障碍；壁垒」，义项自带贬义'),
    'burden': ('消极的', None, '「负担；举证责任」，负担义为负'),
    'misconception': ('消极的', None, '「误解；错误观念」，明确的负面'),
    'nonresponse': ('消极的', None, '「无应答；未回应」，研究流失指标'),
    'overfitting': ('消极的', None, '「过拟合」，模型缺陷'),
    'missing data': ('消极的', None, '「数据缺失；缺失值」，需处理的数据缺陷'),
    'misinformation': ('消极的', None, '「错误信息」，负面'),
    'disinformation': ('消极的', None, '「虚假信息（蓄意）」，负面'),
    'conflict of interest': ('消极的', None, '「利益冲突」，学术伦理上的负面'),
    'disincentive': ('消极的', None, '「抑制因素」，抑制方向'),
    'unemployment': ('消极的', None, '「失业」，负面社会状态'),
    'inequality': ('消极的', None, '「不平等」，负面社会状态'),
    'health inequality': ('消极的', None, '「健康不平等」，负面社会状态'),
    'risk factor': ('消极的', None, '「风险因素」，指向危害'),
    'climate change': ('消极的', None, '「气候变化」，稳定的负面议题'),
    'numeracy': ('积极的', None, '「计算能力；数理素养」，被追求的正面能力'),
    'fairness': ('积极的', None, '「公平性」，公平本身是正面价值'),
    'entrepreneurship': ('积极的', None, '「创业；企业家精神」，被推崇的正面状态'),
    # 语体：学科/方法术语与正式语体标志
    'preprint': (None, '书面语', '预印本的学术出版术语'),
    'erratum': (None, '书面语', '勘误的出版术语'),
    'corrigendum': (None, '书面语', '更正启事的出版术语'),
    'counterexample': (None, '书面语', '反例的逻辑学术语'),
    'concordance': (None, '书面语', '一致性统计/语料索引的术语'),
    'modality': (None, '书面语', '模态/表现形式的学术术语'),
    'nonresponse': (None, '书面语', '无应答率的调查方法术语'),
    'census': (None, '书面语', '普查/全样本调查的方法术语'),
    'CONSORT': (None, '书面语', '随机对照试验报告规范（术语）'),
    'STROBE': (None, '书面语', '观察性研究报告规范（术语）'),
    'standard error': (None, '书面语', '标准误的统计学术语'),
    'covariance': (None, '书面语', '协方差的统计学术语'),
    'heteroskedasticity': (None, '书面语', '异方差性的计量术语'),
    'autocorrelation': (None, '书面语', '自相关的统计学术语'),
    'permutation': (None, '书面语', '置换检验的方法学术语'),
    'degrees of freedom': (None, '书面语', '自由度的统计学术语'),
    'chi-square': (None, '书面语', '卡方检验的统计学术语'),
    'Monte Carlo': (None, '书面语', '蒙特卡洛方法的术语'),
    'median': (None, '书面语', '中位数的统计学术语'),
    'quartile': (None, '书面语', '四分位数的统计学术语'),
    'percentile': (None, '书面语', '百分位数的统计学术语'),
    'recall': (None, '书面语', '查全率/召回率的检索术语'),
    'confusion matrix': (None, '书面语', '混淆矩阵的机器学习术语'),
    'ground truth': (None, '书面语', '真值标注的机器学习术语'),
    'regularization': (None, '书面语', '正则化的统计学习术语'),
    'annotation': (None, '书面语', '标注的语料/数据术语'),
    'coding': (None, '书面语', '质性研究编码过程的术语'),
    'transcription': (None, '书面语', '转录/文字转写的质性研究术语'),
    'member checking': (None, '书面语', '成员核验的质性研究术语'),
    'audit trail': (None, '书面语', '审计轨迹/决策留痕的术语'),
    'ethnography': (None, '书面语', '民族志的研究方法术语'),
    'screening': (None, '书面语', '筛查/筛选的研究方法术语'),
    'surveillance': (None, '书面语', '疾病监测/监测的研究与公卫术语'),
    'scoping review': (None, '书面语', '范围综述的循证术语'),
    'peer review': (None, '书面语', '同行评议的出版术语'),
    'open access': (None, '书面语', '开放获取的出版术语'),
    'repository': (None, '书面语', '存储库/数据仓储的术语'),
    'interoperability': (None, '书面语', '互操作性的技术术语'),
    'metadata': (None, '书面语', '元数据的术语'),
    'ontology': (None, '书面语', '本体（知识表示体系）的术语'),
    'cybersecurity': (None, '书面语', '网络安全的术语'),
    'intellectual property': (None, '书面语', '知识产权的法律/政策术语'),
    'copyright': (None, '书面语', '版权的法律术语'),
    'open science': (None, '书面语', '开放科学的政策术语'),
    'open data': (None, '书面语', '开放数据的政策术语'),
    'land use': (None, '书面语', '土地利用的地理/政策术语'),
    'public health': (None, '书面语', '公共卫生的学科术语'),
    'life expectancy': (None, '书面语', '预期寿命的公卫统计指标'),
    'mental health': (None, '书面语', '心理健康的学科术语'),
    'randomized controlled trial': (None, '书面语', '随机对照试验的方法学术语'),
    'enrollment': (None, '书面语', '入组/招募的临床与调查术语'),
    'engagement': (None, '书面语', '参与度的研究术语'),
    'behavior': (None, '书面语', '行为的学术术语'),
    'taxation': (None, '书面语', '税收/税制的政策术语'),
    'cost-effectiveness': (None, '书面语', '成本效果的卫生经济学术语'),
    'audit': (None, '书面语', '审计/核查的治理术语'),
    'supply chain': (None, '书面语', '供应链的术语'),
    'workforce': (None, '书面语', '劳动力的术语'),
    'artificial intelligence': (None, '书面语', '人工智能的学科术语'),
    'machine learning': (None, '书面语', '机器学习的学科术语'),
    'framing': (None, '书面语', '框架化/框定的传播研究术语'),
    'statistical significance': (None, '书面语', '统计显著性的统计学术语'),
    'systematic review': (None, '书面语', '系统综述的循证术语'),
    'mixed methods': (None, '书面语', '混合方法的研究设计术语'),
    'gender': (None, '书面语', '性别的社会研究术语'),
    'ethnicity': (None, '书面语', '族裔/民族的社会研究术语'),
    'instruction': (None, '书面语', '教学/教学活动的教育学术语'),
    'scholarship': (None, '书面语', '学术研究成果的学术语'),
    'standpoint': (None, '书面语', '立场/出发点的学术语'),
    'rebuttal': (None, '书面语', '答辩/反驳信的同行评议术语'),
    'submission': (None, '书面语', '投稿的出版术语'),
    'objection': (None, '书面语', '反对意见的论证术语'),
    'appraisal': (None, '书面语', '评估/鉴定的术语'),
    'utility': (None, '书面语', '效用（论）的术语'),
    'continuum': (None, '书面语', '连续体/连续谱的学术术语'),
    'lens': (None, '书面语', '视角（through the lens of）的学术惯用搭配'),
    'asymmetry': (None, '书面语', '不对称的术语'),
    'homogeneity': (None, '书面语', '同质性的统计学术语'),
    'symmetry': (None, '书面语', '对称性的术语'),
    'facet': (None, '书面语', '方面/侧面的学术惯用语'),
    'landscape': (None, '书面语', '（研究/政策）格局的学术惯用语'),
    'terrain': (None, '书面语', '（比喻）领域的学术惯用语'),
    'strand': (None, '书面语', '（论证的）一条线索的学术惯用语'),
    'thread': (None, '书面语', '（论证的）线索/脉络的学术惯用语'),
    'practice': (None, '书面语', '实践/惯例的学术用语'),
    'statistics': (None, '书面语', '统计学的学科术语'),
    'framework': (None, '书面语', '框架的学术用语'),
    'input': (None, '书面语', '输入/投入的学术用语'),
    'task': (None, '书面语', '研究任务的学术用语'),
    'paper': (None, '书面语', '（学术）文章的学术用语'),
    'review': (None, '书面语', '综述/评述的学术用语'),
    'discussion': (None, '书面语', '（论文的）讨论部分的学术用语'),
    'study': (None, '书面语', '研究/研究论文的学术用语'),
    'pilot': (None, '书面语', '试点/预试验的研究术语'),
    'privacy': (None, '书面语', '隐私的政策/法律术语'),
    'architecture': (None, '书面语', '体系结构/架构的技术术语'),
    'platform': (None, '书面语', '平台的学术与技术用语'),
    'intervention': (None, '书面语', '干预/干预措施的研究术语'),
    'privacy': (None, '书面语', '隐私的政策/法律术语'),
}


def main():
    with io.open(LEDGER, encoding='utf-8') as f:
        led = json.load(f)
    dec = led['decisions']
    words = set()
    with io.open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8') as f:
        for w in json.load(f):
            words.add(w['word'])
    missing = sorted(set(NEW) - words)
    if missing:
        raise SystemExit('这些词不在当前词表里（已删或改名？）：%s' % missing)
    n_sub = n_reg = 0
    for w, (sub, reg, reason) in NEW.items():
        e = dec.setdefault(w, {})
        if sub:
            e['sub'] = sub
            n_sub += 1
        if reg:
            e['reg'] = reg
            n_reg += 1
        e['reason'] = reason
    led['_meta']['r70_note'] = ('第七十轮并发增补批（213 词）逐词补裁定：'
                                '带褒贬的词显式给档，学科术语显式给语体；'
                                '其余取默认值（见 tools/_audit/r70_new_decisions.py）。')
    tmp = LEDGER + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(tmp, LEDGER)
    print('台账补裁定：%d 词（sub %d / reg %d），台账现共 %d 条'
          % (len(NEW), n_sub, n_reg, len(dec)))


if __name__ == '__main__':
    main()
