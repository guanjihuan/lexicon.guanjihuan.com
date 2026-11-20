#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off applier for the 5th curation round (2026-11-12).

Applies the manual audit conclusions to the three hand-maintained sources:

  data/curation.json      `fix` 段 —— 原 800 词表的释义修正（+ plateaus → plateau 改名）
  tools/_gen_recat.py     T / KEEP / SKIP —— 词性与感情色彩标注
  tools/_gen_additions.py T —— 增补词（801 起）的词性、感情色彩与释义

Policy applied in this round
---------------------------
1. 感情色彩只标注**明确**的褒义/贬义；客观描述性、程度性词汇（significant、valid、
   crucial、main、ambiguous、controversial…）一律标「中性的」。
2. 词性按词典标准判定：多义词取学术语域下的主导词性，释义只列该词性的义项；
   连接副词（however / moreover / hence / by contrast…）归入副词，真连词留在连词，
   纯介词与介词短语（via / in accordance with / despite…）不参与词性索引。
3. 释义只保留准确义项：删除误译、串味义项与口语化表述，补上学术常用义项。

Run:  python3 tools/_round5.py
Then: python3 tools/_gen_additions.py && python3 tools/_gen_recat.py &&
      python3 tools/curate.py && python3 tools/make_data.py &&
      node tools/dom_smoke_test.js

