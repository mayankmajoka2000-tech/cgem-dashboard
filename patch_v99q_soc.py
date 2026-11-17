"""C-GEM v99q online site: three more charts for the "SDG, Social & Economics" tab (built by patch_v99p_sdg).

  1. SDG claims by project stage: for each of the 17 goals (and for all projects) how many projects are issued, registered without credits,
     listed or in the pipeline, stopped, or not recorded. World or India.
  2. Who gets the projects: big economies against Africa and the UN least developed countries (projects and credits issued), with country lists.
  3. India's concentration: Lorenz curves and Gini for states and districts, industrialised states against the left-behind regions, top districts and thinnest states.
Rows are appended to sdg_tab (same columns as before), so the charts read the same dataset as the other SDG charts."""
import copy
import json

from patch_v99p_sdg import COLS, TABLE, TAB_ID, frame, md, COMMON_CSS, COMMON_JS  # noqa: F401

# ---------------------------------------------------------------- stage and group rules
STOP = ('withdraw', 'reject', 'revoked', 'inactive', 'terminat', 'cancel', 'declin', 'denied', 'retract', 'deregist', 'de-regist', 'suspend',
        'on hold', 'decertif', 'not to register', 'unsuccessful', 'not found', 'transferred', '已终止', 'not delivered', 'not published')
REG = ('registered', 'certified', 'credited', 'completed', 'late to verify', 'verified', 'active', 'transition', 'issued', 'end of',
       'published', 'endorsed', '已登记', 'renewal', 'component project', 'project registered')
PEND = ('listed', 'listing', 'pipeline', 'validation', 'validated', 'development', 'request', 'public comment', 'submitted', 'proposed', 'planned',
        'prior consideration', 'assessment', 'received', 'endorse', 'idea', 'open for public', '公示', '申请登记', 'ongoing', 'under public')


def stage(reg_status, vol_status, issued):
    if issued and issued > 0:
        return 1
    t = ''
    for s in (reg_status, vol_status):
        if s and s.strip() and s.strip().lower() not in ('not recorded', 'registry details not read for this registry'):
            t = s.lower().replace('not revoked', '')
            break
    if not t or t.startswith('project id not found'):
        return 5
    if 'registration' in t and 'request' in t:
        return 3
    if t.strip() == 'closed':
        return 4
    if 'approved for verification' in t or t.startswith('verification') or t.startswith('retired'):
        return 2
    if 'provisional' in t or t.startswith('registration'):
        return 3
    if any(w in t for w in STOP):
        return 4
    if 'verification approval requested' in t or any(w in t for w in REG):
        if 'registered' in t or 'certified' in t or 'verification' in t or 'active' in t or 'completed' in t or 'late to verify' in t \
                or 'credited' in t or 'issued' in t or 'transition' in t or 'verified' in t or 'end of' in t or 'renewal' in t or 'published' in t \
                or 'endorsed' in t or '已登记' in t or 'component project' in t:
            return 2
    if any(w in t for w in PEND):
        return 3
    return 5


LDC = ['Afghanistan', 'Angola', 'Bangladesh', 'Benin', 'Burkina Faso', 'Burundi', 'Cambodia', 'Central African Republic', 'Chad', 'Comoros',
       'Congo, The Democratic Republic of the', 'Djibouti', 'Eritrea', 'Ethiopia', 'Gambia', 'Guinea', 'Guinea-Bissau', 'Haiti', 'Kiribati',
       "Lao People's Democratic Republic", 'Lesotho', 'Liberia', 'Madagascar', 'Malawi', 'Mali', 'Mauritania', 'Mozambique', 'Myanmar', 'Nepal', 'Niger',
       'Rwanda', 'Sao Tome and Principe', 'Senegal', 'Sierra Leone', 'Somalia', 'South Sudan', 'Sudan', 'Tanzania', 'Timor-Leste',
       'Togo', 'Tuvalu', 'Uganda', 'Yemen', 'Zambia']
ALIAS = {'Lao PDR': "Lao People's Democratic Republic", 'Laos': "Lao People's Democratic Republic", 'Democratic Republic of the Congo': 'Congo, The Democratic Republic of the',
         'DR Congo': 'Congo, The Democratic Republic of the', 'Congo, Democratic Republic of the': 'Congo, The Democratic Republic of the',
         'Burma': 'Myanmar', 'East Timor': 'Timor-Leste', 'Timor Leste': 'Timor-Leste', 'The Gambia': 'Gambia', 'United Republic of Tanzania': 'Tanzania',
         'Gambia, The': 'Gambia', 'Sao Tome & Principe': 'Sao Tome and Principe', 'São Tomé and Príncipe': 'Sao Tome and Principe'}
