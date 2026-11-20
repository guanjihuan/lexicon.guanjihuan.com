#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""感情色彩 / 语体色彩专项守卫。

运行：python3 tools/sentiment_test.py

覆盖两类问题：
  1. 当前产物的取值、覆盖与台账理由是否一致；
  2. _gen_sentiment.py 遇到缺语体理由、静默撤标签、非法值与失踪词形时，
     是否失败且保持 curation.json 字节不变。
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
SUB_VALS = {'积极的', '消极的', '争议性的', '中性的'}
REG_VALS = {'学术术语', '书面语', '口语', '中性'}
SUB_POS = {'形容词', '名词', '动词'}
FAIL = []
PASSED = 0


def ok(name, cond, extra=''):
    global PASSED
    print(('  ✓ ' if cond else '  ✗ ') + name + (('  [%s]' % extra) if extra else ''))
    if cond:
        PASSED += 1
    else:
        FAIL.append(name + ((' ' + extra) if extra else ''))


def load(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def make_case(base, name):
    root = os.path.join(base, name)
    os.makedirs(os.path.join(root, 'tools'))
    os.makedirs(os.path.join(root, 'data'))
    for fn in ('_gen_sentiment.py', '_strict_json.py', '_console_utf8.py'):
        shutil.copy2(D('tools', fn), os.path.join(root, 'tools', fn))
    for fn in ('curation.json', 'words.json', 'sentiment_decisions.json'):
        shutil.copy2(D('data', fn), os.path.join(root, 'data', fn))
    return root


def run_generator(root):
    return subprocess.run([sys.executable, os.path.join('tools', '_gen_sentiment.py')],
                          cwd=root, text=True, encoding='utf-8', errors='replace',
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)


def save_json(path, obj):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')


def main():
    words = load(D('data', 'words.json'))
    ledger = load(D('data', 'sentiment_decisions.json'))['decisions']
    by_word = {w['word']: w for w in words}

    print('== 当前产物与台账 ==')
    ok('全库每词都有合法语体色彩',
       all(w.get('reg') in REG_VALS for w in words))
    ok('感情色彩只挂在形容词/名词/动词，且取值合法',
       all((w.get('sub') in SUB_VALS) if w.get('pos') in SUB_POS else not w.get('sub')
           for w in words))
    ok('语体四档都非空且合计为全库',
       all(any(w.get('reg') == v for w in words) for v in REG_VALS))
    ok('台账词形全部存在',
       not (set(ledger) - set(by_word)),
       ', '.join(sorted(set(ledger) - set(by_word))[:5]))
    ok('带 reg 的台账都有独立 reg_reason',
       all(str(e.get('reg_reason', '')).strip()
           for e in ledger.values() if 'reg' in e))
    ok('带 sub 的台账都有独立感情理由',
       all(str(e.get('reason', '')).strip()
           for e in ledger.values() if 'sub' in e))
    ok('台账与产物的语体裁定一致',
       all(by_word[w].get('reg') == e['reg']
           for w, e in ledger.items() if 'reg' in e))
    ok('台账与产物的感情裁定一致',
       all(by_word[w].get('sub') == e['sub']
           for w, e in ledger.items() if 'sub' in e))

    print('== 生成器失败闸（均在临时目录）==')
    with tempfile.TemporaryDirectory(prefix='wl_sentiment_test_') as tmp:
        # 正常路径：应成功，且段内容与台账的 sub/reg 一致。
        case = make_case(tmp, 'ok')
        p = run_generator(case)
        ok('生成器正常路径成功', p.returncode == 0, p.stdout[-180:])
        if p.returncode == 0:
            cur = load(os.path.join(case, 'data', 'curation.json'))
            expected = {w: {k: v for k, v in e.items() if k in ('sub', 'reg')}
                        for w, e in ledger.items()}
            ok('生成段与台账的 sub/reg 一致', cur['sentiment'] == expected)

        # 缺 reg_reason：必须失败，且不得改动 curation.json。
        case = make_case(tmp, 'missing_reason')
        led_path = os.path.join(case, 'data', 'sentiment_decisions.json')
        led = load(led_path)
        victim = next(w for w, e in led['decisions'].items() if 'reg' in e)
        led['decisions'][victim].pop('reg_reason', None)
        save_json(led_path, led)
        cur_path = os.path.join(case, 'data', 'curation.json')
        before = md5(cur_path)
        p = run_generator(case)
        ok('缺 reg_reason 时生成器失败', p.returncode != 0)
        ok('失败信息点名缺语体理由', 'reg_reason' in p.stdout, p.stdout[-180:])
        ok('缺理由失败后 curation.json 字节不变', md5(cur_path) == before)

        # 省略 reg 撤掉现有少数档标签：必须显式写中性，否则失败。
        case = make_case(tmp, 'silent_demotion')
        led_path = os.path.join(case, 'data', 'sentiment_decisions.json')
        led = load(led_path)
        cur_words = load(os.path.join(case, 'data', 'words.json'))
        victim = next(w['word'] for w in cur_words
                      if w.get('reg') not in (None, '中性') and w['word'] in led['decisions'])
        led['decisions'][victim].pop('reg', None)
        save_json(led_path, led)
        cur_path = os.path.join(case, 'data', 'curation.json')
        before = md5(cur_path)
        p = run_generator(case)
        ok('静默撤语体标签时生成器失败', p.returncode != 0)
        ok('失败信息要求显式写中性', 'reg=中性' in p.stdout, p.stdout[-220:])
        ok('静默撤标签失败后 curation.json 字节不变', md5(cur_path) == before)

        # 非法 reg：必须失败。
        case = make_case(tmp, 'bad_value')
        led_path = os.path.join(case, 'data', 'sentiment_decisions.json')
        led = load(led_path)
        victim = next(iter(led['decisions']))
        led['decisions'][victim]['reg'] = '看起来像术语'
        led['decisions'][victim]['reg_reason'] = '非法值探针'
        save_json(led_path, led)
        p = run_generator(case)
        ok('非法语体取值被拦截', p.returncode != 0 and 'reg 不合法' in p.stdout,
           p.stdout[-180:])

        # 失踪词形：必须失败。
        case = make_case(tmp, 'orphan')
        led_path = os.path.join(case, 'data', 'sentiment_decisions.json')
        led = load(led_path)
        led['decisions']['zz_not_in_word_list'] = {
            'reg': '中性', 'reason': '探针', 'reg_reason': '探针'}
        save_json(led_path, led)
        p = run_generator(case)
        ok('台账引用失踪词形时被拦截', p.returncode != 0 and '失踪词形' in p.stdout,
           p.stdout[-180:])

    print()
    if FAIL:
        print('RESULT: %d FAILURES' % len(FAIL))
        for f in FAIL:
            print('  - ' + f)
        return 1
    print('RESULT: ALL TESTS PASSED (%d checks passed)' % PASSED)
    return 0


if __name__ == '__main__':
    sys.exit(main())
