#!/usr/bin/env node
/* ================= 零依赖 DOM 冒烟测试 =================
   在 Node 里用最小 DOM 桩加载 js/data.js + js/app.js，
   驱动各视图渲染并检查关键内容与数据契约。

   用途：在没有浏览器的环境里做快速回归（CI / 离线）。
   完整交互测试仍以 tools/smoke_test.py（Playwright）为准。

   运行： node tools/dom_smoke_test.js
   ===================================================== */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FAIL = [];
let passed = 0;

function ok(name, cond, extra) {
  if (cond) { passed++; console.log('  ✓ ' + name + (extra ? `  [${extra}]` : '')); }
  else { FAIL.push(name + (extra ? ' ' + extra : '')); console.log('  ✗ ' + name + (extra ? `  [${extra}]` : '')); }
}
function section(t) { console.log('\n== ' + t + ' =='); }

/* ------------------------------ 最小 DOM 桩 ------------------------------ */
class ClassList {
  constructor(el) { this.el = el; this.set = new Set(); }
  add(...c) { c.forEach(x => this.set.add(x)); }
  remove(...c) { c.forEach(x => this.set.delete(x)); }
  toggle(c, on) { const has = this.set.has(c); const want = on === undefined ? !has : !!on;
                   if (want) this.set.add(c); else this.set.delete(c); return want; }
  contains(c) { return this.set.has(c); }
}

class El {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.style = {};
    this.dataset = {};
    this.attrs = {};
    this.classList = new ClassList(this);
    this.hidden = false;
    this.disabled = false;
    this.value = '';
    this.textContent = '';
    this._innerHTML = '';
    this.onclick = null; this.oninput = null; this.onchange = null; this.onkeydown = null;
  }
  get innerHTML() { return this._innerHTML; }
  set innerHTML(v) { this._innerHTML = String(v); this.children = []; }
  get firstChild() { return this.children[0] || null; }
  appendChild(c) { this.children.push(c); c.parentNode = this; return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  replaceChild(n, o) { const i = this.children.indexOf(o); if (i >= 0) this.children[i] = n; n.parentNode = this; return o; }
  setAttribute(k, v) { this.attrs[k] = v; }
  getAttribute(k) { return this.attrs[k]; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener() {}
  removeEventListener() {}
  getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0 }; }
  focus() {}
  click() { if (this.onclick) this.onclick({ target: this, stopPropagation() {}, preventDefault() {} }); }
  closest() { return null; }
  querySelector() { return new El('div'); }
  querySelectorAll() { return []; }
}

function makeDoc() {
  const doc = new El('#document');
  doc.documentElement = new El('html');
  doc.body = new El('body');
  doc.body.dataset = {};
  doc.createElement = tag => new El(tag);
  doc.createDocumentFragment = () => new El('#fragment');
  doc.createTreeWalker = () => ({ nextNode: () => null });
  doc.addEventListener = () => {};
  doc.getElementById = id => { doc._ids[id] = doc._ids[id] || new El('div'); return doc._ids[id]; };
  doc._ids = {};
  doc.querySelector = sel => doc.getElementById(String(sel).replace(/^#/, ''));
  doc.querySelectorAll = () => [];
  return doc;
}

function makeStorage() {
  const m = new Map();
  return {
    get length() { return m.size; },
    key: i => Array.from(m.keys())[i] ?? null,
    getItem: k => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: k => m.delete(k),
    clear: () => m.clear(),
    _dump: () => Object.fromEntries(m),
  };
}

function makeLocation() {
  return { _hash: '', get hash() { return this._hash; }, set hash(v) { this._hash = v; } };
}

/* ------------------------------ 启动 ------------------------------ */
const doc = makeDoc();
const storage = makeStorage();
const loc = makeLocation();
const listeners = {};

const win = {
  document: doc,
  location: loc,
  localStorage: storage,
  addEventListener: (t, fn) => { (listeners[t] = listeners[t] || []).push(fn); },
  removeEventListener: () => {},
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  requestAnimationFrame: fn => setTimeout(fn, 0),
  scrollTo: () => {},
  scrollY: 0,
  innerWidth: 1280,
  devicePixelRatio: 1,
  getComputedStyle: () => ({ getPropertyValue: () => '' }),
  MutationObserver: class { observe() {} disconnect() {} },
  NodeFilter: { SHOW_TEXT: 4, SHOW_ELEMENT: 1 },
  URL: { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} },
  Blob: class { constructor(a) { this.parts = a; } },
  setTimeout, clearTimeout, setInterval, clearInterval,
  console, structuredClone, JSON, Math, Date, Object, Array, String, Number, Boolean, RegExp, Error,
};
win.window = win;
win.self = win;
win.globalThis = win;

// 让沙箱的全局对象就是 win 本身：
// 这样 data.js 里的 `window.WL_WORDS = ...` 会同时成为全局变量（与浏览器一致）
const sandbox = vm.createContext(win);

const errors = [];
function load(file) {
  const full = path.join(ROOT, file);
  if (!fs.existsSync(full)) { console.log(`  (skip ${file}: not generated yet)`); return; }
  const code = fs.readFileSync(full, 'utf8');
  try { vm.runInContext(code, sandbox, { filename: file }); }
  catch (e) { errors.push(`${file}: ${e && e.stack ? e.stack.split('\n').slice(0, 3).join(' | ') : e}`); }
}

load('js/data.js');
load('js/examples.js');
load('js/app.js');

const WORDS = sandbox.WL_WORDS || [];
const CATS = sandbox.WL_CATS || [];
const EXAMPLES = sandbox.WL_EXAMPLES || {};
const N = WORDS.length;
const NC = CATS.length;
// 纯介词 / 介词短语：词性索引面向实词，这些条目不参与分类（与 due to / via 同处理）
const NO_POS = new Set([
  'due to', 'owing to', 'via', 'regarding', 'onto',
  'despite', 'in accordance with', 'in conjunction with',
  'in light of', 'on the basis of', 'by means of', 'with regard to',
  // 第廿九轮新增介词性连接语块（同 due to 族处理，不进词性索引）
  // 册六十五轮词性校勘：such as（举例从属连词）与 on the one hand（篇章副词，
  // 与 on the other hand 对称）移出本族，理由见 CHANGELOG 一百四十三节
  'in addition to', 'according to', 'instead of', 'as a result of',
  'apart from', 'prior to', 'relative to', 'in contrast to',
  // 册卅八轮分类校勘：versus 系前置词（格指派用法），库无介词桶，随 due to/via 族置 null 不入词性索引
  'versus',
  // 册四十二轮分类校勘续：介词性支配语块误标副词（扫描器 pos_consistency_audit SUSPECT 三案，
  // 同构先例在册 with regard to/in light of/in accordance with 等），随族置 null 不入词性索引
  'in terms of', 'with respect to', 'compared with',
  // 册五十八轮词性域校勘：rather than 与白名单里的 instead of 同为介词性固定语块
  // （后接名词/动名词性成分，本库三条例句皆介词性用法），随族置 null 不入词性索引
  // 册六十五轮词性校勘：other than 同族（与 instead of / rather than 并列的排除语块）
  'rather than', 'other than',
  // 册六十二轮（词汇增补·连词专批）：学术写作常用的介词性固定语块，同族置 null 不入词性索引
  'in order to', 'in spite of', 'on behalf of', 'for the sake of',
  'at the expense of', 'in lieu of', 'by virtue of',
  // 册六十三轮（词汇增补·学术连接语块二批）：学术写作常用的介词性连接语块，同族置 null
  'so as to', 'with the exception of', 'subject to', 'on account of', 'by reason of',
  'in favor of', 'by reference to', 'with reference to', 'in the wake of',
  // 册六十四轮（词汇增补·日常高频连词批）：日常连接性介词语块，同族置 null
  // 册六十五轮词性校勘：for fear that / to the end that 引导从句，移出本族归连词
  'thanks to', 'because of',
  'with a view to', 'with the aim of',
  // 册六十五轮（词汇增补·日常连接词批三）：日常连接性介词语块，同族置 null
  'in the context of', 'in relation to', 'in connection with', 'aside from',
  'in place of', 'for the purpose of', 'for the purposes of', 'in pursuit of',
  'in the absence of',
  // 册六十六轮词性校勘：given（例句 2/3 为 Given+NP 介词性，连词职能由 given that
  // 承担）与 barring（例句 3/3 为 Barring+NP，=except for）同族置 null
  'given', 'barring',
  // 册六十七轮（词汇增补·连词与连接语块批）：介词性连接语块与单词介词，同族置 null
  'as for', 'as to', 'as opposed to', 'during', 'following', 'like',
  // 册六十九轮词性校勘：considering（例句 2/3 为 Considering+NP 介词性用法，
  // 连词职能由库内 considering that 承担），与 given / like 同族置 null
  'considering',
]);

section('load');
ok('no JS errors while loading', errors.length === 0, errors.slice(0, 2).join(' ;; '));
ok('WL_WORDS loaded', N > 0, String(N));
ok('WL_CATS loaded', NC > 0, String(NC));
ok('all words have a meaning', WORDS.every(w => w.senses && w.senses.length && w.senses[0].trim()));
ok('every word has 3 dictionary links', WORDS.every(w => w.links && w.links.length === 3));
ok('no sth/sb placeholders', !WORDS.some(w => /\bsth\b|\bsb\b/.test(w.word)));
ok('no duplicate words', new Set(WORDS.map(w => w.word.toLowerCase())).size === N);
ok('every word has a stable unique id', new Set(WORDS.map(w => w.num)).size === N);
ok('no question-style senses', !WORDS.some(w => w.senses.some(s => /[？?]\s*$/.test(s))));
ok('classified words all exist in main list',
   CATS.every(c => WORDS.some(w => w.num === c.num)));
ok('every word has a part of speech (except pure prepositions)',
   WORDS.filter(w => !w.pos).every(w => NO_POS.has(w.word)));
// 反向锁（第四十九轮）：白名单成员若补了词性或随删词失踪，此前没有任何断言能发现
ok('NO_POS members are still pos-null headwords',
   [...NO_POS].every(w => WORDS.some(x => x.word === w && !x.pos)));
ok('every classified word has a pos', WORDS.filter(w => w.pos).length === NC);
ok('core tier is a strict subset of the full list',
   WORDS.filter(w => w.core).length > 0 && WORDS.filter(w => w.core).length < N);
ok('core words are all classified',
   WORDS.filter(w => w.core).every(w => w.pos || NO_POS.has(w.word)));
// 册卅三轮核心层重建不变量：防分层回涨成「名义筛选」，防 noncore 段被后续
// 自动通道（新增词全入核）静默击穿——判据见 data/core_decisions.json 台账。
const _coreCnt = WORDS.filter(w => w.core).length;
ok('core tier stays below 85% of the list (real filter, not nominal)',
   _coreCnt / N < 0.85, 'ratio ' + (100 * _coreCnt / N).toFixed(1) + '%');
const _noncoreSeg = new Set((JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'curation.json'), 'utf8')).noncore || [])
   .map(x => String(x).trim().toLowerCase()));
const _segHits = WORDS.filter(w => _noncoreSeg.has(w.word.trim().toLowerCase()));
ok('curation noncore segment is fully effective in WORDS',
   _segHits.length === _noncoreSeg.size && _segHits.every(w => !w.core),
   'matched ' + _segHits.length + '/seg ' + _noncoreSeg.size +
   ', still-core ' + _segHits.filter(w => w.core).length);  // 五十六后记：失败信息补 matched/仍核数（口径与 42ae07 提案一致，逻辑零改动）
ok('adjectives carry a sentiment tag',
   CATS.filter(c => c.pos === '形容词').every(c => ['积极的', '消极的', '争议性的', '中性的'].includes(c.sub)));

/* 静态口径守卫：源码与文档里写死的词数/核心数/分类数必须与数据现算一致。
   这些字面量历史上每轮增补都会漂（页头「N 词（核心高频 M 个）」那行靠人肉记得改，
   第六十七轮就漏了一轮 ⇒ 页面署名数字与实际词库对不上）。此处把它变成断言：
   读 js/app.js 页头、index.html 的 meta description、README 首段的计数，
   逐个与 DOM 里的 WORDS/CATS 现算值对账。 */
{
  const appHead = fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8').slice(0, 600);
  const htmlSrc = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const readme = fs.readFileSync(path.join(ROOT, 'README.md'), 'utf8');
  const _nCore = WORDS.filter(w => w.core).length;
  // 页头行形如「学术英语词库：2009 词（核心高频 914 个），1945 词带词性分类、1498 词带感情色彩、2009 词带语体色彩」
  const _nSub = WORDS.filter(w => w.sub).length;
  const _nReg = WORDS.filter(w => w.reg).length;
  const headLine = (appHead.match(/学术英语词库：\d+ 词（核心高频 \d+ 个），\d+ 词带词性分类、\d+ 词带感情色彩、\d+ 词带语体色彩/) || [''])[0];
  ok('app.js header states the live word/core/classified counts',
     headLine === `学术英语词库：${N} 词（核心高频 ${_nCore} 个），${NC} 词带词性分类、${_nSub} 词带感情色彩、${_nReg} 词带语体色彩`,
     headLine || '页头口径行未找到');
  // meta description：「…：2009 词学术词库，含 914 个核心高频词…」
  const metaDesc = (htmlSrc.match(/<meta name="description" content="([^"]*)"/) || ['', ''])[1];
  ok('index.html meta description states the live word/core counts',
     metaDesc.includes(`${N} 词学术词库`) && metaDesc.includes(`${_nCore} 个核心高频词`),
     metaDesc.slice(0, 90));
  // README 首段：「当前词库 2009 词（核心高频 914 个），其中 1945 词带词性分类、1498 词带感情色彩、2009 词带语体色彩」
  const readmeLead = (readme.match(/当前词库 \d+ 词（核心高频 \d+ 个），其中 \d+ 词带词性分类、\d+ 词带感情色彩、\d+ 词带语体色彩/) || [''])[0];
  ok('README lead states the live word/core/classified counts',
     readmeLead === `当前词库 ${N} 词（核心高频 ${_nCore} 个），其中 ${NC} 词带词性分类、${_nSub} 词带感情色彩、${_nReg} 词带语体色彩`,
     readmeLead || 'README 首段口径未找到');
}

