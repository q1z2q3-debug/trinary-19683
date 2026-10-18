# -*- coding: utf-8 -*-
"""生成完全离线、单文件可用的 三元九维19683 离线模型 HTML。
内嵌：27层卦规则 + 19683卦紧凑索引 + 前端规则引擎。
"""
import json, os

ROOT = "/home/user/Doubao/chats/38447794378988290/三元九维19683大模型"
KB = os.path.join(ROOT, "知识库", "三元九维19683_全集_规范校正版.json")
OUT = os.path.join(ROOT, "三元九维19683_离线模型.html")

d = json.load(open(KB, encoding="utf-8"))
recs = d["卦"]
layers = sorted(d["层卦规范"], key=lambda t: t["编号"])

# 紧凑索引 [id(上*10000+中*100+下), 卦名, 等级, 九爻串]
idx = [[r["上编号"]*10000 + r["中编号"]*100 + r["下编号"],
        r.get("复合卦名", ""), r.get("自适配等级", ""), "".join(r["九爻值"])] for r in recs]

LAYERS_JS = []
for t in layers:
    LAYERS_JS.append({
        "n": t["编号"], "name": t["规范名称"], "v": t["规范三爻"],
        "sem": t["逐位语义"]
    })

# 语义字典（前端规则引擎用）
SEM = {"D": "承载：按物理属性削减，能封存兜底，无分辨，不审定，不回灌",
       "R": "判定：审定/否决/回灌，分辨有序无序，输出评估信息，管控吞吐",
       "T": "增益：萌发原生动能，整形生发，对外释放信息"}
POS = ["底层", "中位", "顶层"]
ROLE = {"上": "大势", "中": "枢纽", "下": "底盘"}

