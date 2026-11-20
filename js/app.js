/* ================= GUAN 学术英语词汇库 · Academic English Lexicon =================
   学术英语词库：2222 词（核心高频 1060 个），2158 词带词性分类、1698 词带感情色彩、2222 词带语体色彩
   全部人工改动记录在 data/curation.json
   纯前端单页应用 · 无构建步骤 · 进度存于 localStorage · 可离线 file:// 打开
   ======================================================================== */
(function () {
'use strict';

/* ---------------------------- 基础工具 ---------------------------- */
const $  = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const rnd = a => a[Math.floor(Math.random() * a.length)];
const clone = o => (typeof structuredClone === 'function' ? structuredClone(o) : JSON.parse(JSON.stringify(o)));
const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
function pickN(arr, n) { return shuffle(arr).slice(0, n); }
const DAY = 864e5;
const dayKey = d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
const todayStr = () => dayKey(new Date());
/* 相对今天偏移 n 天的本地日期（用 setDate 推进自然日，夏令时也不会错位） */
function dayOffset(n) { const d = new Date(); d.setDate(d.getDate() + n); return d; }
/* 把「天」换算成人类可读的间隔文案 */
function fmtDur(days) {
  if (days < 1) {
    const h = Math.max(1, Math.round(days * 24));
    return h + ' 小时后';
  }
  return Math.round(days) + ' 天后';
}

/* ---------------------------- 图标系统 ----------------------------
   界面中的“emoji”只作为图标代号写在模板里，渲染后由 fixIcons 统一替换成
   内联 SVG（currentColor 描边），不依赖系统 emoji 字体，任何环境都能显示。 */
const ICONS = {
  cap: '<path d="M2,9 L12,4.5 L22,9 L12,13.5 Z"/><path d="M6.5,11.2 L6.5,15.5 C6.5,17.6 17.5,17.6 17.5,15.5 L17.5,11.2"/><path d="M22,9 L22,13.5"/>',
  home: '<path d="M3.5,10.5 L12,3.5 L20.5,10.5"/><path d="M5.5,9.5 L5.5,20 L10,20 L10,14.5 L14,14.5 L14,20 L18.5,20 L18.5,9.5"/>',
  book: '<path d="M12,6.5 C10,4.8 6.8,4.5 4,5.5 L4,19 C6.8,18 10,18.3 12,20 C14,18.3 17.2,18 20,19 L20,5.5 C17.2,4.5 14,4.8 12,6.5 Z"/><path d="M12,6.5 L12,20"/>',
  cards: '<rect x="7" y="8" width="13" height="13" rx="2"/><path d="M15,8 L15,5 C15,3.9 14.1,3 13,3 L5,3 C3.9,3 3,3.9 3,5 L3,13 C3,14.1 3.9,15 5,15 L7,15"/>',
  pen: '<path d="M16.5,3.5 C18.5,1.5 22.5,5.5 20.5,7.5 L8,20 L3,21 L4,16 Z"/><path d="M14.5,6 L18,9.5"/>',
  folder: '<path d="M3,8 C3,6.9 3.9,6 5,6 L9,6 L11,8.5 L19,8.5 C20.1,8.5 21,9.4 21,10.5 L21,17 C21,18.1 20.1,19 19,19 L5,19 C3.9,19 3,18.1 3,17 Z"/>',
  star: '<path d="M12,3.5 L14.9,9.6 L21.5,10.2 L16.5,14.6 L18.1,21 L12,17.5 L5.9,21 L7.5,14.6 L2.5,10.2 L9.1,9.6 Z"/>',
  'star-f': '<path fill="currentColor" d="M12,3.5 L14.9,9.6 L21.5,10.2 L16.5,14.6 L18.1,21 L12,17.5 L5.9,21 L7.5,14.6 L2.5,10.2 L9.1,9.6 Z"/>',
  chart: '<path d="M3,20.5 L21,20.5"/><path d="M6.5,20.5 L6.5,13"/><path d="M12,20.5 L12,6"/><path d="M17.5,20.5 L17.5,10.5"/>',
  gear: '<path d="M19.47,9.43 L22.07,10.40 L22.07,13.60 L19.47,14.57 L17.96,17.18 L18.42,19.93 L15.66,21.52 L13.51,19.75 L10.49,19.75 L8.34,21.52 L5.58,19.93 L6.04,17.18 L4.53,14.57 L1.93,13.60 L1.93,10.40 L4.53,9.43 L6.04,6.82 L5.58,4.07 L8.34,2.48 L10.49,4.25 L13.51,4.25 L15.66,2.48 L18.42,4.07 L17.96,6.82 Z"/><circle cx="12" cy="12" r="3.2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21,21 L16.3,16.3"/>',
  moon: '<path d="M20,13.2 A8.8,8.8 0 1 1 10.8,3.2 A7,7 0 0 0 20,13.2 Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12,2 L12,4.2 M12,19.8 L12,22 M2,12 L4.2,12 M19.8,12 L22,12 M4.9,4.9 L6.5,6.5 M17.5,17.5 L19.1,19.1 M4.9,19.1 L6.5,17.5 M17.5,6.5 L19.1,4.9"/>',
  flame: '<path d="M12,21.5 C8.4,21.5 5.5,18.8 5.5,15.2 C5.5,10.6 9.8,8.5 10.2,3 C13.6,5.2 14.5,8 14,10.5 C15.5,9.8 16.8,8.4 17,6.5 C18.8,8.8 18.5,12.5 18.5,15.2 C18.5,18.8 15.6,21.5 12,21.5 Z"/>',
  speaker: '<path d="M11,5 L6,9 L3,9 L3,15 L6,15 L11,19 Z"/><path d="M14.8,9 C16.4,10.6 16.4,13.4 14.8,15"/><path d="M17.5,6 C20.5,9 20.5,15 17.5,18"/>',
  'check-c': '<circle cx="12" cy="12" r="9"/><path d="M8,12.3 L10.8,15.2 L16.2,9.2"/>',
  'x-c': '<circle cx="12" cy="12" r="9"/><path d="M8.7,8.7 L15.3,15.3 M15.3,8.7 L8.7,15.3"/>',
  check: '<path d="M4.5,12.5 L9.5,17.5 L19.5,6.5"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/>',
  link: '<path d="M10,13.6 A4.6,4.6 0 0 0 16.5,14.1 L19.5,11.1 A4.6,4.6 0 0 0 13,4.6 L11.2,6.4"/><path d="M14,10.4 A4.6,4.6 0 0 0 7.5,9.9 L4.5,12.9 A4.6,4.6 0 0 0 11,19.4 L12.8,17.6"/>',
  pin: '<path d="M9,3 L15,3 L14.2,10 L17,12.5 L7,12.5 L9.8,10 Z"/><path d="M12,12.5 L12,21"/>',
  sparkles: '<path d="M11,3 L12.6,8.4 L18,10 L12.6,11.6 L11,17 L9.4,11.6 L4,10 L9.4,8.4 Z"/><path d="M18,14.5 L18.8,16.7 L21,17.5 L18.8,18.3 L18,20.5 L17.2,18.3 L15,17.5 L17.2,16.7 Z"/>',
  trend: '<path d="M3,17 L9,11 L13,15 L21,7"/><path d="M14.5,7 L21,7 L21,13.5"/>',
  seed: '<path d="M12,21 L12,11"/><path d="M12,13 C12,8.5 8.5,6.5 4.5,6.5 C4.5,11 8,13 12,13 Z"/><path d="M12,10.5 C12,7 15.5,5 19.5,5 C19.5,9 16,10.5 12,10.5 Z"/>',
  books: '<path d="M4,19.5 A2.5,2.5 0 0 1 6.5,17 L19,17 L19,3.5 L6.5,3.5 A2.5,2.5 0 0 0 4,6 Z"/><path d="M4,19.5 A2.5,2.5 0 0 0 6.5,22 L19,22 L19,17"/>',
  tag: '<path d="M4,4 L12,4 L20,12 C20.8,12.8 20.8,14.2 20,15 L15,20 C14.2,20.8 12.8,20.8 12,20 L4,12 Z"/><circle cx="8.2" cy="8.2" r="1.4"/>',
  rocket: '<path d="M12,2.5 C14.8,4.8 16,8 15.4,11.9 L8.6,11.9 C8,8 9.2,4.8 12,2.5 Z"/><path d="M8.6,11.9 L5.5,14.5 L6.8,18.2 L9.9,15.9"/><path d="M15.4,11.9 L18.5,14.5 L17.2,18.2 L14.1,15.9"/><circle cx="12" cy="7.5" r="1.4"/>',
  print: '<path d="M7,8.5 L7,3.5 L17,3.5 L17,8.5"/><path d="M7,17.5 L4,17.5 C2.9,17.5 2,16.6 2,15.5 L2,11.5 C2,10.4 2.9,9.5 4,9.5 L20,9.5 C21.1,9.5 22,10.4 22,11.5 L22,15.5 C22,16.6 21.1,17.5 20,17.5 L17,17.5"/><path d="M7,13.5 L17,13.5 L17,21 L7,21 Z"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3,10 L21,10 M8,3 L8,6 M16,3 L16,6"/>',
  alarm: '<circle cx="12" cy="13.5" r="7.5"/><path d="M12,10 L12,13.5 L14.8,15.5"/><path d="M4.5,4 L2.5,6 M19.5,4 L21.5,6"/>',
  dice: '<rect x="4" y="4" width="16" height="16" rx="3.5"/><circle cx="9" cy="9" r="1.3" fill="currentColor" stroke="none"/><circle cx="15" cy="15" r="1.3" fill="currentColor" stroke="none"/><circle cx="15" cy="9" r="1.3" fill="currentColor" stroke="none"/><circle cx="9" cy="15" r="1.3" fill="currentColor" stroke="none"/>',
  frown: '<circle cx="12" cy="12" r="9"/><path d="M8.5,15.8 A4,4 0 0 1 15.5,15.8"/><circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/>',
  meh: '<circle cx="12" cy="12" r="9"/><path d="M8.5,14.8 L15.5,14.8"/><circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/>',
  smile: '<circle cx="12" cy="12" r="9"/><path d="M8.5,13.3 A4,4 0 0 0 15.5,13.3"/><circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/>',
  file: '<path d="M14,3 L7,3 C5.9,3 5,3.9 5,5 L5,19 C5,20.1 5.9,21 7,21 L17,21 C18.1,21 19,20.1 19,19 L19,8.5 L14,3 Z"/><path d="M14,3 L14,8.5 L19,8.5"/><path d="M8.5,13 L15.5,13 M8.5,17 L13,17"/>',
  eye: '<path d="M2.5,12 C5.5,6.8 18.5,6.8 21.5,12 C18.5,17.2 5.5,17.2 2.5,12 Z"/><circle cx="12" cy="12" r="3"/>',
  palette: '<path d="M12,2.5 C17.5,2.5 21.5,6.5 21.5,11 C21.5,14.5 19,16.5 16.5,16.5 L14.5,16.5 C13.4,16.5 12.5,17.4 12.5,18.5 C12.5,19.3 12.9,19.9 13.4,20.4 C13.8,20.9 14,21.3 14,21.6 C14,22.3 13.1,22.5 12,22.5 C6.2,22.5 2.5,17.8 2.5,12.5 C2.5,6.6 6.5,2.5 12,2.5 Z"/><circle cx="8" cy="10" r="1.2" fill="currentColor" stroke="none"/><circle cx="12" cy="7.3" r="1.2" fill="currentColor" stroke="none"/><circle cx="16" cy="10" r="1.2" fill="currentColor" stroke="none"/>',
  grid: '<rect x="3" y="3" width="8.5" height="8.5" rx="1.5"/><rect x="12.5" y="3" width="8.5" height="8.5" rx="1.5"/><rect x="3" y="12.5" width="8.5" height="8.5" rx="1.5"/><rect x="12.5" y="12.5" width="8.5" height="8.5" rx="1.5"/>',
  alert: '<path d="M12,3 L21.5,20 L2.5,20 Z"/><path d="M12,9.5 L12,14"/><circle cx="12" cy="17.2" r="1" fill="currentColor" stroke="none"/>',
  minus: '<path d="M5,12 L19,12"/>',
  music: '<path d="M9,17.5 L9,5 L20,3 L20,15.5"/><circle cx="6.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="15.5" r="2.5"/>',
  shuffle: '<path d="M17,4 L21,8 L17,12"/><path d="M3,8 L7.5,8 C11.5,8 12.5,16 16.5,16 L21,16"/><path d="M17,12 L21,16 L17,20"/><path d="M3,16 L7.5,16 C9.6,16 10.8,14.6 11.8,13"/>',
  hash: '<path d="M4.5,9 L19.5,9 M4.5,15 L19.5,15 M9.5,3.5 L7.5,20.5 M16.5,3.5 L14.5,20.5"/>',
  trophy: '<path d="M7,4 L17,4 L17,9.5 C17,13.6 14.6,16 12,16 C9.4,16 7,13.6 7,9.5 Z"/><path d="M7,6.5 L4.5,6.5 C4.5,10.5 6,12 8,12.5"/><path d="M17,6.5 L19.5,6.5 C19.5,10.5 18,12 16,12.5"/><path d="M12,16 L12,19.5 M8.5,21 L15.5,21"/>',
  repeat: '<path d="M17,2.5 L21,6 L17,9.5"/><path d="M3,11 L3,8.5 C3,7.1 4.1,6 5.5,6 L21,6"/><path d="M7,21.5 L3,18 L7,14.5"/><path d="M21,13 L21,15.5 C21,16.9 19.9,18 18.5,18 L3,18"/>',
  trash: '<path d="M4,6.5 L20,6.5"/><path d="M9,6.5 L9,4.2 C9,3.5 9.6,3 10.2,3 L13.8,3 C14.4,3 15,3.5 15,4.2 L15,6.5"/><path d="M6,6.5 L7,20.2 C7.1,21 7.8,21.5 8.5,21.5 L15.5,21.5 C16.2,21.5 16.9,21 17,20.2 L18,6.5"/><path d="M10,10.5 L10,17.5 M14,10.5 L14,17.5"/>',
  zap: '<path d="M13,2 L4,14 L11,14 L10,22 L20,10 L13,10 Z"/>',
  down: '<path d="M12,3.5 L12,15.5"/><path d="M6.5,10.5 L12,16.5 L17.5,10.5"/><path d="M4.5,20.5 L19.5,20.5"/>',
  up: '<path d="M12,20.5 L12,8.5"/><path d="M6.5,13.5 L12,7.5 L17.5,13.5"/><path d="M4.5,3.5 L19.5,3.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12,11.2 L12,16.5"/><circle cx="12" cy="8" r="1.1" fill="currentColor" stroke="none"/>',
  undo: '<path d="M3,12 A9,9 0 1 0 12,3 A9.75,9.75 0 0 0 5.3,5.7 L3,8"/><path d="M3,3 L3,8 L8,8"/>',
  keyboard: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6,10 L6,10.01 M10,10 L10,10.01 M14,10 L14,10.01 M18,10 L18,10.01 M8,14 L16,14"/>',
  chevL: '<path d="M15,5 L8,12 L15,19"/>',
  chevR: '<path d="M9,5 L16,12 L9,19"/>',
  list: '<path d="M8,6 L21,6 M8,12 L21,12 M8,18 L21,18 M3.6,6 L3.6,6.01 M3.6,12 L3.6,12.01 M3.6,18 L3.6,18.01"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5,15 L5,5 C5,3.9 5.9,3 7,3 L15,3"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12,7 L12,12 L15.5,14"/>',
  layers: '<path d="M12,3 L22,8 L12,13 L2,8 Z"/><path d="M2,12 L12,17 L22,12"/><path d="M2,16 L12,21 L22,16"/>',
  arrowR: '<path d="M4,12 L20,12 M14,6 L20,12 L14,18"/>',
  x: '<path d="M6,6 L18,18 M18,6 L6,18"/>',
  filter: '<path d="M3,5 L21,5 L14,13 L14,20 L10,18 L10,13 Z"/>',
  refresh: '<path d="M21,12 A9,9 0 1 1 18,5.6"/><path d="M21,3 L21,8 L16,8"/>',
  plus: '<path d="M12,5 L12,19 M5,12 L19,12"/>',
  bulb: '<path d="M9,18 L15,18 M10,21 L14,21"/><path d="M12,3 A6,6 0 0 1 17.2,10.2 C16.4,11.2 16,12.2 16,13.4 L8,13.4 C8,12.2 7.6,11.2 6.8,10.2 A6,6 0 0 1 12,3 Z"/>',
  skip: '<path d="M5,4.5 L5,19.5"/><path d="M19.5,5 L12,12 L19.5,19 Z"/>',
  scale: '<path d="M12,4.5 L12,19.5"/><path d="M7.5,19.5 L16.5,19.5"/><path d="M4.5,8 L19.5,8"/><path d="M4.5,8 L2,14 L7,14 Z"/><path d="M19.5,8 L17,14 L22,14 Z"/><circle cx="12" cy="8" r="1.2" fill="currentColor" stroke="none"/>',
};
const EMO_MAP = {
  '️': '',
  '🎓': 'cap', '🏠': 'home', '📖': 'book', '🃏': 'cards', '🎴': 'cards', '✍': 'pen',
  '🗂': 'folder', '⭐': 'star-f', '★': 'star-f', '☆': 'star', '📊': 'chart', '⚙': 'gear',
  '🔍': 'search', '🌙': 'moon', '☀': 'sun', '🔥': 'flame', '🔊': 'speaker',
  '✅': 'check-c', '❌': 'x-c', '🎯': 'target', '🔗': 'link', '📌': 'pin',
  '🎉': 'sparkles', '📈': 'trend', '🌱': 'seed', '📚': 'books', '🏷': 'tag', '🚀': 'rocket',
  '📘': 'book', '📕': 'book', '📗': 'book', '🖨': 'print', '📅': 'cal', '⏰': 'alarm',
  '⚖': 'scale', '📎': 'pin', '🎲': 'dice', '😵': 'frown', '🤔': 'meh', '😎': 'smile', '😊': 'smile', '📄': 'file',
  '👀': 'eye', '🎨': 'palette', '🧩': 'grid', '⚠': 'alert', '➖': 'minus',
  '🎹': 'music', '🔀': 'shuffle', '🔢': 'hash', '🏆': 'trophy', '👍': 'check',
  '💪': 'flame', '🔁': 'repeat', '⬇': 'down', '⬆': 'up', '🗑': 'trash', '💥': 'zap',
  'ℹ': 'info',
  '🔄': 'refresh', '↩': 'undo', '⌨': 'keyboard', '📐': 'grid', '📋': 'list',
  '🕐': 'clock', '🗃': 'folder', '➕': 'plus', '🧭': 'target', '❎': 'x', '👁': 'eye',
};
const EMO_SRC = '(?:' + Object.keys(EMO_MAP).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')';
const EMO_RE = new RegExp(EMO_SRC, 'g');
const EMO_TEST = new RegExp(EMO_SRC);
function svgFor(name) {
  return '<svg class="ic" viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor"' +
         ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || '') + '</svg>';
}
function fixTextNode(n) {
  const raw = n.data;
  if (!raw || !EMO_TEST.test(raw)) return;
  const html = raw.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))
                  .replace(EMO_RE, m => {
                    const name = EMO_MAP[m];
                    if (name === '') return '';                       // 变体选择符直接丢弃
                    return (name && ICONS[name]) ? svgFor(name) : m;  // 未收录的字符原样保留
                  });
  if (html === raw) return;
  const holder = document.createElement('div');
  holder.innerHTML = html;
  const frag = document.createDocumentFragment();
  while (holder.firstChild) frag.appendChild(holder.firstChild);
  n.parentNode.replaceChild(frag, n);
}
function fixIcons(root) {
  if (root.nodeType === 3) { fixTextNode(root); return; }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const hits = [];
  for (let n; (n = walker.nextNode()); ) if (EMO_TEST.test(n.data)) hits.push(n);
  hits.forEach(fixTextNode);
}

const WORDS = (window.WL_WORDS || []).slice().sort((a, b) => a.num - b.num);
const BY_NUM = Object.fromEntries(WORDS.map(w => [w.num, w]));
const EXAMPLES = window.WL_EXAMPLES || {};   // 例句：{词形: [{en, zh}, ...]}
const WORDS_MAX = WORDS.length;
const CORE_MAX = WORDS.filter(w => w.core).length;  // 核心高频词数（源站精选 + 人工增补）
const SUB_LABELED_N = WORDS.filter(w => w.sub).length;  // 带感情色彩标注的词数（形容词/名词/动词）

/* ---------------------------- 存储状态 ---------------------------- */
const KEY = 'wl_state_v1';
// 早期版本用过不带版本号的键；保留一次性迁移，升级后不丢已有学习进度
const LEGACY_KEYS = ['wl_state'];
/* 坏存档的留底键：存档里只要有一处坏值或根本不是合法 JSON，就把**原样**留一份在这里，
   别让接下来的 save() 用清洗后的结果把它盖掉——用户还能手工把它捞回来（设置页可提示）。 */
const CORRUPT_KEY = 'wl_state_v1_corrupt';
/* 存档键的中文名（提示用户"哪一项没救回来"时用） */
const FIELD_CN = { progress: '学习进度', settings: '设置', days: '打卡记录',
                   fav: '收藏', quizHist: '测验记录', visits: '访问计数' };
const DEFAULTS = {
  settings: {
    theme: 'dark', rate: .95, goal: 30,
    frontShowHint: false,   // 卡片正面显示词性/感情色彩/语体色彩
    autoSpeak: false,       // 学习自动朗读（默认关：只有用户自己打开才随新卡播）
    autoWrongFav: false,    // 测验答错自动加入收藏
    showKeyHint: true,      // 显示快捷键提示
    fcLimit: 30,            // 学习「每次上限（张）」
    swipeGrade: true,       // 学习触屏左滑=忘了、右滑=认识（仅触摸指针生效）
  },
  progress: {},          // num -> {lv, due, seen, correct, wrong, last}
  fav: [],               // [num]
  quizHist: [],          // [{t, mode, scope, score, total}]
  days: {},              // "YYYY-MM-DD" -> 交互次数（复习+测验）
  visits: {},            // "YYYY-MM-DD" -> 当日访问次数（打开/刷新页面各 +1），只留最近 30 天
  created: Date.now(),
  /* 朗读口径标记：1 = 本存档已按「默认不自动朗读」归一过。
     0/缺失 = 旧存档（自动朗读当时是默认值 true，没人主动点过「开」）。
     它是**存档里的字段**而不是浏览器级标记，这样导出备份、换机导入时口径跟着走：
     换机后的新环境不会又冒出自动出声。 */
  speakVer: 1,
};
/* 进度条目的全部合法字段：入口按此白名单归一/剔除，别的键一律不进运行时
   （须在 loadState() 之前定义：loadState 里的 sanitizeState 会用到它） */
const PROG_FIELDS = ['lv', 'due', 'seen', 'correct', 'wrong', 'last'];
let state = loadState();
/* 结构守卫：坏 localStorage / 坏备份文件不配带病进入运行时。
   顶层类型不对直接 throw（loadState 回落默认档，导入侧转成「格式不正确」提示）；
   条目级脏数据（progress 值非对象、days 值非数字、quizHist 项缺分数）静默剔除 */
/* 数字归一口径（全档共用）：真数字与「可解析成数字的字符串」都算数，
   其余（null / '' / true / [] / NaN / Infinity）一律不算数。
   Number.isFinite('3') 是 false，若直接拿它当准入闸，手改过的备份里
   写成字符串的等级会被当成脏数据——轻则丢一个计数，重则整条进度记录
   被删（用户导入后进度凭空清零且无提示）。 */
function numOrNull(v) {
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  if (typeof v === 'string' && v.trim() !== '' && Number.isFinite(+v)) return +v;
  return null;
}
/* 坏值的处置口径：**逐键摘除，其余照常恢复**。
   此前 progress/settings/days（类型不对）与 fav/quizHist（不是数组）一律 throw，
   而 loadState 捕到 throw 会整档回落默认 —— 结果是**一个字段写错＝整份学习进度被清空**，
   启动时的 save() 还把这个空存档写回本地存储（静默、永久、用户无从察觉）。
   visits 早就按「可丢弃的使用痕迹」处理（类型坏就删该键，回落默认 {}），
   这里把同一口径推广到其余五键：坏的那个键回落默认值，
   其余（进度 / 收藏 / 日历 / 测验史 / 设置）照常恢复。
   被摘除的键名记进 dropped，由调用方提示用户并把原值留底。 */
function sanitizeState(s, dropped) {
  if (!s || typeof s !== 'object' || Array.isArray(s)) throw new Error('state is not an object');
  dropped = dropped || [];
  const drop = (k) => { dropped.push(k); delete s[k]; };
  // 显式 null 字段整键删除，让 DEFAULTS 兜底：下面的 != null 检查只放行合法值、
  // 却不拦 Object.assign 把 null 盖过默认值——quizHist:null 首页 slice 即崩，
  // days:null 访问 state.days[todayStr()] 抛 TypeError，且导入路径会把 null 原样再存盘。
  for (const k of ['progress', 'settings', 'days', 'fav', 'quizHist', 'visits'])
    if (s[k] == null) delete s[k];
  for (const k of ['progress', 'settings', 'days'])
    if (s[k] != null && (typeof s[k] !== 'object' || Array.isArray(s[k]))) drop(k);
  /* visits（访问次数）是**可丢弃的使用痕迹**，不是学习进度：类型坏了就整键删掉
     （回落默认 {}），不像 days 那样 throw —— 为一个统计数字把整份学习进度赔进去
     不划算（loadState 捕到 throw 会整档回落默认，用户进度当场清零）。 */
  if (s.visits != null && (typeof s.visits !== 'object' || Array.isArray(s.visits))) delete s.visits;
  for (const k of ['fav', 'quizHist'])
    if (s[k] != null && !Array.isArray(s[k])) drop(k);
  if (s.progress) for (const [k, p] of Object.entries(s.progress)) {
    if (!p || typeof p !== 'object' || Array.isArray(p)) { delete s.progress[k]; continue; }
    /* lv 认「数字字符串」：备份里写成 "3" 时整条记录曾被当成脏数据删掉——
       用户导入后该词进度凭空清零（seen/correct/due 一并消失），而下面那些
       计数字段本来就认数字字符串，两处口径打架。 */
    const lv = numOrNull(p.lv);
    if (lv === null) { delete s.progress[k]; continue; }
    /* 记忆等级必须钳在 0–5 的整数：LV_LABEL 只有 6 档，超界时
       esc(LV_LABEL[lv]) 取到 undefined → 徽标渲染成「·L-3」，
       收藏导出里更会原样写出 "undefined·L-3"；而统计页按
       (lv ?? -1) === lv 精确分档时，超界词不落任何一档，
       于是同屏「记忆等级分布」与「词汇进度」两张卡数字互相打架。 */
    p.lv = Math.min(5, Math.max(0, Math.trunc(lv)));
    /* 计数与时间戳也必须归一成真数字：备份里写成字符串时，统计页的
       WORDS.reduce 会做 number + "30" → "030" 的字符串拼接，累计次数与
       正确率一起变 NaN。非数字（非空数字字符串除外）一律归零。 */
    for (const f of ['due', 'seen', 'correct', 'wrong', 'last']) {
      const v = numOrNull(p[f]);
      p[f] = v === null ? 0 : v;
    }
    /* 条目只留这六个字段：多余键一律删掉。JSON.parse 会把条目里的 "__proto__"
       造成**自有属性**，若原样留存，快照/撤销路径上的拷贝就会把目标原型换成
       备份里的对象（全局 Object.prototype 未被污染，但活体条目会继承注入属性）。 */
    for (const key of Object.keys(p)) if (!PROG_FIELDS.includes(key)) delete p[key];
  }
  if (s.days) for (const [k, n] of Object.entries(s.days)) {
    /* 日计数同样认数字字符串：备份里写成 "12" 时整日被删 → 打卡日历少一格、
       连续天数少算一天（同一批备份里 progress 的计数字段却认字符串）。 */
    const v = numOrNull(n);
    if (v === null) delete s.days[k]; else s.days[k] = v;
  }
  /* 访问计数与 days 同口径：数字字符串照收，负数与非数字整条剔除
     （负数没有意义，坏值留着会让「最近 30 天访问次数」凭空多出负数）。 */
  if (s.visits) for (const [k, n] of Object.entries(s.visits)) {
    const v = numOrNull(n);
    if (v === null || v < 0) delete s.visits[k]; else s.visits[k] = Math.floor(v);
  }
  /* 测验历史：分数/题数是必填（缺了就整条丢），时间戳 t 与 skipped 是可选
     （坏值只摘字段不丢记录，由 fmtTime 兜底显示）。
     三者一律走数字归一口径：字符串 "8" / "1700000000000" 是可救的，
     真非数字（null/''/true/NaN）才按上面的必填/可选规则处理。 */
  if (s.quizHist) {
    const kept = [];
    for (const h of s.quizHist) {
      if (!h || typeof h !== 'object' || Array.isArray(h)) continue;
      const score = numOrNull(h.score), total = numOrNull(h.total);
      if (score === null || total === null) continue;
      h.score = score; h.total = total;
      if (h.t != null) { const t = numOrNull(h.t); if (t === null) delete h.t; else h.t = t; }
      if (h.skipped != null) { const sk = numOrNull(h.skipped); if (sk === null) delete h.skipped; else h.skipped = sk; }
      kept.push(h);
    }
    s.quizHist = kept;
  }
  // settings 是渲染/朗读直接消费的数字：损坏或异版本备份里若是字符串会让
  // rate.toFixed 抛（设置页整页崩）、goal 变 NaN（首页环形 SVG 画歪），
  // 且 goal/rate 会被内插进 value="…" 属性。此处统一在入口钳制，两条路径（load/导入）都过。
  if (s.settings && typeof s.settings === 'object') {
    const d = DEFAULTS.settings;
    // 只有真数字与数字字符串参与钳制：null/''/true/[7] 的 +v  coercion 会得出
    // 0/0/1/7 这类「合法数」被钳到边界值（goal:null 静默变 5 而非默认 30），违背
    // 「非法值回退默认」口径——非数字一律走 fb。
    const clamp = (v, lo, hi, fb) => {
      const n = (typeof v === 'number' || (typeof v === 'string' && v.trim() !== '')) ? +v : NaN;
      return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fb;
    };
    s.settings.rate = clamp(s.settings.rate, 0.5, 1.5, d.rate);
    s.settings.goal = Math.round(clamp(s.settings.goal, 5, 200, d.goal));
    s.settings.fcLimit = Math.round(clamp(s.settings.fcLimit, 5, WORDS_MAX, d.fcLimit));
    // 主题只有「浅色 / 深色」两档（默认深色）：旧的「跟随系统」(auto) 与任何
    // 非法值一律回落到默认深色。
    if (['light', 'dark'].indexOf(s.settings.theme) < 0) s.settings.theme = d.theme;
    for (const k of ['frontShowHint', 'autoSpeak', 'autoWrongFav', 'showKeyHint', 'swipeGrade'])
      if (s.settings[k] != null) s.settings[k] = !!s.settings[k];
  }
  return s;
}
/* 状态合并只认白名单键：Object.assign 会把备份 JSON 里的 "__proto__" 当普通键写下去，
   把 state 的原型换成文件里的对象——导入一个手改过的备份就能往 state 上注入任意键
   （原型被换后，state 上任何"本来没有"的键都会从注入对象里取值）。
   这里逐键显式拷贝：未知键与 __proto__ 一律不进 state。 */
function pickState(src) {
  const out = clone(DEFAULTS);
  if (!src || typeof src !== 'object') return out;
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  for (const k of Object.keys(DEFAULTS)) {
    if (!own(src, k)) continue;
    if (k === 'settings') {
      const s = src.settings || {};
      for (const sk of Object.keys(DEFAULTS.settings)) if (own(s, sk)) out.settings[sk] = s[sk];
    } else out[k] = src[k];
  }
  /* 「学习自动朗读」的口径归一：旧版本里 autoSpeak 的默认值就是 true，于是
     绝大多数存量存档都写着 autoSpeak:true —— 那是**旧默认值**，不是谁主动点过
     「开」（默认就开着，没人特意点过一次；真手动关过的人存的是 false）。
     全站新口径是「只有点了才读」，若照搬老存档，这些用户升级后依旧每翻一张卡
     就自己响一声，等于这次收敛对他们没生效。故**尚未标记归一过的存档**
     （缺 speakVer 字段，即本轮之前写出的存档）一律把 autoSpeak 落回 false；
     设置项本身保留，用户想听自动播可随时再打开，speakVer=1 随存档一起存下来，
     之后不再被归一。
     判据必须看**源存档里有没有这个字段**，不能看合并后的 out.speakVer ——
     DEFAULTS.speakVer 本身就是 1，用合并结果判会把所有旧存档误判成「已归一」。
     这是**存档内的字段**而不是浏览器级标记：导出备份、换机导入时口径跟着走，
     新环境不会又冒出自动出声。 */
  if (!own(src, 'speakVer') || src.speakVer !== 1) {
    out.settings.autoSpeak = false;
  }
  out.speakVer = 1;
  return out;
}
/* 坏原值留底：把没救回来的存档原文另存一份，save() 覆盖之前先留个底。
   只留一份（同名键覆盖），别无限堆积。 */
function stashCorrupt(raw) {
  try { localStorage.setItem(CORRUPT_KEY, raw); } catch (e) { /* ignore */ }
}
function loadState() {
  let raw = null;
  try { raw = localStorage.getItem(KEY); } catch (e) { return clone(DEFAULTS); }
  if (!raw) {
    for (const k of LEGACY_KEYS) {
      let old = null;
      try { old = localStorage.getItem(k); } catch (e) { /* ignore */ }
      if (old) {
        raw = old;
        try { localStorage.setItem(KEY, raw); localStorage.removeItem(k); } catch (e) { /* ignore */ }
        break;
      }
    }
  }
  if (!raw) return clone(DEFAULTS);
  let parsed = null;
  try { parsed = JSON.parse(raw); }
  catch (e) { stashCorrupt(raw); return clone(DEFAULTS); }   // 存档根本不是合法 JSON：留底后回落默认
  try {
    const dropped = [];
    const s = sanitizeState(parsed, dropped);
    /* 有键被摘除 ⇒ 存档里有坏值：原样留底（save() 会用清洗后的结果覆盖主键），
       其余进度 / 收藏 / 日历 / 测验史照常恢复，不再整档清零。 */
    if (dropped.length) stashCorrupt(raw);
    const st = pickState(s);
    // 旧存档里可能有已下架词条的进度 / 收藏，加载时就剔掉，避免统计数字对不上
    const valid = new Set(WORDS.map(w => w.num));
    st.progress = Object.fromEntries(Object.entries(st.progress || {}).filter(([k]) => valid.has(+k)));
    st.fav = [...new Set((st.fav || []).map(Number).filter(n => valid.has(n)))];
    return st;
  } catch (e) { stashCorrupt(raw); return clone(DEFAULTS); }
}
let _saveT = null;
function save() { clearTimeout(_saveT); _saveT = setTimeout(saveNow, 120); }
function saveNow() { clearTimeout(_saveT);
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { toast('保存失败：存储空间不足'); }
}
window.addEventListener('beforeunload', saveNow);
document.addEventListener('visibilitychange', () => { if (document.hidden) saveNow(); });

