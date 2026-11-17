"""C-GEM v99p online site: a new tab "SDG, Social & Economics".

Data: the sdgs and certifications tables behind the project registry records are summarised into one small table (sdg_tab).
Charts (each a self-contained page inside a chart frame, no network access):
  1. five headline numbers; 2. the 17 goals as an interactive constellation (world / India, click a goal for its sectors, registries, countries or states);
  3. a goal-by-sector heat map; 4. "Does doing good sell?", retirement rates by number of goals claimed and by social label;
  5. India's states ranked by SDG-reporting projects, with each state's signature goals.
Nothing here uses the C-GEM pricing model: only issued and retired credits as the registries report them."""
import copy
import html as H
import json

TAB_ID = 'TAB-sdg'
TAB_NAME = 'SDG, Social & Economics'
TABLE = 'sdg_tab'
SOCIAL = {
    'CCB': "label = 'CCB'",
    'S+ no-net-harm': "label = 'S+ no-net-harm'",
    'SDG+ label (any tier)': "label LIKE '%SDG+ label'",
    'Social Carbon': "label = 'Social Carbon'",
    'Gender responsive': "label = 'Gold Standard Gender Responsive'",
}
BANDS = [('1-2 goals', 1, 2), ('3-4 goals', 3, 4), ('5-6 goals', 5, 6), ('7 or more goals', 7, 99)]


