# -*- coding: utf-8 -*-
"""临时脚本：全页面截图体检（跑完即弃）。遍历各视图+主题+搜索+弹层，落盘 PNG 供人工审读。"""
import os, sys, io, time, functools, http.server, socketserver, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
socketserver.ThreadingTCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.3)
base = f"http://127.0.0.1:{port}/index.html"

from playwright.sync_api import sync_playwright

OUT = "tools/_shots/ui"
os.makedirs(OUT, exist_ok=True)

def shot(page, name, full=True):
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    print("shot:", name)

def run(pw):
    exe = os.environ.get('WL_CHROMIUM')
    try:
        browser = pw.chromium.launch(headless=True, **({'executable_path': exe} if exe else {}))
    except Exception:
        browser = pw.chromium.launch(headless=True, channel="chromium")

    for theme in ("dark", "light"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 960})
        if theme == "light":
            ctx.add_init_script("try{localStorage.setItem('wl_state_v1', JSON.stringify({settings:{theme:'light'}}))}catch(e){}")
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:200]))
        page.on("console", lambda m: errs.append("console.error: " + m.text[:200]) if m.type == "error" else None)
        tag = theme

        # 首页
        page.goto(base, wait_until="load")
        page.wait_for_timeout(700)
        shot(page, f"{tag}_home", full=False)
        page.screenshot(path=f"{OUT}/{tag}_home_full.png", full_page=True)
        print("errors so far:", errs)

        # 词库
        page.goto(base + "#browse", wait_until="load")
        page.wait_for_timeout(700)
        shot(page, f"{tag}_browse", full=False)
        page.screenshot(path=f"{OUT}/{tag}_browse_full.png", full_page=True)

        # 学习（设置面板）
        page.goto(base + "#study", wait_until="load")
        page.wait_for_timeout(700)
        shot(page, f"{tag}_study_setup", full=False)
        page.screenshot(path=f"{OUT}/{tag}_study_setup_full.png", full_page=True)

        # 学习会话（两步流：chip 选中 → 确认）
        try:
            page.click(".deck-opt[data-s='all']")
            page.wait_for_timeout(300)
            page.click("#fcStart")
            page.wait_for_timeout(900)
            shot(page, f"{tag}_study_card", full=False)
            # 翻面
            try:
                page.click("#fcReveal", timeout=2000)
                page.wait_for_timeout(700)
                shot(page, f"{tag}_study_card_back", full=False)
            except Exception as e:
                print("reveal fail:", str(e)[:100])
            # 键盘快捷键弹层
            page.keyboard.press("Shift+Slash") if False else None
            page.keyboard.press("?")
            page.wait_for_timeout(400)
            shot(page, f"{tag}_shortcuts", full=False)
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception as e:
            print("study session fail:", str(e)[:200])

        # 收藏
        page.goto(base + "#fav", wait_until="load")
        page.wait_for_timeout(700)
        shot(page, f"{tag}_fav", full=False)
        page.screenshot(path=f"{OUT}/{tag}_fav_full.png", full_page=True)

        # 统计
        page.goto(base + "#stats", wait_until="load")
        page.wait_for_timeout(700)
        shot(page, f"{tag}_stats", full=False)
        page.screenshot(path=f"{OUT}/{tag}_stats_full.png", full_page=True)

        # 设置
        page.goto(base + "#settings", wait_until="load")
        page.wait_for_timeout(700)
        shot(page, f"{tag}_settings", full=False)
        page.screenshot(path=f"{OUT}/{tag}_settings_full.png", full_page=True)

        # 搜索弹层
        page.goto(base + "#home", wait_until="load")
        page.wait_for_timeout(500)
        page.keyboard.press("/")
        page.wait_for_timeout(300)
        page.type("#searchInput", "abandon", delay=40)
        page.wait_for_timeout(700)
        shot(page, f"{tag}_search", full=False)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # 词条详情弹层：从词库点第一张卡
        page.goto(base + "#browse", wait_until="load")
        page.wait_for_timeout(700)
        try:
            page.click(".wcard, .word-card, [data-w]", timeout=3000)
            page.wait_for_timeout(600)
            shot(page, f"{tag}_word_modal", full=False)
            page.keyboard.press("Escape")
        except Exception as e:
            print("modal fail:", str(e)[:150])

        print(f"== {theme} errors ==", errs if errs else "none")
        ctx.close()
    browser.close()

with sync_playwright() as pw:
    run(pw)
print("DONE")
