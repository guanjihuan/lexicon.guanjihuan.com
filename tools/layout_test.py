#!/usr/bin/env python3
"""版面一致性回归测试（界面自序第五十一轮）

本套件只管一件事：**空态（empty state）的图标与文字的版面关系**。

背景：`.empty-state .es`（空态图标容器）原本写的是 `display:inline-flex`，
于是图标成了行内元素，被后面的首行文字「拉」到同一行里 —— 图标 38px 高、
文字行约 17px，图标下半截实际压进了文字行（实测图标底 333px、文字顶 319px）。
CSS 里同时写着 `margin-bottom:10px`，说明原意就是让图标**独占一行**、站在
文字上方。修法是把 `.es` 改回块级 flex 并用 `margin:0 auto` 居中。

本套件把这个「图标独立成行 + 与文字水平居中对齐」变成可复测的判据，
覆盖全站五处空态：
  · 收藏为空（#fav）
  · 词库按当前筛选无结果（#browse，输入不存在的词）
  · 首页「最近测验记录」为空
  · 首页「错词本」为空
  · 全局搜索无结果（搜索浮层）

运行： python3 tools/layout_test.py
依赖： playwright（浏览器路径用 WL_CHROMIUM 指定）
"""
import functools
import http.server
import json
import os
import socketserver
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


# 量一个空态块：图标盒（.es）与它后面首行文字的矩形
EMPTY_JS = r"""
(scope) => {
  const out = [];
  const roots = scope ? [...document.querySelectorAll(scope)] : [document];
  roots.forEach(root => root.querySelectorAll('.empty-state').forEach(es => {
    const ics = getComputedStyle(es);
    if (ics.display === 'none' || ics.visibility === 'hidden') return;
    const er = es.getBoundingClientRect();
    if (er.width < 20 || er.height < 20) return;
    const icon = es.querySelector('.es');
    if (!icon) { out.push({ where: '空态无图标', ok: false }); return; }
    const ir = icon.getBoundingClientRect();
    // 图标之后的第一个文本节点 → 取它的第一行矩形
    let line = null, txt = '';
    const walk = document.createTreeWalker(es, NodeFilter.SHOW_TEXT);
    let n = walk.nextNode();
    while (n) {
      if (n.textContent.trim()) {
        const rg = document.createRange(); rg.selectNodeContents(n);
        const rects = [...rg.getClientRects()];
        if (rects.length) { line = rects[0]; txt = n.textContent.trim().slice(0, 14); }
        break;
      }
      n = walk.nextNode();
    }
    if (!line) { out.push({ where: '空态无文字', ok: false }); return; }
    out.push({
      iconBottom: Math.round(ir.bottom), iconCx: ir.left + ir.width / 2,
      lineTop: Math.round(line.top), lineCx: line.left + line.width / 2,
      txt: txt
    });
  }));
  return out;
}
"""


# 量顶栏/底栏导航：8 项是否都落在导航条的可视区内（.mainnav 是 overflow-x:auto，
# 滚动条又被 scrollbar-width:none 隐藏 ⇒ 一旦放不下就是**静默裁掉**，用户看不到提示）
NAV_JS = r"""
() => {
  const nav = document.querySelector('.mainnav');
  if (!nav) return { outside: ['无 .mainnav 元素'], sw: 0, cw: 0, pos: '' };
  const nr = nav.getBoundingClientRect();
  const outside = [];
  for (const el of nav.children) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (r.right > nr.right + 1 || r.left < nr.left - 1) {
      outside.push('「' + (el.textContent || '').trim().slice(0, 6) + '」右缘 ' +
        Math.round(r.right) + ' 超出可视右缘 ' + Math.round(nr.right));
    }
  }
  return { outside, sw: nav.scrollWidth, cw: nav.clientWidth, pos: getComputedStyle(nav).position };
}
"""


# 量搜索结果行里的释义（.sr-item .m）是否被横向挤成极窄的省略号。
# 一行里只有它是弹性项（flex:1），窄屏下其余项都不让位 ⇒ 320px 时它只剩 21px / 需要 195px。
SR_GLOSS_JS = r"""
() => {
  const items = [...document.querySelectorAll('#searchOverlay .sr-item')];
  let worst = null;
  for (const it of items) {
    const m = it.querySelector('.m');
    if (!m) continue;
    const need = m.scrollWidth, have = m.clientWidth;
    const ratio = need > 0 ? have / need : 1;
    if (!worst || ratio < worst.ratio) {
      worst = {
        ratio, need, have,
        word: (it.querySelector('.w')?.textContent || '').trim().slice(0, 14),
        gloss: (m.textContent || '').trim().slice(0, 18),
      };
    }
  }
  return worst;
}
"""


# 量首页「最需要加强的词」列表项的释义（.wi-sense）是否被横向砍掉。
# 该行原本是 [单词][释义 flex:1][×错次] 一行排布、释义 nowrap + ellipsis，
# 而一行里只有释义是弹性项 ⇒ 长义项被砍掉一大半（1280px 也只剩 27% 可见）。
# 修复后释义独占第二行整行折行显示；本守卫盯「释义不得被横向/纵向裁切」。
WEAK_GLOSS_JS = r"""
() => {
  const items = [...document.querySelectorAll('.weak-item')];
  let worst = null;
  for (const it of items) {
    const s = it.querySelector('.wi-sense');
    if (!s) continue;
    const need = s.scrollWidth, have = s.clientWidth;
    const vNeed = s.scrollHeight, vHave = s.clientHeight;
    const ratio = need > 0 ? have / need : 1;
    if (!worst || ratio < worst.ratio) {
      worst = {
        ratio, need, have, vNeed, vHave,
        tol: parseFloat(getComputedStyle(s).fontSize) || 12,
        word: (it.querySelector('.wi-word')?.textContent || '').trim().slice(0, 14),
        gloss: (s.textContent || '').trim().slice(0, 18),
      };
    }
  }
  return worst;
}
"""

