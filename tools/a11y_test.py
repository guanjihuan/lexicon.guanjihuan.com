#!/usr/bin/env python3
"""无障碍语义回归测试（界面自序第三十八轮）

在真实浏览器里检查「读屏能不能读懂」这一类结构性事实：
  · 标题层级不跳级（页面 h1 之后直接 h2，不出现 h1→h3）
  · 测验反馈区是 live 区，答题后有内容可播报
  · 闪卡翻面后卡面的可访问名会更新（否则读屏用户翻面听不到任何新内容）
  · 隐藏的文件选择器、词条弹窗、搜索列表框的语义正确
  · 触控目标尺寸（WCAG 2.2 · SC 2.5.8）、触控目标不小于 24×24 CSS px
  · 320px 宽下能回流（WCAG 1.4.10）、用户加大字间距后内容不被裁切（WCAG 1.4.12）

运行： python3 tools/a11y_test.py
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

# 触控目标尺寸扫描（WCAG 2.2 · SC 2.5.8）：非行内的交互元素不得小于 24×24 CSS px。
# 「行内」豁免：夹在句子文字中的链接（父元素文本明显多于自身文本）不在此限。
TARGET_JS = r"""
() => {
  const out = [];
  const sel = 'button,a[href],input,select,textarea,[role="button"],[role="tab"],summary';
  document.querySelectorAll(sel).forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 && r.height < 1) return;
    const p = el.parentElement;
    const inlineInText = el.tagName === 'A' && p &&
      p.textContent.trim().length > el.textContent.trim().length + 12;
    if (inlineInText) return;
    if (r.height < 24 || r.width < 24) {
      const name = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
        (typeof el.className === 'string' && el.className.trim()
          ? '.' + el.className.trim().split(/\s+/)[0] : '');
      out.push(name + ' ' + Math.round(r.width) + '×' + Math.round(r.height));
    }
  });
  return out;
}
"""


# 回流扫描（WCAG 1.4.10）：320 CSS px 宽下不得出现横向滚动，也不得有元素
# 越出视口右缘（内容被切掉 = 实质丢失）。
REFLOW_JS = r"""
() => {
  const de = document.documentElement;
  const over = [];
  document.querySelectorAll('#main *, .topbar *, .footer *, #searchOverlay *, #wordModal *, #shortcutsOverlay *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width < 1) return;
    if (r.right > de.clientWidth + 1) {
      over.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
        (typeof el.className === 'string' && el.className.trim()
          ? '.' + el.className.trim().split(/\s+/)[0] : '') +
        ' right=' + Math.round(r.right) + '/' + de.clientWidth);
    }
  });
  return { docScroll: de.scrollWidth - de.clientWidth, over: over.slice(0, 4) };
}
"""

# 文字间距扫描（WCAG 1.4.12）：按规范注入「用户可覆盖」的间距值后，
# 内容不得被 overflow:hidden 的祖先裁掉。只看**真实元素子节点**是否越出
# 裁切框——伪元素（装饰圆等）不算，否则 .hero 的 ::before/::after 会被误判。
SPACING_JS = r"""
() => {
  const st = document.createElement('style');
  st.id = '__wl_text_spacing';
  st.textContent = '*,*::before,*::after{line-height:1.5!important;letter-spacing:0.12em!important;' +
    'word-spacing:0.16em!important}p{margin-bottom:2em!important}';
  document.head.appendChild(st);
  const bad = [];
  document.querySelectorAll('#main *, .topbar *, .footer *, #searchOverlay *, #wordModal *, #shortcutsOverlay *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width < 1 && r.height < 1) return;
    const hidY = cs.overflowY === 'hidden' || cs.overflowY === 'clip';
    const hidX = cs.overflowX === 'hidden' || cs.overflowX === 'clip';
    if (!hidY && !hidX) return;
    for (const c of el.children) {
      const cr = c.getBoundingClientRect();
      if (cr.width < 1 && cr.height < 1) continue;
      const dy = hidY ? cr.bottom - r.bottom : 0;
      const dx = hidX ? cr.right - r.right : 0;
      if (dy > 2 || dx > 2) {
        bad.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
          (typeof el.className === 'string' && el.className.trim()
            ? '.' + el.className.trim().split(/\s+/)[0] : '') +
          ' 超出 ' + Math.round(Math.max(dy, dx)) + 'px');
        break;
      }
    }
  });
  st.remove();
  return bad.slice(0, 4);
}
"""


# 键盘焦点扫描（WCAG 2.2 · SC 2.4.11 焦点不被遮挡 / SC 2.4.7 焦点可见）：
# 逐个 Tab 走完可聚焦元素，要求每次的焦点元素
#   ① 完整落在视口内（没被切掉半个）
#   ② 中心点没有被别的元素压住（吸顶顶栏、移动端底部固定标签栏）
# 判定用 elementFromPoint 看「谁在最上层」——只看几何重叠会把
# 「焦点元素自己的祖先/子节点」误判成遮挡。
FOCUS_JS = r"""
() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const r = el.getBoundingClientRect();
  if (r.width < 1 && r.height < 1) return null;
  const cx = Math.round(Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1));
  const cy = Math.round(Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 1));
  const top = document.elementFromPoint(cx, cy);
  const covered = !(top === el || (top && el.contains(top)));
  const inView = r.top >= 0 && r.bottom <= innerHeight;
  const name = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/)[0] : '');
  return {
    name: name,
    text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 16),
    top: Math.round(r.top), bot: Math.round(r.bottom),
    inView: inView, covered: covered,
    topEl: top ? top.tagName.toLowerCase() + '.' +
      String(top.className || '').split(/\s+/)[0] : null
  };
}
"""


# 聚焦指示器对比度扫描（WCAG 2.2 · SC 2.4.7 焦点可见 / SC 1.4.11 非文字对比度）：
# 表单控件聚焦时若只有一环浅色阴影（1.1~1.6:1），键盘用户根本看不出焦点在哪。
# 判据：**聚焦相对未聚焦**必须有可见变化（描边色 / outline / 阴影环之一），
# 且变化后的指示器与**相邻底色**达到 3:1。相邻底色 = 控件父元素起逐层合成的底色
# （outline 画在控件外圈，落在父元素那一层上）。
# 只量「聚焦态的绝对值」是不够的：未聚焦时那条 1px 描边本就有 3.2:1，
# 若不与未聚焦态比对，会把「聚焦了但看不出变化」判成通过。
FOCUS_SNAP_JS = r"""
() => {
  const list = [...document.querySelectorAll('input,select,textarea')];
  return list.map((el, i) => {
    const cs = getComputedStyle(el);
    return {
      i: i,
      name: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
        (typeof el.className === 'string' && el.className.trim()
          ? '.' + el.className.trim().split(/\s+/)[0] : ''),
      outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor,
      border: cs.borderTopColor,
      shadow: cs.boxShadow
    };
  });
}
"""

# 可见表单控件清单（与 FOCUS_SNAP_JS 的 name 拼法一致，便于逐个对照）：
# 焦点指示器那条守卫要证明「每个能被键盘聚焦的控件都量过」，
# 光有「量到几个」不够 —— 必须与实际控件清单一一对上。
FORM_CTRL_JS = r"""
() => {
  const list = [...document.querySelectorAll('input,select,textarea')];
  return list.filter(el => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 &&
      cs.visibility !== 'hidden' && cs.display !== 'none';
  }).map(el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/)[0] : ''));
}
"""

FOCUS_IND_JS = r"""
(snap) => {
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

  const el = document.activeElement;
  if (!el || el === document.body) return null;
  if (!/^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)) return null;
  const list = [...document.querySelectorAll('input,select,textarea')];
  const idx = list.indexOf(el);
  if (idx < 0 || !snap || !snap[idx]) return null;
  const before = snap[idx];
  const cs = getComputedStyle(el);
  const adj = bgOf(el.parentElement || el);
  const ind = [];

  const outlineNow = cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor;
  if (outlineNow !== before.outline && cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) {
    const oc = px(cs.outlineColor);
    if (oc) ind.push({ kind: 'outline', cr: +cr(oc.a < 1 ? over(oc, { c: adj, a: 1 }) : oc.c, adj).toFixed(2) });
  }
  if (cs.borderTopColor !== before.border && parseFloat(cs.borderTopWidth) > 0) {
    const bc = px(cs.borderTopColor);
    if (bc && bc.a > 0.05) ind.push({ kind: 'border', cr: +cr(bc.a < 1 ? over(bc, { c: adj, a: 1 }) : bc.c, adj).toFixed(2) });
  }
  if (cs.boxShadow !== before.shadow && cs.boxShadow && cs.boxShadow !== 'none') {
    const cm = cs.boxShadow.match(/rgba?\([^)]+\)|color\(srgb[^)]+\)/);
    if (cm) {
      const c = px(cm[0]);
      if (c) ind.push({ kind: 'ring', cr: +cr(c.a < 1 ? over(c, { c: adj, a: 1 }) : c.c, adj).toFixed(2) });
    }
  }
  const best = ind.length ? Math.max.apply(null, ind.map(x => x.cr)) : 0;
  return { name: before.name, best: best, ind: ind };
}
"""

# 「颜色不单独承载信息」（WCAG 1.4.1）与 Windows 高对比度（forced-colors）探针。
# forced-colors 模式下系统接管全部背景/边框色，只靠颜色区分的状态会全部塌缩；
# 故这里量的不是颜色，而是**与颜色无关的第二通道**：描边（宽度/线型）、边框宽/线型、
# 文字装饰线、以及图形标记（::after content）。
FORCE_MARK_JS = r"""
() => {
  const q = s => document.querySelector(s);
  const after = el => el ? getComputedStyle(el, '::after').content : 'missing';
  const ca = after(q('.quiz-opt.correct'));
  const wa = after(q('.quiz-opt.wrong'));
  const da = after(q('.quiz-opt.dim'));
  const real = s => s && s !== 'none' && s !== 'normal' && s !== 'missing';
  const ok = real(ca) && real(wa) && ca !== wa && !real(da);
  return { ok: ok, info: 'correct=' + ca + ' wrong=' + wa + ' dim=' + da };
}
"""

FORCE_CHIP_JS = r"""
() => {
  const sig = el => {
    const cs = getComputedStyle(el);
    return JSON.stringify({
      ol: cs.outlineStyle === 'none' ? '' : cs.outlineWidth + '/' + cs.outlineStyle,
      bw: cs.borderTopWidth + '/' + cs.borderTopStyle,
      deco: cs.textDecorationLine,
      op: cs.opacity
    });
  };
  const pairs = [['.chip.on', '.chip:not(.on)'], ['.nav-item.active', '.nav-item:not(.active)']];
  const bad = [], info = [];
  for (const [selOn, selOff] of pairs) {
    const on = document.querySelector(selOn), off = document.querySelector(selOff);
    if (!on || !off) { bad.push(selOn + '(缺元素)'); info.push(selOn + ':missing'); continue; }
    const a = sig(on), b = sig(off);
    info.push(selOn + ' on=' + a + ' off=' + b);
    if (a === b) bad.push(selOn + ' 与未选中态完全相同');
  }
  return { diff: !bad.length, info: info.join(' | ') + (bad.length ? ' ⇒ ' + bad.join(';') : '') };
}
"""

FORCE_OPT_JS = r"""
() => {
  const q = s => document.querySelector(s);
  const sig = el => {
    if (!el) return 'missing';
    const cs = getComputedStyle(el);
    return JSON.stringify({
      ol: cs.outlineStyle === 'none' ? '' : cs.outlineWidth + '/' + cs.outlineStyle,
      bw: cs.borderTopWidth + '/' + cs.borderTopStyle,
      op: cs.opacity
    });
  };
  const c = sig(q('.quiz-opt.correct'));
  const w = sig(q('.quiz-opt.wrong'));
  const d = sig(q('.quiz-opt.dim'));
  const dimEl = q('.quiz-opt.dim');
  const dimOp = dimEl ? getComputedStyle(dimEl).opacity : '1';
  const ok = c !== 'missing' && w !== 'missing' && c !== w && c !== d && w !== d;
  return { ok: ok, info: 'correct=' + c + ' wrong=' + w + ' dim=' + d, dimOpacity: dimOp };
}
"""

FORCE_HEAT_JS = r"""
() => {
  const sw = [...document.querySelectorAll('.heat-legend .heat-swatch')];
  const levels = sw.map(e => e.className + ':' + getComputedStyle(e).backgroundColor);
  const named = sw.filter(e => /(^|\s)h[1-4](\s|$)/.test(e.className))
                  .map(e => getComputedStyle(e).backgroundColor);
  const uniq = new Set(named);
  return { ok: named.length === 4 && uniq.size === 4, info: levels.join(' ') };
}
"""

# 减少动态效果扫描（WCAG 2.2 · SC 2.3.3 动画交互 / 2.2.2 暂停停止隐藏）：
# 系统里勾了「减少动态效果」后，页面的动画与过渡必须被压到近零，
# 否则前庭功能敏感的用户会被大面积位移动画晃到。
# 量的是**计算样式里的时长**（不是「动画此刻播没播完」）：
#   · animation-duration / transition-duration 必须 ≤ 0.05s
#   · 无限循环（infinite）的动画必须被改成 1 次
#   · 平滑滚动（scroll-behavior:smooth）本身也是动态效果 ⇒ 必须为 auto
# 另设**对照组**：默认（no-preference）下页面上确实存在会被压掉的动画/过渡，
# 否则上面那条可能只是「本来就没有动画」的空过。
RM_JS = r"""
() => {
  const scope = '#main, #main *, .topbar *, .footer *, #searchOverlay *, #wordModal *, #shortcutsOverlay *';
  const maxSec = (s) => {
    if (!s) return 0;
    const vs = String(s).split(',').map(x => x.trim()).filter(Boolean).map(x => {
      if (x.endsWith('ms')) return parseFloat(x) / 1000;
      if (x.endsWith('s')) return parseFloat(x);
      return 0;
    }).filter(v => !isNaN(v));
    return vs.length ? Math.max.apply(null, vs) : 0;
  };
  const tag = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/)[0] : '');
  const bad = [];
  let measured = 0, animated = 0, transitioned = 0;
  for (const el of document.querySelectorAll(scope)) {
    if (!el.getClientRects().length) continue;
    const cs = getComputedStyle(el);
    measured++;
    const name = (cs.animationName || 'none').split(',')[0].trim();
    const ad = maxSec(cs.animationDuration);
    const td = maxSec(cs.transitionDuration);
    const iter = (cs.animationIterationCount || '1').split(',')[0].trim();
    if (name !== 'none' && ad > 0.05) { animated++; bad.push(tag(el) + ' 动画 ' + ad + 's'); }
    if (td > 0.05) { transitioned++; bad.push(tag(el) + ' 过渡 ' + td + 's'); }
    if (name !== 'none' && iter === 'infinite') bad.push(tag(el) + ' 无限循环动画');
  }
  return { measured, animated, transitioned, bad: bad.slice(0, 6), nbad: bad.length,
           scroll: getComputedStyle(document.documentElement).scrollBehavior };
}
"""

# id / ARIA 引用完整性扫描：
#   · 同一个 id 出现多次 ⇒ getElementById 只认第一个，ARIA 引用会指错对象；
#   · aria-labelledby / aria-describedby / aria-controls / aria-owns / label[for]
#     指向不存在的 id ⇒ 读屏拿到空的可访问名。
# 只对**可见**元素判红（浮层没打开时它内部的 id 还没生成，属正常），
# 但 id 计数与引用计数要如实报出来，用作「判据未空转」的下限。
IDS_JS = r"""
() => {
  const vis = (el) => !!(el.getClientRects().length) && !el.closest('[hidden]');
  const byId = {};
  for (const el of document.querySelectorAll('[id]')) (byId[el.id] = byId[el.id] || []).push(el);
  const dup = [], dupHidden = [];
  for (const [k, list] of Object.entries(byId)) {
    if (list.length > 1) (list.some(vis) ? dup : dupHidden).push(k + '×' + list.length);
  }
  const dangling = [];
  let refs = 0, refsAll = 0;
  const attrs = ['aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-owns'];
  const sel = attrs.map(a => '[' + a + ']').join(',');
  for (const el of document.querySelectorAll(sel)) {
    for (const a of attrs) {
      const v = el.getAttribute(a);
      if (!v) continue;
      for (const t of v.trim().split(/\s+/)) {
        refsAll++;
        if (!vis(el)) continue;
        refs++;
        if (!document.getElementById(t)) dangling.push((el.id || el.tagName) + ' ' + a + '→' + t);
      }
    }
  }
  let labels = 0, labelsAll = 0;
  for (const el of document.querySelectorAll('label[for]')) {
    labelsAll++;
    if (!vis(el)) continue;
    labels++;
    const t = el.getAttribute('for');
    if (!document.getElementById(t)) dangling.push('label[for]→' + t);
  }
  return { nids: Object.keys(byId).length, dup, dupHidden, dangling: dangling.slice(0, 6),
           ndang: dangling.length, refs, labels, refsAll, labelsAll };
}
"""


# 控件可访问名扫描（WCAG 2.2 · SC 1.3.1 信息与关系 / SC 4.1.2 名称与值 /
# SC 2.5.3 标签名包含可见文字）：
#   ① 每个可见交互控件都要有可访问名（图标按钮靠 aria-label、文本按钮靠自身文字）；
#   ② 有**文字**标签的控件，其可访问名必须包含那段可见文字 —— 否则语音控制用户
#      念出屏幕上看到的字，控件却匹配不上（2.5.3）。
# 纯符号/图标的可见标记（如分页器的 ‹ ›、关闭键 ✕）不算「文字标签」：
# 2.5.3 针对的是文字标签，图标按钮用 aria-label 说明功能是通行做法。
LABEL_JS = r"""
() => {
  const accName = (el) => {
    const al = el.getAttribute('aria-label');
    if (al && al.trim()) return al.trim();
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const t = lb.trim().split(/\s+/).map(id => {
        const x = document.getElementById(id);
        return x ? (x.getAttribute('aria-label') || x.textContent || '') : '';
      }).join(' ').trim();
      if (t) return t;
    }
    if (el.id) {
      const lab = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (lab) return lab.textContent.trim();
    }
    const wrap = el.closest('label');
    if (wrap) return wrap.textContent.trim();
    if (el.title && el.title.trim()) return el.title.trim();
    return (el.textContent || '').trim();
  };
  const visText = (el) => {
    // 可见文字＝自身及后代的文字节点，但跳过图标（svg）与 aria-hidden 的装饰
    const parts = [];
    const walk = (n) => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3) { parts.push(c.textContent); continue; }
        if (c.nodeType !== 1) continue;
        if (c.tagName.toLowerCase() === 'svg') continue;
        if (c.getAttribute('aria-hidden') === 'true') continue;
        walk(c);
      }
    };
    walk(el);
    return parts.join(' ').replace(/\s+/g, ' ').trim();
  };
  const isWord = (s) => /[\w一-鿿぀-ヿ]/.test(s);
  const sel = 'button,a[href],input,select,textarea,[role="button"],[role="tab"],[role="option"],summary';
  const unnamed = [], mismatch = [];
  let measured = 0, wordLabels = 0;
  for (const el of document.querySelectorAll(sel)) {
    if (!el.getClientRects().length) continue;
    if (el.closest('[hidden]')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const tag = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
      (typeof el.className === 'string' && el.className.trim()
        ? '.' + el.className.trim().split(/\s+/)[0] : '');
    const name = accName(el);
    const vis = visText(el);
    measured++;
    if (!name) { unnamed.push(tag + (vis ? '「' + vis.slice(0, 16) + '」' : '')); continue; }
    if (vis && isWord(vis)) {
      /* 2.5.3 的正字口径：可见「标签」文字须含于可访问名。标签是用户用来识别
         控件的文字，不是控件内全部后代文字——词条卡里的编号（#856）、状态
         （未学）、提示（点击卡片）是元信息，整串当标签会把名字里含词本身的
         合格控件误判成不符（假红）。判据＝整体规范化后命中，或任一词级 token
         命中（不限长度——「关」vs「关」、「J 5」vs「J5」这类短标签靠整串判，
         卡片里的单词/状态词靠 token 判；token 切分只丢纯标点段）。
         select 豁免（ACT 规则 bc659b）：其可见文字是「当前选中值」，不是标签；
         option 列表是展开后的内容，整表当标签会必然误报。
         （select 仍参与上面的「无名」测量——4.1.2 的可访问名要求不受豁免影响。） */
      wordLabels++;
      if (el.tagName.toLowerCase() !== 'select') {
        const norm = s => s.toLowerCase().replace(/\s+/g, '').trim();
        const nname = norm(name);
        const tokens = vis.toLowerCase().split(/[^\w一-鿿぀-ヿ]+/).filter(Boolean);
        const hit = nname.includes(norm(vis)) || tokens.some(t => nname.includes(norm(t)));
        if (!hit) {
          mismatch.push(tag + ' 可见「' + vis.slice(0, 18) + '」 vs 名「' + name.slice(0, 24) + '」');
        }
      }
    }
  }
  return { measured, wordLabels, unnamed, mismatch };
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

    with sync_playwright() as pw:
        exe = os.environ.get("WL_CHROMIUM")
        if exe and not os.path.exists(exe):
            exe = None
        try:
            browser = pw.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}))
        except Exception:
            browser = pw.chromium.launch(headless=True, channel="chromium")
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            # ── ① 标题层级不跳级 ───────────────────────────────────────────
            print("== 标题层级 ==")
            for v in VIEWS:
                page.goto(base + "#" + v, wait_until="load")
                page.wait_for_timeout(300)
                levels = page.evaluate("""() => [...document.querySelectorAll('#main h1,#main h2,#main h3,#main h4,#main h5,#main h6')]
                    .map(h => +h.tagName[1])""")
                jumps = [(a, b) for a, b in zip(levels, levels[1:]) if b - a > 1]
                # 第五十七轮（守卫诚实度）：原写法 `not levels or levels[0]==1`
                # 把「一个标题都没量到」也判过 —— 这条守卫的本意是
                # 「首个标题必须是 h1」，空集恰好把这条意图短路掉了。
                # 现在空集单独判红，并要求首个标题就是 h1。
                check(f"{v} 视图量到标题（判据未空转）", len(levels) > 0,
                      "levels=" + ",".join(map(str, levels)))
                check(f"{v} 视图标题层级不跳级",
                      bool(levels) and not jumps and levels[0] == 1,
                      "levels=" + ",".join(map(str, levels)))

            # ── ② 测验反馈是 live 区 ───────────────────────────────────────
            print("== 测验反馈 ==")
            page.goto(base + "#quiz", wait_until="load")
            page.wait_for_timeout(300)
            page.click("#startQuiz")
            page.wait_for_timeout(400)
            live = page.evaluate("""() => { const el = document.querySelector('#qFb');
                return el ? { role: el.getAttribute('role'), live: el.getAttribute('aria-live') } : null; }""")
            check("测验反馈区是 live 区", bool(live) and live["live"] == "polite", str(live))
            opts = page.query_selector_all(".quiz-opt")
            if opts:
                opts[0].click()
                page.wait_for_timeout(300)
                fb_text = page.inner_text("#qFb").strip()
                check("答题后反馈区有内容可播报", len(fb_text) > 0, fb_text[:40].replace("\n", " "))
            else:
                check("答题后反馈区有内容可播报", False, "未出现选项")

            # ── ③ 闪卡翻面后卡面可访问名更新 ───────────────────────────────
            # 第五十九轮起（SC 2.5.3，界面窗报出）：正面可访问名必须带上当前词——
            # 焦点保全（工装·一百二十三）让焦点落到卡面上，读屏用户听到的是这个名字；
            # 固定字面量「翻转卡片查看释义」既不含可见文字（2.5.3 不符），
            # 也让读屏用户听不到自己抽到了哪个词。
            print("== 闪卡翻面 ==")
            page.goto(base + "#cards", wait_until="load")
            page.wait_for_timeout(300)
            page.click('.chip[data-s="all"]')
            page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            page.wait_for_timeout(500)
            before = page.get_attribute("#flipCard", "aria-label") or ""
            card_word = page.evaluate(
                "() => (document.querySelector('#flipCard .fc-word')||{}).textContent||''")
            card_word = (card_word or "").strip()
            page.focus("#flipCard")
            page.keyboard.press(" ")
            page.wait_for_timeout(300)
            after = page.get_attribute("#flipCard", "aria-label")
            check("翻面前卡面可访问名包含当前词的可见文字（SC 2.5.3）",
                  bool(card_word) and card_word in before and "翻转卡片查看释义" in before,
                  f"词「{card_word}」名「{before[:40]}」")
            check("翻面后卡面可访问名更新为该面内容",
                  bool(after) and after != before and len(after) > 4, str(after)[:60])

            # ── ④ 词条弹窗语义 ─────────────────────────────────────────────
            print("== 词条弹窗 ==")
            page.goto(base + "#browse", wait_until="load")
            page.wait_for_timeout(400)
            page.click(".wt-open")
            page.wait_for_timeout(400)
            modal = page.evaluate("""() => {
              const card = document.querySelector('#wordModal .modal-card');
              const lab = document.querySelector('#wmTitle');
              return { role: card && card.getAttribute('role'),
                       modal: card && card.getAttribute('aria-modal'),
                       labelledby: card && card.getAttribute('aria-labelledby'),
                       label: card && card.getAttribute('aria-label'),
                       target: lab ? lab.textContent.trim() : null };
            }""")
            check("词条弹窗是 role=dialog + aria-modal", modal["role"] == "dialog" and modal["modal"] == "true", str(modal))
            check("词条弹窗有可访问名（labelledby 命中或 aria-label 兜底）",
                  bool(modal["target"]) or bool(modal["label"]), str(modal))
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)

            # ── ⑤ 搜索列表框只有 option ───────────────────────────────────
            print("== 全局搜索 ==")
            page.click("#btnSearch")
            page.wait_for_timeout(300)
            roles = page.evaluate("""() => [...document.querySelectorAll('#searchList > *')].map(e => e.getAttribute('role'))""")
            check("搜索结果列表框里只有 option", bool(roles) and all(r == "option" for r in roles), str(roles[:3]))
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)

            # ── ⑥ 设置页隐藏的文件选择器有名字 ─────────────────────────────
            print("== 设置页 ==")
            page.goto(base + "#settings", wait_until="load")
            page.wait_for_timeout(300)
            imp = page.evaluate("""() => { const el = document.querySelector('#impFile');
                return el ? (el.getAttribute('aria-label') || '') : null; }""")
            check("导入用的文件选择器有可访问名", bool(imp), str(imp))

            # ── ⑦ 触控目标尺寸（WCAG 2.2 · SC 2.5.8）──────────────────────
            # 移动端实测：独立成行的文字型链接/按钮过去只有 20px 高（「详情 →」「去测验 →」），
            # 滑杆指针带 16px——触屏上难点中。行内于句子里的控件适用「行内」豁免，不计。
            print("== 触控目标尺寸（390×844 触屏）==")
            mctx = browser.new_context(viewport={"width": 390, "height": 844},
                                       is_mobile=True, has_touch=True)
            mpage = mctx.new_page()
            for v in ("home", "browse", "settings"):
                mpage.goto(base + "#" + v, wait_until="load")
                mpage.wait_for_timeout(400)
                small = mpage.evaluate(TARGET_JS)
                check(f"{v} 视图非行内交互目标不小于 24×24", not small, "; ".join(small[:4]))
            mctx.close()

            # ── ⑧ 回流与文字间距（WCAG 1.4.10 / 1.4.12）─────────────────
            # 320 CSS px 宽（SC 1.4.10 规定的下限）下不得出现横向滚动；
            # 移动端模拟会按内容把布局视口撑宽，正好暴露最小内容宽度撑破的缺陷。
            print("== 320px 回流（WCAG 1.4.10）==")
            rctx = browser.new_context(viewport={"width": 320, "height": 720},
                                       is_mobile=True, has_touch=True)
            rpage = rctx.new_page()
            for v in VIEWS:
                rpage.goto(base + "#" + v, wait_until="load")
                rpage.wait_for_timeout(400)
                res = rpage.evaluate(REFLOW_JS)
                check(f"{v} 视图在 320px 宽下无横向滚动",
                      res["docScroll"] <= 1 and not res["over"],
                      f"docScroll={res['docScroll']} 越界={res['over'][:2]}")
            rctx.close()

            # 文字间距覆盖（SC 1.4.12）：注入用户可覆盖的间距值后不得裁切内容。
            # 第五十轮把口径从「三个视图 × 一个视口」扩到「全八视图 + 三个浮层 × 两档视口」：
            #   · 三个浮层是 <main> 的兄弟节点，原口径根本照不到；
            #   · 窄屏一档（320px）最容易把浮层里的长词条/搜索结果撑出裁切框。
            print("== 文字间距（WCAG 1.4.12）==")
            for slabel, vw, vh, mob in (("桌面 1280×900", 1280, 900, False),
                                       ("窄屏 320×720", 320, 720, True)):
                sctx = browser.new_context(viewport={"width": vw, "height": vh},
                                           is_mobile=mob, has_touch=mob)
                spage = sctx.new_page()
                for v in VIEWS:
                    spage.goto(base + "#" + v, wait_until="load")
                    spage.wait_for_timeout(400)
                    clipped = spage.evaluate(SPACING_JS)
                    check(f"{slabel} · {v} 视图在用户加大字间距后不裁切内容",
                          not clipped, "; ".join(clipped[:3]))
                # 三个浮层：搜索（有结果）、词条详情、键盘快捷键
                spage.goto(base + "#browse", wait_until="load")
                spage.wait_for_timeout(400)
                spage.click("#btnSearch")
                spage.wait_for_timeout(300)
                spage.fill("#searchInput", "ab")
                spage.wait_for_timeout(500)
                clipped = spage.evaluate(SPACING_JS)
                check(f"{slabel} · 搜索浮层在用户加大字间距后不裁切内容",
                      not clipped, "; ".join(clipped[:3]))
                spage.keyboard.press("Escape")
                spage.wait_for_timeout(200)
                spage.evaluate("window.WL_DEBUG.openWordModal(1)")
                spage.wait_for_timeout(500)
                clipped = spage.evaluate(SPACING_JS)
                check(f"{slabel} · 词条详情浮层在用户加大字间距后不裁切内容",
                      not clipped, "; ".join(clipped[:3]))
                spage.click("#wmClose")
                spage.wait_for_timeout(200)
                spage.evaluate("window.WL_DEBUG.openShortcuts()")
                spage.wait_for_timeout(300)
                clipped = spage.evaluate(SPACING_JS)
                check(f"{slabel} · 快捷键浮层在用户加大字间距后不裁切内容",
                      not clipped, "; ".join(clipped[:3]))
                spage.click("#scClose")
                spage.wait_for_timeout(200)
                sctx.close()

            # ── ⑨ 键盘焦点不被遮挡（SC 2.4.11 / 2.4.7）───────────────────
            # 逐个 Tab 走完全部可聚焦元素，要求焦点元素①完整在视口内
            # ②中心点没被固定层（吸顶顶栏 / 移动端底部标签栏）压住。
            # 测试期间把 scroll-behavior 改成 auto：平滑滚动只是动画，
            # 判据关心的是滚动「停在哪」，改 auto 后判定确定且跑得快。
            print("== 键盘焦点不被遮挡（WCAG 2.4.11）==")
            for label, vw, vh, mob, views in (
                    ("移动 390×844", 390, 844, True, ("home", "settings", "browse", "stats")),
                    ("桌面 1280×900", 1280, 900, False, ("home", "settings"))):
                kctx = browser.new_context(viewport={"width": vw, "height": vh},
                                           is_mobile=mob, has_touch=mob)
                kpage = kctx.new_page()
                for v in views:
                    kpage.goto(base + "#" + v, wait_until="load")
                    kpage.wait_for_timeout(400)
                    kpage.add_style_tag(content="html{scroll-behavior:auto!important}")
                    bad = []
                    measured = 0
                    for _ in range(30):
                        kpage.keyboard.press("Tab")
                        kpage.wait_for_timeout(60)
                        res = kpage.evaluate(FOCUS_JS)
                        if not res:
                            continue
                        measured += 1
                        if not res["inView"] or res["covered"]:
                            bad.append(f"{res['name']}({res['text']}) top={res['top']} bot={res['bot']}"
                                       f" 压住者={res['topEl']}")
                    # 第五十七轮（守卫诚实度）：原来 `if not res: continue` 之后
                    # 直接 `not bad` 判过 —— 一次都没量到时 bad 为空 ⇒ 恒过。
                    # 现在加测量数下限（实测 28~30/30），量不到即判红。
                    check(f"{v} 视图 Tab 走查量到可聚焦元素（判据未空转）",
                          measured >= 20, f"量到 {measured}/30 次 Tab 的焦点元素")
                    check(f"{v} 视图 Tab 走查：焦点完整可见且不被固定层遮挡",
                          not bad and measured >= 20, "; ".join(bad[:3]))
                kctx.close()

            # ── ⑩ 焦点指示器可见（SC 2.4.7 / 1.4.11）────────────────────
            # 逐 Tab 聚焦每个表单控件，量它聚焦时的指示器（outline / 描边 / 阴影环）
            # 与相邻底色的对比度——至少一种要达到 3:1。
            # 明暗两主题各查一遍（焦点环用 --accent，主题不同比值不同）。
            print("== 焦点指示器对比度（WCAG 2.4.7 / 1.4.11）==")
            for scheme in ("light", "dark"):
                fctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                           color_scheme=scheme)
                fpage = fctx.new_page()
                for v in ("browse", "settings"):
                    fpage.goto(base + "#" + v, wait_until="load")
                    fpage.wait_for_timeout(400)
                    fpage.add_style_tag(content="html{scroll-behavior:auto!important}")
                    snap = fpage.evaluate(FOCUS_SNAP_JS)   # 未聚焦时的样式快照
                    want = set(fpage.evaluate(FORM_CTRL_JS))   # 该视图应量到的可见表单控件
                    got = set()
                    worst = []
                    for _ in range(22):
                        fpage.keyboard.press("Tab")
                        fpage.wait_for_timeout(260)     # 等颜色过渡走完再量
                        res = fpage.evaluate(FOCUS_IND_JS, snap)
                        if not res:
                            continue
                        got.add(res["name"])
                        if res["best"] < 3:
                            worst.append(f"{res['name']} 最强指示器 {res['best']}:1 "
                                         f"({','.join(i['kind'] + '=' + str(i['cr']) for i in res['ind'])})")
                    # 第五十七轮（守卫诚实度）：原写法 `if not res: continue` 之后
                    # 直接 `not worst` 判过 —— 一个控件都没量到时恒过。
                    # 现在要求：该视图每个可见表单控件都被量到（集合对照）。
                    check(f"{scheme} 主题 · {v} 视图：量到全部可见表单控件（判据未空转）",
                          bool(want) and want.issubset(got),
                          f"应量 {sorted(want)} / 实量 {sorted(got)}")
                    check(f"{scheme} 主题 · {v} 视图：聚焦的表单控件指示器 ≥3:1",
                          not worst and bool(want) and want.issubset(got),
                          "; ".join(worst[:3]))
                fctx.close()

            # ── ⑪ 颜色不单独承载信息（SC 1.4.1）+ Windows 高对比度 ────────
            # ① 正常模式：答对/答错要有与颜色无关的图形标记（✓ / ✗）
            # ② 强制颜色模式：系统接管全部配色后，选中态 / 答对答错 / 热力图色阶
            #    是否还剩下可区分的第二通道（描边、边框线型、图形标记）。
            print("== 颜色不单独承载信息 / 强制颜色模式（WCAG 1.4.1）==")
            ANSWER_JS = ("() => { const b=[...document.querySelectorAll('.quiz-opt')];"
                         " const w=b.find(x=>x.dataset.ok!=='true')||b[0]; if(w) w.click(); }")
            qctx = browser.new_context(viewport={"width": 1280, "height": 900})
            qpage = qctx.new_page()
            qpage.goto(base + "#quiz", wait_until="load")
            qpage.wait_for_timeout(500)
            qpage.click("#startQuiz")
            qpage.wait_for_timeout(500)
            qpage.evaluate(ANSWER_JS)
            qpage.wait_for_timeout(400)
            mk = qpage.evaluate(FORCE_MARK_JS)
            check("测验答对/答错有非颜色的图形标记（SC 1.4.1）", mk["ok"], mk["info"])
            qctx.close()

            xctx = browser.new_context(viewport={"width": 1280, "height": 900})
            xpage = xctx.new_page()
            xpage.emulate_media(forced_colors="active")
            xpage.goto(base + "#quiz", wait_until="load")
            xpage.wait_for_timeout(500)
            chip = xpage.evaluate(FORCE_CHIP_JS)
            check("强制颜色模式：选中态与未选中态仍可区分", chip["diff"], chip["info"])
            xpage.click("#startQuiz")
            xpage.wait_for_timeout(500)
            xpage.evaluate(ANSWER_JS)
            xpage.wait_for_timeout(400)
            opt = xpage.evaluate(FORCE_OPT_JS)
            check("强制颜色模式：答对/答错/未答三种选项仍可区分", opt["ok"], opt["info"])
            check("强制颜色模式：未选选项不做淡化（避免拉低文字对比度）",
                  opt["dimOpacity"] == "1", "opacity=" + opt["dimOpacity"])
            xpage.goto(base + "#stats", wait_until="load")
            xpage.wait_for_timeout(800)
            heat = xpage.evaluate(FORCE_HEAT_JS)
            check("强制颜色模式：热力图 4 级色阶仍彼此可区分", heat["ok"], heat["info"])
            xctx.close()

            # ── ⑫ 减少动态效果（WCAG 2.2 · SC 2.3.3 / 2.2.2）────────────
            # 系统勾了「减少动态效果」时，动画/过渡/平滑滚动必须被压到近零。
            # 另设 no-preference 对照组：确认页面上确实存在会被压掉的动画，
            # 否则上面那条可能只是「本来就没有动画」的空过。
            print("== 减少动态效果（SC 2.3.3：prefers-reduced-motion）==")
            rmctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                        reduced_motion="reduce")
            rmpage = rmctx.new_page()
            rm_total = 0
            for v in VIEWS:
                rmpage.goto(base + "#" + v, wait_until="load")
                rmpage.wait_for_timeout(400)
                rm = rmpage.evaluate(RM_JS)
                rm_total += rm["measured"]
                check(f"减少动态效果 · {v} 视图：动画与过渡被压到近零",
                      rm["nbad"] == 0 and rm["measured"] > 0,
                      f"量到 {rm['measured']} 个可见元素；" + "; ".join(rm["bad"][:3]))
                check(f"减少动态效果 · {v} 视图：滚动行为为 auto（非平滑滚动）",
                      rm["scroll"] == "auto", rm["scroll"])
            check("减少动态效果：量到足够的元素（判据未空转）", rm_total >= 200,
                  f"量到 {rm_total} 个可见元素")
            rmctx.close()

            nctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                       reduced_motion="no-preference")
            npage = nctx.new_page()
            npage.goto(base + "#home", wait_until="load")
            npage.wait_for_timeout(600)
            nm = npage.evaluate(RM_JS)
            check("对照组（无减少动态效果偏好）：页面上确实存在动画/过渡",
                  nm["animated"] + nm["transitioned"] > 0,
                  f"动画 {nm['animated']} 个 / 过渡 {nm['transitioned']} 个 / 量到 {nm['measured']} 个元素")
            nctx.close()

            # ── ⑬ id 与 ARIA 引用完整性 ─────────────────────────────────
            print("== id 与 ARIA 引用完整性 ==")
            tot_ids = 0
            tot_refs = 0          # 可见元素上的引用（判「悬空」时真正看的那些）
            tot_refs_all = 0      # 含隐藏元素（证明这把尺子确实扫到了引用）

            def check_ids(label):
                nonlocal tot_ids, tot_refs, tot_refs_all
                ids = page.evaluate(IDS_JS)
                tot_ids += ids["nids"]
                tot_refs += ids["refs"] + ids["labels"]
                tot_refs_all += ids["refsAll"] + ids["labelsAll"]
                check(f"{label}：没有重复的 id", not ids["dup"], "; ".join(ids["dup"][:3]))
                # 「可见引用为 0」时这条断言会空过（nothing to check）⇒ 不发断言，
                # 改由下面的「量到足够的引用」下限兜底，避免拿空集当通过。
                if ids["refs"] + ids["labels"] > 0:
                    check(f"{label}：可见元素的 ARIA 引用都指向存在的元素",
                          ids["ndang"] == 0, "; ".join(ids["dangling"][:3]))

            for v in VIEWS:
                page.goto(base + "#" + v, wait_until="load")
                page.wait_for_timeout(400)
                check_ids(f"{v} 视图")
            # 三个浮层：搜索（有结果）、词条详情、键盘快捷键
            page.goto(base + "#browse", wait_until="load")
            page.wait_for_timeout(400)
            page.click("#btnSearch")
            page.wait_for_timeout(300)
            page.fill("#searchInput", "a")
            page.wait_for_timeout(600)
            check_ids("搜索浮层")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.evaluate("window.WL_DEBUG.openWordModal(1)")
            page.wait_for_timeout(600)
            check_ids("词条详情浮层")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.evaluate("window.WL_DEBUG.openShortcuts()")
            page.wait_for_timeout(400)
            check_ids("快捷键浮层")
            page.click("#scClose")
            page.wait_for_timeout(300)
            check("id/ARIA 扫描：量到足够的 id（判据未空转）", tot_ids >= 50,
                  f"id 计数合计 {tot_ids}")
            check("id/ARIA 扫描：扫到足够的 ARIA 引用（判据未空转）", tot_refs_all >= 10,
                  f"引用计数合计 {tot_refs_all}（其中可见的 {tot_refs} 条）")

            # ── ⑭ 控件可访问名 / 标签名（SC 1.3.1 / 4.1.2 / 2.5.3）─────
            # ① 每个可见交互控件都要有可访问名；
            # ② 有文字标签的控件，可访问名必须包含那段可见文字（语音控制要用）。
            print("== 控件可访问名与标签名（SC 1.3.1 / 4.1.2 / 2.5.3）==")
            lbl_measured = 0
            lbl_words = 0

            def check_labels(label):
                nonlocal lbl_measured, lbl_words
                lb = page.evaluate(LABEL_JS)
                lbl_measured += lb["measured"]
                lbl_words += lb["wordLabels"]
                check(f"{label}：每个可见交互控件都有可访问名（SC 1.3.1 / 4.1.2）",
                      not lb["unnamed"] and lb["measured"] > 0,
                      f"量到 {lb['measured']} 个控件；" + "; ".join(lb["unnamed"][:3]))
                # 没有文字标签的上下文（纯图标控件）不发断言，避免空过。
                if lb["wordLabels"] > 0:
                    check(f"{label}：可访问名包含可见文字（SC 2.5.3）",
                          not lb["mismatch"],
                          f"文字标签 {lb['wordLabels']} 个；" + "; ".join(lb["mismatch"][:3]))

            for v in VIEWS:
                page.goto(base + "#" + v, wait_until="load")
                page.wait_for_timeout(400)
                check_labels(f"{v} 视图")
            page.goto(base + "#browse", wait_until="load")
            page.wait_for_timeout(400)
            page.click("#btnSearch")
            page.wait_for_timeout(300)
            page.fill("#searchInput", "a")
            page.wait_for_timeout(600)
            check_labels("搜索浮层")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.evaluate("window.WL_DEBUG.openWordModal(1)")
            page.wait_for_timeout(600)
            check_labels("词条详情浮层")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.evaluate("window.WL_DEBUG.openShortcuts()")
            page.wait_for_timeout(400)
            check_labels("快捷键浮层")
            page.click("#scClose")
            page.wait_for_timeout(300)
            check("可访问名扫描：量到足够的控件与文字标签（判据未空转）",
                  lbl_measured >= 60 and lbl_words >= 5,
                  f"量到 {lbl_measured} 个控件 / 其中 {lbl_words} 个带文字标签")

            # ── ⑮ 焦点保全（动态更新后焦点不得丢到 body）──────────────
            # 测验/闪卡每换一题都是「整块重渲染」（root.innerHTML = html），
            # 被聚焦的元素随之销毁 ⇒ Chromium 把焦点甩回 <body>：
            # 键盘用户从此失去位置（要重新从文档首 Tab），读屏用户也听不到新内容。
            # 期望（工装·一百二十三 在 js/app.js 里交回焦点）：
            #   开始答题 → #qPrompt（题干）；作答 → #qNext；下一题 → #qPrompt；
            #   拼写题 → #spellInput（题意经 aria-describedby 播报）；
            #   闪卡开卡/评分 → #flipCard。
            print("== 焦点保全（测验/闪卡：整块重渲染后）==")
            ACT_JS = ("() => { const a = document.activeElement; "
                      "return a ? (a.id || a.tagName.toLowerCase()) : 'none'; }")

            def focus_id():
                return page.evaluate(ACT_JS)

            def quiz_setup():
                # quiz 会话是模块级内存态，而本套件所有 #quiz 导航都是同文档 hash 导航
                # （不重载页面）⇒ 块 ② 开过的会话一直活着：重进 #quiz 会直接渲染题目，
                # 没有 #startQuiz，点击会白等 30s——看着像导航超时，实为状态残留。
                # 先退出遗留会话，保证回到出题设置页再点开始。
                page.goto(base + "#quiz", wait_until="load")
                page.wait_for_timeout(600)
                if page.query_selector("#qQuit"):
                    page.click("#qQuit")
                    page.wait_for_timeout(700)
                page.wait_for_selector("#startQuiz")

            quiz_setup()
            page.click("#startQuiz")
            page.wait_for_timeout(1000)
            check("测验：开始答题后焦点落在题干（读屏用户听得到这一题）",
                  focus_id() == "qPrompt", focus_id())
            page.evaluate("()=>{const o=document.querySelector('.quiz-opt'); if(o) o.click();}")
            page.wait_for_timeout(800)
            check("测验：作答后焦点落在「下一题」（键盘用户接着按空格即可）",
                  focus_id() == "qNext", focus_id())
            page.keyboard.press(" ")
            page.wait_for_timeout(1000)
            check("测验：下一题后焦点落回新题干",
                  focus_id() == "qPrompt", focus_id())
            check("测验：题干可编程聚焦但不进 Tab 序列（tabindex=-1）",
                  page.evaluate("()=>{const p=document.getElementById('qPrompt');"
                                "return !!p && p.getAttribute('tabindex')==='-1';}"),
                  "")
            # 拼写题：焦点留在输入框，题意经 aria-describedby 播报
            quiz_setup()
            page.click('#qModes .chip[data-m="spell"]')
            page.wait_for_timeout(600)
            page.click("#startQuiz")
            page.wait_for_timeout(1200)
            check("测验（拼写题）：焦点落在输入框", focus_id() == "spellInput", focus_id())
            desc = page.evaluate("""() => {
                const i = document.getElementById('spellInput');
                const id = i ? i.getAttribute('aria-describedby') : null;
                const t = id ? document.getElementById(id) : null;
                return { id: id, text: t ? (t.textContent || '').trim() : null };
            }""")
            check("测验（拼写题）：输入框经 aria-describedby 指向题干（读屏能听到题意）",
                  bool(desc["id"]) and bool(desc["text"]), str(desc))
            # 闪卡：与 quiz_setup 同理，块 ③ 开过的闪卡会话（fc.session）还在——
            # 会话活着时 #cards 直接渲染牌桌，没有 .deck-opt 可点 ⇒ 先退会话回选牌页
            page.goto(base + "#cards", wait_until="load")
            page.wait_for_timeout(600)
            if page.query_selector("#fcQuit"):
                page.click("#fcQuit")
                page.wait_for_timeout(700)
            page.wait_for_selector('.deck-opt[data-s="new"]')
            page.click('.deck-opt[data-s="new"]')
            page.click("#fcStart")     # 两步流：chip 选中 + 确认开卡
            page.wait_for_timeout(1000)
            check("闪卡：开卡后焦点落在卡面", focus_id() == "flipCard", focus_id())
            # 评分前必须先翻面：未翻面时 rate() 走「先看释义再评分」早退
            # （flip()+toast，不重渲染）⇒ 焦点还在评分钮上，那不是「焦点丢了」。
            # 与 focus_test.py 的步骤一致：点「显示答案」翻面，再评分。
            page.click("#fcReveal")
            page.wait_for_timeout(400)
            page.click('.fc-btns button[data-q="2"]')
            page.wait_for_timeout(1000)
            check("闪卡：评分后焦点落回新卡面", focus_id() == "flipCard", focus_id())

            check("整轮无 JS 报错", not errors, "; ".join(errors[:2]))
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