AFRICA = ['Algeria', 'Angola', 'Benin', 'Botswana', 'Burkina Faso', 'Burundi', 'Cameroon', 'Cape Verde', 'Central African Republic', 'Chad', 'Comoros', 'Congo',
          'Congo, The Democratic Republic of the', "Côte d'Ivoire", 'Djibouti', 'Egypt', 'Equatorial Guinea', 'Eritrea', 'Eswatini', 'Ethiopia', 'Gabon', 'Gambia', 'Ghana',
          'Guinea', 'Guinea-Bissau', 'Kenya', 'Lesotho', 'Liberia', 'Libya', 'Madagascar', 'Malawi', 'Mali', 'Mauritania', 'Mauritius', 'Morocco', 'Mozambique', 'Namibia',
          'Niger', 'Nigeria', 'Rwanda', 'Sao Tome and Principe', 'Senegal', 'Seychelles', 'Sierra Leone', 'Somalia', 'South Africa', 'South Sudan', 'Sudan', 'Tanzania',
          'Togo', 'Tunisia', 'Uganda', 'Zambia', 'Zimbabwe']
INDUSTRIAL = ['Gujarat', 'Maharashtra', 'Karnataka', 'Andhra Pradesh', 'Tamil Nadu']
NE = ['Arunachal Pradesh', 'Assam', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Sikkim', 'Tripura']
BEHIND = NE + ['Bihar', 'Jharkhand', 'Jammu and Kashmir', 'Ladakh']
G_IND, G_BEH, G_OTH = 'Five industrialised states', 'Left-behind regions', 'Other states'


def build_rows(con):
    # remove an earlier run of this patch
    con.execute(f"DELETE FROM {TABLE} WHERE kind IN ('ss','gp','cl','is','id')")
    ins = lambda rows: con.executemany(f'INSERT INTO {TABLE} VALUES (?,?,?,?,?,?,?,?,?)', rows)
    P = con.execute("SELECT project_key, registry_status, voluntary_status, COALESCE(credits_issued,0), COALESCE(credits_retired,0), "
                    "is_india, country, continent, adm1_name FROM projects WHERE registry <> 'Unknown registry'").fetchall()
    goals = {}
    for k, g in con.execute('SELECT DISTINCT project_key, sdg_number FROM sdgs'):
        goals.setdefault(k, set()).add(int(g))
    # 1. stage x goal
    acc = {}
    for k, rs, vs, iss, ret, ind, ctry, cont, st in P:
        s = stage(rs, vs, iss)
        gs = goals.get(k, set())
        keys = ['T'] + (['0'] + [str(g) for g in gs] if gs else [])
        for scope in (('World', 'India') if ind == 'India' else ('World',)):
            for a in keys:
                x = acc.setdefault((a, str(s), scope), [0, 0.0])
                x[0] += 1
                x[1] += iss
    ins([('ss', a, b, '', sc, v[0], v[1], 0, 0) for (a, b, sc), v in acc.items()])
    # 2. country groups and country lists
    cn = {}
    for k, rs, vs, iss, ret, ind, ctry, cont, st in P:
        if not ctry or ctry in ('Not recorded', ''):
            continue
        c = ALIAS.get(ctry, ctry)
        x = cn.setdefault(c, [cont or 'Other', 0, 0.0, 0.0])
        x[1] += 1
        x[2] += iss
        x[3] += ret
    grp = {}

    def add(g, c, x):
        y = grp.setdefault(g, [0, 0.0, 0.0, 0])
        y[0] += x[1]
        y[1] += x[2]
        y[2] += x[3]
        y[3] += 1
    for c, x in cn.items():
        g = 'China' if c == 'China' else 'India' if c == 'India' else ('Rest of Asia' if x[0] == 'Asia' else x[0] if x[0] in ('Africa', 'Europe', 'North America', 'South America', 'Oceania') else 'Other')
        add(g, c, x)
        if c in LDC:
            add('LDC', c, x)
    ins([('gp', g, '', '', 'World', y[0], y[1], y[2], y[3]) for g, y in grp.items()])
    rows = []
    seen = set()
    for c in AFRICA + LDC:
        if c in seen:
            continue
        seen.add(c)
        x = cn.get(c, ['Africa' if c in AFRICA else 'Asia', 0, 0.0, 0.0])
        rows.append(('cl', c, x[0] if c in cn else ('Africa' if c in AFRICA else 'Asia'), ('LDC' if c in LDC else '') + ('|AF' if c in AFRICA else ''), 'World', x[1], x[2], x[3], 0))
    ins(rows)
    miss = [c for c in LDC if c not in cn]
    print('v99q: LDC without projects:', len(miss), 'African without projects:', len([c for c in AFRICA if c not in cn]))
    # 3. India states and districts
    stc = {}
    for k, rs, vs, iss, ret, ind, ctry, cont, st in P:
        if ind == 'India' and st:
            x = stc.setdefault(st, [0, 0.0])
            x[0] += 1
            x[1] += iss
    allst = [r[0] for r in con.execute('SELECT map_state FROM geo_india_state')]
    rows = []
    for s in sorted(set(allst) | set(stc)):
        g = G_IND if s in INDUSTRIAL else G_BEH if s in BEHIND else G_OTH
        x = stc.get(s, [0, 0.0])
        rows.append(('is', s, g, '', 'India', x[0], x[1], 0, 0))
    ins(rows)
    dc = {}
    for st, d, iss in con.execute("SELECT map_state, map_district, COALESCE(credits_issued,0) FROM map_india_district"):
        x = dc.setdefault((st, d), [0, 0.0])
        x[0] += 1
        x[1] += iss
    rows = []
    for st, d in con.execute('SELECT map_state, map_district FROM geo_india_district'):
        x = dc.get((st, d), [0, 0.0])
        rows.append(('id', d, st, '', 'India', x[0], x[1], 0, 0))
    ins(rows)
    con.commit()
    print('v99q: rows added; district rows', len(rows), 'with projects', sum(1 for r in rows if r[5] > 0))


# ---------------------------------------------------------------- chart 1: SDG x project stage
STAGE_CSS = """
.hd{display:grid;grid-template-columns:230px 64px 1fr repeat(5,86px);gap:10px;padding:0 8px 8px;align-items:end;font-size:10.5px;color:#666;line-height:1.2;border-bottom:1px solid #eef0e9}
.hd i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:-1px}
.rw{display:grid;grid-template-columns:230px 64px 1fr repeat(5,86px);gap:10px;align-items:center;padding:6px 8px;border-radius:8px}
.rw:nth-child(even){background:#f8faf5}
.rw.top{background:#eef4e9;font-weight:700}
.nm{display:flex;align-items:center;gap:8px;font-size:12.5px;white-space:nowrap;overflow:hidden}
.nm i{display:inline-block;min-width:22px;height:22px;border-radius:6px;text-align:center;font:800 11px/22px 'Geist Mono',ui-monospace,Menlo,monospace}
.tt{font:700 12.5px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.sb{display:flex;height:14px;border-radius:7px;overflow:hidden;background:#eef0ea}
.sb b{display:block;height:100%}
.c{text-align:right;font:600 12px 'Geist Mono',ui-monospace,Menlo,monospace;line-height:1.15}.c small{display:block;font:500 10px Geist,Arial,sans-serif;color:#8a9080}
.ft{margin:10px 2px 0;font-size:11px;color:#777;line-height:1.5}
@media (max-width:1000px){.hd,.rw{grid-template-columns:200px 60px 1fr}.hd span:nth-child(n+4),.rw .c{display:none}}
"""
STAGE_JS = r"""
var STG=[null,['Credits issued','#265E30'],['Registered, no credits yet','#6B9E4A'],['Listed, pipeline or validation','#C98A1F'],['Stopped (rejected, withdrawn)','#B85829'],['Status not recorded','#B9BDB0']];
function draw(){
  var by={};
  pick('ss',SCOPE).forEach(function(r){var o=by[r.a]=by[r.a]||{t:0,s:{}};o.s[r.b]=r;o.t+=r.n});
  var order=['T','0'];for(var g=1;g<=17;g++)order.push(''+g);
  var h='<div class="top">'+pillsHtml('<span class="nt">One project can claim several goals, so goal rows overlap.</span>')+'</div>';
  h+='<div class="hd"><span>Goal</span><span style="text-align:right">Projects</span><span>Share by stage</span>'+[1,2,3,4,5].map(function(s){return '<span style="text-align:right"><i style="background:'+STG[s][1]+'"></i>'+STG[s][0]+'</span>'}).join('')+'</div>';
  order.forEach(function(a){
    var o=by[a];if(!o)return;
    var lab=a==='T'?'All projects in the dataset':a==='0'?'Projects that report any SDG goal':null;
    var nm=lab?'<span>'+lab+'</span>':'<i style="background:'+SDG[+a][1]+';color:'+ink(SDG[+a][1])+'">'+a+'</i><span>'+esc(SDG[+a][0])+'</span>';
    var seg=[1,2,3,4,5].map(function(s){var r=o.s[s];var n=r?r.n:0;return '<b style="width:'+(100*n/o.t).toFixed(2)+'%;background:'+STG[s][1]+'" title="'+esc(STG[s][0])+': '+ni(n)+'"></b>'}).join('');
    var cells=[1,2,3,4,5].map(function(s){var r=o.s[s];var n=r?r.n:0;return '<span class="c">'+ni(n)+'<small>'+pc(n,o.t,0)+'</small></span>'}).join('');
    h+='<div class="rw'+(lab?' top':'')+'"><span class="nm">'+nm+'</span><span class="tt">'+ni(o.t)+'</span><div class="sb">'+seg+'</div>'+cells+'</div>';
  });
  h+='<div class="ft">Stage is read from each registry’s own status text. <b>Credits issued</b>: the registry reports credits issued. <b>Registered, no credits yet</b>: registered, certified, active or completed with no issuance. '
   +'<b>Listed, pipeline or validation</b>: listed, under development, under validation, or registration requested. <b>Stopped</b>: rejected, withdrawn, revoked, inactive, cancelled. Only some registries publish SDG goals, so goal rows cover fewer projects than the first row.</div>';
  document.getElementById('app').innerHTML=h;bindScope(draw);
}
draw();
"""

# ---------------------------------------------------------------- chart 2: who gets the projects
WHO_CSS = """
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pn{border:1px solid #e3e6dc;border-radius:12px;padding:12px 14px;background:#fbfcf9}
.pn h3{margin:0 0 3px;font:700 11px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;color:#333}
.pn .sb2{margin:0 0 10px;font-size:11px;color:#777}
.ins{border-left:4px solid #C98A1F;background:#FFF9EC;border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5;margin-bottom:12px}
.bw{display:grid;grid-template-columns:150px 1fr 96px;gap:10px;align-items:center;padding:4px 0;font-size:12px}
.bw .bar{height:12px;border-radius:6px;background:#eef0ea;position:relative}.bw .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:6px}
.bw b{font:700 12px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.sc{max-height:236px;overflow-y:auto;border-bottom:1px solid #eef0e9}
.cr{display:grid;grid-template-columns:26px 1fr 68px 68px;gap:8px;align-items:center;padding:6px 6px;font-size:12.5px}
.cr:nth-child(even){background:#f4f7f0}
.cr .v{font:600 12px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.cr .k{color:#8a9080;font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.cr.z .v{color:#B85829}
.ch{position:sticky;top:0;background:#fff;color:#7a8270;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.hn{font-size:11px;color:#888;margin:6px 0 0}
@media (max-width:900px){.g2{grid-template-columns:1fr}}
"""
WHO_JS = r"""
var MET='n',LIST='af';
var GC={'China':'#B85829','India':'#265E30','Rest of Asia':'#C98A1F','Europe':'#4F7CA3','North America':'#6B9E4A','South America':'#8FB56A','Oceania':'#7A5BA6','Africa':'#D2452E','Other':'#B9BDB0'};
function draw(){
  var G={};pick('gp','World').forEach(function(r){G[r.a]=r});
  var key=MET==='n'?'n':'iss';
  var all=0;['China','India','Rest of Asia','Europe','North America','South America','Oceania','Africa','Other'].forEach(function(g){if(G[g])all+=G[g][key]});
  var C=pick('cl','World');
  var af=C.filter(function(r){return r.c.indexOf('AF')>-1}).sort(function(a,b){return b.n-a.n||b.iss-a.iss});
  var ld=C.filter(function(r){return r.c.indexOf('LDC')===0}).sort(function(a,b){return b.n-a.n||b.iss-a.iss});
  var ldz=ld.filter(function(r){return r.n===0}).length;
  var chn=G['China']||{n:0,iss:0},L=G['LDC']||{n:0,iss:0,retbase:0},A=G['Africa']||{n:0,iss:0};
  var a3=af.slice(0,3).reduce(function(s,r){return s+r.n},0);
  var pcn=ld.length?L.n/ld.length:0;
  var ins='<div class="ins"><b>Reading this.</b> China alone hosts <b>'+ni(chn.n)+'</b> projects ('+pc(chn.n,all,0)+' of all). The <b>'+ld.length+' least developed countries</b> together host <b>'+ni(L.n)+'</b> ('+pc(L.n,all,1)+'), about <b>'+ni(pcn)+'</b> per country against '+ni(chn.n)+' for China, and <b>'+ldz+'</b> of them have none at all. '
   +'Africa has <b>'+ni(A.n)+'</b> projects ('+pc(A.n,all,0)+') across '+af.length+' countries, and its top three countries hold '+pc(a3,A.n,0)+' of them. Counts are not adjusted for population, size or emissions.</div>';
  var order=['China','India','Rest of Asia','Europe','North America','South America','Oceania','Africa'].filter(function(g){return G[g]}).sort(function(a,b){return G[b][key]-G[a][key]});
  var mx=Math.max.apply(null,order.map(function(g){return G[g][key]}));
  var left='<div class="pn"><h3>WHERE THE PROJECTS ARE</h3><p class="sb2">Share of all '+(MET==='n'?'projects':'credits issued')+' by host group.</p>'
   +order.map(function(g){var v=G[g][key];return '<div class="bw"><span>'+g+' <span class="nt">('+G[g].retbase+')</span></span><div class="bar"><i style="width:'+(100*v/mx).toFixed(1)+'%;background:'+(GC[g]||'#999')+'"></i></div><b>'+pc(v,all,1)+'</b></div>'}).join('')
   +'<div class="bw" style="border-top:1px dashed #d9dcd2;margin-top:6px;padding-top:8px"><span>Least developed countries <span class="nt">('+ld.length+')</span></span><div class="bar"><i style="width:'+(100*L[key]/mx).toFixed(1)+'%;background:#D2452E;opacity:.55"></i></div><b>'+pc(L[key],all,1)+'</b></div>'
   +'<p class="hn">Numbers in brackets are host countries with at least one project. Least developed countries (UN list of 44) overlap with Africa and Asia, so they are shown separately.</p></div>';
  var rows=(LIST==='af'?af:ld);
  var right='<div class="pn"><h3>'+(LIST==='af'?'AFRICA: COUNTRY BY COUNTRY':'LEAST DEVELOPED COUNTRIES')+'</h3><p class="sb2">Ranked by projects. Countries with none are listed at the bottom.</p>'
   +'<div class="sc"><div class="cr ch"><span></span><span>Country</span><span style="text-align:right">Projects</span><span style="text-align:right">Credits</span></div>'
   +rows.map(function(r,i){return '<div class="cr'+(r.n===0?' z':'')+'"><span class="k">'+(i+1)+'</span><span>'+esc(r.a)+'</span><span class="v">'+ni(r.n)+'</span><span class="v">'+(r.n?fm(r.iss):'none')+'</span></div>'}).join('')+'</div>'
   +'<p class="hn">Showing the top 5. Scroll inside the list to see the rest.</p></div>';
  var pills='<div class="pills"><button class="pill'+(MET==='n'?' on':'')+'" data-m="n">Projects</button><button class="pill'+(MET==='i'?' on':'')+'" data-m="i">Credits issued</button><span style="width:14px"></span>'
   +'<button class="pill'+(LIST==='af'?' on':'')+'" data-l="af">List: Africa</button><button class="pill'+(LIST==='ld'?' on':'')+'" data-l="ld">List: least developed countries</button></div>';
  document.getElementById('app').innerHTML=pills+ins+'<div class="g2">'+left+right+'</div>';
  Array.prototype.forEach.call(document.querySelectorAll('[data-m]'),function(b){b.onclick=function(){MET=b.getAttribute('data-m');draw()}});
  Array.prototype.forEach.call(document.querySelectorAll('[data-l]'),function(b){b.onclick=function(){LIST=b.getAttribute('data-l');draw()}});
}
draw();
"""

# ---------------------------------------------------------------- chart 3: India concentration
IND_CSS = """
.g2{display:grid;grid-template-columns:minmax(380px,1.05fr) 1fr;gap:16px}
.pn{border:1px solid #e3e6dc;border-radius:12px;padding:12px 14px;background:#fbfcf9}
.pn h3{margin:0 0 3px;font:700 11px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;color:#333}
.pn .sb2{margin:0 0 8px;font-size:11px;color:#777}
.ins{border-left:4px solid #C98A1F;background:#FFF9EC;border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5;margin-bottom:12px}
svg{display:block;width:100%;height:auto;max-width:470px;margin:0 auto}
svg text{font-family:Geist,Inter,Arial,sans-serif;font-size:11px;fill:#555}
.lg{display:flex;gap:14px;font-size:11px;color:#555;margin:4px 0 0;flex-wrap:wrap}.lg i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:5px;vertical-align:middle}
.cm{margin:0 0 10px}.cm .t{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px}.cm .t b{font:700 12.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.cm .bar{height:16px;border-radius:8px;background:#eef0ea;overflow:hidden}.cm .bar i{display:block;height:100%;border-radius:8px}
.cm .d{font-size:11px;color:#777;margin-top:3px;line-height:1.4}
.g3{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.sc{max-height:212px;overflow-y:auto;border-bottom:1px solid #eef0e9}
.cr{display:grid;grid-template-columns:26px 1fr 64px 64px;gap:8px;align-items:center;padding:5px 6px;font-size:12.5px}
.cr:nth-child(even){background:#f4f7f0}
.cr .v{font:600 12px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.cr small{display:block;color:#8a9080;font-size:10.5px}
.cr .k{color:#8a9080;font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.cr.z .v{color:#B85829}
.ch{position:sticky;top:0;background:#fff;color:#7a8270;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.hn{font-size:11px;color:#888;margin:6px 0 0}
@media (max-width:900px){.g2,.g3{grid-template-columns:1fr}}
"""
IND_JS = r"""
var MET='n';
function lor(vals){
  var a=vals.slice().sort(function(x,y){return x-y}),n=a.length,tot=a.reduce(function(s,x){return s+x},0),cum=0,pts=[[0,0]],area=0,py=0;
  a.forEach(function(v,i){cum+=v;var x=(i+1)/n,y=tot?cum/tot:0;area+=(y+py)/2/n;py=y;pts.push([x,y])});
  var top=a.slice().reverse(),c5=0;for(var i=0;i<Math.min(5,n);i++)c5+=top[i];
  var k=Math.max(1,Math.round(n*0.1)),c10=0;for(var j=0;j<k;j++)c10+=top[j];
  return {pts:pts,gini:1-2*area,n:n,tot:tot,zero:a.filter(function(v){return v===0}).length,top5:tot?c5/tot:0,top10pct:tot?c10/tot:0};
}
function path(pts,W,H,m){return pts.map(function(p,i){return (i?'L':'M')+(m+p[0]*W).toFixed(1)+' '+(m+H-p[1]*H).toFixed(1)}).join('')}
function draw(){
  var key=MET==='n'?'n':'iss';
  var S=pick('is','India'),Dd=pick('id','India');
  var ls=lor(S.map(function(r){return r[key]})),ld=lor(Dd.map(function(r){return r[key]}));
  var W=360,H=300,m=36;
  var svg='<svg viewBox="0 0 '+(W+m+14)+' '+(H+m+22)+'" role="img" aria-label="Lorenz curves">'
   +[0,.25,.5,.75,1].map(function(t){return '<line x1="'+m+'" x2="'+(m+W)+'" y1="'+(m+H-t*H)+'" y2="'+(m+H-t*H)+'" stroke="#eef0e9"/><text x="'+(m-6)+'" y="'+(m+H-t*H+4)+'" text-anchor="end">'+Math.round(t*100)+'%</text><text x="'+(m+t*W)+'" y="'+(m+H+16)+'" text-anchor="middle">'+Math.round(t*100)+'%</text>'}).join('')
   +'<line x1="'+m+'" y1="'+(m+H)+'" x2="'+(m+W)+'" y2="'+m+'" stroke="#9aa08f" stroke-dasharray="4 4"/>'
   +'<path d="'+path(ld.pts,W,H,m)+'" fill="none" stroke="#C98A1F" stroke-width="2.6"/><path d="'+path(ls.pts,W,H,m)+'" fill="none" stroke="#265E30" stroke-width="2.6"/>'
   +'<text x="'+(m+W/2)+'" y="'+(m+H+34)+'" text-anchor="middle">Share of states or districts, poorest in projects first</text></svg>';
  var curve='<div class="pn"><h3>INEQUALITY CURVE (LORENZ)</h3><p class="sb2">If projects were spread evenly, the curve would follow the dashed line. The more it bows down, the more concentrated.</p>'+svg
   +'<div class="lg"><span><i style="background:#265E30"></i>'+ls.n+' states and territories: Gini <b>'+ls.gini.toFixed(2)+'</b></span><span><i style="background:#C98A1F"></i>'+ld.n+' districts: Gini <b>'+ld.gini.toFixed(2)+'</b></span></div></div>';
  var grp={};S.forEach(function(r){var g=grp[r.b]=grp[r.b]||{n:0,iss:0,c:0,names:[]};g.n+=r.n;g.iss+=r.iss;g.c++;g.names.push(r.a)});
  var tot=S.reduce(function(s,r){return s+r[key]},0);
  var GI=['Five industrialised states','Other states','Left-behind regions'],GCOL={'Five industrialised states':'#265E30','Other states':'#A9B79B','Left-behind regions':'#B85829'};
  var GD={'Five industrialised states':'Gujarat, Maharashtra, Karnataka, Andhra Pradesh, Tamil Nadu','Other states':'All remaining states and territories','Left-behind regions':'North-East, Bihar, Jharkhand, Jammu & Kashmir, Ladakh'};
  var cmp='<div class="pn"><h3>INDUSTRIALISED STATES AGAINST LEFT-BEHIND REGIONS</h3><p class="sb2">Share of India’s '+(MET==='n'?'projects':'credits issued')+'.</p>'
   +GI.map(function(g){var x=grp[g]||{n:0,iss:0,c:0};var v=x[key];return '<div class="cm"><div class="t"><span>'+g+' <span class="nt">('+x.c+')</span></span><b>'+pc(v,tot,1)+'</b></div><div class="bar"><i style="width:'+(tot?100*v/tot:0).toFixed(1)+'%;background:'+GCOL[g]+'"></i></div><div class="d">'+GD[g]+': '+ni(x.n)+' projects</div></div>'}).join('')
   +'<p class="hn">Left-behind regions is an editorial grouping: the North-East, Bihar, Jharkhand, Jammu & Kashmir and Ladakh, which are lower-income, hill or conflict-affected regions. Industrialised states are the five with the most industry and projects.</p></div>';
  var ins='<div class="ins"><b>Reading this.</b> The top five states hold <b>'+Math.round(100*ls.top5)+'%</b> of India’s '+(MET==='n'?'projects':'issued credits')+'. Across districts, the top 10% hold <b>'+Math.round(100*ld.top10pct)+'%</b>, and <b>'+ld.zero+'</b> of '+ld.n+' districts have no project on record. '
   +'Projects cluster in the large industrialised states: Mizoram and Lakshadweep have none and Ladakh and Manipur one each. District figures use only the '+ni(Dd.reduce(function(s,r){return s+r.n},0))+' projects whose location could be matched to a district.</div>';
  var D2=Dd.slice().sort(function(a,b){return b[key]-a[key]||b.n-a.n}),top=D2.filter(function(r){return r.n>0}).slice(0,10);
  var S2=S.slice().sort(function(a,b){return a[key]-b[key]||a.a.localeCompare(b.a)});
  var lst=function(title,sub,rows,fn){return '<div class="pn"><h3>'+title+'</h3><p class="sb2">'+sub+'</p><div class="sc"><div class="cr ch"><span></span><span>Name</span><span style="text-align:right">Projects</span><span style="text-align:right">Credits</span></div>'+rows.map(fn).join('')+'</div><p class="hn">Showing the top 5. Scroll inside the list to see the rest.</p></div>'};
  var l1=lst('TOP 10 DISTRICTS','Districts with the most projects.',top,function(r,i){return '<div class="cr"><span class="k">'+(i+1)+'</span><span>'+esc(r.a)+'<small>'+esc(r.b)+'</small></span><span class="v">'+ni(r.n)+'</span><span class="v">'+fm(r.iss)+'</span></div>'});
  var l2=lst('THINNEST STATES AND TERRITORIES','States with the fewest projects, zero first.',S2.slice(0,12),function(r,i){return '<div class="cr'+(r.n===0?' z':'')+'"><span class="k">'+(i+1)+'</span><span>'+esc(r.a)+'</span><span class="v">'+ni(r.n)+'</span><span class="v">'+(r.n?fm(r.iss):'none')+'</span></div>'});
  var pills='<div class="pills"><button class="pill'+(MET==='n'?' on':'')+'" data-m="n">Projects</button><button class="pill'+(MET==='i'?' on':'')+'" data-m="i">Credits issued</button></div>';
  document.getElementById('app').innerHTML=pills+ins+'<div class="g2">'+curve+cmp+'</div><div class="g3">'+l1+l2+'</div>';
  Array.prototype.forEach.call(document.querySelectorAll('[data-m]'),function(b){b.onclick=function(){MET=b.getAttribute('data-m');draw()}});
}
draw();
"""

NEW = [
    # key, chart name, css, js, frame px, grid units
    ('stage', 'SDG claims by project stage: issued, registered, listed and stopped', STAGE_CSS, STAGE_JS, 850, 118),
    ('who', 'Who gets the projects? Big economies against Africa and the least developed countries', WHO_CSS, WHO_JS, 470, 70),
    ('indc', "India's concentration: states, districts and the left-behind regions", IND_CSS, IND_JS, 940, 129),
]
INTRO2 = {
    'stage': ('Which stage are SDG-claiming projects at?',
              'Every project in the dataset sorted into four stages, then split by the goals it claims: how many are issuing credits, registered but not yet issuing, still listed or under validation, or stopped. Goals claimed on a project that never reaches issuance deliver nothing yet.', 11),
    'who': ('Who is left behind? Carbon projects and vulnerable countries',
            'Climate impacts fall hardest on poor and vulnerable countries, yet a few large economies host a very large share of projects. This compares China, India and the other host groups with Africa and the UN list of least developed countries.', 11),
    'indc': ('The same story inside India: states and districts',
             'Within India too the projects cluster in the industrialised states. This shows how unevenly projects are spread across states and districts, and which regions are left behind.', 11),
}


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        import sqlite3
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        from superset.connectors.sqla.models import SqlaTable
        con = sqlite3.connect('/app/cgem/cgem.db')
        build_rows(con)
        con.close()
        tbl = db.session.query(SqlaTable).filter(SqlaTable.table_name == TABLE).first()
        if tbl is None:
            print('v99q: sdg_tab dataset missing, skipped')
            return
        tbl.fetch_metadata()
        db.session.commit()
        ref = db.session.query(Slice).filter(Slice.slice_name == 'Registry intelligence: the leading registries side by side').first()
        slices = {}
        for key, name, css, js, ph, units in NEW:
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
            if TAB_ID not in pos or 'CHART-sdg-stage' in pos:
                continue
            base = ['ROOT_ID', 'GRID_ID', 'TABS-main', TAB_ID]
            rows = pos[TAB_ID]['children']

            def make(key):
                title, body, h = INTRO2[key]
                code, height = md(key, title, body, h)
                mid, rid = f'MARKDOWN-sdg-{key}', f'ROW-sdg-{key}-m'
                pos[mid] = {'children': [], 'id': mid, 'meta': {'code': code, 'height': height, 'width': 12}, 'parents': base + [rid], 'type': 'MARKDOWN'}
                pos[rid] = {'children': [mid], 'id': rid, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
                sl = slices[key]
                units = [u for k, _n, _c, _j, _h, u in NEW if k == key][0]
                cid, crid = f'CHART-sdg-{key}', f'ROW-sdg-{key}-c'
                comp = copy.deepcopy(pos['CHART-sdg-kpi'])
                comp['id'] = cid
                comp['parents'] = base + [crid]
                comp['meta'] = {'chartId': sl.id, 'sliceName': sl.slice_name, 'height': units, 'width': 12, 'uuid': str(sl.uuid)}
                pos[cid] = comp
                pos[crid] = {'children': [cid], 'id': crid, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
                return [rid, crid]
            a = make('stage')
            b = make('who') + make('indc')
            i = rows.index('ROW-sdg-const-c') + 1 if 'ROW-sdg-const-c' in rows else len(rows)
            rows[i:i] = a
            j = rows.index('ROW-sdg-eff-c') + 1 if 'ROW-sdg-eff-c' in rows else rows.index('ROW-sdg-state-m')
            rows[j:j] = b
            d.position_json = json.dumps(pos)
            print('v99q: added stage, who and India concentration charts')
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:  # never break the build
        import traceback
        traceback.print_exc()
        print('v99q skipped:', e)
