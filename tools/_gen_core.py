#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off generator: writes the "core" and "noncore" arrays into data/curation.json.

核心高频分层重建(册卅三轮)。唯一事实来源 = **data/core_decisions.json 逐词台账**
(每词 verdict: core|noncore + 一行学术频率理由,由判据「AWL 词族 ∪ 高频学术骨架词
∪ 通用高频学术承载词 ∪ 连接语块全入核」逐词复核定稿)。本脚本把台账翻译成 curation
段,**整体覆盖** core 与 noncore 两段(与 _gen_additions/_gen_recat 同规:直接手改
这两段会被下次重跑抹掉,要调分层请改台账再重跑本脚本)。

翻译规则(避免与 curate.py 的自动通道形成双重语义,只补差集):
  * auto 资格 = num∈源站精选(categorized.json) ∪ 词形∈add 段(含 fix 改名映射)
  * verdict=core 且无 auto 资格 → 写入 core 段(提入)
  * verdict=noncore 且有 auto 资格 → 写入 noncore 段(降出,curate 在自动判定后减除)
  * 其余(判断与自动通道一致) → 不写,curate 自动通道自然满足

守卫:台账必须**全覆盖且仅覆盖**当前词表词形(缺词/多词/孤儿一律 fail),
防 54e830 类后落新词被静默留在旧分层口径。

Run:  python3 tools/_gen_core.py
"""
import hashlib, json, os, sys

# 严格 JSON 读取：重复键必须报错（标准库会静默覆盖，人写的 JSON 易踩）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strict_json import load_json, require_curation_segments  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

cur = load_json(D('data', 'curation.json'))
# 段完整性闸（第八轮）：本脚本要读 add/fix 两段。fix 段缺失时 auto_eligible()
# 认不出「被 fix 改过名的新词形」，提入/降出差集会悄悄算错——缺段即报错。
require_curation_segments(cur, ('add', 'fix'))
words = load_json(D('data', 'words.json'))
raw_cats = load_json(D('data', 'categorized.json'))
led = load_json(D('data', 'core_decisions.json'))
decisions = led['decisions']

cat_nums = {c['num'] for c in raw_cats}
add_forms = {a['word'] for a in cur.get('add', [])}
fix = cur.get('fix', {})

def auto_eligible(w):
    if w['num'] in cat_nums or w['word'] in add_forms:
        return True
    # add 词被 fix 段改名后,words.json 只剩新形,curate 靠 src_word 匹配 add——
    # 这里等价还原:新形的原形(fix 键)若∈add,也算自动资格
    for k, v in fix.items():
        if v.get('word') == w['word'] and k in add_forms:
            return True
    return False

head = {w['word']: w for w in words}
missing = sorted(set(head) - set(decisions))
extra = sorted(set(decisions) - set(head))
if missing:
    raise SystemExit('core_decisions 缺词(须补台账后重跑): %s' % missing)
if extra:
    raise SystemExit('core_decisions 引用失踪词形(已删/改名?): %s' % extra)

need_core, need_noncore, bad_reason = [], [], []
for wt, d in decisions.items():
    v = d.get('verdict')
    if v not in ('core', 'noncore'):
        raise SystemExit('bad verdict for %r: %r' % (wt, v))
    if not str(d.get('reason', '')).strip():
        bad_reason.append(wt)
    elig = auto_eligible(head[wt])
    if v == 'core' and not elig:
        need_core.append(wt)
    if v == 'noncore' and elig:
        need_noncore.append(wt)
if bad_reason:
    raise SystemExit('台账缺理由(每词必须一行判据说明): %s' % bad_reason)

cur['core'] = sorted(need_core)
cur['noncore'] = sorted(need_noncore)
with open(D('data', 'curation.json') + '.tmp', 'w', encoding='utf-8') as f:   # v36-④(册四十九): tmp+os.replace 原子写
    json.dump(cur, f, ensure_ascii=False, indent=1)   # 与仓库既有格式一致(四十六轮口径)
    f.write('\n')
os.replace(D('data', 'curation.json') + '.tmp', D('data', 'curation.json'))

n_core = sum(1 for d in decisions.values() if d['verdict'] == 'core')
print('decisions: %d / total words: %d' % (len(decisions), len(words)))
print('expected final core tier: %d (%.1f%%)' % (n_core, 100.0 * n_core / len(words)))
print('core segment rows (显式提入): %d' % len(cur['core']))
print('noncore segment rows (显式降出): %d' % len(cur['noncore']))
# v36-⑤ 新对表制(v36 起批文 triple 的台账位直接抄本行机器输出,手写 hash 面退役——幻影案实证最高危伪造面)
print('ledger sha256[:16]=%s' % hashlib.sha256(open(D('data', 'core_decisions.json'), 'rb').read()).hexdigest()[:16])