html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>三元九维19683 离线模型</title>
<style>
  :root{--bg:#0f1220;--panel:#171b2e;--panel2:#1e2340;--line:#2a3050;--tx:#e8eaf6;--tx2:#aab0d0;--acc:#5b8cff;--acc2:#34d399;--gold:#f5c97b;--red:#ff7b7b;--purple:#a78bfa}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--tx);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7}
  .wrap{max-width:960px;margin:0 auto;padding:20px 16px 80px}
  header{text-align:center;padding:30px 0 8px}
  header h1{font-size:28px;letter-spacing:2px;background:linear-gradient(90deg,var(--acc),var(--purple),var(--acc2));-webkit-background-clip:text;background-clip:text;color:transparent}
  header .sub{color:var(--tx2);margin-top:8px;font-size:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:16px}
  .card h2{font-size:15px;margin-bottom:14px;color:var(--acc);display:flex;align-items:center;gap:8px}
  .card h2::before{content:"";width:4px;height:16px;background:var(--acc);border-radius:2px}
  .layers{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
  .layer{flex:1;min-width:150px}
  .layer label{display:block;font-size:12px;color:var(--tx2);margin-bottom:6px}
  .layer select{width:100%;background:var(--panel2);color:var(--tx);border:1px solid var(--line);border-radius:10px;padding:10px;font-size:15px}
  .btns{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
  button{background:linear-gradient(90deg,var(--acc),var(--purple));color:#fff;border:none;border-radius:10px;padding:11px 20px;font-size:15px;cursor:pointer;font-weight:600}
  button.ghost{background:var(--panel2);border:1px solid var(--line);color:var(--tx)}
  input[type=text]{width:100%;background:var(--panel2);color:var(--tx);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:14px}
  .searchrow{display:flex;gap:8px}
  .searchrow input{flex:1}
  .searchrow button{white-space:nowrap}
  .gua-title{font-size:21px;font-weight:700;margin-bottom:4px;color:var(--gold)}
  .gua-id{color:var(--tx2);font-size:13px;margin-bottom:10px}
  .seq{display:flex;gap:6px;justify-content:center;margin:10px 0}
  .seq .grp{display:flex;gap:6px}
  .seq .sep{color:var(--line);align-self:center;font-weight:700}
  .yao{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:16px;color:#0f1220}
  .yao.D{background:#6b7280}.yao.R{background:#f5c97b}.yao.T{background:#34d399}
  .badges{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
  .badge{font-size:12px;padding:4px 12px;border-radius:20px;border:1px solid var(--line);color:var(--tx2);background:var(--panel2)}
  .badge.lvl{color:var(--gold);border-color:var(--gold)}
  .section{margin-top:14px}
  .section h3{font-size:14px;color:var(--acc2);margin-bottom:6px;border-left:3px solid var(--acc2);padding-left:8px}
  .section p,.section li,.section div{font-size:13.5px;color:var(--tx);text-align:justify}
  .section ul{padding-left:20px}
  .analysis-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}
  .an-card{background:var(--panel2);border-radius:12px;padding:12px;text-align:center}
  .an-card .n{font-size:26px;font-weight:800}
  .an-card .l{font-size:12px;color:var(--tx2);margin-top:2px}
  .an-card.R .n{color:var(--gold)}.an-card.D .n{color:#9ca3af}.an-card.T .n{color:var(--acc2)}
  .balance{background:var(--panel2);border-radius:12px;padding:12px;margin-top:10px;font-size:13px;color:var(--tx)}
  .balance li{margin-left:18px;margin-top:4px}
  .table{width:100%;border-collapse:collapse;font-size:13px}
  .table th,.table td{border:1px solid var(--line);padding:7px 8px;text-align:center}
  .table th{background:var(--panel2);color:var(--acc);position:sticky;top:0}
  .dim{color:var(--tx2)}
  .hint{color:var(--tx2);font-size:12px;margin-top:8px}
  .flow{display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:13px}
  .flow .lbox{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:4px 10px;color:var(--tx2)}
  .flow .lbox b{color:var(--tx)}
  .flow .arr{color:var(--line)}
  footer{text-align:center;color:var(--tx2);font-size:12px;margin-top:30px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>三元九维 · 19683 离线模型</h1>
    <div class="sub">三层（上·中·下）× 三爻 × 三态（D承载 / R判定 / T增益）＝ 3⁹ ＝ 19683 卦 · 单文件可离线运行</div>
  </header>

  <div class="card">
    <h2>起卦推演（规则引擎）</h2>
    <div class="layers">
      <div class="layer"><label>上卦 · 大势</label><select id="selUp"></select></div>
      <div class="layer"><label>中卦 · 枢纽</label><select id="selMid"></select></div>
      <div class="layer"><label>下卦 · 底盘</label><select id="selLo"></select></div>
    </div>
    <div class="btns">
      <button onclick="query()">推演此卦</button>
      <button class="ghost" onclick="rand()">随机抽一卦</button>
    </div>
  </div>

  <div class="card">
    <h2>检索</h2>
    <div class="searchrow">
      <input id="q" type="text" placeholder="输入 编号(如 7-1-2)、卦名(如 全静)、或 9 爻(如 DDD DDR DDT)">
      <button onclick="search()">检索</button>
    </div>
    <div id="searchRes"></div>
  </div>

  <div id="result"></div>

  <div class="card">
    <h2>27 层卦规范表</h2>
    <div style="overflow:auto;max-height:400px">
      <table class="table" id="layerTable"><thead><tr><th>编号</th><th>名称</th><th>底·中·顶</th><th>判定</th><th>承载</th><th>增益</th></tr></thead><tbody></tbody></table>
    </div>
  </div>

  <footer>三元九维19683体系 · 离线规则生成模型 · 内嵌 19683 卦索引</footer>
</div>

<script>
const LAYERS = __LAYERS__;
const INDEX = __INDEX__;
const SEM = __SEM__;
const POS = __POS__;
const ROLE = __ROLE__;

function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');}
const byId = new Map(INDEX.map(r=>[r[0],r]));
const byName = new Map();
INDEX.forEach(r=>{ if(!byName.has(r[1])) byName.set(r[1],[]); byName.get(r[1]).push(r); });

function init(){
  const mk=(sel)=>{LAYERS.forEach(l=>sel.add(new Option(String(l.n).padStart(2,'0')+' · '+l.name, l.n)));};
  mk(document.getElementById('selUp'));mk(document.getElementById('selMid'));mk(document.getElementById('selLo'));
  document.getElementById('selUp').value=14;document.getElementById('selMid').value=27;document.getElementById('selLo').value=1;
  const tb=document.querySelector('#layerTable tbody');
  tb.innerHTML=LAYERS.map(l=>`<tr><td>${String(l.n).padStart(2,'0')}</td><td>${l.name}</td><td>${l.v.join('·')}</td><td>${l.v.filter(x=>x==='R').length}</td><td>${l.v.filter(x=>x==='D').length}</td><td>${l.v.filter(x=>x==='T').length}</td></tr>`).join('');
}

function nameOf(num,role){
  const t=LAYERS.find(l=>l.n===num);
  return t?t.name:'';
}
function valsOf(num){return LAYERS.find(l=>l.n===num).v.slice();}
function lvlOf(nR,nT,nD){
  if(nD===9)return '极弱';
  const s=nR+2*nT;
  if(s===0)return '极弱'; if(s<=2)return '弱'; if(s<=4)return '中等'; if(s<=6)return '较强'; if(s<=8)return '强'; return '极强';
}
function balance(v){
  const notes=[]; const up=v.slice(0,3),mid=v.slice(3,6),lo=v.slice(6,9);
  const cnt=x=>x.filter(c=>c==='R').length;
  if(cnt(up)===0&&up.filter(c=>c==='T').length===0)notes.push('上层纯承载：不读信息、不自知、不对外释放，成果滞留锁界。');
  if(cnt(up)>0&&up.filter(c=>c==='T').length===0)notes.push('上层有判定无增益：算得清但送不出去，价值在于内部存量纯度。');
  if(up.filter(c=>c==='T').length>0)notes.push('上层有增益单元：具备对外释放/生发的通道。');
  if(cnt(mid)===0&&mid.filter(c=>c==='T').length===0)notes.push('中层纯承载：对上行分量一律削减，判定与增益归零。');
  if(cnt(lo)===0&&lo.filter(c=>c==='T').length===0)notes.push('底层纯承载：无自发扰动，资源沉淀封存。');
  if(v.filter(c=>c==='R').length===0)notes.push('全卦零判定：分不清有序与无序。');
  if(v.filter(c=>c==='T').length===0)notes.push('全卦零增益：无撬动能力，只有消耗能力。');
  if(v.filter(c=>c==='D').length===9)notes.push('九爻全承载：全体系最安静的一卦，纯衰减构型。');
  return notes;
}
function yaoHTML(v){return v.map(c=>`<div class="yao ${c}">${c}</div>`).join('');}

function generate(s,m,x){
  const up=valsOf(s),mid=valsOf(m),lo=valsOf(x);
  const v=up.concat(mid).concat(lo);
  const order=[['下',x,lo],['中',m,mid],['上',s,up]];
  const parts=order.map(([role,num,val])=>{
    const t=LAYERS.find(l=>l.n===num);
    let lines=[`${role}卦（${ROLE[role]}）${t.name}【${val.join('·')}】：`];
    val.forEach((c,i)=>lines.push(`　${POS[i]}${c}：${SEM[c]}`));
    return lines.join('\n');
  });
  const nR=v.filter(c=>c==='R').length,nD=v.filter(c=>c==='D').length,nT=v.filter(c=>c==='T').length;
  const flow=order.slice().reverse().map(([role,num])=>`<span class="lbox"><b>${role}</b>${String(num).padStart(2,'0')}·${nameOf(num,role)}</span>`).join('<span class="arr">→</span>');
  const head=`<div class="card">
    <div class="gua-title">${esc((byId.get(s*10000+m*100+x)||['','','',''])[1]||'（规则生成）')}</div>
    <div class="gua-id">九爻编号 ${[s,m,x].map(x=>String(x).padStart(2,'0')).join('｜')} · 规则生成解读</div>
    <div class="flow">${flow}</div>
    <div class="seq"><div class="grp">${yaoHTML(v.slice(0,3))}</div><span class="sep">｜</span><div class="grp">${yaoHTML(v.slice(3,6))}</div><span class="sep">｜</span><div class="grp">${yaoHTML(v.slice(6,9))}</div></div>
    <div class="badges"><span class="badge">判定 ${nR}</span><span class="badge">承载 ${nD}</span><span class="badge">增益 ${nT}</span><span class="badge lvl">自适配 · ${lvlOf(nR,nT,nD)}</span></div>
    <div class="analysis-grid"><div class="an-card R"><div class="n">${nR}</div><div class="l">判定 R</div></div><div class="an-card D"><div class="n">${nD}</div><div class="l">承载 D</div></div><div class="an-card T"><div class="n">${nT}</div><div class="l">增益 T</div></div></div>
    <div class="section"><h3>逐层规则解读</h3><div style="white-space:pre-wrap">${esc(parts.join('\n\n'))}</div></div>
    <div class="section"><h3>制衡要点</h3><ul>${balance(v).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>
  </div>`;
  return head;
}

function query(){document.getElementById('result').innerHTML=generate(+document.getElementById('selUp').value,+document.getElementById('selMid').value,+document.getElementById('selLo').value);document.getElementById('result').scrollIntoView({behavior:'smooth'});}
function rand(){const r=INDEX[Math.floor(Math.random()*INDEX.length)];const s=Math.floor(r[0]/10000),m=Math.floor(r[0]/100)%100,x=r[0]%100;document.getElementById('result').innerHTML=generate(s,m,x);document.getElementById('result').scrollIntoView({behavior:'smooth'});}
function search(){
  const q=document.getElementById('q').value.trim();if(!q)return;
  let out=[];
  const m=q.match(/^(\d{1,2})\D*(\d{1,2})\D*(\d{1,2})$/);
  if(m){const s=+m[1],mm=+m[2],x=+m[3];if(s>=1&&s<=27&&mm>=1&&mm<=27&&x>=1&&x<=27){const r=byId.get(s*10000+mm*100+x);if(r)out=[r];}}
  else{
    const clean=q.replace(/[^DRT]/gi,'').toUpperCase();
    if(clean.length===9){out=INDEX.filter(r=>r[3]===clean);}
    if(out.length===0){INDEX.forEach(r=>{if(r[1].includes(q)&&out.length<20)out.push(r);});}
  }
  const box=document.getElementById('searchRes');
  if(!out.length){box.innerHTML=`<div class="hint">未找到匹配结果。</div>`;return;}
  box.innerHTML=`<div style="margin-top:10px">${out.map(r=>{
    const s=Math.floor(r[0]/10000),m=Math.floor(r[0]/100)%100,x=r[0]%100;
    return `<div style="background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-top:6px;cursor:pointer" onclick='document.getElementById("result").innerHTML=generate(${s},${m},${x});document.getElementById("result").scrollIntoView({behavior:"smooth"})'>
      <b>${[s,m,x].map(x=>String(x).padStart(2,'0')).join('｜')}</b> · ${esc(r[1])} <span class="dim">（自适配 ${esc(r[2])}）</span>
    </div>`;}).join('')}</div>`;
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')search();});
init();
</script>
</body>
</html>
"""

# 注入数据
html = html.replace("__LAYERS__", json.dumps(LAYERS_JS, ensure_ascii=False, separators=(",", ":")))
html = html.replace("__INDEX__", json.dumps(idx, ensure_ascii=False, separators=(",", ":")))
html = html.replace("__SEM__", json.dumps(SEM, ensure_ascii=False))
html = html.replace("__POS__", json.dumps(POS, ensure_ascii=False))
html = html.replace("__ROLE__", json.dumps(ROLE, ensure_ascii=False))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("离线模型已生成:", OUT)
print("体积: %.2f MB" % (os.path.getsize(OUT) / 1048576))
