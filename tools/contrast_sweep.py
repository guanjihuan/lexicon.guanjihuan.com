#!/usr/bin/env python3
"""全站文字对比度全量扫描（界面自序第四十轮；第四十九轮增补悬停态与过渡冻结）

第三十七轮的对比度套件只量「手挑的代表目标」；本套件改为**扫描真实应用**
的每一个有直接文字的元素，按 WCAG 2.1 计算其文字与实际背景的对比度：
  · 明暗两套主题（主题只有浅色/深色两档，默认深色：直接改应用设置走真实路径）
  · 八个视图全跑
  · 正文阈值 4.5:1，大号文字（≥24px，或 ≥18.66px 且加粗）阈值 3:1
  · 透明底色与渐变按层合成后取实际背景色，不做「近似放行」
  · **第四十九轮增补**：① 量尺冻结过渡/动画（量最终态，不量动画中间态）；
    ② 新增**悬停态**扫描 —— 悬停时文字仍受 WCAG 1.4.3 约束，且「悬停样式吃掉
    激活/选中态」是常态扫描查不出的隐蔽缺陷（本库 `.pager button.on` 即是）。
另附非文字对比度判据（WCAG 1.4.11）：表单控件的描边与其**相邻底色**
（自父元素起逐层合成）须 ≥3:1 —— 描边是「认出这是个输入框」的唯一依据。

运行： python3 tools/contrast_sweep.py
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

VIEWS = ["home", "browse", "study", "quiz", "cats", "fav", "stats", "settings"]

# 第五十七轮（守卫诚实度）：扫描类判据必须「量到了东西」才算数。
# 「全部文字过线」在扫到 0 处文字时也是真的 ⇒ 判据空转 ⇒ 恒过。
# 下限按实测最小值取：八个视图里最少的是收藏空态（8 处文字），
# 悬停态每视图最少 7 个可悬停元素（实测 7~30）。
MIN_SCANNED = 5
MIN_HOVERED = 1

# ── 第四十九轮：测量前冻结过渡/动画 ────────────────────────────────
# css/style.css:253 有 `#main.view-enter{animation:viewIn .22s}`（@keyframes viewIn
# 从 opacity:0 起）。视图进场动画期间 #main 自身 opacity<1，祖先链透明度相乘会把
# 文字与底色同时拉向同色 ⇒ 对比度被算低 ⇒ 量出**假的**「低于 AA」（工装窗 e9eb70
# 曾偶发见到 [light] cats 5 处；本机连跑 3 次未复现，故按成因加固而非据未复现改口径）。
# 冻结后量的是最终态，既消除假红，也让悬停态取到的是过渡**终点**的颜色。
FREEZE_JS = r"""
() => {
  if (!document.getElementById('__wl_freeze')) {
    const s = document.createElement('style');
    s.id = '__wl_freeze';
    s.textContent = '*,*::before,*::after{transition:none!important;animation:none!important}';
    document.head.appendChild(s);
  }
  return new Promise(res => requestAnimationFrame(() => requestAnimationFrame(() => res(true))));
}
"""

SWEEP_JS = r"""
(scope) => {
  /* 扫描范围（第五十轮起可传参）：默认只扫 #main。
     页眉/页脚/浮层都是 <main id="main"> 的兄弟节点，默认口径完全照不到它们。
     scope 是一个**容器选择器列表**（逗号分隔），范围＝容器本身 + 其全部后代。 */
  const ROOTS = [...document.querySelectorAll(scope || '#main')];
  const ALL = [];
  for (const r of ROOTS) { ALL.push(r); r.querySelectorAll('*').forEach(e => ALL.push(e)); }
  /* ── 颜色解析 ─────────────────────────────────────────────── */
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
  const over = (fg, bg) => [0, 1, 2].map(i => fg.c[i] * fg.a + bg.c[i] * (1 - fg.a));
  const lum = (c) => {
    const f = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  };
  const cr = (a, b) => { const l1 = lum(a), l2 = lum(b); const hi = Math.max(l1, l2), lo = Math.min(l1, l2); return (hi + 0.05) / (lo + 0.05); };

  /* 渐变里取第一个不透明色作该层的实底；全透明则该层视为无底 */
  const gradOpaque = (el) => {
    const bi = getComputedStyle(el).backgroundImage;
    if (!bi || bi === 'none') return null;
    const ms = bi.match(/color\(srgb [^)]+\)|rgba?\([^)]+\)/g) || [];
    for (const m of ms) { const c = px(m); if (c && c.a >= 0.99) return c; }
    return null;
  };

  /* 从元素自身往上逐层合成背景：元素层(最上) → 祖先层 → 实底(最下) */
  const bgOf = (el) => {
    const layers = [];
    let n = el, base = null;
    while (n && n !== document.documentElement) {
      const g = gradOpaque(n);
      if (g) { base = { c: g.c, a: 1 }; break; }
      const c = px(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) { base = { c: c.c, a: 1 }; break; } }
      n = n.parentElement;
    }
    if (!base) {
      const b = px(getComputedStyle(document.body).backgroundColor);
      base = b && b.a > 0 ? b : { c: [255, 255, 255], a: 1 };
    }
    let acc = base.c;
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], { c: acc, a: 1 });
    return acc;
  };

  /* 元素「身后」的底色：从父元素起逐层合成（不含元素自身的底色）。
     用于算 opacity 淡出时元素被混到哪片底上。 */
  const outerOf = (el) => {
    const layers = [];
    let n = el.parentElement, base = null;
    while (n && n !== document.documentElement) {
      const g = gradOpaque(n); if (g) { base = { c: g.c, a: 1 }; break; }
      const c = px(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) { base = { c: c.c, a: 1 }; break; } }
      n = n.parentElement;
    }
    if (!base) {
      const b = px(getComputedStyle(document.body).backgroundColor);
      base = b && b.a > 0 ? b : { c: [255, 255, 255], a: 1 };
    }
    let acc = base.c;
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], { c: acc, a: 1 });
    return acc;
  };

  /* 有效透明度＝元素自身与祖先链上所有 opacity 的乘积。
     「淡出弱化文字」必须计入合成，否则 opacity:.45 的文字会被量成满不透明而
     整轮漏判（第四十八轮补上的扫描器口径缺陷）。 */
  const alphaOf = (el) => {
    let a = 1, n = el;
    while (n && n !== document.documentElement) { a *= parseFloat(getComputedStyle(n).opacity) || 1; n = n.parentElement; }
    return a;
  };

  /* 非活动组件豁免（WCAG 1.4.3 明列）：disabled / aria-disabled 的控件
     其文字没有对比度要求。 */
  const isInactive = (el) => !!(el.closest && el.closest('[disabled],[aria-disabled="true"]'));

  /* 元素的「展示身份」：标签名 + 排序后的类名集合。悬停样式由类名驱动，
     故同一身份只需量一次（取首个实例），既覆盖到 .chip 与 .chip.on 这类
     「同名不同态」，又不必对上千个同款元素逐个悬停。 */
  const identity = (el) => el.tagName.toLowerCase() + '.' + [...el.classList].sort().join('.');

  /* ── 扫描有直接文字的元素 ────────────────────────────────── */
  const out = [];
  let scanned = 0;
  ALL.forEach(el => {
    const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!ownText) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const fg = px(cs.color);
    if (!fg) return;
    if (isInactive(el)) return;          /* 非活动组件豁免，不计入判据 */
    scanned++;
    const alpha = alphaOf(el);
    const inner = bgOf(el);              /* 元素这一组（含自身底色）的实底 */
    const outer = outerOf(el);           /* 元素身后的底色 */
    let bg, fgOver;
    if (alpha > 0.999) {
      bg = inner;
      fgOver = fg.a < 1 ? over(fg, { c: bg, a: 1 }) : fg.c;
    } else {
      /* 元素整体以 alpha 混到身后底色上：文字像素 = a·文字 + (1-a)·身后底色 */
      const painted = fg.a < 1 ? over(fg, { c: inner, a: 1 }) : fg.c;
      bg = [0, 1, 2].map(i => alpha * inner[i] + (1 - alpha) * outer[i]);
      fgOver = [0, 1, 2].map(i => alpha * painted[i] + (1 - alpha) * outer[i]);
    }
    const ratio = cr(fgOver, bg);
    const size = parseFloat(cs.fontSize);
    const bold = +cs.fontWeight >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    if (ratio < need) {
      out.push({
        sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
              (el.className && typeof el.className === 'string' && el.className.trim()
                ? '.' + el.className.trim().split(/\s+/).join('.') : ''),
        alpha: +alpha.toFixed(3),
        txt: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 26),
        ratio: +ratio.toFixed(3), need, size,
        color: cs.color, bg: 'rgb(' + bg.map(v => Math.round(v)).join(',') + ')'
      });
    }
  });
  /* ── 表单控件边界：非文字对比度（WCAG 1.4.11）─────────────────────
     输入框/下拉框的描边是「认出这是个输入框」的唯一视觉依据，须与**相邻底色**
     （控件之外那层，从父元素起合成）≥3:1。卡片、chip、按钮的描边属装饰
     （控件内有文字或图标作识别依据），不在此限。 */
  const parentBg = (el) => outerOf(el);
  const controls = [];
  document.querySelectorAll('input,select,textarea').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 && r.height < 1) return;
    const bw = parseFloat(cs.borderTopWidth) || 0;
    if (!bw) return;                       /* 无边框的原生控件（range）不在此判据内 */
    const bc = px(cs.borderTopColor);
    if (!bc || bc.a < 0.5) return;
    const bg = parentBg(el);
    const fg = bc.a < 1 ? over(bc, { c: bg, a: 1 }) : bc.c;
    const name = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
      (typeof el.className === 'string' && el.className.trim()
        ? '.' + el.className.trim().split(/\s+/)[0] : '');
    controls.push({ name, ratio: +cr(fg, bg).toFixed(2) });
  });

  /* ── 图标控件：非文字对比度（WCAG 1.4.11，须 ≥3:1）──────────────
     只判「图标是唯一识别依据」的控件（按钮/链接里除图标外没有文字）：
     有文字标签时图标属装饰，1.4.11 明列装饰豁免。
     图标用 stroke="currentColor" 描边 ⇒ 颜色取元素的 computed color；
     控件整体的 opacity 会把描边一起淡出，故按祖先链透明度合成后再比。 */
  const icons = [];
  ALL.filter(el => el.tagName.toLowerCase() === 'svg').forEach(svg => {
    const ctl = svg.closest('button,a');
    if (!ctl) return;
    const hasText = [...ctl.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (hasText) return;                      /* 有文字标签 ⇒ 图标属装饰 */
    const cs = getComputedStyle(svg);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = svg.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const stroke = svg.getAttribute('stroke') || '';
    if (stroke && stroke !== 'currentColor' && stroke !== 'none') {
      const sc = px(stroke);
      if (!sc) return;                         /* 颜色写死在属性上，另行处理 */
    }
    const fg = px(cs.color);
    if (!fg) return;
    const bg = bgOf(ctl);
    const alpha = alphaOf(ctl);
    const painted = fg.a < 1 ? over(fg, { c: bg, a: 1 }) : fg.c;
    const eff = alpha > 0.999 ? painted
              : painted.map((v, i) => alpha * v + (1 - alpha) * bg[i]);
    const name = ctl.tagName.toLowerCase() + (ctl.id ? '#' + ctl.id : '') +
      (typeof ctl.className === 'string' && ctl.className.trim()
        ? '.' + ctl.className.trim().split(/\s+/)[0] : '');
    icons.push({ name, ratio: +cr(eff, bg).toFixed(2), color: cs.color, alpha: +alpha.toFixed(2),
                 bg: 'rgb(' + bg.map(v => Math.round(v)).join(',') + ')' });
  });

  /* ── 悬停态候选：按「展示身份」去重 ─────────────────────────── */
  const hoverKeys = [];
  const seenKey = new Set();
  ALL.forEach(el => {
    const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!ownText) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const k = identity(el);
    if (seenKey.has(k)) return;
    seenKey.add(k);
    hoverKeys.push(k);
  });

  return { out, scanned, controls, icons, hoverKeys };
}
"""

# ── 第四十九轮：悬停态量测 ──────────────────────────────────────────
# 量「被悬停的那个元素」+「它的子树」+「它的祖先链」：
#   · 子树：父元素的 :hover 会改子元素颜色（例 .quick-btn:hover .qb）
#   · 祖先链：:hover 会改祖先底色（例 .word-table tbody tr:hover 给整行铺 accent-soft）
HOVER_TAG_JS = r"""
(o) => {
  const k = o.k, scope = o.scope;
  document.querySelectorAll('[data-wl-hv]').forEach(e => e.removeAttribute('data-wl-hv'));
  const roots = [...document.querySelectorAll(scope || '#main')];
  const all = [];
  for (const r of roots) { all.push(r); r.querySelectorAll('*').forEach(e => all.push(e)); }
  const list = all.filter(el => {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!own) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    return el.tagName.toLowerCase() + '.' + [...el.classList].sort().join('.') === k;
  });
  if (!list.length) return false;
  list[0].setAttribute('data-wl-hv', '1');
  return true;
}
"""

HOVER_MEASURE_JS = r"""
() => {
  const root = document.querySelector('[data-wl-hv]');
  if (!root) return [];
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
  const over = (fg, bg) => [0, 1, 2].map(i => fg.c[i] * fg.a + bg.c[i] * (1 - fg.a));
  const lum = (c) => {
    const f = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  };
  const cr = (a, b) => { const l1 = lum(a), l2 = lum(b); const hi = Math.max(l1, l2), lo = Math.min(l1, l2); return (hi + 0.05) / (lo + 0.05); };
  const gradOpaque = (el) => {
    const bi = getComputedStyle(el).backgroundImage;
    if (!bi || bi === 'none') return null;
    const ms = bi.match(/color\(srgb [^)]+\)|rgba?\([^)]+\)/g) || [];
    for (const m of ms) { const c = px(m); if (c && c.a >= 0.99) return c; }
    return null;
  };
  const stackBg = (start) => {
    const layers = [];
    let n = start, base = null;
    while (n && n !== document.documentElement) {
      const g = gradOpaque(n);
      if (g) { base = { c: g.c, a: 1 }; break; }
      const c = px(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) { base = { c: c.c, a: 1 }; break; } }
      n = n.parentElement;
    }
    if (!base) {
      const b = px(getComputedStyle(document.body).backgroundColor);
      base = b && b.a > 0 ? b : { c: [255, 255, 255], a: 1 };
    }
    let acc = base.c;
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], { c: acc, a: 1 });
    return acc;
  };
  const alphaOf = (el) => {
    let a = 1, n = el;
    while (n && n !== document.documentElement) { a *= parseFloat(getComputedStyle(n).opacity) || 1; n = n.parentElement; }
    return a;
  };
  const isInactive = (el) => !!(el.closest && el.closest('[disabled],[aria-disabled="true"]'));

  const cands = new Set();
  cands.add(root);
  root.querySelectorAll('*').forEach(e => cands.add(e));
  for (let n = root.parentElement; n && n !== document.documentElement; n = n.parentElement) cands.add(n);

  const out = [];
  cands.forEach(el => {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!own) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const fg = px(cs.color);
    if (!fg) return;
    if (isInactive(el)) return;
    const alpha = alphaOf(el);
    const inner = stackBg(el);
    const outer = stackBg(el.parentElement);
    let bg, fgOver;
    if (alpha > 0.999) {
      bg = inner;
      fgOver = fg.a < 1 ? over(fg, { c: bg, a: 1 }) : fg.c;
    } else {
      const painted = fg.a < 1 ? over(fg, { c: inner, a: 1 }) : fg.c;
      bg = [0, 1, 2].map(i => alpha * inner[i] + (1 - alpha) * outer[i]);
      fgOver = [0, 1, 2].map(i => alpha * painted[i] + (1 - alpha) * outer[i]);
    }
    const ratio = cr(fgOver, bg);
    const size = parseFloat(cs.fontSize);
    const bold = +cs.fontWeight >= 700;
    const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
    if (ratio < need) {
      out.push({
        sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
             (typeof el.className === 'string' && el.className.trim()
               ? '.' + el.className.trim().split(/\s+/).join('.') : ''),
        txt: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 26),
        ratio: +ratio.toFixed(3), need, size,
        color: cs.color, bg: 'rgb(' + bg.map(v => Math.round(v)).join(',') + ')'
      });
    }
  });
  return out;
}
"""

# ── 第五十轮：判题反馈面板的两种底色（绿 ok / 红 no）──────────────
# 面板底色由「答对与否」决定，而作答对错是**随机**的 ⇒ 只量到随机的那一种，
# 判据就成了掷骰子。这里把真实渲染出来的面板在 ok / no 两个类之间各量一次
# （改的是面板自己的 class，文字与样式都是真实应用里的那一份），
# 使「两种底色都必须过线」成为确定性判据。
FEEDBACK_PANEL_JS = r"""
() => {
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
  const lum = (c) => {
    const f = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  };
  const cr = (a, b) => { const l1 = lum(a), l2 = lum(b); const hi = Math.max(l1, l2), lo = Math.min(l1, l2); return (hi + 0.05) / (lo + 0.05); };
  const panel = document.querySelector('.quiz-feedback');
  if (!panel) return [{ sel: '.quiz-feedback', txt: '判题反馈面板未出现', ratio: 0, need: 4.5, color: '-', bg: '-' }];
  const orig = panel.className;
  const out = [];
  for (const v of ['ok', 'no']) {
    panel.className = 'quiz-feedback show ' + v;
    const el = panel.querySelector('.faint');
    if (!el) { out.push({ sel: '.quiz-feedback.' + v, txt: '面板内没有释义小字', ratio: 0, need: 4.5, color: '-', bg: '-' }); continue; }
    const fg = px(getComputedStyle(el).color);
    const bg = px(getComputedStyle(panel).backgroundColor);
    if (!fg || !bg) continue;
    const ratio = cr(fg.c, bg.c);
    if (ratio < 4.5) {
      out.push({ sel: '.quiz-feedback.' + v + ' .faint', txt: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 24),
                 ratio: +ratio.toFixed(3), need: 4.5,
                 color: getComputedStyle(el).color,
                 bg: 'rgb(' + bg.c.map(v => Math.round(v)).join(',') + ')' });
    }
  }
  panel.className = orig;
  return out;
}
"""


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def uniq_failures(res):
    """同一 (选择器, 颜色, 背景) 只记一次，避免同一规则刷屏"""
    seen = set()
    uniq = []
    for r in res:
        k = (r["sel"], r["color"], r["bg"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


def scan_scope(page, scope, label, prefix, fails):
    """对给定范围做「常态 + 悬停态」两轮扫描（第五十轮：范围可切换）。

    范围＝scope 选择器命中的容器及其全部后代。常态按 WCAG 1.4.3 判文字对比度，
    悬停态逐个真悬停后量「被悬停元素＋其子树＋其祖先链」。
    返回 (常态失败数, 悬停失败数)，失败同时记进 fails。
    """
    got = page.evaluate(SWEEP_JS, scope)
    res = got["out"]
    if res:
        uniq = uniq_failures(res)
        fails.append(f"[{prefix}] {label}：{len(res)} 处文字低于 AA（去重 {len(uniq)} 类）")
        print(f"  ✗ {label:16s} {len(res)} 处低于 AA（去重 {len(uniq)}）")
        for r in uniq[:12]:
            print(f"      {r['ratio']:6.3f} < {r['need']}  {r['sel'][:44]:44s} "
                  f"{r['color']} on {r['bg']}  「{r['txt']}」")
    else:
        print(f"  ✓ {label:16s} 全部文字过线（扫描 {got['scanned']} 处文字）")
    # 第五十七轮（守卫诚实度）：扫到 0 处文字时「全部过线」也是真的 ⇒ 判据空转
    if got.get("scanned", 0) < MIN_SCANNED:
        fails.append(f"[{prefix}] {label}：只扫到 {got.get('scanned', 0)} 处文字（判据空转）")
        print(f"  ✗ {label:16s} 只扫到 {got.get('scanned', 0)} 处文字，判据空转")

    hover_bad = []
    hovered = 0
    for k in got.get("hoverKeys", []):
        if not page.evaluate(HOVER_TAG_JS, {'k': k, 'scope': scope}):
            continue
        try:
            loc = page.locator("[data-wl-hv]").first
            loc.scroll_into_view_if_needed(timeout=1500)
            loc.hover(timeout=2500)
        except Exception:
            continue
        page.wait_for_timeout(120)   # 过渡已冻结，仅等一帧让 :hover 生效
        hovered += 1
        hover_bad.extend(page.evaluate(HOVER_MEASURE_JS))
    if hover_bad:
        uniq = uniq_failures(hover_bad)
        fails.append(f"[{prefix}] {label}：{len(hover_bad)} 处悬停态文字低于 AA"
                     f"（去重 {len(uniq)} 类）")
        print(f"  ✗ {label:16s} {len(hover_bad)} 处悬停态低于 AA"
              f"（去重 {len(uniq)}，悬停 {hovered} 处）")
        for r in uniq[:12]:
            print(f"      {r['ratio']:6.3f} < {r['need']}  {r['sel'][:44]:44s} "
                  f"{r['color']} on {r['bg']}  「{r['txt']}」")
    else:
        print(f"  ✓ {label:16s} 悬停态全部过线（悬停 {hovered} 处）")
    # 同上：悬停 0 处时「悬停态全部过线」也是真的 ⇒ 判据空转
    if hovered < MIN_HOVERED:
        fails.append(f"[{prefix}] {label}：悬停态一个元素都没量到（判据空转）")
        print(f"  ✗ {label:16s} 悬停态量到 0 处，判据空转")
    return got


def main():
    srv, port = serve()
    time.sleep(0.3)
    from playwright.sync_api import sync_playwright

    fails = []
    checked = 0
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
                # 主题走应用自己的设置项（localStorage seed → 真实设置页路径），
                # 不再依赖 prefers-color-scheme：应用已不跟随系统。
                ctx = browser.new_context(viewport={"width": 1280, "height": 900})
                ctx.add_init_script(
                    "try{var s=JSON.parse(localStorage.getItem('wl_state_v1')||'{}');"
                    "s.settings=s.settings||{};s.settings.theme='%s';"
                    "localStorage.setItem('wl_state_v1',JSON.stringify(s));}catch(e){}" % theme)
                page = ctx.new_page()
                print(f"== 主题 {theme} ==")
                ctrls = {}          # 控件名 → 最差比值（同一控件跨视图只记最差）
                icons = {}          # 图标控件名 → 最差比值
                for v in VIEWS:
                    page.goto(f"http://127.0.0.1:{port}/index.html#{v}", wait_until="load")
                    page.wait_for_timeout(500)
                    page.evaluate(FREEZE_JS)     # 量最终态，不量动画中间态
                    got = page.evaluate(SWEEP_JS)
                    res, scanned = got['out'], got['scanned']
                    for c in got.get('controls', []):
                        k = c["name"]
                        if k not in ctrls or c["ratio"] < ctrls[k]:
                            ctrls[k] = c["ratio"]
                    for c in got.get('icons', []):
                        k = c["name"]
                        if k not in icons or c["ratio"] < icons[k]:
                            icons[k] = c["ratio"]
                    checked += 1
                    if not res:
                        print(f"  ✓ {v:9s} 全部文字过线（扫描 {scanned} 处文字）")
                    else:
                        uniq = uniq_failures(res)
                        fails.append(f"[{theme}] {v}：{len(res)} 处文字低于 AA（去重 {len(uniq)} 类）")
                        print(f"  ✗ {v:9s} {len(res)} 处低于 AA（去重 {len(uniq)}）")
                        for r in uniq[:12]:
                            print(f"      {r['ratio']:6.3f} < {r['need']}  {r['sel'][:44]:44s} {r['color']} on {r['bg']}  「{r['txt']}」")
                    # 第五十七轮（守卫诚实度）：「全部文字过线」在扫到 0 处文字时
                    # 也是真的 ⇒ 判据空转。现在给扫描量加下限（实测最少的是
                    # 收藏空态 8 处），扫不出东西即判红。
                    checked += 1
                    if scanned < MIN_SCANNED:
                        fails.append(f"[{theme}] {v}：只扫到 {scanned} 处文字（判据空转）")
                        print(f"  ✗ {v:9s} 只扫到 {scanned} 处文字，判据空转")

                    # ── 悬停态扫描（第四十九轮新增）────────────────────
                    hover_bad = []
                    hovered = 0
                    for k in got.get('hoverKeys', []):
                        if not page.evaluate(HOVER_TAG_JS, {'k': k, 'scope': '#main'}):
                            continue
                        try:
                            loc = page.locator("[data-wl-hv]").first
                            loc.scroll_into_view_if_needed(timeout=1500)
                            loc.hover(timeout=2500)
                        except Exception:
                            continue
                        page.wait_for_timeout(120)   # 过渡已冻结，仅等一帧让 :hover 生效
                        hovered += 1
                        for r in page.evaluate(HOVER_MEASURE_JS):
                            hover_bad.append(r)
                    checked += 1
                    if not hover_bad:
                        print(f"  ✓ {v:9s} 悬停态全部过线（悬停 {hovered} 处）")
                    else:
                        uniq = uniq_failures(hover_bad)
                        fails.append(f"[{theme}] {v}：{len(hover_bad)} 处悬停态文字低于 AA（去重 {len(uniq)} 类）")
                        print(f"  ✗ {v:9s} {len(hover_bad)} 处悬停态低于 AA（去重 {len(uniq)}，悬停 {hovered} 处）")
                        for r in uniq[:12]:
                            print(f"      {r['ratio']:6.3f} < {r['need']}  {r['sel'][:44]:44s} {r['color']} on {r['bg']}  「{r['txt']}」")
                    # 同上：悬停态「全部过线」在悬停 0 处时也是真的 ⇒ 判据空转。
                    checked += 1
                    if hovered < MIN_HOVERED:
                        fails.append(f"[{theme}] {v}：悬停态一个元素都没量到（判据空转）")
                        print(f"  ✗ {v:9s} 悬停态量到 0 处，判据空转")
                # ── 第五十轮：**交互态**视图纳入扫描口径 ──────────────
                # 只 goto 视图只能量到「冷启动」那一屏：测验进行中的题干、
                # 已作答的判定配色、闪卡翻面后的释义面，都是运行时才出现的
                # DOM ⇒ 原口径压根没量过（例如 .quiz-mode-badge 的
                # accent 压 accent-soft 就是这样漏掉的）。
                page.goto(f"http://127.0.0.1:{port}/index.html#quiz", wait_until="load")
                page.wait_for_timeout(600)
                page.evaluate(FREEZE_JS)
                if page.locator("#startQuiz").count() == 0:
                    fails.append(f"[{theme}] 视图·测验中：找不到「开始测验」按钮（判据空转）")
                    print("  ✗ 视图·测验中          找不到「开始测验」按钮（判据空转）")
                    got = {"icons": []}
                else:
                    page.click("#startQuiz")
                    page.wait_for_timeout(700)
                    got = scan_scope(page, "#main", "视图·测验中", theme, fails)
                for c in got.get("icons", []):
                    k = c["name"]
                    if k not in icons or c["ratio"] < icons[k]:
                        icons[k] = c["ratio"]
                checked += 2
                if page.locator(".quiz-opt").count() == 0:
                    fails.append(f"[{theme}] 视图·已作答：测验未出题（判据空转）")
                    print("  ✗ 视图·已作答          测验未出题（判据空转）")
                    got = {"icons": []}
                else:
                    page.click(".quiz-opt")
                    page.wait_for_timeout(600)
                    got = scan_scope(page, "#main", "视图·已作答", theme, fails)
                # 判题反馈面板的两种底色各量一次（确定性判据，不受随机作答影响）
                fb = page.evaluate(FEEDBACK_PANEL_JS)
                checked += 1
                if not fb:
                    print(f"  ✓ {theme:6s} 判题反馈面板（绿底/红底）释义小字均 ≥4.5:1")
                else:
                    fails.append(f"[{theme}] 视图·判题反馈面板：{len(fb)} 处低于 AA")
                    print(f"  ✗ {theme:6s} 判题反馈面板：{len(fb)} 处低于 AA")
                    for r in fb[:6]:
                        print(f"      {r['ratio']:6.3f} < {r['need']}  {r['sel'][:44]:44s} {r['color']} on {r['bg']}  「{r['txt']}」")
                for c in got.get("icons", []):
                    k = c["name"]
                    if k not in icons or c["ratio"] < icons[k]:
                        icons[k] = c["ratio"]
                checked += 2

                page.goto(f"http://127.0.0.1:{port}/index.html#cards", wait_until="load")
                page.wait_for_timeout(600)
                page.evaluate(FREEZE_JS)
                # 「全部词库」这一档恒有词（其它档位在空档案下可能是 0，点不进去）
                page.click(".chip[data-s=\"all\"]")
                page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
                page.wait_for_timeout(900)
                if page.locator("#fcReveal").count() == 0:
                    fails.append(f"[{theme}] 视图·闪卡背面：未能进入闪卡会话（判据空转）")
                    print("  ✗ 视图·闪卡背面        未能进入闪卡会话（判据空转）")
                    got = {"icons": []}
                else:
                    page.click("#fcReveal")
                    page.wait_for_timeout(600)
                    got = scan_scope(page, "#main", "视图·闪卡背面", theme, fails)
                for c in got.get("icons", []):
                    k = c["name"]
                    if k not in icons or c["ratio"] < icons[k]:
                        icons[k] = c["ratio"]
                checked += 2

                # ── 第五十轮：页眉/页脚/浮层纳入扫描口径 ──────────────
                # 它们都是 <main id="main"> 的**兄弟节点**，原口径只扫
                # `#main *` ⇒ 页眉品牌与主导航、页脚、三个浮层的文字与
                # 悬停态**从未被量过**（第四十九轮的悬停扫描同样照不到）。
                page.goto(f"http://127.0.0.1:{port}/index.html#home", wait_until="load")
                page.wait_for_timeout(500)
                page.evaluate(FREEZE_JS)
                got = scan_scope(page, ".topbar, .footer", "页眉/页脚", theme, fails)
                for c in got.get("icons", []):
                    k = c["name"]
                    if k not in icons or c["ratio"] < icons[k]:
                        icons[k] = c["ratio"]
                checked += 2

                # 浮层：搜索（有结果）、词条详情、键盘快捷键
                page.goto(f"http://127.0.0.1:{port}/index.html#browse", wait_until="load")
                page.wait_for_timeout(500)
                page.evaluate(FREEZE_JS)
                overlays = [
                    ("浮层·搜索", "#searchOverlay",
                     lambda: (page.click("#btnSearch"), page.wait_for_timeout(300),
                              page.fill("#searchInput", "ab"), page.wait_for_timeout(600)),
                     lambda: (page.keyboard.press("Escape"), page.wait_for_timeout(200))),
                    ("浮层·词条详情", "#wordModal",
                     lambda: (page.evaluate("window.WL_DEBUG.openWordModal(1)"),
                              page.wait_for_timeout(600)),
                     lambda: (page.click("#wmClose"), page.wait_for_timeout(200))),
                    ("浮层·快捷键", "#shortcutsOverlay",
                     lambda: (page.evaluate("window.WL_DEBUG.openShortcuts()"), page.wait_for_timeout(400)),
                     lambda: (page.click("#scClose"), page.wait_for_timeout(200))),
                ]
                for label, scope, open_it, close_it in overlays:
                    open_it()
                    got = scan_scope(page, scope, label, theme, fails)
                    for c in got.get("controls", []):
                        k = c["name"]
                        if k not in ctrls or c["ratio"] < ctrls[k]:
                            ctrls[k] = c["ratio"]
                    for c in got.get("icons", []):
                        k = c["name"]
                        if k not in icons or c["ratio"] < icons[k]:
                            icons[k] = c["ratio"]
                    close_it()
                    checked += 2

                # ── 非文字对比度：表单控件边界（WCAG 1.4.11，须 ≥3:1）──
                bad = {k: r for k, r in ctrls.items() if r < 3}
                checked += 1
                if not ctrls:
                    fails.append(f"[{theme}] 未采集到任何表单控件边界，判据空转")
                    print("  ✗ 表单控件边界：未采集到控件（判据空转）")
                elif bad:
                    fails.append(f"[{theme}] {len(bad)} 处表单控件边界低于 3:1")
                    print(f"  ✗ 表单控件边界 {len(bad)} 处低于 3:1（采集 {len(ctrls)} 个）")
                    for k, r in sorted(bad.items(), key=lambda kv: kv[1])[:12]:
                        print(f"      {r:6.2f} < 3  {k}")
                else:
                    print(f"  ✓ 表单控件边界全部 ≥3:1（采集 {len(ctrls)} 个，最差 {min(ctrls.values()):.2f}）")
                # ── 非文字对比度：图标控件（WCAG 1.4.11，须 ≥3:1）────
                bad = {k: r for k, r in icons.items() if r < 3}
                checked += 1
                if not icons:
                    fails.append(f"[{theme}] 未采集到任何图标控件，判据空转")
                    print("  ✗ 图标控件：未采集到图标（判据空转）")
                elif bad:
                    fails.append(f"[{theme}] {len(bad)} 处图标控件低于 3:1")
                    print(f"  ✗ 图标控件 {len(bad)} 处低于 3:1（采集 {len(icons)} 个）")
                    for k, r in sorted(bad.items(), key=lambda kv: kv[1])[:12]:
                        print(f"      {r:6.2f} < 3  {k}")
                else:
                    print(f"  ✓ 图标控件全部 ≥3:1（采集 {len(icons)} 个，最差 {min(icons.values()):.2f}）")
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
