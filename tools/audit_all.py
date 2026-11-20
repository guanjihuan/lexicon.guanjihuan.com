# -*- coding: utf-8 -*-
"""全库词汇内容体检：跨文件一致性 + 新增词深审前置检查。

判据口径**一律复用生产代码**，不另写一套简化版：
  * 语体色彩取值域＝`tools/_gen_sentiment.py` 的 REG_VALS（四档，含「学术术语」）；
  * 「例句是否用了目标词」＝`tools/merge_examples.py` 的 `contains_word()`
    （词干 + 不规则词形 + 前缀 + 短语窗口，与例句合并闸门同口径）。

本脚本此前自带一套简化判据（reg 三档、无屈折还原），导致 257 条 reg 假阳性与
16 条「例句未含目标词」假阳性——**工具判据过期比没有工具更危险**。改口径后
剩 13 条，其中仍多为设计上允许的项（见各处注释），需逐条回源判断真伪。
"""
import json, re, sys, os
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根
D = os.path.join(R, 'data')
sys.path.insert(0, os.path.join(R, 'tools'))

# 取「例句是否用了目标词」的判据：复用 tools/merge_examples.py 的 contains_word()。
# **不能直接 import 该模块**——它的模块体在文件后半段执行合并写盘，import 即写盘。
# 故只取模块前半段的「常量 + 函数定义」到独立命名空间，定义齐备、副作用为零。
def _load_defs_only(relpath, marker):
    """执行目标脚本中 marker 之前的部分（常量与函数定义），跳过其模块体。"""
    path = os.path.join(R, relpath)
    src = open(path, encoding='utf-8').read()
    i = src.find(marker)
    assert i > 0, '未在 %s 中找到模块体起点标记 %r' % (relpath, marker)
    ns = {'__name__': os.path.basename(relpath) + '_defs', '__file__': path}
    exec(compile(src[:i], path, 'exec'), ns)
    return ns

_mer = _load_defs_only('tools/merge_examples.py',
                        '# ---------------------------------------------------------------- 1. read parts')
contains_word = _mer['contains_word']

# 取 reg 取值域：**不 import _gen_sentiment**（那是落段器，import 会执行它的写盘逻辑）；
# 直接从源文件里正则取常量，保证与生产口径同源又不触发副作用。
def _read_reg_vals():
    src = open(os.path.join(R, 'tools', '_gen_sentiment.py'), encoding='utf-8').read()
    m = re.search(r"REG_VALS\s*=\s*\(([^)]*)\)", src)
    assert m, '未能从 tools/_gen_sentiment.py 解析 REG_VALS'
    return tuple(re.findall(r"'([^']+)'", m.group(1)))
REG_VALS = _read_reg_vals()
def L(n): return json.load(open(os.path.join(D, n), encoding='utf-8'))

words = L('words.json'); cats = L('cats.json'); ex = L('examples.json')
cur = L('curation.json'); prop = L('core_proposals.json'); core = L('core_decisions.json')
sent = L('sentiment_decisions.json')
# 允许在中文译文里保留的拉丁缩写：报告规范 / 生物学术语等专名
ZH_KEEP_LATIN = {'DNA', 'RNA', 'PRISMA', 'CONSORT', 'STROBE'}
fails = []
def bad(cat, msg): fails.append((cat, msg))

wm = {w['word']: w for w in words}
cm = {c['word']: c for c in cats}
pm = {p['word']: p for p in prop['rows']}
em = set(ex.keys())
print('words %d cats %d examples %d props %d' % (len(words), len(cats), len(ex), len(prop['rows'])))

# 1 集合一致性
# cats.json 是**词性索引**：null 族（单词介词与介词性固定短语）按设计不入索引，
# 故 words 与 cats 的差集＝null 族是预期的，不算不一致。
null_family = {w for w, v in wm.items() if v.get('pos') is None}
only_words = set(wm) - set(cm)
if only_words - null_family:
    bad('sets', 'words/cats 词集不同(非 null 族): only-words=%s' % sorted(only_words - null_family)[:10])
if set(cm) - set(wm):
    bad('sets', 'words/cats 词集不同: only-cats=%s' % sorted(set(cm)-set(wm))[:10])
if set(wm) != em: bad('sets', 'words/examples 词集不同: only-words=%s only-ex=%s' % (sorted(set(wm)-em)[:10], sorted(em-set(wm))[:10]))
if set(wm) != set(pm): bad('sets', 'words/core_proposals 词集不同')

# 2 重复词形 / 大小写 / 空白
seen = {}
for w in words:
    ww = w['word']
    if ww in seen: bad('dup', '词表重复: %s' % ww)
    seen[ww] = 1
    if ww != ww.strip(): bad('ws', '词形带空白: %r' % ww)
    # 词形大小写：**全大写缩写**（CONSORT、STROBE）与**专名**（Monte Carlo）
    # 是正确写法，判据只抓「首字母大写＋内部还混着小写」的错拼（monte Carlo）。
    is_allcaps = ww.isupper()
    is_proper = re.match(r'^[A-Z][a-z]+(?: [A-Z][a-z]+)*$', ww) is not None
    if ww != ww.lower() and not ww.startswith('N') and ww not in ('I',):
        if re.search(r'[A-Z]', ww[1:]) and not (is_allcaps or is_proper):
            bad('case', '词形内部大写: %s' % ww)

