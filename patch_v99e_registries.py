"""C-GEM v99e online site: the chart "Registry intelligence: the leading registries side by side" now shows the registries that matter for India
(CDM, Verra, Gold Standard, UCR, ICR, GCC, Article 6.4 / PACM) plus Article 6.2, each card seen from India's side, with a footnote on
what the registry is and what it is used for. Article 6.2 numbers come from the article6_* tables (UNEP CCC pipeline)."""
import json
import html as H
import re

MARK = 'cgx-regIN'
NAME = 'Registry intelligence: the leading registries side by side'

CSS_EXTRA = """
.fn{margin-top:12px;border-top:1px dashed #d6d9cf;padding-top:9px;font-size:11.5px;line-height:1.5;color:#444}
.fn b{display:block;font:700 9.5px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.09em;color:var(--c);margin:6px 0 1px}
.fn b:first-child{margin-top:0}
.fn p{margin:0}
.src{font-size:10.5px;color:#888;margin:12px 0 0}
.sub{font-size:11.5px;color:#555;margin:0 0 10px}
.sec .em{font-size:11px;color:#888}
"""

JS = r"""
var D=({{stringify this}}).data;
var A6=__A6__;
var REGS=[
 {k:'Clean Development Mechanism (UNFCCC)',s:'CDM',c:'#8C5BA8',tag:'Legacy UN credits',
  what:'The UN Kyoto Protocol offset scheme (2005 to 2020), run by UNFCCC. It issued CERs (certified emission reductions).',
  use:'Legacy credits for Kyoto and compliance buyers, and a record of India’s early project base. Live projects can move to Article 6.4.'},
 {k:'Verified Carbon Standard',s:'Verra',c:'#2F7FB8',tag:'Largest voluntary standard',
  what:'Verra’s Verified Carbon Standard (VCS), the biggest independent standard for the voluntary carbon market. It issues VCUs.',
  use:'Companies buy VCUs for voluntary offsetting and net-zero claims. Indian renewable, cookstove and tree-planting projects sell here.'},
 {k:'Gold Standard',s:'Gold Standard',c:'#6E9C2E',tag:'Climate + SDG co-benefits',
  what:'A standard set up in 2003 with WWF backing. It certifies climate impact and proof of UN SDG co-benefits.',
  use:'Cookstoves, household energy, water and renewables. Buyers pick it when they want social and health co-benefits shown.'},
 {k:'Universal Carbon Registry (UCR)',s:'UCR',c:'#D9822B',tag:'Simple, low-cost route',
  what:'A registry with a simplified, low-cost listing route. Small projects and Indian developers use it heavily.',
  use:'Voluntary credits (UCR units) from small and household-scale projects, at lower registration cost than the big standards.'},
 {k:'International Carbon Registry (ICR)',s:'ICR',c:'#B5527A',tag:'Few, large projects',
  what:'The International Carbon Registry, Iceland-based, open to many methodologies including carbon removals.',
  use:'Voluntary credits for energy, industrial and removal projects. India has few projects here, but they are large.'},
 {k:'Global Carbon Council',s:'GCC',c:'#0E7C86',tag:'Mostly early pipeline',
  what:'The Global Carbon Council, a Gulf-based programme (Qatar) for the voluntary market.',
  use:'Credits for voluntary buyers, especially in the Gulf. Most Indian projects here are still at listing or registration stage.'},
 {k:'Article 6.4 mechanism (PACM, UNFCCC)',s:'Article 6.4 (PACM)',c:'#265E30',tag:'Successor to CDM',
  what:'The Paris Agreement Crediting Mechanism under Article 6.4, run by the UN Supervisory Body. It replaces the CDM from 2021.',
  use:'Issues A6.4ERs that can count toward a country’s NDC if the host authorises. CDM projects in India transition here.'},
 {k:'PlanVivo',s:'Plan Vivo',c:'#3E8E7E',tag:'Community land-use',
  what:'A foundation-run standard (since 1996) for community-led land-use and nature projects. It issues Plan Vivo Certificates (PVCs).',
  use:'Agroforestry, restoration and community projects where smallholders share the revenue. Buyers pick it for proven community benefit.'},
 {k:'ISOMETRIC',s:'Isometric',c:'#5B6EE1',tag:'Science-led removals',
  what:'A science-led registry (founded 2022) for carbon removal, with detailed public protocols and third-party verification.',
  use:'Buyers of high-integrity durable removals who want strict measurement. India has a few projects here, with very small volumes so far.'},
 {k:'C-Sink',s:'C-Sink (CSI)',c:'#7A5A3A',tag:'Biochar registry',
  what:'The Global Biochar C-Sink registry run by Carbon Standards International (CSI), Switzerland, for biochar carbon sinks.',
  use:'Issues C-Sink credits for biochar made from biomass. Biochar producers and buyers of durable removals use it.'},
 {k:'Puroearth',s:'Puro.earth',c:'#D1495B',tag:'Biochar and removals',
  what:'Puro.earth, a Finland-based registry and standard for engineered carbon removal, including biochar. It issues CORCs (CO2 removal certificates).',
  use:'Durable removal credits (biochar, carbonated materials, wood in construction) that companies buy to meet removal targets.'}
];
var A62={k:'__a62',s:'Article 6.2',c:'#A23B72',tag:'Government to government',
  what:'Bilateral carbon trading between countries under Article 6.2 of the Paris Agreement. The units are called ITMOs.',
  use:'Lets India sell mitigation outcomes to partner countries (Japan, South Korea), which count them toward their own NDC. India must authorise each transfer.'};
function fm(x){x=+x||0;if(x>=1e9)return(x/1e9).toFixed(2).replace(/\.?0+$/,'')+'B';if(x>=1e6)return(x/1e6).toFixed(x>=1e8?0:1).replace(/\.0$/,'')+'m';if(x>=1e3)return Math.round(x/1e3)+'k';return Math.round(x)+''}
function pct(a,b){return b?(100*a/b).toFixed(1)+'%':'n/a'}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function topn(o,n,key){return Object.keys(o).map(function(k){return[k,o[k]]}).filter(function(a){return a[1][key]>0&&a[0]!=='Not recorded'}).sort(function(a,b){return b[1][key]-a[1][key]}).slice(0,n)}
var SEL='All';
function agg(r){
  var x={tot:0,iss:0,ret:0,n:0,act:{},st:{},vs:0,vw:0};
  D.forEach(function(d){
    if(d.registry!==r)return;
    var v=+d.iss||0;
    if(d.lvl==='c'&&d.kind==='s'){x.tot+=v;if(d.code==='IND'){x.iss+=v;x.ret+=(+d.ret||0);x.n+=(+d.n||0);}}
    else if(d.lvl==='c'&&d.kind==='a'&&d.code==='IND'){var a=x.act[d.k]||(x.act[d.k]={v:0,n:0});a.v+=v;a.n+=(+d.n||0);}
    else if(d.lvl==='c'&&d.kind==='v'&&d.code==='IND'){var y=+d.k;if(y>1990&&v>0){x.vs+=y*v;x.vw+=v;}}
    else if(d.lvl==='s'&&d.kind==='s'){var s=x.st[d.country]||(x.st[d.country]={v:0,n:0});s.v+=v;s.n+=(+d.n||0);}
  });
  return x;
}
function fnote(g){return '<div class="fn"><b>WHAT IT IS</b><p>'+esc(g.what)+'</p><b>WHAT IT IS USED FOR</b><p>'+esc(g.use)+'</p></div>'}
function head(g){return '<div class="hd"><div class="nm"><i></i>'+esc(g.s)+'</div><div class="bd">'+esc(g.tag)+'</div></div>'}
function card(g,x){
  var has=x.iss>0, h='<div class="cd" style="--c:'+g.c+'">'+head(g);
  if(has) h+='<div class="big"><b>'+fm(x.iss)+'</b><span>'+pct(x.iss,x.tot)+' of this registry’s credits are Indian</span></div>';
  else h+='<div class="big"><b>'+(x.n||0).toLocaleString('en-US')+'</b><span>Indian projects, no credits issued yet</span></div>';
  var acts=topn(x.act,3,has?'v':'n'), sts=topn(x.st,3,has?'v':'n');
  h+='<div class="sec"><h4>TOP INDIAN PROJECT TYPES</h4>'+(acts.length?acts.map(function(a){return'<div class="rw a"><span>'+esc(a[0])+'</span><b>'+(has?fm(a[1].v):a[1].n.toLocaleString('en-US'))+'</b></div>'}).join(''):'<div class="em">not recorded</div>')+'</div>';
  h+='<div class="sec"><h4>TOP INDIAN STATES</h4>'+(sts.length?sts.map(function(a){return'<div class="rw"><span>'+esc(a[0])+'</span><b>'+(has?fm(a[1].v):a[1].n.toLocaleString('en-US'))+'</b></div>'}).join(''):'<div class="em">not located</div>')+'</div>';
  var rep=x.ret>0;
  h+='<div class="sec"><h4>INDIA SNAPSHOT</h4><div class="rw"><span>Projects</span><b>'+(x.n||0).toLocaleString('en-US')+'</b></div>'
   +'<div class="rw"><span>Retired</span><b class="red">'+(has?(rep?fm(x.ret):'none yet'):'n/a')+'</b></div>'
   +'<div class="rw"><span>Ret. rate</span><b class="grn">'+(has?pct(x.ret,x.iss):'n/a')+'</b></div>'
   +'<div class="rw"><span>Avg vintage</span><b>'+(x.vw?'~'+Math.round(x.vs/x.vw):'n/a')+'</b></div></div>';
  return h+fnote(g)+'</div>';
}
function card62(){
  var g=A62,h='<div class="cd" style="--c:'+g.c+'">'+head(g);
  h+='<div class="big"><b>'+A6.agreements+'</b><span>cooperative approaches with India</span></div>';
  h+='<div class="sec"><h4>INDIA’S POSITION</h4><div class="rw"><span>Role</span><b>'+esc(A6.role)+'</b></div><div class="rw"><span>Partners</span><b>'+esc(A6.partners)+'</b></div>'
   +'<div class="rw"><span>Registered activities</span><b>'+A6.a62+'</b></div><div class="rw"><span>Authorised ITMOs</span><b>'+A6.itmo+'</b></div></div>';
  h+='<div class="sec"><h4>WORLD, ARTICLE 6.2</h4><div class="rw"><span>Cooperative approaches</span><b>'+A6.w_coop+'</b></div><div class="rw"><span>Countries</span><b>'+A6.w_cty+'</b></div>'
   +'<div class="rw"><span>Registered activities</span><b>'+A6.w_act+'</b></div><div class="rw"><span>Outcomes issued</span><b>'+A6.w_iss+'m t</b></div></div>';
  h+='<div class="sec"><h4>FOR COMPARISON, ARTICLE 6.4</h4><div class="rw"><span>Registered activities</span><b>'+A6.p_act+'</b></div><div class="rw"><span>Outcomes issued</span><b>'+A6.p_iss+'m t</b></div></div>';
  return h+fnote(g)+'<div class="nt">UNEP CCC Article 6 Pipeline, as of '+esc(A6.as_of)+'.</div></div>';
}
function stackChart(list){
  var W=420,H=230,L=46,B=26,T=8, mx=Math.max.apply(null,list.map(function(a){return a[2].iss}))||1;
  var gap=(W-L-10)/list.length, bw=gap*.62;
  var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%">';
  for(var i=0;i<=4;i++){var y=T+(H-T-B)*(1-i/4); s+='<line x1="'+L+'" x2="'+W+'" y1="'+y+'" y2="'+y+'" stroke="#e6e8e1"/><text x="'+(L-6)+'" y="'+(y+3)+'" font-size="9" fill="#777" text-anchor="end">'+fm(mx*i/4)+'</text>';}
  list.forEach(function(a,i){var x=L+gap*i+(gap-bw)/2, hi=(H-T-B)*a[2].iss/mx, hr=(H-T-B)*Math.min(a[2].ret,a[2].iss)/mx, y0=H-B;
    s+='<rect x="'+x+'" y="'+(y0-hi)+'" width="'+bw+'" height="'+hi+'" fill="#D9DBD6" rx="3"/><rect x="'+x+'" y="'+(y0-hr)+'" width="'+bw+'" height="'+hr+'" fill="'+a[0].c+'"/>';
    s+='<text x="'+(x+bw/2)+'" y="'+(H-10)+'" font-size="9.5" fill="#333" text-anchor="middle">'+esc(a[0].s.replace(' (PACM)',''))+'</text><title>'+esc(a[0].k)+'</title>';});
  return s+'</svg>';
}
function actChart(list){
  var acts={}; list.forEach(function(a){topn(a[2].act,4,'v').forEach(function(t){acts[t[0]]=(acts[t[0]]||0)+t[1].v})});
  var K=Object.keys(acts).sort(function(a,b){return acts[b]-acts[a]}).slice(0,6);
  var W=420,H=250,L=46,B=44,T=8, mx=1;
  K.forEach(function(k){list.forEach(function(a){mx=Math.max(mx,(a[2].act[k]||{v:0}).v)})});
  var g=(W-L-10)/K.length, bw=g*.8/list.length;
  var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%">';
  for(var i=0;i<=4;i++){var y=T+(H-T-B)*(1-i/4); s+='<line x1="'+L+'" x2="'+W+'" y1="'+y+'" y2="'+y+'" stroke="#e6e8e1" stroke-dasharray="3 3"/><text x="'+(L-6)+'" y="'+(y+3)+'" font-size="9" fill="#777" text-anchor="end">'+fm(mx*i/4)+'</text>';}
  K.forEach(function(k,j){list.forEach(function(a,i){var v=(a[2].act[k]||{v:0}).v, h=(H-T-B)*v/mx, x=L+g*j+g*.1+bw*i;
      s+='<rect x="'+x+'" y="'+(H-B-h)+'" width="'+(bw-1)+'" height="'+h+'" fill="'+a[0].c+'"><title>'+esc(a[0].s)+', '+esc(k)+': '+fm(v)+'</title></rect>';});
    var lab=k.length>16?k.slice(0,15)+'…':k;
    s+='<text x="'+(L+g*j+g/2)+'" y="'+(H-B+14)+'" font-size="9" fill="#333" text-anchor="middle">'+esc(lab)+'</text>';});
  return s+'</svg>';
}
function legend(list,extra){return'<div class="lg">'+list.map(function(a){return'<span><i style="background:'+a[0].c+'"></i>'+esc(a[0].s.replace(' (PACM)',''))+'</span>'}).join('')+(extra||'')+'</div>'}
function draw(){
  var data=REGS.map(function(g){return[g,g.k,agg(g.k)]});
  var withCr=data.filter(function(a){return a[2].iss>0}).sort(function(a,b){return b[2].iss-a[2].iss}).slice(0,6);
  var bar='<button class="pill'+(SEL==='All'?' on':'')+'" data-r="All">All</button>'+REGS.concat([A62]).map(function(g){return'<button class="pill'+(SEL===g.k?' on':'')+'" data-r="'+esc(g.k)+'">'+esc(g.s)+'</button>'}).join('');
  document.getElementById('bar').innerHTML=bar;
  var p1='<div class="pn"><h3>INDIA: RETIRED VS REMAINING, TOP 6 REGISTRIES</h3>'+legend(withCr,'<span><i style="background:#D9DBD6"></i>Remaining</span>')+stackChart(withCr)+'<div class="nt">Bar = credits issued to Indian projects; coloured part = retired.</div></div>';
  var p2='<div class="pn"><h3>INDIA: TOP PROJECT TYPES, TOP 6 REGISTRIES</h3>'+legend(withCr)+actChart(withCr)+'<div class="nt">Credits issued to Indian projects, leading project types.</div></div>';
  var lay=document.getElementById('lay'), cards=data.map(function(a){return card(a[0],a[2])}); cards.push(card62());
  if(SEL==='All'){ lay.style.gridTemplateColumns='repeat(3,1fr)'; lay.innerHTML=cards.join('')+p1+'<div style="grid-column:span 2">'+p2+'</div>'; }
  else { lay.style.gridTemplateColumns='1fr 1.05fr';
    var i=SEL==='__a62'?cards.length-1:REGS.map(function(g){return g.k}).indexOf(SEL);
    lay.innerHTML=cards[i]+'<div class="side">'+p1+p2+'</div>'; }
  var f=document.createElement('p');f.className='src';f.textContent='Source: C-GEM mastersheet (registry project data, India view); Article 6.2 and 6.4 figures from the UNEP CCC Article 6 Pipeline.';lay.parentNode.appendChild(f);
  var old=document.querySelectorAll('.src');for(var q=0;q<old.length-1;q++)old[q].remove();
  Array.prototype.forEach.call(document.querySelectorAll('.pill'),function(b){b.onclick=function(){SEL=b.getAttribute('data-r');draw()}});
}
draw();
"""