# 量窄屏词库页的「当前筛选」摘要行（.filter-summary）：
# 该行是 [筛选按钮][摘要 nowrap+ellipsis]，摘要又是唯一的弹性项
# ⇒ 排在最后的关键词先被砍（320px 实测只剩 75%）。
# 摘要的作用就是告诉用户「现在筛掉了什么」，砍尾巴＝静默丢信息。
FILTER_SUMMARY_JS = r"""
() => {
  const el = document.querySelector('.filter-summary');
  if (!el) return null;
  const need = el.scrollWidth, have = el.clientWidth;
  const txt = (el.textContent || '').trim();
  return {
    need, have, txt,
    ratio: need > 0 ? have / need : 1,
    tol: parseFloat(getComputedStyle(el).fontSize) || 12,
    hasKeyword: txt.includes('interdisciplinary'),
  };
}
"""

# 给「最需要加强的词」列表塞几个答错过的词：首页这张卡只显示
# 答错过且尚未掌握的词（按答错次数取前 5），没有进度 ⇒ 列表为空 ⇒ 量不到。
# 用 init_script 在页面脚本之前写入 localStorage（app.js 启动时会回存状态，
# 事后写入会被覆盖——这一条已踩过）。
SEED_STATE = json.dumps({
    "progress": {
        "1346": {"lv": 1, "due": 4102444800000, "seen": 9, "correct": 0, "wrong": 9, "last": 0},
        "1622": {"lv": 1, "due": 4102444800000, "seen": 5, "correct": 0, "wrong": 5, "last": 0},
        "1601": {"lv": 1, "due": 4102444800000, "seen": 3, "correct": 0, "wrong": 3, "last": 0},
        "1647": {"lv": 1, "due": 4102444800000, "seen": 1, "correct": 0, "wrong": 1, "last": 0},
    },
    "fav": [], "days": {}, "quizHist": [],
}, ensure_ascii=False)


# 在浮层（overlay）自己身上找一个「点的位置确实落在浮层上」的坐标：
# 滚轮要打在浮层的空白处（不是卡片、不是内部可滚动列表），
# 才测得到「遮罩上的滚轮会不会把背景带走」。
BACKDROP_POINT_JS = r"""
(sel) => {
  const o = document.querySelector(sel);
  if (!o || o.hidden) return null;
  const vw = window.innerWidth, vh = window.innerHeight;
  const cands = [[3, 3], [vw - 3, 3], [3, vh - 3], [vw - 3, vh - 3],
                 [Math.round(vw / 2), 3], [3, Math.round(vh / 2)]];
  for (const [x, y] of cands) {
    if (document.elementFromPoint(x, y) === o) return { x: Math.round(x), y: Math.round(y) };
  }
  return null;
}
"""