*** 已退役（2026-11-13）：第五轮改动早已应用并定稿，后续第六/七/八轮在此基础上又重新
*** 校订了其中多条释义（分隔符口径从「；」改为「；」+「，」等）。再跑本脚本会把那些
*** 更新回滚成第五轮的中间态（例如 regime / content / subject / catalogue / a posteriori），
*** 还会往 fix 段写入已删词。留档仅供参考，请勿再次运行。
"""
import sys
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

if not os.environ.get('WL_ROUND5_OVERRIDE'):
    # 防误跑守卫：见文件头「已退役」说明。确要重放（如考古第五轮状态）时
    # 用 WL_ROUND5_OVERRIDE=1，跑完必须重跑 _gen_* → curate.py → make_data.py 校验。
    sys.exit('tools/_round5.py 已退役（第五轮改动已应用且被后续轮次覆盖），不要重放。'
             '如确需考古重放，用 WL_ROUND5_OVERRIDE=1。')

# ---------------------------------------------------------------- 原 800 词的释义修正
# key = data/words800.json 里的原始拼写（改名过的词用改名前的写法）
SENSE_FIX = {
    'comment': ["评论；评述", "发表意见；作出评价"],
    'dictate': ["影响；决定；规定", "命令；下令", "口述；口授"],
    'illustrate': ["（尤指用例子）说明，阐明", "（用图表、插图等）加以说明，图解"],
    'yield': ["产生；导致（结果、收益）", "出产；产出", "屈服；让步"],
    'unexpectedly': ["意外地，出乎意料地"],
    'substantial': ["大的；可观的；重大的；实质的", "价值大的"],
    'amenable': ["顺从的；易接受建议的", "（对某事）易于接受的；可供…处理的"],
    'competitive': ["竞争的；竞赛的", "有竞争力的"],
    'exploit': ["利用；开发；发挥", "剥削；滥用（权力等）"],
    'ingredient': ["（食品的）成分，原料", "（构成的）要素；组成部分"],
    'render': ["使成为；使变得；使处于某种状态", "提供；给予（帮助、服务）", "呈现；使呈现为"],
    'ingenious': ["（方法等）巧妙的；有创造力的", "（物品等）制作精巧的"],
    'discipline': ["纪律；规范；约束", "（尤指大学或学院设立的）专业；学科"],
    'interpret': ["解释；解读；阐释", "口译；笔译"],
    'composite': ["复合的；由不同部分组成的", "（由不同部分组成的）混合物；合成物；综合体"],
    'leverage': ["利用；借助（条件、资源）实现目标", "发挥杠杆作用；使…产生杠杆效应"],
    'implementation': ["执行，履行；实施，贯彻；生效；完成"],
    'permanently': ["永久地；长期地；长久地"],
    'witness': ["目击，看到（尤指事故或犯罪）；见证"],
    'complimentary': ["赞美的；赞赏的；恭维的", "免费的；赠送的"],
    'merely': ["仅仅；只不过"],
    'plethora': ["大量；充足", "过多；过剩"],
    'concomitant': ["同时发生的；伴随的，相伴的"],
    'necessarily': ["不可避免地，必然地"],
    'in situ': ["在原处；就地；在现场"],
    'pedagogical': ["教学的；教育学的；教学法的", "起教育作用的；用于教学的"],
    'invoke': ["援引；引用（法律、条文、理论）", "唤起；引起；使人想起", "诉诸；祈求"],
    'outline': ["提纲；概要；要点", "（对某事的）大致轮廓；概述"],
    'paradigm': ["范式；典范", "（语法或词形变化的）范例；典型"],
    'schematic': ["示意的；简图的；图解的"],
    'evaluate': ["评估；评价；估计"],
    'be endowed with sth': ["具有…的；天生具备…的（be endowed with）"],
    'distinct': ["明显的；清楚的；确切的", "不同的；截然不同的（distinct from）"],
    'harbor': ["包含、庇护；窝藏"],
    'overlook': ["忽视；忽略；未被注意到", "俯瞰；俯视"],
    'excess': ["过分；过量；过度", "多余的，额外的（作定语时）"],
    'quantify': ["量化；确定…的数量；测定"],
    'spark': ["火花；火星", "导火线；引发因素；激起的动因（a spark of interest）"],
    'instrumental': ["起重要作用的；起决定作用的；有帮助的"],
    'insofar as': ["就…而言；据…所知", "在…的范围内；到…的程度"],
    'notwithstanding': ["尽管；不管"],
    'catalogue': ["目录；名录；清单", "一系列，一连串（坏事情）"],
    'correspondence': ["（两个事物之间的）关联；对应", "通信；往来信件"],
    'cement': ["加强，巩固（协议或友谊）", "黏合；凝结"],
    'successively': ["连续；先后；一个接一个地"],
    'coordinate': ["协调；使相配合"],
    'whereas': ["然而；不过；反之"],
    'latter': ["（提及的两者中的）后者；后者的", "后半程的，靠后的，末尾的"],
    'sequence': ["一连串；一系列；顺序；次序"],
    'subject': ["（讨论、考虑或研究的）主题，话题；问题；题目", "学科；科目", "（语法）主语"],
    'validity': ["有效性；效度", "正当性；合理性；效力"],
    'substitution': ["替代；取代；替换"],
    'nonetheless': ["然而，但是；尽管如此"],
    'separate': ["各自的；单独的，不同的"],
    'emanate': ["散发；发出（光、热、气味等）", "源于；出自（emanate from）"],
    'respect': ["尊重；重视", "涉及；关于（in this respect 就…而言）"],
    'construct': ["建造；构筑；构成，组成", "编造，杜撰"],
    # （infancy 已在第三轮删除，不再进 fix 段 —— 留着会让重放脚本往 curation.json 写死键）
    'content': ["满意的；满足的"],
    'either': ["也（用于否定句）；两者之一"],
    'feature': ["特点；特征", "（报刊、广播的）专题节目；特辑"],
    'favour': ["支持；赞成；主张", "偏爱；对…有利（in favor of）"],
    'a posteriori': ["事后推理的；凭经验的（与 a priori 相对）", "事后地；由果及因"],
    'metric': ["指标；度量指标；度量标准", "公制的，米制的"],
    'segment': ["（群体或事物的）部分；片段", "（市场的）细分"],
    'expedient': ["权宜的；应急的；为求方便而采取的"],
    # 括号内的英文用法提示格式统一 / 修正中英混排
    'reside': ["居住；存在于…之中（reside in）"],
    'snapshot': ["快照；简要情况；概貌（a snapshot of … 概貌）"],
    'metaphor': ["隐喻；比喻（metaphor of … 比喻）"],
    'irrespective': ["不管；不理会（irrespective of）"],
    'pave': ["为…铺平道路；为…创造条件（pave the way for）"],
    'regime': ["（物理、化学）状态；状态区间"],
    'onset': ["开始；起始；发作（the onset of … 开始）"],
}

# ---------------------------------------------------------------- 词性 / 感情色彩
# (word, pos, sub)  —— 写进 tools/_gen_recat.py 的 T 表
RECAT_T = [
    # 介词短语不再按「副词」归类
    ("a priori", "形容词", "中性的"),
    ("endowed with", "形容词", "中性的"),
    ("a posteriori", "形容词", "中性的"),
    # 客观描述性形容词：取消「积极的」
    ("unprecedented", "形容词", "中性的"),
    ("paramount", "形容词", "中性的"),
    ("drastic", "形容词", "中性的"),
    ("state-of-the-art", "形容词", "中性的"),
    ("vital", "形容词", "中性的"),
    ("critical", "形容词", "中性的"),
    ("pivotal", "形容词", "中性的"),
    ("representative", "形容词", "中性的"),
    ("feasible", "形容词", "中性的"),
    ("indispensable", "形容词", "中性的"),
    ("cutting-edge", "形容词", "中性的"),
    ("versatile", "形容词", "中性的"),
    ("spectacular", "形容词", "中性的"),
    ("imperative", "形容词", "中性的"),
    ("adequate", "形容词", "中性的"),
    ("concise", "形容词", "中性的"),
    ("intelligible", "形容词", "中性的"),
    ("eligible", "形容词", "中性的"),
    ("compact", "形容词", "中性的"),
    ("hands-on", "形容词", "中性的"),
    ("fertile", "形容词", "中性的"),
    ("viable", "形容词", "中性的"),
    ("superior", "形容词", "积极的"),
    # 描述性 / 中性语境词：取消「消极的」
    ("controversial", "形容词", "中性的"),
    ("daunting", "形容词", "消极的"),
    ("intricate", "形容词", "中性的"),
    ("ambiguous", "形容词", "中性的"),
    ("equivocal", "形容词", "中性的"),
    ("enigmatic", "形容词", "中性的"),
    ("formidable", "形容词", "中性的"),
]

# 写进 tools/_gen_recat.py 的 KEEP 表（词条已在此表中，直接改标注）
RECAT_KEEP = {
    "compelling": {"sub": "积极的"},
    "crucial": {"pos": "形容词", "sub": "中性的"},
    "flexible": {"pos": "形容词", "sub": "中性的"},
    "grand": {"sub": "积极的"},
}

# 介词短语：不参与词性索引（与 due to / via / regarding / onto 同处理）
RECAT_SKIP = {"in accordance with", "in conjunction with"}

# ---------------------------------------------------------------- 增补词（801 起）
# (word, pos, sub, gloss)
GEN_ADD = [
    ("approach", "动词", None, "接近；着手研究；着手处理；处理"),
    ("trace", "动词", None, "追踪；追溯；描摹；查明；探明"),
    ("objective", "名词", None, "目标；目的；宗旨"),
    ("standard", "名词", None, "标准；水平；准则；规格"),
    ("available", "形容词", "中性的", "可获得的；可用的；有空的"),
    ("central", "形容词", "中性的", "中心的；核心的；主要的"),
    ("explicit", "形容词", "中性的", "明确的；清楚的；直言的"),
    ("main", "形容词", "中性的", "主要的；最重要的；总部的"),
    ("major", "形容词", "中性的", "主要的；重大的；首要的；主修的"),
    ("natural", "形容词", "中性的", "自然的；天然的；正常的；固有的"),
    ("necessary", "形容词", "中性的", "必要的；必需的；必然的"),
    ("potential", "形容词", "中性的", "潜在的；可能的；潜在的事物"),
    ("practical", "形容词", "中性的", "实际的；实用的；可行的"),
    ("primary", "形容词", "中性的", "主要的；初级的；首要的"),
    ("principal", "形容词", "中性的", "主要的；首要的；首席的；主体的"),
    ("reasonable", "形容词", "中性的", "合理的；讲道理的；公道的"),
    ("relevant", "形容词", "中性的", "相关的；切题的；有价值的"),
    ("reliable", "形容词", "中性的", "可靠的；可信赖的；稳健的"),
    ("significant", "形容词", "中性的", "显著的；重要的；有意义的"),
    ("simple", "形容词", "中性的", "简单的；朴素的；单一的"),
    ("sufficient", "形容词", "中性的", "足够的；充分的"),
    ("suitable", "形容词", "中性的", "合适的；适宜的；相称的"),
    ("typical", "形容词", "中性的", "典型的；有代表性的；一贯的"),
    ("valid", "形容词", "中性的", "有效的；正当的；确凿的"),
    ("wide", "形容词", "中性的", "广泛的；宽广的；大量的"),
    ("wrong", "形容词", "消极的", "错误的；不适当的；不对的"),
    ("meaningful", "形容词", "中性的", "有意义的；意味深长的"),
    ("deliberately", "副词", None, "故意地；蓄意地；深思熟虑地"),
    ("eventually", "副词", None, "最终；终于；到最后"),
    ("synthesize", "动词", None, "综合；归纳；综合概括；合成"),
    ("corpus", "名词", None, "语料库；语料；文库；汇编"),
    ("synthesis", "名词", None, "综合；综合产物；综合论述；合成"),
    ("integrity", "名词", None, "完整性；诚信；正直"),
    ("provenance", "名词", None, "来源；出处；来源信息"),
    ("redundancy", "名词", None, "冗余；多余；备用；备用装置"),
    ("arguably", "副词", None, "可以说；有理由认为；或许"),
    ("given that", "连词", None, "鉴于；考虑到；假定；假设"),
    ("as long as", "连词", None, "只要；以…为条件；除非（不…）"),
    ("offset", "动词", None, "抵消；补偿；与…相抵"),
    ("quote", "动词", None, "引用；引述；援引；（给…）报价"),
    ("confound", "动词", None, "混淆；使困惑；使（两个因素）混杂、无法区分"),
    ("dataset", "名词", None, "数据集；资料集"),
    ("inference", "名词", None, "推论；结论；推断（过程）"),
    ("retrospective", "形容词", "中性的", "回顾的；回溯性的"),
    ("uncertainty", "名词", None, "不确定性；（程度上的）不确定；变数"),
    ("citation", "名词", None, "引用；引文；引注（出处标注）"),
    ("proposition", "名词", None, "命题；主张；提议"),
    ("applicable", "形容词", "中性的", "适用的；可应用的；切合实际的"),
    ("deterministic", "形容词", "中性的", "确定性的；可确定的；无随机性的"),
    ("dependent", "形容词", "中性的", "依赖的；取决于…的；受…制约的"),
    ("versus", "副词", None, "与…相对；与…相比；对…"),
    ("as a result", "副词", None, "因此；从而"),
    ("present", "动词", None, "提出；呈现；举出（证据、观点）"),
    ("type", "名词", None, "类型；种类；类别"),
    ("replicate", "动词", None, "复现；重复（实验）；重复验证"),
    ("equivalent", "形容词", "中性的", "等同的；相同的；相当的"),
    ("inverse", "名词", None, "反面；相反事物；逆（逆数、逆函数）"),
    ("solely", "副词", None, "仅仅；只是；完全地"),
    ("evidently", "副词", None, "显然；看来；从…可以看出"),
    ("for example", "副词", None, "例如；比如"),
    ("alternative", "形容词", "中性的", "可供选择的；替代的"),
    ("for instance", "副词", None, "例如；比如"),
    # 连接副词：从「连词」改判为「副词」
    ("however", "副词", None, "然而；不过；可是"),
    ("moreover", "副词", None, "而且；此外；再者"),
    ("hence", "副词", None, "因此；所以；由此"),
    ("yet", "副词", None, "然而；不过；还；仍然"),
    ("so", "副词", None, "因此；所以"),
    ("besides", "副词", None, "而且；此外"),
    ("by contrast", "副词", None, "相比之下；与此形成对照"),
    ("in contrast", "副词", None, "与…形成对比；相反"),
    ("in addition", "副词", None, "此外；而且"),
    ("on the other hand", "副词", None, "另一方面；相反"),
    ("in other words", "副词", None, "换句话说；也就是说"),
    ("in conclusion", "副词", None, "总之；综上所述"),
    ("in short", "副词", None, "简言之；总之"),
    ("to sum up", "副词", None, "总而言之；概括来说"),
    ("that is", "副词", None, "也就是说；换句话说"),
    # 纯介词：不参与词性索引（与 due to / via / regarding 同处理）
    ("despite", None, None, "尽管；不管"),
]

# ---------------------------------------------------------------- 应用
log = []

# 1) curation.json 的 fix 段
cur_path = D('data', 'curation.json')
cur = json.load(open(cur_path, encoding='utf-8'))
fix = cur['fix']
for word, senses in SENSE_FIX.items():
    if word not in fix:
        fix[word] = {}
    fix[word]['senses'] = list(senses)
    log.append('fix senses: %s' % word)

# plateaus（复数词形）改收录单数 plateau
if 'plateaus' in fix and 'word' not in fix['plateaus']:
    fix['plateaus']['word'] = 'plateau'
    log.append('rename: plateaus -> plateau')
if 'plateaus' in cur.get('core', []):
    cur['core'] = ['plateau' if w == 'plateaus' else w for w in cur['core']]
# 幂等：第五轮落点版本是 9；重放时只在版本号落后时推进，避免重复运行无限 +1
if (cur.get('version') or 0) < 9:
    cur['version'] = 9
with open(cur_path, 'w', encoding='utf-8') as f:
    json.dump(cur, f, ensure_ascii=False, indent=2)
    f.write('\n')

# 2) tools/_gen_recat.py
rec_path = D('tools', '_gen_recat.py')
src = open(rec_path, encoding='utf-8').read()

# 2a) 改写 T 表中已有条目的标注；表中没有的按词性小节插入
SECTION_HEAD = {
    '形容词': '# ---------------------------------------------------------------- 形容词',
    '动词': '# ---------------------------------------------------------------- 动词',
    '名词': '# ---------------------------------------------------------------- 名词',
    '副词': '# ---------------------------------------------------------------- 副词',
    '连词': '# ---------------------------------------------------------------- 连词',
}
for word, pos, sub in RECAT_T:
    pat = re.compile(r'^\("%s","[^"]+",(?:None|"[^"]*")\),$' % re.escape(word), re.M)
    new = '("%s","%s",%s),' % (word, pos, 'None' if not sub else '"%s"' % sub)
    if pat.search(src):
        src = pat.sub(lambda m: new, src, count=1)
        log.append('recat T edit: %s -> %s/%s' % (word, pos, sub))
    else:
        head = SECTION_HEAD[pos]
        if head not in src:
            raise SystemExit('recat: section header not found for %r' % pos)
        src = src.replace(head, head + '\n' + new, 1)
        log.append('recat T add: %s -> %s/%s' % (word, pos, sub))

# 2b) 介词短语：从 T 表移除，写进 SKIP
for word in RECAT_SKIP:
    pat = re.compile(r'^\("%s","[^"]+",(?:None|"[^"]*")\),$' % re.escape(word), re.M)
    if pat.search(src):
        src = pat.sub('', src, count=1)
        log.append('recat T removed (prepositional phrase): %s' % word)

skip_pat = re.compile(r'^SKIP = \{([^}]*)\}$', re.M)
m = skip_pat.search(src)
items = [s.strip() for s in m.group(1).split(',') if s.strip()]
for word in sorted(RECAT_SKIP):
    if '"%s"' % word not in items:
        items.append('"%s"' % word)
src = skip_pat.sub(lambda mm: 'SKIP = {%s}' % ', '.join(sorted(items, key=lambda s: s.strip('"'))),
                   src, count=1)

# 2c) KEEP 表
for word, patch in RECAT_KEEP.items():
    pat = re.compile(r'^\s*"%s": \{[^}]*\},$' % re.escape(word), re.M)
    if not pat.search(src):
        raise SystemExit('recat: KEEP entry not found for %r' % word)
    body = ', '.join('"%s": "%s"' % (k, v) for k, v in patch.items())
    src = pat.sub(lambda mm: ' "%s": {%s},' % (word, body), src, count=1)
    log.append('recat KEEP edit: %s -> %s' % (word, patch))

with open(rec_path, 'w', encoding='utf-8') as f:
    f.write(src)

# 3) tools/_gen_additions.py
add_path = D('tools', '_gen_additions.py')
asrc = open(add_path, encoding='utf-8').read()
for word, pos, sub, gloss in GEN_ADD:
    pat = re.compile(r'^\("%s",(?:"[^"]+"|None),(?:None|"[^"]*"),".*"\),$' % re.escape(word), re.M)
    if not pat.search(asrc):
        raise SystemExit('additions: target line not found for %r' % word)
    new = '("%s",%s,%s,"%s"),' % (word, 'None' if not pos else '"%s"' % pos,
                                  'None' if not sub else '"%s"' % sub, gloss)
    asrc = pat.sub(lambda mm: new, asrc, count=1)
    log.append('additions edit: %s' % word)
with open(add_path, 'w', encoding='utf-8') as f:
    f.write(asrc)

print('round5 edits applied: %d' % len(log))
for line in log:
    print('  ' + line)
