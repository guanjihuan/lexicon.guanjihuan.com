# -*- coding: utf-8 -*-
"""临时脚本：学习页设置面板（改名后的模式卡）截图。"""
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
    page.goto(base + "#study", wait_until="load")
    page.wait_for_timeout(900)
    page.screenshot(path="tools/_shots/study_setup.png", full_page=True)
    browser.close()
srv.shutdown()