function prog(num) { return state.progress[num] || null; }
function ensureProg(num) {
  let p = state.progress[num];
  if (!p) p = state.progress[num] = { lv: 0, due: 0, seen: 0, correct: 0, wrong: 0, last: 0 };
  return p;
}
const LV_LABEL = ['初学', '学习中', '学习中', '熟悉', '熟悉', '已掌握'];
// 各等级的颜色，标签与统计图共用一套，避免"标签是橙色、柱子却是蓝色"这种对不上的情况
const LV_COLOR = ['var(--bad)', 'var(--warn)', 'var(--warn)', 'var(--blue)', 'var(--blue)', 'var(--good)'];
const isMastered = num => { const p = prog(num); return p && p.lv >= 5; };
const isStarted  = num => !!prog(num);
const isDue      = num => { const p = prog(num); return p && p.lv < 5 && p.due <= Date.now(); };
const isFav = num => state.fav.includes(num);
function bumpActivity() { const t = todayStr(); state.days[t] = (state.days[t] || 0) + 1; }
function todayActivity() { return state.days[todayStr()] || 0; }
function streak() {
  let n = 0, d = new Date();
  if (!state.days[todayStr()]) d.setDate(d.getDate() - 1);   // 今天还没学，从昨天起算
  for (;;) {
    const k = dayKey(d);
    if (state.days[k]) { n++; d.setDate(d.getDate() - 1); } else break;
  }
  return n;
}

/* ---------------------------- 站点访问计数（最近 30 天） ----------------------------
   顶栏那枚徽标显示的不是「连续学习天数」，而是「最近 30 天访问过本站多少次」：
   每次打开页面（含刷新）记一次，按天分桶存在 state.visits 里，窗口（30 天）
   以外的旧桶在启动时剪掉，存档不会无限增长。
   与 state.days 的区别：days 记的是「今天复习/测验了多少次」，
   visits 记的是「今天打开了几次页面」——刷新页面同样算一次访问。 */
const VISIT_WINDOW = 30;
function bumpVisit() {
  if (!state.visits || typeof state.visits !== 'object') state.visits = {};
  const t = todayStr();
  state.visits[t] = (state.visits[t] || 0) + 1;
  const cut = dayKey(dayOffset(-(VISIT_WINDOW - 1)));   // 窗口第一天（今天往前数 29 天）
  for (const k of Object.keys(state.visits)) if (k < cut) delete state.visits[k];
  save();
}
/* 最近 30 天的访问总次数（今天 + 前 29 天，逐桶求和） */
function visitsInWindow() {
  let n = 0;
  for (let i = 0; i < VISIT_WINDOW; i++) n += state.visits[dayKey(dayOffset(-i))] || 0;
  return n;
}

/* ---------------------------- SRS（莱特纳盒子） ---------------------------- */
const INTERVALS = [0, 1, 2, 4, 8, 16, 32];   // 天数，按 lv 0..6；lv=5 视为掌握
function grade(num, q, counts) {             // q: 0 忘了 / 1 模糊 / 2 认识
  const p = ensureProg(num);
  p.seen++; p.last = Date.now();
  if (counts) { if (q === 2) p.correct++; else if (q === 0) p.wrong++; }
  if (q === 2) { p.lv = Math.min(5, p.lv + 1); p.due = Date.now() + INTERVALS[p.lv] * DAY; if (p.lv >= 5) p.due = Date.now() + 120 * DAY; }
  else if (q === 1) {
    // 已掌握（L5）被评「模糊」必须降回 L4：isDue 只认 lv<5，留在 L5 的话
    // 这条 due 永远不会生效——保温复习里评过「模糊」的词将无声消失，不再回队列
    if (p.lv >= 5) p.lv = 4;
    p.due = Date.now() + Math.max(0.35 * DAY, INTERVALS[Math.max(0, p.lv - 1)] * DAY * .55);
  }
  else { p.lv = Math.max(0, p.lv - 1); p.due = Date.now(); }
  bumpActivity(); save(); updateVisitPill();
}
function setStatus(num, s) {   // 手动标记：new/learning/mastered
  if (s === 'new') {
    /* 「不认识」= 退回未学习：进度条目整个删掉。全库的「未学习」判定统一是
       「没有进度条目」（isStarted = !!prog(num)，tierCounts 也以有无条目分流），
       留着条目只把 lv 归零的话，这个词会被算成「学习中」、永远进不了未学习牌组，
       与用户「我不认识它」的意思正相反。删条目 = 该词回到出厂态，下次抽到即新词。 */
    delete state.progress[num];
    save();
    return;
  }
  const p = ensureProg(num);
  if (s === 'mastered') { p.lv = 5; p.due = Date.now() + 120 * DAY; }
  else { p.lv = Math.max(1, Math.min(3, p.lv)); p.due = Date.now(); }
  save();
}
function dueQueue() { return WORDS.filter(w => isDue(w.num)); }
/* 各记忆层级一次遍历计数：首页、学习/测验的范围选择与统计页共用。
   每个词必属「未学 / 学习中 / 已掌握」之一（lv 被 grade/setStatus 钳在 0–5），
   所以 new 恒等于 WORDS_MAX - mastered - learning，与旧写法一致 */
function tierCounts() {
  const now = Date.now();
  /* 复习预测边界：后天零点 / 第 8 天零点（自然日推进，同 dayOffset 口径）。
     只看未掌握词的 due 时间戳——「今天学 30 个，明天会来多少」是用户排计划时最想知道、
     而现有面板唯一没有的数字。（五十四轮删掉了从未被读的 t1=明天零点：
     「今天余下 + 明天整天」的桶本就该以 now 与后天零点为界） */
  const t2 = dayOffset(2); t2.setHours(0, 0, 0, 0);
  const t8 = dayOffset(8); t8.setHours(0, 0, 0, 0);
  let due = 0, nNew = 0, learning = 0, mastered = 0, tomorrow = 0, week = 0;
  for (const w of WORDS) {
    const p = prog(w.num);
    if (!p) nNew++;
    else if (p.lv >= 5) mastered++;
    else {
      learning++;
      if (p.due <= now) due++;
      else if (p.due < t8) {
        week++;
        if (p.due < t2) tomorrow++;   // (now, t2)：今天余下时段 + 明天整天，给「明天见」的直观预期
      }
    }
  }
  return { due, new: nNew, learning, mastered, fav: favWords().length, dueTomorrow: tomorrow, dueWeek: week };
}

/* 收藏中仍存在于当前词库的词条（词表更新后可能残留失效条目） */
function favWords() { return state.fav.map(n => BY_NUM[n]).filter(Boolean); }

/* 词表更新后清理失效的本地数据：删除已下架词条对应的记忆进度与收藏 */
function pruneState() {
  const valid = new Set(WORDS.map(w => w.num));
  let changed = false;
  for (const k of Object.keys(state.progress)) {
    if (!valid.has(+k)) { delete state.progress[k]; changed = true; }
  }
  const fav = state.fav.filter(n => valid.has(n));
  if (fav.length !== state.fav.length) { state.fav = fav; changed = true; }
  if (changed) save();
}

/* ---------------------------- 发音 ---------------------------- */
const TTS = ('speechSynthesis' in window) ? window.speechSynthesis : null;
let ttsVoice = null;
function pickEnglishVoice() {
  if (!TTS) return null;
  const vs = TTS.getVoices();
  /* 只认 lang 明确以 en 开头的音色。中文 Windows 可以只装中文音色：
     这时 ttsVoice 必须是 null，不能让引擎拿中文音色兜底读英文。 */
  ttsVoice = vs.find(v => /^en[-_]US/i.test(v.lang) && /google|samantha|aria|jenny/i.test(v.name))
          || vs.find(v => /^en[-_]US/i.test(v.lang))
          || vs.find(v => /^en(?:[-_]|$)/i.test(v.lang)) || null;
  return ttsVoice;
}
function initTTS() {
  if (!TTS) return;
  pickEnglishVoice();
  TTS.onvoiceschanged = () => {
    pickEnglishVoice();
    /* 音色常异步到达：若出题设置已在屏上，只更新缓存不够，disabled 与缺语音包
       提示也必须重算；答题 / 牌桌进行中不重渲染，避免打断会话。 */
    if ($('#qModes') && !quiz.session) renderView('study');
  };
}
/* 语音列表是异步加载的：出题/试听时现取一次，别拿启动瞬间的空列表下结论。 */
function ttsStatus() {
  if (!TTS) return 'unsupported';
  return pickEnglishVoice() ? 'ready' : 'no-english-voice';
}
function canSpeakEnglish() { return ttsStatus() === 'ready'; }
const TTS_NO_ENGLISH = '未检测到英语语音包，已取消朗读，避免用中文音色读英文。请在系统语音设置中安装英语语音后刷新页面。';
/* 朗读计数（测试用）：每次真正发起朗读 +1。
   全站口径「只有用户点了才读」需要可测的证据 —— 没有计数就只能靠人耳听，
   「打开词条弹窗会不会自己响」这类回归会悄悄溜过去。 */
let speakCount = 0;
function speak(word) {
  if (!TTS) { toast('当前浏览器不支持语音合成'); return; }
  /* 明确指定英语音色，不能只写 u.lang='en-US' 就交给浏览器：
     实测中文 Windows 只有 Huihui/Kangkang/Yaoyao 三个 zh-CN 音色时，
     voice=null + lang=en-US 仍会用系统默认中文音色念英文，声音即「莫名其妙」。
     宁可提示用户装英语语音包，也不能发这种误导性的音。 */
  const voice = pickEnglishVoice();
  if (!voice) { toast(TTS_NO_ENGLISH, 4600, 'info'); return; }
  TTS.cancel();
  const u = new SpeechSynthesisUtterance(word);
  u.lang = 'en-US'; u.voice = voice;
  u.rate = state.settings.rate;
  speakCount++;   // 只计真正交给语音引擎的 utterance；不支持/无英语音色的拒绝路径不计
  TTS.speak(u);
}

/* ---------------------------- 轻提示 ---------------------------- */
function toast(msg, ms, iconName) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = (iconName ? svgFor(iconName) : '') + '<span>' + esc(msg) + '</span>';
  $('#toastWrap').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = '.3s'; setTimeout(() => el.remove(), 320); }, ms || 1900);
}

/* ---------------------------- 主题 ---------------------------- */
function applyTheme() {
  // 主题只有「浅色 / 深色」两档，默认深色；不再跟随系统（prefers-color-scheme）
  const dark = state.settings.theme !== 'light';
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  const btn = $('#btnTheme');
  btn.innerHTML = svgFor(dark ? 'sun' : 'moon');
  btn.title = '切换深浅色（当前：' + (dark ? '深色' : '浅色') + '）';
  // 移动端状态栏/浏览器边缘色跟随主题（深色取石墨底，浅色取纸面底色）
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme) metaTheme.content = dark ? '#0b0b0e' : '#f6f4f3';
}
/* ---------------------------- 通用渲染片段 ---------------------------- */
function lvlChip(num) {
  const p = prog(num);
  if (!p) return '<span class="lvl l-new">未学</span>';
  if (p.lv >= 5) return '<span class="lvl l-5">已掌握</span>';
  return `<span class="lvl l-${p.lv}">${esc(LV_LABEL[p.lv])}·L${p.lv}</span>`;
}
function posTags(w) {
  let h = '';
  if (w.pos) h += `<span class="tag-pos">${esc(w.pos)}</span>`;
  if (w.sub) {
    const cls = w.sub === '积极的' ? 'tag-pos tag-sub-p' : w.sub === '消极的' ? 'tag-pos tag-sub-n'
      : w.sub === '争议性的' ? 'tag-pos tag-sub-c' : 'tag-pos tag-sub-z';
    h += `<span class="${cls}">${esc(w.sub)}</span>`;
  }
  /* 语体色彩只挂三个少数派（学术术语 / 书面语 / 口语）；中性的不挂
     （满屏标签没人看）。三枚各占一色：术语靛蓝、书面青碧、口语橙。 */
  if (w.reg && w.reg !== '中性') {
    const rcls = w.reg === '学术术语' ? 'tag-reg-t' : w.reg === '书面语' ? 'tag-reg-w' : 'tag-reg-s';
    h += `<span class="tag-pos ${rcls}">${esc(w.reg)}</span>`;
  }
  return h;
}
/* ---------------------------- 例句 ---------------------------- */
/* 例句按词形索引（js/examples.js 生成自 data/examples.json）；没有例句的词条自动跳过 */
function exOf(w) { return (w && EXAMPLES[w.word]) || []; }
/* 统一渲染例句块：英文原句 + 中文翻译 */
function exBlock(w, opt) {
  const o = opt || {};
  const list = exOf(w).slice(0, o.max || 3);
  if (!list.length) return '';
  const cls = o.cls || 'wm-ex';
  const renderItem = e => `
    <div class="${cls}-item">
      <div class="${cls}-en">${esc(e.en)}</div>
      ${o.showZh === false ? '' : `<div class="${cls}-zh">${esc(e.zh)}</div>`}
    </div>`;
  const split = Math.max(1, Math.min(list.length, o.collapseAfter || list.length));
  const items = list.slice(0, split).map(renderItem).join('');
  const rest = list.slice(split);
  const more = rest.length ? `<details class="${cls}-more"><summary><span class="${cls}-more-closed">展开其余 ${rest.length} 个例句</span><span class="${cls}-more-open">收起其余例句</span></summary><div class="${cls}-more-body">${rest.map(renderItem).join('')}</div></details>` : '';
  return `<div class="${cls}"><div class="${cls}-label">例句</div>${items}${more}</div>`;
}
const LINK_LABELS = u => {
  if (/ldoceonline/.test(u)) return '📘 Longman';
  if (/merriam/.test(u)) return '📕 Merriam-Webster';
  if (/cambridge/.test(u)) return '📗 Cambridge';
  const d = (u.match(/https?:\/\/([^\/]+)/) || [])[1] || u;
  return '🔗 ' + d;
};

/* ---------------------------- 生词 ---------------------------- */
function toggleFav(num) {
  const i = state.fav.indexOf(num);
  if (i >= 0) { state.fav.splice(i, 1); toast('已从收藏移除'); }
  else { state.fav.push(num); toast('已加入收藏 ⭐'); }
  save();
  return i < 0;
}
/* 词条弹窗与测验反馈里「收藏大按钮」的统一内 HTML
   （学习底栏 fcFav 是「收藏/已收藏」短文案,不走这里） */
const favBtnInner = on => svgFor(on ? 'star-f' : 'star') + ' ' + (on ? '移出收藏' : '加入收藏');

/* ---------------------------- 单词详情弹窗 ---------------------------- */
/* 浮层焦点管理：打开时把焦点移进浮层，Tab 在浮层内循环，关闭后焦点还给触发元素 */
const FOCUSABLE_SEL = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function focusablesIn(root) {
  return [...root.querySelectorAll(FOCUSABLE_SEL)]
    .filter(el => el.getClientRects().length && el.offsetParent !== null);
}
/* 把 Tab 焦点锁在 root 内，避免键盘用户跑到浮层背后的页面上 */
function trapTab(root, e) {
  if (e.key !== 'Tab') return;
  const items = focusablesIn(root);
  if (!items.length) { e.preventDefault(); return; }
  const first = items[0], last = items[items.length - 1];
  const cur = document.activeElement;
  if (e.shiftKey) {
    if (cur === first || !root.contains(cur)) { e.preventDefault(); last.focus(); }
  } else if (cur === last || !root.contains(cur)) { e.preventDefault(); first.focus(); }
}
/* 记录打开浮层前的焦点，关闭时归还（浮层内再打开另一个浮层时不覆盖） */
const focusMemory = new WeakMap();
function rememberFocus(overlay) {
  const cur = document.activeElement;
  if (!cur || !document.contains(cur)) return;
  // 弹窗内换词条时（←→ / wmNext）旧按钮随 innerHTML 重建而销毁，
  // activeElement 短暂落到 body——这不是「触发元素」，记了会把关闭后的
  // 焦点归还毁掉（restoreFocus 的 offsetParent 守卫又会拒绝 focus body = 焦点丢失）
  if (cur === document.body || cur === document.documentElement) return;
  if (overlay && overlay.contains(cur)) return;   // 浮层内部切换内容时不覆盖记忆
  focusMemory.set(overlay, cur);
}
function restoreFocus(el, fallback) {
  const prev = focusMemory.get(el);
  if (prev && document.contains(prev) && prev.offsetParent !== null) { prev.focus(); return; }
  /* 触发元素已不存在（或浮层是用快捷键打开的，没有触发元素可记）时，
     焦点会掉回 body——键盘用户得从页首重新 Tab 一遍。给一个确定的落点兜底。 */
  const fb = fallback ? $(fallback) : null;
  if (fb && fb.offsetParent !== null) fb.focus();
}

