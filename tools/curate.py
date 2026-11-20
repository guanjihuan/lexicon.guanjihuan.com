#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the human curation manifest to the raw extracts.

Inputs (never modified):
  data/words800.json     raw 800-word list scraped from guanjihuan.com/archives/4418
  data/categorized.json   raw 344-word classified selection from .../archives/24732
  data/curation.json      manual edit list (remove / fix / recat / add)

Outputs (regenerated):
  data/words.json         curated word list, each record carrying pos / sub / catGloss
  data/cats.json          curated classified subset (the "分类" module)

Word ids (`num`) are stable: existing entries keep their source number so that
users' localStorage progress survives a curation change; newly added entries get
fresh numbers continuing from the current maximum.

Run:  python3 tools/curate.py
"""
import json, os, re, sys, unicodedata

# 控制台输出钉 UTF-8（Windows GBK 控制台上中文报错会变 mojibake，见 _console_utf8.py）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json, require_curation_segments  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

raw_words = load_json(D('data', 'words800.json'))
raw_cats = load_json(D('data', 'categorized.json'))
cur = load_json(D('data', 'curation.json'))
# 段完整性闸（第八轮）：七段必须**在**（可以为空）。缺段与空段必须区分——
# 空数组＝确实没有覆盖，缺段＝口径不明。缺段时各段 .get(段, 默认值) 的兜底会
# **静默**换一套口径、产出完全不同的词表（实测退出码全是 0）：
#   丢 recat 段   → 分类 2158→1896（262 词悄悄没了词性/感情色彩标注）
#   丢 core 段    → 核心层 1060→968（92 个显式提入的词悄悄降级）
#   丢 noncore 段 → 核心层 1060→2045（985 个显式排除的词悄悄回核）
require_curation_segments(cur, ('remove', 'fix', 'recat', 'add', 'core', 'noncore', 'sentiment'))

# 段里的**元素**类型也要有闸：remove/core/noncore 是词形列表，元素写成对象
# 会让 set()/in 判定抛裸栈（TypeError: unhashable type）而不是人话报错。
for _seg in ('remove', 'core', 'noncore'):
    _bad = [x for x in cur.get(_seg, []) if not isinstance(x, str)]
    if _bad:
        sys.exit('curation.json 的 %r 段里必须是词形字符串，第 %r 这条是 %s'
                 % (_seg, _bad[0], type(_bad[0]).__name__))
REMOVE = set(cur.get('remove', []))
FIX = cur.get('fix', {})
RECAT = cur.get('recat', {})
ADD = cur.get('add', [])
# noncore：核心高频层的显式排除段（册卅三轮引入，由 tools/_gen_core.py 依
# data/core_decisions.json 台账整体重写；**空段**=没有显式排除=旧行为不变；
# 但**缺段**是口径不明，上面的段闸已拦下）
NONCORE_EXCLUDE = {str(x).strip().lower() for x in cur.get('noncore', [])}
# 第七十轮新增：感情色彩 / 语体色彩逐词裁定段（键＝词形，值＝{"sub":…,"reg":…,"reason":…}）。
# 这两维的真源是 data/sentiment_decisions.json 台账，tools/_gen_sentiment.py 由台账
# 整体重写本段（与 core/noncore 段同一规矩：台账是手改的真源，段是它落进词表的通道）。
# 本段**覆盖** recat/add 段里带来的 sub（旧源站标签宽松），但只覆盖它显式给出的键。
SENTIMENT = cur.get('sentiment', {})
SUB_VALS = ('积极的', '消极的', '争议性的', '中性的')
REG_VALS = ('学术术语', '书面语', '口语', '中性')
# 感情色彩挂在这三类实词上；副词/连词/介词不带评价义（未标注）。
SUB_POS = ('形容词', '名词', '动词')
for _sw, _sd in SENTIMENT.items():
    if not isinstance(_sd, dict):
        sys.exit('sentiment 段里 %r 的值必须是对象（{"sub":…,"reg":…}），实际是 %s'
                 % (_sw, type(_sd).__name__))
    if 'sub' in _sd and _sd['sub'] not in SUB_VALS:
        sys.exit('sentiment 段里 %r 的 sub=%r 不合法，只能是 %s'
                 % (_sw, _sd['sub'], '／'.join(SUB_VALS)))
    if 'reg' in _sd and _sd['reg'] not in REG_VALS:
        sys.exit('sentiment 段里 %r 的 reg=%r 不合法，只能是 %s'
                 % (_sw, _sd['reg'], '／'.join(REG_VALS)))

# ---------------------------------------------------------------- helpers
# 少数词英美拼写不同：词表用美式，LDOCE / Cambridge 用英式 headword
BRITISH_ALIAS = {
    'catalog': 'catalogue',
    'favor': 'favour',
    'fulfill': 'fulfil',
    'skepticism': 'scepticism',
    'analog': 'analogue',
}

def slug(word):
    """'in accordance with' -> 'in-accordance-with' (LDOCE / Cambridge style)."""
    s = word.strip().lower()
    s = s.replace("'", '').replace('’', '')
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')

def mw_slug(word):
    """Merriam-Webster style: spaces -> %20, other chars kept."""
    s = word.strip().lower()
    s = s.replace(' ', '%20')
    return s

def dict_links(word):
    """Three dictionary links for a headword.

    词表统一用美式拼写（与 analyze / realize / recognize 一族以及国内教材一致），
    但 LDOCE 与 Cambridge 的词条用英式拼写做 headword，因此对少数两拼不同的词
    做一次别名映射；Merriam-Webster 是美式词典，直接用原词。
    """
    sl, mw = slug(word), mw_slug(word)
    uk = slug(BRITISH_ALIAS.get(word, word))
    return [
        'https://www.ldoceonline.com/dictionary/%s' % uk,
        'https://www.merriam-webster.com/dictionary/%s' % mw,
        'https://dictionary.cambridge.org/dictionary/english-chinese-simplified/%s' % uk,
    ]

def norm_senses(senses):
    """Normalise separators / whitespace and drop empties & duplicates.

    原始抓取里中文标点后常带一个空格（"试探； 试验"），统一清掉；
    半角分号统一为全角"；"，并保证标点后不残留空格。

    分隔符约定（全库统一，第六轮核对后确认原始数据本就符合）：
      "；" 分隔**不同义项**；"，" 分隔**同一义项内的同义说法**。
    例如 grand = "重大的；主要的；首要的；宏伟的，壮丽的；……"，
    对比 = "对照，对比"（两个义项同义，用逗号并列）。
    源站抽取本身即遵循该约定，因此不做"，" -> "；"的全局替换，
    否则会把同义并列拆成独立义项。

    入参必须是**列表**：早先写成字符串时会被逐字符拆成 ['释','义'] 两个义项，
    还能通过「有释义」的闸门、写进产物（实测）。故此直接拦下并说明写法。
    """
    if isinstance(senses, str):
        sys.exit('senses must be a list of strings, got a plain string: %r\n'
                 '        一条义项一个字符串，请写成 ["释义一", "释义二"]' % (senses,))
    out = []
    for s in senses or []:
        s = re.sub(r'\s+', ' ', str(s)).strip()
        s = s.replace(';', '；')
        s = re.sub(r'[；，、]\s*', lambda m: m.group(0)[0], s)   # 标点后不留空格
        s = re.sub(r'\s*([；，、])', r'\1', s)                 # 标点前不留空格
        s = re.sub(r'；\s*；', '；', s)
        s = s.strip('； ').strip()
        if not s:
            continue
        if s not in out:
            out.append(s)
    return out

# ---------------------------------------------------------------- 1. drop
dropped_words = []
kept = []
for w in raw_words:
    if w['word'] in REMOVE:
        dropped_words.append(w['word'])
        continue
    w['src_word'] = w['word']     # 记住原始拼写，改名后仍可追溯
    kept.append(w)
unknown_remove = REMOVE - {w['word'] for w in raw_words}
if unknown_remove:
    sys.exit('remove list mentions unknown words: %s' % sorted(unknown_remove))

kept_nums = {w['num'] for w in kept}

# ---------------------------------------------------------------- 2. fix
by_num = {w['num']: w for w in kept}
fixed_names = []
for src, patch in FIX.items():
    hits = [w for w in kept if w['word'] == src]
    if not hits:
        sys.exit('fix key not found in word list: %r' % src)
    for w in hits:
        if 'word' in patch:
            w['word'] = patch['word']
            fixed_names.append('%s -> %s' % (src, patch['word']))
        if 'senses' in patch:
            # 类型闸：senses 必须是列表。早先写成字符串时 list() 会把它逐字符
            # 拆成 ['释','义']，还能通过「有释义」的闸门写进产物（实测）。
            if not isinstance(patch['senses'], list):
                sys.exit('fix entry %r has a non-list "senses" (%s): 一条义项一个字符串，'
                         '请写成 ["释义一", "释义二"]'
                         % (src, type(patch['senses']).__name__))
            w['senses'] = list(patch['senses'])
        if 'notes' in patch:
            if not isinstance(patch['notes'], list):
                sys.exit('fix entry %r has a non-list "notes" (%s): 一条注解一个字符串，'
                         '请写成 ["注解一", "注解二"]'
                         % (src, type(patch['notes']).__name__))
            w['notes'] = list(patch['notes'])
        elif 'senses' in patch and 'notes' not in patch:
            pass  # keep existing notes

# ---------------------------------------------------------------- 3. build classified map
cat_by_num = {c['num']: dict(c) for c in raw_cats if c['num'] in kept_nums}
dropped_cats = [c['word'] for c in raw_cats if c['num'] not in kept_nums]

# ---------------------------------------------------------------- 4. recat
_add_words = {a.get('word') for a in ADD}
for word, patch in RECAT.items():
    hits = [w for w in kept if w['word'] == word]
    if not hits:
        if word in _add_words:
            sys.exit('recat key %r is an added word: its pos/sub truth source is the '
                     'T table in tools/_gen_additions.py (add segment), not the recat '
                     'segment (which _gen_recat.py rewrites wholesale); edit the T table'
                     % word)
        sys.exit('recat key not found in word list: %r' % word)
    for w in hits:
        # 空义项必须在此拦下：下面要读 senses[0] 建分类 gloss，否则裸 IndexError
        # 抢先于 finalise 的友好报错（「has no meaning after curation」）
        if not w.get('senses'):
            sys.exit('recat word %r has empty senses (fix 段把义项清空了?)' % word)
        c = cat_by_num.get(w['num'])
        if c is None:
            c = cat_by_num[w['num']] = {'num': w['num'], 'word': w['word'],
                                        'pos': None, 'sub': None, 'gloss': w['senses'][0]}
        if 'pos' in patch:
            c['pos'] = patch['pos']
        if 'sub' in patch:
            c['sub'] = patch['sub']
        if not c.get('gloss'):
            c['gloss'] = w['senses'][0]
        # 判为「无词性」的词必须**退出分类表**：分类索引面向实词，无词性的词
        # 留在 cats.json 里就是一条 pos=null 的分类条目（分类页按词性分组，
        # 它会落进一个空组）。口径与 add 段一致（add 段 pos 为空即不入
        # cat_by_num），也与正册「NO_POS 摘出 = pos null + catGloss null 双件」一致。
        if not c.get('pos'):
            cat_by_num.pop(w['num'], None)

# ---------------------------------------------------------------- 5. add
next_num = max(by_num) + 1
added = []
for a in ADD:
    # add 段的空义项必须在此拦下：下面要读 senses[0] 建分类 gloss，裸 IndexError
    # 会抢先于 finalise 的友好报错（「has no meaning after curation」）
    if not isinstance(a, dict):
        sys.exit('add 段里有非对象条目（应是 {"word":…,"senses":[…],"pos":…}），'
                 '这条是 %s：%r' % (type(a).__name__, a))
    _aword = a.get('word')
    if not _aword:
        sys.exit('add entry without a word: %r' % (a,))
    if not isinstance(a.get('senses'), list):
        sys.exit('add entry %r has a non-list "senses" (%s): 一条义项一个字符串，'
                 '请写成 ["释义一", "释义二"]'
                 % (_aword, type(a.get('senses')).__name__))
    if a.get('notes') is not None and not isinstance(a.get('notes'), list):
        sys.exit('add entry %r has a non-list "notes" (%s): 一条注解一个字符串，'
                 '请写成 ["注解一", "注解二"]'
                 % (_aword, type(a.get('notes')).__name__))
    _asenses = norm_senses(a.get('senses'))
    if not _asenses:
        sys.exit('add entry %r has empty senses (T 表/fix 段把义项清空了?)' % _aword)
    w = {
        'num': next_num,
        'word': _aword,
        'senses': _asenses,
        'links': dict_links(_aword),
        'notes': a.get('notes', []),
    }
    kept.append(w)
    # 无词性的条目（纯介词，如 despite / via / regarding）不进入分类索引
    if a.get('pos'):
        cat_by_num[next_num] = {
            'num': next_num, 'word': a['word'], 'pos': a.get('pos'),
            'sub': a.get('sub'), 'gloss': w['senses'][0],
        }
    added.append(a['word'])
    next_num += 1

# ---------------------------------------------------------------- 6. finalise
# 「核心词」= 源站分类精选 + 人工增补 + 清单里显式指定的核心词。
# 其余词条是源站 800 词全表里的补充词，同样有释义与词性，但不属于核心高频层。
CORE_EXTRA = set(cur.get('core', []))
# core 段与 remove/fix/recat 同等对待：引用已删/改名失踪的词形直接失败，
# 不许静默惰性残留（第四十九轮堵回『nail down/fierce』这类删词后 core 段孤儿回流）
_core_known = set()
for _w in kept:
    _core_known.add(_w['word'])
    if _w.get('src_word'):
        _core_known.add(_w['src_word'])
_orphan_core = CORE_EXTRA - _core_known
if _orphan_core:
    sys.exit('core entries reference unknown words (removed/renamed?): %s' % sorted(_orphan_core))
# noncore 段与 core 同等对待：孤儿拦截 + 两段互斥（同一词形不得既显式入核又显式排除）
_core_known_lc = {x.strip().lower() for x in _core_known}
_orphan_noncore = NONCORE_EXCLUDE - _core_known_lc
if _orphan_noncore:
    sys.exit('noncore entries reference unknown words (removed/renamed?): %s' % sorted(_orphan_noncore))
_clash = {str(x).strip().lower() for x in CORE_EXTRA} & NONCORE_EXCLUDE
if _clash:
    sys.exit('word(s) in both core and noncore segments: %s' % sorted(_clash))
_cat_nums = {c['num'] for c in raw_cats}   # 循环外一次性构建，勿在词表循环内重建
for w in kept:
    w['senses'] = norm_senses(w.get('senses'))
    if not w['senses']:
        sys.exit('word %r (%s) has no meaning after curation' % (w['word'], w['num']))
    w['links'] = dict_links(w['word'])
    w['notes'] = [re.sub(r'\s+', ' ', str(n)).strip() for n in (w.get('notes') or []) if str(n).strip()]
    c = cat_by_num.get(w['num'])
    if c:
        c['word'] = w['word']
        # 第二十六轮口径：分类视图释义唯一真源 = 整理后 senses[0]。
        # 此前直接透传源站 gloss，fix 段修订 senses 后分类页仍显示旧释义
        # （如 temporary 残留英文括注、permanently 误译「总是」），共 70 词不一致。
        c['gloss'] = w['senses'][0]
    w['pos'] = c['pos'] if c else None
    w['sub'] = c['sub'] if c else None
    w['catGloss'] = c['gloss'] if c else None
    # 第七十轮：感情色彩 / 语体色彩。台账（sentiment 段）优先于 recat/add 带来的
    # 旧标签——旧标签来自外部源站，对过半形容词偏宽松，这两维以台账为准。
    _sd = SENTIMENT.get(w['word'])
    if _sd:
        if 'sub' in _sd:
            w['sub'] = _sd['sub']
        if 'reg' in _sd:
            w['reg'] = _sd['reg']
    # 兜底：形容词/名词/动词一律带感情色彩（无显式裁定者取「中性的」——
    # 中性是正当结论，不是"没判"）；语体色彩全库都有，无显式裁定者取「中性」。
    # 副词/连词/介词不带评价义，感情色彩留空（＝筛选面板里的「其他」档）。
    if w['pos'] in SUB_POS and not w.get('sub'):
        w['sub'] = '中性的'
    if not w.get('reg'):
        w['reg'] = '中性'
    if c:
        c['sub'] = w['sub']
        c['reg'] = w['reg']
    if not w['notes']:
        w.pop('notes', None)
    # 核心层判定（改名过的词用原始拼写查表）；册卅三轮起追加 noncore 显式排除——
    # 判据为「学术文本高频」而非「按来源自动入核」，自动通道保留、减除在其后。
    _lw = w['word'].strip().lower()
    _lsw = (w.get('src_word') or '').strip().lower()
    w['core'] = bool(
        w['num'] in _cat_nums
        or w['word'] in added
        or w.get('src_word') in added
        or w['word'] in CORE_EXTRA
        or w.get('src_word') in CORE_EXTRA
    ) and not (_lw in NONCORE_EXCLUDE or _lsw in NONCORE_EXCLUDE)
    if not w['core']:
        w.pop('core', None)
    w.pop('src_word', None)

kept.sort(key=lambda w: w['num'])
cats = [cat_by_num[n] for n in sorted(cat_by_num)]
for c in cats:
    c['gloss'] = norm_senses([c.get('gloss', '')])[0] if c.get('gloss') else ''

# ---------------------------------------------------------------- 7. sanity
names = [w['word'] for w in kept]
dupes = {n for n in names if names.count(n) > 1}
if dupes:
    sys.exit('duplicate words after curation: %s' % sorted(dupes))
if len({w['num'] for w in kept}) != len(kept):
    sys.exit('duplicate num ids')
if any(not w['senses'] or not w['senses'][0].strip() for w in kept):
    sys.exit('some words ended up without a meaning')
if any(not w['links'] or len(w['links']) != 3 for w in kept):
    sys.exit('some words have broken dictionary links')
cats_words = {c['word'] for c in cats}
missing = cats_words - set(names)
if missing:
    sys.exit('classified words missing from main list: %s' % sorted(missing))

def dump_atomic(path, obj):
    """v36-④(册四十九): tmp+os.replace,写一半崩溃不再留半截产物"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)   # 无行尾换行,与原直写面字节一致
    os.replace(tmp, path)

dump_atomic(D('data', 'words.json'), kept)
dump_atomic(D('data', 'cats.json'), cats)

by_pos = {}
for c in cats:
    by_pos[c['pos']] = by_pos.get(c['pos'], 0) + 1
print('curated words : %d  (removed %d, added %d)' % (len(kept), len(dropped_words), len(added)))
print('classified    : %d  %s' % (len(cats), by_pos))
print('renamed       : %d' % len(fixed_names))
