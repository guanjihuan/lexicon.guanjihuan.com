#!/usr/bin/env python3
"""发音口径回归：没有英语音色不乱读；听力题不在答案出现后自动出声。

不依赖本机安装了哪些语音包：在页面脚本前替换 speechSynthesis，
分别构造「只有中文音色」与「有英语音色」两种环境，记录真实 speak 调用。

用法：python tools/tts_policy_test.py
"""
import functools
import http.server
import json
import os
import socketserver
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []
PASSED = 0


def ok(name, condition, extra=""):
    global PASSED
    print(("  ✓ " if condition else "  ✗ ") + name + (f"  [{extra}]" if extra else ""))
    if condition:
        PASSED += 1
    else:
        FAIL.append(name + " " + extra)


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.2)
    return f"http://127.0.0.1:{port}/"


def voice_stub(voices):
    return """
    (() => {
      const voices = %s;
      window.__spoken = [];
      const synth = {
        getVoices: () => voices,
        speak: u => window.__spoken.push({
          text: u.text, lang: u.lang,
          voice: u.voice ? u.voice.name : null,
          voiceLang: u.voice ? u.voice.lang : null
        }),
        cancel: () => {}, onvoiceschanged: null
      };
      Object.defineProperty(window, 'speechSynthesis', {value: synth, configurable: true});
      window.__setVoices = next => {
        voices.splice(0, voices.length, ...next);
        if (typeof synth.onvoiceschanged === 'function') synth.onvoiceschanged();
      };
      window.SpeechSynthesisUtterance = class {
        constructor(text) { this.text = String(text); this.voice = null; this.lang = ''; this.rate = 1; }
      };
    })();
    """ % json.dumps(voices, ensure_ascii=False)


def manual_replay_timers(page):
    """把 150ms 读题定时器收进手动队列，排除机器负载造成的竞态假红。"""
    page.evaluate("""
      window.__replayTimers = new Map(); window.__replayId = 1;
      window.__realSetTimeout = window.setTimeout.bind(window);
      window.__realClearTimeout = window.clearTimeout.bind(window);
      window.setTimeout = function(fn, ms, ...args) {
        if (ms === 150) { const id = window.__replayId++; window.__replayTimers.set(id, fn); return id; }
        return window.__realSetTimeout(fn, ms, ...args);
      };
      window.clearTimeout = function(id) {
        if (window.__replayTimers.has(id)) { window.__replayTimers.delete(id); return; }
        return window.__realClearTimeout(id);
      };
      window.__fireReplays = () => {
        const pending = window.__replayTimers;
        window.__replayTimers = new Map();
        pending.forEach(fn => fn());
        return pending.size;
      };
    """)


def open_quiz(page, mode):
    page.click('.nav-item[data-view="study"]')
    page.wait_for_selector("#studyModeSeg")
    page.click('#studyModeSeg button[data-m="quiz"]')
    page.wait_for_selector(".quiz-setup")
    page.click(f'.chip[data-m="{mode}"]')