function modalContextList() {
  return (current === 'browse' || current === 'fav') ? browseRows() : WORDS;
}
/* 弹窗当前词条的编号：← / → 导航按 num 定位（按词形文本找会在同名词条上错位） */
let wmNum = null;
function openWordModal(num) {
  const w = BY_NUM[num]; if (!w) return;
  wmNum = num;
  const body = $('#wordModalBody');
  const list = modalContextList();
  const idx = list.findIndex(x => x.num === num);
  // 当前记忆状态：用于高亮「手动标记」里的对应按钮
  const p = prog(num);
  /* 状态高亮必须与全库口径一致：isStarted = 有进度条目即算「学习中」，
     tierCounts 也据此分流。此前这里写 `!(p.lv > 0)` —— lv 为 0 的条目被算成
     「不认识」，于是弹窗预选的是会**删掉整条进度**的按钮，而统计页同时
     把这个词算作「学习中」，同屏两处数字互相打架。 */
  const cur = !p ? 'new' : isMastered(num) ? 'mastered' : 'learning';
  const prevW = idx > 0 ? list[idx - 1] : null;
  const nextW = idx >= 0 && idx < list.length - 1 ? list[idx + 1] : null;
  body.innerHTML = `
    <div class="wm-num">词条 #${w.num}${idx >= 0 ? ` · 第 ${idx + 1} / ${list.length} 条` : ''}</div>
    <div class="wm-word" id="wmTitle" role="heading" aria-level="2">${esc(w.word)}</div>
    <div class="wm-tags">${posTags(w)} ${lvlChip(num)}</div>
    ${w.senses.map((s, i) => `<div class="wm-sense"><b>${i + 1}</b>${esc(s)}</div>`).join('')}
    ${exBlock(w, { max: 3 })}
    ${(w.notes || []).map(n => `<div class="wm-note">${svgFor('pin')} ${esc(n)}</div>`).join('')}
    <div class="wm-links">${(w.links || []).map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(LINK_LABELS(u))}</a>`).join('')}</div>
    <div class="wm-actions">
      <button class="btn primary sm" id="wmSpeak">${svgFor('speaker')} 朗读</button>
      <button class="btn sm" id="wmCopy">${svgFor('copy')} 复制</button>
      <button class="btn sm wm-fav${isFav(num) ? ' on' : ''}" id="wmFav">${favBtnInner(isFav(num))}</button>
    </div>
    <div class="wm-mark">
      <span class="wm-mark-label">${svgFor('target')} 手动标记记忆状态</span>
      <div class="wm-mark-btns">
        <button class="btn sm${cur === 'new' ? ' on' : ''}" id="wmMark0">${svgFor('frown')} 不认识</button>
        <button class="btn sm${cur === 'learning' ? ' on' : ''}" id="wmMark1">${svgFor('seed')} 学习中</button>
        <button class="btn sm${cur === 'mastered' ? ' on' : ''}" id="wmMark2">${svgFor('trophy')} 已掌握</button>
      </div>
    </div>
    <div class="wm-nav">
      <button class="btn ghost sm" id="wmPrev" ${prevW ? '' : 'disabled'}>${svgFor('chevL')} ${prevW ? esc(prevW.word) : '已是第一条'}</button>
      <button class="btn ghost sm" id="wmNext" ${nextW ? '' : 'disabled'}>${nextW ? esc(nextW.word) : '已是最后一条'} ${svgFor('chevR')}</button>
    </div>`;
  // 容器是复用的：上一词条的滚动深度会原样留给新词条（←→ 连翻时长词
  // 中途接续、重开也停在半截），每次打开/换词都滚回顶部
  body.scrollTop = 0;
  $('#wordModal').hidden = false;
  rememberFocus($('#wordModal'));
  $('#wmClose').focus();
  $('#wmSpeak').onclick = () => speak(w.word);
  $('#wmCopy').onclick = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(w.word);
      else {
        const ta = document.createElement('textarea'); ta.value = w.word;
        document.body.appendChild(ta); ta.select();
        const copied = document.execCommand('copy');
        ta.remove();
        /* execCommand 返回 false 就是**没复制成**（file:// 等非安全上下文、
           权限被拒、浏览器停用该 API）。旧写法丢掉返回值，照样弹「已复制」，
           而这条 toast 是唯一的成功凭据——事实与提示不符。 */
        if (!copied) throw new Error('execCommand copy refused');
      }
      toast('已复制「' + w.word + '」', 1500, 'check');
    } catch (e) { toast('复制失败，请手动选择', 1800, 'alert'); }
  };
  $('#wmFav').onclick = e => {
    const on = toggleFav(num);
    const b = e.currentTarget;
    b.classList.toggle('on', on);
    b.innerHTML = favBtnInner(on);
    rerenderIfBrowse();
  };
  $('#wmMark0').onclick = () => { setStatus(num, 'new'); toast('已标记为不认识', 1500, 'frown'); closeWordModal(); rerenderIfBrowse(); };
  $('#wmMark1').onclick = () => { setStatus(num, 'learning'); toast('已标记为学习中', 1500, 'seed'); closeWordModal(); rerenderIfBrowse(); };
  $('#wmMark2').onclick = () => { setStatus(num, 'mastered'); toast('已标记为已掌握', 1500, 'trophy'); closeWordModal(); rerenderIfBrowse(); };
  $('#wmPrev').onclick = () => { if (prevW) openWordModal(prevW.num); };
  $('#wmNext').onclick = () => { if (nextW) openWordModal(nextW.num); };
  /* 这里曾有一句无条件 speak(w.word)：打开词条弹窗就自动出声。
     全站口径是「只有用户点了才读」——弹窗里已有「朗读」按钮（#wmSpeak），
     自动读一遍等于在用户还没决定要不要听时先响一声。 */
}
function closeWordModal() {
  const m = $('#wordModal');
  if (m.hidden) return;
  m.hidden = true;
  restoreFocus(m, '#main');
}
$('#wmClose').onclick = closeWordModal;
$('#wordModal').addEventListener('click', e => { if (e.target === $('#wordModal')) closeWordModal(); });
$('#wordModal').addEventListener('keydown', e => trapTab($('#wordModal'), e));

/* ---------------------------- 词库筛选（browse / fav 共用） ---------------------------- */
// 窄屏默认用卡片视图：表格挤在手机屏幕上，释义会被折成很窄的几行
const narrowScreen = () => window.matchMedia('(max-width:720px)').matches;
/* 四个互相独立的层：pos = 词性（含「其他」＝介词与介词短语那一档）、
   core = 是否核心（yes / no，跨五种词性的一层）、sub = 感情色彩（积极 / 消极 /
   争议性 / 中性，挂在形容词/名词/动词上，是原「分类」页并入词库后的筛选项）、
   reg = 语体色彩（书面语 / 口语 / 中性，全库都有）。
   各层正交，可自由叠加：「核心词 + 名词 + 消极的 + 书面语」成立。 */
const browse = { q: '', favQ: '', letter: '', pos: '', core: '', sub: '', reg: '', status: '', sort: 'num', dir: 1, page: 1, favPage: 1, per: 50, onlyFav: false, view: narrowScreen() ? 'cards' : 'table', favView: narrowScreen() ? 'cards' : 'table', filtersOpen: null, groupOnce: false };
/* 搜索词按视图分家：词库页用 browse.q，收藏页用 browse.favQ。
   此前两者共用一个 browse.q —— 在收藏里搜一个词，回到词库页发现**整库**被筛了
   （那个搜索框写着「在收藏内搜索…」，实际却作用于全库）；
   反过来，进一趟收藏还会把词库页的搜索词清掉（两边互相踩）。 */
const browseQuery = () => (browse.onlyFav ? browse.favQ : browse.q);
/* 页码也按视图分家：词库页 browse.page / 收藏页 browse.favPage。
   此前两边共用一个 page —— 在词库翻到第 3 页、切去收藏（收藏页进入时要把
   页码与筛选一起清成初始态），回头再看词库也从第 3 页掉回第 1 页：
   用户的浏览位置被另一个视图的初始化动作吃掉。搜索词（q/favQ）与视图
   （view/favView）早已分开，页码是漏掉的那一个。 */
const pageNow = () => (browse.onlyFav ? browse.favPage : browse.page);
const pageSet = p => { if (browse.onlyFav) browse.favPage = p; else browse.page = p; };
/* 词库状态筛选的统一文案表：空状态 chips、筛选摘要、状态下拉三处共用
   （此前 fav 在 chips 里叫「已收藏」、摘要里叫「收藏」，现统一为后者） */
const STATUS_LABEL = { new: '未学习', due: '待复习', learning: '学习中', mastered: '已掌握', fav: '收藏' };
const STATUS_ORDER = ['new', 'due', 'learning', 'mastered', 'fav'];   // 下拉里的展示顺序
/* 「其他」= 库里那一批**没有实义词性标签**的词：单词介词与介词性固定短语
   （due to / via / regarding …）。它们并非「没有词性」—— 词性就是介词；
   只是本库词性索引只设形容词/副词/动词/名词/连词五类，不设「介词」类，
   且多词介词短语（in terms of）本就没有单词级词性，于是这一档统一走 pos=null。
   原先筛选面板只有五种词性可选，这批词在筛选层面完全够不着 —— 补一档兜住。
   展示名用「介词」而非「其他」：旧文案说「不设词性的介词」，
   读起来像这批词没有词性，其实是「不设实义词性标签」。
   「核心」不是词性（它跨五种词性），故另起一行「是否核心」，两层正交可叠加。 */
const POS_OTHER = '其他';                        // 内部键（browse.pos / data-pos），勿改
const POS_OTHER_LABEL = '介词';                  // 展示名
const OTHER_WORDS = () => WORDS.filter(w => !w.pos);
const POS_LABEL = { [POS_OTHER]: POS_OTHER_LABEL };
/* 是否核心：与词性正交的一层。核心词跨五种词性，也能与「其他」那批叠加。 */
const CORE_LABEL = { yes: '核心词', no: '非核心词' };
/* 感情色彩这一维的兜底档「其他」= **没有标注感情色彩**的词。
   第七十轮起这一维不再只挂形容词：形容词/名词/动词三类实词都带评价色彩，
   副词/连词/介词不带（那 524 个词在「其他」这一档里）。
   四档（积极/消极/争议/中性）＋「其他」互斥且穷尽，各档之和 = 不限。
   内部键与展示名分开：内部键用 SUB_OTHER（勿改），展示名仍是「其他」，
   免得与词性那一维的内部键（POS_OTHER = '其他'）混作一谈。 */
const SUB_OTHER = '未标注';                        // 内部键（browse.sub / data-sub），勿改
const SUB_LABEL = { [SUB_OTHER]: '其他' };
/* 感情色彩四档（展示名与内部键同形；勿改字面——数据里存的就是这四个字） */
const SUB_ORDER = ['积极的', '消极的', '争议性的', '中性的'];
/* 感情色彩挂在哪三类实词上。副词/连词/介词不带评价义（=「其他」档）。
   第七十一轮起这一维对副词/连词/介词**照样摆出来**（不再整行藏起来）：
   四个带标签的档在它们下面恒为 0 —— 显示 0、灰显不可点，
   「其他」那一档则等于该词性的全体（副词 375 / 连词 85 / 介词 64）。 */
const SUB_POS = ['形容词', '名词', '动词'];
/* 语体色彩（第七十轮新增·第二稿拆四档）：学术术语 / 书面语 / 口语 / 中性，
   全库每词都有值。拆四档的理由：原先只有三档时，「书面语」把**学科专门术语**
   （covariate、endogeneity、ethnography…）与**正式文体标志**（moreover、
   in the event that…）混装在一档里 —— 两者对写作者是两种完全不同的知识
   （一个是"这词是术语"，一个是"这词是正式书面体"），混装就等于两档都不准。
   四档的归属规则：先判是不是学术术语（是则归「学术术语」），
   否则判带不带正式语域印记（书面语），否则判带不带口语色彩（口语），
   都不带就是「中性」。 */
const REG_ORDER = ['学术术语', '书面语', '口语', '中性'];
/* 某一维的候选取值是否命中某个词（内部键 → 谓词） */
function subHit(w, v) { return v === SUB_OTHER ? !w.sub : w.sub === v; }
/* 某个词性下够不够得着某一档感情色彩 —— 换词性后用它判断要不要撤掉这档条件：
   副词/连词/介词没有「积极的」这类评价色彩（恒 0），三类实词没有「其他」（恒 0）。
   够不着就撤，撤了才不会点下去只剩一张空表；够得着（如副词 + 「其他」）就留着。 */
function subReachable(pos, sub) {
  if (!sub) return true;
  return WORDS.some(w => subHit(w, sub)
    && (pos ? (pos === POS_OTHER ? !w.pos : w.pos === pos) : true));
}
/* 关键词命中判定：词形 / 释义 / 编号之外再加例句正文（英/中）。
   词库、收藏与全局搜索三处共用一份口径（此前只匹配词形与释义，
   数千条例句完全没参与搜索——写作时想不起词、只记得例句里的搭配时最难查）。
   返回 'main'（词形/释义/编号命中）或 'ex'（仅例句命中）或 null。q 须已 trim+lowercase。 */
function wordMatchQ(w, q) {
  if (!q) return 'main';
  if (w.word.toLowerCase().includes(q) ||
      w.senses.some(s => s.toLowerCase().includes(q)) ||
      String(w.num) === q) return 'main';
  if (exOf(w).some(e => e.en.toLowerCase().includes(q) || e.zh.includes(q))) return 'ex';
  return null;
}
function browseRows() {
  let rows = WORDS;
  if (browse.onlyFav) rows = rows.filter(w => isFav(w.num));
  if (browse.letter) rows = rows.filter(w => w.word[0].toUpperCase() === browse.letter);
  /* 词性：五种之外还有「其他」—— 那批介词与介词短语（无实义词性标签） */
  if (browse.pos === POS_OTHER) rows = rows.filter(w => !w.pos);
  else if (browse.pos) rows = rows.filter(w => w.pos === browse.pos);
  /* 是否核心：与词性正交，可自由叠加（核心词跨五种词性，也有 31 个落在「其他」里） */
  if (browse.core === 'yes') rows = rows.filter(w => w.core);
  else if (browse.core === 'no') rows = rows.filter(w => !w.core);
  /* 感情色彩：五档（积极/消极/争议性/中性/其他＝未标注）互斥且穷尽，
     各档之和 = 该维的「不限」条数（见 browseFacetCount 的 sub 维）。 */
  if (browse.sub) rows = rows.filter(w => subHit(w, browse.sub));
  /* 语体色彩：书面语/口语/中性三档，全库都有值，三档之和 = 不限。 */
  if (browse.reg) rows = rows.filter(w => w.reg === browse.reg);
  if (browse.status === 'new') rows = rows.filter(w => !isStarted(w.num));
  if (browse.status === 'due') rows = rows.filter(w => isDue(w.num));
  if (browse.status === 'learning') rows = rows.filter(w => isStarted(w.num) && !isMastered(w.num));
  if (browse.status === 'mastered') rows = rows.filter(w => isMastered(w.num));
  if (browse.status === 'fav') rows = rows.filter(w => isFav(w.num));
  const q = browseQuery().trim().toLowerCase();
  if (q) rows = rows.filter(w => wordMatchQ(w, q));
  const dir = browse.dir;
  const sorters = {
    num: (a, b) => (a.num - b.num) * dir,
    word: (a, b) => a.word.localeCompare(b.word) * dir,
    lv: (a, b) => ((prog(a.num)?.lv ?? -1) - (prog(b.num)?.lv ?? -1)) * dir,
  };
  return rows.slice().sort(sorters[browse.sort] || sorters.num);
}

/* ---- 筛选分面计数 ----
   每个筛选选项旁显示「若把这一维度换成该值，结果还剩多少词」。
   口径：其它维度按当前生效状态算，只有被问的那一维换成候选值，
   于是数字与用户点下去之后列表里的条数一致（而不是全库的静态总数）。
   「不限 / 全部」= 去掉这一维限制后的条数。 */
function browseFacetBase() {
  let rows = WORDS;
  if (browse.onlyFav) rows = rows.filter(w => isFav(w.num));
  const q = browseQuery().trim().toLowerCase();
  if (q) rows = rows.filter(w => wordMatchQ(w, q));
  return rows;
}
function browseStatusFilter(rows, k) {
  if (k === 'new') return rows.filter(w => !isStarted(w.num));
  if (k === 'due') return rows.filter(w => isDue(w.num));
  if (k === 'learning') return rows.filter(w => isStarted(w.num) && !isMastered(w.num));
  if (k === 'mastered') return rows.filter(w => isMastered(w.num));
  if (k === 'fav') return rows.filter(w => isFav(w.num));
  return rows;
}
function browseFacetCount(dim, val, base) {
  const b = base || browseFacetBase();
  let rows = b;
  if (dim !== 'letter' && browse.letter) rows = rows.filter(w => w.word[0].toUpperCase() === browse.letter);
  if (dim !== 'pos') {
    if (browse.pos === POS_OTHER) rows = rows.filter(w => !w.pos);
    else if (browse.pos) rows = rows.filter(w => w.pos === browse.pos);
  }
  if (dim !== 'core') {
    if (browse.core === 'yes') rows = rows.filter(w => w.core);
    else if (browse.core === 'no') rows = rows.filter(w => !w.core);
  }
  /* 感情色彩这一维：算别的维度的数时照常带上当前这一档 ——
     面板上的数字必须是「点下去之后列表里会有的条数」。
     此前对 pos 维开了个例外（当前这一档在该词性下够不着词就不计）：
     结果选了「其他」（未标注）后，词性那一排的数字**一个都不动**
     —— 形容词/名词/动词三类实词恒不带标签（撤掉这一档后反而又是全量），
     副词/连词/介词又全都不带标签（数字与不限时相同），
     用户看着数字纹丝不动，以为筛选没生效。
     现在照常相交：词性=形容词 时「其他」为 0（并把该 chip 灰显），
     副词/连词/介词各显自己那一份。 */
  const subApplies = dim !== 'sub';
  if (subApplies && browse.sub) rows = rows.filter(w => subHit(w, browse.sub));
  /* 语体色彩：全库都有值，这一维永不自动撤销，计数时照常带上。 */
  if (dim !== 'reg' && browse.reg) rows = rows.filter(w => w.reg === browse.reg);
  if (dim !== 'status' && browse.status) rows = browseStatusFilter(rows, browse.status);
  // 候选值替换该维度自身的限制（空值 = 不限）
  if (dim === 'letter' && val) rows = rows.filter(w => w.word[0].toUpperCase() === val);
  if (dim === 'pos' && val) rows = val === POS_OTHER ? rows.filter(w => !w.pos) : rows.filter(w => w.pos === val);
  if (dim === 'core') {
    if (val === 'yes') rows = rows.filter(w => w.core);
    else if (val === 'no') rows = rows.filter(w => !w.core);
  }
  if (dim === 'sub' && val) rows = rows.filter(w => subHit(w, val));
  if (dim === 'reg' && val) rows = rows.filter(w => w.reg === val);
  if (dim === 'status' && val) rows = browseStatusFilter(rows, val);
  return rows.length;
}

/* 就地刷新筛选面板上的计数（搜索词改动只重画表格、不重画面板，
   计数若不跟着更新就会与实际结果对不上）。 */
function refreshFacetCounts() {
  const base = browseFacetBase();
  $$('[data-fcnt]').forEach(el => {
    const [dim, val] = el.dataset.fcnt.split('|');
    const n = browseFacetCount(dim, val, base);
    const fl = el.dataset.flabel;
    el.textContent = fl ? `${fl}（${n}）` : String(n);
    /* 首字母按钮的「无词则灰显」是按数量决定的，数字变了灰显也得跟着变 */
    if (dim === 'letter') {
      const btn = el.closest('.letter-btn');
      if (btn && btn.dataset.l) btn.classList.toggle('dim', !n);
    }
    /* 感情色彩各档：数到 0 词的那几档整枚撤掉（disabled），免得用户点下去
       只得到一张空表 —— 副词/连词/介词下的四个带标签档（恒 0）与
       三类实词下的「其他」都属此列。正选着的那一枚例外：它得留着，
       用户才能点回「不限」。 */
    if (dim === 'sub' && val) {
      const chip = el.closest('.chip');
      if (chip) chip.disabled = !n && browse.sub !== val;
    }
    /* 词性各档同理：与当前感情色彩等条件没有交集的那一档数到 0，
       整枚撤掉（disabled）—— 数字已经是 0 了，再让用户点下去只会得到空表。
       正选着的那一枚例外：它得留着，用户才能点回「不限」。 */
    if (dim === 'pos') {
      const chip = el.closest('.chip');
      if (chip) chip.disabled = !n && browse.pos !== val;
    }
  });
}

/* 筛选「外壳」三件套的就地同步：筛选摘要（.filter-summary）、
   窄屏筛选按钮上的枚数徽标（.ft-count）、面板头「清空筛选」按钮。
   此前这三样只在整页重绘（点筛选 chip）时重算 —— 状态下拉 / 搜索框 /
   每页条数走的是局部刷新（refresh 只重画表格 + refreshFacetCounts），
   于是选了「已掌握」后摘要不出现、徽标不动、面板头也不给清空按钮，
   用户得靠零结果空态才发现筛选在生效（实测窄屏 + 桌面两路都复现）。
   与 views.browse 里的初始渲染共用同一套文案口径，改文案两处一起改。 */
function syncFilterChrome() {
  if (current !== 'browse') return;   // 收藏页没有筛选外壳
  const active = [
    browse.pos ? (browse.pos === POS_OTHER ? POS_LABEL[POS_OTHER] : `词性 ${browse.pos}`) : '',
    browse.core ? (CORE_LABEL[browse.core] || browse.core) : '',
    browse.sub ? `感情色彩 ${esc(SUB_LABEL[browse.sub] || browse.sub)}` : '',
    browse.reg ? `语体色彩 ${esc(browse.reg)}` : '',
    browse.letter ? `首字母 ${esc(browse.letter)}` : '',
    browse.status ? (STATUS_LABEL[browse.status] || browse.status) : '',
    browseQuery().trim() ? `关键词「${esc(browseQuery().trim())}」` : '',
  ].filter(Boolean);
  const n = active.length;
  const sum = $('.filter-summary');
  if (n) {
    const html = active.join(' · ');
    if (sum) sum.innerHTML = html;
    else {
      /* 摘要行不在了（初始渲染时 0 条筛选 → 模板没画这行）：补一行再填内容。
         模板口径：[筛选按钮][摘要行]，摘要是 filter-bar 的弹性尾项。 */
      const bar = $('.filter-bar');
      if (bar) bar.insertAdjacentHTML('beforeend', `<span class="filter-summary">${html}</span>`);
    }
  } else if (sum) sum.remove();
  const badge = $('.ft-count');
  if (n) {
    if (badge) badge.textContent = String(n);
    else {
      /* 徽标不在了（初始渲染时 0 条筛选 → 模板没画）：补一枚（与模板同款空格前缀） */
      const t = $('#btnFilterToggle');
      if (t) t.insertAdjacentHTML('beforeend', ` <span class="ft-count">${n}</span>`);
    }
  } else if (badge) badge.remove();
  const head = $('#btnResetFilters');
  if (n) {
    if (!head) {
      /* 面板头没有清空按钮时补一枚（与初始渲染同一模板、同一绑定） */
      const t = $('.filter-panel-title');
      if (t && t.parentElement) {
        t.insertAdjacentHTML('afterend',
          `<button class="btn sm ghost" id="btnResetFilters">清空筛选</button>`);
        const b = $('#btnResetFilters', t.parentElement);
        if (b) b.onclick = resetBrowseFilters;
      }
    }
  } else if (head) head.remove();
}

/* 当前生效的筛选条件：用于零结果时告诉用户「为什么是空的」 */
function browseActiveFilters() {
  const f = [];
  if (browse.letter) f.push('首字母 ' + browse.letter);
  if (browse.pos) f.push(browse.pos === POS_OTHER ? POS_LABEL[POS_OTHER] : '词性 ' + browse.pos);
  if (browse.core) f.push(CORE_LABEL[browse.core] || browse.core);
  if (browse.sub) f.push('感情色彩 ' + (SUB_LABEL[browse.sub] || browse.sub));
  if (browse.reg) f.push('语体色彩 ' + browse.reg);
  if (browse.status) f.push('状态 ' + (STATUS_LABEL[browse.status] || browse.status));
  const q = browseQuery().trim();
  if (q) f.push('关键词「' + q + '」');
  return f;
}
/* 零结果时的空状态：说明当前筛选并给出「一键清除」，避免只留下一张空表 */
function browseEmptyState() {
  const f = browseActiveFilters();
  const inFav = current === 'fav';
  return `<div class="card empty-state">
    <div class="es">${svgFor('filter')}</div>
    ${inFav ? '收藏里没有匹配的词' : '没有符合条件的词'}
    ${f.length
      ? `<div class="es-filter">${f.map(x => `<span>${esc(x)}</span>`).join('')}</div>
         <div class="mt16"><button class="btn sm" id="btnClearFilters">${svgFor('refresh')} 清除筛选</button></div>`
      : `<div class="faint mt8">${inFav ? '换个关键词再试试' : '换个关键词或状态再试试'}</div>`}
  </div>`;
}
function browseCountLine(rows) {
  // 没有任何筛选且结果就是全库时，不必再写一遍「· 全库 N 词」
  const plain = !browse.onlyFav && !browseActiveFilters().length && rows.length === WORDS_MAX;
  const label = plain
    ? `共匹配 <b>${rows.length}</b> 词`
    : `共匹配 <b>${rows.length}</b> 词${browse.onlyFav ? '（收藏）' : ''} · 全库 ${WORDS_MAX} 词`;
  return `<div class="count-line">
      <span>${label}</span>
      <span class="hstack">
        ${rows.length ? `<button class="btn sm" id="btnStudyFiltered">${svgFor('cards')} ${sessionLabel(rows.length, `学习这 ${rows.length} 个词`)}</button>` : ''}
        ${rows.length ? `<button class="btn sm ghost" id="btnPrint">${svgFor('print')} 打印清单</button>` : ''}
      </span>
    </div>`;
}

/* 只匹配到例句（词形/释义都不含关键词）时挂一枚「例」徽标，避免用户疑惑为何命中；
   表格与卡片两个视图共用 */
function exBadge(w, q) {
  return q && wordMatchQ(w, q.toLowerCase()) === 'ex' ? '<span class="tag-ex" title="仅在例句中匹配">例</span>' : '';
}

function renderBrowseTable(pfx) {
  pfx = pfx || 'browse';
  const rows = browseRows();
  if (!rows.length) return browseCountLine(rows) + browseEmptyState();
  const pages = Math.max(1, Math.ceil(rows.length / browse.per));
  if (pageNow() > pages) pageSet(pages);
  const slice = rows.slice((pageNow() - 1) * browse.per, pageNow() * browse.per);
  const q = browseQuery().trim();
  const hl = t => markHl(t, q);
  const arrow = k => browse.sort === k ? (browse.dir > 0 ? ' ↑' : ' ↓') : '';
  // ↑↓ 只有视觉含义，屏幕阅读器读不出排序方向，补 aria-sort
  const ariaSort = k => browse.sort === k ? (browse.dir > 0 ? 'ascending' : 'descending') : 'none';
  return browseCountLine(rows) + `
    <div class="list-wrap"><table class="word-table"><thead><tr>
      <th scope="col" class="wt-hide-sm" aria-sort="${ariaSort('num')}" title="词条原号：删词留号、增补词自 800 起接续，故号码并不连续（不是漏词）"><button type="button" class="th-sort" data-k="num">原号${arrow('num')}</button></th>
      <th scope="col" aria-sort="${ariaSort('word')}"><button type="button" class="th-sort" data-k="word">单词${arrow('word')}</button></th>
      <th scope="col">释义</th>
      <th scope="col" class="wt-hide-sm" aria-sort="${ariaSort('lv')}"><button type="button" class="th-sort" data-k="lv">状态${arrow('lv')}</button></th><th scope="col" style="width:110px" aria-label="操作"></th>
    </tr></thead><tbody>
      ${slice.map(w => `<tr data-num="${w.num}">
        <td class="wt-num wt-hide-sm">#${w.num}</td>
        <td><button type="button" class="wt-word wt-open" data-open="${w.num}" title="查看「${esc(w.word)}」详情">${hl(w.word)}</button> ${(w.pos ? `<span class="tag-pos">${esc(w.pos)}</span>` : '')}${exBadge(w, q)}<span class="wt-lvl-sm">${lvlChip(w.num)}</span></td>
        <td class="wt-sense">${hl(w.senses[0])}${w.senses.length > 1 ? ' …' : ''}</td>
        <td class="wt-hide-sm">${lvlChip(w.num)}</td>
        <td class="wt-actions">
          <button class="mini-btn" data-act="speak" title="朗读" aria-label="朗读 ${esc(w.word)}">${svgFor('speaker')}</button>
          <button class="mini-btn ${isFav(w.num) ? 'faved' : ''}" data-act="fav" title="收藏" aria-label="收藏 ${esc(w.word)}">${svgFor(isFav(w.num) ? 'star-f' : 'star')}</button>
          <button class="mini-btn" data-act="detail" title="详情" aria-label="查看 ${esc(w.word)} 详情">${svgFor('arrowR')}</button>
        </td></tr>`).join('')}
    </tbody></table></div>
    ${pages > 1 ? `<div class="pager" id="${pfx}Pager"></div>` : ''}`;
}

/* 卡片视图：更适合速览与手机浏览 */
function renderBrowseCards(pfx) {
  pfx = pfx || 'browse';
  const rows = browseRows();
  if (!rows.length) return browseCountLine(rows) + browseEmptyState();
  const pages = Math.max(1, Math.ceil(rows.length / browse.per));
  if (pageNow() > pages) pageSet(pages);
  const slice = rows.slice((pageNow() - 1) * browse.per, pageNow() * browse.per);
  const q = browseQuery().trim();
  const hl = t => markHl(t, q);
  return browseCountLine(rows) + `
    <div class="wcard-grid">
      ${slice.map(w => `<div class="wcard" data-num="${w.num}" tabindex="0" role="button">
        <div class="wc-top"><span class="wc-word">${hl(w.word)}</span>${w.pos ? `<span class="tag-pos">${esc(w.pos)}</span>` : ''}${exBadge(w, q)}<span class="wc-num">#${w.num}</span></div>
        <div class="wc-sense">${hl(w.senses[0])}${w.senses.length > 1 ? ' …' : ''}</div>
        ${exBlock(w, { max: 1, cls: 'wc-ex', showZh: false })}
        <div class="wc-foot">
          ${lvlChip(w.num)}
          <span style="margin-left:auto;display:flex;gap:2px">
            <button class="mini-btn" data-act="speak" title="朗读" aria-label="朗读 ${esc(w.word)}">${svgFor('speaker')}</button>
            <button class="mini-btn ${isFav(w.num) ? 'faved' : ''}" data-act="fav" title="收藏" aria-label="收藏 ${esc(w.word)}">${svgFor(isFav(w.num) ? 'star-f' : 'star')}</button>
          </span>
        </div>
      </div>`).join('')}
    </div>
    ${pages > 1 ? `<div class="pager" id="${pfx}Pager"></div>` : ''}`;
}

/* 三种视图：表格 / 卡片 / 按词性分组。
   分组视图是原「分类」页的版式（按词性分区 + 形容词再按感情色彩三分），
   已并入词库，不再单独占一个导航页。
   收藏用自己的一份视图状态：分组版式是「全库按词性铺开」的整体版式，
   收藏仍只有表格/卡片两种。 */
function renderBrowseBody(pfx, view) {
  pfx = pfx || 'browse';
  const v = view || (pfx === 'fav' ? browse.favView : browse.view);
  if (v === 'group') return renderBrowseGroup(pfx);
  return v === 'cards' ? renderBrowseCards(pfx) : renderBrowseTable(pfx);
}

/* ---------- 按词性分组（原「分类」页） ---------- */
const CAT_ORDER = [
  { pos: '形容词', icon: '🎨', desc: '按感情色彩分为积极 / 消极 / 争议 / 中性四组，写作表态时最常用。', deck: 'adj' },
  { pos: '副词', icon: '🚀', desc: '修饰动词与整句，精确表达程度与方式。', deck: 'adv' },
  { pos: '动词', icon: '⚙️', desc: '学术写作中的论证、描述与对比动作。', deck: 'verb' },
  { pos: '名词', icon: '🧩', desc: '概念与对象名词。', deck: 'noun' },
  { pos: '连词', icon: '🔗', desc: '衔接逻辑关系，篇章组织的骨架。', deck: 'conj' },
];
/* 感情色彩分组的牌组：副词/连词/介词不带评价色彩，故只有这三类实词分组。
   牌组本身取全库同档的词（不只是形容词）——第七十轮起感情色彩跨了名词与动词。 */
const SUB_DECK = { '积极的': 'sub+', '消极的': 'sub-', '争议性的': 'sub?', '中性的': 'sub0' };
/* 无实义词性标签那一组：单词介词与介词性固定短语（due to / via / regarding …）。
   原先它们在分组视图里被整批丢掉（只在页头用一句话交代「不入分组」），
   现补一节「介词」，与筛选面板那一档一一对应。 */
const OTHER_SEC = { pos: POS_OTHER, icon: '📎', title: POS_OTHER_LABEL, desc: '单词介词与介词性固定短语，不归入五类实义词性。', deck: 'other' };

/* 分组视图：当前筛选结果按词性分区铺开，形容词再按感情色彩三分。
   分区里的词是筛选后的子集，所以「核心词 + 消极的」这类组合也成立。 */
function renderBrowseGroup(pfx) {
  pfx = pfx || 'browse';
  const rows = browseRows();
  if (!rows.length) return browseCountLine(rows) + browseEmptyState();
  const byPos = {};
  rows.forEach(w => { if (w.pos) (byPos[w.pos] = byPos[w.pos] || []).push(w); });
  const secs = CAT_ORDER.filter(s => byPos[s.pos] && byPos[s.pos].length);
  const otherItems = rows.filter(w => !w.pos);
  if (!secs.length && !otherItems.length) {
    return browseCountLine(rows) + `<div class="card empty-state"><div class="es">${svgFor('filter')}</div>
      匹配到的词里没有带词性标签的条目<div class="faint mt8">清掉词性或首字母筛选试试</div></div>`;
  }
  /* 分组视图铺开带词性的词；介词与介词短语那批归到末尾的「介词」一节，
     两边加起来才等于「共匹配 N 词」，不用再在页头解释差额。 */
  const grouped = Object.values(byPos).reduce((a, b) => a + b.length, 0);
  const note = otherItems.length
    ? (grouped
        ? `<div class="faint" style="font-size:12.5px;margin:-2px 0 16px">其中 <b>${grouped}</b> 词按词性与感情色彩分组，<b>${otherItems.length}</b> 词为单词介词与介词性固定短语，归入「${POS_OTHER_LABEL}」</div>`
        : `<div class="faint" style="font-size:12.5px;margin:-2px 0 16px">匹配到的 <b>${otherItems.length}</b> 词全是单词介词与介词性固定短语（无实义词性标签），归入「${POS_OTHER_LABEL}」</div>`)
    : '';
  const body = secs.map(s => renderCatSection(s, byPos[s.pos])).join('')
    + (otherItems.length ? renderCatSection(OTHER_SEC, otherItems) : '');
  return browseCountLine(rows) + note + `<div class="group-view" id="browseGroup">${body}</div>`;
}
function renderCatSection(sec, items) {
  items = items || WORDS.filter(w => w.pos === sec.pos);
  let html = '';
  /* 感情色彩跨了形容词/名词/动词三类实词，这三节按色彩再分四组；
     副词/连词不带评价色彩（落在「其他」档），平铺即可。 */
  if (SUB_POS.indexOf(sec.pos) >= 0) {
    html += SUB_ORDER.map(sub => {
      const subItems = items.filter(w => w.sub === sub);
      if (!subItems.length) return '';
      const emo = sub === '积极的' ? '😊' : sub === '消极的' ? '⚠️' : sub === '争议性的' ? '⚖️' : '➖';
      return `<div style="margin:16px 0 6px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <span class="chip" style="pointer-events:none">${emo} ${sub} <span class="cnt">${subItems.length}</span></span>
          <button class="btn sm ghost" data-catdeck="${SUB_DECK[sub]}">🃏 本组学习</button>
        </div>
        <div class="cat-words">${subItems.map(catWordCard).join('')}</div>`;
    }).join('');
  } else {
    html = `<div class="cat-words">${items.map(catWordCard).join('')}</div>`;
  }
  return `<section class="cat-section" data-pos="${sec.pos}">
    <div class="cat-title">${sec.icon} ${sec.title || sec.pos}<span class="n">${items.length} 词</span>
      <button class="btn sm ghost" data-catdeck="${sec.deck}" style="margin-left:auto">🃏 本类学习</button></div>
    <div class="cat-desc">${sec.desc}</div>${html}</section>`;
}
function catWordCard(w) {
  return `<div class="cat-word" data-num="${w.num}" tabindex="0" role="button" aria-label="查看「${esc(w.word)}」详情">
    <span class="num">#${w.num}</span>
    <div class="w">${esc(w.word)}</div>
    <div class="g">${esc((w.catGloss || w.senses[0]))}</div></div>`;
}

/* ---------------------------- 打印清单 ---------------------------- */
/* 打印版单独渲染：单词 + 释义 + 全部例句（英文 + 中文），打印时只显示这一块 */
function renderPrintList(rows, scopeOverride) {
  const el = $('#printList');
  if (!el) return;
  const list = rows || [];
  // 打印时也带上当前筛选条件，纸面上能看出这份清单是从哪个范围导出的
  const f = browseActiveFilters();
  const scope = scopeOverride ? [scopeOverride] : current === 'fav' ? ['收藏'] : (f.length ? f : ['全部词库']);
  el.innerHTML = `
    <div class="pl-head">
      <h1 class="pl-title">学术英语词汇清单 · ${list.length} 词</h1>
      <div class="pl-meta">导出于 ${todayStr()} · 每词附例句 · 范围：${esc(scope.join('、'))}</div>
    </div>
    <div class="pl-list">${list.map(w => `
      <div class="pl-item">
        <div class="pl-w">${esc(w.word)}${w.pos ? `<span class="pl-pos">${esc(w.pos)}</span>` : ''}</div>
        <div class="pl-g">${esc(w.senses.join('；'))}</div>
        ${exOf(w).map(e => `<div class="pl-ex"><span class="pl-ex-en">${esc(e.en)}</span><span class="pl-ex-zh">${esc(e.zh)}</span></div>`).join('')}
      </div>`).join('')}</div>`;
}

// 用户自己按 Ctrl+P / 菜单打印时，#printList 可能还是空的（只有点「打印清单」
// 按钮才会填充），而打印样式隐藏其余全部内容 → 开印前统一重建。
// 分类页另走分类语义：屏幕上停在哪个词性筛选就印哪个类别，
// 不能拿词库页的过期筛选冒充「当前范围」（纸上曾写「全部词库」误导）。
window.addEventListener('beforeprint', () => {
  if (current === 'browse' || current === 'fav') {
    /* 分组视图也走这一支：分组页并入词库后，纸面上的清单就是「当前筛选结果」，
       筛选摘要（browseActiveFilters）会把词性/感情色彩等条件写在纸头，
       不再另造一套「词性分类 · 某类别」的打印语义。 */
    renderPrintList(browseRows());
  } else {
    /* 其它视图（首页/学习/测验/统计/设置）不拿词库页的过期筛选冒充当前范围：
       此前在测验页按 Ctrl+P 会印出「首字母 K」这样一份与屏幕无关的清单，
       去过收藏后更会只印收藏却标着「收藏」。这里统一印全库并在纸上写明。 */
    renderPrintList(WORDS, '全部词库');
  }
});

function bindBrowseTable(scope) {
  // 排序钮是真正的 <button>：Enter/空格原生激活（onAct 门控自动让路），
  // 屏幕阅读器读 th 的 aria-sort——此前挂在裸 th.onclick 上，键盘用户够不着排序
  $$('.th-sort', scope).forEach(b => b.onclick = () => {
    const k = b.dataset.k;
    if (browse.sort === k) browse.dir *= -1; else { browse.sort = k; browse.dir = 1; }
    rerenderIfBrowse();
  });
  $$('[data-num]', scope).forEach(tr => {
    const num = +tr.dataset.num;
    const open = e => {
      const act = e.target.closest('[data-act]')?.dataset.act;
      if (act === 'speak') { speak(BY_NUM[num].word); return; }
      if (act === 'fav') { toggleFav(num); rerenderIfBrowse(); return; }
      // 整行可点，但把焦点落到单词按钮上：关闭详情后焦点能回到原处
      const btn = tr.querySelector('.wt-open');
      if (btn && e.target !== btn) btn.focus();
      openWordModal(num);
    };
    tr.onclick = open;
    tr.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(e); } };
  });
  const pg = $('#' + (scope.dataset.pager || 'browsePager'), scope);
  if (pg) {
    const rows = browseRows(), pages = Math.ceil(rows.length / browse.per);
    const cur = pageNow();
    let h = `<button ${cur <= 1 ? 'disabled' : ''} data-p="prev" aria-label="上一页">‹</button>`;
    const set = new Set([1, pages, cur, cur - 1, cur + 1].filter(p => p >= 1 && p <= pages));
    const arr = Array.from(set).sort((a, b) => a - b); let prev = 0;
    arr.forEach(p => { if (p - prev > 1) h += '<button disabled>…</button>'; h += `<button class="${p === cur ? 'on' : ''}" data-p="${p}"${p === cur ? ' aria-current="page"' : ''}>${p}</button>`; prev = p; });
    h += `<button ${cur >= pages ? 'disabled' : ''} data-p="next" aria-label="下一页">›</button>`;
    pg.innerHTML = h;
    $$('button', pg).forEach(b => b.onclick = () => {
      const v = b.dataset.p;
      pageSet(v === 'prev' ? Math.max(1, cur - 1) : v === 'next' ? Math.min(pages, cur + 1) : +v);
      rerenderIfBrowse();
    });
  }
  const bp = $('#btnPrint', scope);
  if (bp) bp.onclick = () => { renderPrintList(browseRows()); window.print(); };
  const sf = $('#btnStudyFiltered', scope);
  if (sf) sf.onclick = () => {
    const list = browseRows();
    if (!list.length) { toast('当前筛选没有单词'); return; }
    fc.custom = list;
    pendingDeck = { src: 'custom' };
    if (location.hash === '#study') renderView('study'); else location.hash = '#study';
  };
  const cf = $('#btnClearFilters', scope);
  if (cf) cf.onclick = resetBrowseFilters;
  /* 分组视图里的「本类/本组学习」按钮：分组视图并入词库后，这组按钮随
     #browseTable 一起重绘（筛选一变就换 innerHTML），子节点上的监听会跟着没，
     所以把委托挂在容器上；用 onclick 赋值（重复调用幂等），容器本身不换。 */
  scope.onclick = e => {
    const deck = e.target.closest('[data-catdeck]');
    if (!deck) return;
    fc.session = 0;
    pendingDeck = { src: deck.dataset.catdeck };
    if (location.hash === '#study') { renderView('study'); } else { location.hash = '#study'; }
  };
}
function rerenderIfBrowse() {
  if (current !== 'browse' && current !== 'fav') return;
  const y = scrollY;
  renderView(current);
  requestAnimationFrame(() => scrollTo(0, y));
}

/* ============================ 视图 ============================ */
let current = 'home';
const views = {};

/* 随机一词：**每次页面加载/刷新**随机抽一个词（用户直令：「刷新或重新访问，
   就更新一个新的」）。抽签锚在模块加载——app.js 只在整页加载时跑一次，
   会话内切页/回首页都是 renderView 重渲染，不会重跑这里 ⇒ 同一次访问里
   面板词保持不变；刷新/重开标签页 = 重新加载 app.js = 重新抽签。
   此前把抽签值存 sessionStorage 试图区分「切页」与「刷新」，但 sessionStorage
   本就随标签页跨刷新存活 ⇒ 刷新读到的还是旧值，词永远不变（用户实测报出）。
   Math.random 恒在 [0,1)，|0 取整后恒落在 0..N-1，无负索引之虞
   （此前按「日序取模」轮播时机器时钟早于 1970 会算出负索引——随机口径下该雷不复存在）。 */
let wod = WORDS.length ? WORDS[(Math.random() * WORDS_MAX) | 0] : null;

/* 手动重抽一个词：给「随机一词」面板的刷新按钮用。
   抽签结果写回模块级 `wod`——首页此后所有重渲染（改目标、切页回来）都用新词。
   刻意避开当前这个词：全库两千多词时撞回同一个的概率约 1/2000，
   但那一次用户会看到「按了刷新、词没变」，像是按钮坏了——宁可重抽一次。 */
function rerollWord() {
  if (!WORDS.length) return null;
  let nw = WORDS[(Math.random() * WORDS_MAX) | 0];
  if (WORDS.length > 1 && nw.num === wod.num) {
    nw = WORDS[(Math.random() * WORDS_MAX) | 0];   // 再抽一次；极端情况下仍可能相同
  }
  wod = nw;
  return nw;
}

/* 「随机一词」面板的词条区（词 + 释义 + 首条例句）。
   单独抽成函数：初次渲染与「刷新」后重画共用同一份模板——
   此前两处各写一遍模板，改一处忘了另一处就会出现「刷新后版式与初始不同」。 */
function wodPanelHtml(w) {
  if (!w) return '<div class="senses">词库为空</div>';
  const ex = exOf(w)[0];
  return `<div class="w">${esc(w.word)}</div>
       <div class="senses">${esc(w.senses.join(' / '))}</div>
       ${ex ? `<div class="rand-word-ex">
         <div class="rand-word-ex-en">${esc(ex.en)}</div>
         <div class="rand-word-ex-zh">${esc(ex.zh)}</div>
       </div>` : ''}`;
}

/* ---------- 首页 ---------- */
views.home = (root) => {
  const tc = tierCounts();
  const due = tc.due, mastered = tc.mastered, learning = tc.learning, newCount = tc.new;
  const wodHtml = wodPanelHtml(wod);
  const recent = state.quizHist.slice(-5).reverse();
  // 最需要加强的词：按累计答错次数排序，取前 5 个还没掌握的
  const weakList = WORDS
    .map(w => ({ w, wrong: (prog(w.num)?.wrong || 0) }))
    .filter(x => x.wrong > 0 && !isMastered(x.w.num))
    .sort((a, b) => b.wrong - a.wrong || a.w.num - b.w.num)
    .slice(0, 5)
    .map(x => ({ num: x.w.num, word: x.w.word, senses: x.w.senses, wrong: x.wrong }));
  // 情境化主行动：有到期词先复习 → 否则继续未掌握 → 否则开新词 →
  // 全库都学完（新词归零）时指向已掌握词做保温复习，而不是留一个 0 词死路
  let ctaLabel, ctaSrc;
  if (due > 0)          { ctaLabel = sessionLabel(due, `复习 ${due} 个到期词`); ctaSrc = 'due'; }
  else if (learning > 0){ ctaLabel = sessionLabel(learning, `继续学习 ${learning} 词`); ctaSrc = 'learning'; }
  else if (newCount > 0){ ctaLabel = sessionLabel(newCount, `从新词开始（${newCount}）`, `从新词开始（${newCount} 词 · 本次 ${sessionLimit()} 张）`); ctaSrc = 'new'; }
  else                  { ctaLabel = sessionLabel(mastered, `保温复习 ${mastered} 个已掌握词`); ctaSrc = 'mastered'; }
  // 今日目标环形进度
  const goal = state.settings.goal, act = todayActivity();
  const gPct = Math.min(100, Math.round(act / goal * 100));
  const R = 42, CIRC = 2 * Math.PI * R;
  // 近 7 天活跃
  const week = [];
  for (let i = 6; i >= 0; i--) {
    const d = dayOffset(-i);          // 按自然日推进，避免夏令时偏移
    week.push({ lbl: '日一二三四五六'[d.getDay()], n: state.days[dayKey(d)] || 0, today: i === 0 });
  }
  const maxW = Math.max(1, ...week.map(w => w.n));
  const weekSum = week.reduce((s, w) => s + w.n, 0);
  root.innerHTML = `
  <section class="hero">
    <div style="flex:1;min-width:280px">
      <span class="eyebrow">${svgFor('sparkles')} 学术英语词库 · 查词 · 学习 · 测验</span>
      <h1>常见的学术英语词汇</h1>
      <p>词库共 ${WORDS_MAX} 词，含 ${CORE_MAX} 个论文里最常见的高频词；带词性与褒贬色彩标注，配 3 条例句（中英对照）。查词、翻卡、做测验，随取随用。不必刻意背诵，先读懂含义与语境，写作时再精准取用。</p>
      <div class="hero-actions">
        <button class="btn big primary" id="goReview">${svgFor('cards')} ${ctaLabel}</button>
        <button class="btn big" id="goQuiz">${svgFor('pen')} 快速测验</button>
        <button class="btn big" id="goBrowse">${svgFor('book')} 浏览词库</button>
      </div>
      <div class="hero-hint">
        <span>${svgFor('keyboard')} 按 <kbd>/</kbd> 搜索</span>
        <span>${svgFor('zap')} 学习时按 <kbd>空格</kbd> 翻卡</span>
        <span>${svgFor('info')} 按 <kbd>?</kbd> 看全部快捷键</span>
      </div>
    </div>
    <div class="rand-word">
      <div class="rand-word-head">
        <span class="phon-hint">${svgFor('dice')} 随机一词</span>
        ${wod ? `<button class="rand-refresh" id="wodRefresh" title="刷新：换一个词" aria-label="刷新：换一个词">${svgFor('refresh')}</button>` : ''}
      </div>
      ${wodHtml}
      ${wod ? `<div class="rand-word-foot">
        <button class="speak-btn sm" id="wodSpeak" title="朗读" aria-label="朗读">${svgFor('speaker')}</button>
        <button class="btn-link faint" id="wodDetail">词条 #${wod.num} 详情 →</button>
        <button class="btn-link faint" id="wodReroll" title="换一个词" aria-label="换一个词">${svgFor('shuffle')} 换一个</button>
      </div>` : ''}
    </div>
  </section>

  <div class="dash-stats">
    <div class="stat-card" data-goto="mastered" role="button" tabindex="0" title="查看已掌握词汇"><div class="k"><span class="sc-ic">${svgFor('target')}</span>已掌握</div><div class="v">${mastered}<small> / ${WORDS_MAX}</small></div></div>
    <div class="stat-card" data-goto="learning" role="button" tabindex="0" title="查看学习中的词汇"><div class="k"><span class="sc-ic">${svgFor('seed')}</span>学习中</div><div class="v">${learning}</div></div>
    <div class="stat-card" data-goto="due" role="button" tabindex="0" title="开始复习到期词汇" aria-label="今日待复习，开始复习到期词汇"><div class="k"><span class="sc-ic">${svgFor('alarm')}</span>今日待复习</div><div class="v">${due}</div></div>
    <div class="stat-card" data-goto="fav" role="button" tabindex="0" title="打开收藏"><div class="k"><span class="sc-ic">${svgFor('star')}</span>收藏</div><div class="v">${favWords().length}</div></div>
    <div class="stat-card" data-goto="stats" role="button" tabindex="0" title="查看学习统计" aria-label="连续学习，查看学习统计"><div class="k"><span class="sc-ic">${svgFor('flame')}</span>连续学习</div><div class="v">${streak()}<small> 天</small></div></div>
  </div>

  <div class="home-grid">
    <div class="card">
      <div class="panel-h">今日进度 <button class="chip" id="goalEdit">目标 ${goal} 次 · 修改</button></div>
      <div class="card-pad">
        <div class="ring-wrap">
          <div class="ring">
            <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
              <defs><linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent-2)"/>
              </linearGradient></defs>
              <circle cx="48" cy="48" r="${R}" fill="none" stroke="var(--line-2)" stroke-width="9"/>
              <circle cx="48" cy="48" r="${R}" fill="none" stroke="url(#ringGrad)" stroke-width="9" stroke-linecap="round"
                      stroke-dasharray="${CIRC.toFixed(1)}" stroke-dashoffset="${(CIRC * (1 - gPct / 100)).toFixed(1)}"/>
            </svg>
            <div class="ring-label">${act}<small>／ ${goal} 次</small></div>
          </div>
          <div style="flex:1;min-width:180px">
            <div class="goal-row"><span>复习 + 测验交互次数</span><span><b>${act}</b> / ${goal}</span></div>
            <div class="progress-line"><div style="width:${gPct}%"></div></div>
            <p class="${act >= goal ? '' : 'faint'} mt8" style="${act >= goal ? 'color:var(--good);font-size:13.5px' : ''}">
              ${act >= goal ? '今日目标已完成，随时可以停下' : '还没到今日目标也没关系，想练就练'}
            </p>
            <p class="faint mt8" style="font-size:12.6px">${svgFor('cal')} 复习预报：未来 48 小时内将到期 <b>${tc.dueTomorrow}</b> 词 · 未来 7 天内 <b>${tc.dueWeek}</b> 词</p>
          </div>
        </div>
        <div class="sec-title mt24" style="margin-bottom:8px">${svgFor('trend')} 近 7 天活跃</div>
        <div class="week-bars${weekSum ? '' : ' empty'}">
          ${week.map(w => `<div class="wb ${w.n ? '' : 'zero'}" title="${w.lbl} · ${w.n} 次">
            <span class="n">${w.n || ''}</span>
            <div class="track"><div class="bar" style="height:${w.n ? Math.max(6, w.n / maxW * 58) : 0}px"></div></div>
            <span class="lbl" style="${w.today ? 'color:var(--accent);font-weight:800' : ''}">${w.lbl}</span>
          </div>`).join('')}
        </div>
        ${weekSum ? '' : `<div class="empty-inline mt12">${svgFor('info')} 最近 7 天还没有学习记录，想开始时从上面选个范围即可。</div>`}
      </div>
      <p class="faint" style="padding:0 18px 16px;font-size:12.8px;line-height:1.7">
        ${svgFor('bulb')} 小建议：用「未学习新词」扩充生词，用「复习队列」按记忆曲线巩固；把收藏里的词单独开一组学习，效果更好。
      </p>
    </div>

    <div class="home-side">
      <div class="card">
        <div class="panel-h">最近测验 <a class="link-more" href="#study" data-goquiz="1">去测验 →</a></div>
        <div class="card-pad">
          ${recent.length ? recent.map(h => {
            const p = pct(h.score, h.total);
            // 全跳过的场次（total=0）显示「未作答」，不给一个刺眼的红色 0/0
            return `<div class="quiz-hist-item">
              <span class="qh-mode">${svgFor('pen')} ${esc(histModeName(h))} <span class="faint">· ${esc(histScopeName(h))}${h.skipped ? ` · 跳过 ${h.skipped}` : ''}</span></span>
              <span class="qh-score ${h.total ? (p >= 70 ? 'good' : p >= 50 ? 'mid' : 'low') : 'none'}">${h.total ? `${h.score}/${h.total}` : '未作答'}</span>
              <span class="faint">${fmtTime(h.t)}</span></div>`;
          }).join('')
            : `<div class="empty-state"><div class="es">${svgFor('target')}</div>还没有测验记录<br><a class="btn primary sm mt16" href="#study" data-goquiz="1">开始第一次测验</a></div>`}
        </div>
      </div>

      <div class="card">
        <div class="panel-h">最需要加强的词 <a class="link-more" href="#stats">看统计 →</a></div>
        <div class="card-pad">
          ${weakList.length ? weakList.map(w => `
            <div class="weak-item" data-num="${w.num}" role="button" tabindex="0">
              <span class="wi-word">${esc(w.word)}</span>
              <span class="wi-sense">${esc(w.senses[0])}</span>
              <span class="wi-wrong" title="答错次数">${svgFor('x')} ${w.wrong}</span>
            </div>`).join('')
            : `<div class="empty-state" style="padding:30px 16px"><div class="es">${svgFor('check')}</div>还没有答错的词<br><span class="faint">暂时没有需要重来的词</span></div>`}
        </div>
      </div>
    </div>
  </div>`;
  $('#goReview').onclick = () => {
    pendingDeck = { src: ctaSrc };
    if (location.hash === '#study') renderView('study'); else location.hash = '#study';
  };
  $('#goQuiz').onclick = () => { studyTab = 'quiz'; location.hash = '#study'; };
  $('#goBrowse').onclick = () => location.hash = '#browse';
  /* 「按词性分组」入口已从首页移除（快捷入口整块去掉）。
     分组视图现在走词库页工具栏的视图切换按钮；分享链接 #cats 仍能直接落到分组视图。 */
  /* 「刷新」（面板右上角图标按钮）与「换一个」（底部文字链）做同一件事：
     当场重抽一个词并只重画这块面板（整页重渲染会让目标进度、最近测验等
     卡片跟着抖）。抽签结果写回模块级 `wod`——首页此后所有重渲染
     （改目标、切页回来）都用新词。
     重画走同一个模板函数（wodPanelHtml）+ 重新绑定（bindWodPanel），
     两处入口共用一条路径：此前只有「换一个」一条，重画模板与初始渲染
     各写一份，容易漂。 */
  const bindWodPanel = (w) => {
    if (!w) return;
    $('#wodSpeak').onclick = () => speak(w.word);
    $('#wodDetail').onclick = () => openWordModal(w.num);
    const reroll = () => {
      const nw = rerollWord();
      if (!nw) return;
      const panel = $('#wodReroll').closest('.rand-word');
      panel.innerHTML = `
      <div class="rand-word-head">
        <span class="phon-hint">${svgFor('dice')} 随机一词</span>
        <button class="rand-refresh" id="wodRefresh" title="刷新：换一个词" aria-label="刷新：换一个词">${svgFor('refresh')}</button>
      </div>
      ${wodPanelHtml(nw)}
      <div class="rand-word-foot">
        <button class="speak-btn sm" id="wodSpeak" title="朗读" aria-label="朗读">${svgFor('speaker')}</button>
        <button class="btn-link faint" id="wodDetail">词条 #${nw.num} 详情 →</button>
        <button class="btn-link faint" id="wodReroll" title="换一个词" aria-label="换一个词">${svgFor('shuffle')} 换一个</button>
      </div>`;
      fixIcons(panel);
      bindWodPanel(nw);
    };
    $('#wodReroll').onclick = reroll;
    const rf = $('#wodRefresh');
    if (rf) rf.onclick = reroll;
  };
  if (wod) bindWodPanel(wod);
  $('#goalEdit').onclick = () => {
    const chip = $('#goalEdit');
    const input = document.createElement('input');
    input.type = 'number'; input.min = 5; input.max = 200; input.value = state.settings.goal;
    input.className = 'goal-edit-input'; input.setAttribute('aria-label', '每日目标次数');
    chip.replaceWith(input); input.focus(); input.select();
    let cancelled = false;   // Esc 取消：必须在重绘前置位，否则移除输入框触发的 blur 会把值提交掉
    const commit = () => {
      if (cancelled) return;
      /* 数字归一：空串/非数字才落默认 30。`+v || 30` 会把**合法输入 0** 当 falsy
         顶成 30，而 -5 又钳到下限 5 —— 同是越界值两种落点。0 与负数应同走
         「钳到下限 5」这一条口径（二百零一轮）。 */
      const v = input.value.trim();
      const n = Math.round(Math.min(200, Math.max(5, v === '' || !Number.isFinite(+v) ? 30 : +v)));
      state.settings.goal = n; save(); renderView('home');
    };
    input.onblur = commit;
    input.onkeydown = e => {
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      else if (e.key === 'Escape') { e.preventDefault(); cancelled = true; renderView('home'); }
    };
  };
  $$('.weak-item').forEach(el => {
    const open = e => { e.preventDefault(); openWordModal(+el.dataset.num); };
    el.onclick = open;
    el.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') open(e); };
  });
  $$('.stat-card[data-goto]').forEach(c => {
    const v = c.dataset.goto;
    const go = () => {
      if (v === 'mastered' || v === 'learning') {
        // 从首页跳过来时清掉词库页残留的筛选（关键词 / 首字母 / 词性 /
        // 感情色彩），否则「已掌握」的列表会被看不见的条件截短——
        // 此前漏了 sub（感情色彩）：词库页筛过「积极的」再回首页点「已掌握」，
        // 列表静默变成「感情色彩 积极的 · 已掌握」的交集（实测 0 词）。
        browse.status = v; browse.q = ''; browse.letter = ''; browse.pos = ''; browse.core = ''; browse.sub = ''; browse.reg = '';
        browse.onlyFav = false; pageSet(1);
        if (location.hash === '#browse') renderView('browse'); else location.hash = '#browse';
      } else if (v === 'due') {
        pendingDeck = { src: 'due' };
        if (location.hash === '#study') renderView('study'); else location.hash = '#study';
      } else if (v === 'fav') location.hash = '#fav';
      else location.hash = '#stats';
    };
    c.onclick = go;
    // 与 .weak-item 同款键盘约定：Enter / 空格触发，空格不滚页
    c.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } };
  });
  /* 首页的「去测验 →」「开始第一次测验」：合并后测验不再有独立 hash，
     落 #study 时顺手切到测验模式（纯 hash 导航会停在翻卡模式的面板上）。 */
  $$('a[data-goquiz]').forEach(a => a.addEventListener('click', () => { studyTab = 'quiz'; }));
};
function fmtTime(t) {
  /* 时间戳缺失/非数字（损坏备份里没有 t）时不要把 NaN 渲染到页面上：
     new Date(undefined) 是 Invalid Date，取 getMonth() 得 NaN。 */
  if (!Number.isFinite(t)) return '时间未知';
  const d = new Date(t), n = new Date();
  if (Number.isNaN(d.getTime())) return '时间未知';
  const sameDay = d.toDateString() === n.toDateString();
  // 同日只给时刻，其余给「M月D日」——比 M/D 更不容易看错年月
  return sameDay ? `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}` : `${d.getMonth() + 1}月${d.getDate()}日`;
}
/* 统计页「最近测验记录」用的完整时间：同样要挡住坏时间戳，
   否则 new Date(undefined).toLocaleString() 会把 "Invalid Date" 印到纸上。 */
function fmtDateTime(t) {
  if (!Number.isFinite(t)) return '时间未知';
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return '时间未知';
  return d.toLocaleString('zh-CN', { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/* ---------- 词库 ---------- */
views.browse = (root) => {
  browse.onlyFav = false;
  /* 旧链接 #cats（已并入词库的分组视图）落到本页时给一次分组视图；
     用完即弃，不改用户自己选的视图状态（否则以后每次进词库都是分组版式）。 */
  const groupOnce = browse.groupOnce;
  browse.groupOnce = false;
  const curView = groupOnce ? 'group' : browse.view;
  /* 分面计数：每个选项旁的数字 = 点了它之后结果里还剩多少词
     （按当前其它筛选条件算，不受该维度自身当前取值影响）。
     基准集只算一次（收藏 + 关键词），各维度在其上叠自己的条件。 */
  const facetBase = browseFacetBase();
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map(L => {
    const n = browseFacetCount('letter', L, facetBase);
    return `<button class="letter-btn ${browse.letter === L ? 'on' : ''} ${n ? '' : 'dim'}" data-l="${L}">${L}<small data-fcnt="letter|${L}">${n}</small></button>`;
  }).join('');
  /* 「词性」行：五种实义词性 + 「介词」（那批没有实义词性标签的词）。
     「核心」不是词性（它跨五种词性），故另起一行「是否核心」，两层正交可叠加。 */
  const posList = ['全部', '形容词', '副词', '动词', '名词', '连词'];
  const otherN = OTHER_WORDS().length;
  const coreN = CORE_MAX;
  const nonCoreN = WORDS_MAX - CORE_MAX;
  /* 每个选项旁的数字：按当前其它筛选条件算，点下去会剩多少词
     （分面计数，跨维度可叠加 —— 见 browseFacetCount）。 */
  /* 词性各档与「感情色彩」各档同一口径：与当前其它条件（感情色彩 / 是否核心 /
     语体 / 首字母…）没有交集的那一档数到 0，整枚撤掉 —— 数字已经写着 0，
     还让用户点下去只会换来一张空表。正选着的那一枚留着（好点回「不限」）。 */
  const posCnt = p => browseFacetCount('pos', p === '全部' ? '' : p, facetBase);
  const posChip = (val, label, title) => {
    const n = posCnt(val || '全部');
    const dis = !n && browse.pos !== val;
    const on = browse.pos === val ? 'on' : '';
    const ttl = title ? `title="${title}" ` : '';
    return `<button class="chip ${on}" ${dis ? 'disabled ' : ''}${ttl}data-pos="${val}">${label} <span class="cnt" data-fcnt="pos|${val}">${n}</span></button>`;
  };
  const coreCnt = c => browseFacetCount('core', c, facetBase);
  const subCnt = s => browseFacetCount('sub', s, facetBase);
  /* 「其他」（未标注）这一档的词数：各档之和要与「不限」对齐，
     差额（= 没标注感情色彩的词）单列一档，用户才够得着。 */
  const subOtherN = subCnt(SUB_OTHER);
  const regCnt = r => browseFacetCount('reg', r, facetBase);
  const letterCnt = L => browseFacetCount('letter', L, facetBase);
  const statusCnt = k => browseFacetCount('status', k, facetBase);
  /* 感情色彩这一排**永远显示**：词性锁到副词/连词/介词时，
     四个带标签的档恒为 0（显示 0、灰显不可点），「其他」那一档 = 该词性全体 ——
     用户能一眼看出「这一类词不带评价色彩」，而不是面对一行凭空消失的筛选项。 */
  const subChip = (val, label, title) => {
    const n = subCnt(val);
    const dis = !n && browse.sub !== val;   // 够不着词就撤掉；正选着的那枚留着（好点回「不限」）
    return `<button class="chip ${browse.sub === val ? 'on' : ''}" ${dis ? 'disabled ' : ''}${title ? `title="${title}" ` : ''}data-sub="${val}">${label} <span class="cnt" data-fcnt="sub|${val}">${n}</span></button>`;
  };
  // 窄屏上筛选条会占掉整屏，这里默认收起；有筛选条件时自动展开，避免"筛掉了却看不见"
  // 摘要文案口径与 syncFilterChrome 同一份（那里是局部刷新路径的就地同步）——
  // 改文案（维度名 / 拼接符）两处必须一起改。
  const activeFilterCount = (browse.pos ? 1 : 0) + (browse.core ? 1 : 0) + (browse.sub ? 1 : 0) + (browse.reg ? 1 : 0) + (browse.letter ? 1 : 0) + (browse.status ? 1 : 0) + (browse.q.trim() ? 1 : 0);
  const activeFilterText = [
    browse.pos ? (browse.pos === POS_OTHER ? POS_LABEL[POS_OTHER] : `词性 ${browse.pos}`) : '',
    browse.core ? (CORE_LABEL[browse.core] || browse.core) : '',
    browse.sub ? `感情色彩 ${esc(SUB_LABEL[browse.sub] || browse.sub)}` : '',
    browse.reg ? `语体色彩 ${esc(browse.reg)}` : '',
    browse.letter ? `首字母 ${esc(browse.letter)}` : '',
    browse.status ? (STATUS_LABEL[browse.status] || browse.status) : '',
    browse.q.trim() ? `关键词「${esc(browse.q.trim())}」` : '',
  ].filter(Boolean).join(' · ');
  const filtersOpen = browse.filtersOpen === null ? activeFilterCount > 0 : browse.filtersOpen;
  root.innerHTML = `
    <h1 class="page-title">${svgFor('book')} 词库浏览 <span class="faint">共 ${WORDS_MAX} 词</span></h1>
    <div class="page-sub">点击词条看详情 · 支持英文与中文释义搜索</div>
    <div class="toolbar">
      <div class="search-wrap"><input type="search" id="bq" placeholder="搜索单词或释义…" value="${esc(browse.q)}" aria-label="在词库中搜索"></div>
      <div class="toolbar-end">
        <span class="field"><label class="field-label" for="bstatus">状态</label><select id="bstatus" aria-label="学习状态">
          <option value="" data-fcnt="status|" data-flabel="全部状态">全部状态（${statusCnt('')}）</option>
          ${STATUS_ORDER.map(k => `<option value="${k}" ${browse.status === k ? 'selected' : ''} data-fcnt="status|${k}" data-flabel="${STATUS_LABEL[k]}">${STATUS_LABEL[k]}（${statusCnt(k)}）</option>`).join('')}
        </select></span>
        <span class="field"><label class="field-label" for="bper">每页</label><select id="bper" aria-label="每页条数">${[25, 50, 100, 200].map(n => `<option value="${n}" ${browse.per === n ? 'selected' : ''}>${n} 条</option>`).join('')}</select></span>
        <div class="btn-group" id="viewToggle" role="group" aria-label="视图切换">
          <button data-v="table" class="${curView === 'table' ? 'on' : ''}" title="表格视图" aria-label="表格视图">${svgFor('list')}</button>
          <button data-v="cards" class="${curView === 'cards' ? 'on' : ''}" title="卡片视图" aria-label="卡片视图">${svgFor('grid')}</button>
          <button data-v="group" class="${curView === 'group' ? 'on' : ''}" title="按词性分组" aria-label="按词性分组">${svgFor('folder')}</button>
        </div>
        <button class="btn sm" id="btnRandom" title="随机打开一个词条" aria-label="随机词条">${svgFor('dice')}</button>
      </div>
    </div>
    <div class="filter-bar">
      <button class="btn sm filter-toggle" id="btnFilterToggle" aria-expanded="${filtersOpen}" aria-controls="filterWrap">
        ${svgFor('filter')} 筛选${activeFilterCount ? ` <span class="ft-count">${activeFilterCount}</span>` : ''}
      </button>
      ${activeFilterText ? `<span class="filter-summary">${activeFilterText}</span>` : ''}
    </div>
    <div class="filters-wrap${filtersOpen ? '' : ' collapsed'}" id="filterWrap">
      <div class="filter-panel">
        <div class="filter-panel-head">
          <span class="filter-panel-title">筛选</span>
          ${activeFilterCount ? `<button class="btn sm ghost" id="btnResetFilters">清空筛选</button>` : ''}
        </div>
        <div class="filter-row">
          <span class="filter-label">词性</span>
          <div class="filter-body" id="posFilter">${posList.map(p => posChip(p === '全部' ? '' : p, p)).join('')}${otherN ? posChip(POS_OTHER, POS_OTHER_LABEL, '单词介词与介词性固定短语共 ' + otherN + ' 词：它们的词性是介词，本库词性索引只设形容词/副词/动词/名词/连词五类，故这一档不设实义词性标签') : ''}</div>
        </div>
        <div class="filter-row">
          <span class="filter-label">是否核心</span>
          <div class="filter-body" id="coreFilter">
            <button class="chip ${!browse.core ? 'on' : ''}" data-core="">不限 <span class="cnt" data-fcnt="core|">${coreCnt('')}</span></button>
            <button class="chip ${browse.core === 'yes' ? 'on' : ''}" data-core="yes" title="核心高频词，共 ${coreN} 词">是 <span class="cnt" data-fcnt="core|yes">${coreCnt('yes')}</span></button>
            <button class="chip ${browse.core === 'no' ? 'on' : ''}" data-core="no" title="非核心词，共 ${nonCoreN} 词">否 <span class="cnt" data-fcnt="core|no">${coreCnt('no')}</span></button>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">感情色彩</span>
          <div class="filter-body" id="subFilter">${subChip('', '不限', '不限：当前筛选下不限感情色彩')}
          ${SUB_ORDER.map(s => subChip(s, s, `${s} · ${subCnt(s) ? '当前筛选下带这一色彩评价的词' : '当前筛选下没有带这一色彩评价的词（副词/连词/介词不带评价义）'}`)).join('')}
          ${subChip(SUB_OTHER, '其他', `其他 · 本库给 ${SUB_LABELED_N} 个形容词/名词/动词标注了感情色彩，其余 ${WORDS_MAX - SUB_LABELED_N} 词（副词、连词与介词）不带评价义 —— 选它筛出当前筛选下没有感情色彩标签的词（当前筛选下 ${subOtherN} 词）`)}</div>
        </div>
        <div class="filter-row">
          <span class="filter-label">语体色彩</span>
          <div class="filter-body" id="regFilter"><button class="chip ${!browse.reg ? 'on' : ''}" data-reg="">不限 <span class="cnt" data-fcnt="reg|">${regCnt('')}</span></button>${REG_ORDER.map(r => `<button class="chip ${browse.reg === r ? 'on' : ''}" data-reg="${r}" title="${r} · ${r === '学术术语' ? '某学科或专业领域的专门技术词（术语）' : r === '书面语' ? '带正式书面语域印记：正式连接词、文雅词与固定用语' : r === '口语' ? '带口语色彩（学术写作里少用）' : '无明显语域印记（通用词）'}">${r} <span class="cnt" data-fcnt="reg|${r}">${regCnt(r)}</span></button>`).join('')}</div>
        </div>
        <div class="filter-row">
          <span class="filter-label">首字母</span>
          <div class="filter-body"><div class="letter-bar" id="letterBar"><button class="letter-btn ${browse.letter ? '' : 'on'}" data-l="">全部<small data-fcnt="letter|">${letterCnt('')}</small></button>${letters}</div></div>
        </div>
      </div>
    </div>
    <div id="browseTable" data-pager="browsePager">${renderBrowseBody('browse', curView)}</div>`;
  /* 搜索词与状态改动只重画表格，筛选面板不动 —— 所以要顺手把面板上的计数刷新一遍，
     否则面板显示的数字与实际结果对不上。筛选外壳（摘要 / 徽标 / 清空按钮）
     也在这条路上同步：它们跟筛选状态走，跟「是整页重绘还是局部刷新」无关。 */
  const refresh = () => {
    $('#browseTable').innerHTML = renderBrowseBody('browse', curView);
    bindBrowseTable($('#browseTable'));
    refreshFacetCounts();
    syncFilterChrome();
  };
  $('#bq').oninput = debounce(e => { browse.q = e.target.value; pageSet(1); refresh(); }, 200);
  $('#bstatus').onchange = e => { browse.status = e.target.value; pageSet(1); refresh(); };
  $('#bper').onchange = e => { browse.per = +e.target.value; pageSet(1); refresh(); };
  $$('#viewToggle button').forEach(b => b.onclick = () => { browse.view = b.dataset.v; browse.page = 1; renderView('browse'); });
  $('#btnRandom').onclick = () => openWordModal(rnd(WORDS).num);
  $('#btnFilterToggle').onclick = () => { browse.filtersOpen = !filtersOpen; renderView('browse'); };
  $$('#posFilter .chip').forEach(c => c.onclick = () => {
    browse.pos = c.dataset.pos;
    // 换词性后，若当前那一档感情色彩在新词性下**够不着词**，就把它撤掉 ——
    // 否则「副词 + 积极的」恒为空，用户只会看到列表莫名清空。
    // 够不着的两种情形：副词/连词/介词没有「积极的」这类评价色彩（恒 0）；
    // 三类实词没有「其他」（未标注）（实词都带标签）。
    // 「全部」不限词性，感情色彩照常生效，故不清；
    // 「副词 + 其他」够得着（副词全不带标签），故留着。
    if (!subReachable(browse.pos, browse.sub)) browse.sub = '';
    browse.page = 1; browse.filtersOpen = true; renderView('browse');
  });
  $$('#coreFilter .chip').forEach(c => c.onclick = () => {
    // 是否核心与词性、感情色彩、语体色彩都正交：只改自己这一层，不动别的条件。
    browse.core = c.dataset.core;
    browse.page = 1; browse.filtersOpen = true; renderView('browse');
  });
  $$('#subFilter .chip').forEach(c => c.onclick = () => {
    const v = c.dataset.sub;
    // 换感情色彩后，若当前词性下够不着这一档（如 词性=形容词 + 感情色彩=其他：
    // 实词都带评价色彩标签，没有未标注的），就把词性撤掉 ——
    // 与「点词性 chip 时撤掉够不着的感情色彩」同一口径，
    // 否则用户撞上一张空表，却看不出是哪两个条件在打架。
    if (browse.pos && !subReachable(browse.pos, v)) browse.pos = '';
    browse.sub = v;
    browse.page = 1; browse.filtersOpen = true; renderView('browse');
  });
  $$('#regFilter .chip').forEach(c => c.onclick = () => { browse.reg = c.dataset.reg; browse.page = 1; browse.filtersOpen = true; renderView('browse'); });
  $$('#letterBar .letter-btn').forEach(b => b.onclick = () => { browse.letter = b.dataset.l; browse.page = 1; browse.filtersOpen = true; renderView('browse'); });
  const rf = $('#btnResetFilters');
  if (rf) rf.onclick = resetBrowseFilters;
  bindBrowseTable($('#browseTable'));
};
/* 清空全部筛选（面板头的「清空筛选」与零结果时的「清除筛选」共用）：
   一次清空并重画整页，保证工具栏、面板里的按钮状态同步。 */
function resetBrowseFilters() {
  browse.q = ''; browse.favQ = ''; browse.letter = ''; browse.pos = ''; browse.core = ''; browse.sub = ''; browse.reg = ''; browse.status = '';
  browse.page = 1; browse.favPage = 1;
  renderView(current);
}

/* ---------- 收藏（复用词库表格） ---------- */
views.fav = (root, prev) => {
  browse.onlyFav = true;
  // 收藏页面没有状态 / 首字母 / 词性筛选控件，若沿用词库页残留的筛选条件，
  // 用户会看到「已收藏 5 词」却只列出 0 词；进入本页时统一清掉。
  // 但同页重渲染（翻收藏、切视图）必须保留页码——否则在第 3 页点一下收藏
  // 就被无声拽回第 1 页，而滚动位置还停在原来的深度。
  if (prev !== 'fav') { browse.status = ''; browse.letter = ''; browse.pos = ''; browse.core = ''; browse.sub = ''; browse.reg = ''; browse.favQ = ''; browse.favPage = 1; }
  root.innerHTML = `
    <h1 class="page-title">${svgFor('star-f')} 收藏 <span class="faint">已收藏 ${favWords().length} 词</span></h1>
    <div class="page-sub">浏览词库时点 ☆ 即可收藏；可针对收藏直接开学习或测验</div>
    <div class="toolbar">
      <div class="search-wrap"><input type="search" id="favBq" placeholder="在收藏内搜索…" value="${esc(browse.favQ)}" aria-label="在收藏内搜索"></div>
      <div class="toolbar-end">
        <div class="btn-group" id="favViewToggle" role="group" aria-label="视图切换">
          <button data-v="table" class="${browse.favView === 'table' ? 'on' : ''}" title="表格视图">${svgFor('list')}</button>
          <button data-v="cards" class="${browse.favView === 'cards' ? 'on' : ''}" title="卡片视图">${svgFor('grid')}</button>
        </div>
        <button class="btn primary sm" id="favCards">${svgFor('cards')} 收藏学习</button>
        <button class="btn sm" id="favQuiz">${svgFor('pen')} 收藏测验</button>
        ${favWords().length ? `<button class="btn sm ghost" id="favExport" title="把当前列表导出为文本文件">${svgFor('down')} 导出文本</button>` : ''}
      </div>
    </div>
    <div id="favTable" data-pager="favPager">${favWords().length ? renderBrowseBody('fav') :
      `<div class="card empty-state"><div class="es">${svgFor('star')}</div>收藏还是空的<br><span class="faint">去词库点 ☆ 收藏生词吧</span><div class="mt16"><a class="btn primary sm" href="#browse">浏览词库</a></div></div>`}</div>`;
  bindBrowseTable($('#favTable'));
  const refresh = () => { $('#favTable').innerHTML = renderBrowseBody('fav'); bindBrowseTable($('#favTable')); };
  $('#favBq') && ($('#favBq').oninput = debounce(e => { browse.favQ = e.target.value; browse.favPage = 1; refresh(); }, 200));
  $$('#favViewToggle button').forEach(b => b.onclick = () => { browse.favView = b.dataset.v; browse.favPage = 1; renderView('fav'); });
  $('#favCards').onclick = () => { pendingDeck = { src: 'fav' }; if (location.hash === '#study') renderView('study'); else location.hash = '#study'; };
  $('#favQuiz').onclick = () => { studyTab = 'quiz'; pendingScope = 'fav'; if (location.hash === '#study') renderView('study'); else location.hash = '#study'; };
  const ex = $('#favExport');
  if (ex) ex.onclick = () => {
    // 导出范围=当前筛选结果（搜了再导是常见用法）；制表符分隔，记事本/表格软件都能打开
    const rows = browseRows();
    if (!rows.length) { toast('当前筛选没有词可导出'); return; }
    const txt = rows.map(w => {
      const p = prog(w.num);
      const st = !p ? '未学' : p.lv >= 5 ? '已掌握' : LV_LABEL[p.lv] + '·L' + p.lv;
      return `${w.word}\t${w.senses.join('；')}\t${st}`;
    }).join('\n');
    const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'wl-fav-' + todayStr() + '.txt';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast('已导出 ' + rows.length + ' 词', 1800, 'down');
  };
};

/* ---------- 学习 ---------- */
let pendingDeck = null;
const fc = { queue: [], i: 0, flipped: false, session: 0, total: 0, src: 'due', custom: null, lastLimit: Math.max(5, Math.min(WORDS_MAX, +state.settings.fcLimit || 30)), undo: [], stats: null, requeue: 0, autoSpoke: 0, examplesOpen: false };
let fcNotice = null;   // 选到空范围时的内联提示（比一闪而过的 toast 更容易理解）
/* 只做筛选不打乱：设置页统计各牌组大小时用，避免每渲染一次就把全库洗一遍 */
function deckList(src) {
  let list;
  switch (src) {
    case 'due': list = dueQueue(); break;
    case 'all': list = WORDS.slice(); break;
    case 'new': list = WORDS.filter(w => !isStarted(w.num)); break;
    case 'learning': list = WORDS.filter(w => isStarted(w.num) && !isMastered(w.num)); break;
    case 'mastered': list = WORDS.filter(w => isMastered(w.num)); break;
    case 'fav': list = favWords(); break;
    case 'picked': list = WORDS.filter(w => w.core); break;
    case 'adj': list = WORDS.filter(w => w.pos === '形容词'); break;
    case 'custom': list = (fc.custom || []).slice(); break;
    /* 感情色彩牌组（第七十轮起跨了名词与动词，不再只是形容词）：
       sub+ / sub- / sub? / sub0 四档取全库同档的词。 */
    case 'sub+': list = WORDS.filter(w => w.sub === '积极的'); break;
    case 'sub-': list = WORDS.filter(w => w.sub === '消极的'); break;
    case 'sub?': list = WORDS.filter(w => w.sub === '争议性的'); break;
    case 'sub0': list = WORDS.filter(w => w.sub === '中性的'); break;
    case 'adv': list = WORDS.filter(w => w.pos === '副词'); break;
    case 'verb': list = WORDS.filter(w => w.pos === '动词'); break;
    case 'noun': list = WORDS.filter(w => w.pos === '名词'); break;
    case 'conj': list = WORDS.filter(w => w.pos === '连词'); break;
    case 'other': list = OTHER_WORDS(); break;
    default: list = dueQueue();
  }
  return list;
}
/* 洗牌后的牌队列：真正开卡时才打乱顺序 */
function buildDeck(src) { return shuffle(deckList(src)); }
/* 入口按钮的词数口径：一次会话最多开「每次上限」张卡（fc.lastLimit，
   牌组在 buildDeck(src).slice(0, fc.lastLimit || 30) 处被截断）。
   池子比上限大时，光写「学习这 2222 个词」是在承诺一件本次学不完的事：
   点进去只有 30 张卡，页面上没有任何地方说明其余的去哪儿了（上限只在学习页的设置里露一眼）。
   但把池子数藏起来也不行——本库的口径是「说清池子有多大」（范围卡一直这么做）。
   于是两个数都写：池子数照旧（exactText），另加「（本次 N 张）」披露本次真正开出的卡数。
   池子 ≤ 上限时本次就是整个池子，不必再加一句。 */
function sessionLimit() { return fc.lastLimit || 30; }
/* overText 可省：默认把「（本次 N 张）」接在原文后面；
   原文自带括号（如「从新词开始（2222）」）时由调用方给一个整句版本，避免两层括号。 */
function sessionLabel(pool, exactText, overText) {
  const cap = sessionLimit();
  if (pool <= cap) return exactText;
  return overText || `${exactText}（本次 ${cap} 张）`;
}
/* 牌组名（**不带词数**）：进度条与完成页用它。
   此前这里把词数也写进了名字（「形容词 410 词」「核心高频 875 词」），
   而范围选择页的卡片副行又单独写了一遍词数 —— 同一个数字在同一张卡上出现两次；
   名字还会随词库增补而变（卡片标题长度跟着漂）。
   现在名字只说「这是什么范围」，数字一律由 deckList(src).length 现算。 */
const DECK_INFO = {
  due: '复习队列', all: '全部词库', new: '未学习新词', learning: '学习中',
  mastered: '已掌握', fav: '收藏', picked: '核心词', custom: '筛选结果',
  adj: '形容词', 'sub+': '积极的 · 褒义', 'sub-': '消极的 · 贬义', 'sub?': '争议性的 · 两极', 'sub0': '中性的 · 无评价',
  adv: '副词', verb: '动词', noun: '名词', conj: '连词',
  other: '介词',
};
/* 评分后这个词多久会再次出现（SRS 预览） */
function nextIntervalDays(num, q) {
  const p = prog(num) || { lv: 0 };
  if (q === 2) { const lv = Math.min(5, p.lv + 1); return lv >= 5 ? 120 : INTERVALS[lv]; }
  if (q === 1) { const lv = Math.min(p.lv, 4); return Math.max(0.35, INTERVALS[Math.max(0, lv - 1)] * .55); }   // 与 grade 同步：L5 评模糊先降 L4
  return 0;
}
function gradeHint(num, q) {
  if (q === 0) return '今天再来一次';
  return fmtDur(nextIntervalDays(num, q));
}
/* 学习页页首的「今日进度」条：一行说清今天学了多少、目标多少、还差多少。
   学习页此前只有「选范围 → 开始」，用户进来不知道自己今天处于什么位置；
   首页有目标环形进度，但学习页才是真正动手的地方，这里给一条同样的口径。
   口径与首页同源（todayActivity / state.settings.goal），不另立一套数。 */
function todayStrip() {
  const goal = state.settings.goal, act = todayActivity();
  const pct = Math.min(100, Math.round(act / goal * 100));
  const done = act >= goal;
  const st = streak();
  return `
    <div class="study-today">
      <span class="st-ic">${svgFor('target')}</span>
      <span class="st-label">今日目标</span>
      <span class="st-num"><b>${act}</b> / ${goal} 次</span>
      <span class="st-bar" role="progressbar" aria-label="今日目标进度" aria-valuemin="0"
            aria-valuemax="${goal}" aria-valuenow="${Math.min(act, goal)}"
            aria-valuetext="已完成 ${act} 次，目标 ${goal} 次"><span style="width:${pct}%"></span></span>
      <span class="st-note">${done ? '今日目标已完成，随时可以停' : `还差 ${goal - act} 次`}</span>
      ${st ? `<span class="st-streak">${svgFor('flame')} 连续 ${st} 天</span>` : ''}
    </div>`;
}

/* 学习页与测验页合并为一页（一百四十九轮）：顶栏只留「学习」一个入口，
   翻卡学习与测验两套功能都在 #study 一页里，页首的「翻卡学习 / 测验」分段控件切换。
   两套设置面板的口径与交互原样搬入、不换行为：推荐条、范围/词性/每次上限、
   题型/范围/题数/本次、答题中/牌桌中误点导航再回来续上、退出提示，全都保持。 */
let studyTab = 'flashcards';   // 页内模式：'flashcards' 翻卡学习 / 'quiz' 测验。
                               // 内存态（与 fc/quiz 会话同生命周期）：不进存档，
                               // 刷新后回默认的翻卡模式——原 #quiz 刷新后同样回设置页。
views.study = (root) => {
  // 从首页 / 词库 / 收藏直接开学习：同样要遵守「每次上限」，否则会一次来上千张
  if (pendingDeck) { fc.src = pendingDeck.src; pendingDeck = null; fc.queue = buildDeck(fc.src).slice(0, fc.lastLimit || 30); startSession(); return; }
  // 显式指定新范围（收藏测验等）＝切到测验模式并开新场；否则答题中误点导航
  // 再回来要能续上（quiz.session 保持，直接重放当前题），与翻卡会话行为一致
  if (pendingScope) {
    studyTab = 'quiz';
    quiz.scope = pendingScope; pendingScope = null; quiz.session = 0;
    /* 换范围后必须把上一条提示作废：quizNotice（「××只有 2 个词，至少需要 4 个」）
       只在点范围/题型/题量 chip 与真正开考时清空。收藏测验这条路径
       （pendingScope）不清 → 收藏加了词、范围里已经有 7 个词了，
       提示却还写着「只有 2 个词」（实测）。 */
    quizNotice = null;
  }
  /* 会话续接按**当前模式**分流（合并页上 fc.session 与 quiz.session 是两套独立内存态，
     都可能非零——旧 hash #quiz / #cards 重定向、或答题中途切模式都会造成交叉）：
     翻卡模式续翻卡牌桌，测验模式续答题页。另一套会话原样挂着不清——
     用户切回去（点分段控件 / 顶栏）还能从原处继续，与合并前误点导航再回来的行为一致。
     侧效应：切走前未结束的会话在完成面板/成绩页之前就离开的，回来仍是答题中。 */
  if (studyTab === 'flashcards' && fc.session) { renderStage(); return; }
  clearTimeout(quizReplayT);   // 回到设置页时，别把最后一题的发音留到设置页里
  if (studyTab === 'quiz' && quiz.session && quiz.queue[quiz.i]) { renderQuizQuestion(); return; }
  if (studyTab === 'quiz') quiz.session = 0;   // 测验模式下无效会话才清零；翻卡模式不动 quiz 态
  const isQuiz = studyTab === 'quiz';
  /* 推荐牌组的口径在**函数作用域**声明（不藏在下面的 if 块里）：
     翻卡设置面板的渲染与事件绑定分两段走，两段都要读 best/bestN。
     推荐不再有自己的横条与按钮（二百轮：推荐条整条下线）——它的落点是
     「初始选中」：进页时选中的 chip 就是按这个口径拨好的（fc.src 为空时对齐）。 */
  const tcStudy = tierCounts();
  const best = tcStudy.due > 0 ? 'due' : tcStudy.new > 0 ? 'new' : tcStudy.learning > 0 ? 'learning'
             : tcStudy.mastered > 0 ? 'mastered' : 'all';
  const bestN = deckList(best).length;
  /* 模式卡：把两个模式各自的「当前参数」直接写在卡上 —— 此前页首只有两颗
     小分段按钮，用户不知道翻卡与测验分别会做什么、要花多少量。
     两张卡各带图标、名字、一句说明与当前参数（本次 N 张 / N 题 · 某范围），
     切模式之前就能比较，不必来回试。 */
  const qScopeName = (QUIZ_SCOPES[quiz.scope] || [])[1] || '全部词库';
  const qPoolN = quizPool(quiz.scope).length;
  const qModeName = quiz.mode === 'mix' ? '混合题型' : (MODES[quiz.mode] || { name: '混合题型' }).name;
  const modeCard = (m, ic, t, d, s, on) => `
    <button type="button" data-m="${m}" class="mode-card${on ? ' on' : ''}" aria-pressed="${on}">
      <span class="mc-ic">${svgFor(ic)}</span>${esc(t)}
      <span class="mc-d">${esc(d)}</span>
      <span class="mc-s" id="mc-${m}">${esc(s)}</span>
    </button>`;
  let panel = '';
  if (!isQuiz) {
    const tc = tcStudy;
    const due = tc.due, nNew = tc.new, nLearning = tc.learning, nMastered = tc.mastered, nFav = tc.fav;
    /* 两步流的初始选中：跟上推荐口径（到期 > 新词 > …）。fc.src 是跨会话的记忆值
       （上一次开的是哪个范围），但那个范围若是空的（比如收藏被清空、上次开的
       「复习队列」今天没有到期词），chip 高亮会停在一个 0 词的档上，
       「开始学习」按下去却是空场。仅在 fc.src 为空时对齐一次：拨到 best ——
       推荐的语义就落在这颗预选中的 chip 上（二百轮起推荐没有自己的横条了）。
       有词的选择（上次开了「形容词」且形容词还有词）原样保留，不覆盖用户意图。 */
    if (bestN && deckList(fc.src).length === 0) fc.src = best;
    /* 牌组选项：chip 形态（图标 + 名字 + 词数一行），**点一下只是选中**，
       真正开卡要走到面板底的「本次」行按「开始学习」确认（与测验面板的
       「选范围 → 开始测验」同一套两步流）。
       此前点 chip 立即开局：用户只想看看有哪些范围，误点一颗就把牌桌开了；
       且「每次上限」在下一行，改上限必须发生在开卡之前 —— 两步流让
       「先选范围、再定上限、最后确认」成为一条自然的顺序。
       选中态写 fc.src（开卡后它就是会话的范围，进度条也用它）；
       fc.src 有默认值 'due'，新用户进来「复习队列」即处于选中态 ——
       这与页首推荐的口径一致（到期 > 新词 > …），不是凭空高亮。
       名字与词数仍分两个 span（do-t / do-n），aria-label 给出完整读法
       （名字＋词数＋说明），读屏用户听到的仍是一句完整的话。
       空牌组写「0 词」并把**为什么是空的**（「暂无到期」「还没收藏」）放进
       title/aria-label：chip 内的数字与有词的牌组对齐（一眼能比大小），
       空的原因交给悬停与读屏 —— 空牌组本就虚线弱化，不必再占一行说明。
       选中与否也进 aria-pressed：读屏用户按 chip 时能听到「已按下」。 */
    const deck = (s, icon, label, n, note) =>
      `<button class="chip deck-opt${n ? '' : ' empty'}${fc.src === s ? ' on' : ''}" data-s="${s}" data-label="${esc(label)}"
         ${note ? `title="${esc(note)}"` : ''}
         aria-pressed="${fc.src === s ? 'true' : 'false'}"
         aria-label="${esc(label + ' ' + n + ' 词' + (note ? ' · ' + note : ''))}">
         <span class="do-t">${svgFor(icon)} ${esc(label)}</span>
         <span class="do-n">${n} 词</span>
       </button>`;
    /* 词性分两层：**词性**（形容词 / 副词 / 动词 / 名词 / 连词 / 介词）与
       **形容词的感情色彩**（积极 / 消极 / 中性）。
       此前九个词性 chip 并列，「形容词 438 词」与「形容词·积极 50 / 消极 35 /
       中性 353」摆在一起 —— 后三者是前者的**拆分**（50+35+353＝438），
       并列读起来像四组互不相干的范围，用户会以为「学形容词」之外还能再学
       三遍形容词。拆成子行并写明「三者合计＝形容词总数」，口径不再打架。 */
    const POS_DECKS = [['adj', 'tag'], ['adv', 'rocket'], ['verb', 'zap'], ['noun', 'grid'],
                       ['conj', 'link'], ['other', 'layers']];
    const SENT_DECKS = [['sub+', 'smile'], ['sub-', 'frown'], ['sub?', 'scale'], ['sub0', 'palette']];
    panel = `
      ${fcNotice ? `<div class="empty-inline" style="margin-bottom:14px">${svgFor('info')} ${esc(fcNotice)}</div>` : ''}

      <div class="deck-setup filter-panel">
        <div class="filter-panel-head">
          <span class="filter-panel-title">复习范围</span>
          <span class="faint">词库共 ${WORDS_MAX} 词 · 核心高频 ${CORE_MAX} 词</span>
        </div>
        <div class="filter-row">
          <span class="filter-label">范围</span>
          <div class="filter-body"><div class="deck-grid">
            ${deck('due', 'alarm', '复习队列', due, due ? '已到期' : '暂无到期')}
            ${deck('new', 'seed', '未学习新词', nNew, nNew ? '' : '全部已学')}
            ${deck('learning', 'trend', '学习中', nLearning, nLearning ? '' : '暂无在学')}
            ${deck('mastered', 'trophy', '已掌握', nMastered, nMastered ? '' : '还没掌握')}
            ${deck('fav', 'star-f', '收藏', nFav, nFav ? '' : '还没收藏')}
            ${deck('picked', 'tag', '核心词', CORE_MAX)}
            ${deck('all', 'list', '全部词库', WORDS_MAX)}
            ${fc.custom && fc.custom.length ? deck('custom', 'filter', '上次筛选结果', fc.custom.length) : ''}
          </div></div>
        </div>
        <div class="filter-row">
          <span class="filter-label">词性</span>
          <div class="filter-body">
            <div class="deck-grid pos">
              ${POS_DECKS.map(([s, ic]) => deck(s, ic, DECK_INFO[s], deckList(s).length)).join('')}
            </div>
            <div class="deck-sub">
              <span class="deck-sub-cap">感情色彩 · 积极 / 消极 / 争议 / 中性 · 四者合计 ${deckList('sub+').length + deckList('sub-').length + deckList('sub?').length + deckList('sub0').length} 词（跨形容词、名词与动词）</span>
              <div class="deck-grid sub">
                ${SENT_DECKS.map(([s, ic]) => deck(s, ic, DECK_INFO[s], deckList(s).length)).join('')}
              </div>
            </div>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">每次上限</span>
          <div class="filter-body">
            <span class="limit-presets" role="group" aria-label="常用张数">
              ${[10, 20, 30, 50].map(n => `<button type="button" class="chip limit-preset${fc.lastLimit === n ? ' on' : ''}" data-lim="${n}" aria-label="每次上限 ${n} 张">${n}</button>`).join('')}
            </span>
            <span class="field">
              <label class="field-label" for="fcLimit">或自定义</label>
              <input type="number" id="fcLimit" min="5" max="${WORDS_MAX}" value="${fc.lastLimit}" style="width:82px" aria-label="每次上限（张）">
            </span>
            <span class="faint" id="fcLimitHint"></span>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">本次</span>
          <div class="filter-body">
            <span class="q-summary" id="fcSummary"></span>
            <button class="btn primary big" id="fcStart">${svgFor('rocket')} 开始学习</button>
          </div>
        </div>
      </div>`;
  } else {
    const tc = tierCounts();
    /* 出题池与范围计数同源（deckList）：范围标签上的数字就是实际能出题的词数，
       实际题数 = 设置题数与池子大小的较小值 —— 此前两者各说各的，
       范围里只有 7 个词时照样显示「50 题」，点下去才发 7 题。 */
    const pool = quizPool(quiz.scope);
    const poolN = pool.length;
    const effN = Math.min(quiz.count, poolN);
    const scopeName = (QUIZ_SCOPES[quiz.scope] || [])[1] || '全部词库';
    const modeName = quiz.mode === 'mix' ? '混合题型' : (MODES[quiz.mode] || { name: '混合题型' }).name;
    /* 本次到底出什么：范围不够 4 词就说清楚为什么不够，别让用户点「开始」才撞墙 */
    const summary = poolN < 4
      ? (poolN ? `「${scopeName}」只有 ${poolN} 个词，不够出题（至少要 4 个）` : `「${scopeName}」现在还没有单词`)
      : `${modeName} · ${scopeName} · ${effN} 题${effN < quiz.count ? `（该范围只有 ${poolN} 个词）` : ''}`;
    panel = `
      ${quizNotice ? `<div class="empty-inline" style="margin-bottom:14px">${svgFor('info')} ${esc(quizNotice)}</div>` : ''}
      <div class="quiz-setup filter-panel">
        <div class="filter-panel-head">
          <span class="filter-panel-title">出题设置</span>
          <span class="faint">四选一至少要 4 个词</span>
        </div>
        <div class="filter-row">
          <span class="filter-label">题型</span>
          <div class="filter-body" id="qModes">
            ${Object.entries(MODES).map(([k, m]) => `<button class="chip ${quiz.mode === k ? 'on' : ''}" data-m="${k}"${!canSpeakEnglish() && k === 'listen' ? ' disabled title="需要浏览器提供英语语音合成"' : ''}>${svgFor(m.icon)} ${m.name}</button>`).join('')}
            <button class="chip ${quiz.mode === 'mix' ? 'on' : ''}" data-m="mix">${svgFor('shuffle')} 混合</button>
          </div>
        </div>
        ${ttsStatus() !== 'ready' ? `<div class="empty-inline" style="margin:0 0 4px">${svgFor('info')} ${ttsStatus() === 'unsupported' ? '当前浏览器不支持语音合成' : '未检测到英语语音包（只有其他语言的音色不能代替英语发音）'}，「听音辨词」无法出题；其他题型不受影响。可在系统语音设置中安装英语语音后刷新页面。</div>` : ''}
        <div class="filter-row">
          <span class="filter-label">范围</span>
          <div class="filter-body" id="qScopes">
            ${Object.entries(QUIZ_SCOPES).map(([k, [icon, label]]) => { const n = quizScopeCount(k, tc);
              const few = n < 4;
              /* 图标与名字包进 .q-t：宽屏上 chip 排成等宽栅格后，词数要靠右对齐成列，
                 若图标与名字仍是散着的两个 flex 子项，space-between 会把图标推到最左、
                 名字留在中间，图标与名字分了家。 */
              return `<button class="chip ${quiz.scope === k ? 'on' : ''}${few ? ' thin' : ''}" data-sc="${k}"${few ? ` title="该范围只有 ${n} 个词，出题至少要 4 个"` : ''}><span class="q-t">${svgFor(icon)} ${label}</span><span class="cnt">${n}</span></button>`; }).join('')}
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">题数</span>
          <div class="filter-body" id="qCounts">
            ${[10, 20, 30, 50].map(n => { const over = n > poolN;
              return `<button class="chip ${quiz.count === n ? 'on' : ''}${over ? ' thin' : ''}" data-c="${n}"${over ? ` aria-disabled="true" title="该范围只有 ${poolN} 个词，最多出 ${poolN} 题"` : ''}>${n} 题</button>`; }).join('')}
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">本次</span>
          <div class="filter-body">
            <span class="q-summary" id="qSummary">${esc(summary)}</span>
            <button class="btn primary big" id="startQuiz">${svgFor('rocket')} 开始测验</button>
          </div>
        </div>
      </div>
      <p class="faint center mt12">答题快捷键：<span class="kbd">1</span>–<span class="kbd">4</span> 或 <span class="kbd">A</span>–<span class="kbd">D</span> 选择 · <span class="kbd">空格</span> 下一题</p>`;
  }
  root.innerHTML = `
    <div class="study-page">
      <h1 class="page-title">${svgFor('cards')} 学习</h1>
      <div class="page-sub">${isQuiz
        ? '五种题型随机出题，答题结果会同步更新记忆等级。'
        : '间隔重复（莱特纳盒子）：认识升级、模糊保持、忘了降级；翻面后评分，系统自动安排下次复习。'}</div>
      ${todayStrip()}
      <div class="seg study-modes" id="studyModeSeg" role="group" aria-label="学习模式">
        ${modeCard('flashcards', 'cards', '学习', '间隔重复 · 翻面后评分',
          deckList(fc.src).length ? `本次 ${Math.min(deckList(fc.src).length, fc.lastLimit)} 张` : '暂无可学', !isQuiz)}
        ${modeCard('quiz', 'pen', '测验', `${qModeName} · ${qScopeName}`,
          qPoolN < 4 ? '题量不足' : `${Math.min(quiz.count, qPoolN)} 题`, isQuiz)}
      </div>
      ${panel}
    </div>`;
  /* 模式切换：同页换面板。切走时把另一模式留下的过期提示一并清掉
     （翻卡的范围提示不该出现在测验面板上，反之亦然）。 */
  $$('#studyModeSeg button').forEach(b => b.onclick = () => {
    if (studyTab === b.dataset.m) return;
    studyTab = b.dataset.m;
    fcNotice = null; quizNotice = null;
    renderView('study');
  });
  if (!isQuiz) {
    /* 上限在所有入口都要算数（「本次」确认按钮 / 模式卡预览），限值一律现读输入框：
       用户改了上限直接点卡片时，change 事件先于 click 触发，这里再读一次最保险。 */
    /* 数字归一口径与设置页 numInput 相同：空/非数字落 30，0 之类的合法数走钳制
       （`+v || 30` 曾把输入 0 顶成 30，与 -5 → 5 两种落点打架，二百零一轮统一） */
    const limNow = () => {
      const v = String(($('#fcLimit') || {}).value ?? '').trim();
      const n = (v === '' || !Number.isFinite(+v)) ? 30 : +v;
      return Math.max(5, Math.min(WORDS_MAX, n));
    };
    const syncLimit = () => {
      const lim = limNow();
      const hint = $('#fcLimitHint');
      if (hint) hint.textContent = `一次最多取 ${lim} 张，范围不足时按实际张数出卡`;
      /* 模式卡上的「本次 N 张」也跟着走：上限改了，卡上的数字不能还是旧的。
         数字取**实际张数**（当前选中范围与上限的较小者）——本页只有「本次」行
         那一颗「开始学习」，它开的就是 fc.src 这个范围，模式卡上的预览与它同源
         （此前卡上写上限（30 张）、按钮写实际（3 张），同屏两个数打架）。 */
      const mc = $('#mc-flashcards');
      if (mc) {
        const n = deckList(fc.src).length;
        mc.textContent = n ? `本次 ${Math.min(n, lim)} 张` : '暂无可学';
      }
      /* 预设档位与输入框互为镜像：手输了 30 就点亮「30」那颗，
         手输了 25（不匹配任何档位）则全部熄灭 —— 两处数字不能各说各的。 */
      $$('.limit-preset').forEach(c => c.classList.toggle('on', +c.dataset.lim === lim));
    };
    /* 「本次」行的摘要文案：与测验面板的 q-summary 同一口径 ——
       写清「学哪个范围 · 实际会开几张」。实际张数 = 范围词数与上限的较小值；
       范围为 0 词时直接说「现在还没有单词」，开始按钮一并禁用。 */
    const sumEl = () => $('#fcSummary');
    const startBtn = () => $('#fcStart');
    const syncSummary = () => {
      const src = fc.src;
      const label = DECK_INFO[src] || src;
      const n = deckList(src).length;
      const lim = limNow();
      const el = sumEl(), b = startBtn();
      if (!el) return;
      if (!n) {
        el.textContent = `「${label}」现在还没有单词，换一个范围试试`;
        if (b) b.disabled = true;
      } else {
        el.textContent = n > lim
          ? `「${label}」· 本次 ${lim} 张（该范围共 ${n} 词）`
          : `「${label}」· 本次 ${n} 张`;
        if (b) b.disabled = false;
      }
    };
    $('#fcLimit').onchange = e => {
      fc.lastLimit = limNow();
      state.settings.fcLimit = fc.lastLimit; save();
      e.target.value = fc.lastLimit;
      syncLimit();
      syncSummary();
    };
    $('#fcLimit').oninput = () => { syncLimit(); syncSummary(); };
    /* 预设档位：点一下就写入输入框并走同一条 onchange 路径（落存档 + 同步提示）。
       不走 oninput 是因为 oninput 只更新文案不落盘，而上限是要记住的设置。 */
    $$('.limit-preset').forEach(c => c.onclick = () => {
      const inp = $('#fcLimit');
      if (!inp) return;
      inp.value = c.dataset.lim;
      inp.onchange({ target: inp });
    });
    syncLimit();
    /* 开一个牌组：所有入口走同一条路（「本次」行唯一的「开始学习」确认按钮；
       词库 CTA、分组视图、收藏等经 pendingDeck 直开，不经这里的两步流） */
    const startDeck = (src, label) => {
      const limit = limNow();
      fc.src = src;
      fc.lastLimit = limit;
      state.settings.fcLimit = limit; save();   // 上限跟着走，下次从首页直接开卡也守得住
      fc.queue = buildDeck(src).slice(0, limit);
      if (!fc.queue.length) {
        // 空范围：给出常驻的内联说明与替代方案，而不是一闪而过的 toast
        fcNotice = `「${label}」当前没有可复习的单词。可以换成「未学习新词」或「全部词库」开始。`;
        renderView('study');
        return;
      }
      fcNotice = null;
      startSession();
    };
    /* 范围/词性 chip：点一下**只选中**——高亮、写 aria-pressed、更新「本次」摘要，
       不重渲染（重渲染会滚回顶部并打断 chip 上的焦点）。真正开卡走「开始学习」；
       点了空范围摘要会说明为什么开不了，确认按钮一并禁用。
       模式卡上的「本次 N 张」与摘要是同一条事实（同源口径，见 syncLimit），一并刷。 */
    $$('.chip[data-s]', root).forEach(c => c.onclick = () => {
      fc.src = c.dataset.s;
      $$('.chip[data-s]', root).forEach(x => {
        const on = x.dataset.s === fc.src;
        x.classList.toggle('on', on);
        x.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      syncLimit();
      syncSummary();
    });
    startBtn().onclick = () => startDeck(fc.src, DECK_INFO[fc.src] || fc.src);
    syncSummary();
  } else {
    $$('#qModes .chip').forEach(c => c.onclick = () => { quiz.mode = c.dataset.m; quizNotice = null; renderView('study'); });
    $$('#qScopes .chip').forEach(c => c.onclick = () => { quiz.scope = c.dataset.sc; quizNotice = null; renderView('study'); });
    $$('#qCounts .chip').forEach(c => c.onclick = () => {
      // 超出池容量的题数选不了（池里就那么多词，选了也只是白选一个做不到的数字）
      if (c.getAttribute('aria-disabled') === 'true') { toast('该范围词数不足，题数已按实际词数计算'); return; }
      quiz.count = +c.dataset.c; quizNotice = null; renderView('study');
    });
    $('#startQuiz').onclick = () => {
      // 开始测验要求至少 4 词（四选一出题的下限）；「再来一组」不设此门槛，见 quizResult
      const pool = quizPool(quiz.scope);
      if (pool.length < 4) {
        const nm = (QUIZ_SCOPES[quiz.scope] || [])[1] || '该范围';
        quizNotice = pool.length
          ? `「${nm}」只有 ${pool.length} 个词，至少需要 4 个才能出题。换个范围试试，比如「全部词库」或「未学习新词」。`
          : `「${nm}」现在还没有单词，先去学几个或收藏几个再来测验吧。`;
        renderView('study');
        return;
      }
      // 开成了新场就清掉「范围太小」的旧提示，回设置页时不再复述过期原因
      quizNotice = null;
      quiz.queue = pickN(pool, Math.min(quiz.count, pool.length));
      quiz.i = 0; quiz.score = 0; quiz.wrong = []; quiz.skipped = 0; quiz.session = 1; quiz.fb = null;
      renderQuizQuestion();
    };
  }
};
function startSession() {
  if (!fc.queue.length) fc.queue = buildDeck(fc.src).slice(0, fc.lastLimit || 30);
  if (!fc.queue.length) { fcNotice = '这个范围当前没有单词，先去「未学习新词」或「全部词库」看看吧。'; fc.session = 0; renderView('study'); return; }
  // 会话真开起来了：清掉上一次空范围留下的提示，否则将来退回设置页
  // 会看到「○○当前没有可复习的单词」这种已经过期的话（四十六轮）
  fcNotice = null;
  // 开卡动作本身就意味着切到翻卡模式：否则从测验模式经 pendingDeck 开卡
  // （词库分组视图「本类学习」、首页 CTA、收藏学习都可能是这条路径）时，
  // views.study 的会话续接按模式分流会把刚开的牌桌当作「翻卡会话在测验模式下不可见」
  // 而继续渲染测验面板——卡片开了却看不见（实测）。
  studyTab = 'flashcards';
  fc.i = 0; fc.flipped = false; fc.total = fc.queue.length; fc.session = 1; fc.requeue = 0; fc.autoSpoke = 0; fc.examplesOpen = false;
  fc.undo = []; fc.stats = { good: 0, mid: 0, bad: 0 };
  renderView('study');
}
/* 会话进行中（牌桌/答题页）的「换模式」入口：合并页上翻卡与测验都在一页里，
   会话没有占满顶栏，切换不该被「先退出会话」挡住。点它＝放弃当前会话、
   切到另一个模式的设置面板（与 quitSession / 测验退出同一口径：中途放弃的部分不落成绩）。 */
function modeSwitchBtn() {
  const toQuiz = studyTab === 'flashcards';
  return `<button class="btn ghost sm fc-modeswitch" id="modeSwitchBtn"
    title="${toQuiz ? '切到测验（放弃本轮卡片学习）' : '切到学习模式（放弃本场测验）'}"
    aria-label="${toQuiz ? '切到测验模式，当前会话将被放弃' : '切到学习模式，当前会话将被放弃'}">
    ${svgFor(toQuiz ? 'pen' : 'cards')} ${toQuiz ? '测验' : '学习'}</button>`;
}
function bindModeSwitchBtn() {
  const b = $('#modeSwitchBtn');
  if (!b) return;
  b.onclick = () => {
    if (studyTab === 'flashcards') {
      /* 放弃翻卡会话，切到**测验**模式。
         此前只调 quitSession()：它把 fc.session 清零后重渲染，
         但 studyTab 仍是 'flashcards' —— 于是这颗写着「测验」的按钮
         把人送回翻卡的**范围选择页**，压根没切模式（实测：点它之后
         页面上是 deck-setup 而非 quiz-setup，模式卡仍是 flashcards 高亮）。
         两边口径对称：**离开哪个模式就清哪个模式的会话**，被切过去的那个
         模式若还挂着会话则从原处续上（与顶栏来回切页同一条口径）。 */
      fc.session = 0; fc.i = 0; fc.total = 0; fc.requeue = 0; fc.undo = []; fc.stats = null;
      studyTab = 'quiz';
      renderView('study');
    } else {
      quiz.session = 0; quiz.fb = null;
      studyTab = 'flashcards';
      renderView('study');
    }
  };
}
function renderStage() {
  const root = $('#main');
  const w = fc.queue[fc.i];
  if (!w) {   // 兜底：队列异常时回到范围选择，而不是留下一片空白
    fcNotice = '这一轮已经结束了，回范围选择再来一组吧。';
    fc.session = 0; renderView('study'); return;
  }
  /* 进度条口径＝「你在第几张」＝(i+1)/total，与旁边「第 N / M 张」逐字对上。
     此前是 i/total：第一张卡显示 0%，与「第 1 / 30 张」自相矛盾。 */
  const pct = (fc.i + 1) / fc.total * 100;
  const st = fc.stats || { good: 0, mid: 0, bad: 0 };
  // 「按 1/2/3」小字与卡面翻面提示同受「显示快捷键提示」开关管辖（此前常驻，绕过了设置）
  const kbdHint = k => state.settings.showKeyHint ? `<span class="kbd-hint"> · 按 ${k}</span>` : '';
  /* 卡背「手动标记」三钮的当前态：与词条弹窗同一口径（无进度条目＝不认识；
     有条目且已掌握＝已掌握；其余＝学习中），高亮跟页面别处一致。 */
  const markCur = !prog(w.num) ? 'new' : isMastered(w.num) ? 'mastered' : 'learning';
  /* 会话计数条与下方评分钮同一把尺子：忘了 → 模糊 → 认识，左到右同序 ——
     两组三键一上一下，视线不用换算（二百零四轮）。 */
  root.innerHTML = `
    <div class="fc-stage">
      <div class="fc-progress">
        <span style="white-space:nowrap">${svgFor(fc.src === 'due' ? 'alarm' : 'cards')} ${esc(DECK_INFO[fc.src] || fc.src)}</span>
        <div class="progress-line"><div style="width:${pct}%"></div></div>
        <span class="fc-meta">${fc.i + 1} / ${fc.total}${fc.requeue ? `（重排 ${fc.requeue}）` : ''}</span>
        ${modeSwitchBtn()}
      </div>
      <div class="fc-session-strip" aria-label="本会话评分计数">
        <span class="fcss-item bad">${svgFor('frown')} 忘了 <b>${st.bad}</b></span>
        <span class="fcss-item mid">${svgFor('meh')} 模糊 <b>${st.mid}</b></span>
        <span class="fcss-item good">${svgFor('check')} 认识 <b>${st.good}</b></span>
      </div>
      <div class="flip-card ${fc.flipped ? 'flipped' : ''}" id="flipCard" role="button" tabindex="0" aria-label="${esc(cardAriaLabel(fc.flipped))}">
        <div class="flip-inner">
          <div class="flip-face flip-front">
            <span class="fc-num">#${w.num}</span><span class="fc-lvl">${lvlChip(w.num)}</span>
            <div class="fc-front-main">
              <div class="fc-recall">先想一想，这个词是什么意思？</div>
              <div class="fc-word-row">
                <div class="fc-word">${esc(w.word)}</div>
                <button class="speak-btn sm" id="fcSpeak" title="朗读 (P)" aria-label="朗读">${svgFor('speaker')}</button>
              </div>
            <div class="fc-front-meta">释义 ${w.senses.length} 条 · 例句 ${exOf(w).length} 句${(w.notes || []).length ? ' · 备注 ' + w.notes.length + ' 条' : ''}</div>
            ${state.settings.frontShowHint && w.pos ? `<div class="mt8">${posTags(w)}</div>` : ''}
            </div>
            <div class="fc-front-foot">
              ${state.settings.showKeyHint ? `<span class="fc-hint">${svgFor('eye')} 点击卡片 或按 <span class="kbd">空格</span> 翻面</span>` : ''}
              <button class="btn primary" id="fcReveal">显示答案</button>
            </div>
          </div>
          <div class="flip-face flip-back">
            <span class="fc-num">#${w.num}</span><span class="fc-lvl">${lvlChip(w.num)}</span>
            <div class="fc-back-inner">
              <div class="fc-back-head">
                <div class="fc-word-row">
                  <div class="fc-word fc-word-back">${esc(w.word)}</div>
                  <button class="speak-btn sm" id="fcSpeak2" title="朗读 (P)" aria-label="朗读">${svgFor('speaker')}</button>
                </div>
                ${(w.pos || w.sub || w.reg) ? `<div class="fc-tags">${posTags(w)}</div>` : ''}
              </div>
              <div class="fc-body">
                <div class="fc-col fc-definition">
                  <div class="fc-sec">释义</div>
                  <div class="fc-senses">${w.senses.map((s, i) => `<div class="fc-sense"><b>${i + 1}</b><span>${esc(s)}</span></div>`).join('')}</div>
                </div>
                <div class="fc-col fc-examples">
                  ${exBlock(w, { max: 3, cls: 'fc-ex', collapseAfter: 1 })}
                </div>
              </div>
              ${(w.notes || []).length || (w.links || []).length ? `<div class="fc-extras">
                ${(w.notes || []).length ? `<div class="fc-notes"><div class="fc-sec">备注</div>${(w.notes || []).map(n => `<div class="fc-note">${svgFor('pin')}<span>${esc(n)}</span></div>`).join('')}</div>` : ''}
                ${(w.links || []).length ? `<div class="fc-dictionaries"><div class="fc-sec">词典</div><div class="fc-links">${(w.links || []).map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(LINK_LABELS(u))}</a>`).join('')}</div></div>` : ''}
              </div>` : ''}
              <div class="fc-mark-row">
                <span class="fc-mark-label">${svgFor('target')} 手动标记</span>
                <div class="fc-mark-btns">
                  <button class="btn sm fc-mark-btn${markCur === 'new' ? ' on' : ''}" data-mk="new">${svgFor('frown')} 不认识</button>
                  <button class="btn sm fc-mark-btn${markCur === 'learning' ? ' on' : ''}" data-mk="learning">${svgFor('seed')} 学习中</button>
                  <button class="btn sm fc-mark-btn${markCur === 'mastered' ? ' on' : ''}" data-mk="mastered">${svgFor('trophy')} 已掌握</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="fc-btns${fc.flipped ? '' : ' pending'}">
        <button class="btn bad" data-q="0">${svgFor('frown')} 忘了<small>${gradeHint(w.num, 0)}${kbdHint(1)}</small></button>
        <button class="btn warn" data-q="1">${svgFor('meh')} 模糊<small>${gradeHint(w.num, 1)}${kbdHint(2)}</small></button>
        <button class="btn good" data-q="2">${svgFor('smile')} 认识<small>${gradeHint(w.num, 2)}${kbdHint(3)}</small></button>
      </div>
      <div class="fc-foot">
        <button class="btn ghost sm" id="fcQuit" title="已评分的卡片保留进度，当前这张不计"
                aria-label="退出会话（已评分的卡片保留进度，当前这张不计）">${svgFor('chevL')} 退出会话</button>
        <div class="hstack">
          <button class="btn ghost sm fc-undo" id="fcUndo" ${fc.undo.length ? '' : 'disabled'}>${svgFor('undo')} 撤销</button>
          <button class="btn ghost sm" id="fcFav">${isFav(w.num) ? svgFor('star-f') : svgFor('star')} ${isFav(w.num) ? '已收藏' : '收藏'}</button>
        </div>
      </div>
    </div>`;
  const card = $('#flipCard');
  const swipe = state.settings.swipeGrade ? bindSwipe(card) : null;
  // 滑动跨过评分阈值后，浏览器补发的 click 必须吞掉，否则点一下松手就翻回正面
  // 词典链接（a）同样不该触发翻面：点了链接是要开新标签页看词典，不是翻卡
  card.onclick = e => { if (swipe && swipe.consumeClick()) return; if (!e.target.closest('button, a, summary')) flip(); };
  $$('.fc-ex-more').forEach(d => {
    d.open = !!fc.examplesOpen;
    d.addEventListener('toggle', () => { fc.examplesOpen = d.open; fitCardHeight(); });
  });
  /* 卡面自己的键盘处理与全局「空格翻面」快捷键都会触发 flip()：
     焦点在卡面上时一次按键翻两次 = 看起来没反应。这里止住冒泡，只让卡面处理一次。 */
  card.onkeydown = e => {
    if (e.target !== card || (e.key !== 'Enter' && e.key !== ' ')) return;
    e.preventDefault(); e.stopPropagation(); flip();
  };
  $('#fcSpeak').onclick = $('#fcSpeak2').onclick = e => { e.stopPropagation(); speak(w.word); };
  $('#fcReveal').onclick = e => { e.stopPropagation(); flip(); };
  $$('.fc-btns .btn').forEach(b => b.onclick = e => { e.stopPropagation(); rate(+b.dataset.q); });
  $('#fcQuit').onclick = quitSession;
  $('#fcUndo').onclick = undoLast;
  $('#fcFav').onclick = () => { toggleFav(w.num); renderStage(); };
  /* 卡背的「手动标记」（不认识 / 学习中 / 已掌握）：与词条弹窗同一套语义 ——
     「不认识」删掉整条进度（词回到未学），其余写进度条目。
     标记完就地重绘：等级徽标与三钮的高亮都要跟着变。 */
  $$('.fc-mark-btn').forEach(b => b.onclick = e => {
    e.stopPropagation();
    const st = b.dataset.mk;
    setStatus(w.num, st);
    toast(st === 'new' ? '已标记为不认识' : st === 'learning' ? '已标记为学习中' : '已标记为已掌握',
          1500, st === 'new' ? 'frown' : st === 'learning' ? 'seed' : 'trophy');
    renderStage();
  });
  if (!fc.autoSpoke && state.settings.autoSpeak) { speak(w.word); fc.autoSpoke = 1; }
  bindModeSwitchBtn();
  fitCardHeight();   // 评分后重渲染的新卡若仍处翻面态，卡高要跟着新词条重算
  /* 评分后整块重渲染销毁了被聚焦的评分钮 ⇒ 焦点掉回 body。
     把焦点交回新卡（role=button tabindex=0）：键盘用户接着按空格翻面，
     读屏用户也落到新内容上而不是空白页。 */
  refocus($('#flipCard'));
}
/* 卡面的可访问名（role=button）：读屏用户按空格翻面后，得听到这一面在讲什么。
   正面＝「词 + 翻面提示」；背面＝「词 + 释义摘要 + 例句条数」——
   不把整面文字（释义＋三条例句＋备注＋词典链接）原样塞进去：
   那会让读屏用户每次翻面都听一段几百字的清单，反而听不出重点。 */
