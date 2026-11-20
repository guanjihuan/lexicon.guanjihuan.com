#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge per-batch example sentences into one curated example file.

Inputs :
  data/examples_parts/part_*.json   raw batches (written by parallel authoring agents)
  data/words.json                   curated word list (headwords that need examples)

Output :
  data/examples.json                {word: [{en, zh}, ...]}  (3 sentences per word)

The example file is keyed by headword string, NOT by `num`, so it survives
re-numbering / renaming / adding words in data/curation.json.

Run:  python3 tools/merge_examples.py
"""
import glob, json, os, re, sys

# 控制台输出钉 UTF-8（Windows GBK 控制台上中文报错会变 mojibake，见 _console_utf8.py）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

# 严格 JSON 读取：重复键必须报错（标准库会静默覆盖，人写的 JSON 易踩）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

WORDS = load_json(D('data', 'words.json'))
HEADS = [w['word'] for w in WORDS]

# ---------------------------------------------------------------- helpers
# 常见不规则动词/名词的变形（stem -> 其余形式）
IRREGULAR = {
    'arise': ['arose', 'arisen', 'arising'], 'choose': ['chose', 'chosen'],
    'grow': ['grew', 'grown'], 'bear': ['bore', 'borne'], 'bring': ['brought'],
    'build': ['built'], 'become': ['became'], 'begin': ['began', 'begun'],
    'hold': ['held'], 'lead': ['led'], 'make': ['made'], 'take': ['took', 'taken'],
    'give': ['gave', 'given'], 'write': ['wrote', 'written'], 'find': ['found'],
    'show': ['showed', 'shown'], 'prove': ['proved', 'proven'], 'fall': ['fell', 'fallen'],
    'feel': ['felt'], 'keep': ['kept'], 'leave': ['left'], 'lose': ['lost'],
    'meet': ['met'], 'pay': ['paid'], 'say': ['said'], 'seek': ['sought'],
    'sell': ['sold'], 'send': ['sent'], 'spend': ['spent'], 'stand': ['stood'],
    'teach': ['taught'], 'think': ['thought'], 'understand': ['understood'],
    'go': ['went', 'gone'], 'know': ['knew', 'known'], 'run': ['ran'], 'see': ['saw', 'seen'],
    'speak': ['spoke', 'spoken'], 'break': ['broke', 'broken'], 'draw': ['drew', 'drawn'],
    'fly': ['flew', 'flown'], 'rise': ['rose', 'risen'],
    'shine': ['shone'], 'sink': ['sank', 'sunk'], 'spread': ['spread'],
    'strike': ['struck'], 'swear': ['swore', 'sworn'], 'tear': ['tore', 'torn'],
    'throw': ['threw', 'thrown'], 'wear': ['wore', 'worn'], 'win': ['won'],
    'withdraw': ['withdrew', 'withdrawn'], 'lay': ['laid'],
    'read': ['read'], 'deal': ['dealt'], 'mean': ['meant'], 'sit': ['sat'],
    'come': ['came'], 'catch': ['caught'], 'eat': ['ate', 'eaten'],
    'forget': ['forgot', 'forgotten'], 'get': ['got', 'gotten'],
    'drive': ['drove', 'driven'], 'tell': ['told'],
    # 册四十八轮 v36-②:give/lead 重复键(gold 同值覆盖)去重;补 come/catch/eat/forget/get/drive/tell 七族
}
# 常见前缀（不改变词根）：implausible / unstated / incompatible ...
PREFIXES = ['im', 'un', 'in', 'dis', 'non', 'mis', 'over', 'under', 'pre', 're',
            'sub', 'inter', 'anti', 'de', 'co', 'multi', 'semi', 'auto', 'micro']
SUFFIXES = ['s', 'es', 'ed', 'ing', 'd', 'ly', 'er', 'est', 'ion', 'ions', 'al',
            'ment', 'ance', 'ence', 'ity', 'ities', 'ous', 'ive', 'able', 'ible',
            'ful', 'less', 'ist', 'ism', 'ize', 'ise', 'ized', 'ised', 'y', 'ies',
            'ied', 'ation', 'ations', 'ness', 'ic', 'ical', 'ary', 'ory']

def stem(w):
    """Crude English stemmer: strip common suffixes and doubled consonants."""
    s = w.lower()
    if len(s) <= 3:
        return s
    for suf in ('ations', 'ation', 'ies', 'ied', 'ing', 'ies', 'ily', 'ally'):
        if s.endswith(suf) and len(s) - len(suf) >= 3:
            s = s[:-len(suf)]
            if suf == 'ies':
                s += 'y'
            elif suf == 'ied':
                s += 'y'
            break
    else:
        for suf in SUFFIXES:
            if s.endswith(suf) and len(s) - len(suf) >= 3:
                s = s[:-len(suf)]
                break
    # doubled consonant: stemmed -> stem, planned -> plan
    if len(s) >= 3 and s[-1] == s[-2] and s[-1] not in 'aeiousl':
        s = s[:-1]
    return s

def head_stems(word):
    """All stems that may stand for `word` inside a sentence."""
    heads = [w for w in re.split(r'[^a-z]+', word.lower()) if w]
    out = set()
    for h in heads:
        out.add(stem(h))
        for p in PREFIXES:
            if h.startswith(p) and len(h) - len(p) >= 3:
                out.add(stem(h[len(p):]))
        for form in IRREGULAR.get(h, []):
            out.add(stem(form))
    return out

def tokens(sentence):
    return [t for t in re.split(r'[^a-z]+', sentence.lower()) if t]

def contains_word(sentence, word):
    """True if the sentence actually uses the target word (any inflection)."""
    heads = [w for w in re.split(r'[^a-z]+', word.lower()) if w]
    if not heads:
        return False
    toks = tokens(sentence)
    if not toks:
        return False
    tok_stems = [stem(t) for t in toks]
    target = head_stems(word)
    n = len(heads)
    for i in range(len(toks) - n + 1):
        window = tok_stems[i:i + n]
        if all(any(w == ts or ts in w or w in ts for ts in target) for w in window):
            return True
    # 短语动词中间可插入宾语："attribute its success to ..." -> "attribute ... to"
    if n == 2:
        s0, s1 = head_stems(heads[0]), head_stems(heads[1])
        def match(tok, stems):
            ts = stem(tok)
            return any(ts == s or ts in s or s in ts for s in stems)
        for i in range(len(toks)):
            if not match(toks[i], s0):
                continue
            for j in range(i + 1, len(toks)):
                if match(toks[j], s1):
                    return True
    return False

DROPS = []                      # 册四十八轮 v36-③:原两处静默 return None 的丢句面,出声+计数
DROP_BASELINE = 0               # v36 落账时实测 N₀=0;新增丢句一律 fail,历史合法空态若出现须先入台账再抬阈值

def clean(obj, where=''):
    """Normalise one example pair. Silent drops were a blind spot (v36-③)."""
    if isinstance(obj, dict):
        en = obj.get('en') or obj.get('english') or ''
        zh = obj.get('zh') or obj.get('cn') or obj.get('chinese') or ''
    elif isinstance(obj, (list, tuple)) and len(obj) >= 2:
        en, zh = obj[0], obj[1]
    else:
        DROPS.append('%s: 类型不识别 %r' % (where, obj))
        return None
    en = re.sub(r'\s+', ' ', str(en)).strip().strip('"').strip()
    zh = re.sub(r'\s+', ' ', str(zh)).strip().strip('"').strip()
    if not en or not zh:
        DROPS.append('%s: en/zh 有一为空' % where)
        return None
    return {'en': en, 'zh': zh}

# ---------------------------------------------------------------- 1. read parts
merged = {}
dup = []
for path in sorted(glob.glob(D('data', 'examples_parts', 'part_*.json'))):
    # 解析失败/重复键由 _strict_json.load_json 直接以友好报错退出（sys.exit →
    # SystemExit，不属于 Exception，早先那个 `except Exception` 其实是死代码，
    # 「cannot parse …」这条消息永远打不出来）
    data = load_json(path)
    if not isinstance(data, dict):
        sys.exit('%s: top level must be an object' % path)
    for word, exs in data.items():
        if word in merged:
            dup.append(word)
        merged[word] = exs

# ---------------------------------------------------------------- 2. validate
errors, warnings = [], []
head_set = set(HEADS)
out = {}

for word in HEADS:
    exs = merged.get(word)
    if exs is None:
        errors.append('missing examples: %s' % word)
        continue
    if not isinstance(exs, list):
        errors.append('not a list: %s' % word)
        continue
    pairs = [clean(e, '%s[%d]' % (word, i)) for i, e in enumerate(exs)]
    # [en, zh, ...] 第三段以后被静默丢弃曾是盲区：多半是多打了一句或字段错位，出声
    for e in exs:
        if isinstance(e, (list, tuple)) and len(e) > 2:
            warnings.append('extra fragments dropped: %s | %r' % (word, list(e)[2:]))
    pairs = [p for p in pairs if p]
    if len(pairs) != 3:
        errors.append('%d examples (want 3): %s' % (len(pairs), word))
    # 同一条英文例句重复出现（曾可静默通过：3 句内容一模一样也照收，
    # 界面上同一个词的三条例句显示成一模一样）——判错并拦在写盘之前
    if pairs and len({p['en'] for p in pairs}) != len(pairs):
        errors.append('duplicate sentence: %s' % word)
    if not pairs:
        continue
    for p in pairs:
        if len(p['en'].split()) < 4:
            warnings.append('sentence too short: %s | %s' % (word, p['en']))
        if len(p['en'].split()) > 26:
            warnings.append('sentence too long: %s | %s' % (word, p['en']))
        if not contains_word(p['en'], word):
            errors.append('sentence does not contain %r: %s' % (word, p['en']))
    out[word] = pairs

extra = [w for w in merged if w not in head_set]
if dup:
    warnings.append('duplicated across parts (kept last): %s' % sorted(dup))
if extra:
    warnings.append('dropped %d unknown words: %s' % (len(extra), sorted(extra)[:20]))

# ---------------------------------------------------------------- 3. write
if errors:
    print('FAILED: %d problems' % len(errors))
    for e in errors[:300]:
        print('  -', e)
    if len(errors) > 300:
        print('  ... and %d more' % (len(errors) - 300))
    sys.exit(1)

# 丢句闸必须**先于写盘**：原先它在 json.dump 之后，于是「超阈即止」名不副实——
# 工具一边报 FAILED 退出码 1，一边已经把少句的产物写进仓库（下一棒 make_examples
# 照单烤进 js/examples.js）。现在先判闸，闸不过则产物保持原样。
if len(DROPS) > DROP_BASELINE:
    print('FAILED: clean() 丢句 %d 条(基线 %d),超阈即止（产物未写）:' % (len(DROPS), DROP_BASELINE))
    for d in DROPS:
        print('  -', d)
    sys.exit(1)


def dump_atomic(path, obj):
    """原子写(v36-④ 册四十九同规): tmp+os.replace,写一半崩溃不再留半截产物"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


dump_atomic(D('data', 'examples.json'), out)

print('examples       : %d words x 3 sentences' % len(out))
print('clean() drops  : %d (baseline %d)' % (len(DROPS), DROP_BASELINE))
print('unknown words  : %d' % len(extra))
for w in warnings[:20]:
    print('  warn:', w)
if len(warnings) > 20:
    print('  ... and %d more warnings' % (len(warnings) - 20))
