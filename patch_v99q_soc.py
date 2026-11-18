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

SG_CSS = """
.sc{max-height:470px;overflow:auto;border:1px solid #eef0e9;border-radius:10px}
table{border-collapse:separate;border-spacing:2px;width:100%;min-width:900px}
th{position:sticky;top:0;background:#fff;z-index:2;padding:4px 0 6px;font-weight:600;font-size:10.5px;color:#555}
th.s,td.s{position:sticky;left:0;background:#fff;z-index:1;text-align:left;min-width:170px;padding:0 8px}
th.s{z-index:3}
th i{display:inline-block;min-width:24px;height:22px;border-radius:6px;text-align:center;font:800 11px/22px 'Geist Mono',ui-monospace,Menlo,monospace}
td.s{font-size:12.5px;font-weight:600;white-space:nowrap}td.s small{display:block;font:500 10.5px Geist,Arial,sans-serif;color:#8a9080}
td.c{text-align:center;height:26px;border-radius:5px;font:600 11px 'Geist Mono',ui-monospace,Menlo,monospace;min-width:38px}
.hn{font-size:11px;color:#888;margin:8px 0 0}
.lgd{display:flex;align-items:center;gap:8px;font-size:11px;color:#777;margin:8px 0 0}.lgd i{display:inline-block;width:150px;height:9px;border-radius:5px;background:linear-gradient(90deg,rgba(38,94,48,.04),rgba(38,94,48,1))}
"""
SG_JS = r"""
var MODE='s',SORT='n';
function draw(){
  var tot={},cell={};
  pick('sd','India',function(r){return r.b==='state'}).forEach(function(r){if(r.a==='0')tot[r.c]=r.n;else(cell[r.c]=cell[r.c]||{})[r.a]=r.n});
  var names=Object.keys(tot).filter(function(k){return tot[k]>=3});
  names.sort(function(a,b){return SORT==='n'?tot[b]-tot[a]:a.localeCompare(b)});
  var hid=Object.keys(tot).length-names.length;
  var th='<th class="s">State</th>';for(var g=1;g<=17;g++)th+='<th title="'+esc(SDG[g][0])+'"><i style="background:'+SDG[g][1]+';color:'+ink(SDG[g][1])+'">'+g+'</i></th>';
  var rows=names.map(function(k){
    var tds='';for(var g=1;g<=17;g++){var n=(cell[k]||{})[g]||0,sh=n/tot[k];var a=MODE==='s'?sh:Math.min(1,n/Math.max.apply(null,names.map(function(x){return (cell[x]||{})[g]||0})));
      tds+='<td class="c" title="'+esc(SDG[g][0])+': '+n+' of '+tot[k]+' projects" style="background:rgba(38,94,48,'+(0.04+0.96*a).toFixed(2)+');color:'+(a>.5?'#fff':'#333')+'">'+(n?(MODE==='s'?Math.round(100*sh)+'%':n):'\u2013')+'</td>'}
    return '<tr><td class="s">'+esc(k)+'<small>'+ni(tot[k])+' SDG-reporting projects</small></td>'+tds+'</tr>'}).join('');
  var h='<div class="pills"><button class="pill'+(MODE==='s'?' on':'')+'" data-m="s">Share of the state’s projects</button><button class="pill'+(MODE==='c'?' on':'')+'" data-m="c">Number of projects</button><span style="width:12px"></span>'
   +'<button class="pill'+(SORT==='n'?' on':'')+'" data-o="n">Most projects first</button><button class="pill'+(SORT==='a'?' on':'')+'" data-o="a">A to Z</button></div>'
   +'<div class="sc"><table><thead><tr>'+th+'</tr></thead><tbody>'+rows+'</tbody></table></div>'
   +'<div class="lgd">'+(MODE==='s'?'0%':'few')+'<i></i>'+(MODE==='s'?'100% of the state’s SDG-reporting projects':'most projects for that goal')+'</div>'
   +'<div class="hn">Only projects that report SDG goals. '+hid+' states or territories with fewer than 3 such projects are left out. A project can claim several goals, so each row adds up to more than 100%. Hover a cell for the count.</div>';
  document.getElementById('app').innerHTML=h;
  Array.prototype.forEach.call(document.querySelectorAll('[data-m]'),function(b){b.onclick=function(){MODE=b.getAttribute('data-m');draw()}});
  Array.prototype.forEach.call(document.querySelectorAll('[data-o]'),function(b){b.onclick=function(){SORT=b.getAttribute('data-o');draw()}});
}
draw();
"""