function cardAriaLabel(flipped) {
  const w = fc.queue[fc.i];
  const word = w ? w.word : '';
  if (!flipped) return word ? word + '，翻转卡片查看释义' : '翻转卡片查看释义';
  if (!w) return '卡片背面：释义';
  const senses = (w.senses || []).join('；');
  const exN = exOf(w).length;
  return (word ? word + '，' : '') + '卡片背面：' + (senses || '释义')
       + (exN ? '，例句 ' + exN + ' 句' : '')
       + ((w.notes || []).length ? '，备注 ' + w.notes.length + ' 条' : '');
}
function flip() {
  fc.flipped = !fc.flipped;
  const card = $('#flipCard');
  card?.classList.toggle('flipped', fc.flipped);
  /* 评分钮的 pending 态跟着翻面走：flip() 不重渲染（只切卡面类名），
     不在这里同步摘挂的话，「干净翻面」后三颗钮仍是中性灰，语义色不回来
     （renderStage 只在开卡/评分/撤销等整块重绘时算一遍 pending）。 */
  $('.fc-btns')?.classList.toggle('pending', !fc.flipped);
  if (fc.flipped) fc.autoSpoke = 1;
  fitCardHeight();
  if (card) card.setAttribute('aria-label', fc.flipped ? cardAriaLabel(true) : cardAriaLabel(false));
}
/* 卡高随内容走：卡背要装下整条词条（释义 / 例句 / 备注 / 词典 / 标记），
   高度写死就会出现「内容被卡底截掉」或「短词条留一大片空」两种毛病。
   量法：卡背正文是一个高度自适应的块（flex 项，min-height:auto 不缩），
   它的 offsetHeight 就是内容的自然高——不必临时改卡高去量（那会闪一下）。
   宽屏上限按视口高度的 82% 收口：再高就把卡面内部滚动条交给用户；
   窄屏（单栏）不设上限，让整张卡摊开由页面滚——在 3D 翻转面里滚很别扭。 */
