#!/usr/bin/env python3
"""自适应版面巡检（宽屏 / 窄屏）

跑遍若干视口宽度 × 全部视图，检查三件事：
  ① 横向溢出：文档 scrollWidth 是否超过视口宽度（SC 1.4.10 回流）
  ② 元素越界：哪些可见元素的右边界/左边界跑出视口
  ③ 触控目标：窄屏下可点控件是否 ≥24px（SC 2.5.8）

用法： python3 tools/responsive_audit.py [--shots] [--widths 320,414,...]
"""
import functools
import http.server
import json
import os
import socketserver
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

VIEWS = ["home", "browse", "study", "quiz", "cats", "fav", "stats", "settings"]
WIDTHS = [320, 360, 414, 600, 768, 900, 1024, 1280, 1440, 1700, 1920, 2560]


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


AUDIT_JS = r"""
() => {
  const vw = window.innerWidth;
  const out = { vw, docW: document.documentElement.scrollWidth, over: [], small: [] };
  const seen = new Set();
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
    if (el.closest('.skip-link')) return;   /* 跳转链接故意藏在视口外 */
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    // 越界：右侧超出视口 1px 以上，或左侧为负
    if (r.right > vw + 1 || r.left < -1) {
      const key = el.tagName + '.' + (el.className || '').toString().slice(0, 40);
      if (seen.has(key)) return;
      seen.add(key);
      out.over.push({
        sel: key, left: Math.round(r.left), right: Math.round(r.right),
        w: Math.round(r.width), text: (el.textContent || '').trim().slice(0, 24)
      });
    }
  });
  document.querySelectorAll('button, a[href], input, select, [role=button]').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.height < 24 || r.width < 24) {
      out.small.push({
        sel: el.tagName + '#' + (el.id || '') + '.' + (el.className || '').toString().slice(0, 30),
        w: Math.round(r.width), h: Math.round(r.height),
        text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 20)
      });
    }
  });
  return out;
}
"""


def main():
    shots = "--shots" in sys.argv
    widths = WIDTHS
    if "--widths" in sys.argv:
        i = sys.argv.index("--widths")
        widths = [int(x) for x in sys.argv[i + 1].split(",")]
    srv, port = serve()
    from playwright.sync_api import sync_playwright
    findings = []
    with sync_playwright() as pw:
        exe = os.environ.get("WL_CHROMIUM")
        if exe and not os.path.exists(exe):
            exe = None
        try:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"],
                                        **({"executable_path": exe} if exe else {}))
        except Exception:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"],
                                        channel="chromium")
        for w in widths:
            # 每个宽度单独开页：JS 在首屏按视口宽度决定默认视图（窄屏默认卡片视图），
            # 共用一个页面会拿到「桌面端首屏」的决定，测出来的不是真实窄屏形态。
            page = browser.new_page(viewport={"width": w, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
            page.wait_for_timeout(600)
            for v in VIEWS:
                page.evaluate(f"location.hash = '#{v}'")
                page.wait_for_timeout(350)
                r = page.evaluate(AUDIT_JS)
                if r["docW"] > r["vw"] + 1:
                    findings.append((w, v, "H-SCROLL", f'docW={r["docW"]}', r["over"][:4]))
                for o in r["over"][:6]:
                    findings.append((w, v, "OVERFLOW", json.dumps(o, ensure_ascii=False), []))
                if w <= 768:
                    for s in r["small"][:6]:
                        findings.append((w, v, "SMALL", json.dumps(s, ensure_ascii=False), []))
                if shots:
                    d = os.path.join(ROOT, "tools", "_shots")
                    os.makedirs(d, exist_ok=True)
                    page.screenshot(path=os.path.join(d, f"{v}_{w}.png"), full_page=False)
            page.close()
        browser.close()
    srv.shutdown()
    for w, v, kind, detail, _ in findings:
        print(f"[{kind}] {w}px {v}: {detail}")
    print(f"--- {len(findings)} findings")


if __name__ == "__main__":
    main()
