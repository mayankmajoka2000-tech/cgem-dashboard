"""C-GEM v99r online site: three working tools at the end of the "SDG, Social & Economics" tab.

  1. Project finder (buyers): every project that reports SDG goals, filterable by goal, country, sector, registry, stage; CSV download of the filtered list.
  2. Opportunity map (investors): Indian states by SDG India Index score against the carbon projects they host, with the under-served states ranked.
  3. Compare two states (classrooms): side-by-side SDG score, projects, credits and goals claimed, with discussion questions.
Tool 1 reads a project-level table (sdg_projects); tools 2 and 3 read the existing sdg_tab. Screening views from public registry data, not advice."""
import copy
import html as H
import json

from patch_v99p_sdg import COLS, TABLE, TAB_ID, COMMON_CSS, COMMON_JS, md
from patch_v99q_soc import stage

PTABLE = 'sdg_projects'
PCOLS = ['name', 'reg', 'pid', 'ctry', 'st', 'sec', 'goals', 'stg', 'iss', 'ret', 'rrep', 'url']
STATE_IDX = [['Andaman and Nicobar Islands', 58, 70], ['Andhra Pradesh', 64, 74], ['Arunachal Pradesh', 51, 65], ['Assam', 49, 65], ['Bihar', 48, 57], ['Chandigarh', 68, 77],
             ['Chhattisgarh', 58, 67], ['Dadra and Nagar Haveli and Daman and Diu', 57, 66], ['Delhi', 62, 70], ['Goa', 64, 77], ['Gujarat', 64, 74], ['Haryana', 55, 72],
             ['Himachal Pradesh', 69, 77], ['Jammu and Kashmir', 53, 74], ['Jharkhand', 50, 62], ['Karnataka', 64, 75], ['Kerala', 69, 79], ['Ladakh', None, 65],
             ['Lakshadweep', 62, 66], ['Madhya Pradesh', 52, 67], ['Maharashtra', 64, 73], ['Manipur', 59, 72], ['Meghalaya', 52, 63], ['Mizoram', 59, 72],
             ['Nagaland', 51, 63], ['Odisha', 51, 66], ['Puducherry', 65, 74], ['Punjab', 60, 76], ['Rajasthan', 59, 67], ['Sikkim', 58, 76], ['Tamil Nadu', 66, 78],
             ['Telangana', 61, 74], ['Tripura', 55, 71], ['Uttar Pradesh', 42, 67], ['Uttarakhand', 60, 79], ['West Bengal', 56, 70]]