PROG_CSS = """
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px}
.pn{border:1px solid #e3e6dc;border-radius:12px;padding:12px 14px;background:#fbfcf9}
.pn h3{margin:0 0 6px;font:700 11px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;color:#333}
.pn ul{margin:0;padding-left:16px;font-size:12.5px;line-height:1.5}.pn li{margin-bottom:5px}
.ins{border-left:4px solid #C98A1F;background:#FFF9EC;border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5;margin-bottom:12px}
.stk{display:flex;height:26px;border-radius:8px;overflow:hidden;margin:4px 0 6px}.stk b{display:flex;align-items:center;justify-content:center;color:#fff;font:700 11.5px 'Geist Mono',ui-monospace,Menlo,monospace}
.lgd{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#555;margin-bottom:12px}.lgd i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.hd,.rw{display:grid;gap:10px;align-items:center}
.wr{grid-template-columns:230px 1.05fr 1.3fr 96px}
.hd{padding:0 8px 6px;font-size:10.5px;color:#7a8270;text-transform:uppercase;letter-spacing:.05em;font-weight:600;border-bottom:1px solid #eef0e9}
.rw{padding:6px 8px;border-radius:8px;font-size:12.5px;line-height:1.35}.rw:nth-child(even){background:#f8faf5}
.nm{display:flex;align-items:center;gap:8px;font-weight:600}
.nm i{display:inline-block;min-width:22px;height:22px;border-radius:6px;text-align:center;font:800 11px/22px 'Geist Mono',ui-monospace,Menlo,monospace}
.tg{color:#555;font-size:12px}.v{font:600 12px 'Geist Mono',ui-monospace,Menlo,monospace;text-align:right}
.ir{grid-template-columns:230px 1fr 56px 80px 96px}
.sr{grid-template-columns:30px 220px 1fr 50px 60px 96px 82px}
.bar{position:relative;height:14px;border-radius:7px;background:#eef0ea}.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:7px}
.bar u{position:absolute;top:-3px;bottom:-3px;width:2px;background:#333;opacity:.55}
.sc{max-height:520px;overflow-y:auto;border-bottom:1px solid #eef0e9}.hd.s{position:sticky;top:0;background:#fff;z-index:2}
.hn{font-size:11px;color:#888;margin:8px 0 0;line-height:1.5}
.k1{color:#8a9080;font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace}
@media (max-width:1000px){.g2{grid-template-columns:1fr}}
"""
PROG_JS = r"""
var VIEW='w',SORT='s';
var GOAL=[null,
['Eradicate extreme poverty; halve national poverty','800M+ people in extreme poverty; only 1 in 5 countries on track to halve national poverty'],
['End hunger and all malnutrition; double small farmers’ productivity','1 in 11 people hungry (2023); child stunting 26.4% to 23.2%'],
['Under-5 deaths at most 25 per 1,000; maternal deaths under 70 per 100,000','Under-5 deaths 37 per 1,000; maternal deaths 197 per 100,000'],
['Free, quality primary and secondary schooling for all','272M children out of school; 60% finish upper secondary'],
['End discrimination and violence against women and girls','Women hold 27.2% of parliament seats; do 2.5x the unpaid care work'],
['Safe drinking water and sanitation for everyone','2.2B lack safe drinking water; 3.4B lack safe sanitation'],
['Universal modern energy access; a much larger renewable share','92% have electricity; 2.1B lack clean cooking'],
['Full employment and decent work for all; end child labour','Unemployment 5.0% (record low), but 57.8% of workers are informal'],
['Resilient infrastructure; affordable internet in the poorest countries','Internet reach 68% (40% in 2015); 2.6B still offline'],
['Income of the bottom 40% growing faster than the average','Bottom 40% outgrew the average in ~6 of 10 countries; refugees at 37.8M'],
['Safe, affordable housing and basic services; no slums','1.12B people live in slums or informal settlements'],
['Halve food waste; sound management of chemicals and waste','No headline figure in the UN key findings used here'],
['Bring climate action into policy; build resilience to disasters','2024 hottest year on record: 1.55°C above pre-industrial'],
['Cut marine pollution; protect and restore ocean ecosystems','84% of coral reefs hit by bleaching (2023-25), the worst on record'],
['Halt deforestation and biodiversity loss; restore degraded land','Protected key biodiversity areas doubled since 2000'],
['Cut violence; effective, accountable institutions for all','120M+ people forcibly displaced; ~50,000 conflict deaths in 2024'],
['Mobilise finance (aid at 0.7% of income); close the digital divide','Aid fell 7.1% in 2024; developing countries face a $4T yearly SDG financing gap']];
var IG={1:72,3:77,4:61,5:49,6:89,7:96,9:61,10:65,11:83,13:67,15:75};
var IDX=[['Andaman and Nicobar Islands',58,70],['Andhra Pradesh',64,74],['Arunachal Pradesh',51,65],['Assam',49,65],['Bihar',48,57],['Chandigarh',68,77],['Chhattisgarh',58,67],['Dadra and Nagar Haveli and Daman and Diu',57,66],['Delhi',62,70],['Goa',64,77],['Gujarat',64,74],['Haryana',55,72],['Himachal Pradesh',69,77],['Jammu and Kashmir',53,74],['Jharkhand',50,62],['Karnataka',64,75],['Kerala',69,79],['Ladakh',null,65],['Lakshadweep',62,66],['Madhya Pradesh',52,67],['Maharashtra',64,73],['Manipur',59,72],['Meghalaya',52,63],['Mizoram',59,72],['Nagaland',51,63],['Odisha',51,66],['Puducherry',65,74],['Punjab',60,76],['Rajasthan',59,67],['Sikkim',58,76],['Tamil Nadu',66,78],['Telangana',61,74],['Tripura',55,71],['Uttar Pradesh',42,67],['Uttarakhand',60,79],['West Bengal',56,70]];
function cat(x){return x>=65?['Front-runner','#265E30']:x>=50?['Performer','#C98A1F']:['Aspirant','#B85829']}
function draw(){
  var allp={},ip={};
  pick('sd','World',function(r){return r.b==='all'&&r.a!=='0'}).forEach(function(r){allp[r.a]=r.n});
  pick('sd','India',function(r){return r.b==='all'&&r.a!=='0'}).forEach(function(r){ip[r.a]=r.n});
  var h='<div class="pills"><button class="pill'+(VIEW==='w'?' on':'')+'" data-v="w">World: the 17 goals</button><button class="pill'+(VIEW==='i'?' on':'')+'" data-v="i">India: national scores</button><button class="pill'+(VIEW==='s'?' on':'')+'" data-v="s">Indian states</button></div>';
  if(VIEW==='w'){
    h+='<div class="ins"><b>The 2030 deadline.</b> Of the 169 targets with data, only <b>35%</b> are on track or progressing moderately, nearly half are moving too slowly and <b>18%</b> have gone backwards (UN SDG Report 2025). Projects in this dataset claim these goals; the table sets what each goal asks for against where the world stands.</div>'
     +'<div class="stk"><b style="width:35%;background:#265E30">35%</b><b style="width:47%;background:#C98A1F">about 47%</b><b style="width:18%;background:#B85829">18%</b></div>'
     +'<div class="lgd"><span><i style="background:#265E30"></i>on track or moderate progress</span><span><i style="background:#C98A1F"></i>too slow or marginal</span><span><i style="background:#B85829"></i>regressed</span></div>';
    h+='<div class="hd wr"><span>Goal</span><span>What it asks for by 2030</span><span>Where the world stands</span><span style="text-align:right">Carbon projects claiming it</span></div>';
    for(var g=1;g<=17;g++){var c=SDG[g][1];h+='<div class="rw wr"><span class="nm"><i style="background:'+c+';color:'+ink(c)+'">'+g+'</i>'+esc(SDG[g][0])+'</span><span class="tg">'+esc(GOAL[g][0])+'</span><span>'+esc(GOAL[g][1])+'</span><span class="v">'+(allp[g]?ni(allp[g]):'–')+'</span></div>'}
    h+='<div class="hn">Source: UN, The Sustainable Development Goals Report 2025. The last column counts projects in this dashboard whose registry lists the goal (only some registries report goals).</div>';
  }else if(VIEW==='i'){
    var tr=[[2018,57],[2019,60],[2020,66],[2023,71]];
    h+='<div class="ins"><b>India has moved from 57 to 71 out of 100</b> on NITI Aayog’s SDG India Index (100 = every target met). Gender equality (49) is the weakest scored goal; clean energy (96) the strongest, and reduced inequalities is the only goal that slipped (67 to 65 since 2020-21).</div>';
    h+='<div class="g2" style="margin-top:0"><div class="pn"><h3>COMPOSITE SCORE OVER TIME</h3>'+tr.map(function(t){return '<div class="rw" style="grid-template-columns:70px 1fr 40px;padding:4px 0"><span>'+(t[0]===2023?'2023-24':t[0]===2020?'2020-21':t[0])+'</span><div class="bar"><i style="width:'+t[1]+'%;background:#265E30"></i></div><span class="v">'+t[1]+'</span></div>'}).join('')+'<div class="hn">Bands: below 50 aspirant, 50 to 64 performer, 65 to 99 front-runner, 100 achiever.</div><ul style="margin-top:14px"><li>State scores now run from <b>57</b> (Bihar) to <b>79</b> (Kerala and Uttarakhand).</li><li><b>32</b> states and territories are front-runners, up from 22 in 2020-21.</li><li>At the pace of the last three years (about +5 points), India would still be short of 100 in 2030.</li></ul></div>'
     +'<div class="pn"><h3>HOW FAR IS EACH GOAL FROM 100?</h3><div class="hd ir" style="grid-template-columns:200px 1fr 48px 70px"><span>Goal</span><span>Score (100 = goal met)</span><span style="text-align:right">Gap</span><span style="text-align:right">Projects</span></div>'
     +Object.keys(IG).map(Number).sort(function(a,b){return IG[a]-IG[b]}).map(function(g){var c=SDG[g][1];return '<div class="rw" style="grid-template-columns:200px 1fr 48px 70px"><span class="nm"><i style="background:'+c+';color:'+ink(c)+'">'+g+'</i>'+esc(SDG[g][0])+'</span><div class="bar"><i style="width:'+IG[g]+'%;background:'+(IG[g]<50?'#B85829':IG[g]<65?'#C98A1F':'#265E30')+'"></i></div><span class="v">'+(100-IG[g])+'</span><span class="v">'+ni(ip[g]||0)+'</span></div>'}).join('')
     +'<div class="hn">Goals 2, 8, 12 and 16 have no national score in the sources used; goal 14 applies to coastal states only. Projects = Indian projects claiming the goal.</div></div></div>';
  }else{
    var T={};pick('is','India').forEach(function(r){T[r.a]=r.n});
    var rows=IDX.map(function(x){return {s:x[0],a:x[1],b:x[2],n:T[x[0]]||0}});
    rows.sort(function(p,q){return SORT==='s'?q.b-p.b:SORT==='c'?((q.a==null?-1:q.b-q.a)-(p.a==null?-1:p.b-p.a)):q.n-p.n});
    var tot=rows.reduce(function(s,r){return s+r.n},0),srt=rows.slice().sort(function(p,q){return q.b-p.b||q.n-p.n}),top=srt.slice(0,6),low=srt.slice(-6);
    var sh=function(a){return a.reduce(function(s,r){return s+r.n},0)};
    h+='<div class="ins"><b>Reading this.</b> The six best-scoring states hold <b>'+pc(sh(top),tot,0)+'</b> of the carbon projects with a known state, the six lowest-scoring only <b>'+pc(sh(low),tot,0)+'</b> ('+low.map(function(r){return r.s}).join(', ')+'). Scores have risen almost everywhere since 2018, but no state is near 100: even the best are at 79, so every state is at least 21 points short.</div>';
    h+='<div class="pills"><button class="pill'+(SORT==='s'?' on':'')+'" data-o="s">Sort by SDG score</button><button class="pill'+(SORT==='c'?' on':'')+'" data-o="c">Sort by gain since 2018</button><button class="pill'+(SORT==='n'?' on':'')+'" data-o="n">Sort by carbon projects</button></div>';
    h+='<div class="sc"><div class="hd sr s"><span></span><span>State</span><span>SDG India Index 2023-24 (100 = goals met)</span><span style="text-align:right">Gap</span><span style="text-align:right">Since 2018</span><span style="text-align:right">Band</span><span style="text-align:right">Carbon projects</span></div>';
    rows.forEach(function(r,i){var c=cat(r.b);h+='<div class="rw sr"><span class="k1">'+(i+1)+'</span><span class="nm">'+esc(r.s)+'</span><div class="bar"><i style="width:'+r.b+'%;background:'+c[1]+'"></i><u style="left:65%" title="front-runner line"></u></div><span class="v">'+(100-r.b)+'</span><span class="v">'+(r.a==null?'n/a':'+'+(r.b-r.a))+'</span><span class="v" style="color:'+c[1]+';font-size:11px">'+c[0]+'</span><span class="v">'+ni(r.n)+'</span></div>'});
    h+='</div><div class="hn">The vertical line marks 65, the front-runner threshold. Carbon projects = all projects on the registries in this dashboard located in the state. Ladakh has no 2018 score (it became a union territory in 2019). Source: NITI Aayog SDG India Index 2023-24, as published in the RBI Handbook of Statistics on Indian States. The index gives scores, not the reasons behind each state’s gap.</div>';
  }
  h+='<div class="g2"><div class="pn"><h3>WHY THE WORLD IS OFF TRACK</h3><ul><li><b>Money.</b> Developing countries face a $4 trillion yearly financing gap; debt payments hit a record $1.4 trillion in 2023 and official aid fell 7.1% in 2024.</li><li><b>Conflict.</b> Over 120 million people were forcibly displaced by the end of 2024.</li><li><b>Climate.</b> 2024 was the hottest year recorded (1.55°C), hitting the poorest first.</li><li><b>Setbacks.</b> COVID-19 cut healthy life expectancy by 1.8 years and rising inequality slows the rest.</li></ul></div>'
   +'<div class="pn"><h3>WHY INDIA STILL FALLS SHORT (NITI AAYOG)</h3><ul><li><b>Gender equality (49).</b> Sex ratio at birth, women’s ownership of land and assets, and women’s employment and labour-force participation.</li><li><b>Reduced inequalities (65, falling).</b> Unequal job opportunities at the low end and gender gaps in work.</li><li><b>Education (61).</b> Quality, not access, mainly in central India.</li><li><b>Climate (67).</b> Disaster preparedness scores just 19; only 55% of hazardous waste is recycled or reused.</li><li><b>Justice.</b> 71% of IPC crimes reach charge sheet.</li></ul></div></div>';
  document.getElementById('app').innerHTML=h;
  Array.prototype.forEach.call(document.querySelectorAll('[data-v]'),function(b){b.onclick=function(){VIEW=b.getAttribute('data-v');draw()}});
  Array.prototype.forEach.call(document.querySelectorAll('[data-o]'),function(b){b.onclick=function(){SORT=b.getAttribute('data-o');draw()}});
}
draw();
"""

