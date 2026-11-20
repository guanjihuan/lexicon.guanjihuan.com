# -*- coding: utf-8 -*-
"""临时脚本：窄屏（375px）卡背截图与溢出检查。"""
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
    for w, h, tag in ((375, 800, "narrow"), (768, 1000, "mid")):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(base + "#study", wait_until="load")
        page.wait_for_timeout(500)
        page.click('.chip[data-s="all"]')
        page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
        page.wait_for_timeout(900)
        page.click("#fcReveal")
        page.wait_for_timeout(1000)
        page.screenshot(path=f"tools/_shots/card_{tag}.png", full_page=True)
        info = page.evaluate("""()=>{
          const c=document.querySelector('.flip-card');
          const back=document.querySelector('.flip-back');
          const inner=document.querySelector('.fc-back-inner');
          const body=document.querySelector('.fc-body');
          const r=e=>{const b=e.getBoundingClientRect();return {t:Math.round(b.top),h:Math.round(b.height),w:Math.round(b.width)};};
          return {card:r(c), inner:r(inner), body:r(body),
                  cols: getComputedStyle(body).gridTemplateColumns,
                  backOverflow: back.scrollHeight-back.clientHeight,
                  docOverflowX: document.documentElement.scrollWidth-document.documentElement.clientWidth,
                  cardInline: c.style.height};
        }""")
        print(tag, info, "errors:", errs)
        ctx.close()
    browser.close()
srv.shutdown()
