#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语体色彩第二稿：拆四档（学术术语 / 书面语 / 口语 / 中性），逐词重裁。

⚠️ 一次性脚本，**不要重跑**：它整体重写 `data/sentiment_decisions.json`，
而后续各轮的裁定是**直接编辑台账**落下的，不在本脚本的输入里 ⇒ 重跑会用
旧稿覆盖后续裁定，静默写坏台账。要改裁定，直接编辑
data/sentiment_decisions.json（唯一事实源），再跑 tools/_gen_sentiment.py
落进 curation.json 的 sentiment 段。
（同类教训见记忆条目「核心层台账生成器是一次性的」。）

为什么拆：上一稿只有「书面语 / 口语 / 中性」三档，把**学科专门术语**
（covariate、endogeneity、ethnography…）与**正式文体标志**（moreover、
in the event that…）混装在一档。对写作者这是两种完全不同的知识：
一个是「这词是术语」，一个是「这词是正式书面体」；混装等于两档都不准。
拆开后每词唯一归属，判据闭合：

  学术术语  该词在通用英语里基本不单独使用（或日常义与学科义不同），
            且指称某学科的具体方法/技术/测量对象/报告规范。
  书面语    正式/文雅/公文语域标志：书面专用连接词、文雅词、固定语块。
  口语      口语色彩（话语标记、口语惯用）。
  中性      其余（含通用学术词 study/practice/framework/methodology）。

归属优先级：术语 > 书面语 > 口语 > 中性（一个词若既是术语又是正式文雅词，
归术语 —— 对写作者更实用的那一条）。

本脚本是第七十轮第二稿及独立复核的**一次性迁移留档**，下方集合记录当时裁定，
不是日常生成器，**不要重跑**（重跑会把台账后续的人工修订覆盖回这一版）。

后续修改请直接编辑唯一真源 data/sentiment_decisions.json，再运行：
  python3 tools/_gen_sentiment.py && python3 tools/curate.py && python3 tools/make_data.py
最后用 python3 tools/sentiment_test.py 复核。
"""
import io
import json
import os
import shlex
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = lambda *p: os.path.join(ROOT, *p)

# ==================================================================== 学术术语
TERM = set(shlex.split("""
longitudinal benchmark convergence residual recursive iterative fine-grained
heuristic scenario trajectory reproducible probabilistic metric nominal onset
susceptibility extrapolate retraction computational embed validity variance
robustness correlation deviation calibration resolution traceability authenticity
integrity provenance redundancy throughput heterogeneous homogeneous
interdisciplinary multidisciplinary observational cross-sectional deterministic
prospective retrospective reflexivity positionality normative thematic rhetorical
exploratory mediator moderator mediation moderation replicability
generalizability follow-up meta-analysis multicollinearity deductive inductive
operationalization operationalize confounder confounding falsify endogeneity
propensity placebo blinding allocation case-control "effect size" mixed-method
cluster panel pooled simulate conceptualize conceptualization quantification
regress stratify stratum covariate impute inferential triangulation saturation
normalize standardize replicate contextualize citation converge dataset
distribution heterogeneity outlier prevalence proxy regression reproducibility
replication sensitivity specificity causation power anomaly formulation
equivalence latency recurrence reinforcement simulation sufficiency variability
volatility categorical recurrent presuppose anecdotal fallacy corollary precursor
antecedent liability deficit homogeneity asymmetry criterion qualitative
quantitative empirical experimental descriptive prescriptive deductive
audit appraisal concordance counterexample invariant abductive axiomatic
epistemological ontological heterogeneity algorithm sampling
respondent questionnaire cohort iteration proposition elasticity adherence
dissemination scalability equity provenance longitudinal attrition dropout nonresponse mediation heterogeneity
screening surveillance purposive ethnography coding transcription
annotation overfitting regularization heterogeneity
taxonomy notation granularity calibration prototypical
 compliance precedent proposition legislation governance accountability