NEW = [
    # key, chart name, css, js, frame px, grid units
    ('prog', 'How far are the Goals from being met? World, India and Indian states', PROG_CSS, PROG_JS, 1050, 142),
    ('stage', 'SDG claims by project stage: issued, registered, listed and stopped', STAGE_CSS, STAGE_JS, 850, 118),
    ('who', 'Who gets the projects? Big economies against Africa and the least developed countries', WHO_CSS, WHO_JS, 470, 70),
    ('sgrid', 'Which goals does each Indian state claim? (state by goal heat map)', SG_CSS, SG_JS, 580, 84),
    ('indc', "India's concentration: states, districts and the left-behind regions", IND_CSS, IND_JS, 940, 129),
]
INTRO2 = {
    'prog': ('How far are the Goals from being met?',
             'Before looking at the projects: what each goal asks for, how much of it the world and India have achieved, how every Indian state scores, and why the gaps remain.', 11),
    'sgrid': ('Indian states and the goals they claim',
              'Each row is a state, each column one of the 17 goals. Darker means a larger share of that state’s SDG-reporting projects claim the goal, so you can see which states lean on energy, water, health or land.', 11),
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
            p0 = make('prog')
            a = make('stage')
            b = make('who') + make('indc') + make('sgrid')
            i = rows.index('ROW-sdg-const-c') + 1 if 'ROW-sdg-const-c' in rows else len(rows)
            rows[i:i] = a
            k0 = rows.index('ROW-sdg-kpi-c') + 1 if 'ROW-sdg-kpi-c' in rows else 1
            rows[k0:k0] = p0
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