# 第五十八轮：全站「静默截断」扫雷探针。
#
# 判据的四个要点（都是踩出来的）：
#  ① 判据落在**文字行矩形**上，不是容器的 scrollWidth：装饰性伪元素溢出会
#     让 scrollWidth 变大（.hero::before right:-70px ⇒ 多 70px），那不是文字被裁。
#  ② 从文字往上找**最近的「裁切或滚动」祖先**：
#     · 是滚动容器（overflow:auto/scroll 且真的可滚）⇒ 内容够得着，不算静默丢失
#       （词条弹窗 .modal-scroll、搜索浮层 .search-results 都是这一类，
#        早期版本把它们的卡片当成裁切者 ⇒ 假红，现已按滚动可达性排除）；
#     · 是裁切者（overflow:hidden/clip）⇒ 那段文字既看不到也滚不到 ⇒ 静默截断。
#  ③ 「刻意截断」不算缺陷：-webkit-line-clamp（会显示「…」）与
#     text-overflow:ellipsis 都是**有信号**的截断，站点里 .wc-sense（3 行）、
#     .wc-ex-en（2 行）、.wi-word 等都在用 ⇒ 不纳入本守卫。
#  ④ 容差一个字号（≈一个全角字）——Chromium 允许行末收尾括号悬挂到行外。
CLIP_SWEEP_JS = r"""
() => {
  const out = {bad: [], cand: 0, lines: 0, skipped: 0, reach: 0};
  const selOf = el => el.tagName.toLowerCase() +
    (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
  const cache = new Map();
  const csOf = el => {
    let c = cache.get(el);
    if (!c) { c = getComputedStyle(el); cache.set(el, c); }
    return c;
  };
  const clips = cs => cs.overflowX === 'hidden' || cs.overflowX === 'clip' ||
                       cs.overflowY === 'hidden' || cs.overflowY === 'clip';
  const scrolls = cs => cs.overflowX === 'auto' || cs.overflowX === 'scroll' ||
                        cs.overflowY === 'auto' || cs.overflowY === 'scroll';
  // 从文字往上找最近的「裁切或滚动」祖先
  const nearest = el => {
    let q = el;
    while (q && q !== document.body) {
      const cs = csOf(q);
      if (clips(cs) || scrolls(cs)) return {el: q, cs};
      q = q.parentElement;
    }
    return null;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    if (!n.nodeValue || !n.nodeValue.trim() || !n.parentElement) continue;
    const pe = n.parentElement;
    const ns = pe.namespaceURI || '';
    if (ns.indexOf('svg') !== -1) continue;      // SVG 没有 CSS 盒
    const pcs = csOf(pe);
    if (pcs.display === 'none' || pcs.visibility === 'hidden') continue;
    const hit = nearest(pe);
    if (!hit) continue;
    const A = hit.el, acs = hit.cs;
    // 滚动容器且确实可滚 ⇒ 内容可达，不算静默丢失
    if (scrolls(acs) &&
        (A.scrollHeight > A.clientHeight + 1 || A.scrollWidth > A.clientWidth + 1)) {
      out.reach++;
      continue;
    }
    const clamp = acs.webkitLineClamp && acs.webkitLineClamp !== 'none';
    const ell = acs.textOverflow === 'ellipsis';
    if (clamp || ell) { out.skipped++; continue; }   // 有信号的刻意截断
    const rg = document.createRange();
    rg.selectNodeContents(n);
    const rects = [...rg.getClientRects()];
    const ar = A.getBoundingClientRect();
    const bl = parseFloat(acs.borderLeftWidth) || 0;
    const bt = parseFloat(acs.borderTopWidth) || 0;
    const right = ar.left + bl + A.clientWidth;
    const bottom = ar.top + bt + A.clientHeight;
    const clipX = acs.overflowX === 'hidden' || acs.overflowX === 'clip';
    const clipY = acs.overflowY === 'hidden' || acs.overflowY === 'clip';
    for (const rr of rects) {
      if (rr.width < 0.5 && rr.height < 0.5) continue;
      out.lines++;
      out.cand++;
      const overR = clipX ? rr.right - right : 0;
      const overB = clipY ? rr.bottom - bottom : 0;
      const over = Math.max(overR, overB);
      if (over > (parseFloat(pcs.fontSize) || 0)) {
        out.bad.push({sel: selOf(A), axis: overB > overR ? '纵' : '横',
                      over: Math.round(over), txt: n.nodeValue.trim().slice(0, 40)});
        break;
      }
    }
  }
  return out;
}
"""


# 静默截断扫描的「判据未空转」下限（第五十八轮）。
# 实测：320px 一档（八视图 + 三浮层）扫到候选元素 ≈ 190 处、文字行 ≈ 240 行；
# 取下限 80 / 80，留一半余量给浏览器差异，但仍足以挡住「探针扫到 0 处」。
MIN_CLIP_CAND = 80
MIN_CLIP_LINES = 80


# 长单词整词一行：**就地**把真实词元素的内容换成待测词，量它占几行，
# 量完换回原词。
# 不用「另插一个探针」的办法：闪卡正面那一行是 flex（词 + 喇叭钮），
# 插进去的探针要和真词抢宽度，量到的是「探针 + 真词」挤在一起的条件，
# 比真实情况更苛刻（实测 390px 下探针全部报 2 行、真词却只有 1 行）。
# 另附一条「判据未空转」：把同一个元素放大到 120px 时必须报出多行，
# 否则「一行」可能只是量法没生效的空转。
LONG_WORD_JS = r"""
(cfg) => {
  const [realSel, words] = cfg;
  const real = document.querySelector(realSel);
  if (!real) return null;
  const orig = real.textContent;
  const measure = () => {
    const rg = document.createRange();
    rg.selectNodeContents(real);
    const rects = [...rg.getClientRects()].filter(r => r.width > 0);
    const tops = new Set(rects.map(r => Math.round(r.top)));
    return {lines: tops.size, firstTop: rects.length ? Math.round(rects[0].top) : null};
  };
  // 首行最后一个字符的文本：用来判「断在连字符上」还是「从词中间硬拆」
  const firstLineTail = () => {
    const node = real.firstChild;
    if (!node || node.nodeType !== 3) return '';
    const text = node.nodeValue;
    const rg = document.createRange();
    let top0 = null, cut = 0;
    for (let i = 0; i < text.length; i++) {
      rg.setStart(node, i); rg.setEnd(node, i + 1);
      const rects = [...rg.getClientRects()].filter(r => r.width > 0);
      if (!rects.length) continue;
      const t = Math.round(rects[0].top);
      if (top0 === null) top0 = t;
      if (t !== top0) break;
      cut = i + 1;
    }
    return text.slice(0, cut);
  };
  const out = [];
  for (const word of words) {
    real.textContent = word;
    const m = measure();
    out.push({word, lines: m.lines, tail: firstLineTail(),
              fs: getComputedStyle(real).fontSize});
  }
  real.textContent = orig;
  const bigFs = real.style.fontSize;
  real.style.fontSize = '120px';
  real.textContent = words[0];
  const bigLines = measure().lines;
  real.style.fontSize = bigFs;
  real.textContent = orig;
  return {out, bigLines};
}
"""


def long_words(n=8):
    """词库里最长的几个单词（不含词组）——长词是窄屏断行的重灾区。

    现算、不钉字面量：词库增删后自动跟随（写死词条会假红）。
    """
    with open(os.path.join(ROOT, "data", "words.json"), encoding="utf-8") as f:
        ws = json.load(f)
    cand = [w["word"] for w in ws if isinstance(w, dict) and w.get("word")
            and " " not in w["word"]]
    cand.sort(key=lambda w: (-len(w), w))
    return cand[:n]