section('curation outcome');
const has = w => WORDS.some(x => x.word === w);
['crappy', 'vortex', 'perovskite', 'Greek', 'once upon a time', 'pico-', 'sketch']
  .forEach(w => ok(`removed: ${w}`, !has(w)));
['analysis', 'framework', 'hypothesis', 'evidence', 'although', 'nevertheless', 'consequently', 'method',
 'integrate', 'formulate', 'robust', 'coherent', 'empirical', 'thereby', 'respectively', 'whereas',
 'rationale', 'parameter', 'taxonomy', 'stakeholder', 'sustainability', 'by contrast', 'given that',
 'investigate', 'justify', 'substantiate', 'undermine', 'dataset', 'regression', 'significance',
 'reproducibility', 'baseline', 'in terms of', 'with respect to', 'on the other hand', 'to sum up',
 'establish', 'facilitate', 'comply', 'show', 'note', 'field', 'degree']
  .forEach(w => ok(`added: ${w}`, has(w)));
['agnostic', 'row', 'pin', 'stretch', 'deposit', 'mark', 'wrap', 'hint', 'intimate', 'glimpse',
 'nuisance', 'demise', 'ripple', 'typographical', 'obliged', 'sweep', 'sort of']
  .forEach(w => ok(`removed (round 3): ${w}`, !has(w)));
['remnant', 'ensuing', 'coarse', 'elastic', 'hereafter', 'henceforth', 'ab initio', 'preamble',
 'commute', 'lateral', 'specimen', 'interior', 'unwitting', 'defy', 'unimpeded', 'shroud',
 'contour', 'convex', 'just-in-time', 'millennium', 'deflect', 'renovate', 'back and forth',
 'reminiscent', 'jeopardize']
  .forEach(w => ok(`removed (round 4): ${w}`, !has(w)));
['imply', 'posit', 'converge', 'contextualize', 'stratify', 'impute', 'triangulate', 'saturate',
 'overestimate', 'underestimate', 'enforce', 'regress', 'convention', 'post hoc', 'power',
 'interpretation', 'imbalance', 'inverse', 'subset', 'skew', 'weight', 'algorithm', 'covariate',
 'stratum', 'effect', 'sampling', 'recruitment', 'dropout', 'attrition', 'ethics', 'anonymity',
 'interview', 'setting', 'confounding', 'mediating', 'moderating', 'norm', 'solely',
 'statistically', 'analytically', 'conceptually', 'evidently', 'ostensibly', 'seemingly']
  .forEach(w => ok(`added (round 4): ${w}`, has(w)));
['delicacy', 'derivation', 'fathom', 'ignite', 'infancy', 'inspiration', 'layman',
 'misgiving', 'systematize', 'thrive', 'vicinity']
  .forEach(w => ok(`removed (round 6): ${w}`, !has(w)));
['interviewer', 'measurement', 'percentage', 'frequency', 'exposure', 'risk', 'determinant',
 'mediator', 'moderator', 'replicability', 'generalizability', 'response', 'follow-up',
 'meta-analysis', 'disaggregate', 'multicollinearity', 'efficiency', 'deductive', 'inductive']
  .forEach(w => ok(`added (round 6): ${w}`, has(w)));
ok('round 6 gloss rewrite: "popularize"', has('popularize'));
['contribution','operationalization','confounder','falsify','mediation','moderation',
 'endogeneity','propensity','placebo','blinding','allocation','case-control','effect size',
 'mixed-method','cluster','panel','pooled','prospective','pragmatic','reflexivity',
 'positionality','critique','normative','interpretive','adoption','uptake','adherence',
 'dissemination','scalability','equity','bottleneck','alignment','overlap','milestone',
 'blueprint','tipping point']
  .forEach(w => ok(`added (round 7): ${w}`, has(w)));
ok('round 7 additions all carry a part of speech',
   ['contribution','confounder','placebo','adoption','equity','bottleneck']
     .every(w => { const e = WORDS.find(x => x.word === w); return e && e.pos; }));
// 第七轮：高频多义词释义精修 + 词性改判
[['approach', '名词'], ['view', '名词'], ['concern', '名词'], ['content', '名词'],
 ['measure', '动词']].forEach(([w, pos]) =>
  ok(`round 7 gloss/pos refinement: ${w}`, (WORDS.find(x => x.word === w) || {}).pos === pos));
ok('round 7 gloss rewrite: "approach" leads with the noun sense',
   (WORDS.find(x => x.word === 'approach') || {senses: []}).senses[0].startsWith('方法'));
ok('round 7 gloss rewrite: "content" leads with the noun sense',
   (WORDS.find(x => x.word === 'content') || {senses: []}).senses[0].startsWith('内容'));
ok('round 7 gloss rewrite: "issue" drops the non-academic senses',
   !(WORDS.find(x => x.word === 'issue') || {senses: []}).senses.some(s => s.includes('发行')));
// 第八轮：删 21 个低价值条目 + 补 30 个高频学术词 + 释义再校 21 条
['exotic','bizarre','startling','marvelous','plight','unruly','delve','modulate','postulate',
 'nomenclature','superfluous','innocuous','chaotic','lurk','dub','smoking gun','may as well',
 'in a nutshell','or so','at first sight','perplex']
  .forEach(w => ok(`removed (round 8): ${w}`, !has(w)));
['explicate','enumerate','discern','elicit','illuminate','preclude','surmount','undertake',
 'necessitate','alleviate','deviate','consolidate','conceptualization','quantification',
 'preregistration','disclosure','confidentiality','plagiarism','register','genre',
 'counterargument','cohesion','wording','triangulation','conceptual','multidisciplinary',
 'thematic','rhetorical','exploratory','influential']
  .forEach(w => ok(`added (round 8): ${w}`, has(w)));
ok('round 8 additions all carry a part of speech',
   ['explicate','conceptualization','thematic','triangulation']
     .every(w => { const e = WORDS.find(x => x.word === w); return e && e.pos; }));
ok('round 8 gloss refinement: "express" drops the non-academic sense',
   !(WORDS.find(x => x.word === 'express') || {senses: []}).senses.some(s => s.includes('快递')));
ok('round 8 gloss refinement: "subject" drops the grammar sense',
   !(WORDS.find(x => x.word === 'subject') || {senses: []}).senses.some(s => s.includes('主语')));
ok('round 8 gloss refinement: "scale" leads with the academic senses',
   (WORDS.find(x => x.word === 'scale') || {senses: []}).senses[0].startsWith('规模'));
ok('round 8 gloss refinement: "involve" drops "使参与"',
   !(WORDS.find(x => x.word === 'involve') || {senses: []}).senses.some(s => s.includes('使参与')));
// 分隔符约定："；" 分隔不同义项，"，" 分隔同一义项内的同义说法
ok('no sense has a duplicated separator ("；；" / "；，")',
   WORDS.every(w => w.senses.every(s => !/；[；，]|[，；]；|[；，]$|^[；，]/.test(s))));
ok('sense groups keep intra-sense synonym commas ("unprecedented")',
   (WORDS.find(w => w.word === 'unprecedented') || {senses: []}).senses.some(s => s.includes('，')));
ok('senses are separated by "；" across the list (e.g. "extensive")',
   (WORDS.find(w => w.word === 'extensive') || {senses: []}).senses
     .some(s => s.includes('；') && s.includes('，')));
ok('renamed: "attribute sth to sb" -> "attribute to"', has('attribute to'));
ok('renamed: "under no circumstance" -> "under no circumstances"', has('under no circumstances'));
ok('renamed: "cast/shed/throw light on sth" -> "cast light on"', has('cast light on'));
ok('spelling unified to American English',
   ['catalog', 'favor', 'fulfill', 'skepticism', 'analog'].every(has)
   && !['catalogue', 'favour', 'fulfil', 'scepticism', 'analogue'].some(has));
