#!/usr/bin/env python3
"""Extended smoke-test: covers features the main smoke_test.py does not touch.

Exercises: keyboard shortcuts (/?/Esc/←→), global search overlay + navigation,
favourites, flashcard undo (U), quiz modes (en2zh / zh2en / spell / listen),
settings toggles & persistence, localStorage payload, print list, pagination.

Usage:
    WL_CHROMIUM=/usr/bin/chromium-browser python3 tools/smoke_test_extra.py
"""
import argparse, sys, threading, functools, http.server, socketserver, os, time, json, re, tempfile, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAIL = []
PASSED = 0
def ok(name, cond, extra=""):
    global PASSED
    print(("  ✓ " if cond else "  ✗ ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: FAIL.append(name + " " + extra)
    else: PASSED += 1

def serve():
    os.chdir(ROOT)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)
    return f"http://127.0.0.1:{port}/"

def pick_example_only_token():
    """挑一个「只在一个词的例句里出现」的关键词（全库扫描、确定性）。

    判据三条同时成立：① 该词在**任何**词的词形里都不是子串；② 在**任何**词的
    释义里都不是子串；③ 只出现在**一个**词的例句里（按**子串**判定 ——
    搜索是子串匹配，"abandon" 会连 "abandoning" 一起命中）。
    ⇒ 拿它去搜，必定只出一条结果、且是「仅例句命中」——徽标断言不依赖排序。
    """
    with open(os.path.join(ROOT, "data", "words.json"), encoding="utf-8") as f:
        words = json.load(f)
    with open(os.path.join(ROOT, "data", "examples.json"), encoding="utf-8") as f:
        examples = json.load(f)
    blob = " ".join(w["word"].lower() for w in words)
    blob += " " + " ".join(s.lower() for w in words for s in w.get("senses") or [])
    # 每个词的例句正文并成一段（小写），既是子串判定的底，也是候选词的来源
    ex_blobs = {}
    for w in words:
        ex_blobs[w["word"]] = " ".join(
            (e.get("en") or "") + " " + (e.get("zh") or "")
            for e in examples.get(w["word"]) or []).lower()
    # 便宜的预筛：只在一个词的例句里作为**整词**出现过
    owners = {}
    for ow, b in ex_blobs.items():
        for t in set(re.findall(r"[a-z]{6,}", b)):
            owners.setdefault(t, set()).add(ow)
    for t in sorted(owners):
        if len(owners[t]) != 1 or t in blob:
            continue
        # 贵的复核：子串口径下也只能属于这一个词
        hit = [ow for ow, b in ex_blobs.items() if t in b]
        if len(hit) == 1:
            return t
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    base = args.base or serve()

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = os.environ.get('WL_CHROMIUM')
        try:
            browser = pw.chromium.launch(headless=True, **({'executable_path': exe} if exe else {}))
        except Exception:
            browser = pw.chromium.launch(headless=True, channel="chromium")
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        # 发音回归不依赖跑测试的机器装没装英语语音包：本套件要覆盖「有英语音色」
        # 的功能路径，统一注入可控音色；真正的发声拦截交给 tts_policy_test.py。
        ctx.add_init_script("""
          (() => {
            const synth = {
              getVoices: () => [{name: 'Test US English', lang: 'en-US'}],
              speak: () => {}, cancel: () => {}, onvoiceschanged: null
            };
            Object.defineProperty(window, 'speechSynthesis', {value: synth, configurable: true});
            // 原生 utterance.voice 只接受原生 SpeechSynthesisVoice，测试音色是
            // 普通对象；连 utterance 一起换成数据桩，否则 u.voice=voice 会抛 TypeError。
            window.SpeechSynthesisUtterance = class {
              constructor(text) { this.text = String(text); this.voice = null; this.lang = ''; this.rate = 1; }
            };
          })();
        """)
        page = ctx.new_page()
        # 本机常有并发会话抢 CPU（load 6+），默认 30s 导航超时容易假阳性
        page.set_default_navigation_timeout(90000)
        errors = []
        page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)

        page.goto(base, wait_until="load")

        print("== keyboard shortcuts ==")
        page.keyboard.press("/")
        page.wait_for_timeout(200)
        ok("'/' opens global search", page.locator("#searchOverlay").is_visible())
        page.fill("#searchInput", "crucial")
        page.wait_for_timeout(250)
        n_res = page.locator("#searchResults .sr-item").count()
        ok("search finds a word", n_res >= 1, f"{n_res} results")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        ok("search Enter opens the word modal", page.locator("#wordModal").is_visible())
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        ok("Esc closes the modal", page.locator("#wordModal").is_hidden())

        page.keyboard.press("?")
        page.wait_for_timeout(200)
        ok("'?' opens the shortcuts overlay", page.locator("#shortcutsOverlay").is_visible())
        ok("shortcut rows rendered", page.locator("#shortcutsGrid .shortcuts-row").count() >= 8)
        # ---- 二百零一轮：叠层浮层 Esc 只收最上层 ----
        # 上面 Esc 收掉的只是弹窗，帮助浮层还开着 —— 先 Esc 收掉它再重造叠层：
        # 开弹窗 → ? → Esc 收帮助、弹窗留着 → Esc 收弹窗。
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        ok("help closed before restack", page.locator("#shortcutsOverlay").is_hidden())
        page.goto(base + "#browse", wait_until="load")
        page.wait_for_selector("#browseTable .wt-open", timeout=60000)
        page.locator('#browseTable .wt-open').first.click()
        page.wait_for_timeout(200)
        ok("modal reopened for stacking", page.locator("#wordModal").is_visible())
        page.keyboard.press("?")
        page.wait_for_timeout(200)
        ok("shortcuts stack on modal", page.locator("#shortcutsOverlay").is_visible()
           and page.locator("#wordModal").is_visible())
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        ok("Esc closes only the top layer (shortcuts)",
           page.locator("#shortcutsOverlay").is_hidden() and page.locator("#wordModal").is_visible(),
           f"shortcuts_hidden={page.locator('#shortcutsOverlay').is_hidden()} modal_visible={page.locator('#wordModal').is_visible()}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        ok("second Esc closes the modal", page.locator("#wordModal").is_hidden())
        # 回归残留：搜索开着时 Esc 仍只关搜索（原路径不变）
        page.keyboard.press("/")
        page.wait_for_timeout(200)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        ok("Esc still closes lone search overlay", page.locator("#searchOverlay").is_hidden())

        print("== favourites ==")
        page.click('.nav-item[data-view="fav"]')
        page.wait_for_timeout(200)
        ok("favourites view renders", page.locator(".page-title").is_visible())
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector(".word-table")
        page.click(".word-table tbody tr >> nth=0")
        page.wait_for_selector("#wordModal:not([hidden])")
        fav_btn = page.locator("#wmFav")
        ok("favourite button exists in modal", fav_btn.count() == 1)
        fav_btn.click()
        page.wait_for_timeout(250)
        ok("favourite button toggles to on", "on" in (page.locator("#wmFav").get_attribute("class") or ""))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        page.click('.nav-item[data-view="fav"]')
        page.wait_for_timeout(250)
        ok("favourited word shows in 收藏", page.locator(".word-table tbody tr").count() >= 1)

        print("== flashcards ==")
        page.click('.nav-item[data-view="study"]')
        page.wait_for_selector(".deck-setup")
        page.click('.chip[data-s="all"]')
        page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page.wait_for_selector(".flip-card")
        page.keyboard.press(" ")
        page.wait_for_timeout(500)
        page.keyboard.press("3")
        page.wait_for_timeout(300)
        page.keyboard.press("u")
        page.wait_for_timeout(300)
        ok("undo key does not break the deck", page.locator(".flip-card").count() >= 1)
        page.click("#fcQuit")
        page.wait_for_selector(".deck-setup")

        print("== quiz modes ==")
        page.click('.nav-item[data-view="study"]'); page.click('#studyModeSeg button[data-m="quiz"]')
        page.wait_for_selector(".quiz-setup")
        modes = page.locator(".chip[data-m]").count()
        ok("multiple quiz modes offered", modes >= 3, f"{modes} modes")
        for m in ["en2zh", "zh2en", "spell"]:
            page.click(f".chip[data-m='{m}']")
            page.click("#startQuiz")
            page.wait_for_timeout(400)
            rendered = (page.locator(".quiz-prompt").count() > 0) or (page.locator("#spellInput").count() > 0)
            ok(f"quiz mode {m} renders a question", rendered)
            page.click("#qQuit")
            page.wait_for_selector(".quiz-setup")
            page.wait_for_timeout(200)
        # 听音辨词：context 已注入英语音色与记录用 synth，题目结构与「重播」按钮
        # 必须渲染；「只有中文音色时禁用本题」由 tts_policy_test.py 单独覆盖。
        page.click(".chip[data-m='listen']")
        page.click("#startQuiz")
        page.wait_for_timeout(400)
        ok("quiz mode listen renders options", page.locator(".quiz-opt").count() >= 4)
        page.click("#qReplay")
        page.wait_for_timeout(150)
        ok("listen replay button works", len([e for e in errors if "qReplay" in e or "speak" in e.lower()]) == 0)
        page.click("#qQuit")
        page.wait_for_selector(".quiz-setup")

        print("== settings toggles persist ==")
        page.click('.nav-item[data-view="settings"]')
        page.wait_for_selector("#segHint")
        page.click('#segHint button[data-k="1"]')
        page.wait_for_timeout(250)
        page.click('.nav-item[data-view="home"]')
        page.wait_for_timeout(200)
        page.click('.nav-item[data-view="settings"]')
        page.wait_for_selector("#segHint")
        cur = page.evaluate("document.querySelector('#segHint button.on')?.dataset.k")
        ok("front-hint setting persists across view switch", cur == "1", str(cur))
        page.click('#segHint button[data-k="0"]')
        page.wait_for_timeout(200)

        print("== storage ==")
        keys = page.evaluate("Object.keys(localStorage)")
        ok("state stored in localStorage", len(keys) >= 1, ",".join(keys))

        print("== pagination & filters ==")
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector(".word-table")
        page.click('#letterBar .letter-btn[data-l="A"]')
        page.wait_for_timeout(200)
        rows_a = page.locator(".word-table tbody tr").count()
        ok("letter filter returns rows", rows_a >= 1, str(rows_a))
        page.click('#letterBar .letter-btn[data-l="A"]')
        page.wait_for_timeout(200)
        # 「←/→ 翻页」此前是两条恒真断言（ok(..., True)）：翻没翻页都没人管。
        # 改成真断言：读分页器上「当前页」按钮（.pager button.on）的页码，
        # 右键后页码必须变、左键后必须回到原页。
        def _cur_page():
            loc = page.locator(".pager button.on")
            return loc.inner_text().strip() if loc.count() else ""
        pg_before = _cur_page()
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(300)
        pg_after = _cur_page()
        ok("ArrowRight pages forward",
           bool(pg_before) and bool(pg_after) and pg_after != pg_before,
           f"page {pg_before} -> {pg_after}")
        # 「← 能退回去」单看很容易恒真：若「→」根本没翻页，← 再按也是停在原处。
        # 故先连按两次 →（到第 3 页），再按一次 ←：必须精确回到第 2 页（= pg_after），
        # 这一步在「→ 坏了」的世界里必然失败，不会假绿。
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(300)
        pg_two = _cur_page()
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(300)
        pg_back = _cur_page()
        ok("ArrowLeft pages back",
           bool(pg_two) and bool(pg_back) and pg_two != pg_after and pg_back == pg_after,
           f"page {pg_before} -> {pg_after} -> {pg_two} -> {pg_back}")
        # 复位回第 1 页，保持后续步骤看到的视图与改动前一致
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(300)

        print("== print list ==")
        page.click("#btnPrint")
        page.wait_for_timeout(500)
        items = page.evaluate("document.querySelectorAll('#printList .pl-item').length")
        ok("print list populated", items >= 1, str(items))
        has_ex = page.evaluate("document.querySelectorAll('#printList .pl-ex').length")
        ok("print list carries examples", has_ex >= 3, str(has_ex))

        print("== regressions ==")
        # 闪卡「每次上限」必须对所有入口生效（含总览 CTA、分类、收藏）
        # 合并页的模式是持久的（上一段测验用例把页面留在了测验模式）：显式切回翻卡
        page.click('.nav-item[data-view="study"]')
        page.click('#studyModeSeg button[data-m="flashcards"]')
        page.wait_for_selector(".deck-setup")
        page.fill("#fcLimit", "7")
        page.dispatch_event("#fcLimit", "change")
        page.wait_for_timeout(200)
        saved_limit = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).settings.fcLimit")
        ok("flashcard limit is persisted", saved_limit == 7, str(saved_limit))
        page.click('.nav-item[data-view="home"]')
        page.wait_for_timeout(200)
        page.click("#goReview")
        page.wait_for_selector(".fc-stage")
        total = page.evaluate("document.querySelector('.fc-meta')?.textContent.trim()")
        ok("home CTA respects the card limit", "/ 7" in (total or ""), str(total))
        page.click("#fcQuit")
        page.wait_for_selector(".deck-setup")

        # 分组视图（词库页第三种视图，原「分类」页）「形容词 → 本类闪卡」必须是形容词词组，而不是核心高频词
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector("#browseTable")
        page.click('#viewToggle button[data-v="group"]')
        page.wait_for_selector("[data-catdeck='adj']")
        page.click('[data-catdeck="adj"]')
        page.wait_for_selector(".fc-stage")
        label = page.evaluate("document.querySelector('.fc-progress span')?.textContent.trim()")
        ok("adjective deck is used by 分组视图", "形容词" in (label or ""), str(label))
        page.click("#fcQuit")
        page.wait_for_selector(".deck-setup")

        # 撤销评分要把当天的互动次数一起退回来
        page.click('.chip[data-s="all"]')
        page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page.wait_for_selector(".flip-card")
        day_before = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).days[Object.keys(JSON.parse(localStorage.getItem('wl_state_v1')).days)[0]] || 0")
        page.keyboard.press(" ")
        page.wait_for_timeout(500)
        page.keyboard.press("3")
        page.wait_for_timeout(300)
        day_after = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).days[Object.keys(JSON.parse(localStorage.getItem('wl_state_v1')).days)[0]] || 0")
        page.keyboard.press("u")
        page.wait_for_timeout(300)
        day_undo = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).days[Object.keys(JSON.parse(localStorage.getItem('wl_state_v1')).days)[0]] || 0")
        ok("undo restores the daily activity counter", day_after == day_before + 1 and day_undo == day_before,
           f"{day_before} -> {day_after} -> {day_undo}")
        page.click("#fcQuit")
        page.wait_for_selector(".deck-setup")
        # 视图是持久的（跟表格/卡片一个规矩）：分组视图下线的用例要切回表格，
        # 否则后面的用例在同一页里找不到 .word-table
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector("[data-v='table']")
        page.click("#viewToggle button[data-v='table']")
        page.wait_for_selector(".word-table")

        # 收藏不应继承词库页看不见的筛选条件
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector(".word-table")
        page.select_option("#bstatus", "mastered")
        page.wait_for_timeout(250)
        page.click('.nav-item[data-view="fav"]')
        page.wait_for_timeout(300)
        fav_n = page.evaluate("Number((document.querySelector('.page-title .faint')?.textContent.match(/(\\d+)/)||[0,0])[1])")
        rows = page.locator(".word-table tbody tr").count()
        # 此前这条是「fav_n == 0 或 rows == fav_n」：没有收藏时恒真，等于没验。
        # 收藏在本套件前面已加过一个（wmFav 点过一次），所以这里要求 fav_n >= 1，
        # 并且行数必须与收藏数一致——收藏不该继承词库页遗留的「已掌握」筛选。
        ok("favourites ignore leftover browse filters", fav_n >= 1 and rows == fav_n,
           f"{rows} rows vs {fav_n} favs")

        # 切换视图要回到页面顶部
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector(".word-table")
        page.evaluate("window.scrollTo(0, 600)")
        page.wait_for_timeout(200)
        page.click('.nav-item[data-view="stats"]')
        page.wait_for_timeout(400)
        y = page.evaluate("window.scrollY")
        ok("switching views scrolls back to top", y <= 10, str(y))

        # 「?」再按一次应关闭快捷键面板
        page.keyboard.press("?")
        page.wait_for_timeout(200)
        page.keyboard.press("?")
        page.wait_for_timeout(200)
        ok("'?' toggles the shortcuts overlay off", page.locator("#shortcutsOverlay").is_hidden())

        # ---- 第十九轮修复的定向回归 ----

        # 带修饰键的组合必须让位给浏览器：闪卡里 Ctrl+S 不能顺手切换收藏
        page.click('.nav-item[data-view="study"]'); page.click('#studyModeSeg button[data-m="flashcards"]')
        page.wait_for_selector(".deck-setup")
        page.click('.chip[data-s="all"]')
        page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page.wait_for_selector(".flip-card")
        fav_before = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).fav.length")
        page.keyboard.press("Control+s")
        page.wait_for_timeout(250)
        fav_after_mod = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).fav.length")
        ok("Ctrl+S does not toggle the favourite", fav_after_mod == fav_before, f"{fav_before} -> {fav_after_mod}")
        page.keyboard.press("s")
        page.wait_for_timeout(250)
        fav_after_plain = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).fav.length")
        ok("plain S still toggles the favourite", fav_after_plain != fav_before, f"{fav_before} -> {fav_after_plain}")
        page.keyboard.press("s")
        page.wait_for_timeout(250)   # 还原，别把脏收藏留给后面的用例
        page.click("#fcQuit")
        page.wait_for_selector(".deck-setup")

        # 跳过全部题目的测验：存档口径应为「作答 0 题 · 跳过 10 题」，而不是把跳过算成答错
        page.click('.nav-item[data-view="study"]'); page.click('#studyModeSeg button[data-m="quiz"]')
        page.wait_for_selector(".quiz-setup")
        page.click(".chip[data-m='en2zh']")   # 前面的用例把题型留在了 listen，显式选回四选一
        page.wait_for_selector(".quiz-setup")
        page.click("#startQuiz")
        page.wait_for_selector(".quiz-card")
        for _ in range(10):
            page.click("#qSkip")
            page.wait_for_timeout(120)
        page.wait_for_selector(".quiz-result")
        hist = page.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).quizHist.slice(-1)[0]")
        ok("quiz history counts answered, not asked", hist.get("total") == 0 and hist.get("skipped") == 10,
           f"total={hist.get('total')} skipped={hist.get('skipped')}")
        body = page.evaluate("document.querySelector('.quiz-result').textContent")
        ok("result page shows the skipped count", "跳过 10" in body)

        # 收藏里取消收藏应停留在当前页，而不是被无声拽回第 1 页
        # 收藏里取消收藏应停留在当前页，而不是被无声拽回第 1 页。
        # 造 60 个收藏必须在新页面里用 add_init_script 种（先于应用脚本执行、
        # 先于应用的 beforeunload 监听注册）——运行中改 localStorage 再 reload
        # 会被应用卸载时的回写覆盖。
        nums60 = page.evaluate("JSON.stringify(window.WL_WORDS.slice(0, 60).map(w => w.num))")
        nums60 = json.loads(nums60)
        page2 = ctx.new_page()
        page2.set_default_navigation_timeout(90000)
        page2.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page2.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        page2.add_init_script(
            "try{const s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            f"s.fav={json.dumps(nums60)};"
            "localStorage.setItem('wl_state_v1',JSON.stringify(s));}catch(e){}")
        page2.goto(base + "#fav", wait_until="load")
        page2.wait_for_selector(".pager button[data-p='2']")
        page2.click(".pager button[data-p='2']")
        page2.wait_for_timeout(250)
        page2.click(".word-table tbody tr .mini-btn[data-act='fav']")   # 取消收藏第 2 页首行
        page2.wait_for_timeout(300)
        on_page = page2.evaluate("document.querySelector('.pager button.on')?.textContent.trim()")
        rows_p2 = page2.locator(".word-table tbody tr").count()
        ok("unfavouriting in 收藏 keeps the page", on_page == "2" and rows_p2 == 9,
           f"page={on_page} rows={rows_p2}")
        page2.close()

        # 全库学完后首页 CTA 应指向「保温复习」，而不是 0 词的「从新词开始」死路
        all_nums = json.loads(page.evaluate("JSON.stringify(window.WL_WORDS.map(w => w.num))"))
        page3 = ctx.new_page()
        page3.set_default_navigation_timeout(90000)
        page3.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page3.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        page3.add_init_script(
            "try{const s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');const p={},now=Date.now();"
            f"for(const n of {json.dumps(all_nums)})p[n]={{lv:5,due:now+120*864e5,seen:1,correct:1,wrong:0,last:now}};"
            "s.progress=p;localStorage.setItem('wl_state_v1',JSON.stringify(s));}catch(e){}")
        page3.goto(base + "#home", wait_until="load")
        page3.wait_for_selector("#goReview")
        cta = page3.evaluate("document.querySelector('#goReview').textContent")
        ok("home CTA falls back to 保温复习 when nothing is new",
           "保温复习" in cta and str(len(all_nums)) in cta, cta.strip())   # 词数动态取，勿再写字面量
        page3.click("#goReview")
        page3.wait_for_selector(".flip-card")
        ok("the fallback CTA opens a real session", page3.locator(".fc-stage").count() == 1)
        page3.close()

        # ---- 第二十一轮修复的定向回归 ----

        # 输入法合成中的按键必须让位给 IME：候选框里按 Esc 是「取消候选」，不能把详情弹窗关掉
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector(".word-table")
        page.click(".wt-open >> nth=0")
        page.wait_for_selector("#wordModal:not([hidden])")
        ime_ok = page.evaluate(
            "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,isComposing:true})),"
            "!document.getElementById('wordModal').hidden")
        ok("Esc while IME-composing does not close the modal", ime_ok)
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        ok("real Esc still closes the modal", page.locator("#wordModal").is_hidden())

        # 翻卡隐藏面不得留在 Tab 序列里（backface-visibility 只裁渲染不裁焦点）
        page.click('.nav-item[data-view="study"]'); page.click('#studyModeSeg button[data-m="flashcards"]')
        page.wait_for_selector(".deck-setup")
        page.click('.chip[data-s="all"]')
        page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page.wait_for_selector(".flip-card")
        face = page.evaluate(
            "const b=document.getElementById('fcSpeak2'); b.focus();"
            "[getComputedStyle(document.querySelector('.flip-back')).visibility,"
            " document.activeElement.id === 'fcSpeak2']")
        ok("card back face is hidden when not flipped", face[0] == "hidden", str(face[0]))
        ok("hidden back-face speak button is not focusable", face[1] is False)
        page.click(".fc-word")            # 点单词翻面（卡片中心是朗读钮，不能直接点 .flip-card）
        page.wait_for_timeout(500)        # visibility 延迟一整个翻面时长生效
        face2 = page.evaluate(
            "const r=document.getElementById('fcReveal'); r.focus();"
            "[getComputedStyle(document.querySelector('.flip-front')).visibility,"
            " document.activeElement === r]")
        ok("card front face is hidden after flip", face2[0] == "hidden", str(face2[0]))
        ok("hidden 显示答案 button is not focusable when flipped", face2[1] is False)
        page.click("#fcQuit")
        page.wait_for_selector(".deck-setup")

        # 全部跳过的测验：结果页给中性文案，历史与趋势不再出现红色 0/0
        page.click('.nav-item[data-view="study"]'); page.click('#studyModeSeg button[data-m="quiz"]')
        page.wait_for_selector(".quiz-setup")
        page.click(".chip[data-m='en2zh']")
        page.click("#startQuiz")
        page.wait_for_selector(".quiz-card")
        for _ in range(10):
            page.click("#qSkip")
            page.wait_for_timeout(80)
        page.wait_for_selector(".quiz-result")
        res = page.evaluate("document.querySelector('.quiz-result').textContent")
        ok("all-skipped result page uses neutral copy", "全部跳过" in res and "别灰心" not in res)
        page.click('.nav-item[data-view="stats"]')
        page.wait_for_selector(".stats-grid")
        grid = page.evaluate("document.querySelector('.stats-grid').textContent")
        ok("skipped sessions marked 未作答 in history", "未作答" in grid and "0/0（0%）" not in grid)
        # 两条记录全是 total=0 的跳过场：有效样本为 0，趋势卡必须显示门槛提示而不是画 0% 假曲线
        ok("zero-answer sessions excluded from accuracy trend", "完成 2 次以上" in grid)
        page.click('.nav-item[data-view="home"]')
        page.wait_for_selector(".hero")
        home = page.evaluate("document.querySelector('#main').textContent")
        ok("home recent list also avoids red 0/0", "未作答" in home and "0/0" not in home)
        h1 = page.evaluate("document.querySelector('.hero h1')?.textContent || ''")
        # 首页大标题的口径变更（产品口径）：旧口径是「每天练习 N 次，一年吃透学术表达」，
        # 那句把「打卡次数」抬成第一卖点，等于替用户硬性规定学习强度——现口径是
        # 「常见的学术英语词汇」这样的中性描述。因此本断言同步改口径：
        #   ① 标题里不许再出现「每天/一次」式的每日配额承诺；
        #   ② 标题必须点明词库定位（标题以「常见」起头），不是只报一个词数；
        #   ③ 仍不许退化成纯数量的标题（「个词」计数式）。
        ok("hero headline describes the corpus without imposing a daily quota",
           "每天" not in h1 and h1.startswith("常见") and "个词" not in h1, h1)

        # 听音辨词：换题时必须清掉上一题的自动重播定时器。
        # 不能靠「60ms 内点跳过」的真实竞速来复现（并发会话抢 CPU 时必翻车，
        # 本机实测 spoken=2 全是竞态假阳性）——把 150ms 的重播定时器接管进
        # 一个手动发射队列：跳过后再发射，残留旧定时器会被数出来。
        page.evaluate(
            "window.__spoken=[]; const O=window.SpeechSynthesisUtterance;"
            "window.SpeechSynthesisUtterance=function(t){window.__spoken.push(String(t)); return new O(t)};"
            "window.__t=new Map(); window.__id=1;"
            "window.__st=window.setTimeout.bind(window); window.__ct=window.clearTimeout.bind(window);"
            "window.setTimeout=function(fn,ms,...a){ if(ms===150){const h=window.__id++; window.__t.set(h,{fn}); return h;}"
            " return window.__st(fn,ms,...a);};"
            "window.clearTimeout=function(h){ if(window.__t.has(h)){window.__t.delete(h); return;} return window.__ct(h);};"
            "window.__fire=()=>{const m=window.__t; window.__t=new Map(); m.forEach(r=>r.fn()); return m.size};")
        page.click('.nav-item[data-view="study"]'); page.click('#studyModeSeg button[data-m="quiz"]')
        page.wait_for_selector(".quiz-setup")
        page.click(".chip[data-m='listen']")
        page.click("#startQuiz")
        page.wait_for_selector(".quiz-card")
        page.click("#qSkip")               # 立刻换题：第 1 题的重播定时器应已被 clearTimeout
        page.wait_for_timeout(200)
        fired = page.evaluate("window.__fire()")   # 统一发射「还活着」的定时器
        spoken = page.evaluate("window.__spoken")
        ok("skipping cancels the stale auto-replay", fired == 1 and len(spoken) == 1,
           f"pending={fired} spoken={spoken}")
        page.evaluate("window.setTimeout=window.__st; window.clearTimeout=window.__ct;")
        page.click("#qQuit")
        page.wait_for_selector(".quiz-setup")

        # 设置页语速滑杆：拖动时说明里的倍率数字要即时跟进
        page.click('.nav-item[data-view="settings"]')
        page.wait_for_selector("#rateRange")
        page.evaluate("const r=document.getElementById('rateRange');r.value='1.2';"
                      "r.dispatchEvent(new Event('input'));")
        rv = page.evaluate("document.getElementById('rateVal')?.textContent")
        ok("rate label updates while dragging", rv == "1.20", str(rv))

        # 无障碍与降级：noscript 兜底存在；顶栏徽标有可读标签
        ok("page ships a noscript fallback", page.evaluate("document.querySelectorAll('noscript').length") == 1)
        aria = page.evaluate("document.getElementById('visitPill').getAttribute('aria-label')")
        ok("top-bar badge carries a readable label", (aria or "").startswith("最近 30 天访问"), str(aria))

        # ---- 第二十四轮修复的定向回归 ----

        # F1 详情弹窗复用滚动容器：换词/重开必须回到顶部（压扁容器制造真溢出，与内容长短无关）
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector('.word-table tbody tr .wt-open')
        page.click('.word-table tbody tr .wt-open')
        page.wait_for_selector('#wordModal:not([hidden])')
        page.evaluate("const b=document.getElementById('wordModalBody');"
                      "b.style.maxHeight='80px'; b.style.overflowY='auto'; b.scrollTop=60;")
        scrolled = page.evaluate("document.getElementById('wordModalBody').scrollTop")
        page.click('#wmNext')
        page.wait_for_timeout(150)
        after = page.evaluate("document.getElementById('wordModalBody').scrollTop")
        ok("modal scrolls back to top on word switch", scrolled > 0 and after == 0, f"{scrolled} -> {after}")
        page.evaluate("const b=document.getElementById('wordModalBody');b.style.maxHeight='';b.style.overflowY='';")
        page.keyboard.press("Escape")
        page.wait_for_selector('#wordModal[hidden]', state="attached")

        # F2 导出备份的 <a> 必须在文档内被点击（Firefox 对游离节点不执行 download）；
        # 接管 prototype.click 只记录不真下载，避免高负载机上的下载事件竞速
        page.click('.nav-item[data-view="settings"]')
        page.wait_for_selector('#expBtn')
        # 注意：两段 evaluate 都要以 null 收尾——若完成值是刚赋的函数，
        # Playwright 会把它当返回值执行一次（this 变 window，contains 即抛）
        page.evaluate("window.__anc=null;window.__oanc=HTMLAnchorElement.prototype.click;"
                      "HTMLAnchorElement.prototype.click=function(){window.__anc={inDom:document.body.contains(this)};};"
                      "null")
        page.click('#expBtn')
        anc = page.evaluate("window.__anc")
        page.evaluate("HTMLAnchorElement.prototype.click=window.__oanc;"
                      "delete window.__anc;delete window.__oanc;null")
        ok("export anchor is in the DOM when clicked", bool(anc) and anc["inDom"] is True, str(anc))

        # F3 用户直接 Ctrl+P：beforeprint 必须重建打印清单，否则打印样式隐藏一切 → 空白纸
        page.evaluate("document.getElementById('printList').innerHTML='';"
                      "window.dispatchEvent(new Event('beforeprint'));")
        pl = page.evaluate("document.querySelectorAll('#printList .pl-item').length")
        ok("beforeprint rebuilds the print list", pl > 0, f"items={pl}")

        # F5 热力格 tooltip 同时走原生 title（CSS :hover 提示触屏/读屏取不到）
        page.click('.nav-item[data-view="stats"]')
        page.wait_for_selector('.heat')
        ht = page.evaluate("(()=>{const hs=[...document.querySelectorAll('.heat')];"
                           "return {n:hs.length,ok:hs.filter(h=>h.title&&h.title===h.dataset.tip).length};})()")
        ok("heat cells mirror data-tip into native title", ht["n"] > 0 and ht["ok"] == ht["n"], str(ht))

        # F7 未知 hash 归一化：渲染首页之外，地址栏也不能留坏值
        page.evaluate("location.hash='#nope'")
        page.wait_for_timeout(200)
        hv = page.evaluate("({hash:location.hash,view:document.body.dataset.view})")
        ok("unknown hash is normalized in the URL", hv["hash"] == "#home" and hv["view"] == "home", str(hv))

        # F4 重置进度后顶栏连胜必须归零（days 清空但不重跑 updateStreakPill 的话火苗还挂着旧数字）。
        # 今天写入 days 种子 → 新页启动读到连胜 ≥1 → 设置页 resetProg（confirm 自动接受）→ 0
        page4 = ctx.new_page()
        page4.set_default_navigation_timeout(90000)
        page4.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page4.on("dialog", lambda d: d.accept())
        page4.add_init_script(
            "try{const s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            "const d=new Date(),k=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');"
            "s.days=Object.assign({},s.days,{[k]:40});localStorage.setItem('wl_state_v1',JSON.stringify(s));}catch(e){}")
        page4.goto(base + "#settings", wait_until="load")
        page4.wait_for_selector('#resetProg')
        # 连胜数现在显示在总览页的「连续学习」卡片里（顶栏徽标已改为访问次数）
        before = int(page4.evaluate("() => window.WL_DEBUG.streak()"))
        page4.click('#resetProg')
        page4.wait_for_timeout(250)
        after_n = page4.evaluate("() => window.WL_DEBUG.streak()")
        page4.goto(base + "#home", wait_until="load")
        page4.wait_for_timeout(400)
        shown = page4.evaluate(
            "() => { const e = document.querySelector('.stat-card[aria-label^=\"连续学习\"] .v');"
            " return e ? e.textContent.trim() : null; }")
        ok("resetting progress zeroes the streak", before >= 1 and after_n == 0 and shown == "0 天",
           f"before={before} after={after_n} shown={shown}")
        page4.close()

        # ---- 第二十五轮修复的定向回归 ----

        # A 弹窗内换词后关闭，焦点必须还给最初的触发按钮
        # （←→ 换词时旧按钮随 innerHTML 销毁，activeElement 短暂为 body——曾被误记成触发元素）
        page.click('.nav-item[data-view="browse"]')
        page.wait_for_selector('.word-table tbody tr .wt-open')
        first_word = page.evaluate("document.querySelector('.word-table tbody tr .wt-open').textContent.trim()")
        page.click('.word-table tbody tr .wt-open')
        page.wait_for_selector('#wordModal:not([hidden])')
        page.click('#wmNext')
        page.wait_for_timeout(150)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        ae = page.evaluate("({cls:document.activeElement.className, txt:(document.activeElement.textContent||'').trim()})")
        ok("focus returns to the row button after modal word-switch",
           "wt-open" in ae["cls"] and ae["txt"] == first_word, f"active={ae['cls']}|{ae['txt']} want={first_word}")

        # D 全局搜索连按 ↓，选中项必须滚进可视区（结果区 52vh 可滚，第 11 条在折叠线外）
        page.keyboard.press("/")
        page.wait_for_selector('#searchOverlay:not([hidden])')
        page.fill('#searchInput', 'e')
        page.wait_for_timeout(400)
        cnt = page.evaluate("document.querySelectorAll('.sr-item').length")
        for _ in range(11):
            page.keyboard.press("ArrowDown")
        page.wait_for_timeout(100)
        vis = page.evaluate("""(() => {const sr=document.getElementById('searchResults');
            const el=document.getElementById('srOpt10'); if(!el) return null;
            const r=sr.getBoundingClientRect(), e=el.getBoundingClientRect();
            return {top:e.top>=r.top-1, bottom:e.bottom<=r.bottom+1};})()""")
        ok("keyboard selection scrolls into view in search results", cnt >= 11 and vis and vis["top"] and vis["bottom"],
           f"items={cnt} vis={vis}")
        page.keyboard.press("Escape")

        # B+C 合用一页种子：单个 L5 词 + 老格式测验记录（无 modeName/scopeName 快照）。
        # 注意用 % 格式化：这是普通字符串，勿写 {{ }}（那是 f-string 的转义习惯，
        # 会原样进 JS 造成解析失败，整个 init 脚本静默报废、断言蹭历史数据假绿）
        seed_num = int(page.evaluate("window.WL_WORDS[0].num"))
        seed_word = page.evaluate("window.WL_WORDS[0].word")
        page5 = ctx.new_page()
        page5.set_default_navigation_timeout(90000)
        page5.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page5.add_init_script(
            "try{const s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            "s.progress={%d:{lv:5,due:Date.now()+120*864e5,seen:5,correct:5,wrong:0,last:Date.now()}};"
            "s.quizHist=[{t:Date.now()-3600e3,mode:'en2zh',scope:'fav',score:3,total:5}];"
            "localStorage.setItem('wl_state_v1',JSON.stringify(s));}catch(e){}" % seed_num)
        # 种子生效自检：mastered 牌组必须恰好 1 词（否则后面 B 的「1/1 会话」不成立）
        page5.goto(base + "#home", wait_until="load")
        p5prog = page5.evaluate("Object.keys(JSON.parse(localStorage.getItem('wl_state_v1')).progress).length")
        ok("round-25 seed applied (exactly one mastered)", p5prog == 1, f"progressKeys={p5prog}")
        page5.wait_for_selector(".quiz-hist-item")
        hh = page5.evaluate("document.querySelector('.quiz-hist-item').textContent")
        ok("legacy quizHist rows fall back to derived names", "看词选义" in hh and "收藏" in hh and "3/5" in hh, hh.strip())
        # C 统计页同一口径
        page5.click('.nav-item[data-view="stats"]')
        page5.wait_for_selector('.quiz-hist-item')
        sh = page5.evaluate("document.querySelector('.quiz-hist-item').textContent")
        ok("stats history uses the same fallback", "看词选义" in sh, sh.strip()[:80])
        # B 保温复习里评「模糊」：L5 必须降回 L4 并真正回到队列，而不是留一条永不生效的 due
        page5.click('.nav-item[data-view="study"]'); page5.click('#studyModeSeg button[data-m="flashcards"]')
        page5.wait_for_selector('.deck-opt[data-s="mastered"]')
        page5.click('.deck-opt[data-s="mastered"]')
        page5.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page5.wait_for_selector('.flip-card')
        card_word = page5.evaluate("document.querySelector('.fc-word').textContent")
        page5.click('.fc-word')          # 翻面（.flip-card 中心是朗读钮，点 .fc-word）
        page5.wait_for_timeout(500)      # 等隐藏面 visibility 延迟过渡结束
        page5.keyboard.press("2")        # 模糊
        page5.wait_for_timeout(600)      # save() 120ms 防抖 + finishSession
        done_txt = page5.evaluate("document.body.textContent")
        prog5 = page5.evaluate(f"JSON.parse(localStorage.getItem('wl_state_v1')).progress[{seed_num}]")
        now_ms = time.time() * 1000
        ok("rating a mastered card 模糊 demotes L5 to L4 and it re-queues",
           "本轮复习完成" in done_txt and card_word == seed_word
           and prog5["lv"] == 4 and 0 < prog5["due"] - now_ms < 8 * 864e5,
           f"lv={prog5['lv']} dueIn={(prog5['due']-now_ms)/864e5:.2f}d")
        page5.close()

        # ---- 第二十六轮（用户动线打磨）定向回归 ----

        # H1 浏览器标签标题跟随页面切换（多开标签时能认出哪个是词库/统计）
        page6 = ctx.new_page()
        page6.set_default_navigation_timeout(90000)
        page6.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page6.goto(base + "#stats", wait_until="load")
        page6.wait_for_selector(".stats-grid")
        t_stats = page6.evaluate("document.title")
        ok("tab title reflects the stats view", t_stats.endswith(" · 统计"), t_stats)
        page6.click('.nav-item[data-view="browse"]')
        page6.wait_for_selector('#browseTable')
        t_br = page6.evaluate("document.title")
        ok("tab title updates on navigation and keeps the site prefix",
           t_br.endswith(" · 词库") and t_br.split(" · ", 1)[0] == t_stats.split(" · ", 1)[0],
           f"{t_stats!r} -> {t_br!r}")

        # H2 首页：每日一词的朗读钮不再谎称 (P) 快捷键；翻卡提示限定到学习场景
        # （goto 同文档换 hash 属同文档导航，等待语义不稳，统一用点击导航切换）
        page6.click('.nav-item[data-view="home"]')
        page6.wait_for_selector('#wodSpeak')
        h2 = page6.evaluate("({t:document.getElementById('wodSpeak').title,"
                            "hint:document.querySelector('.hero-hint').textContent})")
        ok("home drops the bogus (P) shortcut claim and scopes the space hint",
           h2["t"] == "朗读" and "学习时按" in h2["hint"], str(h2))
        # 首页改名后，标签页标题不挂页面名（只显站名）；顶栏首项文案改口
        t_home = page6.evaluate("document.title")
        ok("tab title on home keeps the site name only", t_home == "GUAN 学术英语词汇库", t_home)
        nav_home = page6.evaluate("document.querySelector('.nav-item[data-view=\"home\"] span:last-child').textContent")
        ok("nav item is renamed to 首页", nav_home.strip() == "首页", nav_home)

        # H5 全局搜索：空查询的随机列表要有来源说明，输入后说明消失
        page6.keyboard.press("/")
        page6.wait_for_selector('#searchOverlay:not([hidden])')
        lab0 = page6.evaluate("(document.querySelector('#searchResults .sr-label')||{}).textContent || ''")
        page6.fill('#searchInput', 'e')
        page6.wait_for_timeout(400)
        lab1 = page6.evaluate("!!document.querySelector('#searchResults .sr-label')")
        ok("search suggestions carry a label before typing; label clears on query",
           "随机推荐" in lab0 and not lab1, f"label0={lab0.strip()[:24]!r} shownAfterQuery={lab1}")
        page6.keyboard.press("Escape")

        # H3 评分钮的「按 1/2/3」小字受「显示快捷键提示」开关管辖。
        # 开关走设置页 UI 而不是种子——localStorage 在 context 内共享，写脏了会污染以后的运行
        page6.click('.nav-item[data-view="study"]'); page6.click('#studyModeSeg button[data-m="flashcards"]')
        page6.wait_for_selector('.deck-opt[data-s="all"]')
        page6.click('.deck-opt[data-s="all"]')
        page6.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page6.wait_for_selector('.flip-card')
        page6.click('.fc-word')          # 翻面（.flip-card 几何中心是朗读钮）
        page6.wait_for_timeout(500)      # 等隐藏面 visibility 过渡结束
        kh_on = page6.evaluate("[...document.querySelectorAll('.fc-btns .kbd-hint')].map(e=>e.textContent.trim())")
        ok("grade-button key hints show while the hint setting is on",
           kh_on == ["· 按 1", "· 按 2", "· 按 3"], str(kh_on))
        page6.click('.nav-item[data-view="settings"]')
        page6.wait_for_selector('#segKeyHint button[data-k="0"]')
        page6.click('#segKeyHint button[data-k="0"]')
        page6.click('.nav-item[data-view="study"]')
        page6.wait_for_selector('.flip-card')     # fc.session 还在，直接回渲染的舞台
        page6.wait_for_timeout(200)
        off = page6.evaluate("({hints:document.querySelectorAll('.fc-btns .kbd-hint').length,"
                             "small:document.querySelector('.fc-btns .btn.bad small').textContent})")
        ok("grade-button key hints hide with the setting off; interval hints stay",
           off["hints"] == 0 and "今天再来一次" in off["small"], str(off))
        page6.click('.nav-item[data-view="settings"]')
        page6.wait_for_selector('#segKeyHint button[data-k="1"]')
        page6.click('#segKeyHint button[data-k="1"]')   # 复原，别把开关留在关的状态
        page6.close()

        # ---- 第二十七轮（深度逻辑）定向回归 ----

        # K3 随机一词（一百五十节修掉 sessionStorage 粘滞后的口径）：
        #   ① 面板文案是「随机一词」（不再是「每日一词 · 日期」）；
        #   ② 同一次页面加载里切页再回来，词不变（抽签锚在模块加载，
        #     会话内 renderView 重渲染不重抽——这就是「同一次访问里稳定」）；
        #   ③ 刷新（重新加载页面）必须重抽——「刷新/重新访问就更新一个新的」。
        #     随机撞上同一个词的概率是 1/1938，单次刷新判不出「换没换」；
        #     连刷 5 次若抽签没重置，5 次必然全部同词（旧缺陷的确定性特征），
        #     正确实现下 5 次全同的概率是 1938^-4 ≈ 忽略不计。
        page8 = ctx.new_page()
        page8.set_default_navigation_timeout(90000)
        page8.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page8.goto(base + "#home", wait_until="load")
        page8.wait_for_selector('#wodDetail')
        hint8 = page8.evaluate("document.querySelector('.rand-word .phon-hint').textContent")
        ok("home panel is labelled 随机一词 (not 每日一词)",
           "随机一词" in hint8 and "每日一词" not in hint8, hint8.strip()[:30])
        word8 = page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()")
        page8.click('.nav-item[data-view="browse"]')
        page8.wait_for_selector('#browseTable')
        page8.click('.nav-item[data-view="home"]')
        page8.wait_for_selector('#wodDetail')
        word8_back = page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()")
        ok("navigating away and back keeps the same random word",
           word8_back == word8, f"{word8!r} -> {word8_back!r}")
        reload_words = [word8_back]
        for _ in range(5):
            page8.reload(wait_until="load")
            page8.wait_for_selector('#wodDetail')
            reload_words.append(page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()"))
        ok("a page reload redraws the random word (5 reloads not all identical)",
           len(set(reload_words)) >= 2,
           " ".join(reload_words[:6]))

        # K3b「随机一词」面板的手动刷新按钮（用户直令：卡片里加一个刷新按钮，
        #      手动更新一个词汇）：
        #   ① 面板头部有一个可聚焦、有可访问名的刷新按钮；
        #   ② 点它（或键盘 Enter）必须换出一个新词，且详情编号同步更新；
        #   ③ 连续点多次仍可继续点（重画后按钮没被吃掉）；
        #   ④ 重画后的版式与初始一致（词 + 释义 + 例句区都在）。
        page8.click('.nav-item[data-view="home"]')
        page8.wait_for_selector('#wodRefresh')
        rf_box = page8.locator('#wodRefresh').bounding_box()
        ok("随机一词面板有刷新按钮（可见且目标尺寸 ≥24px）",
           page8.locator('#wodRefresh').is_visible() and rf_box
           and rf_box['width'] >= 24 and rf_box['height'] >= 24,
           str(rf_box))
        ok("刷新按钮有可访问名",
           bool(page8.locator('#wodRefresh').get_attribute('aria-label')),
           page8.locator('#wodRefresh').get_attribute('aria-label'))
        w_before = page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()")
        d_before = page8.locator('#wodDetail').text_content()
        page8.click('#wodRefresh')
        page8.wait_for_timeout(200)
        w_after = page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()")
        d_after = page8.locator('#wodDetail').text_content()
        ok("点刷新换出新的词", w_before != w_after, "%s -> %s" % (w_before, w_after))
        ok("刷新后详情编号同步更新", d_before != d_after, "%s -> %s" % (d_before, d_after))
        # 连续点：重画后按钮必须还在（否则只能刷新一次就成死键）
        seq = [w_after]
        for _ in range(5):
            page8.click('#wodRefresh')
            page8.wait_for_timeout(120)
            seq.append(page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()"))
        ok("刷新按钮可连续点击并持续换词",
           page8.locator('#wodRefresh').count() == 1 and len(set(seq)) >= 2,
           " ".join(seq))
        ok("刷新后例句区仍在（版式不漂）", page8.locator('.rand-word-ex').count() == 1)
        # 键盘可达：聚焦后 Enter 也能刷新
        page8.evaluate("document.querySelector('#wodRefresh').focus()")
        k_before = page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()")
        page8.keyboard.press('Enter')
        page8.wait_for_timeout(200)
        k_after = page8.evaluate("document.querySelector('.rand-word .w').textContent.trim()")
        ok("刷新按钮可用键盘 Enter 触发", k_before != k_after, "%s -> %s" % (k_before, k_after))

        # K1 测验做一半误点导航再回来：会话必须原样续上（此前一律清零，题目和得分全丢）
        page8.click('.nav-item[data-view="study"]'); page8.click('#studyModeSeg button[data-m="quiz"]')
        page8.wait_for_selector('#startQuiz')
        page8.click('#startQuiz')
        page8.wait_for_selector('.quiz-opt')
        page8.click('.quiz-opt')            # 作答第 1 题（对错都算已答）
        page8.wait_for_selector('#qNext')
        page8.click('#qNext')
        page8.wait_for_selector('.quiz-opt')
        page8.click('.nav-item[data-view="browse"]')   # 误点离开
        page8.wait_for_selector('#browseTable')
        page8.click('.nav-item[data-view="study"]')     # 回来：测验会话活着 ⇒ 直接续答题页（被测行为）
        page8.wait_for_selector('.quiz-stage')
        head = page8.evaluate("document.querySelector('.quiz-q-head').textContent")
        qno = int(re.search(r"第\s*(\d+)", head).group(1))
        ok("quiz session survives an accidental navigation", qno == 2 and "得分" in head, head.strip()[:60])

        # K1b（第四十九轮）反馈态误点导航再回来：必须原样恢复反馈，绝不允许重答二次计分
        def _prog_nums():
            # save() 有 120ms 防抖：读存储前必须等冲刷，否则读到旧值（历轮竞态教训）
            page8.wait_for_timeout(300)
            p = page8.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')).progress)||{}")
            s = c = 0
            for v in p.values():
                s += v.get("seen", 0); c += v.get("correct", 0)
            return s, c
        seen0, corr0 = _prog_nums()
        page8.wait_for_selector('.quiz-opt')
        page8.click('.quiz-opt')                       # 作答第 2 题，反馈已显示（未点下一题）
        page8.wait_for_selector('#qNext')
        score_after = page8.evaluate("document.getElementById('qScore').textContent")
        # 快照重建断言的「离开前基准」：选项集合与 correct/wrong 标记位置
        _opt_js = "[...document.querySelectorAll('.quiz-opt')].map(b=>b.dataset.text).join('|')"
        _mark_js = ("({correct:[...document.querySelectorAll('.quiz-opt.correct')].map(b=>b.dataset.text).join('|'),"
                    "wrong:[...document.querySelectorAll('.quiz-opt.wrong')].map(b=>b.dataset.text).join('|')})")
        pre_opts, pre_marks = page8.evaluate(_opt_js), page8.evaluate(_mark_js)
        seen1, corr1 = _prog_nums()                    # 记账应恰好 +1 seen
        page8.click('.nav-item[data-view="browse"]')   # 反馈没看就误点离开
        page8.wait_for_selector('#browseTable')
        page8.click('.nav-item[data-view="study"]')     # 回来：反馈态续上（被测行为）
        page8.wait_for_selector('.quiz-stage')
        snap = page8.evaluate("""({score:document.getElementById('qScore').textContent,
            fb:document.querySelector('#qFb').classList.contains('show'),
            optsDisabled:[...document.querySelectorAll('.quiz-opt')].every(b=>b.disabled)})""")
        ok("answered question resumes as feedback state (not a re-answerable fresh question)",
           snap["fb"] and snap["optsDisabled"] and snap["score"] == score_after, str(snap))
        head2 = page8.evaluate("document.querySelector('.quiz-q-head').textContent")
        ok("resumed feedback stays on the same question number", "第 2" in head2, head2.strip()[:40])
        post_opts, post_marks = page8.evaluate(_opt_js), page8.evaluate(_mark_js)
        ok("resumed feedback rebuilds the exact option set (distractors not re-rolled)",
           post_opts == pre_opts and post_marks == pre_marks,
           f"pre={str(pre_marks)[:70]} post={str(post_marks)[:70]}")
        seen2, corr2 = _prog_nums()                    # 内置 300ms 等待也给了二次计分发作的时间
        ok("resuming a feedback-state question does not double-count progress",
           (seen2, corr2) == (seen1, corr1), f"after {seen2}/{corr2} want {seen1}/{corr1}")
        page8.click('.quiz-q-head')                    # 焦点还握着导航钮——空格会被 onAct 让位原生激活（浏览器惯例，非缺陷），先点中性区让出焦点
        page8.keyboard.press("Space")                  # 此后空格应走「下一题」全局分支
        page8.wait_for_selector('.quiz-opt:not([disabled])')
        seen3, corr3 = _prog_nums()
        ok("space on resumed feedback advances to a fresh question", seen3 == seen2, f"seen {seen2}->{seen3}")
        page8.click('.nav-item[data-view="browse"]'); page8.wait_for_selector('#browseTable')
        page8.click('.nav-item[data-view="study"]'); page8.wait_for_selector('.quiz-stage')
        fresh = page8.evaluate("""({optsDisabled:[...document.querySelectorAll('.quiz-opt')].every(b=>b.disabled),
            fb:document.querySelector('#qFb').classList.contains('show')})""")
        ok("fresh question is answerable again after the restored one was passed",
           not fresh["optsDisabled"] and not fresh["fb"], str(fresh))
        page8.click('#qQuit')
        page8.wait_for_selector('.quiz-setup')
        ok("quitting still returns to quiz setup", page8.evaluate("!!document.querySelector('#startQuiz')"))

        # K1c（第四十九轮）拼写题鼠标路径：点「核对答案」后钮必须禁用让出键盘，
        # 否则焦点残留在已空转的钮上，Space/Enter 被 onAct 门控吃掉——键盘死锁
        page8.click('#qModes .chip[data-m="spell"]')
        page8.click('#startQuiz')
        page8.wait_for_selector('#spellInput')
        page8.fill('#spellInput', 'zzzzwrong')
        page8.click('#spellCheck')
        page8.wait_for_selector('#qFb.show')
        spell_st = page8.evaluate("""({chkDisabled:document.getElementById('spellCheck').disabled,
            inpDisabled:document.getElementById('spellInput').disabled,
            focusOnBody:document.activeElement===document.body,
            headNext:document.getElementById('qSkip').textContent.trim(),
            bodyNext:document.getElementById('qSkip2').textContent.trim()})""")
        ok("spell check button disables itself on click (no keyboard hostage)",
           spell_st["chkDisabled"] and spell_st["inpDisabled"], str(spell_st))
        # 拼写题的两颗「跳过」走同一个 skip()：作答后都已是翻页，
        # 页首与卡内的标签必须一起变成「下一题」，不能一颗仍写「跳过」。
        ok("both spell-mode skip buttons relabel to next after answering",
           "下一题" in spell_st["headNext"] and "下一题" in spell_st["bodyNext"],
           str({k: spell_st[k] for k in ("headNext", "bodyNext")}))
        # 钮 disabled 后 Chromium 把焦点移回 body 是异步的：立刻按 Space 会撞上半途态
        # （activeElement 仍是刚禁用的钮→onAct 门控让路→空格被吞，30s 超时，394ddc 移交的 flake）。
        # 先有界等待焦点归位；极端慢机等待超时则按既有口径点中性区强制让出焦点。
        # 焦点归位有两种结局（工装·第十一轮加了焦点保全）：旧行为＝回到 body，
        # 新行为＝交回「下一题」钮 #qNext（此时空格由按钮原生激活触发，同样翻页）。
        try:
            page8.wait_for_function(
                "document.activeElement === document.body || document.activeElement.id === 'qNext'",
                timeout=3000)
        except Exception:
            page8.click('.quiz-q-head')
        page8.keyboard.press("Space")          # 核对钮禁用后焦点归位 → 空格走「下一题」
        page8.wait_for_selector('#spellInput:not([disabled])')
        ok("space advances out of a mouse-checked spell question",
           page8.evaluate("!document.querySelector('#qFb').classList.contains('show')"))
        page8.click('#qQuit')
        page8.wait_for_selector('.quiz-setup')
        page8.wait_for_timeout(300)   # 冲刷拼写答题的 120ms 防抖 save——K2 的 days_before 快照必须读到已落盘的活动数

        # K2 闪卡撤销按「评分当天」的日期键回退 days（跨午夜时 todayStr 已变，不能再按撤销时写回）
        tk = datetime.date.today().isoformat()
        days_before = page8.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')).days)||{}")
        page8.click('.nav-item[data-view="study"]'); page8.click('#studyModeSeg button[data-m="flashcards"]')
        page8.wait_for_selector('.deck-opt[data-s="all"]')
        page8.click('.deck-opt[data-s="all"]')
        page8.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page8.wait_for_selector('.flip-card')
        page8.click('.fc-word')
        page8.wait_for_timeout(500)
        page8.keyboard.press("3")           # 认识 → 计入当天活动
        page8.wait_for_timeout(400)         # save() 120ms 防抖
        days_mid = page8.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')).days)||{}")
        page8.click('#fcUndo')
        page8.wait_for_timeout(400)
        days_after = page8.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')).days)||{}")
        ok("grading bumps today's activity; undo rolls it back on the same date key",
           int(days_mid.get(tk, 0)) == int(days_before.get(tk, 0)) + 1
           and int(days_after.get(tk, 0)) == int(days_before.get(tk, 0))
           and set(days_after) - set(days_before) <= {tk},
           f"before={days_before.get(tk, 0)} mid={days_mid.get(tk, 0)} after={days_after.get(tk, 0)}")
        page8.click('#fcQuit')
        page8.close()

        # ---- 第二十八轮（排序可达性）定向回归 ----
        # 种两个已知进度（用 % 格式化 + 生效自检，勿写 {{ }}）：状态列排序结果才可确定验证
        n_a = page.evaluate("([...window.WL_WORDS].sort((a,b)=>a.num-b.num))[5].num")
        n_b = page.evaluate("([...window.WL_WORDS].sort((a,b)=>a.num-b.num))[10].num")
        page9 = ctx.new_page()
        page9.set_default_navigation_timeout(90000)
        page9.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page9.add_init_script(
            "try{const s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            "s.progress={%d:{lv:5,due:0,seen:2,correct:2,wrong:0,last:1},%d:{lv:1,due:0,seen:1,correct:0,wrong:1,last:1}};"
            "localStorage.setItem('wl_state_v1',JSON.stringify(s));}catch(e){}" % (n_a, n_b))
        page9.goto(base + "#browse", wait_until="load")
        pk = page9.evaluate("Object.keys(JSON.parse(localStorage.getItem('wl_state_v1')).progress).length")
        ok("round-28 seed applied (exactly two progress rows)", pk == 2, f"keys={pk}")
        pc = page9.evaluate("document.querySelector('.pager button[aria-current=\"page\"]')?.textContent.trim()")
        ok("pager marks the current page for screen readers", pc == "1", f"cur={pc}")

        def rows9():
            return page9.evaluate("[...document.querySelectorAll('.word-table tbody tr')].map(r=>+r.dataset.num)")
        def expect9(asc):
            return page9.evaluate(
                "((asc) => {const P=JSON.parse(localStorage.getItem('wl_state_v1')).progress||{};"
                "const lv=n=>P[n]?P[n].lv:-1;"
                "const ws=[...window.WL_WORDS].sort((a,b)=>a.num-b.num);"
                "ws.sort((a,b)=>asc ? lv(a.num)-lv(b.num) : lv(b.num)-lv(a.num));"
                "return ws.slice(0,50).map(w=>w.num);})(%s)" % ("true" if asc else "false"))
        page9.click('.th-sort[data-k="lv"]')
        page9.wait_for_timeout(250)
        aria1 = page9.evaluate("document.querySelector('th[aria-sort]:not([aria-sort=\"none\"])').getAttribute('aria-sort')")
        ok("status sort asc reorders rows exactly and is announced", aria1 == "ascending" and rows9() == expect9(True),
           f"aria={aria1} first5={rows9()[:5]}")
        page9.click('.th-sort[data-k="lv"]')
        page9.wait_for_timeout(250)
        aria2 = page9.evaluate("[...document.querySelectorAll('th[aria-sort]')].map(t=>t.getAttribute('aria-sort')).join()")
        ok("status sort toggles to descending", "descending" in aria2 and rows9() == expect9(False),
           f"aria=[{aria2}] first3={rows9()[:3]}")
        # 键盘用户：聚焦排序钮按 Enter 必须能切换排序（旧裸 th 根本不可聚焦）
        page9.focus('.th-sort[data-k="word"]')
        page9.keyboard.press("Enter")
        page9.wait_for_timeout(250)
        word_sorted = page9.evaluate("""(() => {
          const th=[...document.querySelectorAll('th')].find(t=>t.querySelector('.th-sort[data-k="word"]'));
          const first=document.querySelector('.word-table tbody tr .wt-word').textContent.trim();
          return {sort: th.getAttribute('aria-sort'), first};})()""")
        alpha_first = page.evaluate("[...window.WL_WORDS].map(w=>w.word).sort((a,b)=>a.localeCompare(b))[0]")
        ok("Enter on a focused sort button activates sorting (keyboard reachable)",
           word_sorted["sort"] == "ascending" and word_sorted["first"] == alpha_first, str(word_sorted))
        page9.close()

        # ---- 第 29 轮定向回归：损坏 settings 不再崩设置页 ----
        page10 = ctx.new_page()
        page10.set_default_navigation_timeout(90000)
        page10.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page10.add_init_script(
            "try{const s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
            "s.settings={rate:'fast',goal:'many',theme:'halloween',showKeyHint:1,autoSpeak:'x'};"
            "localStorage.setItem('wl_state_v1',JSON.stringify(s));"
            # 另写一个应用不碰的标记键：应用启动时会把**归一后**的存档写回去
            # （顶栏访问计数要落盘 ⇒ 载入即 save），原值 'fast' 会被就地改成 0.95，
            # 拿存档本身自检「种子是否生效」已不成立 ⇒ 用独立标记键自检。
            "localStorage.setItem('__seed_marker','fast');}catch(e){}")
        page10.goto(base + "#settings", wait_until="load")
        page10.wait_for_timeout(300)
        # 种子生效自检须在 goto 之后——about:blank 里读 localStorage 会 SecurityError
        seeded = page10.evaluate("() => localStorage.getItem('__seed_marker')")
        ok("round-29 corrupt settings seeded", seeded == "fast", repr(seeded))
        # 未钳制时 rate.toFixed 抛 TypeError，设置页只剩半截骨架
        sv = page10.evaluate("""(() => {
          const el=document.getElementById('rateVal');
          return {rate: el && el.textContent.trim(),
                  goal: document.querySelector('#goalInput')?.value,
                  themeOn: [...document.querySelectorAll('#segTheme button.on')].map(b=>b.textContent.trim()).join(),
                  hintRow: !!document.querySelector('.fc-hint') || document.body.innerText.includes('按 1')};})()""")
        ok("settings page survives garbage values (no render crash)",
           sv["rate"] == "0.95" and sv["goal"] == "30", str(sv))
        # 兜底主题应回落到应用自己声明的默认值（默认深色），
        # 不在此钉死字面量——改默认值时这里跟着走。
        _app_src = open(os.path.join(ROOT, "js", "app.js"), encoding="utf-8").read()
        _def_theme = (re.search(r"theme:\s*'(light|dark)'", _app_src) or [None, None])[1]
        _def_label = {"light": "浅色", "dark": "深色"}.get(_def_theme)
        ok("unknown theme falls back to the default segment",
           bool(_def_label) and sv["themeOn"] == _def_label,
           f'{sv["themeOn"]} def={_def_theme}')
        # 首页环形进度：goal 为 NaN 时 stroke-dashoffset 会变成 "NaN"
        page10.click('.nav-item[data-view="home"]')
        page10.wait_for_timeout(250)
        ring = page10.evaluate("document.querySelector('.ring circle[stroke-dasharray]')?.getAttribute('stroke-dashoffset') || 'MISSING'")
        ok("home goal ring never emits NaN into SVG geometry",
           ring != "MISSING" and "NaN" not in str(ring), str(ring))
        page10.close()

        # ---- 第 31 轮定向回归：空范围提示不得跨会话残留 ----
        # 旧行为：点空牌组留下「○○当前没有可复习的单词」→ 经首页 CTA（pendingDeck 路径）
        # 开成会话再退出，设置页仍复述这条已经过期的提示（chip 路径当时就清了，独漏 pendingDeck）。
        page11 = ctx.new_page()
        page11.set_default_navigation_timeout(90000)
        page11.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page11.add_init_script("try{localStorage.clear();}catch(e){}")   # 全清 = 全新默认档（init 早于 app.js，绕开 beforeunload 回写）
        page11.goto(base + "#cards", wait_until="load")
        page11.wait_for_selector('.chip.deck-opt[data-s="fav"]')
        # 一百九十四轮起点空牌组**不再**当场开局（两步流），原「内联提示」路径下线：
        # 空范围的表现改为「本次」行摘要说明 + 确认按钮禁用。
        page11.click('.chip.deck-opt[data-s="fav"]')
        page11.wait_for_timeout(250)
        summ = page11.evaluate("document.querySelector('#fcSummary')?.innerText || ''")
        btn_dis = page11.evaluate("document.querySelector('#fcStart')?.disabled")
        ok("empty deck click explains itself in the summary and disables the start",
           "收藏" in summ and btn_dis is True, f"summary={summ[:50]} disabled={btn_dis}")
        page11.click('.nav-item[data-view="home"]')
        page11.wait_for_selector('#goReview')
        page11.click('#goReview')                                        # 全新档 CTA = 「从新词开始」，pendingDeck 路径
        page11.wait_for_selector('#flipCard')
        page11.click('#fcQuit')
        page11.wait_for_timeout(250)
        stale = page11.evaluate("[...document.querySelectorAll('.empty-inline')].map(e=>e.innerText).join('|')")
        ok("a session started via the home CTA clears the earlier empty-range notice",
           "收藏" not in stale, stale[:80])
        page11.close()

        # ---- 第 51 轮定向回归：例句挖空 / 滑动手势开关 / 底部抽屉 / 例句搜索 / 收藏导出 ----
        page12 = ctx.new_page()
        page12.set_default_navigation_timeout(90000)
        page12.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page12.add_init_script("try{localStorage.clear();}catch(e){}")
        page12.goto(base + "#quiz", wait_until="load")

        # C1 例句挖空：整卷作答，绝大多数题应真出挖空（原形不在例句中的少数词回退看词选义，
        # 具体回退数随数据轮浮动，故只断言「几乎全挖空」而不钉死个数）
        page12.click('.chip[data-m="cloze"]')
        page12.wait_for_timeout(150)
        page12.click('#startQuiz')
        page12.wait_for_selector('.quiz-opt')
        total = page12.evaluate("window.WL_DEBUG ? window.WL_DEBUG.quiz.queue.length : 0")
        cloze_n = 0
        for qi in range(total):
            if page12.locator('.cloze-blank').count():
                cloze_n += 1
            page12.click('.quiz-opt[data-ok="true"]')
            page12.wait_for_selector('.quiz-feedback.show')
            page12.click('#qNext')
            page12.wait_for_timeout(120)
        page12.wait_for_selector('.quiz-result')
        ok("cloze quiz renders mostly cloze sentences", cloze_n >= total - 3,
           f"{cloze_n}/{total}")
        hist = page12.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).quizHist.slice(-1)[0]")
        ok("cloze run scores every correct answer once", hist["score"] == hist["total"], str(hist))

        # C2 滑动手势开关：走 UI 关闭 → 新页（共享 localStorage）复验持久 → 复原。
        # 不能用 page12.reload()：page12 挂了每导航清档的 init script，重载会把刚存的值洗掉
        page12.goto(base + "#settings", wait_until="load")
        page12.wait_for_selector('#segSwipe button[data-k="0"]')
        page12.click('#segSwipe button[data-k="0"]')
        page12.wait_for_timeout(250)
        sw_saved = page12.evaluate("JSON.parse(localStorage.getItem('wl_state_v1')).settings.swipeGrade")
        ok("swipe switch persists off to localStorage", sw_saved is False, str(sw_saved))
        page12b = ctx.new_page()
        page12b.set_default_navigation_timeout(90000)
        page12b.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page12b.goto(base + "#settings", wait_until="load")
        page12b.wait_for_selector('#segSwipe button.on')
        sw_on = page12b.evaluate("document.querySelector('#segSwipe button.on').dataset.k")
        ok("swipe switch renders as off on a fresh load", sw_on == "0", str(sw_on))
        page12b.click('#segSwipe button[data-k="1"]')
        page12b.wait_for_timeout(200)
        page12b.close()
        page12.click('#segSwipe button[data-k="1"]')   # 同步 page12 内存态，防 beforeunload 回写脏值
        page12.wait_for_timeout(200)

        # C3 例句搜索：仅例句命中的关键词在搜索建议里带「例」徽标
        page12.goto(base + "#home", wait_until="load")
        page12.keyboard.press("/")
        page12.wait_for_timeout(200)
        # 取词规则：这个关键词在**全库**的词形与释义里都不出现，且只在**一个**词的
        # 例句里出现 ⇒ 搜它必定只有一条结果、且是「仅例句命中」。
        # （旧版只在**同一个词**里检查词形与释义，撞上了「research」这种本身就在
        #   词库里的词：搜索改成按命中强度排序后，精确命中的词排到最前，
        #   仅例句命中的那条被挤出前 12 条，断言便落空 ——
        #   守卫要盯的是「徽标挂没挂」，不是「排序」。）
        tok = pick_example_only_token()
        page12.fill("#searchInput", tok)
        page12.wait_for_timeout(300)
        sr_ex = page12.evaluate("""(() => {
          const it = [...document.querySelectorAll('#searchResults .sr-item')];
          const hit = it.find(el => el.querySelector('.sr-ex'));
          return hit ? hit.textContent : null; })()""")
        ok("example-only search hit carries the 「例」 badge", bool(sr_ex), str(tok))
        page12.keyboard.press("Escape")

        # C3b 搜索排序：词库里有的词，精确命中必须排第一条。
        #    旧实现按词条原号取前 12 条 ⇒ 搜编号靠后的词（这里取**编号最大**的那个）
        #    会被前面几百条「例句里也含它」的词整个挤没，用户搜的词根本看不见。
        page12.goto(base + "#home", wait_until="load")
        page12.keyboard.press("/")
        page12.wait_for_timeout(200)
        probe = page12.evaluate("""(() => {
          const ws = window.WL_WORDS || [];
          let best = null;
          for (const w of ws) if (!best || w.num > best.num) best = w;
          return best ? best.word : null; })()""")
        page12.fill("#searchInput", probe)
        page12.wait_for_timeout(300)
        first_sr = page12.evaluate("""(() => {
          const el = document.querySelector('#searchResults .sr-item');
          const w = el && el.querySelector('.w');
          return w ? w.textContent.trim() : null; })()""")
        ok("全局搜索：词库里有的词，精确命中排第一条（不再被前几百条挤掉）",
           bool(probe) and (first_sr or "").lower() == probe.lower(),
           "%s → %s" % (probe, first_sr))
        page12.keyboard.press("Escape")

        # C3c 浮层放不下的结果有出口：一条「在词库中查看全部」直通词库页
        page12.keyboard.press("/")
        page12.wait_for_timeout(200)
        page12.fill("#searchInput", "a")     # 命中极多 ⇒ 必然超过浮层的 12 条
        page12.wait_for_timeout(300)
        more_txt = page12.evaluate("""(() => {
          const b = document.querySelector('#btnSearchAll');
          return b ? b.textContent.trim() : null; })()""")
        ok("搜索结果超出一条时给出「去词库看全部」的入口",
           bool(more_txt) and more_txt.find("词库") >= 0, str(more_txt))
        if more_txt:
            page12.click("#btnSearchAll")
            page12.wait_for_timeout(500)
            bq = page12.input_value("#bq")
            ok("「去词库看全部」把关键词带进词库页", bq.strip() == "a", bq)
        page12.keyboard.press("Escape")

        # C4 收藏导出钮：收藏后出现，未收藏时不存在
        page12.goto(base + "#browse", wait_until="load")
        page12.wait_for_selector('.wt-open')
        page12.click('tr .mini-btn[data-act="fav"]')
        page12.goto(base + "#fav", wait_until="load")
        page12.wait_for_timeout(250)
        ok("favourites view offers text export once non-empty",
           page12.locator('#favExport').count() == 1)

        # C5 窄屏底部抽屉：弹窗贴底、上方 18px 圆角、sheet-up 进场动画
        page12.set_viewport_size({"width": 400, "height": 800})
        page12.goto(base + "#browse", wait_until="load")
        page12.wait_for_selector('.wt-open')
        page12.click('.wt-open')
        page12.wait_for_selector('.modal-card')
        page12.wait_for_timeout(450)   # sheet-up 动画 0.26s：不等待会量到 translateY(100%) 半途位置
        box = page12.evaluate("""(() => { const m = document.querySelector('.modal-card'),
          r = m.getBoundingClientRect(), cs = getComputedStyle(m);
          return {bottom: r.bottom, vh: innerHeight, tl: cs.borderTopLeftRadius, tr: cs.borderTopRightRadius,
                  bl: cs.borderBottomLeftRadius, anim: cs.animationName}; })()""")
        ok("word modal docks as a bottom sheet on narrow screens",
           abs(box["bottom"] - box["vh"]) <= 1 and box["tl"] == "18px" and box["bl"] == "0px",
           str(box))
        ok("bottom sheet slides up with its own keyframes", box["anim"] == "sheet-up", str(box["anim"]))
        page12.keyboard.press("Escape")
        page12.set_viewport_size({"width": 1280, "height": 900})

        # C6 热力图周对齐：起始补位存在、列内每格同宽、月份标可读
        page12.goto(base + "#stats", wait_until="load")
        heat = page12.evaluate("""(() => {
          const pads = document.querySelectorAll('.heat-pad').length;
          const ms = [...document.querySelectorAll('.heat.ms')];
          const hf = new Date(); hf.setDate(hf.getDate() - 119);
          const first = document.querySelector('.heat-wrap .heat'), fp = document.querySelector('.heat-pad');
          const r1 = first.getBoundingClientRect(), r2 = fp ? fp.getBoundingClientRect() : r1;
          return {pads, exp: (hf.getDay() + 6) % 7, ms: ms.length,
                  mtxt: ms.map(e => e.getAttribute('data-m')), hr: ms.map(e => e.style.getPropertyValue('--hr')),
                  sameW: Math.abs(r1.width - r2.width) < 0.5}; })()""")
        ok("heatmap pads align the first row to Monday", heat["pads"] == heat["exp"], str(heat["pads"]))
        ok("heatmap month tiles carry labels and row vars",
           heat["ms"] >= 4 and all(re.match(r'^\d{1,2}月$', t) for t in heat["mtxt"])
           and all(h in "0123456" for h in heat["hr"]), str(heat))
        ok("heatmap pad and day cells share tile geometry", heat["sameW"], str(heat["sameW"]))

        # C7 五十四轮：滑动手势真实行为——注入 pointerType:'touch' 的 PointerEvent 复刻
        # 手指轨迹（监听器只认 pointerType，合成事件即可），补上第 51 轮只测了开关没测手势的缺口：
        # 横向过阈评分 / 纵向占优斜拖不评分（滚页） / 第二指不得劫持在途滑动 / 开关关闭全程惰性
        page12.goto(base + "#cards", wait_until="load")
        page12.wait_for_selector('.chip.deck-opt[data-s="new"]')
        page12.click('.chip.deck-opt[data-s="new"]')
        page12.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page12.wait_for_selector('#flipCard')

        def swipe_gesture(steps):
            # steps: [[事件类型, pointerId, dx, dy], ...]，坐标取卡面中心为原点
            page12.evaluate("""(steps) => {
              const el = document.getElementById('flipCard');
              const r = el.getBoundingClientRect();
              const x0 = r.left + r.width / 2, y0 = r.top + r.height / 2;
              for (const [type, id, dx, dy] of steps)
                el.dispatchEvent(new PointerEvent(type, {pointerType: 'touch', pointerId: id,
                  bubbles: true, cancelable: true, clientX: x0 + dx, clientY: y0 + dy}));
            }""", steps)

        def stage_sig():
            return page12.evaluate("""(() => { const c = document.getElementById('flipCard');
              return {word: document.querySelector('.fc-word')?.textContent,
                      good: +document.querySelector('.fcss-item.good b')?.textContent,
                      flipped: c?.classList.contains('flipped') || false,
                      transform: c?.style.transform || '' }; })()""")

        page12.keyboard.press(" ")     # 翻面后才允许滑动
        page12.wait_for_timeout(550)
        s0 = stage_sig()
        swipe_gesture([["pointerdown", 1, 0, 0], ["pointermove", 1, 80, 0], ["pointerup", 1, 80, 0]])
        page12.wait_for_timeout(250)
        s1 = stage_sig()
        ok("horizontal touch swipe past threshold grades as known",
           s1["good"] == s0["good"] + 1 and s1["word"] != s0["word"], f"{s0['word']}→{s1['word']}")

        page12.keyboard.press(" ")
        page12.wait_for_timeout(550)
        s2 = stage_sig()
        swipe_gesture([["pointerdown", 1, 0, 0], ["pointermove", 1, 70, 140], ["pointerup", 1, 70, 140]])
        page12.wait_for_timeout(250)
        s3 = stage_sig()
        ok("vertical-dominant diagonal drag scrolls instead of grading",
           s3["good"] == s2["good"] and s3["word"] == s2["word"] and s3["flipped"]
           and s3["transform"] == "", str(s3))

        swipe_gesture([["pointerdown", 1, 0, 0], ["pointermove", 1, 20, 0],
                       ["pointerdown", 2, 0, 0], ["pointermove", 2, 200, 0], ["pointerup", 2, 200, 0],
                       ["pointerup", 1, 20, 0]])
        page12.wait_for_timeout(250)
        s5 = stage_sig()
        ok("a second finger neither hijacks the tracked swipe nor grades",
           s5["good"] == s2["good"] and s5["word"] == s2["word"] and s5["flipped"], str(s5))

        # 先退出会话：hash 导航是 same-document，JS 状态里的 fc.session 不会自己清零，
        # 不 quit 的话再进 #cards 会直接 renderStage，等不到范围 chips
        page12.click('#fcQuit')
        page12.wait_for_selector('.chip.deck-opt[data-s="new"]')

        # 手势开关关闭时（走设置 UI）横向快滑也应完全惰性——bindSwipe 根本没挂监听
        page12.goto(base + "#settings", wait_until="load")
        page12.wait_for_selector('#segSwipe button[data-k="0"]')
        page12.click('#segSwipe button[data-k="0"]')
        page12.wait_for_timeout(250)
        page12.goto(base + "#cards", wait_until="load")
        page12.wait_for_selector('.chip.deck-opt[data-s="new"]')
        page12.click('.chip.deck-opt[data-s="new"]')
        page12.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page12.wait_for_selector('#flipCard')
        page12.keyboard.press(" ")
        page12.wait_for_timeout(550)
        s6 = stage_sig()
        swipe_gesture([["pointerdown", 1, 0, 0], ["pointermove", 1, 90, 0], ["pointerup", 1, 90, 0]])
        page12.wait_for_timeout(250)
        s7 = stage_sig()
        ok("swipe grading stays inert when the switch is off",
           s7["good"] == s6["good"] and s7["word"] == s6["word"] and s7["flipped"], str(s7))
        page12.goto(base + "#settings", wait_until="load")
        page12.wait_for_selector('#segSwipe button[data-k="1"]')
        page12.click('#segSwipe button[data-k="1"]')
        page12.wait_for_timeout(250)
        page12.close()

        # ---- 册四十六轮回归：作答后点「跳过」不重复计数 / 收藏不继承关键词 / 目标 Esc 取消 ----
        page13 = ctx.new_page()
        page13.goto(base + "#quiz", wait_until="load")
        page13.wait_for_selector(".quiz-setup")
        page13.click(".chip[data-m='en2zh']")
        page13.click("#startQuiz")
        page13.wait_for_selector(".quiz-card")
        # 题数从题头现算，不钉字面量（队列长度随范围/设置而变）
        qn46 = page13.evaluate("(() => { const m = /第\\s*\\d+\\s*\\/\\s*(\\d+)\\s*题/.exec(document.querySelector('.quiz-q-head')?.textContent || ''); return m ? +m[1] : 0; })()")
        page13.click(".quiz-opt")                     # 作答第 1 题（对错均可）
        page13.wait_for_selector("#qFb.show")
        page13.click("#qSkip")                        # 反馈态点跳过 = 翻页，不得计入 skipped
        page13.wait_for_timeout(300)
        for _ in range(30):
            if page13.locator(".quiz-result").count(): break
            if page13.locator("#qSkip").count():
                page13.click("#qSkip"); page13.wait_for_timeout(120)
        page13.wait_for_timeout(300)
        h46 = page13.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')||'{}').quizHist||[]).slice(-1)[0]||{}")
        ok("answered question is not double-counted as skipped",
           qn46 > 1 and h46.get("skipped") == qn46 - 1 and h46.get("total") == 1,
           f"queue={qn46} total={h46.get('total')} skipped={h46.get('skipped')}")
        # 选择器写成「挂载视图内唯一的搜索框」而非具体 id：
        # 词库浏览与收藏两视图共用 id="bq"（重名 id 是另一轮在修的 P2 项），
        # 改名不应让本条断言假红。限定 #main 以排除全局搜索浮层里的输入框。
        page13.goto(base + "#browse", wait_until="load")
        page13.wait_for_selector('#main input[type="search"]')
        page13.fill('#main input[type="search"]', "zzzz")
        page13.wait_for_timeout(400)
        page13.click('.nav-item[data-view="fav"]')
        page13.wait_for_timeout(500)
        q46 = page13.evaluate("(() => { const i = document.querySelector('#main input[type=\"search\"]'); return i ? i.value : ''; })()")
        ok("favourites view clears the leftover keyword filter", q46 == "", f"q={q46!r}")
        page13.goto(base + "#home", wait_until="load")
        page13.wait_for_selector("#goalEdit")
        g46a = page13.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')||'{}').settings||{}).goal")
        page13.click("#goalEdit")
        page13.wait_for_timeout(200)
        page13.fill(".goal-edit-input", "77")
        page13.keyboard.press("Escape")
        page13.wait_for_timeout(400)
        g46b = page13.evaluate("(JSON.parse(localStorage.getItem('wl_state_v1')||'{}').settings||{}).goal")
        ok("Escape cancels the daily-goal edit", g46b == g46a, f"{g46a} -> {g46b}")
        if g46b != g46a:                              # 万一回归失败，把设置改回原值，别留脏设置给后面用例
            page13.click("#goalEdit"); page13.wait_for_timeout(150)
            page13.fill(".goal-edit-input", str(g46a))
            page13.keyboard.press("Enter"); page13.wait_for_timeout(250)
        # ---- 二百零一轮：数字输入 0 的归一口径 ----
        # `+v || 30` 把合法输入 0 当 falsy 顶成默认 30，而 -5 钳到下限 5——
        # 同是越界值两种落点。统一后：0 与负数都钳到下限，只有空串/非数字落默认。
        page13.click("#goalEdit")
        page13.wait_for_timeout(150)
        page13.fill(".goal-edit-input", "0")
        page13.dispatch_event(".goal-edit-input", "blur")
        page13.wait_for_timeout(300)
        g0 = page13.evaluate("WL_DEBUG.state.settings.goal")
        ok("goal input 0 clamps to the floor (not the default)", g0 == 5, str(g0))
        page13.click("#goalEdit")
        page13.wait_for_timeout(150)
        page13.fill(".goal-edit-input", "-10")
        page13.dispatch_event(".goal-edit-input", "blur")
        page13.wait_for_timeout(300)
        gneg = page13.evaluate("WL_DEBUG.state.settings.goal")
        ok("goal input -10 clamps to the floor too", gneg == 5, str(gneg))
        page13.click("#goalEdit")
        page13.wait_for_timeout(150)
        # number input 的 fill 只接受数字；「非数字文本」这条路用 evaluate 直写 value
        page13.evaluate("(() => { const i = document.querySelector('.goal-edit-input'); i.value = 'abc'; i.dispatchEvent(new Event('blur')); })()")
        page13.wait_for_timeout(300)
        gbad = page13.evaluate("WL_DEBUG.state.settings.goal")
        ok("goal input 'abc' falls back to the default", gbad == 30, str(gbad))
        page13.goto(base + "#settings", wait_until="load")
        page13.wait_for_selector("#goalInput")
        page13.fill("#goalInput", "0")
        page13.dispatch_event("#goalInput", "change")
        page13.wait_for_timeout(300)
        gs0 = page13.evaluate("WL_DEBUG.state.settings.goal")
        ok("settings goal input 0 clamps to the floor as well", gs0 == 5, str(gs0))
        # 收尾：把目标改回 30，别让脏值影响后续用例
        page13.fill("#goalInput", "30")
        page13.dispatch_event("#goalInput", "change")
        page13.wait_for_timeout(200)
        page13.close()

        # ---- 状态卫生：脏备份不得带病进运行时 ----
        # 种子两处病灶：① 进度计数被写成字符串（统计页 reduce 会 number + "31" 拼成
        #    "031"，累计次数与正确率一起变 NaN）；② 顶层塞了 "__proto__" 注入键
        #    （Object.assign 会照单写入，把 state 的原型换成文件里的对象）。
        # 用 add_init_script 种——必须先于应用脚本执行，否则运行中改 localStorage
        # 会被应用卸载时的回写覆盖。
        page14 = ctx.new_page()
        page14.set_default_navigation_timeout(90000)
        page14.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page14.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        page14.add_init_script(
            "try{localStorage.setItem('wl_state_v1',"
            "'{\"progress\":{\"1\":{\"lv\":2,\"due\":\"x\",\"seen\":\"2\",\"correct\":\"3\",\"wrong\":\"1\","
            "\"last\":\"0\",\"__proto__\":{\"epolluted\":1},\"extra\":9}},"
            "\"__proto__\":{\"polluted\":1}}');}catch(e){}")
        page14.goto(base + "#stats", wait_until="load")
        page14.wait_for_timeout(600)
        st14 = page14.evaluate(
            "(() => { const s = window.WL_DEBUG && window.WL_DEBUG.state; if (!s) return null;"
            "const p = (s.progress || {})['1'] || {};"
            "return {types: [typeof p.correct, typeof p.seen, typeof p.wrong, typeof p.due],"
            " correct: p.correct, wrong: p.wrong, polluted: s.polluted,"
            " protoOk: Object.getPrototypeOf(s) === Object.prototype,"
            " keys: Object.keys(p).sort().join(','),"
            " entryProtoOk: Object.getPrototypeOf(p) === Object.prototype,"
            " epolluted: p.epolluted, extra: p.extra}; })()")
        ok("dirty counters in a backup are normalised to numbers",
           bool(st14) and st14["types"] == ["number"] * 4, json.dumps(st14, ensure_ascii=False))
        ok("a backup cannot inject keys through __proto__",
           bool(st14) and st14.get("polluted") is None and st14.get("protoOk") is True,
           json.dumps(st14, ensure_ascii=False))
        ok("a progress entry keeps only the six known fields",
           bool(st14) and st14.get("keys") == "correct,due,last,lv,seen,wrong",
           json.dumps(st14, ensure_ascii=False))
        ok("a progress entry cannot be proto-injected either",
           bool(st14) and st14.get("entryProtoOk") is True and st14.get("epolluted") is None
           and st14.get("extra") is None, json.dumps(st14, ensure_ascii=False))
        body14 = page14.evaluate("document.body.innerText")
        ok("stats page shows no NaN after a dirty backup", "NaN" not in body14,
           body14[body14.find("累计答题"):body14.find("累计答题") + 40] if "累计答题" in body14 else body14[:60])
        # 此夹具明确是 seen=2、correct=3、wrong=1：累计评分按 seen 显示 2，
        # 对错次数只用于正确率分母。断言按空白归一，避免排版空格造成假红。
        ok("stats page counts the normalised counters numerically",
           "累计答题/评分2次" in re.sub(r"\s+", "", body14),
           body14[body14.find("累计答题"):body14.find("累计答题") + 40] if "累计答题" in body14 else "no stats line")
        page14.close()

        # 导入路径是「重新赋值」state（state = pickState(data)）：调试钩子若取的是
        # 值快照，就会一直指向导入前的旧对象，读到的状态与运行时不符（假红/假绿）。
        # 用一次真实导入验证钩子是活引用。
        #
        # 导入件用**内存 buffer**喂给 file input，不写临时文件：snap 版 chromium
        # 有私有 /tmp 命名空间，读不到沙箱外的路径，FileReader 拿到空串 → 导入静默失败
        # （表现为 state 没变、lv 为 null），那是环境限制不是代码缺陷，不该让套件变红。
        imp_payload = json.dumps(
            {"progress": {"3": {"lv": 4, "due": 0, "seen": 1, "correct": 1, "wrong": 0, "last": 0}},
             "settings": {"theme": "auto", "goal": 30, "rate": 0.95},
             "fav": [3]}, ensure_ascii=False).encode("utf-8")
        page15 = ctx.new_page()
        page15.set_default_navigation_timeout(90000)
        page15.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page15.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        page15.goto(base + "#settings", wait_until="load")
        page15.wait_for_selector("#impFile", state="attached")   # 隐藏的 file input：等挂载而非可见
        page15.set_input_files("#impFile", files=[{"name": "backup.json",
                                                   "mimeType": "application/json",
                                                   "buffer": imp_payload}])
        # 等导入真正落地（等固定 900ms 在机器繁忙时会假红）：以 state 变为准
        try:
            page15.wait_for_function(
                "() => { const s = window.WL_DEBUG && window.WL_DEBUG.state;"
                "const p = s && s.progress && s.progress['3'];"
                "return !!(p && p.lv === 4); }", timeout=15000)
            settled15 = True
        except Exception as e:
            settled15 = False
            errors.append("import did not settle: " + str(e)[:120])
        st15 = page15.evaluate(
            "(() => { const s = window.WL_DEBUG && window.WL_DEBUG.state; if (!s) return null;"
            "const p = (s.progress || {})['3'] || null;"
            "return {lv: p ? p.lv : null, fav: (s.fav || []).length}; })()")
        ok("the debug state hook follows the state after an import",
           settled15 and bool(st15) and st15.get("lv") == 4 and st15.get("fav") == 1,
           json.dumps(st15, ensure_ascii=False))
        page15.close()

        # ================================================================
        # 界面行为修复回归（2026-11-16 工装窗）：下面每一条断言都做过
        # 「变异验证」——把 js/app.js 退回修前版本跑本套件，对应断言必须变红。
        # ================================================================
        print("== 界面行为修复回归 ==")

        # ---------- (1) 拼写填空按 Enter：出反馈卡，且不翻到下一题 ----------
        page16 = ctx.new_page()
        page16.set_default_navigation_timeout(90000)
        page16.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page16.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        try:
            page16.goto(base + "#quiz", wait_until="load")
            page16.wait_for_selector("#qModes .chip[data-m='spell']", state="attached")
            page16.click("#qModes .chip[data-m='spell']")
            page16.wait_for_timeout(200)
            page16.click("#startQuiz")
            page16.wait_for_selector("#spellInput", state="attached")
            spell_word = page16.evaluate("() => window.WL_DEBUG.quiz.queue[window.WL_DEBUG.quiz.i].word")
            page16.fill("#spellInput", spell_word)
            page16.press("#spellInput", "Enter")
            page16.wait_for_timeout(350)
            spell_st = page16.evaluate(
                "() => ({i: window.WL_DEBUG.quiz.i, answered: window.WL_DEBUG.quiz.answered,"
                " fb: (document.querySelector('#qFb') || {}).className || ''})")
            ok("拼写填空按 Enter 出反馈卡且不跳下一题",
               bool(spell_st) and spell_st.get("answered") is True and spell_st.get("i") == 0
               and "show" in (spell_st.get("fb") or ""), json.dumps(spell_st, ensure_ascii=False))
        except Exception as e:
            ok("拼写填空按 Enter 出反馈卡且不跳下一题", False, "exception: " + str(e)[:120])

        # ---------- (2)(3) 闪卡评分记账 + 撤销不再抹掉后来的手动标记 ----------
        try:
            page16.goto(base + "#cards", wait_until="load")
            page16.wait_for_selector(".chip.deck-opt[data-s='all']", state="attached")
            page16.click(".chip.deck-opt[data-s='all']")
            page16.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            page16.wait_for_selector("#flipCard", state="attached")
            fc_num = int(re.sub(r"\D", "", page16.locator("#flipCard .fc-num").first.inner_text()))
            # 起评前先把这个词的旧进度清干净，断言才不受本套件前面用例的残留影响
            page16.evaluate("n => { delete window.WL_DEBUG.state.progress[n]; }", fc_num)
            page16.keyboard.press(" ")          # 翻面
            page16.wait_for_timeout(150)
            page16.keyboard.press("3")          # 认识
            page16.wait_for_timeout(300)
            fc_st = page16.evaluate(
                "n => { const p = window.WL_DEBUG.state.progress[n];"
                "return p ? {lv: p.lv, seen: p.seen, correct: p.correct, wrong: p.wrong} : null; }",
                fc_num)
            ok("闪卡评分计入正确次数",
               bool(fc_st) and fc_st.get("correct") == 1 and fc_st.get("seen") == 1,
               json.dumps(fc_st, ensure_ascii=False))
            # 评分之后手动标「已掌握」，再撤销：撤销只该回退评分那次改动
            page16.evaluate("n => window.WL_DEBUG.setStatus(n, 'mastered')", fc_num)
            page16.keyboard.press("u")
            page16.wait_for_timeout(300)
            undo_st = page16.evaluate(
                "n => { const p = window.WL_DEBUG.state.progress[n];"
                "return p ? {lv: p.lv} : null; }", fc_num)
            ok("撤销不抹掉评分之后的「已掌握」手动标记",
               bool(undo_st) and undo_st.get("lv") == 5, json.dumps(undo_st, ensure_ascii=False))
        except Exception as e:
            ok("闪卡评分计入正确次数", False, "exception: " + str(e)[:120])
            ok("撤销不抹掉评分之后的「已掌握」手动标记", False, "exception: " + str(e)[:120])

        # ---------- (4) 撤销按差量回退当天互动次数（不抹掉评分之后的其它活动） ----------
        try:
            days_sum = "() => { const d = window.WL_DEBUG.state.days || {};"
            days_sum += "let n = 0; for (const k in d) n += (d[k] || 0); return n; }"
            d_before = page16.evaluate(days_sum)
            page16.keyboard.press(" ")          # 翻到下一张
            page16.wait_for_timeout(150)
            page16.keyboard.press("3")          # 再评一次（当天次数 +1）
            page16.wait_for_timeout(250)
            d_rated = page16.evaluate(days_sum)
            # 再制造一次「评分之后」的活动：去测验答一题（会 bump 当天次数）。
            # 注意不能整页重载：闪卡会话（fc）活在内存里，重载后撤销栈就没了。
            # 所以先把残留的测验会话清掉（前面 (1) 留了一场拼写测验），再靠
            # 路由跳转重画测验页。
            page16.evaluate("() => { const q = window.WL_DEBUG.quiz;"
                            "q.session = 0; q.queue = []; q.fb = null; q.answered = false;"
                            "q.mode = 'en2zh'; q.curMode = 'en2zh'; }")
            page16.goto(base + "#quiz", wait_until="load")
            page16.wait_for_selector("#startQuiz", state="attached")
            page16.click("#startQuiz")
            page16.wait_for_selector(".quiz-opt", state="attached")
            page16.locator(".quiz-opt").first.click()
            page16.wait_for_timeout(300)
            d_quiz = page16.evaluate(days_sum)
            page16.goto(base + "#cards", wait_until="load")
            page16.wait_for_selector("#flipCard", state="attached")
            page16.keyboard.press("u")          # 撤销最后一次闪卡评分
            page16.wait_for_timeout(300)
            d_undo = page16.evaluate(days_sum)
            ok("撤销按差量回退当天互动次数（评分之后的测验活动不被抹掉）",
               d_rated == d_before + 1 and d_quiz == d_rated + 1 and d_undo == d_rated,
               "before=%s rated=%s quiz=%s undo=%s" % (d_before, d_rated, d_quiz, d_undo))
        except Exception as e:
            ok("撤销按差量回退当天互动次数（评分之后的测验活动不被抹掉）", False,
               "exception: " + str(e)[:120])
        page16.close()
        # ---------- (8) 挖空句里目标词只出现一次（防御性守卫，当前数据下恒成立） ----------
        try:
            page20 = ctx.new_page()
            page20.set_default_navigation_timeout(90000)
            page20.goto(base + "#home", wait_until="load")
            page20.wait_for_timeout(300)
            cloze_bad = page20.evaluate(
                "() => { const D = window.WL_DEBUG, W = window.WL_WORDS || [];"
                "const countCI = (s, w) => {"
                "  const ws = w.trim().toLowerCase().split(/\\s+/);"
                "  const toks = s.toLowerCase().match(/[a-z]+/g) || [];"
                "  let n = 0;"
                "  for (let i = 0; i + ws.length <= toks.length; i++) {"
                "    let m = true;"
                "    for (let j = 0; j < ws.length; j++)"
                "      if (toks[i + j] !== ws[j]) { m = false; break; }"
                "    if (m) n++;"
                "  }"
                "  return n;"
                "};"
                "const bad = [];"
                "for (const w of W) {"
                "  const slot = D.clozeSlot(w); if (!slot) continue;"
                "  if (countCI(slot.en, w.word) > 1) bad.push(w.word);"
                "}"
                "return bad; }")
            ok("挖空句里目标词不重复出现（答案不会明写在题干里）",
               isinstance(cloze_bad, list) and not cloze_bad, str(cloze_bad[:5]))
            page20.close()
        except Exception as e:
            ok("挖空句里目标词不重复出现（答案不会明写在题干里）", False, "exception: " + str(e)[:120])


        # ---------- (5)(5b)(6) 备份净化：等级钳制 / 坏时间戳 / 弹窗状态高亮 ----------
        page17 = ctx.new_page()
        page17.set_default_navigation_timeout(90000)
        page17.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page17.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        # 种一份「半坏」存档：lv 越界 + 测验记录缺时间戳
        page17.add_init_script(
            "try{localStorage.setItem('wl_state_v1',"
            "'{\"progress\":{\"1\":{\"lv\":0,\"due\":0,\"seen\":1,\"correct\":0,\"wrong\":0,\"last\":0}},"
            "\"quizHist\":[{\"score\":1,\"total\":1,\"mode\":\"mix\",\"scope\":\"all\"}],"
            "\"fav\":[],\"days\":{},"
            "\"settings\":{\"theme\":\"light\",\"goal\":30,\"rate\":0.95}}');}catch(e){}")
        try:
            page17.goto(base + "#home", wait_until="load")   # 先把应用跑起来（钩子挂在页面上）
            page17.wait_for_timeout(300)
            clamp_st = page17.evaluate(
                "() => { const s = window.WL_DEBUG.sanitizeState({"
                "progress: {'1': {lv: -3, due: 0, seen: 1, correct: 0, wrong: 0, last: 0},"
                "             '2': {lv: 99, due: 0, seen: 1, correct: 0, wrong: 0, last: 0}},"
                "quizHist: [{score: 1, total: 1, t: 'abc'}]});"
                "return {lo: s.progress['1'].lv, hi: s.progress['2'].lv, t: s.quizHist[0].t}; }")
            ok("记忆等级越界被钳在 0–5 之间",
               clamp_st.get("lo") == 0 and clamp_st.get("hi") == 5, json.dumps(clamp_st, ensure_ascii=False))
            ok("非法的测验时间戳被摘掉",
               clamp_st.get("t") is None, json.dumps(clamp_st, ensure_ascii=False))
        except Exception as e:
            ok("记忆等级越界被钳在 0–5 之间", False, "exception: " + str(e)[:120])
            ok("非法的测验时间戳被摘掉", False, "exception: " + str(e)[:120])
        try:
            page17.goto(base + "#home", wait_until="load")
            page17.wait_for_timeout(500)
            home_txt = page17.evaluate("() => document.body.innerText")
            ok("首页的最近测验不渲染 NaN 日期", "NaN" not in home_txt,
               home_txt[home_txt.find("最近测验"):home_txt.find("最近测验") + 40]
               if "最近测验" in home_txt else home_txt[:60])
            page17.goto(base + "#stats", wait_until="load")
            page17.wait_for_timeout(500)
            stats_txt = page17.evaluate("() => document.body.innerText")
            ok("统计页的测验记录不渲染 Invalid Date",
               "Invalid Date" not in stats_txt and "NaN" not in stats_txt,
               stats_txt[stats_txt.find("最近测验记录"):stats_txt.find("最近测验记录") + 40]
               if "最近测验记录" in stats_txt else stats_txt[:60])
            # 弹窗里的手动标记高亮必须与全库口径一致（lv=0 的词算「学习中」）
            page17.evaluate("() => window.WL_DEBUG.openWordModal(1)")
            page17.wait_for_timeout(300)
            mark_st = page17.evaluate(
                "() => ({m0: document.querySelector('#wmMark0').className,"
                " m1: document.querySelector('#wmMark1').className,"
                " m2: document.querySelector('#wmMark2').className})")
            ok("lv=0 的词在弹窗里高亮「学习中」而不是「不认识」",
               " on" in mark_st.get("m1", "") and " on" not in mark_st.get("m0", ""),
               json.dumps(mark_st, ensure_ascii=False))
        except Exception as e:
            ok("首页的最近测验不渲染 NaN 日期", False, "exception: " + str(e)[:120])
            ok("统计页的测验记录不渲染 Invalid Date", False, "exception: " + str(e)[:120])
            ok("lv=0 的词在弹窗里高亮「学习中」而不是「不认识」", False, "exception: " + str(e)[:120])

        # ---------- (7) 打印范围：在非清单视图按 Ctrl+P 不再沿用词库页的过期筛选 ----------
        page18 = ctx.new_page()
        page18.set_default_navigation_timeout(90000)
        page18.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page18.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        try:
            page18.goto(base + "#browse", wait_until="load")
            page18.wait_for_selector("#btnFilterToggle", state="attached")
            # 筛选面板默认收起，字母条藏在里面：先展开再点字母
            page18.evaluate("() => { const w = document.querySelector('#filterWrap');"
                            "if (w && w.classList.contains('collapsed'))"
                            "document.querySelector('#btnFilterToggle').click(); }")
            page18.wait_for_selector("#letterBar .letter-btn[data-l='K']", state="visible")
            page18.click("#letterBar .letter-btn[data-l='K']")
            page18.wait_for_timeout(250)
            page18.goto(base + "#quiz", wait_until="load")
            page18.wait_for_timeout(400)
            page18.evaluate("() => window.dispatchEvent(new Event('beforeprint'))")
            pl_meta = page18.evaluate(
                "() => { const el = document.querySelector('#printList .pl-meta');"
                "return el ? el.textContent : ''; }")
            ok("非清单视图打印时不再沿用词库页的过期筛选",
               "全部词库" in pl_meta and "首字母" not in pl_meta, pl_meta)
        except Exception as e:
            ok("非清单视图打印时不再沿用词库页的过期筛选", False, "exception: " + str(e)[:120])
        page18.close()

        # ---------- (8b) 筛选面板各档之和 = 全部（每一维都要兜得住全量） ----------
        # 感情色彩此前只有积极/消极/中性三档：本库只给 438 个形容词标注褒贬色彩，
        # 其余 1571 词在这一维上没有任何入口 —— 点遍三档也拼不出全量，数字加不起来。
        # 现补一档「其他」（未标注）兜住差额：四档之和 = 该维的「不限」条数。
        page18b = ctx.new_page()
        page18b.set_default_navigation_timeout(90000)
        page18b.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page18b.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        try:
            page18b.goto(base + "#browse", wait_until="load")
            page18b.wait_for_selector("#subFilter", state="attached")
            # 宽屏下面板本就展开；窄屏折叠时先展开
            page18b.evaluate("() => { const w = document.querySelector('#filterWrap');"
                             "if (w && w.classList.contains('collapsed'))"
                             "document.querySelector('#btnFilterToggle').click(); }")
            page18b.wait_for_selector("#subFilter .chip", state="visible")
            # 面板上的数字：按 data-fcnt 取每一档
            fc = page18b.evaluate(
                "() => { const o = {};"
                "document.querySelectorAll('#subFilter [data-fcnt]').forEach(e =>"
                "{ const k = e.dataset.fcnt; o[k] = Number(e.textContent.trim()); });"
                "return o; }")
            # 各档之和 = 该维的「不限」条数。档名不写死：按面板上实际存在的档位求和
            # （库内取值随内容轮次增减，写死档名会让断言在新增一档时假红）。
            sum4 = sum(v for k, v in fc.items() if k.startswith("sub|") and k != "sub|")
            ok("感情色彩各档之和 = 该维的「不限」条数",
               sum4 == fc.get("sub|"), f"sum={sum4} unlimited={fc.get('sub|')}")
            # 「其他」这一档真的能筛出未标注的词（数字与点下去的结果一致）
            page18b.click("#subFilter .chip[data-sub='未标注']")
            page18b.wait_for_timeout(300)
            got = page18b.evaluate(
                "() => { const m = document.querySelector('#browseTable')?.innerText.match(/(\\d+)\\s*词/);"
                "return m ? Number(m[1]) : -1; }")
            ok("「其他」这一档筛出的词数与面板上的数字一致",
               got == fc.get("sub|未标注", -1), f"list={got} chip={fc.get('sub|未标注')}")
            # 词性锁到「形容词」时该维度下没有未标注词 → 这档必须撤掉并禁用
            # （否则「形容词 + 其他」恒空，用户点下去只得到一张空表）
            page18b.click("#posFilter .chip[data-pos='形容词']")
            page18b.wait_for_timeout(300)
            st = page18b.evaluate(
                "() => { const c = document.querySelector(\"#subFilter .chip[data-sub='未标注']\");"
                "const s = document.querySelector('.filter-summary');"
                "return { dis: c ? c.disabled : null, txt: c ? c.textContent.trim() : '',"
                " sum: s ? s.textContent.trim() : '' }; }")
            ok("词性锁到形容词时「其他」这一档被撤掉并禁用",
               st.get("dis") is True and "其他" not in (st.get("sum") or ""),
               json.dumps(st, ensure_ascii=False))
            # 词性锁到副词/连词时，感情色彩这一排**仍然显示**：四个带标签的档
            # 恒为 0（显示 0、灰显不可点），「其他」那一档 = 该词性的全体。
            # （此前整行藏起来，用户看不到「这一类词不带评价色彩」这件事。）
            for _pos in ("副词", "连词"):
                page18b.click(f"#posFilter .chip[data-pos='{_pos}']")
                page18b.wait_for_timeout(300)
                adv = page18b.evaluate(
                    "() => { const o = {};"
                    "document.querySelectorAll('#subFilter .chip').forEach(c => {"
                    "  o[c.dataset.sub] = { n: Number(c.querySelector('.cnt')?.textContent.trim()),"
                    "                   dis: c.disabled }; });"
                    "const m = document.querySelector('#browseTable')?.innerText.match(/(\\d+)\\s*词/);"
                    "return { row: !!document.querySelector('#subFilter'), o, list: m ? Number(m[1]) : -1 }; }")
                _lab = ["积极的", "消极的", "争议性的", "中性的"]
                ok(f"词性锁到{_pos}时感情色彩那一排仍然显示、四个带标签档显示 0 且不可点",
                   adv.get("row") is True
                   and all(adv["o"].get(k, {}).get("n") == 0 and adv["o"][k].get("dis") is True for k in _lab),
                   json.dumps(adv, ensure_ascii=False))
                ok(f"词性锁到{_pos}时「其他」那一档 = 该词性全体",
                   adv["o"].get("未标注", {}).get("n") == adv.get("list")
                   and adv["o"].get("未标注", {}).get("dis") is False,
                   json.dumps(adv, ensure_ascii=False))
        except Exception as e:
            ok("感情色彩各档之和 = 该维的「不限」条数", False, "exception: " + str(e)[:120])
            ok("「其他」这一档筛出的词数与面板上的数字一致", False, "exception: " + str(e)[:120])
            ok("词性锁到形容词时「其他」这一档被撤掉并禁用", False, "exception: " + str(e)[:120])
            ok("词性锁到副词/连词时感情色彩那一排仍然显示、四个带标签档显示 0 且不可点",
               False, "exception: " + str(e)[:120])
            ok("词性锁到副词/连词时「其他」那一档 = 该词性全体",
               False, "exception: " + str(e)[:120])
        page18b.close()

        # ---------- (8c) 筛选外壳随局部刷新路径联动（状态下拉 / 搜索框） ----------
        # 此前筛选摘要（.filter-summary）、窄屏枚数徽标（.ft-count）、面板头
        # 「清空筛选」只在点 chip 的整页重绘时重算；状态下拉与搜索框走
        # refresh() 只重画表格 —— 三样全不更新，选了「已掌握」后摘要不出现、
        # 徽标不动、面板头也不给清空按钮（桌面 + 窄屏两路都复现）。
        # 现 syncFilterChrome 挂进 refresh()，三样跟筛选状态走。
        page18c = ctx.new_page()
        page18c.set_default_navigation_timeout(90000)
        page18c.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page18c.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        try:
            page18c.goto(base + "#browse", wait_until="load")
            page18c.wait_for_selector("#browseTable", state="attached")
            def chrome(p):
                return p.evaluate(
                    "() => ({ badge: (document.querySelector('.ft-count')||{}).textContent || '',"
                    " summary: (document.querySelector('.filter-summary')||{}).textContent || '',"
                    " reset: !!document.querySelector('#btnResetFilters'),"
                    " result: (document.querySelector('.count-line b')||{}).textContent })")
            st = chrome(page18c)
            ok("8c 初始（无筛选）外壳全空", st["badge"] == "" and st["summary"] == "" and not st["reset"],
               json.dumps(st, ensure_ascii=False))
            # 状态下拉（refresh 局部刷新路径）
            page18c.select_option("#bstatus", "mastered")
            page18c.wait_for_timeout(300)
            st = chrome(page18c)
            ok("8c 状态下拉后摘要/徽标/清空钮联动", "已掌握" in st["summary"] and st["badge"] == "1" and st["reset"],
               json.dumps(st, ensure_ascii=False))
            # 摘要文案与零结果空态的筛选说明同源：空态里写「状态 已掌握」，
            # 摘要只写「已掌握」（STATUS_LABEL 直出）——两处都不该漏这一条
            ok("8c 摘要含状态名", "已掌握" in st["summary"], st["summary"])
            # 搜索框叠加（同一局部刷新路径）
            page18c.fill("#bq", "able")
            page18c.wait_for_timeout(600)
            st = chrome(page18c)
            ok("8c 搜索叠加后徽标=2、摘要两段",
               st["badge"] == "2" and "关键词「able」" in st["summary"],
               json.dumps(st, ensure_ascii=False))
            # 面板头清空按钮（refresh 路径补出来的那枚）真实可点
            page18c.click("#btnResetFilters")
            page18c.wait_for_timeout(300)
            total = page18c.evaluate("window.WL_WORDS.length")
            st = chrome(page18c)
            ok("8c 点清空 → 外壳归零、结果回全库",
               st["badge"] == "" and st["summary"] == "" and not st["reset"] and st["result"] == str(total),
               json.dumps(st, ensure_ascii=False))
        except Exception as e:
            ok("8c 初始（无筛选）外壳全空", False, "exception: " + str(e)[:120])
            ok("8c 状态下拉后摘要/徽标/清空钮联动", False, "exception: " + str(e)[:120])
            ok("8c 摘要含状态名", False, "exception: " + str(e)[:120])
            ok("8c 搜索叠加后徽标=2、摘要两段", False, "exception: " + str(e)[:120])
            ok("8c 点清空 → 外壳归零、结果回全库", False, "exception: " + str(e)[:120])
        page18c.close()

        # ---------- (9) 「只测错题」也要守题数设置 ----------
        page19 = ctx.new_page()
        page19.set_default_navigation_timeout(90000)
        page19.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page19.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        try:
            page19.goto(base + "#quiz", wait_until="load")
            page19.wait_for_selector("#startQuiz", state="attached")
            page19.evaluate("() => { window.WL_DEBUG.quiz.count = 4; }")
            page19.click("#startQuiz")
            page19.wait_for_selector(".quiz-opt", state="attached")
            for _ in range(4):                 # 四题全答错
                page19.locator(".quiz-opt[data-ok='false']").first.click()
                page19.wait_for_timeout(200)
                page19.wait_for_selector("#qNext", state="attached")
                page19.click("#qNext")
                page19.wait_for_timeout(250)
            page19.wait_for_selector("#redoWrong", state="attached")
            # 事后往错题表里再塞几个（模拟错题多于题数），只测错题仍须截到题数
            page19.evaluate("() => { const w = window.WL_WORDS || [];"
                            "for (const x of w.slice(0, 3)) window.WL_DEBUG.quiz.wrong.push(x); }")
            page19.click("#redoWrong")
            page19.wait_for_timeout(300)
            redo_len = page19.evaluate("() => window.WL_DEBUG.quiz.queue.length")
            ok("「只测错题」按题数设置截断", redo_len == 4, "queue=%s" % redo_len)
        except Exception as e:
            ok("「只测错题」按题数设置截断", False, "exception: " + str(e)[:120])
        page19.close()

        # ---------- (10) 同义组：策展白名单生效（中文选词/听音辨词不出「两个都对」） ----------
        # 背景：自动分组只认「释义全文相同」，objective 后来追加了「客观的…」义项，
        # 于是掉出 goal/aim 组；therefore/hence/document 等更是从来不同义。
        # 机械的「元素互为前缀」规则会造出 287 个假同源团，故前端只登记策展白名单。
        page20 = ctx.new_page()
        page20.set_default_navigation_timeout(90000)
        page20.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page20.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        try:
            page20.goto(base + "#home", wait_until="load")
            page20.wait_for_timeout(400)
            syn_st = page20.evaluate(
                "() => { const W = window.WL_WORDS || [], D = window.WL_DEBUG;"
                "const groups = D.SYNONYM_GROUPS || [];"
                "const pick = w => W.find(x => x.word === w);"
                "const missing = [];"
                "for (const g of groups) for (const w of g)"
                "  if (!pick(w)) missing.push(w);"
                # ① 排除集是确定量：每个成员的排除集必须含同组其它成员
                "const notExcluded = [];"
                "for (const g of groups) for (const w of g) {"
                "  const wo = pick(w); if (!wo) continue;"
                "  const ex = D.excludeNums(wo);"
                "  for (const o of g) if (o !== w && !ex.has(pick(o).num))"
                "    notExcluded.push(w + '->' + o); }"
                # ② 干扰项是随机抽的：抽 60 轮，同组词一次都不许出现
                "const leaked = []; const optCount = {};"
                "for (const g of groups) for (const w of g) {"
                "  const wo = pick(w); if (!wo) continue;"
                "  for (let i = 0; i < 60; i++) {"
                "    const opts = D.optionTexts(wo, x => x.word).map(o => o.t);"
                "    optCount[w] = opts.length;"
                "    for (const o of g) if (o !== w && opts.indexOf(o) >= 0)"
                "      leaked.push(w + '->' + o); } }"
                "return {nGroups: groups.length,"
                " nWords: groups.reduce((a, g) => a + g.length, 0),"
                " missing: missing, notExcluded: notExcluded, leaked: leaked,"
                " optCount: optCount}; }")
            ok("同义白名单的成员都在词表里（9 组 / 22 词）",
               syn_st.get("nGroups") == 9 and syn_st.get("nWords") == 22
               and not syn_st.get("missing"),
               json.dumps({k: syn_st.get(k) for k in ("nGroups", "nWords", "missing")}, ensure_ascii=False))
            ok("每个白名单成员的排除集都含同组其它成员",
               not syn_st.get("notExcluded"),
               json.dumps(syn_st.get("notExcluded"), ensure_ascii=False)[:300])
            ok("同组词永远不会被抽成干扰项（9 组 × 60 轮抽样）",
               not syn_st.get("leaked"),
               json.dumps(syn_st.get("leaked"), ensure_ascii=False)[:300])
            ok("同义排除后仍能凑满 4 个选项",
               syn_st.get("optCount") and all(v == 4 for v in syn_st.get("optCount").values()),
               json.dumps(syn_st.get("optCount"), ensure_ascii=False)[:300])
        except Exception as e:
            for nm in ("同义白名单的成员都在词表里（9 组 / 22 词）",
                       "每个白名单成员的排除集都含同组其它成员",
                       "同组词永远不会被抽成干扰项（9 组 × 60 轮抽样）",
                       "同义排除后仍能凑满 4 个选项"):
                ok(nm, False, "exception: " + str(e)[:120])
        page20.close()
        page17.close()

        # ---------- (11) 时钟/目标/撤销三处口径回归 ----------
        # (11a) 机器时钟早于 1970-01-01（RTC 未初始化、BIOS 设错）时，
        #       旧「每日一词」按日序取模会把索引算成负数 → WORDS[-365] 是
        #       undefined → 模板求值抛错、整页空白。第一百四十八轮改成
        #       「随机一词」（Math.random 取索引），负索引的成因不复存在，
        #       但这条仍要守：异常时钟下总览页必须照常渲染出词来。
        page21 = ctx.new_page()
        page21.set_default_navigation_timeout(90000)
        err21 = []
        page21.on("pageerror", lambda e: err21.append(str(e)))
        page21.add_init_script("""
          (() => {
            const Real = Date;
            const FIXED = new Real('1969-06-03T12:00:00Z').getTime();
            class FakeDate extends Real {
              constructor(...a) { if (!a.length) super(FIXED); else super(...a); }
              static now() { return FIXED; }
            }
            FakeDate.parse = Real.parse; FakeDate.UTC = Real.UTC;
            window.Date = FakeDate;
          })();
        """)
        try:
            page21.goto(base + "#home", wait_until="load")
            page21.wait_for_timeout(500)
            wotd21 = page21.evaluate(
                "() => { const e = document.querySelector('.rand-word .w');"
                " return e ? e.textContent.trim() : ''; }")
            ok("时钟早于 1970 时总览页仍能渲染出随机一词",
               (not err21) and bool(wotd21),
               ("errors=%s " % err21[:1]) if err21 else "wotd=%r" % wotd21)
        except Exception as e:
            ok("时钟早于 1970 时总览页仍能渲染出随机一词", False, "exception: " + str(e)[:120])
        page21.close()

        # (11b) 每日目标：运行时写入与刷新后的 sanitizeState 必须同口径（都取整），
        #       否则输入 30.5 → 当天显示 30.5、刷新后变 31，同一目标两个值。
        page22 = ctx.new_page()
        page22.set_default_navigation_timeout(90000)
        try:
            page22.goto(base + "#settings", wait_until="load")
            page22.wait_for_selector("#goalInput", state="attached")
            page22.fill("#goalInput", "30.5")
            page22.dispatch_event("#goalInput", "change")
            page22.wait_for_timeout(400)
            goal22 = page22.evaluate("() => window.WL_DEBUG.state.settings.goal")
            shown22 = page22.input_value("#goalInput")
            ok("每日目标写入即取整（与刷新后的口径一致）",
               goal22 == 31 and shown22 == "31", "goal=%s shown=%s" % (goal22, shown22))
        except Exception as e:
            ok("每日目标写入即取整（与刷新后的口径一致）", False, "exception: " + str(e)[:120])
        page22.close()

        # (11c) 撤销评分：若评分后该词被手动「不认识」删掉进度条目，
        #       等级/计数无从回退（保留那次手动重置才是对的），提示必须据实说明，
        #       不能仍报「已撤销上一次评分」。
        page23 = ctx.new_page()
        page23.set_default_navigation_timeout(90000)
        try:
            page23.goto(base + "#cards", wait_until="load")
            page23.wait_for_selector(".deck-opt[data-s='all']", state="attached")
            page23.click(".deck-opt[data-s='all']")
            page23.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            page23.wait_for_selector(".flip-card", state="attached")
            w23 = page23.evaluate("() => document.querySelector('.fc-word').textContent.trim()")
            num23 = page23.evaluate(
                "(w) => { const x = (window.WL_WORDS || []).find(v => v.word === w);"
                " return x ? x.num : null; }", w23)
            page23.click(".fc-word")              # 翻面（卡片中心是朗读钮）
            # 先让这个词「已学习」（有进度条目），评分前的快照才非空——
            # 撤销记录里的 before 为空表示「评分前是全新词」，那是另一条分支。
            page23.evaluate("(n) => window.WL_DEBUG.setStatus(n, 'learning')", num23)
            page23.wait_for_timeout(200)
            page23.wait_for_timeout(400)
            page23.keyboard.press("3")            # 评分（lv 会写进度）
            page23.wait_for_timeout(500)
            ok("评分后确有进度条目", page23.evaluate(
                "(n) => !!(window.WL_DEBUG.state.progress[n])", num23) is True,
               "num=%s word=%r" % (num23, w23))
            page23.evaluate("(n) => window.WL_DEBUG.setStatus(n, 'new')", num23)  # 手动「不认识」→ 删条目
            page23.keyboard.press("u")            # 撤销
            page23.wait_for_timeout(400)
            toast23 = page23.inner_text("#toastWrap")
            still23 = page23.evaluate(
                "(n) => window.WL_DEBUG.state.progress[n] === undefined", num23)
            ok("进度被手动重置后撤销提示据实说明（不再谎称已完全撤销）",
               ("手动重置" in toast23) and still23,
               "toast=%r" % toast23.strip()[:80])
        except Exception as e:
            ok("进度被手动重置后撤销提示据实说明（不再谎称已完全撤销）", False,
               "exception: " + str(e)[:120])
        page23.close()

        # ---------- (12) 状态归一 / 内核兼容 / 提示据实 / 快捷键精确匹配 ----------
        # (12a) 备份里写成字符串的数字（手改备份、第三方导出）必须被**归一**而不是
        #        当成脏数据丢掉：lv 是字符串时整条进度记录曾被删 → 导入后该词进度
        #        凭空清零（seen/correct/due 一并消失），而同一批里 days/quizHist
        #        的字符串数字也被逐条剔除，连打卡日历都少格子。
        page24 = ctx.new_page()
        page24.set_default_navigation_timeout(90000)
        try:
            page24.goto(base + "#home", wait_until="load")
            page24.wait_for_timeout(400)
            san24 = page24.evaluate(
                """() => {
                    const D = window.WL_DEBUG;
                    const mk = o => D.sanitizeState(Object.assign(
                        {progress:{}, settings:{}, days:{}, fav:[], quizHist:[]}, o));
                    const out = {};
                    const s1 = mk({progress:{'101':{lv:'3',seen:'12',correct:'5',wrong:'1',due:'0',last:'0'}}});
                    out.lv = s1.progress['101'] ? s1.progress['101'].lv : null;
                    out.seen = s1.progress['101'] ? s1.progress['101'].seen : null;
                    const s2 = mk({days:{'2026-11-17':'12'},
                                   quizHist:[{score:'8',total:'10',t:'1700000000000',skipped:'2'}]});
                    out.day = s2.days['2026-11-17'];
                    out.hist = s2.quizHist[0] || null;
                    const s3 = mk({progress:{'102':{lv:'abc',seen:'3'}},
                                   days:{'2026-11-18':'abc'},
                                   quizHist:[{score:'x',total:'10'}]});
                    out.badLvDropped = !s3.progress['102'];
                    out.badDayDropped = !s3.days['2026-11-18'];
                    out.badHistDropped = s3.quizHist.length === 0;
                    return out;
                }""")
            ok("备份里的数字字符串等级被归一（不再整条删除进度记录）",
               san24.get("lv") == 3 and san24.get("seen") == 12,
               json.dumps(san24, ensure_ascii=False)[:200])
            ok("打卡日计数里的数字字符串被归一",
               san24.get("day") == 12, json.dumps(san24, ensure_ascii=False)[:200])
            hist24 = san24.get("hist") or {}
            ok("测验历史里的字符串分数/题数/时间戳被归一",
               hist24.get("score") == 8 and hist24.get("total") == 10
               and hist24.get("t") == 1700000000000 and hist24.get("skipped") == 2,
               json.dumps(hist24, ensure_ascii=False)[:200])
            ok("真非数字仍按脏数据剔除（归一口径没有放松到收烂值）",
               san24.get("badLvDropped") and san24.get("badDayDropped")
               and san24.get("badHistDropped"),
               json.dumps(san24, ensure_ascii=False)[:200])
        except Exception as e:
            for nm in ("备份里的数字字符串等级被归一（不再整条删除进度记录）",
                       "打卡日计数里的数字字符串被归一",
                       "测验历史里的字符串分数/题数/时间戳被归一",
                       "真非数字仍按脏数据剔除（归一口径没有放松到收烂值）"):
                ok(nm, False, "exception: " + str(e)[:120])
        page24.close()

        # (12b) 旧内核（Safari < 14 等）的 matchMedia 只有 addListener、没有
        #        addEventListener。主题已不再跟随系统（不再监听 prefers-color-scheme），
        #        这里仍保留这条守卫：旧内核形状的 matchMedia 不得让页面渲染崩掉。
        page25 = ctx.new_page()
        page25.set_default_navigation_timeout(90000)
        err25 = []
        page25.on("pageerror", lambda e: err25.append(str(e)))
        page25.add_init_script("""
          (() => {
            const real = window.matchMedia.bind(window);
            window.matchMedia = q => {
              const m = real(q);
              // 旧内核形状：没有 addEventListener，只有被废弃的 addListener
              return {matches: m.matches, media: q,
                      addListener: cb => m.addEventListener ? m.addEventListener('change', cb) : null,
                      removeListener: () => {}};
            };
          })();
        """)
        try:
            page25.goto(base + "#home", wait_until="load")
            page25.wait_for_timeout(600)
            main25 = page25.evaluate(
                "() => { const m = document.querySelector('#main');"
                " return m ? m.textContent.trim().length : 0; }")
            ok("matchMedia 只有 addListener 的旧内核下页面仍完整渲染",
               (not err25) and main25 > 50,
               ("errors=%s " % err25[:1]) if err25 else "main_len=%s" % main25)
        except Exception as e:
            ok("matchMedia 只有 addListener 的旧内核下页面仍完整渲染", False,
               "exception: " + str(e)[:120])
        page25.close()

        # (12c) 复制降级路径：execCommand 返回 false 就是没复制成（file:// 非安全
        #        上下文、权限被拒、浏览器停用该 API）。旧写法丢掉返回值，照样弹
        #        「已复制」——而这条 toast 是唯一的成功凭据。
        page26 = ctx.new_page()
        page26.set_default_navigation_timeout(90000)
        page26.add_init_script("""
          (() => {
            try { Object.defineProperty(navigator, 'clipboard',
                       {value: undefined, configurable: true}); } catch (e) {}
            document.execCommand = () => false;
          })();
        """)
        try:
            page26.goto(base + "#home", wait_until="load")
            page26.wait_for_timeout(400)
            page26.evaluate("() => window.WL_DEBUG.openWordModal(window.WL_WORDS[0].num)")
            page26.wait_for_selector("#wmCopy", state="attached")
            page26.click("#wmCopy")
            page26.wait_for_timeout(400)
            toast26 = page26.inner_text("#toastWrap")
            ok("复制失败时不谎报「已复制」（降级路径据实提示）",
               ("已复制" not in toast26) and ("复制失败" in toast26),
               "toast=%r" % toast26.strip()[:80])
        except Exception as e:
            ok("复制失败时不谎报「已复制」（降级路径据实提示）", False,
               "exception: " + str(e)[:120])
        page26.close()

        # (12d) 快捷键精确匹配：String.includes 是子串判定，key 为多字符（"12"）
        #        时会被当成选项键 → rate(11) 把单词记成「忘了」、或点错测验选项。
        page27 = ctx.new_page()
        page27.set_default_navigation_timeout(90000)
        try:
            page27.goto(base + "#cards", wait_until="load")
            page27.wait_for_selector(".deck-opt[data-s='all']", state="attached")
            page27.click(".deck-opt[data-s='all']")
            page27.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            page27.wait_for_selector(".flip-card", state="attached")
            page27.click(".fc-word")           # 翻面（fc.flipped = true）
            page27.wait_for_timeout(300)
            st27 = page27.evaluate(
                """() => {
                    const w = document.querySelector('.fc-word').textContent.trim();
                    const x = (window.WL_WORDS || []).find(v => v.word === w);
                    return {word: w, num: x ? x.num : null,
                            prog: JSON.stringify(window.WL_DEBUG.state.progress[x ? x.num : -1] || null)};
                }""")
            page27.evaluate(
                """() => document.dispatchEvent(
                       new KeyboardEvent('keydown', {key: '12', bubbles: true}))""")
            page27.wait_for_timeout(400)
            after27 = page27.evaluate(
                "(n) => JSON.stringify(window.WL_DEBUG.state.progress[n] || null)", st27["num"])
            word27 = page27.evaluate("() => document.querySelector('.fc-word').textContent.trim()")
            ok("多字符按键不会被误判成评分/选项键",
               after27 == st27["prog"] and word27 == st27["word"],
               "before=%s after=%s word=%r" % (st27["prog"], after27, word27))
        except Exception as e:
            ok("多字符按键不会被误判成评分/选项键", False, "exception: " + str(e)[:120])
        page27.close()

        # (13) 搜索结果与上下文导航的一致性：
        #      ① 全局搜索的 oninput 是 120ms 防抖，结果列表 srList 只在防抖
        #         触发后重建；用户打完字立刻按 Enter 时，srList 还是上一次的
        #         （空查询时是随机推荐位）⇒ 打开一个与输入毫不相干的词。
        #      ② 上一次查询无结果时 srList 为空，Enter 什么都不做，输入被静默丢弃。
        #      ③ 词条弹窗的 ←/→ 须与「上一条/下一条」按钮一致：当前词不在
        #         上下文列表里时按钮是禁用的，键盘却会跳到列表第一项（无关词）。
        page28 = ctx.new_page()
        page28.set_default_navigation_timeout(90000)
        try:
            page28.goto(base, wait_until="load")
            page28.wait_for_timeout(300)

            # 13a：打完就按 Enter（不等防抖）
            page28.keyboard.press("/")
            page28.wait_for_timeout(150)
            page28.evaluate(
                """() => { const i = document.querySelector('#searchInput');
                           i.value = 'crucial'; i.dispatchEvent(new Event('input')); }""")
            page28.keyboard.press("Enter")
            page28.wait_for_timeout(400)
            t28a = page28.evaluate(
                "() => { const m = document.querySelector('#wmTitle'); return m ? m.textContent.trim() : null; }")
            ok("全局搜索打完就按 Enter 打开的是输入的那个词（不被防抖竞态带偏）",
               t28a == "crucial", "opened=%r" % t28a)
        except Exception as e:
            ok("全局搜索打完就按 Enter 打开的是输入的那个词（不被防抖竞态带偏）",
               False, "exception: " + str(e)[:120])

        try:
            # 13b：上一次查询无结果 → 改输入后立刻按 Enter 也不再被静默丢弃
            page28.goto(base, wait_until="load")
            page28.wait_for_timeout(300)
            page28.keyboard.press("/")
            page28.wait_for_timeout(150)
            page28.evaluate(
                """() => { const i = document.querySelector('#searchInput');
                           i.value = 'zzzzqqq'; i.dispatchEvent(new Event('input')); }""")
            page28.wait_for_timeout(350)          # 让防抖触发一次（空结果）
            page28.evaluate(
                """() => { const i = document.querySelector('#searchInput');
                           i.value = 'crucial'; i.dispatchEvent(new Event('input')); }""")
            page28.keyboard.press("Enter")
            page28.wait_for_timeout(400)
            t28b = page28.evaluate(
                "() => { const m = document.querySelector('#wmTitle'); return m ? m.textContent.trim() : null; }")
            ok("上一次查询无结果时，改输入后按 Enter 仍能打开对应词条",
               t28b == "crucial", "opened=%r" % t28b)
        except Exception as e:
            ok("上一次查询无结果时，改输入后按 Enter 仍能打开对应词条",
               False, "exception: " + str(e)[:120])

        try:
            # 13c：词条不在上下文列表（词库页按 K 过滤，从全局搜索打开 C 开头的词）
            page28.goto(base + "#browse", wait_until="load")
            page28.wait_for_timeout(400)
            # 筛选面板默认折叠，字母条被压住：用脚本点击（事件处理器照常触发）
            page28.evaluate(
                """() => { const b = document.querySelector('#letterBar .letter-btn[data-l="K"]');
                           if (b) b.click(); }""")
            page28.wait_for_timeout(400)
            page28.keyboard.press("/")
            page28.wait_for_timeout(150)
            page28.evaluate(
                """() => { const i = document.querySelector('#searchInput');
                           i.value = 'crucial'; i.dispatchEvent(new Event('input')); }""")
            page28.wait_for_timeout(350)
            page28.keyboard.press("Enter")
            page28.wait_for_timeout(400)
            before28 = page28.evaluate(
                "() => { const m = document.querySelector('#wmTitle'); return m ? m.textContent.trim() : null; }")
            nxt28 = page28.evaluate(
                """() => { const bs = [...document.querySelectorAll('#wordModalBody button')];
                           const b = bs.find(x => /最后一条|下一条/.test(x.textContent));
                           return b ? b.disabled : null; }""")
            page28.keyboard.press("ArrowRight")
            page28.wait_for_timeout(350)
            after28 = page28.evaluate(
                "() => { const m = document.querySelector('#wmTitle'); return m ? m.textContent.trim() : null; }")
            ok("词条不在上下文列表时，←/→ 与禁用的翻页按钮保持一致（不跳到无关词）",
               before28 == "crucial" and nxt28 is True and after28 == "crucial",
               "before=%r nextDisabled=%r after=%r" % (before28, nxt28, after28))
        except Exception as e:
            ok("词条不在上下文列表时，←/→ 与禁用的翻页按钮保持一致（不跳到无关词）",
               False, "exception: " + str(e)[:120])
        page28.close()

        # ---------------- 工装·第七轮：前端四处修复的回归守卫 ----------------
        print("== round-7 front-end regressions ==")

        SEED_TMPL = """(() => { try {
          const st = {settings:{theme:'auto',rate:0.95,goal:30,frontShowHint:false,
            autoSpeak:false,autoWrongFav:false,showKeyHint:true,fcLimit:30,swipeGrade:true},
            progress:{}, fav:%s, quizHist:[], days:{}, created:Date.now()};
          localStorage.setItem('wl_state_v1', JSON.stringify(st));
        } catch(e) {} })();"""

        def new_ctx(fav=None):
            """独立上下文 = 独立 localStorage；种子的收藏词数按用例给定。"""
            c = browser.new_context(viewport={"width": 1280, "height": 900})
            c.set_default_navigation_timeout(90000)
            if fav is not None:
                c.add_init_script(SEED_TMPL % json.dumps(fav))
            return c

        # 14a：闪卡完成面板的「换范围」必须真能回到范围选择页
        name_a = "闪卡完成后「换范围」能回到范围选择页（此前是死链，点了纹丝不动）"
        try:
            cA = new_ctx([1, 2]); pA = cA.new_page()
            pA.goto(base + "#cards", wait_until="load")
            pA.wait_for_selector(".deck-opt[data-s='fav']", state="attached")
            pA.click(".deck-opt[data-s='fav']")
            pA.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            pA.wait_for_selector("#flipCard", state="attached")
            for _ in range(4):
                if pA.locator("#againBtn").count():
                    break
                pA.click("#fcReveal")
                pA.wait_for_timeout(200)
                pA.click(".fc-btns .btn[data-q='2']")
                pA.wait_for_timeout(300)
            done = pA.locator("#againBtn").count() > 0
            # 修前这里是一个没有 id 的 <a href="#cards">：用文本+id 双口径选，
            # 好让「修前是死链」表现为断言失配而不是定位超时
            pA.click("a.btn:has-text('换范围'), #changeDeckBtn")
            pA.wait_for_timeout(500)
            back = pA.locator(".deck-opt[data-s='all']").count() > 0
            gone = pA.locator("#againBtn").count() == 0
            ok(name_a, done and back and gone, "done=%r back=%r gone=%r" % (done, back, gone))
            cA.close()
        except Exception as e:
            ok(name_a, False, "exception: " + str(e)[:140])

        # 14b：导入备份后闪卡「每次上限」必须跟着备份走
        name_b = "导入备份后闪卡「每次上限」跟着备份走（设置页与闪卡页不再自相矛盾）"
        try:
            cB = new_ctx(); pB = cB.new_page()
            pB.goto(base + "#settings", wait_until="load")
            pB.wait_for_selector("#impFile", state="attached")
            backup = json.dumps({"settings": {"fcLimit": 7}, "progress": {}, "fav": [],
                                 "quizHist": [], "days": {}, "created": 0})
            pB.set_input_files("#impFile", {"name": "bak.json", "mimeType": "application/json",
                                            "buffer": backup.encode("utf-8")})
            pB.wait_for_timeout(900)
            setv = pB.evaluate(
                "() => { const i = document.querySelector('#fcLimitInput'); return i ? i.value : null; }")
            # 不能整页刷新：刷新后 fc.lastLimit 会从备份重算，测不出「快照不同步」这个病
            file_value = pB.eval_on_selector("#impFile", "i => i.value")
            pB.click("a[data-view='study']")
            pB.wait_for_timeout(700)
            cardv = pB.evaluate(
                "() => { const i = document.querySelector('#fcLimit'); return i ? i.value : null; }")
            ok(name_b, str(setv) == "7" and str(cardv) == "7", "settings=%r cards=%r" % (setv, cardv))
            ok("导入完成后文件框复位（同一备份可再次导入）", file_value == "",
               "input=%r" % file_value)
            cB.close()
        except Exception as e:
            ok(name_b, False, "exception: " + str(e)[:140])

        # 14c：范围变大后，旧的「范围太小」提示必须作废
        name_c = "收藏范围变大后，旧的「范围太小」提示不残留"
        try:
            cC = new_ctx([1, 2]); pC = cC.new_page()
            pC.goto(base + "#fav", wait_until="load")
            pC.wait_for_selector("#favQuiz", state="attached")
            pC.click("#favQuiz")
            pC.wait_for_timeout(600)
            pC.click("#startQuiz")
            pC.wait_for_timeout(600)
            n1 = pC.evaluate(
                "() => [...document.querySelectorAll('.empty-inline')].map(e => e.textContent).join(' | ')")
            # 收藏扩到 7 个词，再从收藏进一次测验（pendingScope 这条路径）
            pC.evaluate("() => { window.WL_DEBUG.state.fav = [1,2,3,4,5,6,7]; }")
            pC.click("a[data-view='fav']")
            pC.wait_for_timeout(600)
            pC.click("#favQuiz")
            pC.wait_for_timeout(700)
            n2 = pC.evaluate(
                "() => [...document.querySelectorAll('.empty-inline')].map(e => e.textContent).join(' | ')")
            ok(name_c, "至少需要 4 个" in n1 and "至少需要 4 个" not in n2,
               "before=%r after=%r" % (n1[:70], n2[:70]))
            cC.close()
        except Exception as e:
            ok(name_c, False, "exception: " + str(e)[:140])

        # 14d：词库与收藏的搜索词互不串台
        name_d = "词库与收藏的搜索互不串台（各搜各的，切换视图不互相清空）"
        try:
            cD = new_ctx([1]); pD = cD.new_page()
            pD.goto(base + "#fav", wait_until="load")
            pD.wait_for_selector("#favBq", state="attached")
            pD.evaluate("""() => { const i = document.querySelector('#favBq');
                                    i.value = 'crucial'; i.dispatchEvent(new Event('input')); }""")
            pD.wait_for_timeout(600)
            pD.click("a[data-view='browse']")
            pD.wait_for_timeout(700)
            lib1 = pD.evaluate("() => { const i = document.querySelector('#bq'); return i ? i.value : null; }")
            pD.evaluate("""() => { const i = document.querySelector('#bq');
                                    i.value = 'crucial'; i.dispatchEvent(new Event('input')); }""")
            pD.wait_for_timeout(600)
            pD.click("a[data-view='fav']")
            pD.wait_for_timeout(600)
            pD.click("a[data-view='browse']")
            pD.wait_for_timeout(700)
            lib2 = pD.evaluate("() => { const i = document.querySelector('#bq'); return i ? i.value : null; }")
            ok(name_d, (lib1 or "") == "" and (lib2 or "") == "crucial", "lib1=%r lib2=%r" % (lib1, lib2))
            cD.close()
        except Exception as e:
            ok(name_d, False, "exception: " + str(e)[:140])

        # 14e：页码与搜索词同属视图状态，进入收藏不得重置词库页的浏览位置
        name_e = "词库页经收藏往返后保留页码与首条词（鼠标/键盘翻页共用视图页码）"
        try:
            cE = new_ctx([1]); pE = cE.new_page()
            pE.goto(base + "#browse", wait_until="load")
            pE.wait_for_selector("#browsePager [data-p='next']", state="attached")
            pE.click("#browsePager [data-p='next']")
            pE.wait_for_timeout(350)
            before_page = pE.locator("#browsePager [aria-current='page']").inner_text()
            before_word = pE.locator(".word-table tbody tr").first.get_attribute("data-num")
            pE.click("a[data-view='fav']")
            pE.wait_for_timeout(350)
            pE.click("a[data-view='browse']")
            pE.wait_for_timeout(350)
            after_page = pE.locator("#browsePager [aria-current='page']").inner_text()
            after_word = pE.locator(".word-table tbody tr").first.get_attribute("data-num")
            pE.click("#browsePager [data-p='prev']")
            pE.wait_for_timeout(250)
            prev_page = pE.locator("#browsePager [aria-current='page']").inner_text()
            pE.keyboard.press("ArrowRight")
            pE.wait_for_timeout(250)
            key_page = pE.locator("#browsePager [aria-current='page']").inner_text()
            ok(name_e, before_page == after_page == key_page == "2" and
               before_word == after_word and prev_page == "1",
               "before=%r after=%r prev=%r key=%r first=%r/%r" %
               (before_page, after_page, prev_page, key_page, before_word, after_word))
            cE.close()
        except Exception as e:
            ok(name_e, False, "exception: " + str(e)[:140])

        # 14f：导入 / 重置必须作废旧测验，不能由最后一题的反馈页复活已清数据
        def prepare_answered_quiz(p):
            p.goto(base + "#study", wait_until="load")
            p.click('#studyModeSeg button[data-m="quiz"]')
            p.click("#startQuiz")
            p.wait_for_selector(".quiz-opt")
            # 缩短为一题，但保留真实的作答、评分与反馈路径。
            p.evaluate("""() => { const q = WL_DEBUG.quiz;
              q.queue = q.queue.slice(0, 1); q.i = 0; WL_DEBUG.renderQuizQuestion(); }""")
            p.wait_for_selector(".quiz-opt")
            p.evaluate("document.querySelector('.quiz-opt').click()")
            p.wait_for_selector("#qNext")
            p.click("a[data-view='settings']")
            p.wait_for_selector("#impFile", state="attached")

        for action in ("resetProg", "resetAll", "import"):
            name_f = "旧测验在 %s 后彻底失效，不能写回已清历史" % action
            try:
                cF = new_ctx(); pF = cF.new_page()
                prepare_answered_quiz(pF)
                if action == "import":
                    backup = json.dumps({"settings": {}, "progress": {}, "fav": [],
                                         "quizHist": [], "days": {}, "created": 0})
                    pF.set_input_files("#impFile", {"name": "empty.json", "mimeType": "application/json",
                                                    "buffer": backup.encode("utf-8")})
                    pF.wait_for_timeout(500)
                else:
                    pF.once("dialog", lambda d: d.accept())
                    pF.click("#" + action)
                    pF.wait_for_timeout(250)
                pF.click("a[data-view='study']")
                pF.wait_for_selector(".quiz-setup")
                snapshot = pF.evaluate("""() => ({
                  session: WL_DEBUG.quiz.session, fb: WL_DEBUG.quiz.fb,
                  queue: WL_DEBUG.quiz.queue.length,
                  hist: WL_DEBUG.state.quizHist.length,
                  progress: Object.keys(WL_DEBUG.state.progress).length,
                  feedback: !!document.querySelector('.quiz-feedback.show')
                })""")
                ok(name_f, snapshot == {"session": 0, "fb": None, "queue": 0,
                                        "hist": 0, "progress": 0, "feedback": False}, str(snapshot))
                cF.close()
            except Exception as e:
                ok(name_f, False, "exception: " + str(e)[:140])

        # 14g：旧翻卡会话同样不得穿过重置继续评分
        name_g = "重置进度后旧翻卡会话作废，返回学习只见牌组设置"
        try:
            cG = new_ctx(); pG = cG.new_page()
            pG.goto(base + "#study", wait_until="load")
            pG.click(".deck-opt[data-s='all']")
            pG.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            pG.wait_for_selector("#flipCard")
            pG.click("a[data-view='settings']")
            pG.once("dialog", lambda d: d.accept())
            pG.click("#resetProg")
            pG.click("a[data-view='study']")
            pG.wait_for_selector(".deck-setup")
            card_state = pG.evaluate("""() => ({session: WL_DEBUG.fc.session,
              queue: WL_DEBUG.fc.queue.length, card: !!document.querySelector('#flipCard'),
              progress: Object.keys(WL_DEBUG.state.progress).length})""")
            ok(name_g, card_state == {"session": 0, "queue": 0, "card": False, "progress": 0}, str(card_state))
            cG.close()
        except Exception as e:
            ok(name_g, False, "exception: " + str(e)[:140])

        # 14h：卡内按钮与 details 的 Enter/Space 走原生激活，不被卡面翻页截走
        name_h = "卡内朗读、展开例句、手动标记均可用键盘激活"
        try:
            cH = new_ctx()
            cH.add_init_script("""
              window.__kbSpoken = [];
              const voice = {name:'Keyboard English', lang:'en-US'};
              const synth = {getVoices:() => [voice], cancel:() => {}, onvoiceschanged:null,
                speak:u => window.__kbSpoken.push(u.text)};
              Object.defineProperty(window, 'speechSynthesis', {value:synth, configurable:true});
              window.SpeechSynthesisUtterance = class {
                constructor(text) { this.text = String(text); this.voice = null; this.lang = ''; this.rate = 1; }
              };
            """)
            pH = cH.new_page()
            pH.goto(base + "#study", wait_until="load")
            pH.click(".deck-opt[data-s='all']")
            pH.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            pH.locator("#fcSpeak").focus()
            pH.keyboard.press("Enter")
            pH.wait_for_timeout(120)
            speak_state = pH.evaluate("""() => ({spoken: WL_DEBUG.speakCount,
              flipped: document.querySelector('#flipCard').classList.contains('flipped')})""")
            pH.click("#fcReveal")
            pH.locator(".fc-ex-more summary").focus()
            pH.keyboard.press("Enter")
            pH.wait_for_timeout(120)
            detail_state = pH.evaluate("""() => { const d = document.querySelector('.fc-ex-more');
              const visible = s => getComputedStyle(document.querySelector(s)).display !== 'none';
              return {open:d.open, flipped:document.querySelector('#flipCard').classList.contains('flipped'),
                closedVisible:visible('.fc-ex-more-closed'), openVisible:visible('.fc-ex-more-open')}; }""")
            pH.locator(".fc-mark-btn[data-mk='mastered']").focus()
            pH.keyboard.press("Enter")
            pH.wait_for_timeout(120)
            mark_state = pH.evaluate("""() => { const n = WL_DEBUG.fc.queue[WL_DEBUG.fc.i].num;
              return {lv:(WL_DEBUG.prog(n) || {}).lv,
                flipped:document.querySelector('#flipCard').classList.contains('flipped')}; }""")
            ok(name_h, speak_state == {"spoken": 1, "flipped": False}
               and detail_state == {"open": True, "flipped": True,
                                    "closedVisible": False, "openVisible": True}
               and mark_state == {"lv": 5, "flipped": True},
               "speak=%r detail=%r mark=%r" % (speak_state, detail_state, mark_state))
            cH.close()
        except Exception as e:
            ok(name_h, False, "exception: " + str(e)[:140])

        # 14i：首页状态卡跳词库时先退出收藏上下文，再重置真正的词库页码
        name_i = "从收藏回首页再点已掌握，词库从第一页开始"
        try:
            cI = new_ctx(); pI = cI.new_page()
            pI.goto(base, wait_until="load")
            pI.evaluate("() => { WL_WORDS.slice(0, 60).forEach(w => WL_DEBUG.setStatus(w.num, 'mastered')); }")
            pI.click("a[data-view='browse']")
            pI.select_option("#bstatus", "mastered")
            pI.wait_for_selector("#browsePager [data-p='next']", state="attached")
            pI.click("#browsePager [data-p='next']")
            pI.click("a[data-view='fav']")
            pI.click("a[data-view='home']")
            pI.click(".stat-card[data-goto='mastered']")
            pI.wait_for_selector("#browsePager [aria-current='page']", state="attached")
            page_i = pI.locator("#browsePager [aria-current='page']").inner_text()
            count_i = pI.locator(".count-line b").first.inner_text()
            ok(name_i, page_i == "1" and count_i == "60", "page=%r count=%r" % (page_i, count_i))
            cI.close()
        except Exception as e:
            ok(name_i, False, "exception: " + str(e)[:140])

        # 14j：累计评分按 seen 计，模糊不再从总数里消失；正确率分母仍是对错次数
        name_j = "一次模糊评分计入累计答题 / 评分次数"
        try:
            cJ = new_ctx(); pJ = cJ.new_page()
            pJ.goto(base + "#study", wait_until="load")
            pJ.click(".deck-opt[data-s='all']")
            pJ.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            pJ.click("#fcReveal")
            pJ.click(".fc-btns .btn[data-q='1']")
            pJ.click("a[data-view='stats']")
            pJ.wait_for_selector(".donut-row")
            stat_text = pJ.evaluate("""() => [...document.querySelectorAll('p')]
              .map(e => e.textContent).find(t => t.includes('累计答题 / 评分')) || ''""")
            seen = pJ.evaluate("Object.values(WL_DEBUG.state.progress).reduce((n,p) => n + (p.seen || 0), 0)")
            ok(name_j, seen == 1 and "累计答题 / 评分 1 次" in stat_text,
               "seen=%r text=%r" % (seen, stat_text))
            cJ.close()
        except Exception as e:
            ok(name_j, False, "exception: " + str(e)[:140])

        # 14k：两步流端到端——chip 选中（不开卡）→ 换选 → 摘要跟着走 → 确认后
        #      开出的就是最后选中的范围。此前点 chip 立即开局，无「选择→确认」可言。
        name_k = "两步流：选中只高亮、摘要随换选更新、确认开出的是最后选中的范围"
        try:
            cK = new_ctx(); pK = cK.new_page()
            pK.goto(base + "#study", wait_until="load")
            pK.wait_for_selector(".deck-opt[data-s='all']")
            pK.click(".deck-opt[data-s='learning']")          # 选中「学习中」：不开卡
            sel = pK.evaluate("""() => ({
              still: !!document.querySelector('.deck-setup'),
              learningOn: document.querySelector(".deck-opt[data-s='learning']").getAttribute('aria-pressed'),
              summary: document.querySelector('#fcSummary').innerText})""")
            ok(name_k + " ①", sel["still"] and sel["learningOn"] == "true"
               and "学习中" in sel["summary"], str(sel)[:120])
            pK.click(".deck-opt[data-s='all']")               # 换选「全部词库」
            sel2 = pK.evaluate("""() => ({
              allOn: document.querySelector(".deck-opt[data-s='all']").getAttribute('aria-pressed'),
              learnOff: document.querySelector(".deck-opt[data-s='learning']").getAttribute('aria-pressed'),
              summary: document.querySelector('#fcSummary').innerText})""")
            ok(name_k + " ②", sel2["allOn"] == "true" and sel2["learnOff"] == "false"
               and "全部词库" in sel2["summary"], str(sel2)[:120])
            pK.click("#fcStart")                              # 确认
            pK.wait_for_selector("#flipCard")
            got = pK.evaluate("() => document.querySelector('.fc-progress span').innerText.trim()")
            ok(name_k + " ③", "全部词库" in got, got)
            cK.close()
        except Exception as e:
            ok(name_k, False, "exception: " + str(e)[:140])

        # 14l：设置页「恢复默认」——只回拨九个设置项，学习数据原样保留；
        #      fc.lastLimit（学习页建牌组的唯一真相）必须跟着默认值走，不留在旧上限。
        name_l = "恢复默认设置：九项回默认、学习数据保留、学习页上限同步"
        try:
            cL = new_ctx(); pL = cL.new_page()
            pL.on("dialog", lambda d: d.accept())
            # 种子：设置改得面目全非 + 学习数据（进度/收藏/测验史）在场
            pL.add_init_script("""(() => { try {
              const st = JSON.parse(localStorage.getItem('wl_state_v1') || '{}');
              st.settings = {theme:'light', rate:0.5, goal:200, frontShowHint:true,
                autoSpeak:true, autoWrongFav:true, showKeyHint:false, fcLimit:88, swipeGrade:false};
              st.progress = {5:{lv:3,due:0,seen:4,correct:3,wrong:1,last:1}};
              st.fav = [7, 9]; st.quizHist = [{t:1, mode:'choice', scope:'all', score:8, total:10}];
              localStorage.setItem('wl_state_v1', JSON.stringify(st));
            } catch(e) {} })();""")
            pL.goto(base + "#settings", wait_until="load")
            pL.wait_for_selector("#resetSettings")
            # 种子生效自检：改乱的设置真的在页上（light 主题 + 0.5 语速）
            seeded = pL.evaluate("""() => ({
              theme: document.documentElement.dataset.theme,
              rate: document.querySelector('#rateVal').textContent.trim(),
              limit: document.querySelector('#fcLimitInput').value})""")
            ok(name_l + " ①种子生效", seeded["theme"] == "light" and seeded["rate"] == "0.50"
               and seeded["limit"] == "88", str(seeded))
            pL.click("#resetSettings")                        # confirm 由上面的 handler 自动接受
            pL.wait_for_timeout(400)
            after = pL.evaluate("""() => {
              const s = JSON.parse(localStorage.getItem('wl_state_v1'));
              return { settings: s.settings, favN: s.fav.length, quizN: s.quizHist.length,
                       prog5: s.progress['5'] ? s.progress['5'].lv : null } }""")
            d = pL.evaluate("() => WL_DEBUG.DEFAULTS.settings")
            same = all(str(after["settings"][k]) == str(d[k]) for k in d)
            ok(name_l + " ②九项全回默认", same,
               "after=" + json.dumps(after["settings"], ensure_ascii=False) + " def=" + json.dumps(d))
            ok(name_l + " ③学习数据原样", after["favN"] == 2 and after["quizN"] == 1
               and after["prog5"] == 3, str({k: after[k] for k in ("favN", "quizN", "prog5")}))
            # 学习页镜像同步：上限输入框读的是 fc.lastLimit，必须也是默认值（不是旧 88）
            pL.goto(base + "#study", wait_until="load")
            pL.wait_for_selector("#fcLimit", state="attached")
            study_limit = pL.evaluate("() => document.querySelector('#fcLimit').value")
            ok(name_l + " ④学习页上限同步", study_limit == str(d["fcLimit"]),
               f"study={study_limit} default={d['fcLimit']}")
            cL.close()
        except Exception as e:
            ok(name_l, False, "exception: " + str(e)[:140])

        print("== overall ==")
        ok("no JS errors during extended run", not errors, "; ".join(errors[:5]))
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