def main():
    from playwright.sync_api import sync_playwright
    base = serve()
    with sync_playwright() as pw:
        exe = os.environ.get("WL_CHROMIUM")
        try:
            browser = pw.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}))
        except Exception:
            browser = pw.chromium.launch(headless=True, channel="chromium")

        print("== 只有中文音色：绝不拿中文音色读英文 ==")
        ctx = browser.new_context()
        ctx.add_init_script(voice_stub([
            {"name": "Microsoft Huihui", "lang": "zh-CN"},
            {"name": "Microsoft Yaoyao", "lang": "zh-CN"},
        ]))
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base, wait_until="load")
        page.click('.nav-item[data-view="browse"]')
        page.click('.mini-btn[data-act="speak"]')
        page.wait_for_timeout(100)
        ok("clicking read-aloud with only zh-CN voices produces no utterance",
           page.evaluate("window.__spoken.length") == 0,
           json.dumps(page.evaluate("window.__spoken"), ensure_ascii=False))
        ok("the refusal explains the missing English voice pack",
           "英语语音包" in page.locator("#toastWrap").inner_text())
        page.click('.nav-item[data-view="settings"]')
        page.wait_for_selector("#rateRange")
        ok("settings explains how to install an English voice",
           "时间和语言" in page.locator("#main").inner_text())
        open_quiz(page, "mix")
        ok("listen mode is disabled without an English voice",
           page.locator('.chip[data-m="listen"]').is_disabled())
        ok("quiz setup reports missing English voices, not missing Web Speech API",
           "未检测到英语语音包" in page.locator(".quiz-setup").inner_text())
        page.click('.chip[data-m="30"]') if page.locator('.chip[data-m="30"]').count() else None
        page.click("#startQuiz")
        page.wait_for_selector(".quiz-card")
        modes = []
        for _ in range(10):
            modes.append(page.locator(".quiz-mode-badge").inner_text())
            if page.locator("#qSkip").count() == 0:
                break
            page.click("#qSkip")
            page.wait_for_timeout(30)
            if page.locator(".quiz-result").count():
                break
        ok("mixed quiz never emits an unusable listen question",
           all("听音辨词" not in m for m in modes), " / ".join(modes[:4]))
        ok("no-English-voice scenario raises no JS errors", not errors, " | ".join(errors[:2]))
        ctx.close()

        print("== 有英语音色：明确绑定音色，作答后不再自动读 ==")
        ctx = browser.new_context()
        ctx.add_init_script(voice_stub([{"name": "Test US English", "lang": "en-US"}]))
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base, wait_until="load")
        page.click('.nav-item[data-view="browse"]')
        page.click('.mini-btn[data-act="speak"]')
        spoken = page.evaluate("window.__spoken")
        ok("manual read-aloud explicitly binds the English voice",
           len(spoken) == 1 and spoken[0]["voice"] == "Test US English"
           and spoken[0]["voiceLang"] == "en-US" and spoken[0]["lang"] == "en-US",
           json.dumps(spoken, ensure_ascii=False))

        manual_replay_timers(page)
        open_quiz(page, "listen")
        page.click("#startQuiz")
        page.wait_for_selector(".quiz-card")
        ok("a fresh listen question schedules exactly one read-aloud",
           page.evaluate("window.__replayTimers.size") == 1)
        page.evaluate("document.querySelector('.quiz-opt').click()")
        ok("answering before 150ms cancels the pending read-aloud",
           page.evaluate("window.__fireReplays()") == 0
           and page.evaluate("window.__spoken.length") == 1,  # 只有前面手动点的朗读
           json.dumps(page.evaluate("window.__spoken"), ensure_ascii=False))

        # 开下一场新听力题，先手动发射读题，再作答、离开、回来。
        page.click("#qQuit")
        page.wait_for_selector(".quiz-setup")
        page.evaluate("window.__spoken = []")
        page.click('.chip[data-m="listen"]')
        page.click("#startQuiz")
        page.wait_for_selector(".quiz-card")
        ok("the new listen question replays once on demand",
           page.evaluate("window.__fireReplays()") == 1
           and page.evaluate("window.__spoken.length") == 1)
        page.evaluate("document.querySelector('.quiz-opt').click()")
        page.wait_for_selector(".quiz-feedback.show")
        page.click('.nav-item[data-view="home"]')
        page.click('.nav-item[data-view="study"]')
        page.wait_for_selector(".quiz-feedback.show")
        ok("resuming an answered listen question schedules no automatic replay",
           page.evaluate("window.__fireReplays()") == 0
           and page.evaluate("window.__spoken.length") == 1,
           json.dumps(page.evaluate("window.__spoken"), ensure_ascii=False))
        # 已答听力题在音色消失后仍是同一张历史题：题干与选项语义不能错位。
        page.click('.nav-item[data-view="home"]')
        page.evaluate("window.__setVoices([])")
        page.click('.nav-item[data-view="study"]')
        page.wait_for_selector(".quiz-feedback.show")
        ok("resuming answered listen feedback without voices keeps listen prompt and word options",
           "听音辨词" in page.locator(".quiz-mode-badge").inner_text()
           and page.locator("#qReplay").count() == 1
           and page.locator("#qSpeak").count() == 0
           and page.locator(".quiz-opt").count() == 4,
           page.locator(".quiz-card").inner_text()[:180])
        ok("voice loss during answered feedback does not schedule a replay",
           page.evaluate("window.__fireReplays()") == 0
           and page.evaluate("window.__spoken.length") == 1)
        ok("English-voice scenario raises no JS errors", not errors, " | ".join(errors[:2]))
        ctx.close()

        print("== 音色异步到达：已渲染的出题设置立即解锁 ==")
        ctx = browser.new_context()
        ctx.add_init_script(voice_stub([]))
        page = ctx.new_page()
        page.goto(base, wait_until="load")
        open_quiz(page, "mix")
        disabled_before = page.locator('.chip[data-m="listen"]').is_disabled()
        page.evaluate("window.__setVoices([{name:'Late English', lang:'en-GB'}])")
        page.wait_for_function("!document.querySelector('.chip[data-m=listen]').disabled")
        ok("voiceschanged re-renders quiz setup and enables listen immediately",
           disabled_before and page.locator('.chip[data-m="listen"]').is_enabled()
           and "未检测到英语语音包" not in page.locator(".quiz-setup").inner_text())
        ctx.close()
        browser.close()

    print(f"\nRESULT: {'ALL TESTS PASSED' if not FAIL else 'FAILED'}")
    print(f"({PASSED} checks passed, {len(FAIL)} failed)")
    for item in FAIL:
        print("  FAIL:", item)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