function fitCardHeight() {
  const card = $('#flipCard');
  if (!card) return;
  if (!fc.flipped) { card.style.height = ''; return; }
  const inner = card.querySelector('.fc-back-inner');
  const face = card.querySelector('.flip-back');
  if (!inner || !face) return;
  /* 内容高之外还要算卡面的 padding 与 border。此前固定 +58 对应旧版 28px
     上下内边距；卡面改成 32px 后仍加 58，会让桌面卡背平白多出 8px 滚动。 */
  const fs = getComputedStyle(face);
  const px = v => parseFloat(v) || 0;
  const chrome = px(fs.paddingTop) + px(fs.paddingBottom)
               + px(fs.borderTopWidth) + px(fs.borderBottomWidth);
  const need = Math.ceil(inner.offsetHeight + chrome);
  const narrow = (window.innerWidth || 1280) <= 760;
  const cap = narrow ? Infinity : Math.round((window.innerHeight || 900) * 0.82);
  const base = narrow ? 390 : 420;
  const h = Math.max(base, Math.min(need, cap));
  card.style.height = h + 'px';
}
/* 触屏滑动评分：只在卡面（已翻面）响应触摸指针。横向拖过 64px 松手 →
   右=认识 / 左=忘了；阈值内按点击对待，走原有翻面逻辑。拖动中卡片跟手平移
   （transform 挂在外壳 .flip-card 上，与 .flip-inner 的 rotateY 互不打架）；
   CSS 侧 .flip-card{touch-action:pan-y} 保证竖滑仍能滚页面。
   五十四轮加固两处：① 锁定首个 touch 的 pointerId——双指/手掌误触时
   第二根手指的 move/up 不得劫持正在进行的滑动（起点被改写会误评分）；
   ② 松手判定要求「水平仍占优」——斜向下滑（实为滚页意图）哪怕 dx 过阈
   也不触发，与 move 里跟手平移的门槛保持一致口径 */