def main():
    srv, port = serve()
    time.sleep(0.3)
    base = f"http://127.0.0.1:{port}/index.html"
    from playwright.sync_api import sync_playwright

    fails = []
    checked = 0

    def check(name, cond, extra=""):
        nonlocal checked
        checked += 1
        if cond:
            print(f"  ✓ {name}" + (f"  [{extra}]" if extra else ""))
        else:
            print(f"  ✗ {name}" + (f"  [{extra}]" if extra else ""))
            fails.append(name + ((" " + str(extra)) if extra else ""))

    def nav(page, url, tries=4):
        """导航到 url，失败重试。

        多窗口同机跑套件时，Chromium 偶尔等不到 load 事件（同一份代码在纯净
        HEAD 副本上也会复现 ⇒ 属环境抖动，不是代码缺陷）。
        这里用 domcontentloaded + 有限次重试；四次都失败才算真红。
        """
        last = None
        for _ in range(tries):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(250)
                return True
            except Exception as e:      # noqa: BLE001 —— 只重试，不掩盖最终失败
                last = e
                page.wait_for_timeout(400)
        raise last

    def measure_empty(page, where, scope=None, expect=1):
        """量当前页面上每个可见空态，返回 (图标行, 文字行) 判定结果列表。

        第五十八轮（据工装窗报出、本窗直验属实）：原写法拿到 rows 直接
        `for r in rows:` —— 一个空态都没量到时循环零次、**一条断言都不产生**，
        四个调用点的空态守卫会凭空消失而套件照样报 ALL TESTS PASSED
        （变异：css 追加 `.empty-state{display:none!important}` ⇒ 38 项全过）。
        故加两道下限：①量到空态元素（空集判红）②量到的处数不少于预期。
        """
        rows = page.evaluate(EMPTY_JS, scope)
        if not rows:
            check(f"{where}：量到空态元素（判据未空转）", False,
                  "未量到任何可见 .empty-state")
            return
        check(f"{where}：量到空态元素（判据未空转）", True,
              f"量到 {len(rows)} 处")
        check(f"{where}：空态处数不少于预期",
              len(rows) >= expect, f"预期至少 {expect} 处 / 实测 {len(rows)} 处")
        for r in rows:
            if not r.get("iconBottom"):
                check(f"{where}：空态结构完整", False, str(r.get("where")))
                continue
            # ① 图标独占一行：图标底边不得压进首行文字（容差 1px）
            check(f"{where}：空态图标独立成行（不压文字行）",
                  r["iconBottom"] <= r["lineTop"] + 1,
                  f"图标底 {r['iconBottom']}px / 文字顶 {r['lineTop']}px ·「{r['txt']}」")
            # ② 图标与文字水平居中对齐（容差 2px）
            check(f"{where}：空态图标与首行文字水平居中对齐",
                  abs(r["iconCx"] - r["lineCx"]) <= 2,
                  f"图标中 {r['iconCx']:.1f} / 文字中 {r['lineCx']:.1f} ·「{r['txt']}」")

    with sync_playwright() as pw:
        exe = os.environ.get("WL_CHROMIUM")
        # WL_CHROMIUM 是别的机器写死的绝对路径时（如 mutation_test 从 Linux
        # 环境透传过来的默认值），本机不存在该文件 ⇒ 不要把浏览器起在坏路径上，
        # 当作没设过，走 Playwright 自带 chromium / channel 兜底。
        if exe and not os.path.exists(exe):
            exe = None
        # --no-sandbox：容器里 chromium 自带的沙箱与工具沙箱会打架，
        # 表现为导航偶发超时/浏览器被杀（同代码在纯净 HEAD 副本上同样复现）。
        try:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"],
                                         **({"executable_path": exe} if exe else {}))
        except Exception:
            # 有些环境只装了完整 Chromium、没有 headless shell，退回 channel 模式
            # （与 smoke_test.py 的兜底同规；否则本机无 WL_CHROMIUM 命中的环境
            # 会直接崩掉，变异测试的 layout 基线被误判成红）。
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"],
                                         channel="chromium")
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            # ① 收藏为空
            print("== 收藏为空 ==")
            nav(page, base + "#fav")
            page.wait_for_timeout(500)
            measure_empty(page, "收藏", expect=1)

            # ② 词库按关键词筛出零结果
            print("== 词库无结果 ==")
            nav(page, base + "#browse")
            page.wait_for_timeout(500)
            page.fill("#bq", "zzzqqqxxx")
            page.wait_for_timeout(700)
            measure_empty(page, "词库无结果", expect=1)

            # ③ 首页两处空态（最近测验记录 / 错词本）
            print("== 首页空态 ==")
            nav(page, base + "#home")
            page.wait_for_timeout(600)
            measure_empty(page, "首页", expect=2)

            # ④ 全局搜索无结果
            print("== 搜索无结果 ==")
            nav(page, base + "#home")
            page.wait_for_timeout(400)
            page.click("#btnSearch")
            page.wait_for_timeout(400)
            page.fill("#searchInput", "zzzqqqxxx")
            page.wait_for_timeout(700)
            measure_empty(page, "搜索无结果", "#searchOverlay", expect=1)

            # ⑤ 顶栏/底栏导航：8 项是否都落在导航条的可视区内
            #    （.mainnav 是 overflow-x:auto，滚动条被 scrollbar-width:none 隐藏 ⇒
            #      一旦放不下就是静默裁掉，用户看不到任何提示）
            print("== 导航可达性（宽度扫描） ==")
            for w in (320, 375, 861, 870, 880, 884, 900, 920, 940, 1024, 1080):
                page.set_viewport_size({"width": w, "height": 900})
                page.wait_for_timeout(250)
                navm = page.evaluate(NAV_JS)
                check(f"导航 {w}px：8 项全部落在可视区内",
                      not navm["outside"],
                      ("；".join(navm["outside"]) if navm["outside"]
                       else f"scrollW {navm['sw']} / clientW {navm['cw']}（position={navm['pos']}）"))

            # ⑥ 搜索结果行里的释义不得被横向挤成省略号（第五十三轮）
            print("== 搜索结果释义可见性 ==")
            for w in (320, 375, 480):
                page.set_viewport_size({"width": w, "height": 900})
                nav(page, base + "#home")
                page.keyboard.press("Escape")   # 上一场景把搜索浮层开着，先关掉再点开
                page.wait_for_timeout(200)
                page.wait_for_timeout(350)
                page.click("#btnSearch")
                page.wait_for_timeout(350)
                page.fill("#searchInput", "a")
                page.wait_for_timeout(800)
                g = page.evaluate(SR_GLOSS_JS)
                if not g:
                    check(f"搜索 {w}px：结果行有释义可量", False, "未取到搜索结果行")
                    continue
                check(f"搜索 {w}px：释义未被横向挤成省略号",
                      g["need"] <= g["have"] + 1,
                      f"最差行「{g['word']}」释义可见 {g['have']}px / 需要 {g['need']}px"
                      f"（{g['ratio']:.0%}）「{g['gloss']}」")

            check("页面无 JS 运行时错误", not errors, "; ".join(errors[:2]))

            # ⑦ 首页「最需要加强的词」列表项的释义不得被裁切（第五十四轮）
            #    单独开一个 context 并在页面脚本之前写入进度：这张卡只在
            #    「答错过且未掌握」时才有行，否则量不到东西；
            #    独立 context 是为了不污染前面各项检查的空态前提。
            print("== 首页「最需要加强的词」释义可见性 ==")
            ctx2 = browser.new_context(viewport={"width": 1280, "height": 900})
            ctx2.add_init_script(
                "try{localStorage.setItem('wl_state_v1', " + json.dumps(SEED_STATE) + ");}catch(e){}")
            p2 = ctx2.new_page()
            for w in (320, 375, 480, 1280):
                p2.set_viewport_size({"width": w, "height": 900})
                nav(p2, base + "#home")
                p2.wait_for_timeout(600)
                g = p2.evaluate(WEAK_GLOSS_JS)
                if not g:
                    check(f"最需加强 {w}px：列表项有释义可量", False, "未取到「最需要加强的词」列表项")
                    continue
                # 横向：释义不得被砍掉。容差一个全角字（≈字号）——Chromium 的 CJK
                # 换行允许行末收尾括号悬挂到行外（实测末字「）」外挂 6px），
                # 那不是截断；真正的截断（旧 CSS）差着几百像素。
                check(f"最需加强 {w}px：释义未被横向截断",
                      g["need"] <= g["have"] + g["tol"],
                      f"最差行「{g['word']}」释义可见 {g['have']}px / 需要 {g['need']}px"
                      f"（{g['ratio']:.0%}）「{g['gloss']}」")
                # 纵向：释义整段都要放得下（不许只显示头几行）
                check(f"最需加强 {w}px：释义未被纵向裁切",
                      g["vNeed"] <= g["vHave"] + 1,
                      f"内容高 {g['vNeed']}px / 盒高 {g['vHave']}px ·「{g['gloss']}」")
            ctx2.close()

            # ⑧ 浮层打开时，背景不该跟着滚（第五十五轮）
            #    实测两处漏：
            #    ① 浮层的遮罩上滚滚轮 ⇒ 背后的页面被带着滚走；
            #    ② 浮层内部列表滚到尽头后继续滚 ⇒ 滚动链一路传到文档。
            #    修法两层：根元素在浮层打开时锁滚动（html:has(...)），
            #    浮层与内部滚动块各自 overscroll-behavior:contain。
            print("== 浮层打开时背景不跟随滚动 ==")
            ctx3 = browser.new_context(viewport={"width": 375, "height": 700})
            p3 = ctx3.new_page()
            for w in (375, 1280):
                p3.set_viewport_size({"width": w, "height": 700})
                nav(p3, base + "#browse")
                p3.wait_for_timeout(700)
                # 平滑滚动会让 scrollY 读数滞后（动画未结束时读到 0）⇒
                # 这里把滚动行为改成瞬时，量到的才是真实位移。
                p3.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';}")

                # ① 词条弹窗：遮罩上滚滚轮，背景不动
                p3.evaluate("()=>window.WL_DEBUG.openWordModal(1346)")
                p3.wait_for_timeout(500)
                pt = p3.evaluate(BACKDROP_POINT_JS, "#wordModal")
                if pt:
                    y0 = p3.evaluate("()=>window.scrollY")
                    p3.mouse.move(pt["x"], pt["y"])
                    p3.mouse.wheel(0, 800)
                    p3.wait_for_timeout(350)
                    y1 = p3.evaluate("()=>window.scrollY")
                    check(f"浮层 {w}px：词条弹窗遮罩上滚滚轮，背景不动",
                          y1 == y0, f"背景 scrollY {y0} -> {y1}")
                else:
                    check(f"浮层 {w}px：词条弹窗遮罩上滚滚轮，背景不动", False, "未取到遮罩坐标")
                # 弹窗内容仍要能独立滚动（锁背景不能锁掉浮层自己）
                inner = p3.evaluate(
                    "()=>{const e=document.querySelector('#wordModalBody');"
                    "e.scrollTop=200; return e.scrollTop;}")
                check(f"浮层 {w}px：词条弹窗内容仍可独立滚动",
                      inner > 0, f"内容区 scrollTop={inner}")
                p3.keyboard.press("Escape")
                p3.wait_for_timeout(400)

                # ② 搜索浮层：结果列表滚到底后继续滚，背景不动
                p3.click("#btnSearch")
                p3.wait_for_timeout(350)
                p3.fill("#searchInput", "a")
                p3.wait_for_timeout(800)
                lst = p3.evaluate(
                    "()=>{const e=document.querySelector('#searchResults');"
                    "e.scrollTop=e.scrollHeight; const r=e.getBoundingClientRect();"
                    "return {x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)};}")
                y0 = p3.evaluate("()=>window.scrollY")
                p3.mouse.move(lst["x"], lst["y"])
                p3.mouse.wheel(0, 3000)
                p3.wait_for_timeout(400)
                y1 = p3.evaluate("()=>window.scrollY")
                check(f"浮层 {w}px：搜索结果列表滚到底继续滚，背景不动",
                      y1 == y0, f"背景 scrollY {y0} -> {y1}")
                p3.keyboard.press("Escape")
                p3.wait_for_timeout(400)

                # ③ 快捷键浮层：遮罩上滚滚轮，背景不动
                # 顶栏的「键盘快捷键」按钮已下线（与设置页那一节重复），
                # 面板只剩「?」一个入口 ⇒ 改走 WL_DEBUG 钩子驱动，别再找按钮。
                p3.evaluate("()=>window.WL_DEBUG.openShortcuts()")
                p3.wait_for_timeout(400)
                pt = p3.evaluate(BACKDROP_POINT_JS, "#shortcutsOverlay")
                if pt:
                    y0 = p3.evaluate("()=>window.scrollY")
                    p3.mouse.move(pt["x"], pt["y"])
                    p3.mouse.wheel(0, 800)
                    p3.wait_for_timeout(350)
                    y1 = p3.evaluate("()=>window.scrollY")
                    check(f"浮层 {w}px：快捷键浮层遮罩上滚滚轮，背景不动",
                          y1 == y0, f"背景 scrollY {y0} -> {y1}")
                else:
                    check(f"浮层 {w}px：快捷键浮层遮罩上滚滚轮，背景不动", False, "未取到遮罩坐标")
                p3.keyboard.press("Escape")
                p3.wait_for_timeout(400)

                # ④ 浮层全关后页面恢复可滚（锁不能忘了解）
                y = p3.evaluate(
                    "()=>{window.scrollTo({top:300,left:0,behavior:'instant'});"
                    "return window.scrollY;}")
                check(f"浮层 {w}px：浮层关闭后页面恢复可滚",
                      y > 0, f"scrollTo(0,300) 后 scrollY={y}")

            # ⑨ 窄屏词库页的「当前筛选」摘要不得被横向砍掉（第五十六轮）
            #    摘要行是 [筛选按钮][摘要 nowrap+ellipsis]，摘要是唯一的弹性项
            #    ⇒ 排在最后的关键词先被砍（修前 320px 只剩 75%）。
            print("== 词库窄屏筛选摘要可见性 ==")
            for w in (320, 375, 414):
                p3.set_viewport_size({"width": w, "height": 800})
                nav(p3, base + "#browse")
                p3.wait_for_timeout(400)
                # 施加多个筛选（关键词 + 词性 + 首字母），把摘要行拉长到会被砍的长度
                p3.fill("#bq", "interdisciplinary")
                p3.wait_for_timeout(700)
                p3.evaluate(
                    "()=>{const c=document.querySelector(\"#posFilter .chip[data-pos='动词']\");"
                    "if(c) c.click();}")
                p3.wait_for_timeout(500)
                p3.evaluate(
                    "()=>{const b=[...document.querySelectorAll('#letterBar .letter-btn')]"
                    ".find(x=>x.dataset.l==='C'); if(b) b.click();}")
                p3.wait_for_timeout(500)
                p3.select_option("#bstatus", "learning")
                p3.wait_for_timeout(500)
                g = p3.evaluate(FILTER_SUMMARY_JS)
                if not g:
                    check(f"筛选摘要 {w}px：取到摘要行", False, "未取到 .filter-summary")
                    continue
                # 容差一个全角字：Chromium 允许行末收尾括号悬挂到行外，那不是截断
                check(f"筛选摘要 {w}px：摘要未被横向截断",
                      g["need"] <= g["have"] + g["tol"],
                      f"可见 {g['have']}px / 需要 {g['need']}px（{g['ratio']:.0%}）「{g['txt']}」")
                check(f"筛选摘要 {w}px：关键词完整出现在摘要里",
                      g["hasKeyword"], f"摘要「{g['txt']}」")
            ctx3.close()

            # ⑩ 学习页版面守卫（本次修复的三处几何缺陷）
            #    ① 移动端底部标签栏：栅格列数曾写死 8 列，而页内只有 6 个导航项
            #       （「内容窗」「键盘快捷键」两轮下线后没同步）——
            #       六颗图标挤在左边四分之三，右端空出一条死白（375px 档实测 96px）。
            #    ② 牌组 chip 的栅格：auto-fill 会把「放不下的」那些列照样造出来，
            #       最后一行右侧空出整列的空壳（1920px 档词性行实测 487px）。
            #    ③ 翻卡正面：.flip-face::after 的 auto 边距与操作行的那一份
            #       把余量三等分，「显示答案」钮浮在卡身中部、卡底空出约 100px。
            print("== 学习页版面守卫 ==")
            ctx5 = browser.new_context(viewport={"width": 375, "height": 900})
            p5 = ctx5.new_page()

            # ① 底部标签栏：末项右缘应当贴住栏右缘（不留整列空隙）
            nav(p5, base + "#study")
            p5.wait_for_timeout(500)
            navr = p5.evaluate(
                "()=>{const n=document.querySelector('.mainnav');"
                "if(!n) return null;"
                "const items=[...n.querySelectorAll('.nav-item')]"
                ".filter(a=>a.getBoundingClientRect().width>0);"
                "if(!items.length) return null;"
                "const nr=n.getBoundingClientRect();"
                "const last=items[items.length-1].getBoundingClientRect();"
                "return {n:items.length,gap:Math.round(nr.right-last.right),"
                "w:Math.round(nr.width)};}")
            check("底部标签栏：导航项数与栅格列数一致（不留空列）",
                  navr is not None and navr["n"] == 6, f"导航项 {navr and navr['n']} 个")
            check("底部标签栏：末项贴住栏右缘（无整列空隙）",
                  navr is not None and navr["gap"] <= 4,
                  f"末项右缘距栏右缘 {navr and navr['gap']}px")
            ctx5.close()

            # ②③ 牌组栅格与翻卡正面：宽屏（1920）与桌面（1440）各量一次
            ctx6 = browser.new_context(viewport={"width": 1920, "height": 1000})
            p6 = ctx6.new_page()
            nav(p6, base + "#study")
            p6.wait_for_timeout(600)
            rows = p6.evaluate(
                "()=>[...document.querySelectorAll('.deck-grid')].map(g=>{"
                "const gr=g.getBoundingClientRect();"
                "const kids=[...g.children].filter(k=>k.getBoundingClientRect().width>0);"
                "if(!kids.length) return null;"
                "const last=kids[kids.length-1].getBoundingClientRect();"
                "return {cls:g.className,rows:new Set(kids.map(k=>Math.round(k.getBoundingClientRect().y))).size,"
                "hole:Math.round(gr.right-last.right)};})")
            rows = [r for r in rows if r]
            # 词性行与范围行：最后一行右侧不该空出整列（auto-fit 会收掉空列）
            for r in rows:
                if r["cls"] in ("deck-grid", "deck-grid pos"):
                    check(f"牌组栅格 {r['cls']}：无空列死白",
                          r["hole"] <= 8, f"右侧空 {r['hole']}px / {r['rows']} 行")
            # 翻卡正面：「显示答案」操作行应贴住卡底（余量不再被三处 auto 边距分走）
            # （二百轮起页首推荐条不再有按钮，「本次」行那颗是全页唯一的「开始学习」）
            p6.click("#fcStart")
            p6.wait_for_timeout(600)
            flip = p6.evaluate(
                "()=>{const c=document.querySelector('.flip-card');"
                "const f=document.querySelector('.fc-front-foot');"
                "if(!c||!f) return null;"
                "const cr=c.getBoundingClientRect(), fr=f.getBoundingClientRect();"
                "return {gap:Math.round(cr.bottom-fr.bottom),h:Math.round(cr.height)};}")
            check("翻卡正面：操作行贴住卡底（不浮在卡身中部）",
                  flip is not None and flip["gap"] <= 40,
                  f"操作行底距卡底 {flip and flip['gap']}px / 卡高 {flip and flip['h']}px")
            ctx6.close()

            # ⑩ 全站静默截断扫雷（第五十八轮）
            #    判据：任何 overflow:hidden/clip 的容器，若**文字行矩形**越出它的
            #    padding box 且超出量超过一个字号 ⇒ 那段文字被无声吃掉（既没有
            #    「…」也没有滚动条可滚）。刻意截断（line-clamp / ellipsis）不计。
            #    覆盖八视图 + 三个浮层 × 窄屏两档。
            print("== 全站静默截断扫描 ==")
            ctx4 = browser.new_context(viewport={"width": 375, "height": 900})
            p4 = ctx4.new_page()
            views = ("home", "browse", "study", "quiz", "cats", "fav", "stats", "settings")

            def sweep(page, label):
                r = page.evaluate(CLIP_SWEEP_JS)
                if r is None:
                    check(f"截断扫描 {label}：无静默截断", False, "探针未返回")
                    return 0, 0
                check(f"截断扫描 {label}：无静默截断", not r["bad"],
                      ("；".join(f"{b['sel']} {b['axis']}向超出 {b['over']}px「{b['txt']}」"
                                 for b in r["bad"][:3])
                       if r["bad"] else f"候选 {r['cand']} 处 / 文字行 {r['lines']} 行"))
                return r["cand"], r["lines"]

            for w in (320, 375):
                p4.set_viewport_size({"width": w, "height": 900})
                c_sum = l_sum = 0
                for v in views:
                    nav(p4, base + "#" + v)
                    p4.wait_for_timeout(450)
                    c, l = sweep(p4, f"{w}px #{v}")
                    c_sum += c
                    l_sum += l
                # 三个浮层：浮层里的内容同样会被裁，浮层不在八视图之内
                p4.evaluate("()=>window.WL_DEBUG.openWordModal(1346)")
                p4.wait_for_timeout(500)
                c, l = sweep(p4, f"{w}px 词条弹窗")
                c_sum += c
                l_sum += l
                p4.keyboard.press("Escape")
                p4.wait_for_timeout(300)
                p4.click("#btnSearch")
                p4.wait_for_timeout(300)
                p4.fill("#searchInput", "a")
                p4.wait_for_timeout(800)
                c, l = sweep(p4, f"{w}px 搜索浮层")
                c_sum += c
                l_sum += l
                p4.keyboard.press("Escape")
                p4.wait_for_timeout(300)
                p4.evaluate("()=>window.WL_DEBUG.openShortcuts()")
                p4.wait_for_timeout(400)
                c, l = sweep(p4, f"{w}px 快捷键浮层")
                c_sum += c
                l_sum += l
                p4.keyboard.press("Escape")
                p4.wait_for_timeout(300)
                # 判据未空转：这一档必须真的扫到足够多的候选元素与文字行，
                # 否则「无静默截断」是因为什么都没量到。
                check(f"截断扫描 {w}px：扫到足够的候选元素与文字行（判据未空转）",
                      c_sum >= MIN_CLIP_CAND and l_sum >= MIN_CLIP_LINES,
                      f"候选 {c_sum} 处（下限 {MIN_CLIP_CAND}）/ 文字行 {l_sum} 行"
                      f"（下限 {MIN_CLIP_LINES}）")
            ctx4.close()

            # ⑪ 长单词整词一行（窄屏）
            #    首页「随机一词」与闪卡正面都是大号衬线体，而词库里最长的词有
            #    18 个字母（operationalization / heteroskedasticity…）。
            #    窄屏放不下时 word-break:break-word 会从**词中间**硬拆
            #    （multidisciplina / ry），读起来像坏字。
            #    判据：把词库里最长的几个词按真实排版量它占几行——
            #    必须是 1 行；**带连字符的复合词断在连字符上不算从词中间断**
            #    （quasi-experimental 断成 quasi- / experimental 是规范排版），
            #    只在「首行不是以连字符收尾」时判红。
            print("== 长单词整词一行（窄屏） ==")
            words_long = long_words()
            ctx7 = browser.new_context(viewport={"width": 320, "height": 900})
            p7 = ctx7.new_page()

            def hard_broken(rows):
                """从词中间硬拆的词：多行，且首行不是以连字符收尾。"""
                return [x for x in rows
                        if x["lines"] > 1 and not x.get("tail", "").endswith("-")]

            for w in (320, 360, 390):
                p7.set_viewport_size({"width": w, "height": 900})
                # ① 首页「随机一词」面板
                nav(p7, base + "#home")
                p7.wait_for_timeout(500)
                g = p7.evaluate(LONG_WORD_JS, [".rand-word .w", words_long])
                if not g:
                    check(f"长单词 {w}px：首页取得到随机一词面板", False, "未取到 .rand-word .w")
                else:
                    check(f"长单词 {w}px：首页随机一词——探针能测出断行（判据未空转）",
                          g["bigLines"] > 1, f"120px 探针行数 {g['bigLines']}")
                    bad = hard_broken(g["out"])
                    check(f"长单词 {w}px：首页随机一词整词一行",
                          not bad,
                          ("；".join(f"{x['word']} 断成 {x['lines']} 行（首行「{x.get('tail')}」）"
                                     for x in bad)
                           if bad else f"字号 {g['out'][0]['fs']}"))
                # ② 闪卡正面
                nav(p7, base + "#study")
                p7.wait_for_timeout(700)
                # 用 evaluate 点按钮：窄屏下 Playwright 的可点击性判定会等
                # 「可见且稳定」，而这张卡在重绘时元素会被换掉 → 偶发超时。
                p7.evaluate("()=>{const b=document.querySelector('#fcStart');"
                            "if(b) b.click();}")
                p7.wait_for_timeout(900)
                g2 = p7.evaluate(LONG_WORD_JS, [".fc-word", words_long])
                if not g2:
                    check(f"长单词 {w}px：学习页取得到闪卡正面", False, "未取到 .fc-word")
                else:
                    check(f"长单词 {w}px：闪卡正面——探针能测出断行（判据未空转）",
                          g2["bigLines"] > 1, f"120px 探针行数 {g2['bigLines']}")
                    bad2 = hard_broken(g2["out"])
                    check(f"长单词 {w}px：闪卡正面整词一行",
                          not bad2,
                          ("；".join(f"{x['word']} 断成 {x['lines']} 行（首行「{x.get('tail')}」）"
                                     for x in bad2)
                           if bad2 else f"字号 {g2['out'][0]['fs']}"))
            ctx7.close()
        finally:
            browser.close()

    print()
    if fails:
        print(f"RESULT: {len(fails)} FAILURES ({checked} checks)")
        for f in fails:
            print("  ✗ " + f)
        sys.exit(1)
    print(f"RESULT: ALL TESTS PASSED ({checked} checks passed)")


# 控制台输出钉 UTF-8（Windows GBK 控制台对 ✓/✗ 直接崩，见 _console_utf8.py）
from _console_utf8 import force_utf8_console  # noqa: E402

force_utf8_console()

if __name__ == "__main__":
    main()
