#!/usr/bin/env python3
"""对比度回归测试（界面自序第三十七轮）

在真实浏览器里量测「文字压在饱和底色上」的对比度：
  · 明暗两套主题各跑一遍，低于 WCAG AA 正文阈值 4.5:1 即失败
  · 另测打印态：深色主题下打印清单的词头必须是黑字（不能继承浅色 --text）

运行： python3 tools/contrast_test.py
依赖： playwright（浏览器路径用 WL_CHROMIUM 指定）
"""
import functools
import http.server
import os
import socketserver
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# ── 被测目标：选择器 → 说明 ──────────────────────────────────────────────
TARGETS = [
    (".nav-item.active", "导航选中态"),
    (".btn-group button.on", "视图切换组选中"),
    (".chip.on", "筛选 chip 选中"),
    (".letter-btn.on", "字母分组选中"),
    (".pager button.on", "分页当前页"),
    (".seg button.on", "设置分段控件选中"),
    (".skip-link", "跳转链接"),
    (".btn.primary", "主按钮"),
    (".hero .btn.primary", "首页主 CTA"),
    (".btn.good", "认识按钮"),
    (".btn.warn", "模糊按钮"),
    (".btn.bad", "忘了按钮"),
    (".fc-btns .btn.good", "闪卡评分·认识"),
    (".fc-btns .btn.warn", "闪卡评分·模糊"),
    (".fc-btns .btn.bad", "闪卡评分·忘了"),
    (".fcss-item.good", "掌握度·好"),
    (".fcss-item.mid", "掌握度·中"),
    (".fcss-item.bad", "掌握度·差"),
    (".danger-zone-strong .l", "清空数据块标题"),
    (".danger-zone-strong .d", "清空数据块说明"),
    (".danger-zone-strong .btn.bad", "清空数据块按钮"),
    (".visit-pill", "访问次数徽标"),
    (".faint", "弱化文字"),
    (".page-sub", "次级说明"),
    (".btn.danger-outline", "危险描边按钮"),
    (".word-table th", "表头"),
    # 第三十九轮新增（bc67bb 转交的残留白字，已实测复现）
    (".brand-logo", "品牌图标"),
    (".quiz-opt.correct .oi", "测验正确序号"),
    (".quiz-opt.wrong .oi", "测验错误序号"),
]

# 悬停态目标：先悬停到 hover_sel，再量测 measure_sel 的实际配色
HOVER_TARGETS = [
    (".quick-btn", ".quick-btn .qb", "快捷入口图标·悬停"),
]

# 窄屏态目标：只在 ≤860px 的视口下出现（.filter-bar 桌面端 display:none）
NARROW_TARGETS = [
    (".filter-toggle .ft-count", "筛选计数徽标·窄屏"),
]

AA = 4.5