function bindSwipe(card) {
  const TH = 64;
  let sx = 0, sy = 0, dx = 0, dy = 0, pid = -1, tracking = false, fired = false;
  card.addEventListener('pointerdown', e => {
    if (e.pointerType !== 'touch' || !fc.flipped || tracking) return;
    tracking = true; fired = false; pid = e.pointerId; dx = dy = 0; sx = e.clientX; sy = e.clientY;
  });
  card.addEventListener('pointermove', e => {
    if (!tracking || e.pointerId !== pid) return;
    dx = e.clientX - sx; dy = e.clientY - sy;
    if (Math.abs(dx) <= Math.abs(dy)) { card.style.transform = ''; return; }
    card.style.transform = 'translateX(' + Math.max(-96, Math.min(96, dx)) + 'px)';
  });
  const end = e => {
    if (!tracking || e.pointerId !== pid) return;   // 其他手指的抬起不结束本次滑动
    tracking = false; pid = -1;
    card.style.transform = '';
    if (Math.abs(dx) <= Math.abs(dy)) return;       // 纵向占优＝滚页手势，不评分
    if (dx > TH) { fired = true; rate(2); }
    else if (dx < -TH) { fired = true; rate(0); }
  };
  card.addEventListener('pointerup', end);
  card.addEventListener('pointercancel', e => {
    if (!tracking || e.pointerId !== pid) return;
    tracking = false; pid = -1; card.style.transform = '';
  });
  return { consumeClick() { const f = fired; fired = false; return f; } };
}
function rate(q) {
  const w = fc.queue[fc.i];
  if (!w) return;
  if (!fc.flipped) { flip(); toast('先看释义再评分', 1400, 'eye'); return; }
  const before = prog(w.num) ? { ...prog(w.num) } : null;
  /* 撤销要用「差量」而不是「整条快照覆盖」：评分之后这个词还可能被手动标记、
     被测验答到、被再次评分——整条覆盖会把那些后来 legitimate 的改动一起抹掉
     （此前撤销会把手动标成「已掌握」的词直接退回未学）。
     快照仍要存：它用来判断「此后的改动有没有动过同一个字段」，
     没动过的字段才回退，动了的字段原样保留。 */
  const dayK = todayStr();
  const statsBefore = Object.assign({}, fc.stats);
  grade(w.num, q, true);
  const after = prog(w.num) ? { ...prog(w.num) } : null;
  fc.undo.push({ num: w.num, before, after, q, dayK, requeued: q === 0, stats: statsBefore });
  if (q === 2) fc.stats.good++; else if (q === 1) fc.stats.mid++; else fc.stats.bad++;
  if (q === 0) { fc.queue.push(w); fc.requeue++; fc.total++; }
  fc.i++; fc.flipped = false; fc.autoSpoke = 0; fc.examplesOpen = false;
  if (fc.i >= fc.queue.length) return finishSession();
  renderStage();
}
/* 撤销上一次评分：回滚记忆等级、队列与会话统计 */
function undoLast() {
  const u = fc.undo.pop();
  if (!u) { toast('没有可撤销的评分', 1400, 'info'); return; }
  /* 撤销只回退「这次评分造成的那一份改动」，不整条覆盖：
     评分之后该词可能又被手动标记 / 被测验答到 / 被再次评分，
     整条覆盖会把那些后来 legitimate 的改动一起抹掉。
     做法：与「评分后快照」逐字段比对——没被后来改过的字段才回退。 */
  const cur = state.progress[u.num];
  /* 该词的进度条目在评分之后被手动「不认识」删掉了（setStatus 'new' 删条目）：
     此时的正确语义是「保留那次手动重置」，但等级/计数无从回退（条目已不存在）。
     若仍提示「已撤销上一次评分」，提示与实际状态不符 → 换成据实提示。 */
  const staleReset = !!(u.before && !cur);
  if (u.before) {
    if (cur) {
      if (cur.lv === u.after.lv) cur.lv = u.before.lv;
      if (cur.due === u.after.due) cur.due = u.before.due;
      if (cur.last === u.after.last) cur.last = u.before.last;
      /* 计数同理：只有「评分之后没人动过这个计数」才回退到评分前的值。
         评分后又答过一次（seen/correct 又 +1）时，回退会把那次也抹掉。 */
      if (cur.seen === u.after.seen) cur.seen = u.before.seen;
      if (cur.correct === u.after.correct) cur.correct = u.before.correct;
      if (cur.wrong === u.after.wrong) cur.wrong = u.before.wrong;
    }
  } else if (cur && u.after && cur.lv === u.after.lv && cur.seen === u.after.seen
             && cur.correct === u.after.correct && cur.wrong === u.after.wrong) {
    // 评分前本来没有进度条目，且此后没人动过它 → 整条删掉（回到出厂态）
    delete state.progress[u.num];
  }
  /* 互动次数按差量回退（此前是绝对值覆盖：评分后又在测验里答了题，
     撤销会把当天次数直接写成评分当时的旧值，测验那次的活跃被抹掉）。
     日期键仍取「评分当天」——跨午夜撤销时要减的是昨天那一次。 */
  if (u.dayK && state.days[u.dayK] != null) {
    state.days[u.dayK] = Math.max(0, state.days[u.dayK] - 1);
    if (!state.days[u.dayK]) delete state.days[u.dayK];
  }
  updateVisitPill();   // 回退可能把当天次数清零，顶栏徽标跟着重算
  if (u.requeued) { fc.queue.pop(); fc.requeue = Math.max(0, fc.requeue - 1); fc.total = Math.max(0, fc.total - 1); }
  fc.stats = u.stats;
  fc.i = Math.max(0, fc.i - 1);
  if (fc.i >= fc.queue.length) fc.i = Math.max(0, fc.queue.length - 1);
  fc.flipped = false; fc.autoSpoke = 0; fc.examplesOpen = false;
  save();
  renderStage();
  toast(staleReset ? '已撤销评分与当日计数（该词进度已被手动重置，等级未回退）'
                    : '已撤销上一次评分', 1500, 'undo');
}
function finishSession() {
  fc.session = 0;
  const done = fc.queue.length;
  const st = fc.stats || { good: 0, mid: 0, bad: 0 };
  const rated = st.good + st.mid + st.bad;
  const acc = rated ? Math.round(st.good / rated * 100) : 0;
  const tc = tierCounts();
  const root = $('#main');
  root.innerHTML = `
    <div class="fc-stage center card card-pad" style="max-width:560px;margin:52px auto">
      <div class="fc-done-ic">${svgFor('sparkles')}</div>
      <h2 style="font-size:22px;margin:10px 0 4px">本轮复习完成！</h2>
      <p class="dim">${esc(DECK_INFO[fc.src] || fc.src)} · 共 <b>${done}</b> 张卡片</p>
      <div class="fc-summary">
        <div class="fc-sum"><div class="n" style="color:var(--good)">${st.good}</div><div class="l">认识</div></div>
        <div class="fc-sum"><div class="n" style="color:var(--warn)">${st.mid}</div><div class="l">模糊</div></div>
        <div class="fc-sum"><div class="n" style="color:var(--bad)">${st.bad}</div><div class="l">忘了</div></div>
        <div class="fc-sum"><div class="n">${acc}%</div><div class="l">记得率</div></div>
      </div>
      <p class="faint">当前复习队列剩 ${tc.due} 词 · 已掌握 ${tc.mastered} 词</p>
      <div class="mt24 hstack-center">
        <button class="btn primary" id="againBtn">${svgFor('repeat')} 再来一轮</button>
        <button class="btn" id="changeDeckBtn">换范围</button>
        <button class="btn" id="toQuizBtn">做个测验</button>
      </div>
    </div>`;
  $('#againBtn').onclick = () => { fc.queue = buildDeck(fc.src).slice(0, fc.lastLimit || 30); startSession(); };
  /* 「换范围」此前是 <a href="#cards">：完成面板是**就地**渲染的，此时 URL 片段
     已经是 #cards，点它等于把片段设成同一个值 → 不触发 hashchange → 路由不跑 →
     完成面板纹丝不动（实测：deck-setup 不出现，#againBtn 仍在，顶栏「学习」同样点不动）。
     改成按钮，直接回到范围选择页。 */
  $('#changeDeckBtn').onclick = () => { fc.session = 0; renderView('study'); };
  /* 「做个测验」同样就地切模式：完成面板此时 URL 已是 #study，
     <a href="#study"> 不会再触发路由（与上面「换范围」同一坑）。 */
  $('#toQuizBtn').onclick = () => { fc.session = 0; studyTab = 'quiz'; renderView('study'); };
}
function quitSession() { fc.session = 0; fc.i = 0; fc.total = 0; fc.requeue = 0; fc.undo = []; fc.stats = null; renderView('study'); }

/* ---------- 测验 ---------- */
let pendingScope = null;
const MODES = {
  en2zh: { name: '看词选义', prompt: '选出正确释义', icon: 'eye' },
  zh2en: { name: '看义选词', prompt: '选出对应单词', icon: 'link' },
  spell: { name: '拼写填空', prompt: '根据释义拼写单词', icon: 'pen' },
  listen: { name: '听音辨词', prompt: '听发音，选出单词', icon: 'speaker' },
  cloze: { name: '例句挖空', prompt: '选出能填入空格的本词', icon: 'file' },
};
/* 例句挖空：只用「原形恰好出现在例句中」的句子（大小写不敏感、词边界守卫），
   选项永远是原形本体——不挖屈折形（surged 的空答 surge 会显得「语法不对」）。
   确定性取第一句命中，「离开→resume」重放渲染同一句，与 fb 快照口径一致；
   原形不现身的少数词（如 irregular 变形）由出题处回退「看词选义」。 */
function clozeSlot(w) {
  /* 挖空句必须**只出现一次**目标词：句中若还有第二处该词，挖掉一处后答案
     仍明晃晃写在题干里（"Extraordinary claims require extraordinary evidence"）。
     优先挑只含一次的句子；全都含多次时才退而求其次用第一处（并照旧只挖一处）。 */
  const re = new RegExp('(^|[^A-Za-z])' + escRe(w.word) + '(?![A-Za-z])', 'gi');
  let fallback = null;
  for (const e of exOf(w)) {
    re.lastIndex = 0;
    const m = re.exec(e.en);
    if (!m) continue;
    const start = m.index + m[1].length;
    const slot = { en: e.en, zh: e.zh, start, len: w.word.length };
    const hits = e.en.match(new RegExp('(^|[^A-Za-z])' + escRe(w.word) + '(?![A-Za-z])', 'gi'));
    if (!hits || hits.length <= 1) return slot;   // 只出现一次 → 直接用
    if (!fallback) fallback = slot;                // 全都出现多次 → 记第一句兜底
  }
  return fallback;
}
const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const quiz = { mode: 'en2zh', scope: 'all', count: 10, queue: [], i: 0, score: 0, wrong: [], answered: false, skipped: 0, fb: null };
                                  // fb：已作答但反馈还没翻篇的题的快照 {i, ok, mode, pick|val}——
                                  // 反馈态误点导航再回来时按快照恢复反馈，绝不重新计分
let quizNotice = null;   // 范围太小时常驻提示
let quizReplayT = null;  // 听音辨词的自动重播定时器：换题/退出必须清掉，
                         // 否则快速连点「跳过」时，上一题的单词会在 150ms 后追读出来
/* 导入 / 重置不只替换存档，还必须作废两套内存会话。否则旧反馈页能在清空后
   继续 quizResult() 写回历史，旧牌桌也能靠下一次评分重建 progress。 */
function invalidateStudySessions() {
  clearTimeout(quizReplayT); quizReplayT = null;
  pendingDeck = null; pendingScope = null;
  fc.queue = []; fc.i = 0; fc.flipped = false; fc.session = 0; fc.total = 0;
  fc.custom = null; fc.undo = []; fc.stats = null; fc.requeue = 0; fc.autoSpoke = 0; fc.examplesOpen = false;
  quiz.queue = []; quiz.i = 0; quiz.score = 0; quiz.wrong = [];
  quiz.answered = false; quiz.skipped = 0; quiz.fb = null; quiz.session = 0; quiz.curMode = null;
  fcNotice = null; quizNotice = null;
}
/* 测验范围表：设置页 chips 与结果页 scopeName 共用。
   （历史记录的 scopeName 此前单独写死为「全部」，现与设置页统一为「全部词库」；
     已存的历史记录是字符串快照，不受影响）
   「未学习」这一档的名字与翻卡面板统一为「未学习新词」：两个标签页
   取的是**同一个集合**（deckList('new') = 还没开始学的词），此前一个写
   「未学习新词」、一个写「未学习」，同一页上同一个范围两个名字，
   用户切标签时得自己认这两条说的是同一批词。其余各档两页本就同名。 */
const QUIZ_SCOPES = {
  all: ['books', '全部词库'], due: ['alarm', '复习队列'], learning: ['trend', '学习中'],
  new: ['seed', '未学习新词'], picked: ['tag', '核心词'], fav: ['star-f', '收藏'],
};
/* 各范围词数与 tierCounts 同源；all/picked 是固定量 */
const quizScopeCount = (k, tc) => k === 'all' ? WORDS_MAX : k === 'picked' ? CORE_MAX : tc[k];
/* 历史记录的展示名：modeName/scopeName 快照是后加的字段，老存档里可能没有；
   按当时代就已存在的 mode/scope 码回推，别让首页/统计页读出一行空白 */
const histModeName = h => h.modeName || (MODES[h.mode] || { name: '混合题型' }).name;
const histScopeName = h => h.scopeName || (QUIZ_SCOPES[h.scope] || [])[1] || h.scope || '';
/* 取池：与学习牌组共用 deckList（all/due/learning/new/picked/fav 六个 key 语义一致；
   deckList 的 default 分支是到期队列——若将来新增 scope，记得同步两边） */
const quizPool = scope => deckList(scope);
/* 焦点保全：整块重渲染（root.innerHTML = html）会销毁被聚焦的元素，
   Chromium 于是把焦点甩回 <body>——键盘用户从此失去位置，
   读屏用户也听不到新内容（界面窗报出、本窗在 Chromium 上直验：
   开始测验／作答／下一题／评分之后 document.activeElement 都是 BODY）。
   下面的 refocus 只在「焦点确实是随这次重渲染丢了」时交回新内容：
   焦点若还在别处（例如搜索浮层还开着），不抢。 */
function refocus(target) {
  if (!target) return;
  const a = document.activeElement;
  if (a && a !== document.body && a !== document.documentElement) return;
  try { target.focus(); } catch (e) { /* 元素已不在文档里 */ }
}
function renderQuizQuestion() {
  // 出题动作本身就意味着切到测验模式（与 startSession 置翻卡模式同一逻辑：
  // 老结果页的「再来一组」「只测错题」等入口都经这里渲染答题页）
  studyTab = 'quiz';
  clearTimeout(quizReplayT);   // 先掐掉上一题的自动重播，再出新题
  const root = $('#main');
  const w = quiz.queue[quiz.i];
  if (!w) {   // 兜底：队列为空时回到设置页，而不是继续渲染造成报错
    quizNotice = '这个范围现在没有可测验的单词了，换个范围试试。';
    quiz.session = 0; renderView('study'); return;
  }
  // 没有可用的**英语**音色时，混合模式也不能抽到「听音辨词」：
  // 浏览器有 speechSynthesis 不等于它能读英语（中文 Windows 可只装中文音色）。
  const mkeys = canSpeakEnglish() ? Object.keys(MODES) : Object.keys(MODES).filter(m => m !== 'listen');
  // 反馈态恢复（第四十九轮）：已作答的题被「离开→resume」重放时会重新洗牌重出，
  // 再答一次就会二次 score++/grade()（得分可超总数、seen 双计、wrong 出重复项）。
  // 有快照就沿用快照题型，渲染完直接重建反馈，不重走计分路径。
  const fbSnap = quiz.fb && quiz.fb.i === quiz.i ? quiz.fb : null;
  let mode = fbSnap ? fbSnap.mode : (quiz.mode === 'mix' ? rnd(mkeys) : quiz.mode);
  // 只有新听力题才在音色失效时退回文字题。已答反馈只是回看历史：
  // 保留 listen 的题干与英文选项快照，既不自动朗读，也不把题型换成 en2zh。
  if (!fbSnap && mode === 'listen' && !canSpeakEnglish()) mode = 'en2zh';
  // 挖空回退：该词所有例句都没有本词原形时改出「看词选义」。
  // 判定确定性（总是取第一句命中），resume 重放与快照口径一致
  const cz = mode === 'cloze' ? clozeSlot(w) : null;
  if (mode === 'cloze' && !cz) mode = 'en2zh';
  quiz.curMode = mode; quiz.answered = false;
  let html = `
    <div class="quiz-stage">
      <div class="quiz-q-head">
        <span class="quiz-mode-badge">${svgFor(MODES[mode].icon)} ${MODES[mode].name}</span>
        <span>第 <b>${quiz.i + 1}</b> / ${quiz.queue.length} 题 · 得分 <b id="qScore">${quiz.score}</b></span>
        <span class="hstack">
          <button class="btn ghost sm" id="qSkip">${svgFor('skip')} 跳过</button>
          ${modeSwitchBtn()}
          <button class="btn ghost sm" id="qQuit">${svgFor('x')} 退出</button>
        </span>
      </div>
      <div class="progress-line" id="qProgress" style="margin-bottom:16px"><div style="width:${(quiz.i + 1) / quiz.queue.length * 100}%"></div></div>
      <div class="card quiz-card">`;
  if (mode === 'en2zh') {
    html += `<div class="quiz-prompt-tag">${MODES.en2zh.prompt}</div>
      <div class="quiz-prompt" id="qPrompt" tabindex="-1">${esc(w.word)} <button class="speak-btn sm" id="qSpeak" aria-label="朗读">${svgFor('speaker')}</button></div>
      <div class="quiz-opts">${buildOptions(optionTexts(w, x => x.senses.join('；')))}</div>`;
  } else if (mode === 'zh2en') {
    html += `<div class="quiz-prompt-tag">${MODES.zh2en.prompt}</div>
      <div class="quiz-prompt small" id="qPrompt" tabindex="-1">${esc(w.senses[0])}${w.senses.length > 1 ? '…' : ''}</div>
      <div class="quiz-opts">${buildOptions(optionTexts(w, x => x.word))}</div>`;
  } else if (mode === 'listen') {
    html += `<div class="quiz-prompt-tag" id="qPrompt" tabindex="-1">${MODES.listen.prompt}（<button class="btn-link" id="qReplay">${svgFor('speaker')} 重播</button>）</div>
      <div class="quiz-opts">${buildOptions(optionTexts(w, x => x.word))}</div>`;
  } else if (mode === 'cloze') {
    // 题干=挖掉本词的例句 + 中文对照（中文不点词、只作语义线索；不朗读，朗读会泄答案）
    html += `<div class="quiz-prompt-tag">${MODES.cloze.prompt}</div>
      <div class="quiz-prompt cloze-sent" id="qPrompt" tabindex="-1">${esc(cz.en.slice(0, cz.start))}<span class="cloze-blank" aria-label="空格">____</span>${esc(cz.en.slice(cz.start + cz.len))}</div>
      <p class="cloze-zh">${esc(cz.zh)}</p>
      <div class="quiz-opts">${buildOptions(optionTexts(w, x => x.word))}</div>`;
  } else { // spell
    const mask = w.word.replace(/[a-zA-Z]/g, '_');
    const nLetters = (w.word.match(/[a-zA-Z]/g) || []).length;   // 字母数不含空格/连字符，否则与掩码长度对不上
    html += `<div class="quiz-prompt-tag">${MODES.spell.prompt}</div>
      <div class="quiz-prompt small" id="qPrompt" tabindex="-1">${esc(w.senses.join('；'))}</div>
      <p class="dim mt8">提示：<b>${esc(w.word[0])}</b>${esc(mask.slice(1))} （${nLetters} 个字母${w.word.includes('-') ? ' · 含连字符' : ''}）</p>
      <input type="text" class="spell-input" id="spellInput" placeholder="在此输入英文单词…" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="输入英文单词" aria-describedby="qPrompt">
      <div class="quiz-next-row">
        <button class="btn ghost" id="qSkip2">${svgFor('skip')} 跳过</button>
        <button class="btn primary" id="spellCheck">核对答案</button>
      </div>`;
  }
  /* 反馈区给读屏播报：答完一题若没有任何 live 区，读屏用户只会听到「按钮被按下」 */
  html += `<div class="quiz-feedback" id="qFb" role="status" aria-live="polite"></div></div></div>`;
  root.innerHTML = html;
  const replay = () => speak(w.word);
  if ($('#qSpeak')) $('#qSpeak').onclick = replay;
  if ($('#qReplay')) $('#qReplay').onclick = replay;
  /* 自动读题只给**尚未作答的新听力题**。恢复已答反馈时题干与答案已在屏上，
     再自动念一遍就是无操作出声；150ms 的延迟由 afterAnswer 在作答时掐掉。 */
  if (mode === 'listen' && !fbSnap) quizReplayT = setTimeout(replay, 150);
  /* 「退出」＝放弃本场：成绩只在 quizResult 落盘，中途退出等于把已答的题丢掉。
     不弹确认框（会打断键盘流，也挡路），但要说清楚发生了什么，
     否则用户以为「退出」只是先离开一下，回头成绩没了却一头雾水。 */
  $('#qQuit').onclick = () => {
    const answered = quiz.i - quiz.skipped;
    quiz.session = 0;
    renderView('study');
    if (answered > 0) toast(`已退出测验：已答的 ${answered} 题没有计入成绩`, 2600, 'info');
  };
  bindModeSwitchBtn();
  /* 跳过只在「未作答」时计数：反馈态（已答题）下 #qSkip 仍在页首（showFeedback
     只重画 #qFb，不重画 .quiz-q-head），此时点它若照样 skipped++，一道已作答的题
     会被同时算成「已答」和「已跳过」——quizResult 的 answered = total - skipped
     于是把总题数算小，历史 total 记 0、结果页显示「全部跳过」，用户的真实成绩被吞。
     已作答时点「跳过」= 单纯翻页。 */
  const skip = () => {
    if (quiz.answered) { nextQuestion(); return; }
    quiz.skipped++; nextQuestion();
  };
  $('#qSkip').onclick = skip;
  if ($('#qSkip2')) $('#qSkip2').onclick = skip;
  if (mode === 'spell') {
    const inp = $('#spellInput');
    $('#spellCheck').onclick = () => checkSpell(inp.value, w);
    inp.onkeydown = e => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      /* 必须止住冒泡：checkSpell 会禁用输入框（焦点随之落到 body），
         于是同一个 Enter 事件继续冒到 document 的全局快捷键分支时
         「焦点在输入框里」已不成立，全局分支看到 quiz.answered=true
         就立刻 nextQuestion()——反馈卡还没渲染就被翻页，
         用户永远看不到自己拼对了没有（鼠标点「核对答案」不受影响）。 */
      e.stopPropagation();
      if (!quiz.answered) checkSpell(inp.value, w); else nextQuestion();
    };
    if (!fbSnap) inp.focus();   // 恢复反馈态时别抢焦点（空格应走「下一题」全局分支）
  } else {
    $$('.quiz-opt').forEach(b => b.onclick = () => checkChoice(b, w));
  }
  if (fbSnap) restoreFeedback(fbSnap, w);
  /* 新题＝新内容：焦点交给题干，读屏用户才知道「换题了」。
     重渲染销毁了旧焦点后焦点落在 body，新题对读屏用户是静默的；
     题干 tabindex="-1" 只是可编程聚焦，不进 Tab 序列、不改变读屏浏览顺序。
     拼写题例外：焦点留在输入框（上面 inp.focus()），题干经 aria-describedby 播报。 */
  if (!fbSnap && mode !== 'spell') {
    const p = $('#qPrompt');
    if (p) { try { p.focus(); } catch (e) { /* 忽略 */ } }
  }
}
/* 把恢复态画成「刚答完」的样子：选项禁用+标色 / 拼写框定格，反馈卡重建。
   与 checkChoice/checkSpell 的视觉完全一致，唯一区别是不记账（见 renderQuizQuestion 头注） */
function restoreFeedback(snap, w) {
  quiz.answered = true;
  if (snap.pick != null) {
    // 用答题瞬间的选项快照重建（含位置与字母序），干扰项不重抽，
    // 刚点错的那一项必在集合内、标红位置与离开前一致
    const box = $('.quiz-opts');
    if (box && snap.opts) {
      box.innerHTML = buildOptions(snap.opts);
      [...box.children].forEach(b => { b.disabled = true; });
    }
    $$('.quiz-opt').forEach(b => {
      if (b.dataset.ok === 'true') b.classList.add('correct');
      else if (b.dataset.text === snap.pick) b.classList.add('wrong');
      else b.classList.add('dim');
      b.disabled = true;
    });
  } else {
    const inp = $('#spellInput');
    if (inp) {
      inp.value = snap.val || ''; inp.disabled = true;
      inp.style.borderColor = snap.ok ? 'var(--good)' : 'var(--bad)';
      inp.style.boxShadow = 'none';
      const chk = $('#spellCheck');
      chk.textContent = snap.ok ? '✓ 正确' : '✗ 错误';
      chk.className = 'btn sm ' + (snap.ok ? 'good' : 'bad');
      chk.disabled = true;
    }
  }
  showFeedback(snap.ok, w);
}
/* 同释义词分组：WORDS 是静态数据，首次出题时全库建一次，之后 O(1) 查表。
   旧写法每出一题都要对全库词表各做一次 senses.join 再比较，出题密集时是纯浪费 */
let sameSenseGroups = null;
/* 策展同义白名单：释义相近但**不完全相同**的同义词组。
   自动分组只认「释义全文相同」，而像 objective（目标；目的；宗旨；客观的…）
   这样后来追加过义项的词就掉出了 goal / aim 组——中文选词、听音辨词这类
   「按释义出题、按词形出选项」的模式下，同屏会出现两个都算对的选项。
   机械规则（释义元素互为前缀即同组）全库会造出 287 个极大团、内含
   acknowledge·versus 一类假同源，误排除会把题目变浅，故此处只登记策展结论。
   名单随词表维护：新增同义组先在此登记，并把组规模与成员表记入 CHANGELOG。 */
const SYNONYM_GROUPS = [
  ['consequently', 'so', 'therefore', 'hence'],        // 因此；所以
  ['analogous', 'similar'],                            // 相似的；类似的
  ['aim', 'goal', 'objective'],                         // 目标；目的；宗旨
  ['impede', 'obstruct'],                              // 阻碍；妨碍
  ['compare', 'comparison'],                           // 比较；对比
  ['unified', 'uniform'],                              // 统一的；一致的
  ['mainly', 'principally', 'predominantly'],           // 主要地；大体上
  ['in particular', 'particularly'],                   // 尤其；特别是
  ['document', 'record'],                              // 记录；记载
];
let synonymGroupNums = null;
function buildSenseGroups() {
  sameSenseGroups = new Map();
  synonymGroupNums = new Map();
  const byWord = new Map();
  for (const x of WORDS) {
    const k = x.senses.join('；');
    let g = sameSenseGroups.get(k);
    if (!g) sameSenseGroups.set(k, g = new Set());
    g.add(x.num);
    byWord.set(x.word, x.num);
  }
  for (const grp of SYNONYM_GROUPS) {
    const nums = new Set();
    for (const word of grp) {
      const n = byWord.get(word);
      if (n != null) nums.add(n);
    }
    if (nums.size < 2) continue;          // 词表里只剩一个成员 → 不成组
    for (const word of grp) {
      const n = byWord.get(word);
      if (n != null) synonymGroupNums.set(n, nums);
    }
  }
}
function sameSenseGroup(sKey) {
  if (!sameSenseGroups) buildSenseGroups();
  return sameSenseGroups.get(sKey);
}
/* 出题时某个词要排除的同源词编号集合 ＝ 全文同释义组 ∪ 策展白名单组 */
function excludeNums(w) {
  if (!sameSenseGroups) buildSenseGroups();
  const out = new Set(sameSenseGroup(w.senses.join('；')) || []);
  const syn = synonymGroupNums.get(w.num);   // 表按词条编号建（与 sameSenseGroups 一致）
  if (syn) for (const n of syn) out.add(n);
  return out;
}
function optionTexts(w, fieldFn) {   // 正确项 + 3 个去重干扰项
  const out = [fieldFn(w)];
  const seen = new Set([String(out[0]).toLowerCase()]);
  const len = String(out[0]).length;
  // goal / aim / objective 等同义词：这类「同义对」当干扰项会出现两个都对
  // 的选项（zh2en / 听音辨词按词形出选项，无法靠文本去重），因此整组排除
  const sameSenses = excludeNums(w);
  // 干扰项挑选策略：词性相同优先，其次释义长度接近，最后随机抖动避免固定组合
  const rank = x => {
    let s = (w.pos && x.pos) ? (x.pos === w.pos ? 0 : 10) : 5;
    s += Math.min(9, Math.abs(String(fieldFn(x)).length - len));
    return s + Math.random() * 4;
  };
  const ranked = WORDS.filter(x => x.num !== w.num && !sameSenses.has(x.num))
                      .map(x => ({ x, r: rank(x) }))
                      .sort((a, b) => a.r - b.r);
  for (const { x } of ranked) {
    if (out.length >= 4) break;
    const t = String(fieldFn(x));
    if (seen.has(t.toLowerCase())) continue;
    seen.add(t.toLowerCase()); out.push(t);
  }
  const correct = out[0];
  return shuffle(out).map(t => ({ t, ok: t === correct }));
}
function buildOptions(items) {
  return items.map((o, i) => `<button class="quiz-opt" data-ok="${o.ok}" data-text="${esc(o.t)}"><span class="oi">${'ABCD'[i]}</span>${esc(o.t)}</button>`).join('');
}
function afterAnswer(ok, w) {
  /* 听力题如果在 150ms 内作答（rAF 点击、熟练用户的键盘操作），读题定时器
     可能还没发射；答案出现后必须取消它，否则会在反馈卡上突然念出旧题。
     checkChoice 与 checkSpell 都经这里，避免两条作答路径只堵一条。 */
  clearTimeout(quizReplayT);
  quiz.answered = true;
  ok ? quiz.score++ : quiz.wrong.push(w);
  const sc = $('#qScore'); if (sc) sc.textContent = quiz.score;   // 顶栏分数实时更新
  // 由 grade() 统一记账（seen / correct / wrong / 今日活跃），避免重复累加
  grade(w.num, ok ? 2 : 0, true);
  if (!ok && state.settings.autoWrongFav && !isFav(w.num)) { state.fav.push(w.num); }
  save(); updateVisitPill();
  showFeedback(ok, w);
}
/* 反馈卡绘制与「记账」解耦：首答走 afterAnswer→showFeedback，
   resume 恢复走 restoreFeedback→showFeedback，两条路共用视觉但只有一条计分 */