def a6_json(con):
    con.row_factory = None
    h = con.execute("select agreements, partners, role, a62_activities, as_of from article6_hosts where country='India'").fetchone()
    ov = {(r[0], r[1]): r for r in con.execute("select indicator, sub_indicator, a62_value, pacm_value, a62_countries from article6_overview")}
    g = lambda k, i: ov[k][i]
    n = lambda x: int(x) if float(x) == int(x) else x
    return {'agreements': h[0], 'partners': h[1], 'role': h[2], 'a62': h[3], 'itmo': 0, 'as_of': h[4],
            'w_coop': n(g(('Cooperative approaches', None), 2)), 'w_cty': n(g(('Cooperative approaches', None), 4)),
            'w_act': n(g(('Registered Activities', None), 2)), 'w_iss': g(('Registered Activities', 'Mitigation Outcome Issued (tCO₂e)'), 2),
            'p_act': n(g(('Registered Activities', None), 3)), 'p_iss': g(('Registered Activities', 'Mitigation Outcome Issued (tCO₂e)'), 3)}


def build(old_tpl, a6, h=2860):
    m = re.search(r'srcdoc="(.*?)" style="', old_tpl, re.S)
    doc = H.unescape(m.group(1))
    i = doc.index('<script>\nvar D=')
    j = doc.rindex('</script></body>')
    doc = doc[:i] + '<script>' + JS.replace('__A6__', json.dumps(a6, ensure_ascii=False)) + doc[j:]
    doc = doc.replace('</style></head>', CSS_EXTRA + '/*' + MARK + '*/</style></head>', 1)
    new_attr = H.escape(doc, quote=True).replace('\n', '&#10;')
    out = old_tpl[:m.start(1)] + new_attr + old_tpl[m.end(1):]
    return re.sub(r'height:\d+px;border:0', f'height:{h}px;border:0', out)


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        import sqlite3
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        con = sqlite3.connect('/app/cgem/cgem.db')
        a6 = a6_json(con)
        con.close()
        n = 0
        for sl in db.session.query(Slice).filter(Slice.slice_name == NAME).all():
            p = json.loads(sl.params)
            t = p.get('handlebarsTemplate') or ''
            if MARK in H.unescape(t) or 'srcdoc=' not in t:
                continue
            p['handlebarsTemplate'] = build(t, a6)
            p['row_limit'] = max(int(p.get('row_limit') or 0), 20000)
            sl.params = json.dumps(p)
            sl.query_context = None
            sl.description = 'The registries that matter for India (CDM, Verra, Gold Standard, UCR, ICR, GCC, Article 6.4, Plan Vivo, Isometric, C-Sink, Puro.earth) plus Article 6.2, each with what it is and what it is used for.'
            n += 1
            for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
                pos = json.loads(d.position_json)
                for comp in pos.values():
                    if isinstance(comp, dict) and comp.get('meta', {}).get('chartId') == sl.id:
                        comp['meta']['height'] = 358
                d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99e: registry cards for India:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional chart
        import traceback
        traceback.print_exc()
        print('v99e: skipped:', exc)