# 3 字段取值域
POS = {'形容词','名词','动词','副词','连词',None}
REG = set(REG_VALS)
SUB = {'积极的','消极的','争议性的','中性的',None}
for w in words:
    if w.get('pos') not in POS: bad('pos', '%s pos=%r' % (w['word'], w.get('pos')))
    if w.get('reg') not in REG: bad('reg', '%s reg=%r' % (w['word'], w.get('reg')))
    if w.get('sub') not in SUB: bad('sub', '%s sub=%r' % (w['word'], w.get('sub')))
    if not w.get('senses'): bad('senses', '%s senses 空' % w['word'])
    if len(w.get('links') or []) != 3: bad('links', '%s links=%d' % (w['word'], len(w.get('links') or [])))
    if w.get('core') is not None and not isinstance(w['core'], bool): bad('core', '%s core 类型' % w['word'])
    # 词性与情感档：形容词/名词/动词必须有 sub
    if w.get('pos') in ('形容词','名词','动词') and w.get('sub') is None:
        bad('subrule', '%s(%s) 缺 sub' % (w['word'], w['pos']))
    if w.get('pos') in ('副词','连词',None) and w.get('sub') is not None:
        bad('subrule', '%s(%s) 多余 sub=%s' % (w['word'], w['pos'], w['sub']))
    # 语体：每词都有
    if w.get('reg') is None: bad('reg', '%s reg 空' % w['word'])

# 4 words vs cats 字段一致
for w in words:
    c = cm.get(w['word'])
    if not c: continue
    if c.get('pos') != w.get('pos'): bad('w/c', '%s pos 不一致 %r/%r' % (w['word'], w.get('pos'), c.get('pos')))
    if c.get('sub') != w.get('sub'): bad('w/c', '%s sub 不一致 %r/%r' % (w['word'], w.get('sub'), c.get('sub')))
    if c.get('reg') != w.get('reg'): bad('w/c', '%s reg 不一致 %r/%r' % (w['word'], w.get('reg'), c.get('reg')))
    if c.get('gloss') != w.get('catGloss'): bad('w/c', '%s gloss 不一致' % w['word'])

# 5 台账覆盖：上一轮带非中性标签的词必须在 sentiment 台账显式出现
sd = sent.get('decisions') if isinstance(sent, dict) else None
if sd is None and isinstance(sent, dict):
    for k,v in sent.items():
        if isinstance(v, (dict,list)) and k not in ('_summary','_comment'): sd = v
sent_words = set(sd.keys()) if isinstance(sd, dict) else set()
need = {w['word'] for w in words if w.get('sub') in ('积极的','消极的','争议性的')}
miss = need - sent_words
if miss: bad('ledger', '非中性词未入台账 %d: %s' % (len(miss), sorted(miss)[:20]))

# 6 例句结构
for k, v in ex.items():
    if not isinstance(v, list): bad('ex', '%s 例句非列表' % k); continue
    if len(v) != 3: bad('ex', '%s 例句数=%d' % (k, len(v)))
    for i, s in enumerate(v):
        if not isinstance(s, dict) or 'en' not in s or 'zh' not in s: bad('ex', '%s[%d] 结构' % (k, i)); continue
        if not s['en'].strip() or not s['zh'].strip(): bad('ex', '%s[%d] 空句' % (k, i))
        if re.search(r'[\u4e00-\u9fff]', s['en']): bad('ex', '%s[%d] en 含中文' % (k, i))
        if not re.search(r'[\u4e00-\u9fff]', s['zh']): bad('ex', '%s[%d] zh 无中文' % (k, i))
        # zh 里残留未翻译英文：**专名/术���缩写允许保留**（CONSORT、STROBE、
        # PRISMA、DNA 等报告规范与生物学术语，在中文语境里保留拉丁缩写是正确写法，
        # 且本库该批词的释义本身带中文说明）。只有「非专名的普通英文词」才该译。
        for m in re.finditer(r'[A-Za-z]{2,}', s['zh']):
            tok = m.group(0)
            if tok in ZH_KEEP_LATIN:
                continue
            bad('zhres', '%s[%d] zh 残留英文 %r' % (k, i, tok))

# 7 例句是否含目标词（屈折还原口径＝merge_examples.contains_word，与例句合并闸门同源）
missing_in_ex = []
for k, v in ex.items():
    if not isinstance(v, list): continue
    hit = sum(1 for s in v if isinstance(s, dict) and contains_word(s.get('en', ''), k))
    if hit < 2: missing_in_ex.append((k, hit))
if missing_in_ex:
    bad('exhit', '例句未含目标词 %d 词: %s' % (len(missing_in_ex), missing_in_ex[:25]))

# 8 核心层：words.core 与 core_decisions 台账一致。
# 台账条目字段是 `verdict`（'core'/'noncore'）与 `reason`——**不是** `final_core`
# （此前脚本查的是 final_core，永远 0 命中，该检查等于没做）。
dec = core.get('decisions') if isinstance(core, dict) else None
if isinstance(dec, dict):
    for w, v in dec.items():
        if w in wm and isinstance(v, dict) and 'verdict' in v:
            if bool(v['verdict'] == 'core') != bool(wm[w].get('core')):
                bad('core', '%s core 与台账不符 %s/%s' % (w, v['verdict'], wm[w].get('core')))
    # 台账覆盖：全库每词都该有裁定
    no_verdict = [w for w in wm if w not in dec]
    if no_verdict:
        bad('ledger', '核心层台账缺词 %d: %s' % (len(no_verdict), sorted(no_verdict)[:10]))

print('--- 问题 ---')
from collections import Counter
cnt = Counter(c for c,_ in fails)
for c, n in cnt.most_common(): print('%-10s %d' % (c, n))
for c, m in fails[:80]: print('  [%s] %s' % (c, m))
print('TOTAL %d' % len(fails))
# 作为回归套件，发现问题时必须**非零退出**（此前一律返回 0，无法接进常规回归）。
sys.exit(1 if fails else 0)
