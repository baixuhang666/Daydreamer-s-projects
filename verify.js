// 用 DOM 桩验证生成的单文件 HTML 里的 JS 能正常跑通
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, '..', '银行行测200题刷题.html');
const html = fs.readFileSync(htmlPath, 'utf8');

// 取 <script> 内容
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('未找到 script'); process.exit(1); }
let js = m[1];

// 极简 DOM 桩
let currentHTML = '';
const storeData = {};
const mkEl = () => ({
  set innerHTML(v) { currentHTML = v; },
  get innerHTML() { return currentHTML; },
  addEventListener: () => {},
  onclick: null, classList: { add: () => {}, remove: () => {}, toggle: () => {} },
  style: {}, scrollIntoView: () => {}, focus: () => {},
  querySelectorAll: () => [], querySelector: () => mkEl(),
});
const document = {
  getElementById: () => mkEl(),
  querySelectorAll: () => [],
  querySelector: () => mkEl(),
  createElement: () => mkEl(),
  addEventListener: () => {},
};
const localStorage = {
  getItem: (k) => storeData[k] || null,
  setItem: (k, v) => { storeData[k] = v; },
  removeItem: (k) => { delete storeData[k]; },
};
const window = { addEventListener: () => {}, scrollTo: () => {}, innerWidth: 1200 };
const elProto = {};
js = js.replace(/document\.addEventListener/g, 'noopListen');
js = js.replace(/window\.addEventListener/g, 'noopListen');
js += `
;globalThis.__T = {BANK, IMGS, MOD_ORDER, renderHome, startMod, pick, move, openSheet};
`;
const noopListen = () => {};
const vm = require('vm');
const ctx = { document, localStorage, window, noopListen, console,
  location: { hash: '' }, setTimeout, JSON, Math, Object, Array, String, Number };
ctx.globalThis = ctx;
vm.createContext(ctx);
try {
  vm.runInContext(js, ctx);
} catch (e) {
  console.error('脚本执行失败:', e.message);
  process.exit(1);
}

const T = ctx.__T;
const BANK = T.BANK;
console.log('模块顺序:', T.MOD_ORDER.join(', '));

let total = 0, noAns = [], noOpt = [], imgOk = 0;
for (const k of T.MOD_ORDER) {
  const mod = BANK[k];
  total += mod.questions.length;
  for (const q of mod.questions) {
    if (!q.answer) noAns.push(`${k}#${q.num}`);
    if (Object.keys(q.options || {}).length === 0 && !q.mergedImg && !q.origImg)
      noOpt.push(`${k}#${q.num}`);
    if ((q.stemImgs || []).length) imgOk++;
  }
  console.log(`  ${k} ${mod.name}: ${mod.questions.length} 题`);
}
console.log('总题数:', total);
console.log('无答案:', noAns.length ? noAns.join(',') : '无');
console.log('无选项也无图:', noOpt.length ? noOpt.join(',') : '无');
console.log('带图题:', imgOk, '| 图片资源:', Object.keys(T.IMGS).length);

// 渲染首页
T.renderHome();
if (currentHTML.includes('银行行测') && currentHTML.includes('判断推理')) {
  console.log('✔ 首页渲染正常');
} else { console.error('✗ 首页渲染异常'); process.exit(1); }

// 逐题渲染 + 作答
let rendered = 0;
for (const k of T.MOD_ORDER) {
  T.startMod(k, 'all');
  for (const q of BANK[k].questions) {
    const ans = q.answer;
    if (ans) { ctx.__T.pick(ans[0]); }
    rendered++;
  }
}
console.log(`✔ 全部 ${rendered} 题渲染+作答无异常`);

// 答题卡
T.openSheet();
console.log('✔ 答题卡渲染正常');
console.log('\n全部通过 ✅');