def build_projects(con):
    con.execute(f'DROP TABLE IF EXISTS {PTABLE}')
    con.execute(f'CREATE TABLE {PTABLE} (name TEXT, reg TEXT, pid TEXT, ctry TEXT, st TEXT, sec TEXT, goals TEXT, stg INTEGER, iss REAL, ret REAL, rrep INTEGER, url TEXT)')
    goals = {}
    for k, g in con.execute('SELECT DISTINCT project_key, sdg_number FROM sdgs ORDER BY 1, 2'):
        goals.setdefault(k, []).append(int(g))
    rows = []
    for k, nm, reg, pid, ctry, st, sec, rs, vs, iss, ret, rr, u1, u2 in con.execute(
            "SELECT project_key, project_name, registry, project_id, country, adm1_name, sector, registry_status, voluntary_status, credits_issued, credits_retired, "
            "credits_retired_reported, registry_page, source_link FROM projects WHERE registry <> 'Unknown registry'"):
        if k not in goals:
            continue
        url = u1 if (u1 or '').startswith('http') else (u2 if (u2 or '').startswith('http') else '')
        rows.append(((nm or '')[:110], reg, pid or '', ctry or '', st or '', sec or '', ','.join(map(str, goals[k])), stage(rs, vs, iss or 0),
                     float(iss or 0), float(ret or 0), 1 if ret is not None else 0, url))
    con.executemany(f'INSERT INTO {PTABLE} VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    con.commit()
    print('v99r: project finder rows', len(rows))


# ---------------------------------------------------------------- 1. project finder
FIND_CSS = """
.bar{display:grid;grid-template-columns:1.4fr repeat(4,1fr);gap:8px;margin-bottom:10px}
.bar input,.bar select{width:100%;box-sizing:border-box;border:1px solid #d9dcd2;border-radius:8px;padding:7px 9px;font:500 12.5px Geist,Inter,Arial,sans-serif;background:#fff;color:#222}
.gl{display:flex;gap:5px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.gl b{font-size:11px;color:#777;margin-right:4px;font-weight:600}
.gc{border:1px solid #d9dcd2;background:#fff;border-radius:7px;min-width:30px;height:26px;font:800 11px 'Geist Mono',ui-monospace,Menlo,monospace;cursor:pointer;padding:0 6px;color:#555}
.gc.on{color:#fff;border-color:transparent}
.sm{display:flex;gap:18px;flex-wrap:wrap;align-items:center;background:#f4f7f0;border-radius:10px;padding:8px 12px;margin-bottom:8px;font-size:12.5px}
.sm b{font:700 13px 'Geist Mono',ui-monospace,Menlo,monospace;color:#173F0F}
.sm .sp{margin-left:auto;display:flex;gap:6px}
.btn{border:1px solid #265E30;background:#fff;color:#265E30;border-radius:8px;padding:6px 12px;font:600 12px Geist,Inter,Arial,sans-serif;cursor:pointer}
.btn.f{background:#265E30;color:#fff}
.hd,.r{display:grid;grid-template-columns:minmax(0,2.6fr) minmax(0,1.4fr) minmax(0,1.2fr) minmax(0,1.5fr) 110px 78px 70px;gap:10px;align-items:center}
.hd{padding:0 8px 6px;font-size:10.5px;color:#7a8270;text-transform:uppercase;letter-spacing:.05em;font-weight:600;position:sticky;top:0;background:#fff;z-index:2;border-bottom:1px solid #eef0e9}
.sc{max-height:330px;overflow-y:auto;border-bottom:1px solid #eef0e9}
.r{padding:7px 8px;border-radius:8px;font-size:12px;line-height:1.3}.r:nth-child(even){background:#f8faf5}
.r .n{font-weight:600;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.r .n a{color:#173F0F;text-decoration:none}.r .n a:hover{text-decoration:underline}
.r small{display:block;color:#8a9080;font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.g{display:flex;gap:3px;flex-wrap:wrap}.g i{display:inline-block;min-width:18px;height:18px;border-radius:5px;text-align:center;font:800 10px/18px 'Geist Mono',ui-monospace,Menlo,monospace}
.st{display:inline-block;border-radius:999px;padding:2px 8px;font-size:10.5px;font-weight:600;color:#fff}
.v{font:600 11.5px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.hn{font-size:11px;color:#888;margin:8px 0 0;line-height:1.5}
@media (max-width:1000px){.bar{grid-template-columns:1fr 1fr}.hd{display:none}.r{grid-template-columns:1fr 90px}}
"""
FIND_JS = r"""
var STG={1:['Issuing credits','#265E30'],2:['Registered, no credits','#6B9E4A'],3:['Listed or pipeline','#C98A1F'],4:['Stopped','#B85829'],5:['Not recorded','#9aa08f']};
var P=D.filter(function(r){return r.name!==undefined});
P.forEach(function(r){r.g=String(r.goals||'').split(',').filter(Boolean).map(Number);r.iss=+r.iss||0;r.ret=+r.ret||0;r.stg=+r.stg||5});
var F={q:'',c:'',s:'',r:'',t:'',sc:'World',gs:[],all:true,sort:'iss'};
function uniq(k,sc){var m={};P.forEach(function(r){if(sc&&!sc(r))return;m[r[k]]=(m[k+r[k]]||0)+1;});return Object.keys(m).filter(function(x){return x&&x!=='undefined'})}
function opts(list,cur,all){return '<option value="">'+all+'</option>'+list.sort().map(function(x){return '<option'+(x===cur?' selected':'')+'>'+esc(x)+'</option>'}).join('')}
function match(r){
  if(F.sc==='India'&&r.ctry!=='India')return false;
  if(F.c&&r.ctry!==F.c)return false;if(F.s&&r.sec!==F.s)return false;if(F.r&&r.reg!==F.r)return false;if(F.t&&String(r.stg)!==F.t)return false;
  if(F.gs.length){var ok=F.all?F.gs.every(function(g){return r.g.indexOf(g)>-1}):F.gs.some(function(g){return r.g.indexOf(g)>-1});if(!ok)return false}
  if(F.q){var t=(r.name+' '+r.reg+' '+r.pid+' '+r.ctry+' '+r.st).toLowerCase();if(t.indexOf(F.q.toLowerCase())<0)return false}
  return true}
function csv(rows){var h=['Project','Registry','Project ID','Country','State','Sector','SDG goals','Stage','Credits issued','Credits retired','Registry link'];
  var q=function(x){x=String(x==null?'':x);return /[",\n]/.test(x)?'"'+x.replace(/"/g,'""')+'"':x};
  return [h.join(',')].concat(rows.map(function(r){return [r.name,r.reg,r.pid,r.ctry,r.st,r.sec,r.g.join(' '),STG[r.stg][0],Math.round(r.iss),r.rrep?Math.round(r.ret):'',r.url].map(q).join(',')})).join('\n')}
var built=false;
function shell(){
  var ctry=uniq('ctry'),sec=uniq('sec'),reg=uniq('reg');
  document.getElementById('app').innerHTML='<div class="pills"><button class="pill on" data-sc="World">World</button><button class="pill" data-sc="India">India only</button></div>'
   +'<div class="bar"><input id="q" placeholder="Search name, ID, state, registry"><select id="c">'+opts(ctry,'','All countries')+'</select><select id="s">'+opts(sec,'','All sectors')+'</select><select id="r">'+opts(reg,'','All registries')+'</select>'
   +'<select id="t"><option value="">All stages</option>'+[1,2,3,4,5].map(function(k){return '<option value="'+k+'">'+STG[k][0]+'</option>'}).join('')+'</select></div>'
   +'<div class="gl"><b>Goals</b>'+SDG.slice(1).map(function(g,i){return '<button class="gc" data-g="'+(i+1)+'" title="'+esc(g[0])+'">'+(i+1)+'</button>'}).join('')+'<button class="pill" id="mode" style="padding:4px 10px;font-size:11px">must claim all selected</button><button class="pill" id="clr" style="padding:4px 10px;font-size:11px">Clear</button></div>'
   +'<div id="out"></div>';
  var on=function(id,ev,fn){document.getElementById(id).addEventListener(ev,fn)};
  on('q','input',function(e){F.q=e.target.value;draw()});on('c','change',function(e){F.c=e.target.value;draw()});on('s','change',function(e){F.s=e.target.value;draw()});on('r','change',function(e){F.r=e.target.value;draw()});on('t','change',function(e){F.t=e.target.value;draw()});
  on('mode','click',function(){F.all=!F.all;document.getElementById('mode').textContent=F.all?'must claim all selected':'claims any selected';draw()});
  on('clr','click',function(){F.gs=[];F.q='';F.c=F.s=F.r=F.t='';['q','c','s','r','t'].forEach(function(i){document.getElementById(i).value=''});draw()});
  Array.prototype.forEach.call(document.querySelectorAll('.gc'),function(b){b.onclick=function(){var g=+b.getAttribute('data-g'),i=F.gs.indexOf(g);if(i>-1)F.gs.splice(i,1);else F.gs.push(g);draw()}});
  Array.prototype.forEach.call(document.querySelectorAll('[data-sc]'),function(b){b.onclick=function(){F.sc=b.getAttribute('data-sc');Array.prototype.forEach.call(document.querySelectorAll('[data-sc]'),function(x){x.classList.toggle('on',x===b)});draw()}});
}
var SORTS={iss:function(a,b){return b.iss-a.iss},ret:function(a,b){return (b.rrep?b.ret/Math.max(b.iss,1):-1)-(a.rrep?a.ret/Math.max(a.iss,1):-1)},name:function(a,b){return a.name.localeCompare(b.name)}};
function draw(){
  if(!built){shell();built=true}
  Array.prototype.forEach.call(document.querySelectorAll('.gc'),function(b){var g=+b.getAttribute('data-g'),on=F.gs.indexOf(g)>-1;b.classList.toggle('on',on);b.style.background=on?SDG[g][1]:'#fff'});
  var rows=P.filter(match).sort(SORTS[F.sort]);var iss=0,ret=0,rb=0;rows.forEach(function(r){iss+=r.iss;if(r.rrep){ret+=r.ret;rb+=r.iss}});
  var shown=rows.slice(0,400);
  var h='<div class="sm"><span><b>'+ni(rows.length)+'</b> projects</span><span><b>'+fm(iss)+'</b> credits issued</span><span><b>'+(rb?Math.round(100*ret/rb)+'%':'n/a')+'</b> retired (where reported)</span>'
   +'<span class="sp"><select id="so" style="border:1px solid #d9dcd2;border-radius:8px;padding:5px 8px;font:500 12px Geist,Arial"><option value="iss"'+(F.sort==='iss'?' selected':'')+'>Sort: most credits issued</option><option value="ret"'+(F.sort==='ret'?' selected':'')+'>Sort: highest retirement rate</option><option value="name"'+(F.sort==='name'?' selected':'')+'>Sort: name</option></select><button class="btn f" id="dl">Download CSV</button></span></div>'
   +'<div class="sc"><div class="hd"><span>Project</span><span>Location</span><span>Sector</span><span>SDG goals</span><span>Stage</span><span style="text-align:right">Issued</span><span style="text-align:right">Retired</span></div>'
   +(shown.length?shown.map(function(r){var s=STG[r.stg];
     return '<div class="r"><div class="n" title="'+esc(r.name)+'">'+(r.url?'<a href="'+esc(r.url)+'" target="_blank" rel="noopener">'+esc(r.name)+'</a>':esc(r.name))+'<small><span>'+esc(r.reg)+'</span> '+esc(r.pid)+'</small></div><div><span>'+esc(r.ctry)+'</span><small>'+esc(r.st)+'</small></div><div>'+esc(r.sec)+'</div>'
      +'<div class="g">'+r.g.map(function(g){return '<i style="background:'+SDG[g][1]+';color:'+ink(SDG[g][1])+'" title="'+esc(SDG[g][0])+'">'+g+'</i>'}).join('')+'</div><div><span class="st" style="background:'+s[1]+'">'+s[0]+'</span></div><div class="v">'+(r.iss?fm(r.iss):'0')+'</div><div class="v">'+(r.rrep?fm(r.ret):'n/a')+'</div></div>'}).join(''):'<div class="r"><div class="n">No project matches these filters.</div></div>')
   +'</div><div class="hn">'+(rows.length>400?'Showing the first 400 of '+ni(rows.length)+' (the download holds all). ':'')+'Scroll inside the table for more rows. Only projects whose registry publishes SDG goals are listed, so absence here does not mean a project has no co-benefits. Stage is read from registry status text. Retired shows credits used, where the registry reports it. Not investment or purchasing advice: check each registry page and the project documents.</div>';
  document.getElementById('out').innerHTML=h;
  document.getElementById('so').onchange=function(e){F.sort=e.target.value;draw()};
  document.getElementById('dl').onclick=function(){var b=new Blob(['﻿'+csv(rows)],{type:'text/csv'});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='cgem_sdg_projects.csv';document.body.appendChild(a);a.click();setTimeout(function(){a.remove()},500)};
}
draw();
"""

# ---------------------------------------------------------------- 2. opportunity map
OPP_CSS = """
.ins{border-left:4px solid #C98A1F;background:#FFF9EC;border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5;margin-bottom:12px}
.g2{display:grid;grid-template-columns:minmax(380px,1.1fr) 1fr;gap:16px}
.pn{border:1px solid #e3e6dc;border-radius:12px;padding:12px 14px;background:#fbfcf9}
.pn h3{margin:0 0 3px;font:700 11px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;color:#333}.pn .sb{margin:0 0 8px;font-size:11px;color:#777}
svg{display:block;width:100%;height:auto}svg text{font-family:Geist,Inter,Arial,sans-serif;font-size:10.5px;fill:#555}
svg circle{cursor:pointer}
.cr{display:grid;grid-template-columns:24px minmax(0,1.5fr) 44px 58px 70px minmax(0,1.6fr);gap:8px;align-items:center;padding:5px 6px;font-size:12px}
.cr:nth-child(even){background:#f4f7f0}.cr .v{font:600 11.5px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.ch{position:sticky;top:0;background:#fff;color:#7a8270;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;z-index:2}
.cr .k{color:#8a9080;font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.cp{display:inline-block;min-width:18px;height:18px;border-radius:5px;text-align:center;font:800 10px/18px 'Geist Mono',ui-monospace,Menlo,monospace;margin-right:3px}
.sc{max-height:300px;overflow-y:auto;border-bottom:1px solid #eef0e9}
.hn{font-size:11px;color:#888;margin:8px 0 0;line-height:1.5}
.lg{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:#555;margin-top:4px}.lg i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}
@media (max-width:1000px){.g2{grid-template-columns:1fr}}
"""
OPP_JS = r"""
var IDX=__IDX__;
function draw(){
  var T={},I={},G={};
  pick('is','India').forEach(function(r){T[r.a]=r});
  pick('sd','India',function(r){return r.b==='state'}).forEach(function(r){if(r.a==='0')I[r.c]=r.n;else(G[r.c]=G[r.c]||{})[r.a]=r.n});
  var S=IDX.map(function(x){var t=T[x[0]]||{n:0,iss:0};return {s:x[0],sc:x[2],p:t.n,iss:t.iss,sd:I[x[0]]||0,g:G[x[0]]||{}}});
  var ps=S.map(function(s){return s.p}).sort(function(a,b){return a-b}),med=ps[Math.floor(ps.length/2)],avg=71;
  S.forEach(function(s){s.opp=s.sc<avg&&s.p<=med});
  var W=520,H=390,L=46,B=44,Tm=14,R=14,mx=Math.log10(1000),mn=0;
  var X=function(v){return L+(v-52)/(82-52)*(W-L-R)},Y=function(p){return Tm+(1-(Math.log10(p+1)-mn)/(mx-mn))*(H-Tm-B)};
  var svg='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="SDG score against carbon projects by state">'
   +'<rect x="'+L+'" y="'+Y(med)+'" width="'+(X(avg)-L)+'" height="'+(H-B-Y(med))+'" fill="#B85829" opacity=".08"/>'
   +[52,58,64,70,76,82].map(function(v){return '<text x="'+X(v)+'" y="'+(H-B+14)+'" text-anchor="middle">'+v+'</text><line x1="'+X(v)+'" x2="'+X(v)+'" y1="'+Tm+'" y2="'+(H-B)+'" stroke="#eef0e9"/>'}).join('')
   +[0,10,100,1000].map(function(p){return '<text x="'+(L-6)+'" y="'+(Y(p)+4)+'" text-anchor="end">'+p+'</text><line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(p)+'" y2="'+Y(p)+'" stroke="#eef0e9"/>'}).join('')
   +'<line x1="'+X(avg)+'" x2="'+X(avg)+'" y1="'+Tm+'" y2="'+(H-B)+'" stroke="#888" stroke-dasharray="4 3"/><line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(med)+'" y2="'+Y(med)+'" stroke="#888" stroke-dasharray="4 3"/>'
   +'<text x="'+(L+6)+'" y="'+(H-B-8)+'" style="fill:#B85829;font-weight:700">Under-served corner</text>'
   +S.map(function(s){var c=s.sc>=65?'#265E30':s.sc>=50?'#C98A1F':'#B85829';return '<circle cx="'+X(s.sc)+'" cy="'+Y(s.p)+'" r="'+(s.opp?6:4.5)+'" fill="'+(s.opp?'#B85829':c)+'" fill-opacity="'+(s.opp?.9:.55)+'" stroke="#fff"><title>'+esc(s.s)+': SDG score '+s.sc+', '+s.p+' projects</title></circle>'}).join('')
   +S.filter(function(s){return s.opp&&(s.sc<=66||s.p<=3)||s.p>=400}).map(function(s){return '<text x="'+(X(s.sc)+8)+'" y="'+(Y(s.p)+3)+'">'+esc(s.s.replace('Dadra and Nagar Haveli and Daman and Diu','DNH & DD'))+'</text>'}).join('')
   +'<text x="'+(L+(W-L-R)/2)+'" y="'+(H-4)+'" text-anchor="middle">SDG India Index score 2023-24 (higher = closer to the goals)</text><text transform="rotate(-90 12 '+(H/2)+')" x="12" y="'+(H/2)+'" text-anchor="middle">Carbon projects in the state (log scale)</text></svg>';
  var opp=S.filter(function(s){return s.opp}).sort(function(a,b){return a.sc-b.sc||a.p-b.p});
  var list=opp.map(function(s,i){var gs=Object.keys(s.g).map(function(g){return[+g,s.g[g]]}).sort(function(a,b){return b[1]-a[1]}).slice(0,3);
    return '<div class="cr"><span class="k">'+(i+1)+'</span><span>'+esc(s.s)+'</span><span class="v">'+s.sc+'</span><span class="v">'+ni(s.p)+'</span><span class="v">'+(s.iss?fm(s.iss):'none')+'</span><span>'+(gs.length?gs.map(function(a){return '<span class="cp" style="background:'+SDG[a[0]][1]+';color:'+ink(SDG[a[0]][1])+'" title="'+esc(SDG[a[0]][0])+'">'+a[0]+'</span>'}).join(''):'<span class="nt">no SDG data</span>')+'</span></div>'}).join('');
  var low=S.filter(function(s){return s.sc<avg}).length,lowp=S.filter(function(s){return s.sc<avg}).reduce(function(a,s){return a+s.p},0),tp=S.reduce(function(a,s){return a+s.p},0);
  document.getElementById('app').innerHTML='<div class="ins"><b>How to read it.</b> '+low+' of 36 states and territories score below India’s average of 71 on the SDG India Index, but together they host only <b>'+pc(lowp,tp,0)+'</b> of the carbon projects that have a known state. '
   +'<b>'+opp.length+'</b> sit in the shaded corner: below-average score <b>and</b> at most '+med+' projects (the median). Thin supply can reflect real constraints (security, land, grid, capacity), so treat this as a screening list, not a recommendation.</div>'
   +'<div class="g2"><div class="pn"><h3>SDG SCORE AGAINST CARBON PROJECTS</h3><p class="sb">One dot per state or territory. Hover a dot for its numbers.</p>'+svg+'<div class="lg"><span><i style="background:#B85829"></i>under-served corner</span><span><i style="background:#C98A1F"></i>performer band</span><span><i style="background:#265E30"></i>front-runner band</span></div></div>'
   +'<div class="pn"><h3>UNDER-SERVED STATES, LOWEST SCORE FIRST</h3><p class="sb">Score below 71 and projects at or under the median ('+med+').</p><div class="sc"><div class="cr ch"><span></span><span>State</span><span style="text-align:right">Score</span><span style="text-align:right">Projects</span><span style="text-align:right">Issued</span><span>Goals claimed</span></div>'+list+'</div><div class="hn">Showing the top 5; scroll inside the list for the rest. Goals claimed are the three most common among the state’s SDG-reporting projects. Scores: NITI Aayog SDG India Index 2023-24.</div></div></div>';
}
draw();
"""

# ---------------------------------------------------------------- 3. compare two states
CMP_CSS = """
.sel{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px;font-size:12.5px}
.sel select{border:1px solid #d9dcd2;border-radius:8px;padding:7px 10px;font:600 13px Geist,Inter,Arial,sans-serif;background:#fff;min-width:200px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pn{border:1px solid #e3e6dc;border-radius:12px;padding:14px;background:#fbfcf9}
.pn h2{margin:0 0 2px;font:800 18px Geist,Inter,Arial,sans-serif;color:#173F0F}
.bd{display:inline-block;border-radius:999px;padding:2px 10px;font-size:11px;font-weight:700;color:#fff;margin-bottom:10px}
.kv{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:12.5px;margin-bottom:12px}.kv b{font:700 13px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.gb{display:grid;grid-template-columns:24px 1fr 38px;gap:8px;align-items:center;margin:4px 0;font-size:12px}
.gb i{display:inline-block;min-width:22px;height:20px;border-radius:5px;text-align:center;font:800 10.5px/20px 'Geist Mono',ui-monospace,Menlo,monospace}
.gb .b{height:10px;border-radius:5px;background:#eef0ea;position:relative}.gb .b u{position:absolute;left:0;top:0;bottom:0;border-radius:5px;background:#265E30}
.gb span{text-align:right;font:600 11.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.h4{font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;color:#333;margin:6px 0 4px}
.ins{border-left:4px solid #C98A1F;background:#FFF9EC;border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5;margin:12px 0}
.qs{border:1px solid #e3e6dc;border-radius:12px;padding:12px 16px;background:#fff;font-size:12.5px;line-height:1.55}.qs ol{margin:4px 0 0;padding-left:18px}.qs li{margin-bottom:4px}
@media (max-width:900px){.g2{grid-template-columns:1fr}}
"""
CMP_JS = r"""
var IDX=__IDX__;
var A='Gujarat',B='Bihar';
function cat(x){return x>=65?['Front-runner','#265E30']:x>=50?['Performer','#C98A1F']:['Aspirant','#B85829']}
function card(name,T,I,G,tp,tsd){
  var x=IDX.filter(function(r){return r[0]===name})[0],t=T[name]||{n:0,iss:0},n=I[name]||0,c=cat(x[2]);
  var rank=IDX.slice().sort(function(a,b){return b[2]-a[2]}).map(function(r){return r[0]}).indexOf(name)+1;
  var gs=Object.keys(G[name]||{}).map(function(g){return[+g,G[name][g]]}).sort(function(a,b){return b[1]-a[1]}).slice(0,5);
  return '<div class="pn"><h2>'+esc(name)+'</h2><span class="bd" style="background:'+c[1]+'">'+c[0]+'</span><div class="kv">'
   +'<span>SDG India Index 2023-24</span><b>'+x[2]+' / 100</b><span>Rank among 36</span><b>'+rank+'</b><span>Change since 2018</span><b>'+(x[1]==null?'n/a':'+'+(x[2]-x[1]))+'</b>'
   +'<span>Carbon projects on the registries</span><b>'+ni(t.n)+'</b><span>Share of India’s located projects</span><b>'+pc(t.n,tp,1)+'</b><span>Credits issued</span><b>'+(t.iss?fm(t.iss):'none')+'</b><span>Projects that report SDG goals</span><b>'+ni(n)+'</b></div>'
   +'<div class="h4">GOALS MOST CLAIMED (SHARE OF ITS SDG-REPORTING PROJECTS)</div>'
   +(gs.length?gs.map(function(a){return '<div class="gb"><i style="background:'+SDG[a[0]][1]+';color:'+ink(SDG[a[0]][1])+'">'+a[0]+'</i><div class="b"><u style="width:'+(100*a[1]/n).toFixed(0)+'%"></u></div><span>'+Math.round(100*a[1]/n)+'%</span></div>'}).join(''):'<div class="nt">No project in this state reports SDG goals.</div>')+'</div>';
}
function draw(){
  var T={},I={},G={},tp=0;
  pick('is','India').forEach(function(r){T[r.a]=r;tp+=r.n});
  pick('sd','India',function(r){return r.b==='state'}).forEach(function(r){if(r.a==='0')I[r.c]=r.n;else(G[r.c]=G[r.c]||{})[r.a]=r.n});
  var names=IDX.map(function(r){return r[0]}).sort();
  var sel=function(id,cur){return '<select id="'+id+'">'+names.map(function(n){return '<option'+(n===cur?' selected':'')+'>'+esc(n)+'</option>'}).join('')+'</select>'};
  var xa=IDX.filter(function(r){return r[0]===A})[0],xb=IDX.filter(function(r){return r[0]===B})[0];
  var ta=(T[A]||{n:0}).n,tb=(T[B]||{n:0}).n;
  var ins='<div class="ins"><b>The contrast.</b> '+esc(A)+' scores '+xa[2]+' and hosts '+ni(ta)+' carbon projects; '+esc(B)+' scores '+xb[2]+' and hosts '+ni(tb)+'. '
   +(ta&&tb?(ta>=tb?esc(A)+' has '+(ta/tb).toFixed(1)+'x as many projects.':esc(B)+' has '+(tb/ta).toFixed(1)+'x as many projects.'):'')+' A higher SDG score does not by itself explain the gap: grids, state policy, developers and land all matter.</div>';
  var qs='<div class="qs"><b>Questions for discussion</b><ol><li>Carbon projects claim goals such as 7 (energy) and 13 (climate) almost everywhere. Which goals would a buyer who wants social co-benefits have to look for instead, and why are they rarer?</li>'
   +'<li>The states with the lowest SDG scores host very few projects. Is that a market failure, a bankability problem or a data gap? What evidence would settle it?</li>'
   +'<li>Within one registry, do SDG-reporting projects retire more credits than others? (See “Does doing good sell?” above.) What would a fair test look like?</li>'
   +'<li>A project that never reaches issuance delivers no credits. How should a university or buyer treat claimed goals on listed or stopped projects?</li></ol></div>';
  document.getElementById('app').innerHTML='<div class="sel"><label>Compare '+sel('a',A)+'</label><span>with</span>'+sel('b',B)+'</div><div class="g2">'+card(A,T,I,G,tp)+card(B,T,I,G,tp)+'</div>'+ins+qs;
  document.getElementById('a').onchange=function(e){A=e.target.value;draw()};document.getElementById('b').onchange=function(e){B=e.target.value;draw()};
}
draw();
"""

TOOLS = [
    # key, name, css, js, frame px, units, dataset ('p' = project table, 't' = sdg_tab)
    ('finder', 'Project finder: SDG-reporting projects by goal, place, sector and stage', FIND_CSS, FIND_JS, 600, 86, 'p'),
    ('opp', 'Where is the gap widest? SDG score against carbon projects, by Indian state', OPP_CSS, OPP_JS.replace('__IDX__', json.dumps(STATE_IDX)), 690, 97, 't'),
    ('cmp', 'Compare two Indian states: SDG score, projects and goals claimed', CMP_CSS, CMP_JS.replace('__IDX__', json.dumps(STATE_IDX)), 660, 94, 't'),
]
INTRO3 = {
    'finder': ('For buyers: find projects that claim the goals you care about',
               'Pick the goals, place, sector and stage you need and get a shortlist of projects with their registry links and credit volumes. The filtered list downloads as a CSV.', 11),
    'opp': ('For investors and funders: where is the gap widest?',
            'States that score below India’s average on the SDG India Index but host few carbon projects are where social need and project supply are furthest apart.', 11),
    'cmp': ('For classrooms and research: compare two states',
            'Choose any two states or territories to compare their SDG score, project count, credits and the goals their projects claim. The questions below the cards are written for seminars.', 11),
}


def frame(title, css, js, height):
    doc = ('<!doctype html><html><head><meta charset="utf-8"><style>' + COMMON_CSS + css + '</style></head><body><div id="app"></div><script>'
           'var D=({{stringify this}}).data;' + COMMON_JS + js + '</script></body></html>')
    attr = H.escape(doc, quote=True).replace('\n', '&#10;')
    return (f'<div class="cgxsdg"><div><iframe title="{H.escape(title, quote=True)}" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-downloads" srcdoc="{attr}" '
            f'style="width:100%;height:{height}px;border:0;display:block"></iframe></div></div>')


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        import sqlite3
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.core import Database
        con = sqlite3.connect('/app/cgem/cgem.db')
        build_projects(con)
        con.close()
        dbo = db.session.query(Database).filter(Database.database_name == 'C-GEM mastersheet').first()
        t_sdg = db.session.query(SqlaTable).filter(SqlaTable.table_name == TABLE).first()
        t_p = db.session.query(SqlaTable).filter(SqlaTable.table_name == PTABLE).first()
        if t_p is None:
            t_p = SqlaTable(table_name=PTABLE, schema='main', database=dbo)
            db.session.add(t_p)
            db.session.commit()
        t_p.fetch_metadata()
        db.session.commit()
        if t_sdg is None:
            print('v99r: sdg_tab dataset missing, skipped')
            return
        ref = db.session.query(Slice).filter(Slice.slice_name == 'Registry intelligence: the leading registries side by side').first()
        slices = {}
        for key, name, css, js, ph, units, ds in TOOLS:
            tbl = t_p if ds == 'p' else t_sdg
            cols = PCOLS if ds == 'p' else COLS
            sl = db.session.query(Slice).filter(Slice.slice_name == name).first()
            if sl is None:
                sl = Slice(slice_name=name, viz_type='handlebars', datasource_type='table', datasource_id=tbl.id)
                db.session.add(sl)
            p = json.loads(ref.params) if ref is not None else {'viz_type': 'handlebars'}
            for k in ('slice_id', 'handlebarsTemplate', 'timeseries_limit_metric', 'orderby', 'order_desc', 'extra_form_data'):
                p.pop(k, None)
            p.update({'viz_type': 'handlebars', 'datasource': f'{tbl.id}__table', 'query_mode': 'raw', 'all_columns': cols, 'groupby': [], 'metrics': [],
                      'adhoc_filters': [], 'row_limit': 20000, 'order_by_cols': [], 'styleTemplate': '', 'handlebarsTemplate': frame(name, css, js, ph)})
            sl.params = json.dumps(p)
            sl.viz_type = 'handlebars'
            sl.datasource_type = 'table'
            sl.datasource_id = tbl.id
            sl.query_context = None
            sl.description = 'SDG, social and economics tab: ' + name
            slices[key] = sl
        db.session.commit()
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            for sl in slices.values():
                if sl not in d.slices:
                    d.slices.append(sl)
            pos = json.loads(d.position_json)
            if TAB_ID not in pos or 'CHART-sdg-finder' in pos:
                continue
            base = ['ROOT_ID', 'GRID_ID', 'TABS-main', TAB_ID]
            rows = pos[TAB_ID]['children']
            ins_at = rows.index('ROW-sdg-note-m') if 'ROW-sdg-note-m' in rows else len(rows)
            new_rows = []
            for key, name, css, js, ph, units, ds in TOOLS:
                title, body, h = INTRO3[key]
                code, height = md(key, title, body, h)
                mid, rid = f'MARKDOWN-sdg-{key}', f'ROW-sdg-{key}-m'
                pos[mid] = {'children': [], 'id': mid, 'meta': {'code': code, 'height': height, 'width': 12}, 'parents': base + [rid], 'type': 'MARKDOWN'}
                pos[rid] = {'children': [mid], 'id': rid, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
                sl = slices[key]
                cid, crid = f'CHART-sdg-{key}', f'ROW-sdg-{key}-c'
                comp = copy.deepcopy(pos['CHART-sdg-kpi'])
                comp['id'] = cid
                comp['parents'] = base + [crid]
                comp['meta'] = {'chartId': sl.id, 'sliceName': sl.slice_name, 'height': units, 'width': 12, 'uuid': str(sl.uuid)}
                pos[cid] = comp
                pos[crid] = {'children': [cid], 'id': crid, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
                new_rows += [rid, crid]
            rows[ins_at:ins_at] = new_rows
            d.position_json = json.dumps(pos)
            print('v99r: added finder, opportunity map and state comparison')
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:  # never break the build
        import traceback
        traceback.print_exc()
        print('v99r skipped:', e)
