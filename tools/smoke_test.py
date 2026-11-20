#!/usr/bin/env python3
"""Smoke-test the site in headless Chromium via Playwright.
Serves ./ on localhost, then walks every view & core interaction.
Usage: python3 tools/smoke_test.py [--headed] [--base URL]
"""
import argparse, sys, threading, functools, http.server, socketserver, os, time, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 期望值直接从整理后的词表读取，避免测试与数据不同步
_words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))
_cats = json.load(open(os.path.join(ROOT, 'data', 'cats.json'), encoding='utf-8'))
N_WORDS = len(_words)
N_CATS = len(_cats)
N_CONJ = sum(1 for c in _cats if c['pos'] == '连词')
N_OTHER = sum(1 for w in _words if not w.get('pos'))   # 介词 / 固定语块（不设词性）
N_CORE = sum(1 for w in _words if w.get('core'))         # 核心高频词
N_OTHER_CORE = sum(1 for w in _words if not w.get('pos') and w.get('core'))

FAIL = []
PASSED = 0
def ok(name, cond, extra=""):
    global PASSED
    print(("  ✓ " if cond else "  ✗ ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: FAIL.append(name + " " + extra)
    else: PASSED += 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    base = args.base
    if not base:
        os.chdir(ROOT)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        socketserver.TCPServer.allow_reuse_address = True
        # 线程化：浏览器会并行拉取 data.js / examples.js 等多个大文件，
        # 单线程 TCPServer 会串行排队，系统繁忙时 load 事件等不到就超时
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}/"
        time.sleep(0.3)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        import os as _os
        _exe = _os.environ.get('WL_CHROMIUM')
        try:
            browser = pw.chromium.launch(headless=not args.headed, **({'executable_path': _exe} if _exe else {}))
        except Exception:
            # 有些环境只装了完整 Chromium、没有 headless shell，这时退回 channel 模式
            browser = pw.chromium.launch(headless=not args.headed, channel="chromium")
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        # 本机常有并发会话抢 CPU（load 6+），默认 30s 导航超时容易假阳性
        page.set_default_navigation_timeout(90000)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        print("== load ==")
        page.goto(base, wait_until="load")
        ok("no page JS errors on load", not errors, "; ".join(errors[:3]))
        ok("title", "学术英语词汇" in page.title())
        ok("hero visible", page.locator(".hero h1").is_visible())
        ok("dash stats count = 5", page.locator(".dash-stats .stat-card").count() == 5)

        print("== browse ==")
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector(".word-table")
        ok("table rendered", page.locator(".word-table tbody tr").count() > 0)
        n0 = page.locator(".count-line b").first.inner_text()
        ok("word count shown matches data", n0 == str(N_WORDS), f"{n0} vs {N_WORDS}")
        page.fill("#bq", "crucial")
        page.wait_for_timeout(350)
        # 第 51 轮口径：搜索覆盖例句后，crucial 除了命中头词本身，还会带出
        # 「只在例句里出现该词」的行（挂「例」徽标）；头词行必须仍在且不再有例徽标
        rows_c = page.locator(".word-table tbody tr").count()
        head_n = page.locator('.word-table tbody tr', has_text="crucial").count()
        ok("search crucial keeps headword row and appends example-only rows",
           rows_c > 1 and head_n >= 1
           and page.locator(".word-table .tag-ex").count() >= 1, f"rows={rows_c} head={head_n}")
        page.fill("#bq", "至关重要的")
        page.wait_for_timeout(350)
        ok("chinese search works", page.locator(".word-table tbody tr").count() >= 1)
        page.fill("#bq", "")
        page.wait_for_timeout(350)
        page.click('#letterBar .letter-btn[data-l="A"]')
        page.wait_for_timeout(150)
        ok("letter filter A", page.locator(".word-table tbody tr").count() >= 1)
        page.click('#posFilter .chip[data-pos="形容词"]')
        page.wait_for_timeout(150)
        ok("pos filter shows adj rows", page.locator(".word-table tbody tr").count() >= 1)
        # open modal
        page.click("#posFilter .chip >> nth=0")  # 全部
        page.wait_for_timeout(150)
        page.click('.word-table tbody tr >> nth=0')
        page.wait_for_selector("#wordModal:not([hidden])")
        ok("word modal opens", page.locator(".wm-word").is_visible())
        links = page.locator(".wm-links a").count()
        ok("modal has dict links", links >= 1, f"{links} links")
        page.click("#wmMark2")  # mark mastered
        # 保存有 120ms 防抖：等进度真正落盘再继续，避免慢机器上持久化断言抖动
        page.wait_for_function(
            "() => { try { const s = JSON.parse(localStorage.getItem('wl_state_v1') || '{}');"
            "  return Object.values(s.progress || {}).some(p => p.lv >= 5); } catch (e) { return false; } }",
            timeout=5000)
        ok("modal closes on mark", page.locator("#wordModal").is_hidden())
        # 「徽标/连续天数会更新」此前是一条**恒真断言**（ok(..., True)）：什么都没验，
        # 却让这条通过数虚增一格。真断言放在下面闪卡评分之后（那时连续天数从 0 变成 1，
        # 才验得出「UI 跟着状态走」；在 0 天时 aria-label 的初值恰好也是 0，验了等于没验）。

        print("== fav ==")
        page.click('.nav-item[data-view="fav"]')
        page.wait_for_timeout(100)
        ok("fav view (may be empty)", page.locator(".page-title").is_visible())

        print("== flashcards ==")
        # 一百四十九轮：学习/测验合并为 #study 一页，顶栏只剩「学习」一项
        page.click('.nav-item[data-view="study"]')
        page.wait_for_selector(".deck-setup")
        ok("study nav lands on flashcards mode with the mode switch",
           page.locator('#studyModeSeg button[data-m="flashcards"]').get_attribute("aria-pressed") == "true"
           and page.locator('#studyModeSeg button[data-m="quiz"]').count() == 1)
        ok("deck setup shows options", page.locator('.chip[data-s="all"]').count() == 1)
        # 一百九十四轮起是两步流：chip 只选中，「开始学习」确认后才开局
        page.click('.chip[data-s="new"]')
        ok("selecting a deck chip does not start the session (two-step flow)",
           page.locator(".deck-setup").is_visible() and
           page.locator('.chip[data-s="new"]').get_attribute("aria-pressed") == "true")
        page.click("#fcStart")
        page.wait_for_selector(".flip-card")
        ok("flashcard stage", page.locator(".fc-word").first.is_visible())
        # 评分前的当日互动计数与连续天数（评分后应当涨）
        _days_before = page.evaluate(
            "(() => { try { const s = JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            " const v = Object.values(s.days||{}); return v.length ? Math.max.apply(null, v) : 0; }"
            " catch(e) { return 0; } })()")
        _streak_before = page.evaluate("() => window.WL_DEBUG.streak()")
        page.keyboard.press(" ")
        page.wait_for_timeout(550)
        ok("card flipped", page.locator(".flip-card.flipped").count() == 1)
        # 卡高必须按当前 CSS 的实际 padding/border 计算，不能沿用旧版固定补偿值。
        _card_h = page.evaluate("""() => {
            const c = document.querySelector('#flipCard');
            const f = c.querySelector('.flip-back');
            const inner = c.querySelector('.fc-back-inner');
            const s = getComputedStyle(f), px = v => parseFloat(v) || 0;
            const chrome = px(s.paddingTop) + px(s.paddingBottom) + px(s.borderTopWidth) + px(s.borderBottomWidth);
            const need = Math.ceil(inner.offsetHeight + chrome);
            const cap = Math.round(innerHeight * .82);
            return {actual: c.offsetHeight, want: Math.max(420, Math.min(need, cap)), need, cap};
        }""")
        ok("card back height includes its real padding and border",
           abs(_card_h["actual"] - _card_h["want"]) <= 2, str(_card_h))
        # 焦点在例句 summary 上时，空格只展开例句，不应同时触发卡面翻面。
        page.locator(".fc-ex-more summary").focus()
        page.keyboard.press("Space")
        page.wait_for_timeout(450)
        ok("space expands examples without flipping the card",
           page.locator(".fc-ex-more").evaluate("d => d.open")
           and page.locator(".flip-card.flipped").count() == 1)
        # 收藏会重绘牌桌：同一词条的展开状态不能因此被悄悄丢掉。再点一次恢复原收藏态。
        page.click("#fcFav")
        page.wait_for_timeout(400)
        ok("favorite rerender preserves expanded examples",
           page.locator(".fc-ex-more").evaluate("d => d.open")
           and page.locator(".flip-card.flipped").count() == 1)
        page.click("#fcFav")
        page.wait_for_timeout(250)
        page.keyboard.press("1")
        page.wait_for_timeout(250)
        ok("grade 'forgot' advances (may requeue)", page.locator(".flip-card").count() == 1)
        ok("advancing resets the previous card's expanded examples",
           page.evaluate("() => WL_DEBUG.fc.examplesOpen === false && !document.querySelector('.fc-ex-more').open"))
        page.keyboard.press(" ")
        page.wait_for_timeout(550)
        page.keyboard.press("3")
        page.wait_for_timeout(250)
        ok("rating works twice", page.locator(".flip-card, .fc-stage.card").count() >= 1)
        # 评分后：当日互动计数要涨、连续天数要 +1，且顶栏徽标的 aria-label 必须跟着数字走
        # （aria-label 停在初值＝ 屏幕阅读器读到的数字是错的）。
        # 顶栏徽标现已改为「最近 30 天访问次数」（连胜数改由总览页的「连续学习」卡片显示），
        # 故连胜改读 WL_DEBUG.streak()，顶栏这一路只核对可访问名与可见数字一致。
        _days_after = page.evaluate(
            "(() => { try { const s = JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            " const v = Object.values(s.days||{}); return v.length ? Math.max.apply(null, v) : 0; }"
            " catch(e) { return 0; } })()")
        _streak_after = page.evaluate("() => window.WL_DEBUG.streak()")
        _visit_text = page.locator("#visitCount").inner_text()
        _aria_after = page.locator("#visitPill").get_attribute("aria-label") or ""
        ok("grading a card bumps today's activity counter and the streak",
           _days_after > _days_before and int(_streak_after) == int(_streak_before) + 1
           and _aria_after == f"最近 30 天访问 {_visit_text} 次",
           f"days {_days_before}->{_days_after}, streak {_streak_before}->{_streak_after},"
           f" visit={_visit_text}, aria={_aria_after}")
        # exit
        page.click("#fcQuit")
        # 退出按钮坏掉时 wait_for_selector 会一直等到超时并抛出，测试就崩成一坨栈，
        # 看不出是哪一条坏了 ⇒ 改成有界等待 + 断言，让失败以「断言红」的形式出现
        _back = True
        try:
            page.wait_for_selector(".deck-setup", timeout=5000)
        except Exception:
            _back = False
        ok("quit back to setup", _back and page.locator(".deck-setup").is_visible())

        print("== quiz ==")
        # 合并页：顶栏点「学习」再切测验模式（旧 #quiz 导航项已不存在）
        page.click('.nav-item[data-view="study"]')
        page.click('#studyModeSeg button[data-m="quiz"]')
        page.wait_for_selector(".quiz-setup")
        ok("mode switch lands on quiz setup",
           page.locator('#studyModeSeg button[data-m="quiz"]').get_attribute("aria-pressed") == "true"
           and page.locator("#studyModeSeg").count() == 1)
        page.click(".chip[data-m='zh2en']")
        page.click('#startQuiz')
        page.wait_for_selector(".quiz-prompt")
        ok("quiz question rendered", page.locator(".quiz-opt").count() == 4)
        page.click('.quiz-opt[data-ok="true"]')
        page.wait_for_selector("#qFb.show")
        ok("feedback appears", page.locator("#qFb.show").is_visible())
        page.click("#qNext")
        page.wait_for_timeout(200)
        # answer all remaining quickly by clicking 2nd option + next
        for _ in range(30):
            if page.locator(".quiz-result").count(): break
            if page.locator(".quiz-opt").count():
                page.click('.quiz-opt >> nth=0')
                page.wait_for_selector("#qFb.show", timeout=2000)
                page.click("#qNext")
            else: break
        page.wait_for_selector(".quiz-result", timeout=5000)
        ok("quiz completes to result screen", page.locator(".quiz-result").is_visible())
        page.wait_for_timeout(200)
        hist = page.evaluate("""(() => { for (let i=0;i<localStorage.length;i++){
            const k=localStorage.key(i);
            try { const v=JSON.parse(localStorage.getItem(k)); if (v && Array.isArray(v.quizHist)) return v.quizHist.length; } catch(e){}
        } return -1 })()""")
        ok("quiz recorded in history", hist >= 1, str(hist))

        print("== spell mode ==")
        page.click("#backSetup")
        page.click(".chip[data-m='spell']")
        page.click("#startQuiz")
        page.wait_for_selector("#spellInput")
        ok("spell input present", page.locator("#spellInput").is_visible())
        page.fill("#spellInput", "qqqqzzzz")
        page.click("#spellCheck")
        page.wait_for_selector("#qFb.show")
        ok("spell check shows feedback", page.locator("#qFb.no.show").count() == 1)
        page.click("#qQuit")

        print("== grouped browse (原「分类」页，已并入词库的分组视图) ==")
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector("#browseTable")
        page.click('#viewToggle button[data-v="group"]')
        page.wait_for_selector(".cat-word")
        cards = page.locator(".cat-word").count()
        # 分组视图把那批介词与介词短语也铺到末尾一节，卡片数 = 全库词数
        ok("all words rendered in grouped view", cards == N_WORDS, f"{cards} vs {N_WORDS}")
        page.click('#posFilter .chip[data-pos="连词"]')
        page.wait_for_timeout(250)
        ok("conj filter count matches data", page.locator(".cat-word").count() == N_CONJ,
           f"{page.locator(chr(46)+'cat-word').count()} vs {N_CONJ}")
        page.click('#posFilter .chip[data-pos=""]')
        page.wait_for_timeout(250)
        # 那批没有实义词性标签的词（单词介词与介词短语）在「词性」行末尾，
        # 展示名是「介词 / 介词短语」，内部键仍是「其他」
        page.click('#posFilter .chip[data-pos="其他"]')
        page.wait_for_timeout(250)
        ok("其他 filter count matches data",
           page.locator(".cat-word").count() == N_OTHER,
           f"{page.locator(chr(46)+'cat-word').count()} vs {N_OTHER}")
        # 「是否核心」与词性正交：其他 + 核心 = 31（两层同时生效，不互相清掉）
        page.click('#coreFilter .chip[data-core="yes"]')
        page.wait_for_timeout(250)
        ok("其他 + 核心 filter count matches data",
           page.locator(".cat-word").count() == N_OTHER_CORE,
           f"{page.locator(chr(46)+'cat-word').count()} vs {N_OTHER_CORE}")
        page.click('#posFilter .chip[data-pos=""]')
        page.wait_for_timeout(250)
        ok("核心 filter count matches data",
           page.locator(".cat-word").count() == N_CORE,
           f"{page.locator(chr(46)+'cat-word').count()} vs {N_CORE}")
        page.click('#coreFilter .chip[data-core=""]')
        page.wait_for_timeout(250)
        page.click('[data-catdeck="verb"]')
        page.wait_for_selector(".flip-card")
        ok("category → flashcards deck starts", page.locator(".fc-word").first.is_visible())
        page.click("#fcQuit")

        print("== stats ==")
        page.click('.nav-item[data-view="stats"]')
        page.wait_for_selector(".stats-grid")
        ok("stats grid", page.locator(".stats-grid .card").count() >= 4)
        ok("heatmap rendered", page.locator(".heat").count() == 120)

        print("== settings + theme ==")
        page.click('.nav-item[data-view="settings"]')
        page.wait_for_selector("#segTheme")
        page.click('#segTheme button[data-k="dark"]')
        page.wait_for_timeout(150)
        ok("dark theme applied", page.evaluate("document.documentElement.dataset.theme") == "dark")
        page.click('#segTheme button[data-k="light"]')
        # export uses download: just check button exists
        ok("export/import buttons", page.locator("#expBtn").count() == 1 and page.locator("#impBtn").count() == 1)

        print("== persistence ==")
        # 顶栏徽标＝最近 30 天的访问次数：同一浏览器上下文里再打开一次页面
        # （本例用新标签页，与「刷新」等价——都是重新加载一次 app.js），
        # 徽标上的数字必须 +1，且计数只存在本机 localStorage 里。
        _visit_before = page.locator("#visitCount").inner_text()
        page2 = ctx.new_page()
        page2.set_default_navigation_timeout(90000)
        page2.goto(base, wait_until="load")
        _visit_after = page2.locator("#visitCount").inner_text()
        ok("a page load counts as one more visit",
           _visit_after.isdigit() and _visit_before.isdigit()
           and int(_visit_after) == int(_visit_before) + 1,
           f"visit {_visit_before} -> {_visit_after}")
        page2.click('.nav-item[data-view="browse"]')
        page2.wait_for_timeout(200)
        page2.select_option("#bstatus", "mastered")
        try:
            page2.wait_for_selector(".word-table tbody tr", timeout=3000)
        except Exception:
            pass   # 真的没有行时落到下面的断言里报 0，而不是把测试崩掉
        rows = page2.locator(".word-table tbody tr").count()
        ok("progress persisted after reload (>=1 mastered)", rows >= 1, str(rows))
        page2.close()

        print("== mobile ==")
        ctxm = browser.new_context(viewport={"width": 390, "height": 780})
        pm = ctxm.new_page()
        pm.set_default_navigation_timeout(90000)
        errs_m = []
        pm.on("pageerror", lambda e: errs_m.append(str(e)))
        pm.goto(base, wait_until="load")
        ok("mobile home renders", pm.locator(".hero").is_visible())
        ok("no overflow-x on body", pm.evaluate("document.body.scrollWidth <= window.innerWidth + 2"))
        pm.goto(base + "#browse", wait_until="load")
        # 窄屏（≤720px）默认用卡片视图（.wcard-grid），表格视图是桌面端默认
        ok("mobile browse renders", pm.locator(".wcard-grid, .word-table").first.is_visible())
        ok("no mobile JS errors", not errs_m, "; ".join(errs_m[:2]))

        print("== data integrity in page ==")
        n = page.evaluate("window.WL_WORDS.length")
        c = page.evaluate("window.WL_CATS.length")
        ok("page word count matches data", n == N_WORDS, f"{n} vs {N_WORDS}")
        ok("page cat count matches data", c == N_CATS, f"{c} vs {N_CATS}")
        # every word has non-empty senses
        bad = page.evaluate("(window.WL_WORDS||[]).filter(w=>!w.senses||!w.senses.length||!w.senses.some(s=>s.trim())).length")
        ok("every word has a meaning", bad == 0, str(bad))
        all_nums = page.evaluate("[...new Set((window.WL_WORDS||[]).map(w=>w.num))].length")
        ok("unique ids = word count", all_nums == N_WORDS, f"{all_nums} vs {N_WORDS}")

        # 整理结果检查：生僻/不当词已删、高频常用词已补
        obsolete = ["crappy", "vortex", "perovskite", "Greek", "once upon a time", "pico-"]
        still_there = [x for x in obsolete if page.evaluate("w => (window.WL_WORDS||[]).some(v => v.word === w)", x)]
        ok("obscure/unsuitable words removed", not still_there, ",".join(still_there))
        wanted = ["analysis", "framework", "hypothesis", "evidence", "although", "nevertheless", "consequently"]
        missing = [x for x in wanted if not page.evaluate("w => (window.WL_WORDS||[]).some(v => v.word === w)", x)]
        ok("frequent academic words added", not missing, ",".join(missing))
        dupes = page.evaluate("(() => { const a = window.WL_WORDS.map(w => w.word.toLowerCase()); return a.length - new Set(a).size; })()")
        ok("no duplicate words", dupes == 0, str(dupes))
        badlinks = page.evaluate("(() => (window.WL_WORDS||[]).filter(w => !w.links || w.links.length !== 3 || w.links.some(u => u.indexOf('http') !== 0)).length)()")
        ok("every word has 3 dictionary links", badlinks == 0, str(badlinks))
        placeholders = page.evaluate("(() => (window.WL_WORDS||[]).filter(w => /\\bsth\\b|\\bsb\\b/.test(w.word)).length)()")
        ok("no sth/sb placeholders left", placeholders == 0, str(placeholders))

        ok("no accumulated console errors (overall)", not errors, "; ".join(errors[:5]))

        browser.close()

    print()
    if FAIL:
        print(f"RESULT: {len(FAIL)} FAILURES")
        for f in FAIL: print("  -", f)
        sys.exit(1)
    print(f"RESULT: ALL TESTS PASSED ({PASSED} checks passed)")

# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    main()
