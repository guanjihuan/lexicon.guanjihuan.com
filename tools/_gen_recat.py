#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off generator: writes the "recat" array into data/curation.json.

recat = 词性 / 感情色彩标注修正。本表覆盖**全部**词条（含原 800 词表中此前未分类的部分），
让「按词性筛选」与「按感情色彩分组」在全库范围内可用。

覆盖的规则：
  * 纯介词（due to / via / onto / regarding / owing to）不设词性 —— 词性索引面向实词。
  * 形容词一律标注感情色彩：学术语域下中性词最多，只有明确褒贬的才标积极/消极。

Run:  python3 tools/_gen_recat.py
"""
import json, os, collections, sys

# 严格 JSON 读取：重复键必须报错（标准库会静默覆盖，人写的 JSON 易踩）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json, require_curation_segments  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (word, pos, sub)   sub 仅形容词有效
T = [
# ---------------------------------------------------------------- 形容词
("formidable","形容词","中性的"),
("equivocal","形容词","中性的"),
("ambiguous","形容词","中性的"),
("intricate","形容词","中性的"),
("controversial","形容词","中性的"),
("compact","形容词","中性的"),
("eligible","形容词","中性的"),
("intelligible","形容词","中性的"),
("concise","形容词","中性的"),
("adequate","形容词","中性的"),
("imperative","形容词","中性的"),
("indispensable","形容词","中性的"),
("feasible","形容词","中性的"),
("representative","形容词","中性的"),
("pivotal","形容词","中性的"),
("critical","形容词","中性的"),
("vital","形容词","中性的"),
("unprecedented","形容词","中性的"),
("prior","形容词","中性的"),
("paramount","形容词","中性的"),
("drastic","形容词","中性的"),
("subsequent","形容词","中性的"),
("preceding","形容词","中性的"),
("modest","形容词","中性的"),
("elusive","形容词","中性的"),
("thorough","形容词","中性的"),
("amenable","形容词","中性的"),
("competitive","形容词","中性的"),
("seamless","形容词","积极的"),
("longitudinal","形容词","中性的"),
("state-of-the-art","形容词","中性的"),
("cumulative","形容词","中性的"),
("revised","形容词","中性的"),
("extraneous","形容词","中性的"),
("ingenious","形容词","积极的"),
("spurious","形容词","消极的"),
("reciprocal","形容词","中性的"),
("akin","形容词","中性的"),
("top-down","形容词","中性的"),
("bottom-up","形容词","中性的"),
("prohibitive","形容词","消极的"),
("complimentary","形容词","中性的"),
("recursive","形容词","中性的"),
("iterative","形容词","中性的"),
("twofold","形容词","中性的"),
("preferable","形容词","中性的"),
("hierarchical","形容词","中性的"),
("fine-grained","形容词","中性的"),
("legitimate","形容词","中性的"),
("pedagogical","形容词","中性的"),
("well-defined","形容词","中性的"),
("blurred","形容词","中性的"),
("onerous","形容词","消极的"),
("inclined","形容词","中性的"),
("cutting-edge","形容词","中性的"),
("provisional","形容词","中性的"),
("temporal","形容词","中性的"),
("heuristic","形容词","中性的"),
("prestigious","形容词","积极的"),
("aforementioned","形容词","中性的"),
("self-contained","形容词","中性的"),
("preliminary","形容词","中性的"),
("multifaceted","形容词","中性的"),
("nascent","形容词","中性的"),
("radical","形容词","中性的"),
("in-depth","形容词","中性的"),
("superior","形容词","积极的"),
("versatile","形容词","中性的"),
("daunting","形容词","消极的"),
("long-standing","形容词","中性的"),
("mounting","形容词","中性的"),
("concerned","形容词","中性的"),
("probabilistic","形容词","中性的"),
("singular","形容词","中性的"),
("ample","形容词","中性的"),
("uniform","形容词","中性的"),
("unintentional","形容词","中性的"),
("far-reaching","形容词","中性的"),
("vertical","形容词","中性的"),
("sparse","形容词","中性的"),
("incremental","形容词","中性的"),
("ad hoc","形容词","中性的"),
("historical","形容词","中性的"),
("computational","形容词","中性的"),
("statistical","形容词","中性的"),
("myriad","形容词","中性的"),
("prone","形容词","中性的"),
("content","名词",None),   # 第七轮改判：学术语域以名词义（内容）为主
("invisible","形容词","中性的"),
("fertile","形容词","中性的"),
("coercive","形容词","消极的"),
("exponential","形容词","中性的"),
("expedient","形容词","中性的"),
("nominal","形容词","中性的"),
("viable","形容词","中性的"),
# ---------------------------------------------------------------- 动词
("yield","动词",None),
("stem from","动词",None),
("prevail","动词",None),
("ascribe","动词",None),
("dictate","动词",None),
("pinpoint","动词",None),
("hinder","动词",None),
("claim","动词",None),
("prohibit","动词",None),
("compensate","动词",None),
("trigger","动词",None),
("compose","动词",None),
("resemble","动词",None),
("adhere to","动词",None),
("perceive","动词",None),
("inherit","动词",None),
("scrutinize","动词",None),
("extract","动词",None),
("attribute to","动词",None),
("decline","动词",None),
("bypass","动词",None),
("render","动词",None),
("proofread","动词",None),
("leverage","动词",None),
("provoke","动词",None),
("witness","动词",None),
("accommodate","动词",None),
("immerse","动词",None),
("invoke","动词",None),
("encapsulate","动词",None),
("collapse","动词",None),
("owe","动词",None),
("endowed with","动词",None),  # 册六十五轮词性校勘：be endowed with 为被动动词结构，与同族多词动词短语（adhere to / take into account）一致
("exemplify","动词",None),
("discard","动词",None),
("overlook","动词",None),
("quantify","动词",None),
("popularize","动词",None),
("obstruct","动词",None),
("encompass","动词",None),
("articulate","动词",None),
("diversify","动词",None),
("entail","动词",None),
("consist in","动词",None),
("intervene","动词",None),
("suffice","动词",None),
("evade","动词",None),
("cement","动词",None),
("delineate","动词",None),
("specialize","动词",None),
("designate","动词",None),
("conceal","动词",None),
("govern","动词",None),
("refer to","动词",None),
("merge","动词",None),
("surge","动词",None),
("coordinate","动词",None),
("confront","动词",None),
("revisit","动词",None),
("debunk","动词",None),
("prove","动词",None),
("leap","动词",None),
("mitigate","动词",None),
("emulate","动词",None),
("embed","动词",None),
("unify","动词",None),
("pave","动词",None),
("migrate","动词",None),
("diagnose","动词",None),
("respect","动词",None),
("cease","动词",None),
("obviate","动词",None),
("disseminate","动词",None),
("lay the foundation for","动词",None),
("cast light on","动词",None),
("spur","动词",None),
("account for","动词",None),
("pertain","动词",None),
("synchronize","动词",None),
("raise","动词",None),
("categorize","动词",None),
("drive","动词",None),
("favour","动词",None),
("acquire","动词",None),
("validate","动词",None),
("stagger","动词",None),
("anchor","动词",None),
("disrupt","动词",None),
("conflate","动词",None),
# ---------------------------------------------------------------- 名词
("contrast","名词",None),
("trial","名词",None),
("routine","名词",None),
("prerequisite","名词",None),
("paradox","名词",None),
("proof","名词",None),
("protocol","名词",None),
("consent","名词",None),
("innovation","名词",None),
("harvest","名词",None),
("incorporation","名词",None),
("fingerprint","名词",None),
("repetition","名词",None),
("obstacle","名词",None),
("ratio","名词",None),
("outline","名词",None),
("clarity","名词",None),
("capacity","名词",None),
("discipline","名词",None),
("column","名词",None),
("plethora","名词",None),
("criterion","名词",None),
("fraction","名词",None),
("cascade","名词",None),
("recipe","名词",None),
("snapshot","名词",None),
("spark","名词",None),
("interface","名词",None),
("catalogue","名词",None),
("evolution","名词",None),
("assertion","名词",None),
("remainder","名词",None),
("trajectory","名词",None),
("trait","名词",None),
("confirmation","名词",None),
("asset","名词",None),
("formula","名词",None),
("metaphor","名词",None),
("merit","名词",None),
("expertise","名词",None),
("scope","名词",None),
("fashion","名词",None),
("atmosphere","名词",None),
("scrutiny","名词",None),
("logic","名词",None),
("regime","名词",None),
("dissertation","名词",None),
("availability","名词",None),
("penalty","名词",None),
("recipient","名词",None),
("reservoir","名词",None),
("entity","名词",None),
("dichotomy","名词",None),
("assignment","名词",None),
("susceptibility","名词",None),
("retraction","名词",None),
("scepticism","名词",None),
("visibility","名词",None),
("building block","名词",None),
("synonym","名词",None),
("metric","名词",None),
("segment","名词",None),
("scale","名词",None),
("arena","名词",None),
("territory","名词",None),
("impetus","名词",None),
("onset","名词",None),
("parenthesis","名词",None),
("implementation","名词",None),
("reconciliation","名词",None),
("revelation","名词",None),
# ---------------------------------------------------------------- 副词
("hitherto","副词",None),
("accordingly","副词",None),
("exclusively","副词",None),
("a priori","形容词","中性的"),
("initially","副词",None),
("likewise","副词",None),
("alternatively","副词",None),
("merely","副词",None),
("barely","副词",None),
("in situ","副词",None),
("therein","副词",None),
("interchangeably","副词",None),
("namely","副词",None),
("purely","副词",None),


("by no means","副词",None),
("not to mention","副词",None),
("from scratch","副词",None),
("under no circumstances","副词",None),
("a posteriori","形容词","中性的"),
("either","副词",None),
# ---------------------------------------------------------------- 连词
("insofar as","连词",None),
]

# 纯介词：词性索引面向实词，介词短语不纳入分类
SKIP = {"due to", "in accordance with", "in conjunction with", "onto", "owing to", "regarding", "via"}

# 此前已分类、这里保持不变（避免生成器覆盖既有正确标注）
KEEP = {
 "counterintuitive": {"sub": "中性的"},
 "unequivocal": {"sub": "中性的"},
 "elementary": {"sub": "中性的"},
 "unusual": {"sub": "中性的"},
 "unique": {"sub": "中性的"},
 "distinct": {"sub": "中性的"},
 "distinctive": {"sub": "中性的"},
 "disparate": {"sub": "中性的"},
 "paradigmatic": {"sub": "中性的"},
 "pronounced": {"sub": "中性的"},
 "dominant": {"sub": "中性的"},
 "predominant": {"sub": "中性的"},
 "prominent": {"sub": "中性的"},
 "notable": {"sub": "中性的"},
 "remarkable": {"sub": "中性的"},
 "striking": {"sub": "中性的"},
 "plausible": {"sub": "中性的"},
 "genuine": {"sub": "中性的"},
 "substantial": {"sub": "中性的"},
 "precise": {"sub": "中性的"},
 "salient": {"sub": "中性的"},
 "considerable": {"sub": "中性的"},
 "definite": {"sub": "中性的"},
 "extraordinary": {"sub": "中性的"},
 "dramatic": {"sub": "中性的"},
 "peculiar": {"sub": "中性的"},
 "compelling": {"sub": "积极的"},
 "noteworthy": {"sub": "中性的"},
 "diverse": {"sub": "中性的", "pos": "形容词"},
 "instrumental": {"sub": "中性的"},
 "distinguish": {"pos": "动词"},
 "reveal": {"pos": "动词"},
 "feature": {"pos": "名词"},
 "subject": {"pos": "名词"},
 "consistent": {"pos": "形容词", "sub": "中性的"},
 "crucial": {"pos": "形容词", "sub": "中性的"},
 "flexible": {"pos": "形容词", "sub": "中性的"},
 "additionally": {"pos": "副词"},
 "consequently": {"pos": "副词"},
 "essentially": {"pos": "副词"},
 "indeed": {"pos": "副词"},
 "notably": {"pos": "副词"},
 "roughly": {"pos": "副词"},
 "ultimately": {"pos": "副词"},
 "virtually": {"pos": "副词"},
 "overall": {"pos": "形容词", "sub": "中性的"},   # 源站词：pos 由副词改形容词（定语用法为主），色彩按第五轮口径归中性
 "irrespective": {"pos": "形容词", "sub": "中性的"},   # 册六十六轮词性校勘：源站副词→形容词（LDOCE/MW 主词性 adjective；-ive 形容词后缀；例句为形容词短语+of 补语作状语）
}

# 与 fix 一致的拼写统一（美式）：recat 的键是改名之后的词形
RENAME = {"analogue": "analog", "catalogue": "catalog", "favour": "favor",
          "fulfil": "fulfill", "scepticism": "skepticism"}

recat = dict(KEEP)
seen = set()
for word, pos, sub in T:
    word = RENAME.get(word, word)
    if word in recat:
        raise SystemExit("duplicate in recat: %r" % word)
    seen.add(word)
    e = {"pos": pos}
    if sub:
        e["sub"] = sub
    recat[word] = e

# 校验：每个待分类词都被覆盖
cur_path = os.path.join(ROOT, 'data', 'curation.json')
cur = load_json(cur_path)
# 段完整性闸（第八轮）：本脚本要读 remove/fix/add 三段（recat 段由它整体重写）。
# 段名打错（如把 recat 写成 reccat）时旧版**静默忽略**、改错的那段永远不被
# 读取且原样留在文件里——现在会出警告并给出近似拼写建议。
require_curation_segments(cur, ('remove', 'fix', 'add'))
raw = load_json(os.path.join(ROOT, 'data', 'words800.json'))
cats = load_json(os.path.join(ROOT, 'data', 'categorized.json'))
existing = {w['word'] for w in raw} | {c['word'] for c in cats}
removed = set(cur['remove'])
fixed_new = {v.get('word', k) for k, v in cur['fix'].items()}
known = (existing - removed) | fixed_new
known |= {v.get('word', k) for k, v in cur['fix'].items()}
# 增补词的词性真源在 tools/_gen_additions.py 的 T 表（add 段），不在 recat 段：
# 本脚本**整体重写** recat 段，手写进去的增补词条目下次重跑就被抹掉；而且
# curate.py 解析 recat 键时增补词还没进词表（增补在第 5 步才追加），
# 于是「生成器放行 → 应用器报 recat key not found」的死路。
# 故此处显式拦下并指向真正的真源。
add_words = {a['word'] for a in cur['add']}

for k in recat:
    if k in add_words:
        raise SystemExit("recat key %r 是增补词：增补词的词性/色彩真源是 "
                         "tools/_gen_additions.py 的 T 表（add 段），不是 recat 段"
                         "（recat 段会被本脚本整体重写）；请改 T 表" % k)
    if k not in known:
        raise SystemExit("recat key not found in word list: %r" % k)

cur['recat'] = recat
with open(cur_path + '.tmp', 'w', encoding='utf-8') as f:   # v36-④(册四十九): tmp+os.replace 原子写
    json.dump(cur, f, ensure_ascii=False, indent=1)   # 与仓库既有格式一致（四十六轮:原 indent=2 令每次重跑整文件重排缩进）
    f.write('\n')
os.replace(cur_path + '.tmp', cur_path)
print("recat entries: %d" % len(recat))
print("  newly assigned here: %d" % len(T))
by = collections.Counter(v.get('pos') for v in recat.values())
for k, v in sorted(by.items(), key=lambda x: -x[1]):
    print("  %s: %d" % (k, v))
print("  adjectives with sentiment: %d"
      % sum(1 for v in recat.values() if v.get('pos') == '形容词' and v.get('sub')))
print("  skipped (prepositions): %s" % ', '.join(sorted(SKIP)))
