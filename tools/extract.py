#!/usr/bin/env python3
"""Extract word data from the two source pages into data/*.json.

Fetch (or reuse) the cached HTML of:
  - https://www.guanjihuan.com/archives/4418    (the 800-word list)
  - https://www.guanjihuan.com/archives/24732   (344-word categorized selection)

Writes: data/words800.json, data/categorized.json  (原始抽取结果，不做任何人工调整)

These two files are the *raw* upstream data and are never edited by hand.
All manual curation (删减 / 增补 / 释义与分类修正) lives in data/curation.json
and is applied by tools/curate.py, which produces data/words.json + data/cats.json.
Then run tools/make_data.py to regenerate the front-end data.

Usage:  python3 tools/extract.py [--offline /tmp/page4418.html /tmp/page24732.html]
        python3 tools/extract.py [--cache /tmp/page4418.html /tmp/page24732.html]
"""
import argparse, json, os, re, sys, html as H

# 控制台输出钉 UTF-8（Windows GBK 控制台上中文报错会变 mojibake，见 _console_utf8.py）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console_utf8 import force_utf8_console  # noqa: E402
force_utf8_console()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fetch(url, cache, offline=False):
    """取页面 HTML。offline=True（--offline）时**绝不联网**、也**绝不写**该路径。

    早先的 bug：--offline 只影响「失败时要不要隔离缓存」，路径不存在时仍会
    去 guanjihuan.com 抓一份写进用户给的那个路径（实测 739KB 落到
    /tmp/nonexistent_4418.html，抽取还「成功」了）——于是
      ① --offline 名不副实：路径拼错会变成一次静默的联网抓取；
      ② 用户自备路径被内容覆盖；
      ③ 抓到的是坏页时，这份坏内容留在用户路径上，下次重跑继续复用（正是
         pipeline_test ⑦ 对 --cache 拦的那条毒缓存死循环）。
    """
    if os.path.exists(cache):
        return open(cache, encoding='utf-8', errors='replace').read()
    if offline:
        sys.exit('FAILED: --offline 指定的文件不存在：%s\n'
                 '        --offline 的意思是「只用本地样本、不联网」，不会去抓网页；'
                 '请检查路径拼写，或改用 --cache（联网抓取并缓存到该路径）。' % cache)
    import subprocess
    # 先下到 .part 再原子改名：curl 被中断时不会把半截文件留在缓存位上
    part = cache + '.part'
    try:
        r = subprocess.run(['curl', '-k', '-s', '-L', '--max-time', '60', '-A', 'Mozilla/5.0',
                            url, '-o', part], timeout=90)
        if r.returncode != 0 or not os.path.exists(part) or os.path.getsize(part) == 0:
            sys.exit(f"fetch failed: {url} (try a proxy or place HTML at {cache})")
        os.replace(part, cache)
    finally:
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
    return open(cache, encoding='utf-8', errors='replace').read()

