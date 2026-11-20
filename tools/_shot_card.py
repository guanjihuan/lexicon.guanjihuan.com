# -*- coding: utf-8 -*-
"""临时脚本：翻卡页新卡面的截图（跑完即弃）。"""
import os, sys, io, time, functools, http.server, socketserver
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
port = srv.server_address[1]
threading = __import__('threading')
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
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(base + "#study", wait_until="load")
    page.wait_for_timeout(600)
    page.click('#studyModeSeg button[data-m="flashcards"]')
    page.wait_for_timeout(400)
    page.click('.chip[data-s="all"]')
    page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
    page.wait_for_timeout(900)
    page.screenshot(path="tools/_shots/card_front.png", full_page=True)
    page.click("#fcReveal")
    page.wait_for_timeout(900)
    page.screenshot(path="tools/_shots/card_back.png", full_page=True)
    info = page.evaluate("""()=>{
      const c=document.querySelector('.flip-card');
      const back=document.querySelector('.flip-back');
      const b=document.querySelector('.fc-body');
      const mr=document.querySelector('.fc-mark-row');
      const r=e=>{const b=e.getBoundingClientRect();return {t:Math.round(b.top),b:Math.round(b.bottom),h:Math.round(b.height),w:Math.round(b.width)};};
      return {card:r(c), back:r(back), body:r(b), mark:r(mr),
              backScrollH: back.scrollHeight, backClientH: back.clientHeight,
              overflow: back.scrollHeight - back.clientHeight,
              docH: document.documentElement.scrollHeight};
    }""")
    print(info)
    print("errors:", errs)
    browser.close()
srv.shutdown()