def build_table(con):
    con.execute(f'DROP TABLE IF EXISTS {TABLE}')
    con.execute(f'CREATE TABLE {TABLE} (kind TEXT, a TEXT, b TEXT, c TEXT, scope TEXT, n INTEGER, iss REAL, ret REAL, retbase REAL)')
    con.execute('DROP TABLE IF EXISTS _sdg_p')
    # one row per project with its attributes and goal count
    con.execute("""CREATE TEMP TABLE _sdg_p AS
        SELECT p.project_key AS k, COALESCE(p.sector,'Not classified') AS sector, COALESCE(p.registry,'Unknown') AS registry, p.country AS country,
               CASE WHEN p.is_india='India' THEN 'India' ELSE 'World' END AS sc, p.adm1_name AS state,
               COALESCE(p.credits_issued,0) AS iss, COALESCE(p.credits_retired,0) AS ret,
               CASE WHEN p.credits_retired IS NOT NULL THEN COALESCE(p.credits_issued,0) ELSE 0 END AS rb,
               (SELECT COUNT(DISTINCT sdg_number) FROM sdgs s WHERE s.project_key = p.project_key) AS ng
        FROM projects p WHERE p.registry <> 'Unknown registry'""")
    con.execute('CREATE TEMP TABLE _sdg_pair AS SELECT DISTINCT project_key AS k, sdg_number AS g FROM sdgs')
    agg = 'COUNT(DISTINCT k), SUM(iss), SUM(ret), SUM(rb)'

    def ins(kind, a, b, c, scope_sql, where, frm):
        # scope 'World' = everything; 'India' = Indian projects only
        for scope, cond in (('World', '1=1'), ('India', "sc='India'")):
            con.execute(f"INSERT INTO {TABLE} SELECT '{kind}', {a}, {b}, {c}, '{scope}', {agg} FROM {frm} WHERE {where} AND {cond} GROUP BY 1,2,3,4,5")
    pj = '_sdg_pair x JOIN _sdg_p p ON p.k = x.k'
    for scope, cond in (('World', '1=1'), ('India', "sc='India'")):
        base = f"FROM _sdg_pair x JOIN _sdg_p p ON p.k = x.k WHERE {cond}"
        for dim, col, lim in (('sector', 'sector', 14), ('registry', 'registry', 8), ('country', 'country', 8), ('state', 'state', 60)):
            if dim == 'state' and scope == 'World':
                continue
            # per goal and for "any goal" (0)
            for goal_sql in ("CAST(x.g AS TEXT)", None):
                if goal_sql:
                    q = (f"SELECT {goal_sql}, '{dim}', {col}, '{scope}', COUNT(DISTINCT p.k), SUM(p.iss), SUM(p.ret), SUM(p.rb) {base} AND {col} IS NOT NULL GROUP BY 1,3")
                else:
                    q = (f"SELECT '0', '{dim}', {col}, '{scope}', COUNT(DISTINCT p.k), SUM(p.iss), SUM(p.ret), SUM(p.rb) FROM _sdg_p p WHERE p.ng > 0 AND {cond} AND {col} IS NOT NULL GROUP BY 1,3")
                rows = con.execute(q).fetchall()
                if dim != 'sector' and dim != 'state':
                    rows = sorted(rows, key=lambda r: -r[4])
                    keep = {}
                    out = []
                    for r in rows:
                        keep[r[0]] = keep.get(r[0], 0) + 1
                        if keep[r[0]] <= lim:
                            out.append(r)
                    rows = out
                con.executemany(f"INSERT INTO {TABLE} VALUES ('sd', ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        # all-goal totals and per-goal totals
        con.execute(f"INSERT INTO {TABLE} SELECT 'sd', CAST(x.g AS TEXT), 'all', '', '{scope}', COUNT(DISTINCT p.k), SUM(p.iss), SUM(p.ret), SUM(p.rb) {base} GROUP BY 2")
        con.execute(f"INSERT INTO {TABLE} SELECT 'sd', '0', 'all', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE ng > 0 AND {cond}")
        # breadth bands, and the projects with no SDG data as the baseline
        for name, lo, hi in BANDS:
            con.execute(f"INSERT INTO {TABLE} SELECT 'br', '{name}', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE ng BETWEEN {lo} AND {hi} AND {cond}")
        con.execute(f"INSERT INTO {TABLE} SELECT 'br', 'No SDG data', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE ng = 0 AND {cond}")
        # social labels
        con.execute('DROP TABLE IF EXISTS _sdg_soc')
        for name, w in SOCIAL.items():
            con.execute(f"INSERT INTO {TABLE} SELECT 'lb', '{name}', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE {cond} AND k IN (SELECT project_key FROM certifications WHERE {w})")
        anyw = ' OR '.join(f'({w})' for w in SOCIAL.values())
        con.execute(f"INSERT INTO {TABLE} SELECT 'lb', 'Any social label', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE {cond} AND k IN (SELECT project_key FROM certifications WHERE {anyw})")
        con.execute(f"INSERT INTO {TABLE} SELECT 'lb', 'No social label', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE {cond} AND k NOT IN (SELECT project_key FROM certifications WHERE {anyw})")
        # like for like: the same registry, projects with and without SDG data
        for g, w in (('sdg', 'ng > 0'), ('nosdg', 'ng = 0')):
            con.execute(f"INSERT INTO {TABLE} SELECT 'rg', registry, '{g}', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE {w} AND {cond} GROUP BY registry")
        con.execute(f"DELETE FROM {TABLE} WHERE kind = 'rg' AND scope = '{scope}' AND a IN (SELECT a FROM {TABLE} WHERE kind = 'rg' AND scope = '{scope}' GROUP BY a HAVING MIN(n) < 25 OR COUNT(*) < 2 OR SUM(retbase) < 1000)")
        # headline numbers
        con.execute(f"INSERT INTO {TABLE} SELECT 'kp', 'all', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE {cond}")
        con.execute(f"INSERT INTO {TABLE} SELECT 'kp', 'sdg', '', '', '{scope}', COUNT(*), SUM(iss), SUM(ret), SUM(rb) FROM _sdg_p WHERE ng > 0 AND {cond}")
        con.execute(f"INSERT INTO {TABLE} SELECT 'kp', 'tags', '', '', '{scope}', COUNT(*), 0, 0, 0 FROM _sdg_pair x JOIN _sdg_p p ON p.k = x.k WHERE {cond}")
    con.commit()


# ---------------------------------------------------------------- chart pages (JS and CSS run inside a sandboxed frame)
COMMON_CSS = """
html,body{margin:0;background:#fff;font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;color:#1b1b1b;font-size:12.5px}
body{padding:2px 2px 8px}
.mono{font-family:'Geist Mono',ui-monospace,Menlo,monospace}
.pills{display:flex;gap:6px;margin:0 0 12px;align-items:center;flex-wrap:wrap}
.pill{border:1px solid #d9dcd2;background:#fff;border-radius:999px;padding:6px 14px;font:600 12.5px Geist,Inter,Arial,sans-serif;color:#444;cursor:pointer}
.pill.on{background:#265E30;border-color:#265E30;color:#fff}
.pills .nt{margin-left:auto;font-size:11px;color:#888}
.nt{font-size:11px;color:#888}
"""

COMMON_JS = r"""
var SDG=[null,['No poverty','#E5243B'],['Zero hunger','#DDA63A'],['Good health','#4C9F38'],['Quality education','#C5192D'],['Gender equality','#FF3A21'],['Clean water','#26BDE2'],['Clean energy','#FCC30B'],['Decent work','#A21942'],['Industry & innovation','#FD6925'],['Reduced inequalities','#DD1367'],['Sustainable cities','#FD9D24'],['Responsible consumption','#BF8B2E'],['Climate action','#3F7E44'],['Life below water','#0A97D9'],['Life on land','#56C02B'],['Peace & justice','#00689D'],['Partnerships','#19486A']];
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function fm(x){x=+x||0;if(x>=1e9)return(x/1e9).toFixed(2).replace(/\.?0+$/,'')+'B';if(x>=1e6)return(x/1e6).toFixed(x>=1e8?0:1).replace(/\.0$/,'')+'M';if(x>=1e3)return Math.round(x/1e3)+'K';return Math.round(x)+''}
function ni(x){return Math.round(+x||0).toLocaleString('en-US')}
function pc(a,b,d){return b>0?(100*a/b).toFixed(d==null?0:d)+'%':'n/a'}
function num(r){r.n=+r.n||0;r.iss=+r.iss||0;r.ret=+r.ret||0;r.retbase=+r.retbase||0;return r}
D.forEach(num);
function pick(kind,scope,f){return D.filter(function(r){return r.kind===kind&&r.scope===scope&&(!f||f(r))})}
function ink(hex){var h=hex.replace('#','');var r=parseInt(h.substr(0,2),16),g=parseInt(h.substr(2,2),16),b=parseInt(h.substr(4,2),16);return(r*299+g*587+b*114)/1000>150?'#1b1b1b':'#fff'}
var SCOPE='World';
function pillsHtml(extra){return '<div class="pills"><button class="pill'+(SCOPE==='World'?' on':'')+'" data-s="World">World</button><button class="pill'+(SCOPE==='India'?' on':'')+'" data-s="India">India only</button>'+(extra||'')+'</div>'}
function bindScope(fn){Array.prototype.forEach.call(document.querySelectorAll('.pill[data-s]'),function(b){b.onclick=function(){SCOPE=b.getAttribute('data-s');fn()}})}
"""

KPI_CSS = """
#app{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.k{border:1px solid #e3e6dc;border-top:4px solid var(--c);border-radius:12px;padding:12px 14px;background:linear-gradient(180deg,#fff,#f8faf4)}
.k .v{font:800 28px/1.1 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:-.02em;color:#173F0F}
.k .l{font-weight:700;font-size:12.5px;margin:4px 0 3px}
.k .s{font-size:11px;color:#6b7266;line-height:1.35}
@media (max-width:900px){#app{grid-template-columns:repeat(2,1fr)}}
"""
KPI_JS = r"""
var K=function(s,a){return pick('kp',s,function(r){return r.a===a})[0]||{n:0,iss:0}};
var wa=K('World','all'),ws=K('World','sdg'),wt=K('World','tags'),ia=K('India','all'),is_=K('India','sdg');
var soc=pick('lb','World',function(r){return r.a==='Any social label'})[0]||{n:0};
var T=[['#2C7A3D',ni(ws.n),'projects report SDG goals',pc(ws.n,wa.n,1)+' of the '+ni(wa.n)+' projects in the dataset'],
 ['#4C9F38',(wt.n/Math.max(ws.n,1)).toFixed(1),'goals claimed per reporting project',ni(wt.n)+' goal tags in total'],
 ['#C98A1F',fm(ws.iss),'credits issued by SDG-reporting projects',pc(ws.iss,wa.iss,0)+' of all credits issued'],
 ['#0A97D9',ni(soc.n),'projects carry a social-impact label','CCB, SDG+, S+ no-net-harm, Social Carbon, Gender responsive'],
 ['#B85829',ni(is_.n),'Indian projects report SDG goals',pc(is_.n,ws.n,0)+' of all SDG-reporting projects; '+pc(is_.n,ia.n,0)+' of India’s own projects']];
document.getElementById('app').innerHTML=T.map(function(t){return '<div class="k" style="--c:'+t[0]+'"><div class="v">'+t[1]+'</div><div class="l">'+esc(t[2])+'</div><div class="s">'+esc(t[3])+'</div></div>'}).join('');
"""

CONST_CSS = """
#tiles{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}
.t{position:relative;border-radius:12px;padding:10px 11px 9px;cursor:pointer;color:var(--ink);background:var(--c);min-height:92px;border:0;text-align:left;font-family:inherit;transition:transform .15s,box-shadow .15s}
.t:hover{transform:translateY(-2px);box-shadow:0 6px 14px -8px rgba(0,0,0,.45)}
.t.on{box-shadow:0 0 0 3px #fff,0 0 0 5px var(--c)}
.t .g{font:800 22px/1 'Geist Mono',ui-monospace,Menlo,monospace}
.t .nm{font-weight:700;font-size:11.5px;margin:3px 0 6px;line-height:1.2;min-height:28px}
.t .bar{height:5px;border-radius:3px;background:rgba(255,255,255,.35);overflow:hidden}.t .bar i{display:block;height:100%;background:var(--ink);opacity:.85}
.t .c{font-size:11px;margin-top:5px;display:flex;justify-content:space-between;opacity:.95}
.t.sum{background:#F3F5EE;color:#1b1b1b;cursor:default}.t.sum:hover{transform:none;box-shadow:none}
.t.sum .g{font-size:22px;color:#173F0F}
.dt{margin-top:12px;border:1px solid #e3e6dc;border-radius:14px;background:#FBFBF8;overflow:hidden}
.dh{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--c);color:var(--ink)}
.dh .g{font:800 26px/1 'Geist Mono',ui-monospace,Menlo,monospace}.dh b{font-size:16px}.dh span{font-size:12px;opacity:.9;margin-left:auto}
.db{display:grid;grid-template-columns:1.05fr 1fr 1fr 1fr;gap:18px;padding:14px 16px}
.st{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.st div{border-left:3px solid var(--c);padding-left:9px}.st b{display:block;font:700 18px 'Geist Mono',ui-monospace,Menlo,monospace}.st span{font-size:11px;color:#666}
.ls h4{margin:0 0 7px;font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.09em;color:#333}
.ls .r{display:grid;grid-template-columns:1fr auto;gap:2px 8px;margin-bottom:7px;font-size:12px}
.ls .r span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ls .r b{font:600 11.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.ls .r i{grid-column:1/-1;height:5px;border-radius:3px;background:#eef0ea;overflow:hidden}.ls .r i u{display:block;height:100%;background:var(--c);opacity:.85}
@media (max-width:900px){#tiles{grid-template-columns:repeat(3,1fr)}.db{grid-template-columns:1fr 1fr}}
"""
CONST_JS = r"""
var SEL=0;
function draw(){
  var rows=pick('sd',SCOPE,function(r){return r.b==='all'&&r.a!=='0'}),by={};rows.forEach(function(r){by[+r.a]=r});
  var tot=pick('sd',SCOPE,function(r){return r.b==='all'&&r.a==='0'})[0]||{n:1,iss:0,ret:0,retbase:0};
  var mx=Math.max.apply(null,rows.map(function(r){return r.n}).concat([1]));
  if(!SEL||!by[SEL]){SEL=rows.sort(function(a,b){return b.n-a.n})[0]?+rows[0].a:13}
  var h=pillsHtml('<span class="nt">Click a goal to open it. A project can claim several goals.</span>')+'<div id="tiles">';
  for(var g=1;g<=17;g++){var r=by[g]||{n:0,iss:0},c=SDG[g][1];
    h+='<button class="t'+(g===SEL?' on':'')+'" data-g="'+g+'" style="--c:'+c+';--ink:'+ink(c)+'"><div class="g">'+g+'</div><div class="nm">'+esc(SDG[g][0])+'</div><div class="bar"><i style="width:'+(100*r.n/mx).toFixed(1)+'%"></i></div><div class="c"><span>'+ni(r.n)+' projects</span><span>'+fm(r.iss)+'</span></div></button>'}
  h+='<div class="t sum"><div class="g">'+ni(tot.n)+'</div><div class="nm">projects report SDGs</div><div class="c" style="margin-top:12px"><span>'+fm(tot.iss)+' credits issued</span></div></div></div>';
  var r=by[SEL]||{n:0,iss:0,ret:0,retbase:0},c=SDG[SEL][1];
  var w=pick('sd','World',function(x){return x.b==='all'&&+x.a===SEL})[0]||{n:0},ind=pick('sd','India',function(x){return x.b==='all'&&+x.a===SEL})[0]||{n:0};
  function list(title,dim,lim){var L=pick('sd',SCOPE,function(x){return +x.a===SEL&&x.b===dim}).sort(function(a,b){return b.n-a.n}).slice(0,lim||5),m=L.length?L[0].n:1;
    return '<div class="ls"><h4>'+title+'</h4>'+(L.length?L.map(function(x){return '<div class="r"><span title="'+esc(x.c)+'">'+esc(x.c)+'</span><b>'+ni(x.n)+'</b><i><u style="width:'+(100*x.n/m).toFixed(0)+'%"></u></i></div>'}).join(''):'<div class="nt">no data</div>')+'</div>'}
  h+='<div class="dt" style="--c:'+c+'"><div class="dh" style="--c:'+c+';--ink:'+ink(c)+'"><span class="g">'+SEL+'</span><b>'+esc(SDG[SEL][0])+'</b><span>'+(SCOPE==='India'?'India only':'World')+'</span></div><div class="db">'
   +'<div class="st"><div><b>'+ni(r.n)+'</b><span>projects ('+pc(r.n,tot.n,0)+' of reporters)</span></div><div><b>'+fm(r.iss)+'</b><span>credits issued ('+pc(r.iss,tot.iss,0)+')</span></div>'
   +'<div><b>'+pc(r.ret,r.retbase,0)+'</b><span>retired ('+fm(r.ret)+')</span></div><div><b>'+(SCOPE==='World'?pc(ind.n,w.n,0):pc(r.n,w.n,0))+'</b><span>'+(SCOPE==='World'?'of these projects are Indian':'of the world’s projects for this goal')+'</span></div></div>'
   +list('TOP SECTORS','sector')+list('TOP REGISTRIES','registry')+(SCOPE==='India'?list('TOP STATES','state'):list('TOP COUNTRIES','country'))+'</div></div>';
  document.getElementById('app').innerHTML=h;
  bindScope(draw);
  Array.prototype.forEach.call(document.querySelectorAll('.t[data-g]'),function(b){b.onclick=function(){SEL=+b.getAttribute('data-g');draw()}});
}
draw();
"""

HEAT_CSS = """
.hm{width:100%;border-collapse:separate;border-spacing:3px}
.hm th{font-weight:600;font-size:11px;color:#444;text-align:center;vertical-align:bottom;padding:0 2px 4px;line-height:1.2}
.hm th small{display:block;font:500 10px 'Geist Mono',ui-monospace,Menlo,monospace;color:#888;margin-top:2px}
.hm td.l{text-align:left;white-space:nowrap;font-size:12px;padding:0 8px 0 0;width:210px}
.hm td.l i{display:inline-block;width:20px;height:20px;border-radius:5px;margin-right:8px;vertical-align:middle;text-align:center;font:800 11px/20px 'Geist Mono',ui-monospace,Menlo,monospace}
.hm td.c{text-align:center;height:26px;border-radius:5px;font:600 11.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.hm td.c.mx{box-shadow:inset 0 0 0 2px #173F0F}
.hm td.a{background:none;color:#444;border-left:1px solid #e3e6dc;border-radius:0}
.lgd{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:11px;color:#777}
.lgd i{display:inline-block;width:150px;height:9px;border-radius:5px;background:linear-gradient(90deg,rgba(38,94,48,.04),rgba(38,94,48,1))}
"""
HEAT_JS = r"""
function draw(){
  var cols=pick('sd',SCOPE,function(r){return r.a==='0'&&r.b==='sector'&&r.c!=='Not classified'}).sort(function(a,b){return b.n-a.n}).slice(0,7);
  var all=pick('sd',SCOPE,function(r){return r.a==='0'&&r.b==='all'})[0]||{n:1};
  var cell={};pick('sd',SCOPE,function(r){return r.b==='sector'&&r.a!=='0'}).forEach(function(r){cell[r.a+'|'+r.c]=r.n});
  var tot={};pick('sd',SCOPE,function(r){return r.b==='all'&&r.a!=='0'}).forEach(function(r){tot[r.a]=r.n});
  var mxc={};cols.forEach(function(c){var m=0,gm=0;for(var g=1;g<=17;g++){var v=(cell[g+'|'+c.c]||0);if(v>m){m=v;gm=g}}mxc[c.c]=gm});
  var h=pillsHtml('<span class="nt">Share of each sector’s SDG-reporting projects that claim the goal. Outlined cell = the sector’s most claimed goal.</span>')+'<table class="hm"><tr><th></th>'+cols.map(function(c){return '<th>'+esc(c.c)+'<small>'+ni(c.n)+' projects</small></th>'}).join('')+'<th>All sectors<small>'+ni(all.n)+' projects</small></th></tr>';
  for(var g=1;g<=17;g++){var col=SDG[g][1];
    h+='<tr><td class="l"><i style="background:'+col+';color:'+ink(col)+'">'+g+'</i>'+esc(SDG[g][0])+'</td>';
    cols.forEach(function(c){var n=cell[g+'|'+c.c]||0,s=c.n?n/c.n:0,a=Math.min(1,Math.pow(s/0.85,0.75));
      h+='<td class="c'+(mxc[c.c]===g?' mx':'')+'" style="background:rgba(38,94,48,'+(n?Math.max(.05,a).toFixed(2):0)+');color:'+(a>.5?'#fff':'#1b1b1b')+'" title="'+esc(SDG[g][0])+': '+ni(n)+' of '+ni(c.n)+' '+esc(c.c)+' projects">'+(n?Math.round(100*s)+'%':'–')+'</td>'});
    h+='<td class="c a">'+pc(tot[g]||0,all.n,0)+'</td></tr>'}
  h+='</table><div class="lgd">0% <i></i> 100% of the sector’s SDG-reporting projects</div>';
  document.getElementById('app').innerHTML=h;bindScope(draw);
}
draw();
"""

EFF_CSS = """
#app{display:grid;grid-template-columns:1fr 1fr 1.25fr;gap:14px;align-items:start}
.top{grid-column:1/-1}
.pn{border:1px solid #e3e6dc;border-radius:12px;padding:14px 16px;background:#FBFBF8}
.pn h3{margin:0 0 2px;font:700 11px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.09em;color:#333}
.pn .sb{font-size:11px;color:#888;margin:0 0 10px}
.rw{display:grid;grid-template-columns:1fr;gap:2px;margin-bottom:11px}
.rw .a{display:flex;justify-content:space-between;gap:8px;font-size:12px}.rw .a span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rw .a b{font:700 12.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.rw .m{font-size:10.5px;color:#888}
.bar{position:relative;height:10px;border-radius:5px;background:#eef0ea}.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:5px;background:linear-gradient(90deg,#173F0F,#4E8A2E)}
.bar.na i{display:none}
.bar u{position:absolute;top:-3px;bottom:-3px;width:2px;background:#B85829}
.base{font-size:10.5px;color:#B85829}
.pr{display:grid;grid-template-columns:1fr;gap:3px;margin-bottom:12px}.pr .a{display:flex;justify-content:space-between;font-size:12px}.pr .a b{font:700 11px 'Geist Mono',ui-monospace,Menlo,monospace;color:#555}
.pr .bar i.w{background:linear-gradient(90deg,#0E7C86,#35A9B3)}.pr .bar i.n{background:#B9BEB1}
.pr .m{font-size:10.5px;color:#888;display:flex;justify-content:space-between}
.ins{border-left:4px solid #C98A1F;background:#FFF9EC;border-radius:8px;padding:11px 14px;font-size:13px;line-height:1.5}
.ins b{color:#173F0F}
.lg{display:flex;gap:12px;font-size:10.5px;color:#666;margin-bottom:8px}.lg i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:-1px}
@media (max-width:900px){#app{grid-template-columns:1fr}}
"""
EFF_JS = r"""
var SHORT={'Verified Carbon Standard':'Verra','Gold Standard':'Gold Standard','Universal Carbon Registry (UCR)':'UCR','Cercarbono (EcoRegistry)':'Cercarbono','Climate Action Reserve':'Climate Action Reserve','Global Carbon Council':'GCC'};
function rate(r){return r.retbase>=1000?r.ret/r.retbase:null}
function barRow(label,r,base){var q=rate(r);
  return '<div class="rw"><div class="a"><span>'+esc(label)+'</span><b>'+(q==null?'n/a':Math.round(100*q)+'%')+'</b></div><div class="bar'+(q==null?' na':'')+'"><i style="width:'+(q==null?0:Math.min(100,100*q)).toFixed(1)+'%"></i>'+(base!=null?'<u style="left:'+Math.min(100,100*base).toFixed(1)+'%"></u>':'')+'</div><div class="m">'+ni(r.n)+' projects, '+fm(r.iss)+' issued'+(q==null?', retirements not reported':'')+'</div></div>'}
function draw(){
  var br=pick('br',SCOPE),lb=pick('lb',SCOPE),by={};br.forEach(function(r){by[r.a]=r});
  var order=['1-2 goals','3-4 goals','5-6 goals','7 or more goals'],base=by['No SDG data']?rate(by['No SDG data']):null;
  var p1='<div class="pn"><h3>BY NUMBER OF GOALS CLAIMED</h3><p class="sb">Share of issued credits that have been retired. Orange tick = projects with no SDG data.</p>'+order.map(function(k){return by[k]?barRow(k,by[k],base):''}).join('')+(by['No SDG data']?barRow('No SDG data',by['No SDG data'],null):'')+'</div>';
  var lorder=['SDG+ label (any tier)','S+ no-net-harm','CCB','Social Carbon','Gender responsive'],lby={};lb.forEach(function(r){lby[r.a]=r});
  var nb=lby['No social label']?rate(lby['No social label']):null;
  var p2='<div class="pn"><h3>BY SOCIAL-IMPACT LABEL</h3><p class="sb">Same measure. Orange tick = projects with no social label.</p>'+lorder.filter(function(k){return lby[k]&&lby[k].n>0}).map(function(k){return barRow(k,lby[k],nb)}).join('')+(lby['No social label']?barRow('No social label',lby['No social label'],null):'')+'</div>';
  var rg=pick('rg',SCOPE),R={};rg.forEach(function(r){(R[r.a]=R[r.a]||{})[r.b]=r});
  var names=Object.keys(R).filter(function(k){return R[k].sdg&&R[k].nosdg}).sort(function(a,b){return (R[b].sdg.n+R[b].nosdg.n)-(R[a].sdg.n+R[a].nosdg.n)});
  var wins=0,tot=0;
  var p3='<div class="pn"><h3>LIKE FOR LIKE: THE SAME REGISTRY</h3><p class="sb">Retirement rate of projects with and without SDG data, inside one registry.</p><div class="lg"><span><i style="background:#0E7C86"></i>reports SDGs</span><span><i style="background:#B9BEB1"></i>no SDG data</span></div>'+names.map(function(k){var a=R[k].sdg,b=R[k].nosdg,qa=rate(a),qb=rate(b);if(qa!=null&&qb!=null){tot++;if(qa>qb)wins++}
    return '<div class="pr"><div class="a"><span>'+esc(SHORT[k]||k)+'</span><b>'+(qa==null?'n/a':Math.round(100*qa)+'%')+' vs '+(qb==null?'n/a':Math.round(100*qb)+'%')+'</b></div><div class="bar"><i class="w" style="width:'+(qa==null?0:100*qa).toFixed(1)+'%"></i></div><div class="bar"><i class="n" style="width:'+(qb==null?0:100*qb).toFixed(1)+'%"></i></div><div class="m"><span>'+ni(a.n)+' with SDG data</span><span>'+ni(b.n)+' without</span></div></div>'}).join('')+'</div>';
  var hi=by['7 or more goals'],q7=hi?rate(hi):null;
  var ins='<div class="top ins"><b>Reading this.</b> '+(q7!=null&&base!=null?'Across all registries, projects claiming 7 or more goals retire <b>'+Math.round(100*q7)+'%</b> of what they issue, against <b>'+Math.round(100*base)+'%</b> for projects with no SDG data. ':'')
   +(tot?'But inside the same registry, SDG-reporting projects retire more in only <b>'+wins+' of '+tot+'</b> comparisons, so the gap is mostly about <b>which registry</b> a project sits in. ':'')
   +'This is correlation, not proof that goals sell or do not sell. Retirement data is only partly reported (GCC reports almost none, UCR retires very little), and small groups move a lot.</div>';
  document.getElementById('app').innerHTML='<div class="top">'+pillsHtml('<span class="nt">Retirement rate = credits retired / credits issued, where the registry reports retirements.</span>')+'</div>'+ins+p1+p2+p3;
  bindScope(draw);
}
draw();
"""

ST_CSS = """
.hd{display:grid;grid-template-columns:30px 190px 78px 78px 1fr 230px;gap:12px;padding:0 10px 6px;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:#7a8270;font-weight:600;position:sticky;top:0;background:#fff;z-index:2;border-bottom:1px solid #eef0e9}
.sc{max-height:264px;overflow-y:auto;border-bottom:1px solid #eef0e9}
.r{display:grid;grid-template-columns:30px 190px 78px 78px 1fr 230px;gap:12px;align-items:center;padding:8px 10px;border-radius:10px}
.r:nth-child(even){background:#f8faf5}
.k1{width:24px;height:24px;border-radius:50%;background:#eef2e8;color:#2F6B1E;font:700 11px/24px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:center}
.nm{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v{font:600 12.5px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.ch{display:flex;gap:5px;flex-wrap:wrap}
.cp{display:inline-flex;align-items:center;gap:5px;border-radius:7px;padding:2px 7px 2px 3px;font-size:11px;background:#fff;border:1px solid #e3e6dc}
.cp i{display:inline-block;min-width:19px;height:19px;border-radius:5px;text-align:center;font:800 10.5px/19px 'Geist Mono',ui-monospace,Menlo,monospace}
.sg{font-size:11.5px;line-height:1.35;color:#444}.sg b{color:#173F0F}
.hn{font-size:11px;color:#888;margin:6px 0 0}
.pills{margin-bottom:8px}
@media (max-width:900px){.hd{display:none}.r{grid-template-columns:30px 1fr 70px}.ch,.sg{grid-column:2/-1}}
"""
ST_JS = r"""
var SORT='n';
function draw(){
  var tot={},ng={},st={},T=pick('sd','India',function(r){return r.a==='0'&&r.b==='state'}),G=pick('sd','India',function(r){return r.a!=='0'&&r.b==='state'}),I=pick('sd','India',function(r){return r.b==='all'}),iall={},itot=0;
  I.forEach(function(r){if(r.a==='0')itot=r.n;else iall[r.a]=r.n});
  T.forEach(function(r){tot[r.c]=r});G.forEach(function(r){(ng[r.c]=ng[r.c]||{})[r.a]=r.n});
  var list=Object.keys(tot).map(function(k){return {s:k,t:tot[k],g:ng[k]||{}}}).sort(function(a,b){return SORT==='n'?b.t.n-a.t.n:b.t.iss-a.t.iss});
  var h='<div class="pills"><button class="pill'+(SORT==='n'?' on':'')+'" data-o="n">Rank by projects</button><button class="pill'+(SORT==='i'?' on':'')+'" data-o="i">Rank by credits issued</button><span class="nt">Only projects that report SDG goals. Signature goal = most over-represented against India as a whole (states with 10 or more projects).</span></div>';
  h+='<div class="sc"><div class="hd"><span>#</span><span>State</span><span style="text-align:right">Projects</span><span style="text-align:right">Credits</span><span>Most claimed goals (share of the state’s projects)</span><span>Signature goal</span></div>';
  list.forEach(function(x,i){
    var gs=Object.keys(x.g).map(function(g){return[+g,x.g[g]]}).sort(function(a,b){return b[1]-a[1]}).slice(0,5);
    var sig=null;if(x.t.n>=10){Object.keys(x.g).forEach(function(g){var sh=x.g[g]/x.t.n,ia=(iall[g]||0)/itot;if(ia>0&&x.g[g]>=5){var q=sh/ia;if(!sig||q>sig.q)sig={g:+g,q:q}}})}
    h+='<div class="r"><span class="k1">'+(i+1)+'</span><span class="nm" title="'+esc(x.s)+'">'+esc(x.s)+'</span><span class="v">'+ni(x.t.n)+'</span><span class="v">'+fm(x.t.iss)+'</span><span class="ch">'
      +gs.map(function(a){var c=SDG[a[0]][1];return '<span class="cp" title="'+esc(SDG[a[0]][0])+'"><i style="background:'+c+';color:'+ink(c)+'">'+a[0]+'</i>'+Math.round(100*a[1]/x.t.n)+'%</span>'}).join('')+'</span>'
      +'<span class="sg">'+(sig&&sig.q>=1.25?'<b>SDG '+sig.g+'</b> '+esc(SDG[sig.g][0])+'<br>'+sig.q.toFixed(1)+'\u00d7 the India average':(sig?'<span class="nt">close to the India average</span>':'<span class="nt">too few projects</span>'))+'</span></div>'});
  h+='</div><div class="hn">Showing the top 5. Scroll inside the list to see the rest.</div>';
  document.getElementById('app').innerHTML=h;
  Array.prototype.forEach.call(document.querySelectorAll('.pill[data-o]'),function(b){b.onclick=function(){SORT=b.getAttribute('data-o');draw()}});
}
draw();
"""


# ---------------------------------------------------------------- wrapping, slices and tab
COLS = ['kind', 'a', 'b', 'c', 'scope', 'n', 'iss', 'ret', 'retbase']

CHARTS = [
    # key, chart name, css, js, frame height (px), grid height units
    ('kpi', 'SDG and social impact in numbers', KPI_CSS, KPI_JS, 132, 17),
    ('const', 'The 17 Sustainable Development Goals: where carbon projects claim them', CONST_CSS, CONST_JS, 640, 82),
    ('heat', 'Which goals does each sector claim? (goal by sector heat map)', HEAT_CSS, HEAT_JS, 660, 84),
    ('eff', 'Does doing good sell? Retirement rates by SDG breadth and social label', EFF_CSS, EFF_JS, 700, 88),
    ('state', "India's states: social-impact leaderboard and signature goals", ST_CSS, ST_JS, 360, 45),
]


def frame(title, css, js, height):
    doc = ('<!doctype html><html><head><meta charset="utf-8"><style>' + COMMON_CSS + css + '</style></head><body><div id="app"></div><script>'
           'var D=({{stringify this}}).data;' + COMMON_JS + js + '</script></body></html>')
    attr = H.escape(doc, quote=True).replace('\n', '&#10;')
    return (f'<div class="cgxsdg"><div><iframe title="{H.escape(title, quote=True)}" sandbox="allow-scripts" srcdoc="{attr}" '
            f'style="width:100%;height:{height}px;border:0;display:block"></iframe></div></div>')


def md(code_id, title, body, height):
    code = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:12px 6px 4px\"><div style=\"font-size:15px;font-weight:700;color:#2C7A3D;margin-bottom:10px;\">"
            + title + "</div><p style=\"margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify\">" + body + "</p></div>")
    return code, height