def strip_tags(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', '', s))).strip()

def parse_words(raw):
    raw = re.sub(r'<script.*?</script>', '', raw, flags=re.S)
    raw = re.sub(r'<style.*?</style>', '', raw, flags=re.S)
    sec = raw[raw.find('class="entry-content'):]
    if '<div class="addthis' in sec:
        sec = sec[:sec.find('<div class="addthis')]
    parts = re.split(r'<h2[^>]*>', sec)[1:]
    entries = []
    for p in parts:
        hm = re.match(r'(.*?)</h2>(.*)', p, re.S)
        if not hm:
            continue
        head = strip_tags(hm.group(1))
        hm2 = re.match(r'^(\d+)\.\s*(.+)$', head)
        if not hm2:
            continue  # "Published by…" / navigation headings
        num, word = int(hm2.group(1)), re.sub(r'\s+', ' ', H.unescape(hm2.group(2))).strip()
        body = re.sub(r'<p class="post-footer-note">.*?</p>', '', hm.group(2), flags=re.S)
        links = []
        for a in re.finditer(r'<a[^>]+href="(https?://[^"]+)"', body):
            u = H.unescape(a.group(1))
            if u not in links:
                links.append(u)
        senses, notes = [], []
        blocks = re.findall(r'(<h3[^>]*>.*?</h3>|<p[^>]*>.*?</p>|<u[li][^>]*>.*?</u[li]>)', body, re.S)
        i = 0
        while i < len(blocks):
            b = blocks[i]
            if b.startswith('<h3'):
                w = strip_tags(re.match(r'<h3[^>]*>(.*?)</h3>', b, re.S).group(1))
                # h3 后面若**不是** <p>（例如直接跟一个 <ul> 义项列表），此前
                # 一律 i += 2 会把下一块整块吞掉 —— 那个词条的全部义项就此
                # 消失，而且不报任何错（词数闸只看条数，看不见义项没了）。
                # 现在：只有「下一块确实是 <p>、被当作小标题释义吃掉」时才 +2，
                # 否则 +1，让下一块照常被处理。
                nxt = blocks[i + 1] if i + 1 < len(blocks) else ''
                if nxt.startswith('<p'):
                    meaning = strip_tags(nxt)
                    if w and meaning:
                        notes.append(f"{w}: {meaning}")
                    i += 2
                else:
                    i += 1
                continue
            if b.startswith('<ul') or b.startswith('<ol'):
                for li in re.findall(r'<li[^>]*>(.*?)</li>', b, re.S):
                    t = strip_tags(li)
                    if t and not re.match(r'^https?://', t) and '来源于链接' not in t:
                        senses.append(t)
                i += 1
                continue
            inner = re.match(r'<p[^>]*>(.*?)</p>', b, re.S).group(1)
            t = strip_tags(inner)
            if not t or re.match(r'^https?://\S+$', t) or '来源于链接' in t or re.match(r'^[a-z\-/\.]+$', t):
                i += 1
                continue
            if '<a ' in inner and '<strong>' not in inner and re.search(r'https?://', t):
                i += 1
                continue
            if re.search(r'[一-鿿]', t):
                senses.append(re.sub(r'https?://\S+', '', t).strip())
            else:
                notes.append(t)
            i += 1
        entries.append({'num': num, 'word': word, 'senses': [s for s in senses if s],
                        'links': links, 'notes': notes})
    entries.sort(key=lambda e: e['num'])
    return entries

def parse_cats(raw):
    raw = re.sub(r'<script.*?</script>', '', raw, flags=re.S)
    raw = re.sub(r'<style.*?</style>', '', raw, flags=re.S)
    sec = raw[raw.find('class="entry-content'):]
    text = H.unescape(re.sub(r'<[^>]+>', '\n', sec))
    lines = [re.sub(r'\s+', ' ', l).strip() for l in text.split('\n') if l.strip()]
    pos = sub = None
    out = []
    for l in lines:
        m1 = re.match(r'^([一二三四五])、(形容词|副词|动词|名词|连词)$', l)
        m2 = re.match(r'^（([123])）(积极的|消极的|中性的)$', l)
        m3 = re.match(r'^(\d+)\.\s*(.+)$', l)
        if m1:
            pos, sub = m1.group(2), None
        elif m2:
            sub = m2.group(2)
        elif m3 and pos:
            num = int(m3.group(1))
            wm = re.match(r'^([A-Za-z][A-Za-z .,\'’\-–]*?)([一-鿿（(].*)$', m3.group(2).strip())
            if wm:
                out.append({'num': num, 'word': re.sub(r'\s+', ' ', wm.group(1)).strip(),
                            'pos': pos, 'sub': sub, 'gloss': wm.group(2).strip()})
            else:
                print('WARN unparsed line:', l, file=sys.stderr)
    return out

def dump_atomic(path, obj):
    """原子写(v36-④ 册四十九同规): tmp+os.replace,写一半崩溃不再留半截原始件"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', nargs=2, metavar=('PAGE4418', 'PAGE24732'), default=None)
    ap.add_argument('--cache', nargs=2, metavar=('CACHE4418', 'CACHE24732'), default=None,
                    help='缓存 HTML 路径（默认 /tmp/page4418.html /tmp/page24732.html）；'
                         '给了 --offline 时忽略')
    args = ap.parse_args()
    c1, c2 = '/tmp/page4418.html', '/tmp/page24732.html'
    if args.cache:
        c1, c2 = args.cache
    from_cache = True          # 缓存来源（不是用户自备的 --offline 文件）
    if args.offline:
        c1, c2 = args.offline
        from_cache = False     # 用户自备文件：失败时**不**动它（可能是唯一一份样本）
    raw1 = fetch('https://www.guanjihuan.com/archives/4418', c1, offline=bool(args.offline))
    raw2 = fetch('https://www.guanjihuan.com/archives/24732', c2, offline=bool(args.offline))
    words = parse_words(raw1)
    cats = parse_cats(raw2)
    # sanity checks —— 必须**先于写盘**（v36-④ 册四十九同规）
    # 原先断言排在 json.dump 之后：数量对不上时，原始抽取文件已经被坏数据覆盖，
    # 且这两份是「永不手改」的上游原始件，一被覆盖就得重新抓取才能复原。
    # 这里也把 assert 换成显式检查：python -O 会关掉 assert，闸门不能靠它。
    # 这里校验的是「原始抽取」的数量，与整理后的词库数量无关
    errs = []
    if len(words) != 799:
        errs.append(f'expected 799 raw words, got {len(words)}')
    if len(cats) != 344:
        errs.append(f'expected 344 raw cats, got {len(cats)}')
    nums = {w['num'] for w in words}
    bad = [c['num'] for c in cats if c['num'] not in nums]
    if bad:
        errs.append(f'cat words missing from main list: {bad}')
    empty = [w['num'] for w in words if not w['senses'] or not w['senses'][0]]
    if empty:
        errs.append(f'words without meaning: {empty}')
    if errs:
        print('FAILED: raw extract sanity checks (产物未写):')
        for e in errs:
            print('  -', e)
        # 缓存被坏 HTML（404 页 / 半截下载 / 站点改版）占住时，若原样留着，
        # 下次重跑会**继续复用这份坏缓存**、于是永远失败且看不出原因。
        # 隔离掉它（改名为 .bad 留作查证），下次跑就会重新抓取。
        if from_cache:
            for c in (c1, c2):
                if os.path.exists(c):
                    try:
                        os.replace(c, c + '.bad')
                        print('  · 坏缓存已隔离为 %s.bad（下次运行会重新抓取）' % c)
                    except OSError as e:
                        print('  · 缓存隔离失败：%s（%s）' % (c, e))
        sys.exit(1)

    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    dump_atomic(os.path.join(ROOT, 'data', 'words800.json'), words)
    dump_atomic(os.path.join(ROOT, 'data', 'categorized.json'), cats)
    print(f'OK: raw extract — {len(words)} words (source numbering 1-800, #736 absent on source), {len(cats)} categorized')
    print('Next: python3 tools/curate.py && python3 tools/make_data.py')

if __name__ == '__main__':
    main()