transparency stakeholder pipeline workflow
ecology epidemiology catalyst enzyme protein genome metabolism neuron
polymer neural semiconductor database bandwidth clinical diagnosis epidemic
pandemic outbreak symptom syndrome therapy chronic acute episodic intermittent
mortality "public health" "health inequality" "life expectancy" "mental health" "risk factor" enrollment literacy sustainability resilience ecosystem oversight disclosure confidentiality anonymity recruitment discourse cohesion genre
purposive """))

# ==================================================================== 书面语
FORMAL = set(shlex.split("""
accordingly additionally consequently nevertheless nonetheless furthermore
whereas albeit "insofar as" whereby notwithstanding conversely namely
"provided that" "not to mention" "in accordance with" "in conjunction with"
therefore thus moreover however besides hence thereby subsequently
"in contrast" "by contrast" "in contrast to" "on the other hand"
"on the one hand" "in addition" "in addition to" "given that" "in that"
thereafter "prior to" "in turn" firstly secondly lastly thirdly
"for fear that" "in order that" "in the sense that" lest
"on condition that" "on the assumption that" "on the grounds that"
"so as to" "to the extent that" "with the result that" "owing to" via
"a priori" "a posteriori" "ad hoc" "in situ" "by no means"
"under no circumstances" "cast light on" "lay the foundation for"
"attribute to" "consist in" reside "in practice" "in principle"
"in light of" "on the basis of" "by means of" "with regard to"
"with respect to" "take into account" "shed light on" "in conclusion"
"in short" "to sum up" "as such" "per se" "inter alia" "vice versa"
"in the event that" "by the same token" "by analogy" "in lieu of"
"by virtue of" "where applicable" "by reason of" "with reference to"
"in the wake of" barring "that being so" "in so doing" "to that end"
"all things considered" "in no small measure" "in the interim"
"to no avail" "at the outset" "thus far" "to date" "in consequence"
"as a case in point" "as appropriate" "as regards" "as to" "as yet"
"in connection with" "in relation to" "in the absence of"
"in the context of" "in which case" "it goes without saying"
"needless to say" "of note" "on account of" "on behalf of"
"subject to" "with a view to" "with the aim of" "with the exception of"
"with this in mind" "post hoc"
hitherto therein thereof wherein seminal corroborate invoke elucidate
exemplify delineate obviate disseminate ascribe commence trenchant
putative aforementioned conflate untenable onerous expedient stringent
pertinent paramount prerequisite disentangle intrinsic salient commensurate
propel cease suffice plethora myriad cornerstone prior eminent equivocal
pertain utilize preclude substantiate affirm allege appraise cogent confer
contend circumvent curtail delimit demarcate germane hindrance impediment
incisive judicious permeate pervade preempt purport ramification ratify
rebut reiterate situate stipulate subsume uphold enumerate discern elicit
illuminate surmount necessitate alleviate deviate consolidate juxtapose
rectify transcend warrant endorse augment embody deploy harness facilitate
ascertain comprehend underscore foster attain undertake
substantive overarching nuanced holistic methodological succinct verbatim
exhaustive pervasive ancillary ostensibly arguably principally rationale
caveat underlie eligible commensurate
delimit elucidate
"""))

# ==================================================================== 口语
COLLOQ = set(shlex.split("""
well anyway "by the way" "on that note" "the minute" tricky
"""))

# fashion 不能据日常词形判口语：本库对应 in a similar fashion，不是口语义。
# anyhow 与 anyway 一样常作会话中的转换/收束标记；from scratch 是跨语域通用习语。
COLLOQ |= {'anyhow'}

# 独立复核后确认的「常见但并未更正式」：学术写作里常见不等于书面语。
FORMAL_NEUTRAL = set(shlex.split("""
"attribute to" via besides "not to mention" "lay the foundation for" cornerstone
"cast light on" "shed light on" eligible nuanced methodological overarching
arguably "take into account" "vice versa" "in practice" "in principle" "in turn"
"on the one hand" "on the other hand" "in conclusion" "in short" "to sum up"
"with this in mind" "on behalf of" "in the wake of" barring "in which case"
"needless to say" "it goes without saying" "all things considered"
"in the context of" "to date" holistic foster harness deploy disentangle consolidate
"""))
FORMAL -= FORMAL_NEUTRAL

# 这四项的专门概念就是本库主要学习内容，归术语比归一般书面语更准确。
FORMAL_TO_TERM = {'a priori', 'a posteriori', 'in situ', 'post hoc'}
TERM |= FORMAL_TO_TERM
FORMAL -= FORMAL_TO_TERM

# 术语复核：本库只列普通抽象义/一般动作，不能借学科搭配反推单词本身是术语。
TERM_NEUTRAL = set(shlex.split("""
convergence converge iterative iteration fine-grained granularity criterion scenario
prototypical embed computational metric pipeline transparency oversight authenticity
integrity literacy interdisciplinary multidisciplinary recruitment allocation panel pooled
equity thematic exploratory recurrent anecdotal intermittent empirical experimental
observational categorical adherence enrollment descriptive prescriptive resolution
distribution citation
"""))
TERM -= TERM_NEUTRAL

# 这些词较普通替代表达更正式，但本库义项并未承载明确的专门技术概念。
TERM_TO_FORMAL = set(shlex.split("""
residual extrapolate nominal onset conceptualize conceptualization formulation
contextualize provenance propensity dissemination disclosure sufficiency presuppose
appraisal compliance anomaly
"""))
FORMAL |= TERM_TO_FORMAL
TERM -= TERM_TO_FORMAL

# ==================================================================== 感情色彩改判
# 这一轮顺带校出 8 处感情色彩误判（都是"中性被当成褒贬"或"褒贬被当成中性"）：
SENT_FIX = {
    'recipe': ('中性的', '「配方、做法」，学术里多为中性描述（recipe for success 是比喻用法）'),
    'hallmark': ('中性的', '「标志性特征」，是描述性名词，褒贬取决于所指对象'),
    'outcome': ('中性的', '「结果、结局」，本身不褒不贬（outcome 可能好坏皆有）'),
    'cascade': ('中性的', '「接连不断的一连串；级联效应」，中性描述（cascade of failures 的负面色彩来自所搭配的事件）'),
    'complexity': ('中性的', '「错综复杂」，是复杂度描述，学术语域下不带贬义'),
    'devise': ('中性的', '「设计、想出」，中性动作动词'),
    'saturation': ('中性的', '「饱和；饱和点」，技术概念，中性'),
    'replication': ('中性的', '「复现、重复」，方法学概念，中性'),
}


def load(p):
    with io.open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    words = load(D('data', 'words.json'))
    known = {w['word'] for w in words}
    gloss = {w['word']: (w.get('catGloss') or (w.get('senses') or [''])[0]) for w in words}
    for name, st in (('TERM', TERM), ('FORMAL', FORMAL), ('COLLOQ', COLLOQ)):
        miss = sorted(st - known)
        if miss:
            raise SystemExit('%s 里有词表里没有的词：%s' % (name, miss))
    both = TERM & FORMAL
    if both:
        raise SystemExit('同时落在术语与书面语的词（须二选一）：%s' % sorted(both))
    tcf = TERM & COLLOQ
    if tcf:
        raise SystemExit('同时落在术语与口语的词：%s' % sorted(tcf))
    fcf = FORMAL & COLLOQ
    if fcf:
        raise SystemExit('同时落在书面语与口语的词：%s' % sorted(fcf))

    led = load(D('data', 'sentiment_decisions.json'))
    dec = led['decisions']

    # 感情理由与语体理由分开：reason 留给 sub，reg_reason 专记 reg。
    # 初判理由按「词＋档位」取，避免某词从术语改判书面语后仍沿用旧档理由。
    reason_pool = {}
    for fn, tag in (('term_1', '学术术语'), ('term_2', '学术术语'), ('term_3', '学术术语'),
                    ('formal_1', '书面语'), ('formal_2', '书面语'), ('formal_3', '书面语'),
                    ('colloquial', '口语')):
        p = D('tools', '_audit', 'reg_batches2', fn + '.json')
        if not os.path.exists(p):
            continue
        for r in load(p):
            reason_pool.setdefault((r['word'], tag), '%s：%s' % (tag, r['reason']))
    custom_reason = {
        'eligible': '书面语：正式表示具备规定资格，学术与制度文本常用',
        'post hoc': '学术术语：研究设计与统计检验中表示事后分析/事后检验',
        'anyhow': '口语：常作转换或收束话题的会话标记，与 anyway 同类',
        'to no avail': '书面语：正式固定用语，表示努力没有取得效果',
        'transparency': '学术术语：治理与公共管理中表示决策和程序公开程度',
        'experimental': '学术术语：研究设计中表示通过操纵变量进行因果检验',
        'operationalize': '学术术语：研究方法中表示把抽象概念转化为可测量指标',
        'audit': '学术术语：治理与研究质量保证中指系统核查程序',
    }

    n = {'学术术语': 0, '书面语': 0, '口语': 0}
    for w in sorted(TERM | FORMAL | COLLOQ):
        val = '学术术语' if w in TERM else ('书面语' if w in FORMAL else '口语')
        e = dec.setdefault(w, {})
        e['reg'] = val
        n[val] += 1
        if w in TERM_TO_FORMAL:
            e['reg_reason'] = ('书面语：本库义项为「%s」，较普通替代表达更正式，'
                               '但不构成特定学科术语' % gloss[w])
        else:
            e['reg_reason'] = custom_reason.get(w) or reason_pool.get((w, val))
        if not e['reg_reason']:
            raise SystemExit('%r 缺少与档位 %s 对应的语体理由' % (w, val))
        # 该字段只保证落段器接受这条记录；它不是语体理由。
        if not str(e.get('reason', '')).strip():
            e['reason'] = '感情色彩默认中性；语体裁定见 reg_reason'
    # 不在三个少数档里的词：显式写「中性」并留降级理由。省略 reg 只能表示
    # 「没有特别裁定」，不能兼任「撤掉上一轮的少数档标签」（_gen_sentiment 有守卫）。
    dropped = []
    for w, e in dec.items():
        if 'reg' in e and w not in (TERM | FORMAL | COLLOQ):
            e['reg'] = '中性'
            e['reg_reason'] = ('语体复核：本库义项为「%s」，未见足够明确的'
                               '术语、正式书面或口语印记，归中性' % gloss[w])
            dropped.append(w)
    # 感情色彩改判
    nfix = 0
    for w, (sub, reason) in SENT_FIX.items():
        e = dec.setdefault(w, {})
        e['sub'] = sub
        e['reason'] = reason
        nfix += 1

    led['_meta']['reg_scheme'] = (
        '语体色彩第二稿（第七十轮·第二稿）拆四档：学术术语 / 书面语 / 口语 / 中性。'
        '判据见 tools/_audit/reg_reclassify.py 头部的说明与下方三个集合；'
        '归属优先级 术语 > 书面语 > 口语 > 中性。'
        '不在三档里的词取默认「中性」。')
    led['_meta']['coverage'] = (
        '形容词为全量逐词裁定（438 词，四档各留一行理由）；'
        '名词/动词只登记带评价色彩的裁定，其余取默认「中性的」；'
        '语体色彩登记带语域印记的词（学术术语/书面语/口语），其余取默认「中性」。')

    tmp = D('data', 'sentiment_decisions.json') + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(tmp, D('data', 'sentiment_decisions.json'))
    print('语体色彩重裁：学术术语 %d / 书面语 %d / 口语 %d' % (n['学术术语'], n['书面语'], n['口语']))
    print('撤回落默认（中性）的旧「书面语」标注：%d 词' % len(dropped))
    print('感情色彩改判：%d 词' % nfix)
    print('台账现共 %d 条' % len(dec))


if __name__ == '__main__':
    main()