INTRO = [
    ('intro', 'SDG, Social & Economics: what carbon projects deliver beyond the tonne',
     'A carbon credit is a tonne of emissions avoided or removed, but many projects also claim wider benefits: clean energy, health, jobs, gender equality, water and land. '
     'This tab shows which of the 17 UN Sustainable Development Goals projects claim, where, and in which sectors, and then asks an economic question: do credits from projects with social claims or labels actually get used (retired) more?', 22),
    ('const', 'The goals at a glance',
     'Each tile is one goal; its size of bar shows how many projects claim it. Click a goal to see its sectors, registries and countries or states. Switch to India only to see the Indian picture.', 11),
    ('heat', 'Which sectors claim which goals?',
     'Renewable energy leans on SDG 7 and 13, household and community projects (cookstoves, water) on health, gender and poverty, and forestry on land and climate. The heat map shows each sector’s signature.', 11),
    ('eff', 'Does doing good sell?',
     'Retirement means a credit has been used, so retirement rates are a simple market signal. The comparison below is deliberately like for like: the registry a project sits in matters more than its SDG claims.', 11),
    ('state', "India: where the social claims are",
     'Which Indian states host the most projects that report SDG goals, and which goals each state stands out for.', 9),
]
NOTE = ('Coverage note: SDG goals are reported by some registries only (mainly Gold Standard, GCC, UCR and ICR), so about one project in six carries SDG data. '
        'Goal claims are what developers declare, not independently measured outcomes. Retirement rates use only credits where the registry reports retirements.')


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
        build_table(con)
        con.close()
        dbo = db.session.query(Database).filter(Database.database_name == 'C-GEM mastersheet').first()
        tbl = db.session.query(SqlaTable).filter(SqlaTable.table_name == TABLE).first()
        if tbl is None:
            tbl = SqlaTable(table_name=TABLE, schema='main', database=dbo)
            db.session.add(tbl)
            db.session.commit()
        tbl.fetch_metadata()
        db.session.commit()
        ref = db.session.query(Slice).filter(Slice.slice_name == 'Registry intelligence: the leading registries side by side').first()
        slices = {}
        for key, name, css, js, ph, units in CHARTS:
            sl = db.session.query(Slice).filter(Slice.slice_name == name).first()
            if sl is None:
                sl = Slice(slice_name=name, viz_type='handlebars', datasource_type='table', datasource_id=tbl.id)
                db.session.add(sl)
            p = json.loads(ref.params) if ref is not None else {'viz_type': 'handlebars'}
            for k in ('slice_id', 'handlebarsTemplate', 'timeseries_limit_metric', 'orderby', 'order_desc', 'extra_form_data'):
                p.pop(k, None)
            p.update({'viz_type': 'handlebars', 'datasource': f'{tbl.id}__table', 'query_mode': 'raw', 'all_columns': COLS, 'groupby': [], 'metrics': [],
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
            if TAB_ID in pos:
                continue
            base = ['ROOT_ID', 'GRID_ID', 'TABS-main', TAB_ID]
            rows = []

            def add_md(rid, code, height):
                mid = f'MARKDOWN-sdg-{rid}'
                pos[mid] = {'children': [], 'id': mid, 'meta': {'code': code, 'height': height, 'width': 12}, 'parents': base + [f'ROW-sdg-{rid}-m'], 'type': 'MARKDOWN'}
                pos[f'ROW-sdg-{rid}-m'] = {'children': [mid], 'id': f'ROW-sdg-{rid}-m', 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
                rows.append(f'ROW-sdg-{rid}-m')

            def add_chart(key, units):
                sl = slices[key]
                cid = f'CHART-sdg-{key}'
                comp = copy.deepcopy(pos['CHART-cp_regcards']) if 'CHART-cp_regcards' in pos else {'children': [], 'meta': {}, 'type': 'CHART'}
                comp['id'] = cid
                comp['parents'] = base + [f'ROW-sdg-{key}-c']
                comp['meta'] = {'chartId': sl.id, 'sliceName': sl.slice_name, 'height': units, 'width': 12, 'uuid': str(sl.uuid)}
                pos[cid] = comp
                pos[f'ROW-sdg-{key}-c'] = {'children': [cid], 'id': f'ROW-sdg-{key}-c', 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
                rows.append(f'ROW-sdg-{key}-c')

            units = {k: u for k, _n, _c, _j, _h, u in CHARTS}
            for key, title, body, h in INTRO:
                code, height = md(key, title, body, h)
                add_md(key, code, height)
                if key == 'intro':
                    add_chart('kpi', units['kpi'])
                elif key in units:
                    add_chart(key, units[key])
            note_code = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:8px 6px;font-size:12.5px;color:#777\">" + NOTE + '</div>')
            add_md('note', note_code, 9)
            pos[TAB_ID] = {'children': rows, 'id': TAB_ID, 'meta': {'defaultText': TAB_NAME, 'text': TAB_NAME}, 'parents': ['ROOT_ID', 'GRID_ID', 'TABS-main'], 'type': 'TAB'}
            kids = pos['TABS-main']['children']
            anchor = 'TAB-3' if 'TAB-3' in kids else kids[-1]
            kids.insert(kids.index(anchor) + 1, TAB_ID)
            d.position_json = json.dumps(pos)
            print('v99p: SDG, Social & Economics tab added')
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tab
        import traceback
        traceback.print_exc()
        print('v99p: skipped:', exc)