function showFeedback(ok, w) {
  const pg = $('#qProgress > div'); if (pg) pg.style.width = ((quiz.i + 1) / quiz.queue.length * 100) + '%';
  /* 已作答后，页首那颗「跳过」其实只是翻页（skip() 里 answered 分支走 nextQuestion），
     标签却还写着「跳过」——用户会以为这一题没答对被记成了跳过。
     改标成「下一题」：控件位置与键位不变，标签与实际行为对齐。
     （不能直接藏掉：那会连「反馈态点跳过＝翻页、不计 skipped」这条口径一起废掉。） */
  /* 拼写题还有卡片内的第二颗「跳过」#qSkip2。它走同一个 skip()：
     作答后实际行为已是翻页，若只改页首 #qSkip，这颗仍写「跳过」，
     同屏两颗按钮做着同一件事却一个叫「下一题」、一个叫「跳过」。 */
  for (const sk of [$('#qSkip'), $('#qSkip2')]) {
    if (sk) { sk.innerHTML = `${svgFor('arrowR')} 下一题`; sk.setAttribute('aria-label', '下一题'); }
  }
  const fb = $('#qFb');
  fb.className = 'quiz-feedback show ' + (ok ? 'ok' : 'no');
  fb.innerHTML = `
    <div class="fb-head">${svgFor(ok ? 'check-c' : 'x-c')} ${ok ? '回答正确！' : '答错了 —— 正确答案如下'}</div>
    <div><span class="fb-word">${esc(w.word)}</span> <span class="faint">${esc(w.senses.join('；'))}</span></div>
    ${(w.notes || [])[0] ? `<div class="fb-note">${svgFor('pin')} ${esc(w.notes[0])}</div>` : ''}
    <div class="fb-actions">
      <button class="btn primary sm" id="qNext">${quiz.i + 1 >= quiz.queue.length ? '查看结果' : '下一题 →'} <span class="kbd">空格</span></button>
      <button class="btn ghost sm" id="qFavToggle">${favBtnInner(isFav(w.num))}</button>
      <button class="btn ghost sm" id="qSpeak2">${svgFor('speaker')} 朗读</button>
    </div>`;
  $('#qNext').onclick = nextQuestion;
  $('#qSpeak2').onclick = () => speak(w.word);
  $('#qFavToggle').onclick = e => {
    const on = toggleFav(w.num);
    e.currentTarget.innerHTML = favBtnInner(on);
  };
  /* 作答后焦点可能已经丢了：选项钮被禁用 ⇒ Chromium 把焦点甩回 body；
     若焦点还停在题干（用 A-D 快捷键作答时）也一并交给「下一题」——
     键盘用户接着按空格就能翻页，读屏用户也不会停在已被禁用的旧控件上。
     注意：**浏览器禁用焦点元素时的失焦是异步的**，而且比下一帧还晚
     （本窗实测：点选项 → 该按钮的 focusout 事件在 timeout(0) 之后才发生；
      rAF1 时 activeElement 仍是那个 disabled 的按钮，rAF3 才落到 body）。
     所以「读 activeElement 判断焦点是否已丢」的写法无论同步还是 rAF 都判不中
     ⇒ 焦点就此丢在 body（focus_test 实测 activeElement=BODY）。
     改成：认「当前焦点是那张被禁用的选项钮」也算失焦，
     并在 rAF 与稍后的 timeout 各交接一次（幂等，谁先成功都无所谓）。 */
  const handoffToNext = () => {
    const a = document.activeElement;
    const lost = !a || a === document.body || a === document.documentElement;
    const onDisabled = !!(a && a.disabled && a.closest && a.closest('.quiz-card'));
    const onPrompt = !!(a && a.id === 'qPrompt');
    if (!lost && !onDisabled && !onPrompt) return;   // 焦点在别处（如搜索浮层）就不抢
    const nb = $('#qNext');
    if (nb) { try { nb.focus(); } catch (e) { /* 元素已不在文档里 */ } }
  };
  requestAnimationFrame(handoffToNext);
  setTimeout(handoffToNext, 80);
}
function checkChoice(btn, w) {
  if (quiz.answered) return;
  const ok = btn.dataset.ok === 'true';
  // 连选项集一起快照：optionTexts 的干扰项每次渲染重抽，恢复时若现场重建，
  // 被点错的选项可能根本不在新集合里，反馈态就“丢了刚刚答错的那一项”
  quiz.fb = { i: quiz.i, ok, mode: quiz.curMode, pick: btn.dataset.text,
              opts: $$('.quiz-opt').map(b => ({ t: b.dataset.text, ok: b.dataset.ok === 'true' })) };
  $$('.quiz-opt').forEach(b => {
    if (b.dataset.ok === 'true') b.classList.add('correct');
    else if (b === btn) b.classList.add('wrong');
    else b.classList.add('dim');
    b.disabled = true;
  });
  afterAnswer(ok, w);
}
function checkSpell(val, w) {
  if (quiz.answered) return;
  const norm = s => s.toLowerCase().replace(/[^a-z]/g, '');
  const v = norm(val);
  // 整词形匹配：多词短语（by no means / stem from…）输入其中一个单词不能算对
  const ok = v && v === norm(w.word);
  quiz.fb = { i: quiz.i, ok, mode: 'spell', val };
  const inp = $('#spellInput'); inp.disabled = true;
  // 核对钮同步禁用：否则鼠标党点完核对后焦点仍停在该钮，Space/Enter 被 onAct
  // 门控让位给钮的原生激活、而 checkSpell 又因 answered 守卫空转——键盘死锁
  $('#spellCheck').disabled = true;
  inp.style.borderColor = ok ? 'var(--good)' : 'var(--bad)';
  inp.style.boxShadow = 'none';
  $('#spellCheck').textContent = ok ? '✓ 正确' : '✗ 错误';
  $('#spellCheck').className = 'btn sm ' + (ok ? 'good' : 'bad');
  afterAnswer(ok, w);
}
function nextQuestion() {
  quiz.fb = null;   // 快照只在当前题有效，翻页即作废
  quiz.i++;
  if (quiz.i >= quiz.queue.length) return quizResult();
  renderQuizQuestion();
}
function quizResult() {
  quiz.session = 0;
  const total = quiz.queue.length, score = quiz.score;
  const answered = total - quiz.skipped;
  // 存档口径与结果页一致：total 记「实际作答数」而不是「出题数」，
  // 跳过的题单独记 skipped 字段——否则同一场测验在结果页是 80%、
  // 回到首页/统计页按旧口径会算出更低的百分比，正确率趋势也会被跳题拉歪
  const histItem = { t: Date.now(), mode: quiz.mode, modeName: (MODES[quiz.mode] || { name: '混合题型' }).name, scope: quiz.scope, scopeName: (QUIZ_SCOPES[quiz.scope] || [])[1] || quiz.scope, score, total: answered, skipped: quiz.skipped };
  state.quizHist.push(histItem); if (state.quizHist.length > 200) state.quizHist = state.quizHist.slice(-200);
  save();
  const pct = answered ? Math.round(score / answered * 100) : 0;
  // 全部跳过的场次没有作答样本：不该给出「0% · 别灰心」这种惩罚性文案，
  // 也不该把环涂红——它反映的是「未测量」，不是「测量结果为差」
  const msg = !answered ? '这组题全部跳过了，没有产生成绩。'
            : pct >= 90 ? '非常出色！' : pct >= 70 ? '不错，继续保持！' : pct >= 50 ? '及格线附近，重点复习错题。' : '别灰心，先过一遍学习再测验。';
  const mIcon = !answered ? 'skip' : pct >= 90 ? 'trophy' : pct >= 70 ? 'smile' : pct >= 50 ? 'flame' : 'seed';
  const ringColor = !answered ? 'var(--text-3)' : pct >= 70 ? 'var(--good)' : pct >= 50 ? 'var(--warn)' : 'var(--bad)';
  const RC = 2 * Math.PI * 52;
  $('#main').innerHTML = `
    <div class="quiz-stage">
      <div class="card quiz-result">
        <div class="dim">${histItem.modeName} · ${histItem.scopeName}${quiz.skipped ? ` · 跳过 ${quiz.skipped} 题` : ''}</div>
        <div class="result-ring">
          <svg width="132" height="132" viewBox="0 0 120 120" aria-hidden="true">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--line-2)" stroke-width="11"/>
            <circle cx="60" cy="60" r="52" fill="none" stroke="${ringColor}" stroke-width="11" stroke-linecap="round"
                    stroke-dasharray="${RC.toFixed(1)}" stroke-dashoffset="${(RC * (1 - pct / 100)).toFixed(1)}"/>
          </svg>
          <div class="result-ring-label" style="color:${ringColor}">${pct}<small>%</small></div>
        </div>
        <div style="font-size:17px;font-weight:700;display:inline-flex;align-items:center;gap:7px">${svgFor(mIcon)} ${msg}</div>
        <div class="result-bars">
          <span>答对</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;min-width:${pct ? 2 : 0}px;background:var(--good)"></div></div><span>${score}</span>
          <span>答错</span><div class="bar-track"><div class="bar-fill" style="width:${answered ? (1 - pct / 100) * 100 : 0}%;min-width:${answered && pct < 100 ? 2 : 0}px;background:var(--bad)"></div></div><span>${answered - score}</span>
        </div>
        ${quiz.wrong.length ? `<div class="wrong-list">
          <h2 style="font-size:15px;margin:16px 0 10px">错题回顾（${quiz.wrong.length}）</h2>
          ${quiz.wrong.map(w => `<div class="wrong-item" data-num="${w.num}" tabindex="0" role="button">
            <div><span class="wi-w">${esc(w.word)}</span><div class="wi-s">${esc(w.senses.join('；'))}</div></div>
            <div style="display:flex;gap:8px;align-items:center"><button class="mini-btn" data-speak="${esc(w.word)}" aria-label="朗读">${svgFor('speaker')}</button><span>${lvlChip(w.num)}</span></div>
          </div>`).join('')}
        </div>` : ''}
        <div class="mt24 hstack-center">
          ${quiz.wrong.length ? `<button class="btn warn" id="redoWrong">${svgFor('repeat')} 只测错题</button>` : ''}
          <button class="btn primary" id="goAgain">${svgFor('shuffle')} 再来一组</button>
          <button class="btn" id="backSetup">出题设置</button>
        </div>
      </div>
    </div>`;
  $$('.wrong-item').forEach(el => {
    const open = e => {
      const sp = e.target.closest('[data-speak]');
      if (sp) { speak(sp.dataset.speak); return; }
      openWordModal(+el.dataset.num);
    };
    el.onclick = open;
    // 与全站 role="button" 的键盘约定一致：Enter / 空格都可打开，空格不滚页
    el.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(e); } };
  });
  const redo = $('#redoWrong');
  // 只测错题也要守「题数」设置：错题多于设置题数时按设置截断
  // （正常开考路径是 Math.min(count, pool.length)，此处原先整队灌入，超设题数）
  if (redo) redo.onclick = () => { quizNotice = null; quiz.queue = shuffle(quiz.wrong).slice(0, quiz.count); quiz.i = 0; quiz.score = 0; quiz.wrong = []; quiz.skipped = 0; quiz.session = 1; quiz.fb = null; renderQuizQuestion(); };
  $('#goAgain').onclick = () => {
    // 与开始测验不同：再测一组允许 1–3 词的短池（刚答完题范围可能自然缩水），只防真空
    const pool = quizPool(quiz.scope);
    if (!pool.length) {
      // 该范围已经空了（比如复习队列刚被清空），别让题目渲染崩掉
      quizNotice = '这个范围现在没有可测验的单词了，换个范围试试。';
      quiz.session = 0; renderView('study'); return;
    }
    quizNotice = null;
    quiz.queue = pickN(pool, Math.min(quiz.count, pool.length));
    quiz.i = 0; quiz.score = 0; quiz.wrong = []; quiz.skipped = 0; quiz.session = 1; quiz.fb = null; renderQuizQuestion();
  };
  $('#backSetup').onclick = () => renderView('study');
}

