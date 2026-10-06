# -*- coding: utf-8 -*-
"""把题库JSON+图片打包成单文件HTML刷题程序"""
import os
import json
import base64
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import OUT_DIR, OUT_HTML, TITLE, H1, SUB

OUTDIR = OUT_DIR
IMGDIR = os.path.join(OUTDIR, 'images')


def load_imgs():
    imgs = {}
    for f in os.listdir(IMGDIR):
        if f.endswith('.png'):
            with open(os.path.join(IMGDIR, f), 'rb') as fp:
                imgs[f[:-4]] = base64.b64encode(fp.read()).decode()
    return imgs


def build():
    with open(os.path.join(OUTDIR, 'questions_raw.json'), encoding='utf-8') as f:
        bank = json.load(f)
    imgs = load_imgs()

    # 清理数据：把图片标记转为文件名key
    def conv_img_tag(tag, mod):
        m = re.match(r'\[IMG:(.+)\]', tag)
        if m:
            return f'{mod}_{m.group(1)[4:]}'  # IMG:p7_xxx -> mod_p7_xxx
        m = re.match(r'\[MERGED:(.+)\]', tag)
        if m:
            return m.group(1)[:-4]
        return None

    for mod, m in bank.items():
        for q in m['questions']:
            new_imgs = []
            for tag in q['stemImgs']:
                k = conv_img_tag(tag, mod)
                if k:
                    new_imgs.append(k)
            q['stemImgs'] = new_imgs
            # 解析中的图片
            def repl(mm):
                k = f"{mod}_{mm.group(1)[4:]}"
                return f'@@IMG:{k}@@'
            q['explanation'] = re.sub(r'\[IMG:(.+?)\]', repl, q['explanation'])
            if q.get('mergedImg'):
                q['mergedImg'] = os.path.basename(q['mergedImg'])[:-4]
            if q.get('origImg'):
                q['origImg'] = os.path.basename(q['origImg'])[:-4]

    bank_js = json.dumps(bank, ensure_ascii=False)
    imgs_js = json.dumps(imgs)

    html = HTML_TEMPLATE.replace('__BANK__', bank_js).replace('__IMGS__', imgs_js)
    html = html.replace('__TITLE__', TITLE).replace('__H1__', H1).replace('__SUB__', SUB)
    out = os.path.join(os.path.dirname(OUTDIR), OUT_HTML)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'已生成: {out} ({os.path.getsize(out)//1024} KB)')


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
:root{
  --bg:#f5f7fa; --card:#ffffff; --line:#e5e9f0; --tx:#1f2937; --tx2:#6b7280;
  --blue:#2f6fed; --blue-bg:#eef4ff; --green:#16a34a; --green-bg:#f0fdf4;
  --red:#dc2626; --red-bg:#fef2f2; --amber:#d97706;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--tx);font-size:15px;line-height:1.7}
.wrap{max-width:860px;margin:0 auto;padding:16px}
button{font-family:inherit;cursor:pointer;border:none;background:none}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:14px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:9px 18px;border-radius:9px;font-size:14px;background:var(--blue);color:#fff;transition:.15s}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:var(--card);color:var(--tx);border:1px solid var(--line)}
.btn:disabled{opacity:.45;cursor:not-allowed}
/* 首页 */
.home h1{text-align:center;margin:26px 0 6px;font-size:24px}
.home .sub{text-align:center;color:var(--tx2);margin-bottom:24px;font-size:13px}
.mods{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.mod-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;cursor:pointer;transition:.15s}
.mod-card:hover{border-color:var(--blue);box-shadow:0 4px 16px rgba(47,111,237,.10)}
.mod-card h2{font-size:18px;margin-bottom:4px}
.mod-card .cnt{color:var(--tx2);font-size:13px;margin-bottom:10px}
.bar{height:7px;background:var(--line);border-radius:4px;overflow:hidden;margin:10px 0 6px}
.bar>i{display:block;height:100%;background:var(--blue);border-radius:4px}
.stat{font-size:12px;color:var(--tx2);display:flex;gap:14px}
.stat b{color:var(--tx)}
.gstats{margin-top:16px;text-align:center;color:var(--tx2);font-size:13px}
/* 刷题页 */
.top{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.top .back{padding:7px 14px;font-size:13px}
.top .mname{font-weight:600;font-size:16px}
.top .pos{color:var(--tx2);font-size:13px;margin-left:auto}
.pbar{height:5px;background:var(--line);border-radius:3px;margin-bottom:14px;overflow:hidden}
.pbar>i{display:block;height:100%;background:var(--blue);transition:.3s}
.material{background:#fbfcfe;border:1px dashed #d4dce8;border-radius:10px;padding:14px 16px;margin-bottom:14px;font-size:14px}
.material h3{font-size:13px;color:var(--blue);margin-bottom:8px;font-weight:600}
.material .fold{float:right;color:var(--tx2);font-size:12px;cursor:pointer}
.stem{font-size:16px;line-height:1.9;white-space:pre-wrap}
.stem img,.material img,.exp img{max-width:100%;border-radius:8px;margin:8px 0;display:block}
.opts{margin-top:16px;display:flex;flex-direction:column;gap:10px}
.opt{display:flex;gap:10px;align-items:flex-start;padding:12px 14px;border:1.5px solid var(--line);border-radius:10px;cursor:pointer;transition:.12s;font-size:15px;text-align:left;background:var(--card);width:100%}
.opt:hover{border-color:var(--blue);background:var(--blue-bg)}
.opt .letter{font-weight:700;color:var(--blue);flex-shrink:0}
.opt.picked{border-color:var(--blue);background:var(--blue-bg)}
.opt.right{border-color:var(--green);background:var(--green-bg)}
.opt.right .letter{color:var(--green)}
.opt.wrong{border-color:var(--red);background:var(--red-bg)}
.opt.wrong .letter{color:var(--red)}
.opt:disabled{cursor:default}
.opt.only-letter{justify-content:center;padding:10px}
.verdict{margin-top:14px;padding:11px 14px;border-radius:10px;font-weight:600;font-size:14px}
.verdict.ok{background:var(--green-bg);color:var(--green)}
.verdict.no{background:var(--red-bg);color:var(--red)}
.exp{margin-top:12px;border-top:1px dashed var(--line);padding-top:12px;font-size:14px;color:#374151;white-space:pre-wrap}
.exp .tag{display:inline-block;background:var(--blue-bg);color:var(--blue);font-size:12px;font-weight:700;padding:2px 10px;border-radius:6px;margin-bottom:8px}
.nav{display:flex;gap:10px;margin:16px 0}
.nav .btn{flex:1}
.tools{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.tools button{font-size:12.5px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--tx2)}
.tools button.on{border-color:var(--blue);color:var(--blue);background:var(--blue-bg)}
.tools button.faved{color:var(--amber);border-color:var(--amber)}
/* 答题卡 */
.sheet{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:flex-end;justify-content:center;z-index:50}
.sheet.open{display:flex}
.sheet .panel{background:var(--card);border-radius:16px 16px 0 0;padding:20px;max-width:860px;width:100%;max-height:72vh;overflow:auto}
.sheet h3{margin-bottom:12px;font-size:15px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(44px,1fr));gap:8px}
.grid button{aspect-ratio:1;border-radius:8px;border:1px solid var(--line);font-size:13px;background:var(--card);font-weight:600}
.grid button.done{background:var(--blue-bg);border-color:var(--blue);color:var(--blue)}
.grid button.ok{background:var(--green-bg);border-color:var(--green);color:var(--green)}
.grid button.bad{background:var(--red-bg);border-color:var(--red);color:var(--red)}
.grid button.cur{outline:2.5px solid var(--blue);outline-offset:1px}
.sheet .legend{display:flex;gap:16px;margin-top:12px;font-size:12px;color:var(--tx2)}
kbd{background:#eef1f5;border-radius:4px;padding:0 5px;font-size:11px;border:1px solid var(--line)}
@media(max-width:600px){.mods{grid-template-columns:1fr}}
</style>
</head>
<body>
<div id="app" class="wrap"></div>
<div class="sheet" id="sheet"><div class="panel" id="sheetPanel"></div></div>
<script>
const BANK = __BANK__;
const IMGS = __IMGS__;
const MOD_ORDER = Object.keys(BANK);   // 顺序由 config.MODULE_ORDER 决定
const STORE_KEY = 'bank_quiz_200_v1';

let store = JSON.parse(localStorage.getItem(STORE_KEY) || '{"ans":{},"favs":{}}');
function save(){ localStorage.setItem(STORE_KEY, JSON.stringify(store)); }

let S = {view:'home', mod:null, queue:[], idx:0, filter:'all', revealed:{}};

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function img(k){return IMGS[k]?`<img src="data:image/png;base64,${IMGS[k]}">`:'';}

/* 富文本：表格 + 图片 + 换行 */
function rich(text, mod){
  if(!text) return '';
  let out = '';
  const lines = text.split('\n');
  let i = 0;
  while(i < lines.length){
    const L = lines[i];
    if(L.trim() === '[TABLE]'){
      let rows = [];
      i++;
      while(i < lines.length && lines[i].trim() !== '[/TABLE]'){
        if(/^\|.+\|$/.test(lines[i].trim()) && !/^\|[-\s|]+\|$/.test(lines[i].trim())){
          rows.push(lines[i].trim().slice(1,-1).split('|').map(c=>c.trim()));
        }
        i++;
      }
      i++;
      if(rows.length){
        let t = '<table style="border-collapse:collapse;margin:8px 0;font-size:13px;width:100%">';
        rows.forEach((r,ri)=>{
          t += '<tr>';
          r.forEach(c=>{
            const tag = ri===0?'th':'td';
            const st = `border:1px solid #d4dce8;padding:5px 8px;text-align:center;${ri===0?'background:#eef4ff;font-weight:600':''}`;
            t += `<${tag} style="${st}">${esc(c)||'&nbsp;'}</${tag}>`;
          });
          t += '</tr>';
        });
        out += t + '</table>';
      }
    } else {
      let line = esc(L);
      line = line.replace(/@@IMG:([@\w.\-]+)@@/g, (m,k)=>img(k));
      out += line + '<br>';
      i++;
    }
  }
  return out;
}

function modStats(mod){
  const a = store.ans[mod] || {};
  const qs = BANK[mod].questions;
  let done=0, ok=0;
  qs.forEach(q=>{ if(a[q.num]){done++; if(a[q.num].ok) ok++;} });
  return {total: qs.length, done, ok};
}
function globalStats(){
  let done=0, ok=0, total=0;
  MOD_ORDER.forEach(m=>{const s=modStats(m); done+=s.done; ok+=s.ok; total+=s.total;});
  return {done, ok, total};
}

function renderHome(){
  const g = globalStats();
  let html = `<div class="home"><h1>📘 __H1__</h1>
  <div class="sub">__SUB__</div>
  <div class="mods">`;
  MOD_ORDER.forEach(m=>{
    const s = modStats(m);
    const pct = s.total? Math.round(s.done/s.total*100):0;
    html += `<div class="mod-card" onclick="startMod('${m}','all')">
      <h2>${BANK[m].name}</h2><div class="cnt">共 ${s.total} 题 · 已做 ${s.done} 题</div>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <div class="stat"><span>正确 <b>${s.ok}</b></span><span>正确率 <b>${s.done?Math.round(s.ok/s.done*100):0}%</b></span><span>错题 <b>${s.done-s.ok}</b></span></div>
    </div>`;
  });
  html += `</div><div class="gstats">总进度：${g.done}/${g.total} 题 · 答对 ${g.ok} 题 · 总正确率 ${g.done?Math.round(g.ok/g.done*100):0}%</div></div>`;
  document.getElementById('app').innerHTML = html;
}

function startMod(mod, filter){
  const qs = BANK[mod].questions;
  const a = store.ans[mod] || {};
  let list;
  if(filter==='wrong') list = qs.filter(q=>a[q.num] && !a[q.num].ok);
  else if(filter==='undone') list = qs.filter(q=>!a[q.num]);
  else if(filter==='redo') list = qs.filter(q=>a[q.num]);
  else list = qs;
  if(!list.length){ alert('没有符合条件的题目'); return; }
  if(filter==='random'){ list = [...list].sort(()=>Math.random()-.5); }
  S = {view:'quiz', mod, queue:list.map(q=>q.num), idx:0, filter, revealed:{}};
  renderQuiz();
}

function qByNum(mod, num){ return BANK[mod].questions.find(q=>q.num===num); }

function renderQuiz(){
  const mod = S.mod;
  const q = qByNum(mod, S.queue[S.idx]);
  const a = store.ans[mod] || {};
  const rec = a[q.num];
  const s = modStats(mod);
  const pickable = !rec && !S.revealed[q.num];
  const hasOpts = Object.keys(q.options||{}).length > 0 && Object.values(q.options).some(v=>v.trim());

  let html = `<div class="top">
    <button class="btn ghost back" onclick="S.view='home';renderHome()">← 首页</button>
    <span class="mname">${BANK[mod].name}</span>
    <span class="pos">${S.idx+1} / ${S.queue.length} 题 · 已做${s.done} 对${s.ok}</span>
  </div>
  <div class="pbar"><i style="width:${Math.round((S.idx+1)/S.queue.length*100)}%"></i></div>
  <div class="tools">
    <button class="${S.filter==='all'?'on':''}" onclick="startMod('${mod}','all')">全部</button>
    <button class="${S.filter==='undone'?'on':''}" onclick="startMod('${mod}','undone')">未做</button>
    <button class="${S.filter==='wrong'?'on':''}" onclick="startMod('${mod}','wrong')">错题</button>
    <button class="${S.filter==='random'?'on':''}" onclick="startMod('${mod}','random')">随机</button>
    <button class="${(store.favs[mod]||[]).includes(q.num)?'faved':''}" onclick="toggleFav(${q.num})">${(store.favs[mod]||[]).includes(q.num)?'★ 已收藏':'☆ 收藏'}</button>
  </div>`;

  if(q.material){
    html += `<div class="material"><h3>📄 资料${'一二三四五六七八'[countMat(q.num)-1] || ''}（本题根据以下材料作答）<span class="fold" onclick="this.closest('.material').classList.toggle('hide')">收起/展开</span></h3>
    <div class="matbody">${rich(q.material, mod)}</div></div>`;
  }

  html += `<div class="card">
    <div style="color:var(--tx2);font-size:12.5px;margin-bottom:6px">第 ${q.num} 题</div>
    <div class="stem">${rich(q.stem, mod)}</div>
    ${(q.stemImgs||[]).map(k=>img(k)).join('')}
    ${q.mergedImg?img(q.mergedImg):''}
    ${q.origImg?img(q.origImg):''}
    <div class="opts">`;

  const letters = ['A','B','C','D'];
  letters.forEach(L=>{
    const text = (q.options||{})[L] || '';
    let cls = 'opt';
    if(!hasOpts) cls += ' only-letter';
    if(rec){ if(L===rec.pick) cls += rec.ok?' right':' wrong'; if(L===q.answer && !rec.ok) cls += ' right'; }
    else if(S.revealed[q.num] && L===q.answer) cls += ' right';
    html += `<button class="${cls}" ${pickable?`onclick="pick('${L}')"`:'disabled'}>
      <span class="letter">${L}.</span><span>${esc(text)}</span></button>`;
  });
  html += `</div>`;

  if(rec){
    html += rec.ok
      ? `<div class="verdict ok">✔ 回答正确</div>`
      : `<div class="verdict no">✘ 回答错误，正确答案：${q.answer}</div>`;
  } else if(S.revealed[q.num]){
    html += `<div class="verdict ok">正确答案：${q.answer}</div>`;
  }
  if(rec || S.revealed[q.num]){
    html += `<div class="exp"><span class="tag">解析</span><br>${rich(q.explanation, mod)}</div>`;
  } else if(!pickable){}
  html += `</div>`;

  html += `<div class="nav">
    <button class="btn ghost" ${S.idx===0?'disabled':''} onclick="move(-1)">上一题</button>
    ${rec||S.revealed[q.num]
      ? `<button class="btn" onclick="move(1)">${S.idx===S.queue.length-1?'完成':'下一题'}</button>`
      : `<button class="btn ghost" onclick="reveal()">直接看答案</button>
         <button class="btn" onclick="move(1)" ${S.idx===S.queue.length-1?'disabled':''}>跳过</button>`}
    <button class="btn ghost" onclick="openSheet()">答题卡</button>
  </div>`;
  document.getElementById('app').innerHTML = html;
  const mat = document.querySelector('.material .matbody');
  if(mat && S.idx % 5 !== 0) mat.style.display = 'none';
  window.scrollTo(0,0);
}

function countMat(num){
  const qs = BANK[S.mod].questions.filter(q=>q.material);
  const sorted = [...qs].sort((a,b)=>a.num-b.num);
  for(let i=sorted.length-1;i>=0;i--){ if(num>=sorted[i].num) return i+1; }
  return 1;
}

function pick(L){
  const mod=S.mod, q=qByNum(mod, S.queue[S.idx]);
  if(!store.ans[mod]) store.ans[mod]={};
  store.ans[mod][q.num] = {pick:L, ok:L===q.answer};
  save(); renderQuiz();
}
function reveal(){
  const q=qByNum(S.mod, S.queue[S.idx]);
  S.revealed[q.num]=true; renderQuiz();
}
function move(d){
  if(S.idx+d<0||S.idx+d>=S.queue.length){ if(d>0){renderHome();S.view='home';} return; }
  S.idx+=d; renderQuiz();
}
function toggleFav(num){
  if(!store.favs[S.mod]) store.favs[S.mod]=[];
  const arr=store.favs[S.mod];
  const i=arr.indexOf(num);
  if(i>=0) arr.splice(i,1); else arr.push(num);
  save(); renderQuiz();
}
function openSheet(){
  const mod=S.mod, a=store.ans[mod]||{};
  let g='<div class="grid">';
  S.queue.forEach((num,i)=>{
    const r=a[num];
    let cls='';
    if(r) cls = r.ok?'ok':'bad';
    else if(S.revealed[num]) cls='done';
    if(i===S.idx) cls+=' cur';
    g+=`<button class="${cls}" onclick="S.idx=${i};closeSheet();renderQuiz()">${num}</button>`;
  });
  g+='</div>';
  document.getElementById('sheetPanel').innerHTML =
    `<h3>答题卡（${BANK[mod].name} · 本组 ${S.queue.length} 题）</h3>${g}
     <div class="legend"><span>■ 绿=对</span><span>■ 红=错</span><span>■ 蓝=已看</span><span>点击题号跳转</span>
     <span style="margin-left:auto">快捷键：<kbd>A-D</kbd>作答 <kbd>←→</kbd>翻题</span></div>`;
  document.getElementById('sheet').classList.add('open');
}
function closeSheet(){ document.getElementById('sheet').classList.remove('open'); }
document.getElementById('sheet').addEventListener('click', e=>{ if(e.target.id==='sheet') closeSheet(); });

document.addEventListener('keydown', e=>{
  if(S.view!=='quiz') return;
  if(document.getElementById('sheet').classList.contains('open')){ if(e.key==='Escape') closeSheet(); return; }
  const q = qByNum(S.mod, S.queue[S.idx]);
  const rec = (store.ans[S.mod]||{})[q.num];
  if('abcdABCD'.includes(e.key) && !rec && !S.revealed[q.num]) pick(e.key.toUpperCase());
  if(e.key==='ArrowRight') move(1);
  if(e.key==='ArrowLeft') move(-1);
});

renderHome();
</script>
</body>
</html>'''

if __name__ == '__main__':
    build()