ok('no leftover slash-separated phrasal entries',
   !WORDS.some(w => /\//.test(w.word) && !/^[a-z]+$/.test(w.word)),
   WORDS.filter(w => /\//.test(w.word)).map(w => w.word).join(','));

section('state & persistence');
const KEY = 'wl_state_v1';
// 此前这两条都是「恒真/空过」断言：
//   ok('uses the documented localStorage key', storage.getItem(KEY) !== null || true)
//       ← `|| true` 直接短路，键名写错、根本没写盘，这条照样绿；
//   ok('legacy key "***" is migrated away', ...)
//       ← 键名还是错的：应用声明的旧键是 wl_state（见 app.js 的 LEGACY_KEYS），
//         库里根本没有 '***' 这个键，查它等于查了个不存在的东西。
// 现在改成真断言：应用必须把状态写到文档化的键上，且不写第二个键。
// save 是 120ms 防抖的，冒烟里等不到定时器，所以直接调它注册的 beforeunload 钩子
// （应用在 beforeunload 时是同步落盘的）。
const _saveHook = (listeners['beforeunload'] || [])[0];
ok('the app registers a beforeunload save hook', typeof _saveHook === 'function');
if (typeof _saveHook === 'function') {
  _saveHook();
  ok('the app writes its state under the documented key', storage.getItem(KEY) !== null);
  const _keys = Object.keys(storage._dump());
  ok('state is written under no key other than wl_state_v1',
     _keys.length === 1 && _keys[0] === KEY, _keys.join(','));
}

section('examples');
/* 粗略词干还原，用于校验例句里确实出现了目标词（不规则动词走白名单） */
const SUFFIXES = ['ations','ation','ies','ied','ing','ily','ally','s','es','ed','ly','er','est',
  'ion','ions','al','ment','ance','ence','ity','ous','ive','able','ible','ful','less','ist','ism',
  'ize','ise','y'];
const IRREGULAR = { arise: ['arose','arisen'], choose: ['chose','chosen'], grow: ['grew','grown'],
  bear: ['bore','borne'], bring: ['brought'], build: ['built'], become: ['became'],
  begin: ['began','begun'], hold: ['held'], lead: ['led'], make: ['made'], take: ['took','taken'],
  give: ['gave','given'], write: ['wrote','written'], find: ['found'], show: ['showed','shown'],
  fall: ['fell','fallen'], feel: ['felt'], keep: ['kept'], leave: ['left'], meet: ['met'],
  pay: ['paid'], say: ['said'], seek: ['sought'], sell: ['sold'], send: ['sent'], spend: ['spent'],
  stand: ['stood'], teach: ['taught'], think: ['thought'], understand: ['understood'],
  go: ['went','gone'], know: ['knew','known'], run: ['ran'], see: ['saw','seen'],
  speak: ['spoke','spoken'], break: ['broke','broken'], draw: ['drew','drawn'], fly: ['flew','flown'],
  rise: ['rose','risen'], throw: ['threw','thrown'], wear: ['wore','worn'], win: ['won'],
  undertake: ['undertook','undertaken','undertaking'], overcome: ['overcame','overcome'],
  withdraw: ['withdrew','withdrawn'], undergo: ['underwent','undergone'] };
function stem(w) {
  let s = String(w).toLowerCase();
  if (s.length <= 3) return s;
  for (const suf of SUFFIXES) {
    if (s.endsWith(suf) && s.length - suf.length >= 3) {
      s = s.slice(0, -suf.length);
      if (suf === 'ies' || suf === 'ied') s += 'y';
      break;
    }
  }
  if (s.length >= 3 && s[s.length - 1] === s[s.length - 2] && 'aeiousl'.indexOf(s[s.length - 1]) < 0) {
    s = s.slice(0, -1);
  }
  return s;
}
const PREFIXES = ['im', 'un', 'in', 'dis', 'non', 'mis', 'over', 'under', 'pre', 're',
  'sub', 'inter', 'anti', 'de', 'co', 'multi', 'semi', 'auto', 'micro'];
function formsOf(word) {
  const w = String(word).toLowerCase();
  const out = new Set([stem(w)]);
  for (const p of PREFIXES) {
    if (w.startsWith(p) && w.length - p.length >= 3) out.add(stem(w.slice(p.length)));
  }
  for (const f of (IRREGULAR[w] || [])) out.add(stem(f));
  return [...out];
}
function mentionsWord(sentence, head) {
  const toks = (String(sentence).toLowerCase().match(/[a-z]+/g) || []).flatMap(formsOf);
  const heads = (String(head).toLowerCase().match(/[a-z]+/g) || []).flatMap(formsOf);
  // 守卫诚实度（工装·第十轮）：headword 若是「完全没有字母」的词（如纯数字词），
  // 这里原来直接 return true ⇒ 「例句有没有用到词头」这一条**恒过**（空过）。
  // 改为 return false：判红、等人来修，而不是悄悄放过（当前词库 1428 词零命中此分支）。
  if (!heads.length) return false;
  return heads.some(h => toks.some(t => t === h ||
    (t.length >= 3 && h.length >= 3 && (t.startsWith(h) || h.startsWith(t)))));
}
ok('example file loaded', Object.keys(EXAMPLES).length > 0, String(Object.keys(EXAMPLES).length));
// 全库每词必须恰好 3 条例句（第七轮补齐后已恢复为 100% 覆盖的硬断言）
ok('every word that has examples has exactly 3',
   WORDS.every(w => !EXAMPLES[w.word] ||
     (Array.isArray(EXAMPLES[w.word]) && EXAMPLES[w.word].length === 3)),
   WORDS.filter(w => !(EXAMPLES[w.word] || []).length).slice(0, 5).map(w => w.word).join(','));
ok('every word has 3 examples',
   WORDS.every(w => Array.isArray(EXAMPLES[w.word]) && EXAMPLES[w.word].length === 3),
   WORDS.filter(w => (EXAMPLES[w.word] || []).length !== 3).slice(0, 5).map(w => w.word).join(','));
ok('every example has an English sentence and a Chinese translation',
   WORDS.every(w => (EXAMPLES[w.word] || []).every(e => e && e.en && e.zh)));
ok('every English example actually uses its headword',
   WORDS.every(w => (EXAMPLES[w.word] || []).every(e => mentionsWord(e.en, w.word))),
   WORDS.filter(w => (EXAMPLES[w.word] || []).some(e => !mentionsWord(e.en, w.word)))
     .slice(0, 5).map(w => w.word).join(','));
ok('no examples for unknown words',
   Object.keys(EXAMPLES).every(k => WORDS.some(w => w.word === k)),
   Object.keys(EXAMPLES).filter(k => !WORDS.some(w => w.word === k)).slice(0, 5).join(','));

section('rendering');
const DBG = sandbox.WL_DEBUG || {};
ok('app exposes its render helpers for testing', !!DBG.openWordModal);
if (DBG.openWordModal) {
  DBG.openWordModal(WORDS[0].num);
  const modalHTML = doc.getElementById('wordModalBody').innerHTML;
  ok('word modal lists example sentences', modalHTML.includes('wm-ex-en'));
  ok('word modal shows the Chinese translation', modalHTML.includes('wm-ex-zh'));
}

section('朗读口径：只有点了才读（不自动出声）');
{
  /* 用户直令：「不应该自动朗读，当点击后才朗读。严格控制住。」
     这类回归靠人耳听不出来 —— 打开弹窗时快到没察觉的一小声，等发现时已经
     过了好几轮。故用应用自报的 speakCount 做可测的断言。 */
  ok('app exposes a speak counter for the read-on-click policy',
     typeof DBG.speakCount === 'number', String(DBG.speakCount));

  /* ① 打开词条弹窗不得自动朗读（弹窗里另有「朗读」按钮，点了才读）。
     node 环境没有 speechSynthesis，speak() 会走 toast 分支，但仍会计数，
     所以计数断言对「有没有调用 speak」是有效的证据。 */
  if (DBG.openWordModal && typeof DBG.speakCount === 'number') {
    const before = DBG.speakCount;
    DBG.openWordModal(WORDS[1].num);
    ok('opening the word modal does not speak by itself',
       DBG.speakCount === before, `speakCount ${before} -> ${DBG.speakCount}`);
  }

  /* ② 闪卡自动朗读默认关：DEFAULTS 就是新装用户拿到的口径。 */
  ok('flashcard auto-speak is off by default',
     DBG.DEFAULTS && DBG.DEFAULTS.settings.autoSpeak === false,
     String(DBG.DEFAULTS && DBG.DEFAULTS.settings.autoSpeak));
  /* node 沙箱没有 speechSynthesis：这里不仅要不发声，还要把状态报成
     unsupported（而不是 no-english-voice），两种降级提示不能混。 */
  ok('speech status distinguishes an unsupported browser',
     DBG.ttsStatus() === 'unsupported' && DBG.canSpeakEnglish() === false,
     String(DBG.ttsStatus()));

  /* ③ 存量存档归一：旧版本里 autoSpeak 默认就是 true，绝大多数老存档都写着
     true（那是旧默认值，不是谁主动点过「开」）。升级后必须落回 false，
     否则这次收敛对老用户等于没生效。判据是「源存档有没有 speakVer 字段」。 */
  if (typeof DBG.pickState === 'function') {
    const legacy = DBG.pickState({ settings: { autoSpeak: true } });
    ok('a legacy archive (no speakVer) has its auto-speak forced off',
       legacy.settings.autoSpeak === false && legacy.speakVer === 1,
       `autoSpeak=${legacy.settings.autoSpeak} speakVer=${legacy.speakVer}`);
    const normalized = DBG.pickState({ speakVer: 1, settings: { autoSpeak: true } });
    ok('an already-normalized archive keeps the user\'s own auto-speak choice',
       normalized.settings.autoSpeak === true, String(normalized.settings.autoSpeak));
    const fresh = DBG.pickState(null);
    ok('a fresh archive starts with auto-speak off',
       fresh.settings.autoSpeak === false, String(fresh.settings.autoSpeak));
  }

  /* ④ 例句不做朗读功能：例句块里不得出现任何朗读控件。 */
  if (typeof DBG.exBlock === 'function') {
    const exHTML = DBG.exBlock(WORDS[0], { max: 3 });
    ok('example sentences carry no read-aloud control',
       !/speak|朗读|mini-btn|speak-btn/i.test(exHTML),
       (exHTML.match(/speak|朗读/gi) || []).join(','));
  }
}

if (DBG.renderBrowseCards) {
  const cardsHTML = DBG.renderBrowseCards();
  ok('browse cards show an example sentence', cardsHTML.includes('wc-ex-en'));
}
// 上面两个 render 助手此前是「有就跑、没有就悄悄跳过」——助手一旦改名/删除，
// 这两条断言就无声消失、套件照样全绿。这里补上「助手必须在」的前置断言。
ok('app exposes renderBrowseCards for testing', typeof DBG.renderBrowseCards === 'function');
ok('app exposes renderPrintList for testing', typeof DBG.renderPrintList === 'function');
if (DBG.renderPrintList) {
  DBG.renderPrintList(WORDS.slice(0, 5));
  const printHTML = doc.getElementById('printList').innerHTML;
  ok('print list includes example sentences', printHTML.includes('pl-ex-en'));
  ok('print list includes the Chinese translation', printHTML.includes('pl-ex-zh'));
}
ok('flashcard back shows an example sentence',
   fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8').includes("cls: 'fc-ex'"));
ok('the example bundle is loaded by the page',
   fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').includes('js/examples.js'));
const main = doc.getElementById('main');
function render(hash) {
  loc.hash = hash;
  (listeners['hashchange'] || []).forEach(fn => fn());
}
render('#browse');
const browseHTML = main.innerHTML;
ok('browse renders a word table', browseHTML.includes('word-table'));
ok('browse shows the live word count', browseHTML.includes(`共匹配 <b>${N}</b> 词`));
ok('browse does not hardcode a stale count', !browseHTML.includes('799 词'));
// 排序入口必须是真按钮（键盘可达、原生 Enter/空格激活），状态列也在其列
ok('all three sortable headers expose real buttons incl. status',
   // [^>]* ：aria-sort 与按钮之间允许再挂别的属性（如编号列的口径说明 title）
   ['num', 'word', 'lv'].every(k => new RegExp(`aria-sort="(none|ascending|descending)"[^>]*><button type="button" class="th-sort" data-k="${k}">`).test(browseHTML)));
// DOM 桩不解析 innerHTML，分页钮是 bind 阶段注入的，这里只能验容器；
// 「当前页 aria-current」的真实断言在 smoke_test_extra.py（浏览器里跑）
ok('pager container is rendered for multi-page results', browseHTML.includes('id="browsePager"'));
ok('browse offers the core-word filter', browseHTML.includes('核心'));
ok('browse pos chips are complete',
   ['形容词', '副词', '动词', '名词', '连词'].every(p => browseHTML.includes(`data-pos="${p}"`)));
// 「其他」＝那批没有实义词性标签的词（单词介词与介词短语），归在「词性」行末尾；
// 展示名是「介词」而不是「其他」——旧文案说「不设词性的介词」，
// 读起来像这批词没有词性，其实只是本库不设「介词」类（册六十八轮改名）。
// 「核心」不是词性（它跨五种词性），故另起一行「是否核心」（是 / 否），两层正交。
ok('pos-less words get an 其他 chip in the pos row',
   browseHTML.includes('data-pos="其他"')
   && !browseHTML.includes('data-pos="核心"')
   && WORDS.filter(w => !w.pos).length > 0);
// 只看**那枚 chip 自己**（含它自己的 title），不要扫整页：
// 「固定语块」这类词会出现在别的行的说明文字里（语体色彩「书面语」的提示
// 就写着「正式连接词、文雅词与固定语块」）——整页扫会把无关文案误判成
// 「这枚 chip 的旧文案没改干净」。判据取自该 chip 的 data-pos="其他" 那一段。
{
  const _posOtherChip = (browseHTML.match(/<button[^>]*data-pos="其他"[\s\S]*?<\/button>/) || [''])[0];
  ok('that chip is labelled 介词 (not a bare 其他, not 介词 / 介词短语)',
     _posOtherChip !== ''
     && />介词 <span class="cnt"/.test(_posOtherChip)
     && !_posOtherChip.includes('介词 / 介词短语')
     && !_posOtherChip.includes('不设词性')
     && !_posOtherChip.includes('固定语块'));
}
ok('core tier has its own 是否核心 row, orthogonal to the pos row',
   browseHTML.includes('id="coreFilter"')
   && browseHTML.includes('data-core="yes"')
   && browseHTML.includes('data-core="no"')
   && !browseHTML.includes('非词性'));
// 词条编号是「原号」而非连续序号（删词留号、增补自 800 起，故 1..1647 缺 219 号）：
// 表头若写「序号」并与「共 1428 词」并置，用户会以为漏词 —— 表头改名并带口径说明
ok('browse number column is labelled as the original entry number',
   browseHTML.includes('>原号') && !browseHTML.includes('>序号')
   && browseHTML.includes('删词留号'));

// 旧链接 #cats（原「分类」页）已并入词库：旧地址要能落到分组视图上，内容不丢
render('#cats');
const groupHTML = main.innerHTML;
ok('the legacy #cats link lands on the grouped browse view',
   groupHTML.includes('cat-section') && groupHTML.includes('词库浏览'));
// 分组视图现在把那批介词与介词短语也铺到末尾「介词」一节，
// 所以卡片数应等于全库词数，而不是只有带词性的那部分
ok('grouped view covers every word (classified + 介词)',
   (groupHTML.match(/class="cat-word"/g) || []).length === N,
   String((groupHTML.match(/class="cat-word"/g) || []).length));
ok('grouped view has an 其他 section for the pos-less words',
   groupHTML.includes('data-pos="其他"')
   && groupHTML.includes('📎 介词')
   && WORDS.filter(w => !w.pos).every(w => groupHTML.includes(`data-num="${w.num}"`)));
// 原来结尾的 `|| true` 把断言变成了永真式；改为真正校验每个已分类词条都以 data-num 出现
ok('grouped view lists every classified word', CATS.every(c => groupHTML.includes(`data-num="${c.num}"`)));
// 形容词分类的「本类闪卡」必须指向形容词牌组（adj），不能是核心高频词（picked）
ok('adjective section opens the adjective deck', groupHTML.includes('data-catdeck="adj"'));
ok('no category section falls back to the core-word deck', !groupHTML.includes('data-catdeck="picked"'));
// 分组视图并入词库后，词库页自带第三种视图与「感情色彩」筛选项
render('#browse');
const browseGroupHTML = main.innerHTML;
ok('browse offers the grouped view toggle', browseGroupHTML.includes('data-v="group"'));
ok('browse offers the sentiment-colour filter',
   browseGroupHTML.includes('id="subFilter"')
   && ['积极的', '消极的', '争议性的', '中性的'].every(s => browseGroupHTML.includes(`data-sub="${s}"`)));
ok('browse offers the register-colour filter',
   browseGroupHTML.includes('id="regFilter"')
   && ['学术术语', '书面语', '口语', '中性'].every(r => browseGroupHTML.includes(`data-reg="${r}"`)));
// 筛选区改成面板后，每一排都要有**可见标签**说明「这一排筛的是什么」
// （此前只有感情色彩那一排带标签，词性与首字母两排的「全部」按钮分属不同维度，
//  用户只能猜哪个是哪个）；面板本身有「筛选」标题，且感情色彩排必须有「不限」选项
ok('every filter row carries a visible label',
   browseGroupHTML.includes('filter-panel-title">筛选<')
   && ['词性', '感情色彩', '语体色彩', '首字母'].every(l => browseGroupHTML.includes(`filter-label">${l}<`)));
ok('the sentiment filter offers an unfiltered option',
   browseGroupHTML.includes('data-sub="">不限'));
// 筛选面板的**每一个**选项都要带数量：此前只有「介词」「是/否」和首字母字母有，
// 词性五档、是否核心的「不限」、感情色彩四档、首字母「全部」都没数 —— 用户点之前
// 不知道会剩多少词。现在每一档都带 data-fcnt="维度|取值" + 数字。
{
  const panel = browseGroupHTML.slice(browseGroupHTML.indexOf('id="posFilter"'),
                                      browseGroupHTML.indexOf('id="browseTable"'));
  const chips = panel.match(/<button class="chip[^"]*"[^>]*data-(pos|core|sub|reg)="[^"]*"/g) || [];
  const counts = panel.match(/data-fcnt="(pos|core|sub|reg)\|/g) || [];
  ok('every filter chip carries a count',
     chips.length > 0 && counts.length === chips.length,
     `chips=${chips.length} counts=${counts.length}`);
  const letters = panel.match(/<small data-fcnt="letter\|/g) || [];
  ok('every letter button carries a count (incl. 全部)',
     letters.length === 27, `letters=${letters.length}`);
  ok('the status dropdown carries counts too',
     (browseGroupHTML.match(/data-fcnt="status\|/g) || []).length === 6);
}
// 每一维的各档之和必须等于该维的「不限」条数 —— 加起来对不上就说明有词在这一层够不着。
// 感情色彩此前正是这样：本库只给 438 个形容词标注褒贬色彩，其余 1571 词在这一维上
// 没有任何入口（点遍积极/消极/中性也拼不出全量）。现补一档「其他」（未标注）兜住差额。
{
  // 从面板 HTML 里取每个 data-fcnt="维度|取值" 的数字（面板未受其它筛选影响时即为全库口径）
  const fcnt = {};
  for (const m of browseGroupHTML.matchAll(/data-fcnt="([a-z]+)\|([^"]*)"[^>]*>(\d+)</g)) {
    fcnt[`${m[1]}|${m[2]}`] = Number(m[3]);
  }
  const sumOf = (dim, vals) => vals.reduce((a, v) => a + (fcnt[`${dim}|${v}`] || 0), 0);
  // 感情色彩：各档之和 = 不限。档名不写死：库里实际出现过的取值 ＋
  // 「未标注」（没有感情色彩标签的那一批）都要算进去。
  const _subVals = [...new Set(WORDS.map(w => w.sub).filter(Boolean)), '未标注'];
  ok('sentiment buckets sum to the unfiltered total',
     sumOf('sub', _subVals) === fcnt['sub|'],
     `sum=${sumOf('sub', _subVals)} unlimited=${fcnt['sub|']}`);
  // 语体色彩：各档之和 = 不限（全库每词都有值）。
  // 档名**不写死**：按库里实际出现过的语体色彩取值求和
  // （值集随内容轮次增减，写死档名会让断言在新增一档时假红）。
  const _regVals = [...new Set(WORDS.map(w => w.reg).filter(Boolean))];
  ok('register buckets sum to the unfiltered total',
     sumOf('reg', _regVals) === fcnt['reg|'],
     `sum=${sumOf('reg', _regVals)} unlimited=${fcnt['reg|']}`);
  // 词性：五档 + 介词（其他）之和 = 不限
  ok('part-of-speech buckets sum to the unfiltered total',
     sumOf('pos', ['形容词', '副词', '动词', '名词', '连词', '其他']) === fcnt['pos|'],
     `sum=${sumOf('pos', ['形容词', '副词', '动词', '名词', '连词', '其他'])} unlimited=${fcnt['pos|']}`);
  // 是否核心：是 + 否 = 不限
  ok('core buckets sum to the unfiltered total',
     sumOf('core', ['yes', 'no']) === fcnt['core|'],
     `sum=${sumOf('core', ['yes', 'no'])} unlimited=${fcnt['core|']}`);
  // 首字母：A..Z 全部字母之和 = 全部（每词都归到某个首字母）
  const letterSum = Object.keys(fcnt)
    .filter(k => k.startsWith('letter|') && k !== 'letter|')
    .reduce((a, k) => a + fcnt[k], 0);
  ok('first-letter buckets sum to the unfiltered total',
     letterSum === fcnt['letter|'], `sum=${letterSum} unlimited=${fcnt['letter|']}`);
  // 「其他」这一档必须真的兜住差额：未标注的词数 = 全库 − 带标签的词数
  const unlabeledN = WORDS.filter(w => !w.sub).length;
  ok('the sentiment 其他 bucket accounts for every unlabelled word',
     fcnt['sub|未标注'] === unlabeledN && unlabeledN > 0,
     `bucket=${fcnt['sub|未标注']} unlabeled=${unlabeledN}`);
}

render('#home');
const homeHTML = main.innerHTML;
ok('home renders the dashboard', homeHTML.includes('dash-stats'));
// 「词条 #799 详情」里的 #799 是**随机一词抽到的条目原号**（合法渲染，不是写死的词数）。
// 词库一变长就可能抽到原号 799/344 的词，旧写法会**假红**——
// 判「首页没写死旧词数」前先把这处合法数字抠掉，再查其余位置。
const homeNoWodNum = homeHTML.replace(/词条 #\d+/g, '词条 #N');
ok('home does not hardcode 799/344',
   !homeNoWodNum.includes('799') && !homeNoWodNum.includes('344'),
   '随机一词原号已豁免');
// 首页的「快捷入口」整块已下线（用户要求去掉）：首页不该再出现这个区块，
// 也不该再出现它带的三个入口（含「按词性分组 N」）。
ok('home no longer shows the quick-entry block',
   !homeHTML.includes('快捷入口') && !homeHTML.includes('quick-row') && !homeHTML.includes('quick-btn'));
// 分组视图的计数口径：**铺开的词数 + 「介词」一节的词数 = 全库**。
// 这个数以前挂在首页「按词性分组 N」入口上（入口下线后无处可查），
// 现在在分组视图自己的说明行里核对——「其中 N 词按词性与感情色彩分组，
// M 词为单词介词与介词性固定短语」。判据取说明行的完整文案，别裸扫数字。
{
  const gHTML = (DBG.renderBrowseGroup ? DBG.renderBrowseGroup('browse') : '');
  const gm = gHTML.match(/其中 <b>(\d+)<\/b> 词按词性与感情色彩分组，<b>(\d+)<\/b> 词为单词介词与介词性固定短语/);
  const grouped = WORDS.filter(w => w.pos).length;
  const others = WORDS.length - grouped;
  ok('the group view counts every word (grouped + 介词 = 全库)',
     !!gm && Number(gm[1]) === grouped && Number(gm[2]) === others,
     `grouped=${grouped} others=${others} total=${WORDS.length}`);
}
// 随机一词（第一百四十八轮）：口径从「每日一词·按日轮播」改为「每次打开/刷新随机抽一个」。
// 判据：①面板文案是「随机一词」而不是「每日一词」；②沙箱里没实现 sessionStorage 时
// 取词走当场抽签兜底、渲染不崩（词库非空必有词）。
ok('home shows the random-word panel (not the daily one)',
   homeHTML.includes('随机一词') && !homeHTML.includes('每日一词'));

render('#stats');
ok('stats view renders', main.innerHTML.includes('stats-grid'));
ok('stats heatmap has 120 cells', (main.innerHTML.match(/data-tip="/g) || []).length === 120,
   String((main.innerHTML.match(/data-tip="/g) || []).length));
/* 第五十一轮：热力图按周对齐（7 行×列＝周），补位格用 .heat-pad（不带 data-tip，
   上面 120 格口径不变）；月份标挂在 .ms 格上，data-m + --hr 供 CSS 提回顶行 */
{
  const statsHTML = main.innerHTML;
  const hf = new Date(); hf.setDate(hf.getDate() - 119);
  ok('heatmap week-align pads match first weekday',
     (statsHTML.match(/class="heat-pad"/g) || []).length === (hf.getDay() + 6) % 7,
     String((statsHTML.match(/class="heat-pad"/g) || []).length));
  ok('heatmap month cells carry label and row var',
     /class="heat(?: h[1-4])? ms" data-m="\d{1,2}月" style="--hr:[0-6](?:;--heat-lv:\d)?"/.test(statsHTML));
  const msN = (statsHTML.match(/ ms"/g) || []).length;
  ok('heatmap marks every month boundary in the window', msN >= 4 && msN <= 6, String(msN));
  ok('heatmap no longer emits inline month labels', !statsHTML.includes('heat-mlabel'));
  ok('stats offers the per-POS mastery stacked bars',
     statsHTML.includes('按词性掌握分布') && statsHTML.includes('class="stack-bar"'));
}
/* 月份标错层（--heat-lv）：相邻两个月份标必须一高一低，否则两列标签会叠成
   「7月8月」一坨（相邻列间距只有一格宽，同高必叠）。
   判据：把渲染出的 .ms 格的 --heat-lv 按出现顺序取出来，相邻两项必须不同。
   此前实现用「每天递增的计数器」取奇偶（mLabelN++ % 2），而月份标只挂在
   跨月那一格上 ⇒ 计数器是按天走的，落在同奇偶的两 个月照样同高
   （实测 2026-09/2026-10 同为 lv=0，标签仍叠）。正确口径是按**月份标个数**
   递增：只有真的挂了一个月份标时才 +1。 */
{
  const statsHTML = main.innerHTML;
  const lvSeq = [...statsHTML.matchAll(/class="heat(?: h[1-4])? ms" data-m="(\d{1,2})月" style="--hr:\d(?:;--heat-lv:(\d))?"/g)]
    .map(m => (m[2] === undefined ? null : Number(m[2])));
  if (lvSeq.length) {
    const sameAdj = lvSeq.filter((v, i) => i > 0 && v === lvSeq[i - 1]);
    ok('adjacent month labels are staggered to different heights',
       sameAdj.length === 0,
       'lv 序列 ' + lvSeq.join(',') + '｜同高相邻 ' + sameAdj.length + ' 对');
  } else {
    ok('adjacent month labels are staggered to different heights',
       false, '未渲染出 --heat-lv 的月份标（该特性在途？）');
  }
}
ok('stats summary forecasts the next 7 days', main.innerHTML.includes('未来 7 天将到期'));

/* 一百五十一轮：学习与测验两页合并为 #study 一页（页首分段切换）。
   旧 hash #quiz / #cards 由 route() 重定向到 #study 并切到对应模式，
   下面的驱动沿用旧 hash —— 顺带就把「旧链接不作废」这条口径也测了。 */
render('#quiz');
ok('legacy #quiz lands on the merged study page in quiz mode',
   main.innerHTML.includes('quiz-setup') && main.innerHTML.includes('studyModeSeg'),
   'merged study page');
ok('quiz does not hardcode 799/344', !main.innerHTML.includes('799') && !main.innerHTML.includes('344'));
// node 环境没有 speechSynthesis：设置页须说明「听音辨词」不可用并禁用该题型钮
ok('quiz setup flags listen mode when TTS is unavailable',
   main.innerHTML.includes('无法出题') && /data-m="listen"[^>]*disabled/.test(main.innerHTML));
/* 出题设置页：范围/题数/本次三排各带可见标签，并且「本次出什么」写在页面上 */
{
  const qh = main.innerHTML;
  ok('quiz setup labels every control row (题型/范围/题数/本次)',
     ['题型', '范围', '题数', '本次'].every(t => qh.includes(`>${t}</span>`)), '');
  ok('quiz setup states what this round will actually be',
     qh.includes('id="qSummary"') && /看词选义|混合题型/.test(qh), '');
  /* 「范围太小」的提示只能出现一次：提示挪到面板上方时若忘了删原来那份，
     同一句警告会在页面上出现两遍（源码级断言，挡这类改版回归）。 */
  ok('the range notice is rendered in one place only',
     (fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8').match(/quizNotice \?/g) || []).length === 1,
     String((fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8').match(/quizNotice \?/g) || []).length));
  /* 池子不够时：范围标 thin（弱化）、题数标 aria-disabled（选不了） */
  DBG.quiz.scope = 'fav';           // 收藏在本轮没有词 ⇒ 池子容量 0
  render('#quiz');
  const qh2 = main.innerHTML;
  ok('quiz setup marks a too-small scope as unavailable',
     /data-sc="fav"[^>]*class="[^"]*thin/.test(qh2) ||
     /class="[^"]*thin[^"]*"[^>]*data-sc="fav"/.test(qh2), '');
  ok('quiz setup disables question counts the pool cannot fill',
     (qh2.match(/data-c="\d+"[^>]*aria-disabled="true"/g) || []).length >= 1, '');
  DBG.quiz.scope = 'all';
  render('#quiz');
}

render('#cards');
ok('flashcard setup renders (legacy #cards lands on the merged page)',
   main.innerHTML.includes('deck-setup') && main.innerHTML.includes('studyModeSeg'));
ok('flashcard limit max is not hardcoded to 799', !main.innerHTML.includes('max="799"'));
// 「按词性复习」里要有形容词整档（adj），与副词/动词/名词/连词并列
ok('flashcard setup offers an adjective deck',
   main.innerHTML.includes(`形容词 ${WORDS.filter(w => w.pos === '形容词').length} 词`));
/* 合并页的模式分段：两个模式钮都在（aria-pressed 标选中态），当前在翻卡模式 */
{
  const seg = main.innerHTML.match(/<div class="seg study-modes"[^>]*>[\s\S]*?<\/div>/) || [''];
  ok('study page offers the flashcards/quiz mode switch',
     /data-m="flashcards"[^>]*aria-pressed="true"/.test(seg[0]) &&
     /data-m="quiz"[^>]*aria-pressed="false"/.test(seg[0]), seg[0].slice(0, 80));
}
/* 牌组卡：名字与词数分开 —— 标题里不夹带数字（此前「形容词 410 词」+「410 词」重复一次） */
{
  const ch = main.innerHTML;
  const adjN = WORDS.filter(w => w.pos === '形容词').length;
  /* 图标不能静默落空：svgFor 对未登记的名字返回空 SVG，视觉上是少一枚图标，
     却不产生 JS 异常（学习页「争议性的」曾引用不存在的 scale，所有行为测试全绿）。
     每张实际渲染的牌组 chip 都必须有 SVG 内容，不能只检查字面调用。 */
  const deckChips = ch.match(/<button class="chip deck-opt[\s\S]*?<\/button>/g) || [];
  ok('every rendered deck chip contains actual SVG artwork',
     deckChips.length >= 10 && deckChips.every(chip =>
       !/<svg\b[^>]*><\/svg>/.test(chip)),
     `deck chips=${deckChips.length} empty=${deckChips.filter(chip => /<svg\b[^>]*><\/svg>/.test(chip)).length}`);
  ok('no rendered SVG icon is empty in the study setup',
     !/<svg\b[^>]*><\/svg>/.test(ch), '');
  const seg = (ch.match(/data-s="adj"[\s\S]*?<\/button>/) || [''])[0];
  const t = (seg.match(/<span class="do-t">([\s\S]*?)<\/span>/) || [])[1] || '';
  const n = (seg.match(/<span class="do-n">([\s\S]*?)<\/span>/) || [])[1] || '';
  ok('deck card title carries the name only (count is not repeated)',
     t.replace(/<[^>]*>/g, '').trim() === '形容词' && n.trim() === adjN + ' 词',
     `title=${t.replace(/<[^>]*>/g, '').trim()} count=${n.trim()}`);
  ok('deck card keeps a full accessible name (name + count)',
     seg.includes(`aria-label="形容词 ${adjN} 词"`), '');
  /* 二百轮：开卡动作收拢到「本次」行唯一一颗「开始学习」；页首推荐条整条下线
     （推荐语义落进初始选中的 chip），页面上不再有第二个各自开卡的入口。 */
  ok('the recommendation banner is gone (no second start entry)',
     !ch.includes('study-hero') && !ch.includes('id="fcBest"'), '');
  ok('the study setup has exactly one primary start button',
     ch.includes('id="fcStart"') &&
     (ch.match(/btn primary big/g) || []).length === 1,
     `primary big buttons=${(ch.match(/btn primary big/g) || []).length}`);
  ok('study page labels every deck row (范围/词性/每次上限/本次)',
     ['范围', '词性', '每次上限', '本次'].every(t => ch.includes(`>${t}</span>`)), '');
  /* 一百五十七轮（学习页设计优化）：
     ① 牌组选项改 chip 流 —— 15 张大卡（范围 7 + 词性 8）撑到三屏高，
        新用户的空范围又占半屏。守卫：牌组选项是 chip（.chip.deck-opt），
        页面里不再有大栅格牌组卡（.deck-grid 不是 grid）。
     ② 空牌组写「0 词」而不是「暂无到期」：chip 内数字与有词的牌组对齐，
        空的原因放 title/aria-label（悬停与读屏能听到）。
     ③ 页首有「今日目标」条：今日已学 / 目标 / 还差几次。
     ④ 「每次上限」有 10/20/30/50 预设档位，不必手输数字。
     ⑤ 一百九十四轮（两步流）：范围/词性 chip 点一下**只选中**（aria-pressed +
        .on 高亮），面板底新增「本次」行——摘要（哪个范围 · 实际几张）+
        「开始学习」确认按钮。此前点 chip 立即开局，误点一颗牌桌就开了；
        「每次上限」改在开卡前完成，选择→确认与测验面板同构。 */
  {
    ok('deck options are chips, not large grid cards',
       (ch.match(/class="chip deck-opt/g) || []).length >= 8 &&
       !/<div class="deck-grid"[^>]*style="[^"]*grid/.test(ch),
       `deck-opt chips=${(ch.match(/class="chip deck-opt/g) || []).length}`);
    const emptySeg = (ch.match(/data-s="fav"[\s\S]*?<\/button>/) || [''])[0];
    ok('an empty deck shows a count in place (the reason goes to title/aria)',
       /<span class="do-n">0 词<\/span>/.test(emptySeg),
       (emptySeg.match(/<span class="do-n">([^<]*)<\/span>/) || [])[1] || '');
    ok('the study page states today\'s goal progress',
       ch.includes('study-today') && ch.includes('今日目标') && /还差|已完成/.test(ch), '');
    ok('the session limit offers one-tap presets',
       (ch.match(/class="chip limit-preset/g) || []).length >= 4 &&
       ch.includes('id="fcLimit"'), '');
    ok('every deck chip carries an aria-pressed state (select, not start)',
       (ch.match(/class="chip deck-opt/g) || []).length >= 8 &&
       (ch.match(/aria-pressed="(?:true|false)"/g) || []).length >= 8, '');
    ok('exactly one deck chip is selected on render',
       (ch.match(/class="chip deck-opt[^"]* on"/g) || []).length === 1,
       (ch.match(/class="chip deck-opt[^"]*"/g) || []).filter(c => c.includes(' on')).join(' | '));
    ok('the confirm row pairs a summary with a start button',
       ch.includes('id="fcSummary"') && ch.includes('id="fcStart"') &&
       /id="fcStart"[^>]*>[^<]*<svg[^>]*>[\s\S]*?开始学习/.test(ch.slice(Math.max(0, ch.indexOf('id="fcStart"') - 200)),
         ch.indexOf('id="fcStart"') + 300), '');
  }
  /* 进度条口径：与「第 N / M」逐字对上（位置 = (i+1)/total，不是 i/total） */
  if (DBG.fc && DBG.renderStage) {
    DBG.fc.queue = [WORDS[0], WORDS[1], WORDS[2], WORDS[3]];
    DBG.fc.i = 0; DBG.fc.total = 4; DBG.fc.session = 1; DBG.fc.flipped = false;
    DBG.fc.stats = { good: 0, mid: 0, bad: 0 };
    DBG.renderStage();
    ok('study progress bar shows the current card (1 of 4 → 25%)',
       /width:25%/.test(main.innerHTML), (main.innerHTML.match(/width:[\d.]+%/) || [''])[0]);
    DBG.fc.session = 0;
  }
  /* 「换模式」按钮必须真的换模式。
     此前翻卡牌桌上的那颗「测验」只调 quitSession()（清 fc.session 后重渲染），
     studyTab 仍是 'flashcards' —— 点它回到的是**翻卡的设置页**，测验压根没进去
     （实测：点它之后页面是 deck-setup 而非 quiz-setup，模式卡仍 flashcards 高亮）。
     这里驱动按钮本体，断言「翻卡 → 测验」与「测验 → 翻卡」两个方向都换到了对面面板。 */
  if (DBG.fc && DBG.bindModeSwitchBtn && DBG.renderStage) {
    /* 二百零四轮（牌桌层逻辑显性化）三件套：
       ① 未翻面时评分钮行挂 .fc-btns.pending（中性灰，语义色等翻面才点亮）；
          flip() 后摘除——flip() 不重渲染，摘挂必须在 flip() 里同步做。
       ② 会话计数条与评分钮同序（忘了 → 模糊 → 认识），两组三键一上一下同把尺子。
       ③ 「退出会话」说清后果（已评分保留、当前这张不计）。 */
    DBG.fc.queue = [WORDS[0], WORDS[1]];
    DBG.fc.i = 0; DBG.fc.total = 2; DBG.fc.session = 1; DBG.fc.flipped = false;
    DBG.fc.stats = { good: 0, mid: 0, bad: 0 };
    DBG.renderStage();
    ok('the rating row carries the pending state before flipping',
       /class="fc-btns pending"/.test(main.innerHTML), '');
    ok('the session counter strip matches the rating-row order (忘了/模糊/认识)',
       (() => {
         const strip = (main.innerHTML.match(/class="fc-session-strip"[\s\S]*?<\/div>/) || [''])[0];
         const items = (strip.match(/fcss-item (?:good|mid|bad)/g) || []);
         return items.join(',') === 'fcss-item bad,fcss-item mid,fcss-item good';
       })(), (main.innerHTML.match(/class="fc-session-strip"[\s\S]*?<\/div>/) || [''])[0].slice(0, 120));
    ok('the quit button states what happens to graded cards',
       /id="fcQuit"[^>]*title="已评分的卡片保留进度[^"]*"/.test(main.innerHTML), '');
    DBG.fc.flipped = true;
    DBG.renderStage();
    ok('the rating row drops the pending state once flipped',
       !/class="fc-btns pending"/.test(main.innerHTML) &&
       /class="fc-btns"/.test(main.innerHTML), '');
    DBG.fc.session = 0;
    const clickModeSwitch = () => {
      // 沙箱的 $ 走 document.querySelector('#id') → 取同一颗元素再点它
      const b = doc.getElementById('modeSwitchBtn');
      DBG.bindModeSwitchBtn();
      b.click();
    };
    DBG.fc.queue = [WORDS[0], WORDS[1]];
    DBG.fc.i = 0; DBG.fc.total = 2; DBG.fc.session = 1; DBG.fc.flipped = false;
    DBG.fc.stats = { good: 0, mid: 0, bad: 0 };
    DBG.studyTab = 'flashcards';
    DBG.renderStage();
    ok('the flashcard table offers a mode-switch button', !!doc.getElementById('modeSwitchBtn'));
    clickModeSwitch();
    ok('the mode switch on the flashcard table really switches to the quiz panel',
       DBG.studyTab === 'quiz' && main.innerHTML.includes('quiz-setup'),
       `studyTab=${DBG.studyTab} quizSetup=${main.innerHTML.includes('quiz-setup')}`);
    ok('the mode switch abandons the flashcard session',
       DBG.fc.session === 0, String(DBG.fc.session));
    /* 反向：测验答题页的「翻卡」应换到翻卡面板，并清掉测验会话 */
    DBG.studyTab = 'quiz';
    DBG.quiz.session = 1;
    clickModeSwitch();
    ok('the mode switch on the quiz page really switches to the flashcard panel',
       DBG.studyTab === 'flashcards' && main.innerHTML.includes('deck-setup'),
       `studyTab=${DBG.studyTab} deckSetup=${main.innerHTML.includes('deck-setup')}`);
    ok('the mode switch abandons the quiz session',
       DBG.quiz.session === 0, String(DBG.quiz.session));
  }
  /* 模式卡上的参数必须与页面上真正会发生的量同源：
     模式卡写「本次 N 张」，而「本次」行摘要写「「××」· 本次 M 张」——
     两处说的都是 fc.src 这个范围：N ＝ min(选中范围词数, 上限)，摘要同源。
     此前卡上写推荐牌组、按钮写另一处，选中范围一换两个数就打架。 */
  if (DBG.fc) {
    render('#cards');
    const mcTxt = (main.innerHTML.match(/id="mc-flashcards"[^>]*>([^<]*)</) || [])[1] || '';
    // syncLimit() 走 textContent（沙箱不会回写进 main），直接读那颗徽标元素
    const mcLive = doc.getElementById('mc-flashcards');
    ok('the flashcards mode card states the same card count as the confirm summary',
       !!mcLive && /本次 \d+ 张/.test(mcLive.textContent || ''),
       `card="${(mcLive && mcLive.textContent) || mcTxt}"`);
  }
  /* 一百八十轮：卡背摊开整条词条，右下角「词条详情」按钮下线。
     断言四件事：① 例句上限是 3 不是 1；② 卡背有词典链接与手动标记三钮；
     ③ 底栏不再有 fcDetail；④ 手动标记真的改记忆状态（行为级，不只查源码）。 */
  if (DBG.fc && DBG.renderStage && DBG.state) {
    const w0 = WORDS.find(w => w.pos && !DBG.state.progress[w.num] && (w.links || []).length && DBG.exOf(w).length >= 3) || WORDS[0];
    DBG.fc.queue = [w0, WORDS[1]];
    DBG.fc.i = 0; DBG.fc.total = 2; DBG.fc.session = 1; DBG.fc.flipped = false;
    DBG.fc.stats = { good: 0, mid: 0, bad: 0 };
    DBG.renderStage();
    const h = main.innerHTML;
    ok('the card back shows all three example sentences',
       h.includes('fc-ex') && (h.match(/class="fc-ex-item"/g) || []).length === 3,
       `例句块 ${(h.match(/class="fc-ex-item"/g) || []).length} 条`);
    ok('the card back carries the dictionary links',
       /class="fc-links"/.test(h) && /Longman|Cambridge|Merriam/.test(h), '');
    ok('the card back offers the three manual-status buttons',
       (h.match(/class="btn sm fc-mark-btn/g) || []).length === 3 &&
       ['data-mk="new"', 'data-mk="learning"', 'data-mk="mastered"'].every(k => h.includes(k)), '');
    ok('the corner 词条详情 button is gone from the card footer',
       !h.includes('id="fcDetail"'), '');
    ok('the mode card is named 学习 (not 翻卡学习)',
       !h.includes('翻卡学习'), '');
    /* 卡背上的收藏/手动标记会重绘正反两面。正面词性提示属于词条设置，
       不能因为渲染时 fc.flipped=true 就从隐藏的正面 DOM 里消失。 */
    const oldFrontHint = DBG.state.settings.frontShowHint;
    DBG.state.settings.frontShowHint = true;
    DBG.fc.flipped = true;
    DBG.renderStage();
    const frontHtml = main.innerHTML.split('flip-front')[1].split('flip-back')[0];
    ok('rerendering the card back keeps the enabled front-side POS hint',
       frontHtml.includes('tag-pos'), '');
    DBG.state.settings.frontShowHint = oldFrontHint;
    DBG.fc.flipped = false;
    DBG.renderStage();
    /* 手动标记是行为级改动：点「已掌握」应让该词立即算已掌握（等级徽标与高亮跟手）。
       走公开 setStatus 与 renderStage，与按钮绑定同一路径。 */
    DBG.setStatus(w0.num, 'mastered');
    DBG.renderStage();
    const h2 = main.innerHTML;
    ok('marking a card 已掌握 updates its status chip and the mark highlight',
       DBG.prog(w0.num) && DBG.prog(w0.num).lv >= 5 &&
       /class="btn sm fc-mark-btn on" data-mk="mastered"/.test(h2), '');
    DBG.setStatus(w0.num, 'new');
    ok('marking a card 不认识 removes its progress entry',
       !DBG.prog(w0.num), JSON.stringify(DBG.prog(w0.num) || null));
    DBG.fc.session = 0;
  }
}

render('#fav');
ok('favourites view renders', main.innerHTML.includes('收藏'));

render('#settings');
ok('settings view renders', main.innerHTML.includes('segTheme'));

section('state boundary hardening (round 29)');
const ss = DBG.sanitizeState;
ok('debug surface exposes the state sanitizer', typeof ss === 'function');
if (typeof ss === 'function') {
  // 损坏备份：rate 是字符串，未钳制会让设置页 rate.toFixed 抛异常整页崩
  let s = ss({ settings: { rate: 'fast', goal: 'many', theme: 'halloween', fcLimit: -9, showKeyHint: 0 } });
  /* 兜底主题跟应用自己声明的默认值走（第五十九轮起默认改为深色），
     不在此处钉死字面量——改默认值时这里跟着走，不会假红。 */
  const appSrc2 = fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8');
  const defTheme = (appSrc2.match(/theme:\s*'(auto|light|dark)'/) || [])[1];
  ok('non-numeric settings fall back to defaults, never poison render',
     s.settings.rate === 0.95 && s.settings.goal === 30 && defTheme && s.settings.theme === defTheme,
     JSON.stringify(s.settings) + ' defTheme=' + defTheme);
  ok('out-of-range numbers are clamped to the documented bounds',
     s.settings.fcLimit === 5, 'fcLimit=' + s.settings.fcLimit);
  ok('after sanitize the settings value is always toFixed-safe',
     typeof s.settings.rate === 'number' && Number.isFinite(+s.settings.rate.toFixed(2)));
  s = ss({ settings: { rate: 99, goal: 0 } });
  ok('rate clamps to slider max 1.5 and goal to floor 5',
     s.settings.rate === 1.5 && s.settings.goal === 5, `rate=${s.settings.rate} goal=${s.settings.goal}`);
  ok('flag-like settings coerce to real booleans',
     ss({ settings: { showKeyHint: 0, autoSpeak: 'yes' } }).settings.showKeyHint === false
     && ss({ settings: { autoSpeak: 'yes' } }).settings.autoSpeak === true);
}

section('round 51 features (cloze quiz / example search / forecast / swipe)');
{
  const D = DBG, Q = D.quiz;
  ok('debug surface exposes the cloze + search helpers',
     typeof D.clozeSlot === 'function' && typeof D.wordMatchQ === 'function' && !!D.quiz);
  /* 搜索口径：词形/释义命中＝main，只在例句里＝ex（扫描找一条真实「仅例句」查询） */
  let qEx = null, qMain = null;
  for (const w of WORDS) {
    for (const e of D.exOf(w)) {
      const tok = (e.en.toLowerCase().match(/[a-z]{5,}/g) || []).find(t =>
        !w.word.toLowerCase().includes(t) && !w.senses.some(s => s.toLowerCase().includes(t)));
      if (tok) { qEx = { w, tok }; break; }
    }
    if (qEx) break;
  }
  ok('search hits words whose example contains the keyword',
     !!qEx && D.wordMatchQ(qEx.w, qEx.tok) === 'ex', qEx ? qEx.w.word + '/' + qEx.tok : 'none');
  qMain = WORDS.find(w => w.word.length > 5);
  ok('headword match is classified as main hit',
     D.wordMatchQ(qMain, qMain.word.toLowerCase().slice(0, 5)) === 'main');
  ok('numeric query matches by word number', D.wordMatchQ(WORDS[0], '1') !== null);
  /* cloze 挖空：原形整词命中的词出挖空题；命不中的词回退看词选义 */
  const cw = WORDS.find(w => D.clozeSlot(w));
  const fw = WORDS.find(w => !D.clozeSlot(w));
  ok('some words are clozable and some fall back', !!cw && !!fw,
     `${WORDS.filter(w => D.clozeSlot(w)).length}/${WORDS.length} clozable`);
  const cz = D.clozeSlot(cw);
  ok('clozeSlot marks the exact inflection-free form',
     cz && cz.en.slice(cz.start, cz.start + cz.len) === cw.word, cw && cw.word);
  Q.mode = 'cloze'; Q.fb = null; Q.i = 0; Q.score = 0; Q.queue = [cw];
  D.renderQuizQuestion();
  let qHTML = main.innerHTML;
  ok('cloze question renders sentence with a blank slot',
     qHTML.includes('cloze-sent') && qHTML.includes('cloze-blank') && qHTML.includes('cloze-zh'));
  ok('cloze question offers four word-form options',
     (qHTML.match(/class="quiz-opt"/g) || []).length === 4);
  ok('cloze mode badge shown to user', qHTML.includes('例句挖空'));
  Q.queue = [fw]; Q.i = 0; Q.fb = null;
  D.renderQuizQuestion();
  ok('non-clozable word silently falls back to en2zh',
     !main.innerHTML.includes('cloze-blank') && main.innerHTML.includes('看词选义'), fw.word);
  /* 反馈态快照（第四十九轮口径）：resume 重放沿用快照题型，且不二次计分 */
  const opts = D.optionTexts(cw, x => x.word);
  Q.mode = 'en2zh'; Q.queue = [cw]; Q.i = 0; Q.score = 7;
  Q.fb = { i: 0, ok: true, mode: 'cloze', pick: String(opts.find(o => o.ok).t), opts };
  D.renderQuizQuestion();
  ok('feedback snapshot pins the cloze mode on resume',
     main.innerHTML.includes('cloze-blank') && Q.curMode === 'cloze');
  ok('resume replay restores answered state without scoring',
     Q.answered === true && Q.score === 7, 'score=' + Q.score);
  Q.fb = null; Q.mode = 'en2zh'; Q.queue = []; Q.i = 0; Q.score = 0;
  /* 复习预测字段 */
  const tc = D.tierCounts();
  ok('tierCounts carries the forecast buckets',
     typeof tc.dueTomorrow === 'number' && typeof tc.dueWeek === 'number' && tc.dueWeek >= tc.dueTomorrow,
     `tomorrow=${tc.dueTomorrow} week=${tc.dueWeek}`);
  render('#home');
  ok('home goal card shows the review forecast', main.innerHTML.includes('复习预报'));
  /* 闪卡滑动手势开关 */
  render('#settings');
  ok('settings expose the swipe-grading switch',
     main.innerHTML.includes('学习滑动手势') && main.innerHTML.includes('segSwipe'));
  /* 分段控件现在带 role=group / aria-label / aria-pressed（界面自序第三十六轮 a11y），
     断言按结构写，别钉死按钮标签的完整 HTML（否则加一个无障碍属性就假红） */
  const segSwipe = (main.innerHTML.match(/<div class="seg" id="segSwipe"[\s\S]*?<\/div>/) || [''])[0];
  ok('swipeGrade defaults to on in the rendered seg',
     /data-k="1"[^>]*class="on"[^>]*aria-pressed="true"/.test(segSwipe) &&
     /data-k="0"[^>]*aria-pressed="false"/.test(segSwipe),
     segSwipe.slice(0, 120));
  ok('swipeGrade survives sanitize as a real boolean',
     D.sanitizeState({ settings: { swipeGrade: 0 } }).settings.swipeGrade === false &&
     D.sanitizeState({ settings: { swipeGrade: 'x' } }).settings.swipeGrade === true);
  render('#fav');
  ok('favourites view renders without export button when empty',
     main.innerHTML.includes('收藏') && !main.innerHTML.includes('favExport'));
}

section('册四十六轮回归（标记为不认识语义 / 测验跳过计数）');
{
  const D = DBG, Q = D.quiz;
  /* ① 「标记为不认识」= 退回未学习：进度条目必须整个删掉。
     只把 lv 归零的话 isStarted 仍为真，该词会被算成「学习中」且永远进不了未学习牌组。
     走公开路径（setStatus），不直接改 state，避免给后续用例留脏进度。 */
  const mw = WORDS[0];
  const lc0 = D.tierCounts().learning;          // 现状快照（现算值，不钉字面量）
  D.setStatus(mw.num, 'learning');
  const lc1 = D.tierCounts().learning;
  ok('a word marked 学习中 counts into the learning tier',
     D.isStarted(mw.num) && lc1 === lc0 + 1, `learning ${lc0} -> ${lc1}`);
  D.setStatus(mw.num, 'new');
  const lc2 = D.tierCounts().learning;
  ok('标记为不认识 removes the progress entry (word returns to 未学习)',
     !D.state.progress[mw.num] && !D.isStarted(mw.num) && lc2 === lc0,
     `progress=${JSON.stringify(D.state.progress[mw.num] || null)} learning ${lc1} -> ${lc2}`);

  /* ② 已作答后再点「跳过」不得重复计入 skipped：
     showFeedback 只重画 #qFb，页首的 #qSkip 在反馈态仍然可点，
     旧逻辑会把这道已答的题同时算成「已答」和「已跳过」，
     quizResult 的 answered = total - skipped 于是把总题数算小、成绩被吞。 */
  Q.mode = 'en2zh'; Q.queue = [WORDS[1], WORDS[2]]; Q.i = 0; Q.score = 0;
  Q.skipped = 0; Q.answered = false; Q.fb = null;
  D.renderQuizQuestion();
  doc.getElementById('qSkip').click();          // 未作答时跳过 = 记 1 次跳过
  ok('skipping an unanswered question counts once', Q.skipped === 1, 'skipped=' + Q.skipped);
  Q.answered = true;                            // 模拟已作答（反馈态）
  doc.getElementById('qSkip').click();          // 此时点跳过只应翻页
  ok('skipping an already-answered question does not count as skipped',
     Q.skipped === 1, 'skipped=' + Q.skipped);
  Q.mode = 'en2zh'; Q.queue = []; Q.i = 0; Q.score = 0; Q.skipped = 0; Q.answered = false; Q.fb = null;
}

/* 段名用「界面自序 round 36」：全局台账的「五十六」是数据域分层轮（42ae07），
   界面轮沿用自序数（承第三十五轮 532d4c4），两套编号不可混 */
section('round 36 a11y & settings coverage (interface round: headings / aria-pressed / fcLimit)');
{
  /* ① 每个非首页视图都要有唯一的一级标题：此前七页的标题都是普通 div，
     屏幕阅读器与「跳到主内容」后的结构导航都读不到页面名。
     （一百五十一轮起 cards/quiz 并为 study 一页，视图清单跟着收。） */
  const h1Pages = ['browse', 'study', 'quiz', 'cards', 'cats', 'fav', 'stats', 'settings'];
  const missingH1 = h1Pages.filter(p => {
    render('#' + p);
    return !/<h1 class="page-title">/.test(main.innerHTML);
  });
  ok('every non-home view has an h1 page title', missingH1.length === 0, missingH1.join(','));
  ok('home keeps its own h1 in the hero',
     (render('#home'), /<h1>/.test(main.innerHTML)));

  /* ② 分段控件的选中态要能被读屏读到（aria-pressed），容器要有可访问名 */
  render('#settings');
  const segs = main.innerHTML.match(/<div class="seg"[^>]*>[\s\S]*?<\/div>/g) || [];
  ok('settings segmented controls expose a group role and a label',
     segs.length >= 6 && segs.every(s => /role="group"/.test(s) && /aria-label="[^"]+"/.test(s)),
     'segs=' + segs.length);
  ok('settings segmented buttons expose the selected state with aria-pressed',
     segs.every(s => (s.match(/aria-pressed="/g) || []).length === (s.match(/<button/g) || []).length),
     segs[0] ? segs[0].slice(0, 120) : '');

  /* ③ 设置页要能改到 DEFAULTS.settings 里的每一个参数：
     fcLimit 此前只在闪卡页有输入框，在「设置」里找不到。 */
  const S = DBG.state.settings;
  ok('settings page exposes the flashcard limit control',
     main.innerHTML.includes('id="fcLimitInput"') && main.innerHTML.includes('学习每次上限'));
  /* 覆盖断言走「设置键 → 控件标记」映射，数据驱动：
     DEFAULTS.settings 将来加新开关而这里没登记时，断言会指名道姓报出缺哪个键，
     而不是靠钉死键数（=9）间接漂移。 */
  const CTRL = { theme: 'segTheme', rate: 'rateRange', goal: 'goalInput', frontShowHint: 'segHint',
    autoSpeak: 'segSpeak', autoWrongFav: 'segWrongFav', showKeyHint: 'segKeyHint',
    fcLimit: 'fcLimitInput', swipeGrade: 'segSwipe' };
  const unmapped = Object.keys(S).filter(k => !CTRL[k]);
  const notRendered = Object.keys(S).filter(k => CTRL[k] && !main.innerHTML.includes(CTRL[k]));
  ok('all settings knobs are reachable from the settings page',
     unmapped.length === 0 && notRendered.length === 0,
     'unmapped=' + unmapped.join(',') + ' notRendered=' + notRendered.join(',') +
     ' keys=' + Object.keys(S).join(','));
}


/* 界面自序第三十七轮：对比度/语义修补（承 bc67bb 转交的 CSS 只读审计，逐条直验后落修） */
section('round 37 contrast & semantics (interface round: ink tokens / listbox / scoped ids)');
{
  const css = fs.readFileSync(path.join(ROOT, 'css/style.css'), 'utf8');
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

  /* ① 选中态不能硬编码白字：明暗两套主题的 accent 明度差很大，
     白字在深色主题只有 2.93:1。统一走「压色墨水」token。 */
  ok('css defines the on-colour ink tokens for both themes',
     /--on-accent:\s*#/.test(css) && /--on-warn:\s*#/.test(css) &&
     /--on-bad:\s*#/.test(css) && /--on-good:\s*#/.test(css),
     'tokens=' + (css.match(/--on-(accent|warn|bad|good):#/g) || []).length);
  const sel = ['.nav-item.active', '.btn-group button.on', '.chip.on', '.letter-btn.on',
    '.pager button.on', '.seg button.on', '.skip-link', '::selection'];
  const hardCodedWhite = sel.filter(r => {
    const m = css.match(new RegExp(r.replace(/[.:#]/g, '\\$&') + '\\{[^}]*\\}'));
    return m && /color:#fff(;|\s)/.test(m[0]);
  });
  ok('no selected state hardcodes white text on the accent colour',
     hardCodedWhite.length === 0, hardCodedWhite.join(','));
  ok('selected states use the accent ink token',
     sel.filter(r => {
       const m = css.match(new RegExp(r.replace(/[.:#]/g, '\\$&') + '\\{[^}]*\\}'));
       return m && /color:var\(--on-accent\)/.test(m[0]);
     }).length === sel.length);

  /* ② 打印：深色主题下词头不能继承浅色 --text（白纸上等于隐形） */
  const printBlock = css.slice(css.indexOf('@media print{'));
  ok('print media resets the body colour for both themes',
     /body\{background:#fff;color:#000/.test(printBlock), printBlock.slice(0, 80));

  /* ③ 列表框语义：listbox 容器里只允许有 option */
  ok('search listbox is a dedicated container',
     /id="searchList" role="listbox"/.test(html) && /aria-controls="searchList"/.test(html) &&
     !/id="searchResults" role="listbox"/.test(html));
  ok('word modal keeps a dialog role and an accessible-name fallback',
     /class="modal-card" role="dialog" aria-modal="true" aria-labelledby="wmTitle" aria-label=/.test(html));

  /* ④ 收藏与词库视图的 id 不再重名（此前两视图都用 bq/viewToggle/browseTable/browsePager） */
  const idsOf = html2 => (html2.match(/\sid="([^"]+)"/g) || []).map(s => s.slice(5, -1));
  const dupIds = html2 => {
    const seen = new Set(), dup = new Set();
    idsOf(html2).forEach(i => { if (seen.has(i)) dup.add(i); seen.add(i); });
    return [...dup];
  };
  render('#browse');
  const bHTML = main.innerHTML;
  render('#fav');
  const fHTML = main.innerHTML;
  ok('browse keeps its own scoped ids', ['bq', 'viewToggle', 'browseTable'].every(i => bHTML.includes(`id="${i}"`)));
  ok('fav view uses its own scoped ids',
     ['favBq', 'favViewToggle', 'favTable'].every(i => fHTML.includes(`id="${i}"`)) &&
     !/\sid="bq"/.test(fHTML) && !/\sid="browseTable"/.test(fHTML));
  ok('no duplicate element ids inside a rendered view',
     dupIds(bHTML).length === 0 && dupIds(fHTML).length === 0,
     'browse=' + dupIds(bHTML).join(',') + ' fav=' + dupIds(fHTML).join(','));
  render('#settings');
}

/* 界面自序第三十八轮：语义与键盘（标题层级 / live 区 / 翻面可访问名） */
section('round 38 semantics & keyboard (interface round: heading levels / live region / flip label)');
{
  const appSrc = fs.readFileSync(path.join(ROOT, 'js/app.js'), 'utf8');
  const htmlSrc = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

  /* ① 标题层级：页面 h1 之后不许直接跳到 h3（读屏的「结构导航」按层级列标题）
     守卫诚实度（工装·第十轮）：原来写的是 `if (tags.length && tags[0] !== 1)`——
     一屏**一个标题都没量到**时 tags 为空 ⇒ 整条判据不产生任何 badLevels ⇒
     「标题全没了」也算判过（空过）。拆成两条：先「量到标题」（每屏至少一个），
     再「首个是 h1 且不跳级」。与界面窗第五十七轮 a11y 侧同源同治。 */
  const noHeading = [], badLevels = [];
  for (const v of ['home', 'browse', 'study', 'quiz', 'cards', 'cats', 'fav', 'stats', 'settings']) {
    render('#' + v);
    const tags = (main.innerHTML.match(/<h([1-6])[\s>]/g) || []).map(t => +t[2]);
    if (!tags.length) { noHeading.push(v); continue; }   // 量不到 ⇒ 判红，不当「无问题」
    if (tags[0] !== 1) badLevels.push(v + ':首个标题是 h' + tags[0]);
    let prev = 0;
    tags.forEach(lv => { if (prev && lv - prev > 1) badLevels.push(v + ':h' + prev + '→h' + lv); prev = lv; });
  }
  ok('every view renders at least one heading (heading probe not vacuous)',
     noHeading.length === 0, noHeading.join(','));
  ok('every view keeps a gap-free heading order (h1 first)', badLevels.length === 0, badLevels.join(','));

  /* ② 测验反馈是 live 区：答题结果必须能被读屏播报 */
  ok('quiz feedback is a live region',
     /id="qFb" role="status" aria-live="polite"/.test(appSrc));

  /* ③ 弹窗标题是 h2（与页内小节同级） */
  ok('shortcuts dialog title is an h2',
     /<h2 id="scTitle"/.test(htmlSrc) && !/<h3 id="scTitle"/.test(htmlSrc));

  /* ④ 闪卡卡面：翻面后要更新可访问名，且空格只翻一次
     （卡面自身的 keydown 与全局「空格翻面」快捷键都调 flip() 时会翻两次） */
  ok('flashcard card updates its accessible name after flipping',
     /aria-label', fc\.flipped \? \(t \|\| '卡片背面：释义'\)/.test(appSrc) ||
     /setAttribute\('aria-label', fc\.flipped/.test(appSrc));
  /* 例句详情等嵌套控件自己处理 Enter/空格；卡面只处理以卡片为 target 的按键。
     因而不再锁死某一行的排版，分别断言 target 守卫与阻止重复翻面的关键动作。 */
  const cardKeydown = appSrc.match(/card\.onkeydown = e => \{([\s\S]*?)\n  \};/);
  ok('flashcard card stops the space key from flipping twice',
     !!cardKeydown && cardKeydown[1].includes('e.target !== card') &&
     cardKeydown[1].includes('e.stopPropagation(); flip();'));

  /* ⑤ 二百零四轮：flip() 不重渲染（只切卡面类名），评分钮的 pending 摘挂
     必须在 flip() 里同步做——否则「干净翻面」（点卡面/显示答案/空格）后
     三颗评分钮仍是中性灰，语义色不回来（renderStage 只在整块重绘时算 pending；
     重渲染路径的行为级断言在 deck-setup 段已覆盖，这里守住 flip 这条捷径路）。 */
  const flipFn = appSrc.match(/function flip\(\) \{([\s\S]*?)\n\}/);
  ok('flip() syncs the rating-row pending state (no rerender on flip)',
     !!flipFn && flipFn[1].includes("classList.toggle('pending'"),
     flipFn ? 'flip body lacks pending toggle' : 'flip() not found');
}

section('round 39 contrast residuals (interface round: ink tokens on saturated surfaces / computed word count)');
{
  const css = fs.readFileSync(path.join(ROOT, 'css/style.css'), 'utf8');
  const ctest = fs.readFileSync(path.join(ROOT, 'tools/contrast_test.py'), 'utf8');
  const fixture = fs.readFileSync(path.join(ROOT, 'tools/fixtures/contrast.html'), 'utf8');

  /* ① 块级解析：凡「同块内既有硬编码白字、又有饱和底色 token」即判失败
     （bc67bb 指出：同行匹配会让多行写法静默漏过；ae16dd 裁：块级解析 + 显式白名单）
     饱和族覆盖 accent|good|bad|warn 的本体与 -2/-3 变体；
     只认 var(--token) 整名，--accent-ink / --accent-soft / --on-accent 这类不算底色。 */
  const SAT = /var\(--(?:accent|accent-2|accent-3|good|good-2|warn|warn-2|bad|bad-2)\)/;
  const WHITE = /(?<![\w-])color:\s*(?:#fff\b|#ffffff\b|white\b)/;
  /* 已备案的合理例外：暗底 hero 的白字（白字压在 accent 渐变上）。
     白名单按**确切选择器**枚举（不是 `.hero*` 通配）——否则日后新写的
     `.hero 某物{background:var(--bad);color:#fff}` 会静默过闸（机制迁就孤例）。 */
  const WHITE_LIST = ['.hero'];
  const scanWhiteOnSaturated = (cssText) => {
    const noComments = cssText.replace(/\/\*[\s\S]*?\*\//g, '');
    const out = [];
    const reBlock = /([^{}]+)\{([^{}]*)\}/g;
    let mb;
    while ((mb = reBlock.exec(noComments))) {
      const sel = mb[1].trim();
      const body = mb[2];
      if (!SAT.test(body) || !WHITE.test(body)) continue;
      const parts = sel.split(',').map(x => x.trim());
      if (parts.some(x => WHITE_LIST.includes(x))) continue;   // 精确匹配白名单
      out.push(sel.replace(/\s+/g, ' ').slice(0, 60));
    }
    return out;
  };
  const whiteOnSaturated = scanWhiteOnSaturated(css);
  ok('no hardcoded white text on saturated surfaces (block-level scan)',
     whiteOnSaturated.length === 0, whiteOnSaturated.join(' | '));

  /* ①b 守卫自测（bc67bb 变异测试转正）：同一函数喂合成 CSS 必须按预期判定 */
  ok('guard catches a multi-line white-on-saturated rule',
     scanWhiteOnSaturated('.mut-a{background:var(--accent);\n  color:#fff;}').length === 1);
  ok('guard no longer lets any .hero* rule through (whitelist is exact, not wildcard)',
     scanWhiteOnSaturated('.hero .mut-c{background:var(--bad);color:#fff}').length === 1);
  ok('guard still exempts the exact .hero dark-on-gradient block',
     scanWhiteOnSaturated('.hero{background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff}').length === 0);

  /* ② 五处残留各自改走墨水 token —— 双件属性查表（底色与字色都要对，
     只验字色会被「rgba 半透底改回去」假绿），且用正则而非整串字面量（免声明顺序/空格变化假红） */
  const esc = t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pair = (sel, bgTok, fgTok) => {
    const m = css.match(new RegExp(esc(sel) + '\\s*\\{([^}]*)\\}'));
    if (!m) return false;
    return new RegExp('background[^:]*:\\s*[^;]*var\\(--' + bgTok + '\\)', 'i').test(m[1])
        && new RegExp('(?<![\\w-])color:\\s*var\\(--' + fgTok + '\\)', 'i').test(m[1]);
  };
  ok('audit residuals use ink tokens for both background and foreground',
     pair('.quiz-opt.correct .oi', 'good', 'on-good')
     && pair('.quiz-opt.wrong .oi', 'bad', 'on-bad')
     && pair('.quick-btn:hover .qb', 'accent', 'on-accent')
     && pair('.filter-toggle .ft-count', 'accent', 'on-accent')
     && pair('.brand-logo', 'accent', 'on-accent'));

  /* ③ 对比度套件不得钉死词数字面量（加词数据轮会假红）——改为现算 */
  ok('contrast test computes the word count instead of hardcoding it',
     !ctest.includes('1428') && ctest.includes('WL_WORDS'));

  /* ④ 夹具补齐本轮新增的量测锚点 */
  ok('contrast fixture anchors the new targets',
     ['brand-logo', 'quiz-opt correct', 'quick-btn', 'ft-count'].every(s => fixture.includes(s)));
}

section('round 40 app-wide contrast sweep (interface round: full-app scan / hero glass / pos tag)');
{
  const css = fs.readFileSync(path.join(ROOT, 'css/style.css'), 'utf8');
  const sweepPath = path.join(ROOT, 'tools/contrast_sweep.py');

  /* ① hero 的玻璃层必须「深卡掺深、纸卡掺浅」——判据随一百九十六轮改为主题
     token 审计：hero 玻璃色全部收进 --hero-glass（两套主题各给一个字面值），
     这里从 :root 与 html[data-theme="dark"] 两个块里抽出字面值分别校验：
     深色主题必须掺深（白字压「白玻璃」逐层叠亮会低于 AA，原 accent 渐变底
     实测 eyebrow 4.17/3.60、.btn.big 4.25/3.67 的旧账）、rgb 和 < 150 且非纯白；
     浅色主题必须是浅纸玻璃（深字压得住）、rgb 和 > 600。
     此前「规则体里抓 background:rgba 字面量」的写法在玻璃色 token 化后抓不到
     任何东西，守卫会被空转放行——所以改为审计 token 本身。 */
  const heroTokenVal = (name) => {
    const grab = (block) => {
      const m = block && block.match(new RegExp('--' + name + ':\\s*([^;]+);'));
      return m ? m[1].trim() : null;
    };
    const rootM = css.match(/:root\{([^}]*)\}/);
    const darkM = css.match(/html\[data-theme="dark"\]\{([^}]*)\}/);
    return { light: grab(rootM && rootM[1]), dark: grab(darkM && darkM[1]) };
  };
  const rgbSum = (v) => {
    if (!v) return null;
    let m = v.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
    if (m) return (+m[1]) + (+m[2]) + (+m[3]);
    m = v.match(/^#([0-9a-f]{6})$/i);
    if (m) return [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16)).reduce((a, b) => a + b, 0);
    return null;
  };
  const glassT = heroTokenVal('hero-glass');
  const glassSumL = rgbSum(glassT.light), glassSumD = rgbSum(glassT.dark);
  ok('hero glass is token-driven: light paper glass / dark tinted glass (never white on dark)',
     glassSumL !== null && glassSumL > 600
     && glassSumD !== null && glassSumD < 150,
     'light=' + glassT.light + ' (sum ' + glassSumL + ') dark=' + glassT.dark + ' (sum ' + glassSumD + ')');
  /* ①b 玻璃 token 必须真的被两处关键规则引用（守卫不是摆设）：
     eyebrow 徽章与 hero 次级按钮的 background 都走 var(--hero-glass 家族)。 */
  ok('hero glass tokens are referenced by the eyebrow badge and hero buttons',
     /\.hero \.eyebrow\{[^}]*background:var\(--hero-chip-bg\)/.test(css)
     && /\.hero \.btn\{[^}]*background:var\(--hero-btn-bg\)/.test(css));

  /* ② 词性标签 11px 小字：--accent 压 --accent-soft = 4.4963:1（差 0.004 未过 AA）→ 改走 --accent-ink */
  ok('pos tag uses the darker accent ink',
     /\.tag-pos\{[^}]*color:var\(--accent-ink\)/.test(css));

  /* ③ 全站扫描套件已挂上，且按「路径完备（2 主题 × 8 视图）」计定数 checks，
     逐元素 ratio 只进诊断输出，不随界面文字增减动基线数 */
  ok('app-wide contrast sweep suite exists with a fixed check count',
     fs.existsSync(sweepPath)
     && /VIEWS = \[/.test(fs.readFileSync(sweepPath, 'utf8'))
     && /checked \+= 1/.test(fs.readFileSync(sweepPath, 'utf8')));

  /* ④ 新套件已登记进 CHANGELOG（README 归 bc67bb 域，本轮不碰其件） */
  const changelog = fs.readFileSync(path.join(ROOT, 'CHANGELOG.md'), 'utf8');
  ok('changelog registers the app-wide contrast sweep suite',
     changelog.includes('contrast_sweep.py'));
}

section('工装·第八轮回归（复习预报与今日待复习：两个「到期」桶不许混为一谈）');
{
  const D = DBG;
  /* 首页同屏有两处「到期」：统计卡「今日待复习」＝**已到期**（含逾期）的词；
     下方「复习预报」＝**未来**才会到期的词。两个桶本就不相交，但旧文案把
     预报那行写成「今天和明天将到期 N 词」——「今天」与统计卡的「今日待复习」
     字面撞车，用户看到「今日待复习 5」与「今天和明天将到期 0 词」无从判断
     谁对。修法：预报那行改说「未来 48 小时内」，两处的字面窗口不再重叠
     （桶本身不动：t2＝后天零点，(now, t2] 落在未来 48 小时内）。 */
  const saved = Object.assign({}, D.state.progress);
  const wOver = WORDS.find(w => !D.state.progress[w.num]);
  const wSoon = WORDS.slice(WORDS.indexOf(wOver) + 1).find(w => !D.state.progress[w.num]);
  if (wOver && wSoon) {
    const tc0 = D.tierCounts();
    D.state.progress[wOver.num] = { lv: 1, due: Date.now() - 3600e3, seen: 1, correct: 0, wrong: 1, last: 0 };
    const tc1 = D.tierCounts();
    ok('an overdue word lands in the due bucket only, never in the forecast',
       tc1.due === tc0.due + 1 && tc1.dueTomorrow === tc0.dueTomorrow,
       `due ${tc0.due}->${tc1.due} forecast ${tc0.dueTomorrow}->${tc1.dueTomorrow}`);
    /* 守卫诚实度（工装·第十轮）：这里原来写的是「due = now + 36 小时」——
       预报桶的边界 t2 ＝ **后天零点**（(now, t2)），而 now 到 t2 的距离随钟点
       在 24~48 小时之间浮动：本地 12:00 之后 now+36h 已经越过后天零点，
       那个词就掉出预报桶 ⇒ 这条断言**每天中午之后必假红**（产品没问题、套件红）。
       实测：2026-11-17 12:03 跑，now+36h = 11-19 00:03 > t2 = 11-19 00:00 ⇒ 判红。
       改成 +2 小时：恒在 (now, t2) 内（t2-now ≥ 24h），任何钟点都成立。 */
    D.state.progress[wSoon.num] = { lv: 1, due: Date.now() + 2 * 3600e3, seen: 1, correct: 1, wrong: 0, last: 0 };
    const tc2 = D.tierCounts();
    ok('a word due in 2 hours lands in the forecast bucket only',
       tc2.dueTomorrow === tc1.dueTomorrow + 1 && tc2.due === tc1.due,
       `forecast ${tc1.dueTomorrow}->${tc2.dueTomorrow} due ${tc1.due}->${tc2.due}`);
    render('#home');
    const fcText = (main.innerHTML.match(/复习预报：([^·]*)/) || ['', ''])[1];
    ok('the forecast line no longer claims 今天 (that word belongs to the 今日待复习 card)',
       fcText.includes('未来') && !fcText.includes('今天'), fcText.trim());
    D.state.progress = saved;
  } else {
    ok('the forecast-bucket test has two untouched words to work with', false, 'no free word');
  }
}

section('入口按钮的词数口径：池子大于「每次上限」时不许承诺整池');
{
  /* 牌组在 buildDeck(src).slice(0, fc.lastLimit || 30) 处被截断，
     而筛选页的按钮写着「学习这 2222 个词」、首页主行动写着「从新词开始（2222）」——
     点进去只有 30 张卡，页面上没有任何一处说明其余的去哪儿了。
     现在：池子 ≤ 上限写确数；池子 > 上限写「本次 N 张」。 */
  const D = DBG;
  const savedLimit = D.fc.lastLimit;
  const savedProgress = D.state.progress;
  D.state.progress = {};                     // 清空进度 ⇒ 首页主行动落到「从新词开始」
  render('#home');
  const homeHTML = main.innerHTML;
  ok('the home CTA states the session size instead of promising the whole pool',
     homeHTML.includes('从新词开始（2222 词 · 本次 30 张）') && !homeHTML.includes('从新词开始（2222）'),
     (homeHTML.match(/从新词开始[^<]*/) || [''])[0]);
  render('#browse');
  const browseHTML = main.innerHTML;
  ok('the browse study button does not promise the whole filtered pool',
     browseHTML.includes('学习这 2222 个词（本次 30 张）') && !browseHTML.includes('学习这 2222 个词<'),
     (browseHTML.match(/学习这[^<]*/) || [''])[0]);
  /* 上限够大时（一次会话能学完整个池子）仍写确数，别把口径一刀切成「本次 N 张」 */
  D.fc.lastLimit = 3000;
  render('#browse');
  ok('the exact count is shown when one session can cover the whole pool',
     main.innerHTML.includes('学习这 2222 个词'), (main.innerHTML.match(/学习这[^<]*/) || [''])[0]);
  render('#home');
  ok('the home CTA shows the exact count when the pool fits in one session',
     main.innerHTML.includes('从新词开始（2222）'), (main.innerHTML.match(/从新词开始[^<]*/) || [''])[0]);
  D.fc.lastLimit = savedLimit;
  D.state.progress = savedProgress;
}

section('存档坏值：逐键摘除、其余照常恢复（不许整份清零）');
{
  /* 此前 sanitizeState 对类型不对的键一律 throw，loadState 捕到就整档回落默认，
     启动时的 save() 又把这个空存档写回本地存储 —— **一个字段写错＝整份学习进度被静默清空**。
     现在改成逐键摘除：坏的那个键回落默认，其余（进度/收藏/打卡/测验史）照常恢复，
     坏原值另存留底（wl_state_v1_corrupt），不静默覆盖。 */
  const good = {
    progress: { '1': { lv: 3, due: 0, seen: 2, correct: 2, wrong: 0, last: 1 } },
    fav: [1, 2],
    quizHist: [{ score: 5, total: 10, t: 1700000000000 }],
    days: { '2026-11-19': 3 },
    visits: { '2026-11-19': 2 },
    settings: { theme: 'dark', goal: 30, rate: 1.0, fcLimit: 30, autoSpeak: false,
                frontShowHint: false, autoWrongFav: false, showKeyHint: true, swipeGrade: true },
    created: 1, speakVer: 1,
  };
  const badDays = Object.assign({}, good, { days: [1, 2] });   // days 要是对象，数组＝类型坏
  storage.clear();
  storage.setItem(KEY, JSON.stringify(badDays));
  const errBefore = errors.length;
  load('js/app.js');                       // 重新启动＝重新读一次存档
  ok('re-booting with a corrupt archive raises no JS error',
     errors.length === errBefore, errors.slice(errBefore).slice(0, 2).join(' ;; '));
  const D2 = sandbox.WL_DEBUG || {};
  const st2 = D2.state || {};
  ok('one wrong-typed field no longer wipes the whole archive',
     Object.keys(st2.progress || {}).length === 1 && (st2.fav || []).length === 2
     && (st2.quizHist || []).length === 1,
     `progress=${Object.keys(st2.progress || {}).length} fav=${(st2.fav || []).length} quiz=${(st2.quizHist || []).length}`);
  ok('the corrupt field itself falls back to the default (empty days)',
     !st2.days || Object.keys(st2.days).length === 0, JSON.stringify(st2.days));
  const hooks = listeners['beforeunload'] || [];
  const lastHook = hooks[hooks.length - 1];       // 重启过一次 ⇒ 最新的那个钩子属于新实例
  if (typeof lastHook === 'function') lastHook();
  ok('the corrupt original is kept aside instead of being silently overwritten',
     storage.getItem('wl_state_v1_corrupt') === JSON.stringify(badDays),
     String(storage.getItem('wl_state_v1_corrupt')).slice(0, 60));
  const written = JSON.parse(storage.getItem(KEY) || '{}');
  ok('the salvaged archive is what gets written back',
     Object.keys(written.progress || {}).length === 1 && (written.fav || []).length === 2,
     `progress=${Object.keys(written.progress || {}).length} fav=${(written.fav || []).length}`);
}

section('工装·第九轮回归（旧版状态键迁移：键名取应用真实声明的那个）');
{
  /* 应用启动时 loadState() 会把 LEGACY_KEYS 里的旧存档搬进 wl_state_v1 并删掉旧键。
     此前那条冒烟断言查的是 '***' —— 应用里根本没有这个键，等于查了个不存在的东西。
     现在用应用**真实声明**的旧键重跑一次启动来验迁移：
       ① 旧值被原样搬进 wl_state_v1；
       ② 旧键被删掉；
       ③ 重跑启动不报 JS 错；
       ④ 测试用的旧键名与源码声明一致（防测试自己写死一个错键名）。
     放在文件最后：重跑启动会再注册一遍监听器，不能影响前面的断言。 */
  const _legacyKey = 'wl_state';
  const _legacyRaw = JSON.stringify({ days: {}, fav: [], progress: {}, settings: {} });
  storage.clear();
  storage.setItem(_legacyKey, _legacyRaw);
  const _errBefore = errors.length;
  load('js/app.js');
  ok('re-booting for the legacy-key check raises no JS error',
     errors.length === _errBefore, errors.slice(_errBefore).slice(0, 2).join(' ;; '));
  ok('legacy state is migrated into the documented key',
     storage.getItem(KEY) === _legacyRaw, String(storage.getItem(KEY)).slice(0, 60));
  ok('the legacy key is removed after migration',
     !(_legacyKey in storage._dump()), Object.keys(storage._dump()).join(','));
  const _appSrc = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
  ok('the legacy key used here is the one the app declares',
     new RegExp("LEGACY_KEYS\\s*=\\s*\\[[^\\]]*'" + _legacyKey + "'").test(_appSrc));
}

console.log('\n' + (FAIL.length ? `RESULT: ${FAIL.length} FAILURES` : 'RESULT: ALL TESTS PASSED'));
if (FAIL.length) { FAIL.forEach(f => console.log('  - ' + f)); process.exit(1); }
console.log(`(${passed} checks passed)`);
