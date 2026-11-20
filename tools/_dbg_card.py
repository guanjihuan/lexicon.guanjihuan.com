# -*- coding: utf-8 -*-
"""临时脚本：调试卡背量高。"""
import os, sys, io, time, functools, http.server, socketserver, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.3)
base = f"http://127.0.0.1:{port}/index.html"

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    exe = os.environ.get('WL_CHROMIUM')
    try:
        browser = pw.chromium.launch(headless=True, **({'executable_path': exe} if exe else {}))
    except Exception:
        browser = pw.chromium.launch(headless=True, channel="chromium")
    ctx = browser.new_context(viewport={"width": 1280, "height": 1000})
    page = ctx.new_page()
    page.on("console", lambda m: print("CONSOLE:", m.text))
    page.on("pageerror", lambda e: print("PAGEERROR:", e))
    page.goto(base + "#study", wait_until="load")
    page.wait_for_timeout(500)
    page.click('.chip[data-s="all"]')
    page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
    page.wait_for_timeout(900)
    page.click("#fcReveal")
    page.wait_for_timeout(1200)
    info = page.evaluate("""()=>{
      const c=document.querySelector('.flipCard')||document.querySelector('.flip-card');
      const inner=document.querySelector('.fc-back-inner');
      const r=e=>{const b=e.getBoundingClientRect();return {t:Math.round(b.top),h:Math.round(b.height),w:Math.round(b.width)};};
      return {inlineH: c.style.height, computedH: getComputedStyle(c).height,
              inner: r(inner), card: r(c), innerH: inner.offsetHeight,
              innerScroll: inner.scrollHeight, innerComputed: getComputedStyle(inner).height,
              innerFlex: getComputedStyle(inner).flex, innerParent: getComputedStyle(inner.parentElement).display,
              innerParentAlign: getComputedStyle(inner.parentElement).alignItems};
    }""")
    for k, v in info.items():
        print(k, "=", v)
    browser.close()
srv.shutdown()