/* ---------- 统计 ---------- */
/* 折线图（测验正确率趋势） */
function sparkline(points, w, h, avg) {
  if (!points || points.length < 2) return '';
  const step = w / (points.length - 1);
  const pts = points.map((p, i) => [i * step, h - (Math.max(0, Math.min(100, p)) / 100) * h]);
  const line = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const area = line + ` L ${w} ${h} L 0 ${h} Z`;
  const last = pts[pts.length - 1];
  // 端点用「零长度圆头描边」画点而不是 <circle>：preserveAspectRatio=none 会把
  // 圆横向拉成椭圆（宽卡片上肉眼可见），non-scaling-stroke 的圆头点保持固定像素
  const dot = `M ${last[0].toFixed(1)} ${last[1].toFixed(1)} l 0.01 0`;
  /* 平均线：一条水平虚线。曲线本身说明「在动」，平均线说明「动到哪儿了」——
     没有它，用户只能凭感觉读高低。横线在 preserveAspectRatio=none 下不会变形，
     线宽用 non-scaling-stroke 保持像素粗细。 */
  const avgLine = (avg == null || !points.length) ? '' :
    `<path d="M 0 ${(h - (Math.max(0, Math.min(100, avg)) / 100) * h).toFixed(1)} L ${w} ${(h - (Math.max(0, Math.min(100, avg)) / 100) * h).toFixed(1)}"
      fill="none" stroke="var(--text-3)" stroke-width="1" stroke-dasharray="5 5"
      vector-effect="non-scaling-stroke" opacity=".75"/>`;
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="spg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="var(--accent)" stop-opacity=".32"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/>
    </linearGradient></defs>
    <path d="${area}" fill="url(#spg)"/>
    ${avgLine}
    <path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
    <path d="${dot}" fill="none" stroke="var(--accent)" stroke-width="7" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
  </svg>`;
}
views.stats = (root) => {
  const tc = tierCounts();
  const mastered = tc.mastered, learning = tc.learning, untouched = tc.new;
  const lvDist = [0, 1, 2, 3, 4, 5].map(lv => WORDS.filter(w => (prog(w.num)?.lv ?? -1) === lv).length);
  const totalAnswers = WORDS.reduce((a, w) => a + ((prog(w.num)?.correct || 0) + (prog(w.num)?.wrong || 0)), 0);
  const totalGrades = WORDS.reduce((a, w) => a + (prog(w.num)?.seen || 0), 0);
  const totalCorrect = WORDS.reduce((a, w) => a + (prog(w.num)?.correct || 0), 0);
  const acc = totalAnswers ? Math.round(totalCorrect / totalAnswers * 100) : 0;
  // 字母覆盖
  const letters = 'abcdefghijklmnopqrstuvwxyz'.split('').map(L => {
    const ws = WORDS.filter(w => w.word[0].toLowerCase() === L);
    return { L: L.toUpperCase(), total: ws.length, mastered: ws.filter(w => isMastered(w.num)).length };
  }).filter(x => x.total);
  // 柱长以“已掌握数最多”的字母为基准，否则用总词数做分母会让柱子细得看不见
  const maxL = Math.max(1, ...letters.map(x => x.mastered));
  /* 首字母卡的两层条共用一把尺子：灰条＝该字母的**总词数**（按词数最多的字母归一），
     琥珀条＝其中已掌握的部分。原来的尺子只有「已掌握」一把（maxL），
     一个字母都还没掌握时整张卡只剩一排空轨道，看不出这个字母有多少词。 */
  const maxT = Math.max(1, ...letters.map(x => x.total));
  const maxLv = Math.max(1, ...lvDist);
  // 按词性的掌握分布：写作时选形容词最慌，用户需要知道薄弱在哪个词类
  const posDist = ['形容词', '副词', '动词', '名词', '连词', POS_OTHER].map(p => {
    const ws = p === POS_OTHER ? OTHER_WORDS() : WORDS.filter(w => w.pos === p);
    const m = ws.filter(w => isMastered(w.num)).length;
    const l = ws.filter(w => isStarted(w.num) && !isMastered(w.num)).length;
    return { p: p === POS_OTHER ? '介词' : p, total: ws.length, m, l };
  }).filter(x => x.total);
  /* 日历热力（最近 120 天）：按周对齐（7 行＝一~日、列＝周），星期几一眼可读；
     起始补位用 .heat-pad（不带 .heat/data-tip，120 格断言口径不变），
     月份标挂在每月首个出现的格子上方（.ms + data-m），不再用行内文字标签 */
  const heatFirst = dayOffset(-119);
  const heatPad = (heatFirst.getDay() + 6) % 7;    // 周一起算的行内偏移
  let heat = '';
  for (let i = heatPad; i-- > 0; ) heat += '<span class="heat-pad" aria-hidden="true"></span>';
  let lastM = '';
  let mLabelN = 0;            // 月份标序号：用来给相邻月份错开高度（--heat-lv）
  const heatCounts = [];      // 近 120 天的逐日次数（日历右侧的概览要用）
  for (let i = 119; i >= 0; i--) {
    const d = dayOffset(-i);          // 按自然日推进，避免夏令时偏移
    const k = dayKey(d), mk = k.slice(0, 7), n = state.days[k] || 0;
    heatCounts.push(n);
    const mstart = mk !== lastM; if (mstart) lastM = mk;
    const cls = n === 0 ? '' : n < 10 ? 'h1' : n < 25 ? 'h2' : n < 50 ? 'h3' : 'h4';
    // data-tip 走 CSS :hover，触屏与读屏都取不到；补原生 title 让无障碍树也能读出日期和次数
    const hTip = `${k}${n ? ` · ${n} 次` : ''}`;
    // --hr＝该格所在星期行（0＝周一）：月首常落在周中，月份标要靠它把 ::before 提回网格顶行上方
    const hr = (heatPad + 119 - i) % 7;
    /* --heat-lv＝月份标的错层（0/1）：相邻两列的间距只有一格宽，
       两个月份的标签若同高就会叠成「7月8月」一坨。逐个交错后，
       相邻月份必然一高一低，横向错开。
       计数器必须**按月份标**递增、不是按天递增：原写法 `mLabelN++ % 2` 在
       每天的循环体里执行，而 --heat-lv 只挂在跨月那一格上 ⇒ 取到的是
       「该月首格在 120 天窗口里的日序奇偶」。相邻两个月的日序差＝上个月天数
       （28/29/30/31），偶数月（30 天）⇒ 两个月日序同奇偶 ⇒ 同为 lv=0 ⇒
       标签照旧叠在一起（实测 2026-09 与 2026-10 同为 lv=0）。
       改为：只在真挂了一个月份标时才 +1 ⇒ 挂出的标依次 0,1,0,1… 相邻必异。 */
    const lv = mstart ? (mLabelN++ % 2) : 0;
    heat += `<span class="heat${cls ? ' ' + cls : ''}${mstart ? ' ms' : ''}"${mstart ? ` data-m="${+mk.slice(5)}月" style="--hr:${hr};--heat-lv:${lv}"` : ''} data-tip="${hTip}" title="${hTip}"></span>`;
  }
  /* 120 天概览：日历本身只说「哪天有活动」，这几个数字回答「一共练了多少、连着练了多久」。
     有记录天数 / 最长连续（窗口内）/ 近 30 天次数 / 当前连续（streak，与首页同源）。 */
  const heatActive = heatCounts.filter(n => n > 0).length;
  let heatBest = 0, heatRun = 0;
  for (const n of heatCounts) { if (n > 0) { heatRun++; if (heatRun > heatBest) heatBest = heatRun; } else heatRun = 0; }
  const heat30 = heatCounts.slice(-30).reduce((a, b) => a + b, 0);
  /* 星期标签列：7 行里标出周一/三/五/日，与网格逐行对齐（标签列的行高＝格子行高） */
  const heatDays = ['一', '', '三', '', '五', '', '日'].map(d => `<span>${d}</span>`).join('');
  // 近 14 天活跃（标签用“日”，跨月处标注月份，避免窄屏溢出）
  const days = [];
  let prevM = 0;
  for (let i = 13; i >= 0; i--) {
    const d = dayOffset(-i);          // 按自然日推进，避免夏令时偏移
    const m = d.getMonth() + 1;
    const lbl = (m !== prevM) ? (m + '月') : String(d.getDate());
    prevM = m;
    days.push({ k: dayKey(d), n: state.days[dayKey(d)] || 0, lbl, today: i === 0 });
  }
  const maxD = Math.max(1, ...days.map(d => d.n));
  const daysSum = days.reduce((s, d) => s + d.n, 0);
  // 测验正确率趋势：全跳过的场次 total=0、没有正确率可言，
  // 不能当成 0% 画进曲线/算进平均（否则一次「全部跳过」把趋势拽到地板）
  const trend = state.quizHist.filter(h => h.total > 0).slice(-20).map(h => pct(h.score, h.total));
  const trendAvg = trend.length ? Math.round(trend.reduce((a, b) => a + b, 0) / trend.length) : 0;
  const hist = state.quizHist.slice(-12).reverse();
  /* 顶部关键指标条：统计页此前直接从「词汇进度」环开始，
     用户要读完三张卡才能拼出「我学了多少、掌握多少、正确率多少」。
     这里把六个最常问的数字提到最上面，一眼可读。
     口径全部现算（tierCounts / state.days / prog），不另存一份。 */
  const started = mastered + learning;                 // 学过的词（有进度条目）
  const goalNow = state.settings.goal, actNow = todayActivity();
  const kpi = (v, unit, k, ic) => `<div class="sk-card"><div class="k"><span class="sc-ic">${svgFor(ic)}</span>${k}</div><div class="v">${v}${unit ? `<small>${unit}</small>` : ''}</div></div>`;
  /* 「最薄弱」结论：只看样本够大的（词数 ≥ 阈值），否则「介词 3 词」这类
     小样本会霸榜，结论反而没用。全部掌握数为 0 时不写结论（说了也是废话）。 */
  const posWeak = posDist.filter(x => x.total >= 30)
    .sort((a, b) => (a.m / a.total) - (b.m / b.total))[0];
  const letterWeak = letters.filter(x => x.total >= 20)
    .sort((a, b) => (a.mastered / a.total) - (b.mastered / b.total))[0];
  const canConclude = started > 0;
  const noData = started === 0 && !state.quizHist.length;
  root.innerHTML = `
    <h1 class="page-title">${svgFor('chart')} 学习统计</h1>
    <div class="page-sub">所有数字都来自本机存档；时间维度显示最近 120 天。</div>
    ${noData ? `<div class="stats-empty-banner">${svgFor('info')}<span>还没有学习数据 —— 去「学习」页开一组卡，这里就会出现你的进度曲线、等级分布与正确率趋势。</span><a class="btn primary sm" href="#study">开始学习</a></div>` : ''}
    <div class="stats-kpis">
      ${kpi(started, ` / ${WORDS_MAX}`, '学过', 'seed')}
      ${kpi(mastered, '', '已掌握', 'target')}
      ${kpi(actNow, ` / ${goalNow} 次`, '今日完成', 'flame')}
      ${kpi(acc, '%', '总正确率', 'check-c')}
      ${kpi(streak(), ' 天', '连续学习', 'repeat')}
      ${kpi(tc.dueWeek, ' 词', '未来 7 天到期', 'alarm')}
    </div>
    <div class="stats-grid">
      <div class="card card-pad">
        <h2 class="sec-title">${svgFor('target')} 词汇进度</h2>
        <div class="donut-chart"><svg width="150" height="150" viewBox="0 0 42 42">${donut(mastered, learning, untouched)}</svg>
        <div class="donut-legend">
          <div class="donut-row"><span class="dot" style="background:var(--good)"></span>已掌握 <b>${mastered}</b><span class="faint">（${pct(mastered, WORDS_MAX)}%）</span></div>
          <div class="donut-row"><span class="dot" style="background:var(--blue)"></span>学习中 <b>${learning}</b><span class="faint">（${pct(learning, WORDS_MAX)}%）</span></div>
          <div class="donut-row"><span class="dot" style="background:var(--line-2)"></span>未开始 <b>${untouched}</b><span class="faint">（${pct(untouched, WORDS_MAX)}%）</span></div>
        </div></div>
        <p class="faint mt16">累计答题 / 评分 ${totalGrades} 次 · 未来 7 天将到期 ${tc.dueWeek} 词</p>
        <div class="stats-forecast">
          <div class="sf"><span class="v">${tc.dueTomorrow}</span><span class="k">未来 48 小时到期</span></div>
          <div class="sf"><span class="v">${tc.dueWeek}</span><span class="k">未来 7 天到期</span></div>
        </div>
      </div>
      <div class="card card-pad">
        <h2 class="sec-title">${svgFor('trend')} 记忆等级分布（莱特纳 L0–L5）</h2>
        ${lvDist.every(n => !n)
          ? `<div class="empty-inline">${svgFor('info')} 还没有学习记录 —— 翻一张卡或答一道题，这里就会按记忆等级把词分堆。</div>`
          : lvDist.map((n, i) => `<div class="bar-row wide"><span class="bl">L${i} ${LV_LABEL[i]}<small class="bp">${pct(n, WORDS_MAX)}%</small></span>
          <div class="bar-track"><div class="bar-fill" style="width:${n / maxLv * 100}%;min-width:${n ? 2 : 0}px;background:${LV_COLOR[i]}"></div></div>
          <span class="bar-val">${n}</span></div>`).join('')}
        <p class="faint" style="font-size:12px;margin-top:10px">颜色与词条上的等级标签一致：红＝初学 L0，橙＝学习中 L1–L2，蓝＝熟悉 L3–L4，绿＝已掌握 L5。</p>
      </div>
      <div class="card card-pad">
        <h2 class="sec-title">${svgFor('folder')} 按词性掌握分布</h2>
        ${posDist.map(x => `<div class="bar-row posrow"><span class="bl">${x.p} <small class="bp">${x.total}</small></span>
          <div class="stack-bar" title="已掌握 ${x.m} · 学习中 ${x.l} · 未学 ${x.total - x.m - x.l}">
            ${x.m ? `<i class="s-m" style="width:${x.m / x.total * 100}%"></i>` : ''}${x.l ? `<i class="s-l" style="width:${x.l / x.total * 100}%"></i>` : ''}${x.total - x.m - x.l ? `<i class="s-n" style="width:${(x.total - x.m - x.l) / x.total * 100}%"></i>` : ''}
          </div>
          <span class="bar-val">${x.m}<small class="bp"> · ${pct(x.m, x.total)}%</small></span></div>`).join('')}
        <p class="faint" style="font-size:12px;margin-top:10px">绿＝已掌握 · 蓝＝学习中 · 灰＝未学；右侧为该词性的已掌握数与掌握率。</p>
        ${canConclude && posWeak ? `<p class="stats-note">${svgFor('bulb')} 最薄弱的是<b>${posWeak.p}</b>：${posWeak.total} 词里只掌握了 ${posWeak.m} 个（${pct(posWeak.m, posWeak.total)}%），写作时这个词类最容易卡壳。</p>` : ''}
      </div>
      <div class="card card-pad">
        <h2 class="sec-title">${svgFor('flame')} 近 14 天学习量</h2>
        <div class="week-bars dense${daysSum ? '' : ' empty'}" style="height:118px">
          ${days.map(d => `<div class="wb ${d.n ? '' : 'zero'}" title="${d.k} · ${d.n} 次">
            <span class="n">${d.n || ''}</span>
            <div class="track"><div class="bar" style="height:${d.n ? Math.max(6, d.n / maxD * 76) : 0}px"></div></div>
            <span class="lbl" style="${d.today ? 'color:var(--accent);font-weight:800' : ''}">${d.lbl}</span>
          </div>`).join('')}
        </div>
        ${daysSum ? '' : `<div class="empty-inline mt12">近 14 天暂无学习记录。</div>`}
      </div>
      <div class="card card-pad" style="grid-column:1/-1">
        <h2 class="sec-title">${svgFor('pen')} 测验正确率趋势</h2>
        ${trend.length >= 2 ? `<div class="spark-wrap">${sparkline(trend, 900, 110, trendAvg)}</div>
          <div class="trend-stats">
            <span><i>最新一次</i><b>${trend[trend.length - 1]}%</b></span>
            <span><i>平均</i><b>${trendAvg}%</b></span>
            <span><i>最低</i><b>${Math.min.apply(null, trend)}%</b></span>
            <span><i>计入场次</i><b>${trend.length}</b></span>
          </div>` : '<p class="faint">完成 2 次以上测验后，这里会显示正确率趋势曲线。</p>'}
        ${trend.length ? `<p class="trend-note">${svgFor('info')} 最近 ${trend.length} 次平均正确率 <b style="color:var(--text)">${trendAvg}%</b>（图中的虚线＝平均线）</p>` : ''}
      </div>
      <div class="card card-pad" style="grid-column:1/-1">
        <h2 class="sec-title">${svgFor('cal')} 学习活跃（最近 120 天）</h2>
        <div class="heat-body">
          <div class="heat-cal">
            <div class="heat-days" aria-hidden="true">${heatDays}</div>
            <div class="heat-wrap">${heat}</div>
          </div>
          <div class="heat-sum">
            <div class="hs"><div class="v">${heatActive}<small> 天</small></div><div class="k">有记录的天数</div></div>
            <div class="hs"><div class="v">${heatBest}<small> 天</small></div><div class="k">最长连续</div></div>
            <div class="hs"><div class="v">${heat30}<small> 次</small></div><div class="k">近 30 天次数</div></div>
            <div class="hs"><div class="v">${streak()}<small> 天</small></div><div class="k">当前连续</div></div>
          </div>
        </div>
        <div class="heat-legend"><span>少</span><span class="heat-swatch"></span><span class="heat-swatch h1"></span><span class="heat-swatch h2"></span><span class="heat-swatch h3"></span><span class="heat-swatch h4"></span><span>多</span>
          <span class="heat-legend-note">颜色越深表示当天复习/答题次数越多</span></div>
      </div>
      <div class="card card-pad" style="grid-column:1/-1">
        <h2 class="sec-title">${svgFor('hash')} 按首字母掌握情况</h2>
        <div class="letter-bars">
        ${letters.map(x => `<div class="bar-row lrow"><span class="bl">${x.L} <small class="bp">${x.total}</small></span>
          <div class="bar-track"><i class="bt-total" style="width:${x.total / maxT * 100}%"></i><div class="bar-fill" style="width:${x.mastered / maxT * 100}%;min-width:${x.mastered ? 2 : 0}px"></div></div>
          <span class="bar-val">${x.mastered}<small class="bp"> · ${pct(x.mastered, x.total)}%</small></span></div>`).join('')}
        </div>
        <p class="faint" style="font-size:12px;margin-top:10px">灰条＝该字母的词数，琥珀色＝其中已掌握的词数；右侧为已掌握数与掌握率。</p>
        ${canConclude && letterWeak ? `<p class="stats-note">${svgFor('bulb')} 最薄弱的首字母是<b>${letterWeak.L}</b>（${letterWeak.total} 词里掌握 ${letterWeak.mastered} 个，${pct(letterWeak.mastered, letterWeak.total)}%）—— 从这一列开始补最省力。</p>` : ''}
      </div>
      <div class="card card-pad" style="grid-column:1/-1">
        <h2 class="sec-title">${svgFor('chart')} 最近测验记录</h2>
        ${hist.length ? hist.map(h => {
          const p = pct(h.score, h.total);
          return `<div class="quiz-hist-item"><span>${esc(fmtDateTime(h.t))} · ${esc(histModeName(h))} · ${esc(histScopeName(h))}${h.skipped ? ` · 跳过 ${h.skipped}` : ''}</span>
            <span class="qh-score ${h.total ? (p >= 70 ? 'good' : p >= 50 ? 'mid' : 'low') : 'none'}">${h.total ? `${h.score}/${h.total}（${p}%）` : '未作答'}</span></div>`;
        }).join('')
        : '<div class="empty-state">暂无测验记录</div>'}
      </div>
    </div>`;
};

function pct(a, b) { return b ? Math.round(a / b * 100) : 0; }
function donut(good, mid, rest) {
  const t = good + mid + rest || 1;
  const segs = [];
  let off = 25;
  const push = (n, color) => {
    if (!n) return;
    const len = n / t * 100;
    segs.push(`<circle r="15.9" cx="21" cy="21" fill="transparent" stroke="${color}" stroke-width="6" stroke-dasharray="${len} ${100 - len}" stroke-dashoffset="${off}" style="transition:1s"/>`);
    off -= len; if (off < 0) off += 100;
  };
  push(good, 'var(--good)'); push(mid, 'var(--blue)'); push(rest, 'var(--line-2)');
  return segs.join('') + `<text x="21" y="22.4" text-anchor="middle" font-size="6" font-weight="800" fill="currentColor">${Math.round(good / t * 100)}%</text>`;
}

/* ---------- 设置 ---------- */
/* ---------------------------- 快捷键表 ---------------------------- */
const SHORTCUTS = [
  { group: '全局', items: [['/', '打开全局搜索'], ['?', '显示 / 隐藏快捷键说明'], ['Esc', '关闭弹窗或搜索'], ['← →', '词库翻页']] },
  { group: '学习（翻卡）', items: [['空格', '翻面显示释义'], ['1 / 2 / 3', '忘了 / 模糊 / 认识'], ['S', '收藏当前词'], ['P', '朗读当前词'], ['U', '撤销上一次评分']] },
  { group: '学习（测验）', items: [['1–4 或 A–D', '选择答案'], ['空格 / Enter', '下一题']] },
  { group: '词条弹窗', items: [['← →', '上一个 / 下一个词条'], ['Esc', '关闭弹窗']] },
];
function renderShortcuts() {
  return SHORTCUTS.map(g => `<div class="shortcuts-group"><h3>${esc(g.group)}</h3>${
    g.items.map(([k, v]) => `<div class="shortcuts-row"><span>${esc(v)}</span><kbd>${esc(k)}</kbd></div>`).join('')
  }</div>`).join('');
}

/* ---------- 设置 ---------- */
views.settings = (root) => {
  const s = state.settings;
  /* 分段控件的选中态不能只靠 class 的颜色（屏幕阅读器读不出来）：
     容器给 role=group + 无障碍名，每个按钮给 aria-pressed 当前选中态 */
  const seg = (id, opts, cur, label) => `<div class="seg" id="${id}" role="group"${label ? ` aria-label="${esc(label)}"` : ''}>${opts.map(([k, l]) =>
    `<button type="button" data-k="${k}" class="${String(cur) === String(k) ? 'on' : ''}" aria-pressed="${String(cur) === String(k)}">${esc(l)}</button>`).join('')}</div>`;
  /* 本机存档概况：数据面板要说明「导出的到底是什么」，
     危险面板也要让人知道「清空会删掉这些」——数字全部现算，不另存一份。 */
  const startedN = WORDS.reduce((a, w) => a + (isStarted(w.num) ? 1 : 0), 0);
  const favN = favWords().length;
  const dayN = Object.keys(state.days || {}).length;
  /* 体积按**字节**算：JSON.stringify().length 是字符数，中文一字三字节，
     用字符数会把 UTF-8 体积少报三分之二（「约 N KB」看着比实际小得多）。
     保留 encodeURIComponent 兜底：零依赖 DOM 沙箱不一定提供 TextEncoder。 */
  const stateJson = JSON.stringify(state);
  const utf8Bytes = typeof TextEncoder === 'function'
    ? new TextEncoder().encode(stateJson).length
    : encodeURIComponent(stateJson).replace(/%[0-9A-F]{2}|./g, 'x').length;
  const sizeKB = Math.max(1, Math.round(utf8Bytes / 1024));
    root.innerHTML = `
    <div class="settings-wrap">
    <h1 class="page-title">${svgFor('gear')} 设置</h1>
    <div class="page-sub">所有设置与学习数据都只保存在本机浏览器（localStorage），不会上传到任何服务器；改动即时生效。</div>

    <div class="set-cols">
    <div class="set-col">
      <section class="card card-pad set-card">
        <div class="set-card-head">
          <h2>${svgFor('palette')} 外观与语音</h2>
          <span class="faint">主题与朗读</span>
        </div>
        <div class="set-row"><div><div class="l">主题外观</div><div class="d">浅色 / 深色（默认深色）；顶栏的月亮按钮也能随时切换</div></div>
          ${seg('segTheme', [['light', '浅色'], ['dark', '深色']], s.theme, '主题外观')}</div>
        <div class="set-row"><div><div class="l">朗读语速</div><div class="d">浏览器语音合成（支持离线），词条朗读与「听音辨词」都用它</div></div>
          <div class="range-wrap"><input type="range" id="rateRange" min="0.5" max="1.5" step="0.05" value="${s.rate}" aria-label="朗读语速"><span class="rate-chip"><b id="rateVal">${(s.rate).toFixed(2)}</b>×</span><button class="btn sm" id="rateTest">${svgFor('speaker')} 试听</button></div></div>
        ${TTS && !canSpeakEnglish() ? `<div class="empty-inline" style="margin:0 0 4px">${svgFor('info')} 当前没有英语语音包，朗读已停用，避免用中文音色读英文。Windows 可在「设置 → 时间和语言 → 语音」中添加英语语音，安装后刷新页面即可。</div>` : ''}
        <div class="set-row"><div><div class="l">学习自动朗读</div><div class="d">每次出现新卡片时自动播放发音（默认关；卡面上的喇叭按钮始终可手动朗读）</div></div>
          ${seg('segSpeak', [['0', '关'], ['1', '开']], s.autoSpeak ? '1' : '0', '学习自动朗读')}</div>
      </section>

      <section class="card card-pad set-card">
        <div class="set-card-head">
          <h2>${svgFor('cards')} 学习与测验</h2>
          <span class="faint">翻卡与答题时的行为</span>
        </div>
        <div class="set-row"><div><div class="l">每日目标</div><div class="d">每天希望完成的复习 / 答题次数（5–200），首页的进度环按它算</div></div>
          <span class="num-wrap"><input type="number" id="goalInput" class="set-num" min="5" max="200" value="${s.goal}" aria-label="每日目标次数"><span class="num-unit">次</span></span></div>
        <div class="set-row"><div><div class="l">学习每次上限</div><div class="d">一次复习最多取多少张卡（5–${WORDS_MAX}）；学习页的「每次上限」与此同步</div></div>
          <span class="num-wrap"><input type="number" id="fcLimitInput" class="set-num" min="5" max="${WORDS_MAX}" value="${s.fcLimit}" aria-label="学习每次上限（张）"><span class="num-unit">张</span></span></div>
        <div class="set-row"><div><div class="l">卡片正面显示词性</div><div class="d">带分类标签的词在翻面前即显示词性 / 感情色彩 / 语体色彩</div></div>
          ${seg('segHint', [['0', '关'], ['1', '开']], s.frontShowHint ? '1' : '0', '卡片正面显示词性')}</div>
        <div class="set-row"><div><div class="l">学习滑动手势</div><div class="d">翻面后右滑＝认识、左滑＝忘了（仅触屏，桌面不受影响）</div></div>
          ${seg('segSwipe', [['0', '关'], ['1', '开']], s.swipeGrade ? '1' : '0', '学习滑动手势')}</div>
        <div class="set-row"><div><div class="l">显示快捷键提示</div><div class="d">在卡片与页面上显示可用的键盘操作提示</div></div>
          ${seg('segKeyHint', [['0', '关'], ['1', '开']], s.showKeyHint ? '1' : '0', '显示快捷键提示')}</div>
        <div class="set-row"><div><div class="l">答错自动加入收藏</div><div class="d">测验答错的单词会自动收藏，方便集中攻克</div></div>
          ${seg('segWrongFav', [['0', '关'], ['1', '开']], s.autoWrongFav ? '1' : '0', '答错自动加入收藏')}</div>
      </section>
    </div>

    <div class="set-col">
      <section class="card card-pad set-card">
        <div class="set-card-head">
          <h2>${svgFor('refresh')} 恢复默认设置</h2>
          <span class="faint">只动设置项，不碰学习数据</span>
        </div>
        <div class="set-row"><div class="l">设置恢复默认值</div>
          <button class="btn sm" id="resetSettings">${svgFor('undo')} 恢复默认</button></div>
      </section>
      <section class="card card-pad set-card">
        <div class="set-card-head">
          <h2>${svgFor('keyboard')} 键盘快捷键</h2>
          <span class="faint">按 ? 也能随时唤出</span>
        </div>
        <div class="shortcuts-grid">${renderShortcuts()}</div>
      </section>

      <section class="card card-pad set-card">
        <div class="set-card-head">
          <h2>${svgFor('file')} 数据备份</h2>
          <span class="faint">换设备时先导出、到新设备导入</span>
        </div>
        <div class="set-row"><div><div class="l">导出 / 导入</div><div class="d">导出为 JSON 文件；导入将覆盖当前进度</div></div>
          <div class="hstack"><button class="btn sm" id="expBtn">${svgFor('down')} 导出</button><button class="btn sm" id="impBtn">${svgFor('up')} 导入</button><input type="file" id="impFile" accept=".json" hidden aria-label="选择要导入的备份 JSON 文件"></div></div>
        <p class="set-note">${svgFor('info')}<span>本机存档：已开始 <b>${startedN}</b> 词 · 收藏 <b>${favN}</b> 词 · 活动 <b>${dayN}</b> 天 · 约 <b>${sizeKB}</b> KB。导出的 JSON 就是这些内容。</span></p>
      </section>

      <section class="set-danger">
        <h2 class="set-danger-title">${svgFor('alert')} 危险操作</h2>
        <p class="set-danger-sub">下面两项会删掉本机数据且不可撤销。</p>
        <p class="set-danger-tip">${svgFor('info')} 执行前建议先在上一节「导出」一份备份。</p>
        <div class="danger-zone"><div class="split-row">
          <div><div class="l">重置学习进度</div><div class="d">清除等级、错题、测验记录与活动日历（保留收藏）</div></div>
          <button class="btn sm danger-outline" id="resetProg">${svgFor('trash')} 重置进度</button></div></div>
        <div class="danger-zone danger-zone-strong"><div class="split-row">
          <div><div class="l">清空全部数据</div><div class="d">包括收藏在内的一切本地数据</div></div>
          <button class="btn sm bad" id="resetAll">${svgFor('zap')} 全部清空</button></div></div>
      </section>
    </div>

    <section class="card card-pad set-card set-about">
      <div class="set-card-head">
        <h2>${svgFor('info')} 关于本站</h2>
        <span class="faint">独立维护的学术英语词库</span>
      </div>
      <div class="about-facts">
        <div class="af"><span class="k">词库规模</span><span class="v">共 ${WORDS_MAX} 词，其中 ${CORE_MAX} 个是论文里最常出现的高频词</span></div>
                <div class="af"><span class="k">记忆算法</span><span class="v">莱特纳五盒间隔重复：认识升级、模糊保持、忘了降级</span></div>
        <div class="af"><span class="k">开发者</span><span class="v">关济寰 · <a href="https://www.guanjihuan.com/about" target="_blank" rel="noopener noreferrer">https://www.guanjihuan.com/about</a></span></div>
      </div>
    </section>
    </div>
`;
  $$('#segTheme button').forEach(b => b.onclick = () => { state.settings.theme = b.dataset.k; save(); applyTheme(); renderView('settings'); });
  $$('#segHint button').forEach(b => b.onclick = () => { state.settings.frontShowHint = b.dataset.k === '1'; save(); renderView('settings'); });
  $$('#segSpeak button').forEach(b => b.onclick = () => { state.settings.autoSpeak = b.dataset.k === '1'; save(); renderView('settings'); });
  $$('#segSwipe button').forEach(b => b.onclick = () => { state.settings.swipeGrade = b.dataset.k === '1'; save(); renderView('settings'); });
  $$('#segWrongFav button').forEach(b => b.onclick = () => { state.settings.autoWrongFav = b.dataset.k === '1'; save(); renderView('settings'); });
  $$('#segKeyHint button').forEach(b => b.onclick = () => { state.settings.showKeyHint = b.dataset.k === '1'; save(); renderView('settings'); });
  $('#rateRange').oninput = e => { state.settings.rate = +e.target.value; save();
    // 拖动时同步刷新说明里的倍率数字——此前要等整页重渲染才更新，拖着滑杆看不到反馈
    $('#rateVal').textContent = (+e.target.value).toFixed(2); };
  $('#rateTest').onclick = () => speak('academic vocabulary');
  /* 数字输入归一口径（与首页 goalEdit 同一条，二百零一轮统一）：
     空串/非数字落默认，0 与负数钳到下限 —— `+v || 30` 的 falsy 顶替会把
     合法输入 0 顶成默认值，与 -5 的「钳到下限」两种落点打架。 */
  const numInput = (raw, fb) => {
    const v = String(raw).trim();
    return (v === '' || !Number.isFinite(+v)) ? fb : +v;
  };
  $('#goalInput').onchange = e => { state.settings.goal = Math.round(Math.min(200, Math.max(5, numInput(e.target.value, 30)))); save(); toast('每日目标已更新', 1500, 'check'); renderView('settings'); };
  /* 学习上限此前只在学习页有输入框，设置页九个开关/参数里独缺这一项，
     用户在「设置」里找不到它。这里补上，并与 fc.lastLimit 同步（学习页读的是它） */
  $('#fcLimitInput').onchange = e => {
    const n = Math.max(5, Math.min(WORDS_MAX, Math.round(numInput(e.target.value, 30))));
    state.settings.fcLimit = n; fc.lastLimit = n; save();
    e.target.value = n;
    toast('学习每次上限已更新为 ' + n + ' 张', 1600, 'check');
  };
  $('#expBtn').onclick = () => {
    const blob = new Blob([JSON.stringify(state, null, 1)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'word-learning-backup-' + todayStr() + '.json';
    // Firefox 对未插入文档的 <a> 不执行 download 点击，先挂后点再收起
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);   // click 是异步启动下载，立即 revoke 有竞态
    toast('已导出备份文件', 1800, 'down');
  };
  $('#impBtn').onclick = () => $('#impFile').click();
  $('#impFile').onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = () => { try {
      /* 坏值逐键摘除、其余照常导入（与 loadState 同一口径）：
         一个字段写错不再让整份备份都救不回来。摘掉的键要告诉用户，
         不能让人以为 99% 的备份都原样进来了。 */
      const dropped = [];
      const data = sanitizeState(JSON.parse(r.result), dropped);
      if (!data.progress || !data.settings || !Array.isArray(data.fav)) throw new Error('core fields missing');
      invalidateStudySessions();
      state = pickState(data);
      state.fav = [...new Set(data.fav.map(Number).filter(Number.isFinite))];
      /* 学习每次上限要跟着备份走：fc.lastLimit 是模块加载时从
         state.settings.fcLimit 取的一次性快照，只被设置页的两个输入写回。
         导入换了整份 state 却不同步它 → 设置页显示 40、学习页仍按 30 建牌组，
         两个界面自相矛盾；用户随后在学习页动一下输入框就把 30 写回 state，
         备份里的 40 被永久抹掉（实测）。 */
      fc.lastLimit = Math.max(5, Math.min(WORDS_MAX, +state.settings.fcLimit || 30));
      pruneState();
      save(); applyTheme(); updateVisitPill(); renderView('settings');
      if (dropped.length) {
        const names = dropped.map(k => FIELD_CN[k] || k).join('、');
        toast('已导入，但备份里的' + names + '格式不对，已忽略', 3600, 'alert');
      } else toast('导入成功', 1800, 'check');
    } catch (e) {
      toast(e && e.message === 'core fields missing'
        ? '备份缺少学习进度 / 设置 / 收藏等必要字段，导入失败'
        : '文件格式不正确，导入失败', 2600, 'alert');
    } };
    r.readAsText(f);
    /* 文件框要清空：value 没变时 change 事件不再触发，同一个备份文件
       第二次导入会被静默吞掉（用户以为导入没生效）。 */
    e.target.value = '';
  };
  /* 「恢复默认设置」只回拨九个设置项，与下面两个危险操作划清界限：
     不动 progress / fav / quizHist / days —— 用户想推倒重来的只是「改乱的偏好」，
     学习数据一份都不该少。confirm 挡的是误触（默认值写回去同样即时生效）。
     fc.lastLimit 必须跟着走：它是「学习每次上限」的唯一真相，换档/导入/清空
     三处都同步过，这里是第四处 —— 不然设置页回到 30、学习页仍按旧上限建牌组。 */
  $('#resetSettings').onclick = () => {
    if (confirm('把所有设置恢复为默认值？（学习进度、收藏等数据不受影响）')) {
      state.settings = clone(DEFAULTS.settings);
      fc.lastLimit = Math.max(5, Math.min(WORDS_MAX, +state.settings.fcLimit || 30));
      save(); applyTheme(); renderView('settings');
      toast('已恢复默认设置', 1800, 'check');
    }
  };
  $('#resetProg').onclick = () => {
    if (confirm('确定清空所有记忆等级、答题记录与活动数据？（收藏保留）')) {
      invalidateStudySessions();
      state.progress = {}; state.quizHist = []; state.days = {}; save();
      updateVisitPill();   // 存档清空后顶栏徽标必须重算，否则还挂着旧数字
      renderView('settings'); toast('学习进度已重置', 1800, 'trash');
    }
  };
  $('#resetAll').onclick = () => {
    if (confirm('确定清空包括收藏在内的全部本地数据？此操作不可撤销。')) {
      invalidateStudySessions();
      state = clone(DEFAULTS);
      /* 「清空全部数据」要真清到本地存储这一层：把本机所有 wl* 键删掉
         （现行档 wl_state_v1 之外，早期无版本号的 wl_state 也算「本地数据」，
         留着它等于旧进度还躺在机器上），随后再落一份默认档。 */
      try { Object.keys(localStorage).filter(k => k.startsWith('wl')).forEach(k => localStorage.removeItem(k)); } catch (e) { /* 隐私模式等场景可能禁写，忽略 */ }
      save();
      /* fc.lastLimit 是「学习每次上限」的唯一真相（学习页读它，设置页只是镜像）。
         换档/导入时都同步过它，清空同理 —— 不然设置页回到 30、学习页仍按旧上限建牌组，
         用户刚清空数据就撞见两个界面自相矛盾。 */
      fc.lastLimit = Math.max(5, Math.min(WORDS_MAX, +state.settings.fcLimit || 30));
      applyTheme(); updateVisitPill(); renderView('settings'); toast('已清空全部数据', 1800, 'zap');
    }
  };
};

/* ---------------------------- 全局快速搜索 ---------------------------- */
const so = $('#searchOverlay'), si = $('#searchInput'), sr = $('#searchResults');
/* listbox 容器只允许装 option：随机推荐的说明行与「无结果」空态另放一个 status 容器，
   否则读屏会把非选项的行当列表内容念出来 */
const srStatus = $('#searchStatus'), srBox = $('#searchList'), srMore = $('#searchMore');
/* 浮层里最多列几条：超出的走「在词库中查看全部」（词库页能翻页、能按状态筛） */
const SR_MAX = 12;
let srIdx = -1, srList = [], srQuery = null;
function openSearch() {
  rememberFocus(so);
  so.hidden = false; si.value = ''; si.focus(); doSearch();
}
function closeSearch() {
  if (so.hidden) return;
  so.hidden = true; srIdx = -1;
  /* 组合框状态同步收尾：aria-expanded 只在 doSearch 里被写成 true（结果列表
     出现时），关闭浮层时没人把它写回 false —— 下一次按 / 打开浮层前，
     读屏用户听到的是「已展开」而列表其实还没出（实测：关浮层后
     #searchInput 的 aria-expanded 停留 true）。 */
  si.setAttribute('aria-expanded', 'false');
  si.removeAttribute('aria-activedescendant');
  srMore.hidden = true;
  restoreFocus(so, '#btnSearch');
}
/* 高亮 t 中首个大小写不敏感匹配 q 的片段（q 须已归一化好；由调用方保证转义）。
   词库表格/卡片视图与全局搜索共用这一份实现（此前三处各有一份同构代码）。 */
function markHl(t, q) {
  if (!q) return esc(t);
  const i = t.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return esc(t);
  return esc(t.slice(0, i)) + '<mark>' + esc(t.slice(i, i + q.length)) + '</mark>' + esc(t.slice(i + q.length));
}
function doSearch() {
  const q = si.value.trim().toLowerCase();
  srQuery = q;
  srIdx = -1;
  /* 空查询：给 8 个随机词当门面，并说清它们是随机来的（否则会被当成「全部结果」） */
  if (!q) {
    srList = pickN(WORDS, 8);
    $('#searchCount').textContent = `全库 ${WORDS_MAX} 词`;
    srStatus.innerHTML = `<div class="sr-label">${svgFor('dice')} 随机推荐 · 输入单词或中文释义即可搜索</div>`;
    srBox.innerHTML = srList.map((w, i) => srRow(w, null, i)).join('');
    bindSr();
    setSrExpanded(true);
    srMore.hidden = true;
    return;
  }
  /* 一次扫描说清「命中在哪 + 命中有多强」，再按强度排序 ——
     旧实现按原号顺序取前 12 条：搜「research」（词库里有，#907）会被前头
     两百多个「例句里含 research」的词整个挤掉，用户搜的那个词根本看不见。 */
  const hits = [];
  for (const w of WORDS) {
    const h = searchHit(w, q);
    if (h) hits.push({ w, h });
  }
  /* 同强度时短词在前（搜 "use" 时 "use" 该排在 "because" 前面），再按原号 */
  hits.sort((a, b) => a.h.rank - b.h.rank || a.w.word.length - b.w.word.length || a.w.num - b.w.num);
  const shown = hits.slice(0, SR_MAX);
  srList = shown.map(x => x.w);
  // 右下角计数跟随实际结果，而不是固定显示全库词数
  $('#searchCount').textContent = hits.length
    ? (hits.length > SR_MAX ? `${hits.length} 个结果 · 显示前 ${SR_MAX} 条` : `${hits.length} 个结果`)
    : '无匹配';
  if (!shown.length) {
    srStatus.innerHTML = `<div class="empty-state" style="padding:32px 20px"><div class="es">${svgFor('search')}</div>没有找到「${esc(si.value.trim())}」<br><span class="faint">试试英文前缀或中文释义</span></div>`;
    srBox.innerHTML = '';
    setSrExpanded(false);
    srMore.hidden = true;
    return;
  }
  srStatus.innerHTML = '';
  srBox.innerHTML = shown.map((x, i) => srRow(x.w, x.h, i)).join('');
  bindSr();
  setSrExpanded(true);
  /* 浮层只放得下几条：超出的给一条通往词库的入口（那里能翻页、能按学习状态筛） */
  srMore.hidden = hits.length <= SR_MAX;
  if (!srMore.hidden) {
    srMore.innerHTML = `<button type="button" class="search-more-btn" id="btnSearchAll">${svgFor('list')}在词库中查看全部 ${hits.length} 个结果</button>`;
    $('#btnSearchAll').onclick = () => gotoBrowseResults(q);
  }
}
/* 命中判定：一次扫描给出「命中在哪 + 命中有多强」。
   kind: word（词形）/ num（编号）/ sense（释义）/ ex（仅例句）
   rank 越小越靠前 —— 词形全等 > 词形前缀 > 词形包含 > 编号 > 释义 > 例句。
   q 须已 trim + lowercase（调用方保证）。 */
function searchHit(w, q) {
  const word = w.word.toLowerCase();
  if (word === q) return { rank: 0, kind: 'word', text: w.word };
  if (word.startsWith(q)) return { rank: 1, kind: 'word', text: w.word };
  if (word.includes(q)) return { rank: 2, kind: 'word', text: w.word };
  if (String(w.num) === q) return { rank: 3, kind: 'num', text: w.word };
  for (const s of w.senses) if (s.toLowerCase().includes(q)) return { rank: 4, kind: 'sense', text: s };
  for (const e of exOf(w)) {
    if (e.en.toLowerCase().includes(q)) return { rank: 5, kind: 'ex', text: e.en };
    if (e.zh.includes(q)) return { rank: 6, kind: 'ex', text: e.zh };
  }
  return null;
}
/* 例句片段：以命中处为中心裁一段，让「为什么这条会命中」直接看得见，
   而不是只给一枚「例」徽标让人猜（例句命中的词，释义里根本没有那个词）。 */
function snip(text, q, span) {
  const i = text.toLowerCase().indexOf(q);
  if (i < 0) return text;
  const sp = span || 44;
  const start = Math.max(0, i - sp), end = Math.min(text.length, i + q.length + sp);
  return (start > 0 ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : '');
}
/* 一条结果：上行是词形与标签，下行是「命中处」——
   释义命中就显示**那条**释义，例句命中就显示例句片段（都带高亮）。
   旧版只显示 senses[0]：命中在第 2 条释义或只在例句里的词，显示出来的却是
   没命中的第一条释义，看着像误报。 */
function srRow(w, h, i) {
  const q = srQuery;
  const ex = h && h.kind === 'ex';
  let body;
  if (!h) body = `<span class="m">${esc(w.senses[0])}${w.senses.length > 1 ? ' …' : ''}</span>`;
  else if (h.kind === 'sense') body = `<span class="m">${markHl(h.text, q)}${w.senses.length > 1 ? ' …' : ''}</span>`;
  else if (h.kind === 'ex') body = `<span class="m sr-x">${markHl(snip(h.text, q), q)}</span>`;
  else body = `<span class="m">${markHl(w.senses[0], q)}${w.senses.length > 1 ? ' …' : ''}</span>`;
  return `<div class="sr-item" id="srOpt${i}" data-num="${w.num}" data-i="${i}" role="option" aria-selected="false">
    <span class="sr-top">
      <span class="w">${markHl(w.word, q)}</span>
      ${w.pos ? `<span class="tag-pos sr-pos">${esc(w.pos)}</span>` : ''}
      ${ex ? '<span class="tag-ex sr-ex" title="仅在例句中匹配">例</span>' : ''}
      <span class="n">${h && h.kind === 'num' ? markHl('#' + w.num, q) : '#' + w.num}</span>
    </span>
    ${body}</div>`;
}
function bindSr() {
  $$('.sr-item', srBox).forEach(el => {
    el.onmouseenter = () => { srIdx = +el.dataset.i; markSel(); };
    el.onclick = () => { closeSearch(); openWordModal(+el.dataset.num); };
  });
  markSel();
}
/* 组合框的展开状态（结果列表出现时为 true，空态/关闭时为 false） */
function setSrExpanded(on) {
  si.setAttribute('aria-expanded', on ? 'true' : 'false');
  if (!on) si.removeAttribute('aria-activedescendant');
}
/* 结果条数播报：读屏用户听得到「搜到几条」，不必自己数。
   播报位就是右下角那个可见的计数（#searchCount 带 aria-live）——
   另设一个视觉隐藏的播报位反而会被「静默截断」守卫判成文字被裁
   （隐藏位就是 1px 宽 + overflow:hidden，文字必然溢出）。 */
/* 「在词库中查看全部」：把关键词带进词库页（那里能翻页、能按学习状态筛），
   并清掉词库里残留的筛选条件 —— 否则用户看到结果比浮层里还少，
   却不知道是旧筛选条件还在生效。 */
function gotoBrowseResults(q) {
  browse.q = q; browse.favQ = ''; browse.letter = ''; browse.pos = '';
  browse.core = ''; browse.sub = ''; browse.reg = ''; browse.status = ''; browse.page = 1; browse.favPage = 1;
  closeSearch();
  if (location.hash === '#browse') renderView('browse'); else location.hash = '#browse';
}
/* 选中项用 aria-activedescendant 同步给输入框（组合框的标准做法，焦点始终留在输入框） */
function markSel() {
  $$('.sr-item', sr).forEach(el => {
    const on = +el.dataset.i === srIdx;
    el.classList.toggle('sel', on);
    el.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  if (srIdx >= 0 && srList[srIdx]) {
    si.setAttribute('aria-activedescendant', 'srOpt' + srIdx);
    // 结果区 max-height 52vh 可滚：连按 ↓ 选出第 12 条时高亮会滚出可视区，
    // 键盘用户看不到当前选中项。block:nearest 只动容器不动页面
    const el = $('#srOpt' + srIdx, srBox);
    if (el) el.scrollIntoView({ block: 'nearest' });
  } else si.removeAttribute('aria-activedescendant');
}
si.oninput = debounce(doSearch, 120);   // 全库扫描 + 重建结果列表，与词库搜索框一致做防抖
/* 防抖尚未触发时（用户打完字就按 Enter/↓），srList 还是上一次的——甚至是
   空查询时的随机推荐。这时按 Enter 会打开一个与输入毫不相干的词（实测：
   输 "crucial" 后 120ms 内按 Enter，打开的是推荐位里的 "transient"）；
   若上一次查询无结果，srList 为空，Enter 更是**什么都不做**，输入被静默丢弃。
   动作前先把结果同步到当前输入值。 */
function syncSearch() {
  const q = si.value.trim().toLowerCase();
  if (q !== srQuery) doSearch();
}
$('#searchCount').textContent = `全库 ${WORDS_MAX} 词`;

/* ---------------------------- 路由 ---------------------------- */
/* 「分类」页已并入词库（词性分组视图 + 感情色彩筛选），不再是一个独立视图；
   「学习」「测验」两页已合并为「学习」一页（页内分段切换），也不再各占一个视图 */
const VIEWS = ['home', 'browse', 'study', 'fav', 'stats', 'settings'];
/* 浏览器标签页标题随页面切换（多开标签时一眼能认出哪个是词库/哪个是统计）
   口径：站名在前、页面名在后 —— 「GUAN 学术英语词汇库 · 词库」 */
const TAB_LABEL = { home: '首页', browse: '词库', study: '学习',
  fav: '收藏', stats: '统计', settings: '设置' };
const BASE_TITLE = document.title;
function renderView(name) {
  const prev = current;
  current = name;
  /* 听音辨词的自动重播定时器（150ms 后朗读本题单词）必须在**每次**切页时掐掉：
     此前只在 renderQuizQuestion 与 views.quiz 里清，切到词库/收藏/分类时
     那个定时器还活着 → 在新页面上把上一题念出来（150ms 的窗口，人手不易复现，
     但控制流上确实漏了）。views.quiz 会在本行之后重出题并另起一个定时器，
     不受影响。 */
  clearTimeout(quizReplayT);
  /* 首页不挂页面名：站名本身就是这一页的身份，标签页上再写一遍「首页」是废话 */
  document.title = (name === 'home') ? BASE_TITLE
    : BASE_TITLE + ' · ' + TAB_LABEL[name];
  document.body.dataset.view = name;
  $$('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.view === name);
    // 高亮靠 class 承载，屏幕阅读器读不到；当前页补 aria-current 让语义也到位
    if (a.dataset.view === name) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  const root = $('#main');
  // 切页淡入微动效：remove → 强制回流 → 重加，只在真正换视图时触发（同视图重渲染不打断）
  if (prev !== name) { root.classList.remove('view-enter'); void root.offsetWidth; root.classList.add('view-enter'); }
  // prev 一并传给视图：区分「换页进入」与「同页重渲染」（如收藏里点收藏）
  (views[name] || views.home)(root, prev);

  // 换页时回到顶部，否则会停在上一个页面的滚动位置（页面内容已换，位置却留着）；
  // 同页重渲染（rerenderIfBrowse 会自己恢复滚动位置）不能滚，否则收藏里
  // 点一下收藏就从第 3 页被拽回第 1 页顶部
  if (prev !== name) window.scrollTo(0, 0);
}
function route() {
  const h = location.hash.replace('#', '') || 'home';
  let v = VIEWS.includes(h) ? h : 'home';
  /* 旧链接 #cats（原「分类」页）不作废：并到词库并给一次分组视图，
     别人分享出去的地址仍能落到对应的内容上。groupOnce 只影响这一次渲染，
     不改用户自己选的视图状态。 */
  if (h === 'cats') { v = 'browse'; browse.groupOnce = true; }
  /* 旧链接 #cards / #quiz（合并前的「学习」「测验」页）落到合并后的「学习」页，
     并直接切到对应的模式：#cards → 翻卡学习，#quiz → 测验。
     别人分享出去的旧地址、以及用户书签里的收藏，都还能落到对应的内容上。 */
  if (h === 'cards') { v = 'study'; studyTab = 'flashcards'; }
  if (h === 'quiz')  { v = 'study'; studyTab = 'quiz'; }
  // 未知 hash 渲染了首页但地址栏仍留坏值：刷新、收藏、分享出去还是 404 感。
  // replaceState 归一化且不多塞一条历史；个别环境（如 file:// 旧浏览器）会抛，退直接改 hash
  if (v !== h) { try { history.replaceState(null, '', '#' + v); } catch { location.hash = v; } }
  renderView(v);
}
window.addEventListener('hashchange', route);
/* 视口变宽变窄时，卡背的可用宽度变了 ⇒ 内容高度也变（例句换行数不同），
   卡高要重算，否则窄一点的窗口里内容会被卡底截掉。 */
let fcFitT = 0;
window.addEventListener('resize', () => {
  if (!fc.flipped || !$('#flipCard')) return;
  clearTimeout(fcFitT);
  fcFitT = setTimeout(fitCardHeight, 120);
});
/* 顶栏导航**再点一次当前页**：把同一段 hash 赋回去不会触发 hashchange，
   路由根本不跑 —— 而学习/测验的结束面板是就地渲染的（finishSession / quizResult
   直接写 #main，不经过 renderView），此时点顶栏「学习」「测验」看着像没反应，
   页面停在结束面板上出不来。这里补一次同页重画。 */
$$('.nav-item').forEach(a => a.addEventListener('click', e => {
  const v = a.dataset.view;
  if (location.hash.replace('#', '') !== v) return;   // 换页仍交给 hashchange
  e.preventDefault();
  renderView(v);
}));

/* ---------------------------- 全局键盘 ---------------------------- */
const scOv = $('#shortcutsOverlay');
function openShortcuts() {
  rememberFocus(scOv);
  scOv.hidden = false; $('#shortcutsGrid').innerHTML = renderShortcuts();
  $('#scClose').focus();
}
function closeShortcuts() {
  if (scOv.hidden) return;
  scOv.hidden = true;
  restoreFocus(scOv, '#main');
}
$('#scClose').onclick = closeShortcuts;
scOv.addEventListener('click', e => { if (e.target === scOv) closeShortcuts(); });
scOv.addEventListener('keydown', e => trapTab(scOv, e));
/* 顶栏的「键盘快捷键」按钮已下线（与设置页「键盘快捷键」一节重复）：
   快捷键面板只剩「?」一个入口，内容以设置页那份为准。 */

document.addEventListener('keydown', e => {
  // 输入法合成中一律让路：拼音候选里按 Esc 是「取消候选」而不是「关弹层」，
  // 按 Enter 是「上屏」而不是「打开第一条结果」；字母键是拼音，也不能当快捷键。
  // （此前注释误以为浏览器自带保护——实际 Chrome/Firefox 都会把合成中的
  //   Esc/Enter/字母原样派发给页面，只是带 isComposing=true）
  if (e.isComposing) return;
  if (e.key === 'Escape') {
    /* 只收**最上层**浮层：三层可叠着开（弹窗上按 / 开搜索、按 ? 开帮助——
       z 序帮助 140 > 搜索 130 > 弹窗 120）。此前一条 Esc 把三层全关：
       用户想收的是眼前这一层，底下没打算关的弹窗也一起没了（二百零一轮）。
       每层收起时各自 restoreFocus，焦点逐层归还，链路不变。 */
    if (!scOv.hidden) { closeShortcuts(); return; }
    if (!so.hidden) { closeSearch(); return; }
    closeWordModal();
    return;
  }
  // 带修饰键的组合交给浏览器/系统：学习会话里 Ctrl+S 不应同时切换收藏、
  // Cmd+P 不应同时触发朗读
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const inField = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || '');
  // 焦点在按钮/链接上时，Enter/Space 应交给原生激活（如评分钮、下一题钮），全局翻页/翻面逻辑要让路
  const onAct = /^(BUTTON|A|SUMMARY)$/.test(document.activeElement?.tagName || '');
  if (!so.hidden) {
    if (e.key === 'Tab') { trapTab(so, e); return; }
    if (e.key === 'ArrowDown') { syncSearch(); srIdx = Math.min(srList.length - 1, srIdx + 1); markSel(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { syncSearch(); srIdx = Math.max(0, srIdx - 1); markSel(); e.preventDefault(); }
    else if (e.key === 'Enter') { syncSearch(); const t = srList[srIdx] || srList[0]; if (t) { closeSearch(); openWordModal(t.num); } e.preventDefault(); }
    return;
  }
  // 「?」是开关：帮助面板开着时再按一次就收起
  if (e.key === '?' && !inField) { scOv.hidden ? openShortcuts() : closeShortcuts(); e.preventDefault(); return; }
  if (!scOv.hidden) return;
  if (e.key === '/' && !inField) { openSearch(); e.preventDefault(); return; }
  // 词条弹窗：上下翻阅
  if (!$('#wordModal').hidden) {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const list = modalContextList();
      const idx = list.findIndex(x => x.num === wmNum);
      /* 当前词条不在上下文列表里时（词库页按字母过滤时从全局搜索打开的词、
         收藏里打开的非收藏词），弹窗中的「上一条/下一条」按钮是禁用的
         （openWordModal 里 idx=-1 ⇒ prevW/nextW 为空）。键盘必须与按钮一致：
         此前没有 idx>=0 的护栏，idx=-1 时 → 会取 list[0]，跳到一个与当前词
         毫无关系的词（实测：K 过滤下打开 crucial，按 → 跳到 knowledge）。 */
      if (idx < 0) { e.preventDefault(); return; }
      const nx = e.key === 'ArrowRight' ? list[idx + 1] : list[idx - 1];
      if (nx) { openWordModal(nx.num); e.preventDefault(); }
    }
    return;
  }
  // 学习快捷键（翻卡会话）。合并页上 fc.session 与 quiz.session 可同时非零
  // （翻卡中途切到测验开考，翻卡会话还挂着），谁在屏上谁说了算：以 studyTab 分流。
  if (current === 'study' && fc.session && studyTab === 'flashcards') {
    if (e.key === ' ' || e.key === 'Enter') { if (!inField && !onAct) { flip(); e.preventDefault(); } }
    else if (e.key.length === 1 && '123'.includes(e.key)) {
      /* 未翻面时鼠标点评分钮有 toast 提示（rate 里的 flipped 守卫），键盘按 1/2/3
         却被上面的 fc.flipped 条件静默吞掉——同样一个操作，键盘用户「按了没反应」。
         放行给 rate()，让它与鼠标共用同一条「先看释义再评分」提示（SC 2.5.3 一致性）。 */
      rate(+e.key - 1); e.preventDefault();
    }
    else if (e.key.toLowerCase() === 's') { toggleFav(fc.queue[fc.i].num); renderStage(); }
    else if (e.key.toLowerCase() === 'p') speak(fc.queue[fc.i].word);
    else if (e.key.toLowerCase() === 'u') { undoLast(); e.preventDefault(); }
    return;
  }
  // 测验快捷键
  if (current === 'study' && quiz.session && studyTab === 'quiz') {
    if (quiz.answered && (e.key === ' ' || e.key === 'Enter') && !inField && !onAct) { nextQuestion(); e.preventDefault(); return; }
    if (!quiz.answered && quiz.curMode !== 'spell' && !inField) {
      const k = e.key.toLowerCase();
      /* String.includes 是**子串**判定：key 为多字符（"12"、"ab"）时会误判成
         选项键，进而把单词记成「忘了」或点错选项。e.key 正常是单字符，
         这里再加一道长度闸把这一类彻底关掉。 */
      const n = (k.length === 1 && '1234'.includes(k)) ? +k - 1 : (k.length === 1 && 'abcd'.includes(k) ? 'abcd'.indexOf(k) : -1);
      if (n >= 0) { const b = $$('.quiz-opt')[n]; if (b) b.click(); e.preventDefault(); }
    }
    return;
  }
  // 词库翻页
  if ((current === 'browse' || current === 'fav') && !inField) {
    if (e.key === 'ArrowRight') { pageSet(pageNow() + 1); rerenderIfBrowse(); }
    if (e.key === 'ArrowLeft') { pageSet(Math.max(1, pageNow() - 1)); rerenderIfBrowse(); }
  }
});
so.addEventListener('click', e => { if (e.target === so) closeSearch(); });
$('#btnSearch').onclick = openSearch;
$('#btnTheme').onclick = () => {
  const order = ['light', 'dark'];
  state.settings.theme = order[(order.indexOf(state.settings.theme) + 1) % 2];
  save(); applyTheme(); toast('主题：' + { light: '浅色', dark: '深色' }[state.settings.theme]);
};
$('#brandHome').onclick = () => location.hash = '#home';
// 品牌区是 role="button"，键盘用户也要能触发（Enter / 空格）
$('#brandHome').onkeydown = e => {
  // 同上：止住冒泡，避免空格同时触发全局快捷键（如学习会话里的翻面）
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); location.hash = '#home'; }
};

/* 顶栏徽标：最近 30 天的访问次数（不是连胜天数）。
   页面每加载一次记一次访问，刷新页面同样计数；
   数字与 aria-label 同步更新，屏幕阅读器读到的是完整口径而不是裸数字。 */
function updateVisitPill() {
  const n = visitsInWindow();
  $('#visitCount').textContent = n;
  $('#visitPill').setAttribute('aria-label', '最近 30 天访问 ' + n + ' 次');
}

/* ---------------------------- 启动 ---------------------------- */
if ('MutationObserver' in window) {
  new MutationObserver(list => {
    for (const m of list) {
      if (m.type === 'characterData') fixTextNode(m.target);
      else m.addedNodes.forEach(fixIcons);
    }
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
}
fixIcons(document);
initTTS();
pruneState();          // 词表更新后清理已下架词条留下的进度与收藏
bumpVisit();           // 每次打开页面（含刷新）记一次访问：顶栏徽标显示最近 30 天的访问次数
applyTheme();
updateVisitPill();
route();

/* 调试/测试钩子：暴露几个纯渲染函数，方便零依赖冒烟测试直接检查输出 */
window.WL_DEBUG = { openWordModal, renderBrowseCards, renderPrintList, exOf, exBlock, sanitizeState,
  /* 快捷键浮层：顶栏按钮下线后只剩「?」一个入口，测试改走这两个钩子驱动 */
  openShortcuts, closeShortcuts,
  /* 第五十一轮扩充：cloze 出题链路与搜索/统计辅助，供零依赖冒烟测试直接驱动 */
  clozeSlot, wordMatchQ, tierCounts, optionTexts, MODES, quiz, renderQuizQuestion,
  /* 册四十六轮扩充：手动标记与进度读取，供零依赖冒烟测试直接驱动「不认识→未学习」语义 */
  setStatus, prog, isStarted, flip,
  /* 同义组：白名单名单 + 按当前规则算出的同源编号集合（供冒烟测试核对口径） */
  SYNONYM_GROUPS, excludeNums,
  /* 学习会话的内部态与渲染入口（供冒烟测试核对进度条口径、开卡后的行为） */
  fc, renderStage, startSession,
  /* 页内模式（翻卡 / 测验）与「换模式」按钮的绑定：供冒烟测试直接驱动
     「牌桌上点『测验』是否真的切到测验面板」——此前它只退出会话、studyTab 不变，
     按钮把人送回翻卡的设置页（源码级断言挡不住，行为级才挡得住）。 */
  get studyTab() { return studyTab; },
  set studyTab(v) { studyTab = v; },
  bindModeSwitchBtn, modeSwitchBtn,
  /* 连续学习天数：顶栏徽标已改为「最近 30 天访问次数」，连胜数改由首页的
     「连续学习」卡片显示——冒烟测试要核对「评分 ⇒ 连胜 +1」，
     这里把 streak() 一并开出来（它本来只在视图里被调用）。 */
  streak,
  /* 朗读口径守卫：speakCount 累计真正发起朗读的次数（供冒烟测试断言
     「打开弹窗不自动出声」「学习默认不自动播」）；pickState 供测试直接
     验证旧存档的自动朗读归一（speakVer 缺失 ⇒ autoSpeak 落回 false）。 */
  get speakCount() { return speakCount; },
  ttsStatus, canSpeakEnglish,
  pickState, DEFAULTS,
  /* state 用取值器而不是值快照：导入备份时 state 是**重新赋值**的，
     值快照会一直指向导入前的旧对象，读到的状态与运行时不符（假红/假绿都可能） */
  get state() { return state; },
  /* 分组视图的渲染入口：首页「按词性分组 N」入口已下线，计数口径改在
     分组视图自己的说明行里核对，冒烟测试需要能单独把这段 HTML 取出来。 */
  renderBrowseGroup };

})();