MEASURE_JS = r"""
(targets) => {
  const px = (s) => {
    if (!s) return null;
    s = String(s).trim();
    let m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) {
      const p = m[1].split(/[,\s/]+/).filter(Boolean).map(parseFloat);
      if (p.length >= 3) return { c: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 };
    }
    m = s.match(/^color\(srgb ([^)]+)\)$/);
    if (m) {
      const p = m[1].split(/[\s/]+/).filter(Boolean).map(parseFloat);
      if (p.length >= 3) return { c: p.slice(0, 3).map(v => v * 255), a: p.length > 3 ? p[3] : 1 };
    }
    if (s === 'transparent') return { c: [0, 0, 0], a: 0 };
    return null;
  };
  const over = (fg, bg) => {
    const a = fg.a;
    return [0, 1, 2].map(i => fg.c[i] * a + bg.c[i] * (1 - a));
  };
  const lum = (c) => {
    const f = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  };
  const cr = (a, b) => { const l1 = lum(a), l2 = lum(b); const hi = Math.max(l1, l2), lo = Math.min(l1, l2); return (hi + 0.05) / (lo + 0.05); };
  const bgOf = (el) => {
    const stack = [];
    let n = el;
    while (n && n !== document.documentElement) {
      const c = px(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      n = n.parentElement;
    }
    const bodyBg = px(getComputedStyle(document.body).backgroundColor);
    stack.push(bodyBg && bodyBg.a > 0 ? bodyBg : { c: [255, 255, 255], a: 1 });
    let acc = stack.pop().c;
    for (let i = stack.length - 1; i >= 0; i--) acc = over(stack[i], { c: acc, a: 1 });
    return acc;
  };
  const gradTop = (el) => {
    const bi = getComputedStyle(el).backgroundImage;
    const m = bi.match(/color\(srgb [^)]+\)|rgba?\([^)]+\)/);
    return m ? m[0] : null;
  };
  return targets.map(([sel, label]) => {
    const el = document.querySelector(sel);
    if (!el) return { label, sel, missing: true };
    const cs = getComputedStyle(el);
    const fg = px(cs.color);
    if (!fg) return { label, sel, missing: true };
    let bg = bgOf(el);
    if (cs.backgroundImage !== 'none') {
      const g = gradTop(el);
      const gc = g ? px(g) : null;
      if (gc) bg = gc.a < 1 ? over(gc, { c: bg, a: 1 }) : gc.c;
    }
    const fgOver = fg.a < 1 ? over(fg, { c: bg, a: 1 }) : fg.c;
    return { label, sel, ratio: +cr(fgOver, bg).toFixed(2),
             color: cs.color, bg: 'rgb(' + bg.map(v => Math.round(v)).join(',') + ')' };
  });
}
"""


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def main():
    srv, port = serve()
    time.sleep(0.3)
    from playwright.sync_api import sync_playwright

    fails = []
    checked = 0

    def report(r, tag):
        """量测结果记账：低于 AA 记失败。tag 用于区分 桌面/悬停/窄屏。"""
        nonlocal checked
        checked += 1
        if r.get("missing"):
            fails.append(f"[{tag}] {r['label']}：选择器 {r['sel']} 未命中")
            print(f"  ✗ {r['label']:22s} 未命中 {r['sel']}")
            return
        flag = "✓" if r["ratio"] >= AA else "✗"
        print(f"  {flag} {r['label']:22s} {r['ratio']:6.2f}  {r['color']} on {r['bg']}")
        if r["ratio"] < AA:
            fails.append(f"[{tag}] {r['label']}（{r['sel']}）仅 {r['ratio']}:1，低于 {AA}:1")

    with sync_playwright() as pw:
        exe = os.environ.get("WL_CHROMIUM")
        if exe and not os.path.exists(exe):
            exe = None
        try:
            browser = pw.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}))
        except Exception:
            browser = pw.chromium.launch(headless=True, channel="chromium")
        try:
            for theme in ("light", "dark"):
                ctx = browser.new_context(viewport={"width": 1200, "height": 900})
                page = ctx.new_page()
                page.goto(f"http://127.0.0.1:{port}/tools/fixtures/contrast.html", wait_until="load")
                page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
                page.wait_for_timeout(250)
                print(f"== 主题 {theme} ==")
                for r in page.evaluate(MEASURE_JS, TARGETS):
                    report(r, theme)
                # 悬停态：悬停到 hover_sel 后量测其子元素的实际配色
                for hover_sel, measure_sel, label in HOVER_TARGETS:
                    try:
                        page.hover(hover_sel, timeout=3000)
                    except Exception as exc:
                        # 悬停没发生就不能拿静态颜色冒充悬停态通过。
                        checked += 1
                        detail = "[%s/悬停] %s：无法悬停 %s（%s）" % (
                            theme, label, hover_sel, str(exc).splitlines()[0][:120])
                        fails.append(detail)
                        print("  ✗ " + detail)
                        continue
                    page.wait_for_timeout(200)
                    report(page.evaluate(MEASURE_JS, [(measure_sel, label)])[0], theme + "/悬停")
                ctx.close()

            # 窄屏态（≤860px 才出现的元素，如筛选条计数徽标）
            for theme in ("light", "dark"):
                ctx = browser.new_context(viewport={"width": 800, "height": 900})
                page = ctx.new_page()
                page.goto(f"http://127.0.0.1:{port}/tools/fixtures/contrast.html", wait_until="load")
                page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
                page.wait_for_timeout(250)
                print(f"== 主题 {theme}（窄屏 800px） ==")
                for r in page.evaluate(MEASURE_JS, NARROW_TARGETS):
                    report(r, theme + "/窄屏")
                ctx.close()

            # 打印态：深色主题下打印清单必须是黑字白底
            print("== 打印态 ==")
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{port}/index.html#browse", wait_until="load")
            page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", "dark")
            page.wait_for_timeout(400)
            page.evaluate("() => { const b = document.querySelector('#btnPrint'); if (b) b.click(); }")
            page.wait_for_timeout(500)
            page.emulate_media(media="print")
            page.wait_for_timeout(300)
            info = page.evaluate("""() => {
              const g = s => { const el = document.querySelector(s); return el ? getComputedStyle(el).color : null; };
              return { body: g('body'), w: g('.pl-w'), title: g('.pl-title'),
                       n: document.querySelectorAll('.pl-item').length,
                       words: (window.WL_WORDS || []).length };
            }""")
            for key, val in (("body", info["body"]), (".pl-w", info["w"]), (".pl-title", info["title"])):
                checked += 1
                if val != "rgb(0, 0, 0)":
                    fails.append(f"[打印] {key} 颜色为 {val}，应为黑字")
                    print(f"  ✗ {key:12s} {val}")
                else:
                    print(f"  ✓ {key:12s} {val}")
            # 词数现算自 js/data.js（window.WL_WORDS），不钉死字面量——
            # 将来任何加词数据轮都应自动跟随，不该假红
            checked += 1
            words = info["words"]
            if not words:
                fails.append("[打印] 未取到 window.WL_WORDS，无法核对打印清单条数")
                print("  ✗ 未取到 window.WL_WORDS")
            elif info["n"] != words:
                fails.append(f"[打印] 打印清单 {info['n']} 条，应为词库现算条数 {words}")
                print(f"  ✗ 打印清单条数 {info['n']}（词库 {words}）")
            else:
                print(f"  ✓ 打印清单条数 {info['n']}（与词库现算条数一致）")
            ctx.close()
        finally:
            browser.close()
            srv.shutdown()

    print()
    if fails:
        print(f"RESULT: {len(fails)} FAILURES")
        for f in fails:
            print("  - " + f)
        sys.exit(1)
    print(f"RESULT: ALL TESTS PASSED ({checked} checks passed)")


# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    main()
