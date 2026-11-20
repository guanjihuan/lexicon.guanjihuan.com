#!/usr/bin/env python3
"""焦点保全守卫（工装·第十一轮）——整块重渲染不得把焦点甩回 <body>。

背景（界面窗 93d280 报出，本窗在 Chromium 上直验）：测验/闪卡都靠
`root.innerHTML = html` 整块重画，重画会销毁被聚焦的元素，Chromium 于是把焦点
甩回 <body>：键盘用户失去位置，读屏用户也听不到新内容（新题/新卡对读屏是静默的）。

本守卫逐个量「重渲染之后焦点落在哪儿」，判据是**必须落到明确的新内容上**，
且每条断言都要求「先量到东西再判过」（防空过——量不到焦点就判红，不许静默跳过）。

用法：python3 tools/focus_test.py [--base URL]
依赖：playwright + WL_CHROMIUM。
"""
import argparse, sys, threading, functools, http.server, socketserver, os, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAIL = []
PASSED = 0


def ok(name, cond, extra=""):
    global PASSED
    print(("  ✓ " if cond else "  ✗ ") + name + (f"  [{extra}]" if extra else ""))
    if not cond:
        FAIL.append(name + " " + extra)
    else:
        PASSED += 1


# 一次量出「焦点在哪、是不是 body、题干/卡片是否可聚焦」
PROBE = r"""() => {
  const a = document.activeElement;
  const p = document.querySelector('#qPrompt');
  const c = document.querySelector('#flipCard');
  const inp = document.querySelector('#spellInput');
  return {
    active: a ? (a.id || (a.tagName + (a.className ? '.' + String(a.className).split(' ')[0] : ''))) : 'null',
    body: a === document.body,
    promptText: p ? (p.textContent || '').replace(/\s+/g, ' ').trim() : '',
    promptTabindex: p ? p.getAttribute('tabindex') : null,
    cardPresent: !!c,
    spellDescribedBy: inp ? (inp.getAttribute('aria-describedby') || '') : '',
    spellFocus: inp ? (document.activeElement === inp) : false,
  };
}"""


def _launch(pw):
    """挑一个能用的 Chromium：先 WL_CHROMIUM，再本机常见路径，最后 channel 兜底。"""
    cands = []
    exe = os.environ.get("WL_CHROMIUM")
    if exe:
        cands.append(exe)
    cands += [
        "/home/ubuntu/.cache/ms-playwright/chromium-1155/chrome-linux/chrome",
        "/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome",
    ]
    for c in cands:
        if not c or not os.path.exists(c):
            continue
        try:
            return pw.chromium.launch(headless=True, args=["--no-sandbox"], executable_path=c)
        except Exception:
            continue
    return pw.chromium.launch(headless=True, channel="chromium")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    base = args.base
    if not base:
        os.chdir(ROOT)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        socketserver.TCPServer.allow_reuse_address = True
        # 线程化：浏览器并行拉 data.js / examples.js 等大文件，单线程会串行排队
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}/"
        time.sleep(0.3)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = _launch(pw)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.set_default_navigation_timeout(90000)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # ── 测验 ──────────────────────────────────────────────────────────
        page.goto(base + "#quiz", wait_until="load")
        page.wait_for_selector("#startQuiz")
        page.click("#startQuiz")
        page.wait_for_selector("#qPrompt")
        page.wait_for_timeout(150)
        st = page.evaluate(PROBE)
        ok("测验开始后焦点落在题干（不是 body）",
           (not st["body"]) and st["active"] == "qPrompt", str(st.get("active")))
        ok("题干可编程聚焦但不进 Tab 序列（tabindex=-1）",
           st["promptTabindex"] == "-1", str(st.get("promptTabindex")))
        ok("量到题干文字（判据未空转）", bool(st["promptText"]), st["promptText"][:24])

        # 作答 → 反馈出现 → 焦点交给「下一题」
        page.locator(".quiz-opt").first.click()
        page.wait_for_selector("#qFb.show")
        page.wait_for_timeout(150)
        st2 = page.evaluate(PROBE)
        ok("作答后焦点落在「下一题」按钮（不是 body）",
           (not st2["body"]) and st2["active"] == "qNext", str(st2.get("active")))

        # 下一题 → 新题渲染 → 焦点交给新题干
        prev_text = st2["promptText"]
        page.click("#qNext")
        page.wait_for_selector("#qPrompt")
        page.wait_for_timeout(150)
        st3 = page.evaluate(PROBE)
        ok("下一题后焦点落在新题干（不是 body）",
           (not st3["body"]) and st3["active"] == "qPrompt", str(st3.get("active")))
        ok("新题干有内容（判据未空转）", bool(st3["promptText"]), st3["promptText"][:24])
        ok("下一题后题干确实换了内容", st3["promptText"] != prev_text,
           f"{prev_text[:14]} -> {st3['promptText'][:14]}")
        page.click("#qQuit")
        page.wait_for_timeout(150)

        # ── 拼写题：焦点留在输入框，题干经 aria-describedby 关联 ─────────
        page.click('#qModes .chip[data-m="spell"]')
        page.wait_for_timeout(150)
        page.click("#startQuiz")
        page.wait_for_selector("#spellInput")
        page.wait_for_timeout(150)
        st4 = page.evaluate(PROBE)
        ok("拼写题焦点落在输入框", st4["spellFocus"], str(st4.get("active")))
        ok("拼写题题干由 aria-describedby 关联（读屏能听到题意）",
           bool(st4["spellDescribedBy"]), st4["spellDescribedBy"])
        page.click("#qQuit")
        page.wait_for_timeout(150)

        # ── 闪卡 ──────────────────────────────────────────────────────────
        page.goto(base + "#cards", wait_until="load")
        page.wait_for_selector('.chip[data-s="all"]')
        page.click('.chip[data-s="all"]')
        page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page.wait_for_selector("#flipCard")
        page.wait_for_timeout(200)
        st5 = page.evaluate(PROBE)
        ok("闪卡开场后焦点落在卡片（不是 body）",
           (not st5["body"]) and st5["active"] == "flipCard", str(st5.get("active")))

        page.click("#fcReveal")          # 翻面（评分前必须先翻面）
        page.wait_for_timeout(300)
        page.click(".fc-btns .btn.good")  # 评分 → 整块重渲染
        page.wait_for_selector("#flipCard")
        page.wait_for_timeout(250)
        st6 = page.evaluate(PROBE)
        ok("闪卡评分后焦点落回新卡片（不是 body）",
           (not st6["body"]) and st6["active"] == "flipCard", str(st6.get("active")))
        ok("量到卡片元素（判据未空转）", st6["cardPresent"], str(st6.get("cardPresent")))

        ok("全程无 JS 报错", not errors, "; ".join(errors[:2]))
        browser.close()

    print()
    if FAIL:
        print(f"RESULT: {len(FAIL)} of {PASSED + len(FAIL)} checks FAILED")
        for f in FAIL:
            print("  - " + f)
        return 1
    print(f"RESULT: ALL TESTS PASSED ({PASSED} checks)")
    return 0


# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    sys.exit(main())
