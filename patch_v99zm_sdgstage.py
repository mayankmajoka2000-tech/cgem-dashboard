"""v99zm: the project-stage split (issued / registered / listed / stopped) moves into the 17-goals chart.
Each goal's detail panel now ends with a stage strip for that goal; the separate stage chart comes off."""
import json
from patch_v99t_trim import remove_comp

NAME = 'The 17 Sustainable Development Goals: where carbon projects claim them'
MARK = 'function stageBlock'
EXTRA_CSS = """
.sg{border-top:1px solid #e3e6dc;padding:12px 16px 14px;background:#fff}
.sg h4{margin:0 0 8px;font:700 10.5px 'Geist Mono',ui-monospace,Menlo,monospace;letter-spacing:.09em;color:#333}
.sg h4 span{font:500 11px Geist,Arial,sans-serif;letter-spacing:0;color:#888;margin-left:8px}
.sg .sb{display:flex;height:14px;border-radius:7px;overflow:hidden;background:#eef0ea}.sg .sb b{display:block;height:100%}
.sg .lg{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:10px}
.sg .lg div{font-size:11px;color:#666;line-height:1.25}.sg .lg i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.sg .lg b{display:block;font:700 15px 'Geist Mono',ui-monospace,Menlo,monospace;color:#1b1b1b;margin-top:3px}.sg .lg small{font:500 11px Geist,Arial,sans-serif;color:#8a9080;margin-left:4px}
.sg .ft{margin-top:9px;font-size:11px;color:#777;line-height:1.5}
@media (max-width:900px){.sg .lg{grid-template-columns:1fr 1fr}}
"""
EXTRA_JS = r"""
var STG=[null,['Credits issued','#265E30'],['Registered, no credits yet','#6B9E4A'],['Listed, pipeline or validation','#C98A1F'],['Stopped (rejected, withdrawn)','#B85829'],['Status not recorded','#B9BDB0']];
function stageBlock(){
  var o={t:0,s:{}};
  pick('ss',SCOPE,function(r){return +r.a===SEL}).forEach(function(r){o.s[r.b]=r;o.t+=r.n});
  if(!o.t)return '';
  var seg=[1,2,3,4,5].map(function(s){var n=o.s[s]?o.s[s].n:0;return '<b style="width:'+(100*n/o.t).toFixed(2)+'%;background:'+STG[s][1]+'" title="'+esc(STG[s][0])+': '+ni(n)+'"></b>'}).join('');
  var lg=[1,2,3,4,5].map(function(s){var n=o.s[s]?o.s[s].n:0;return '<div><i style="background:'+STG[s][1]+'"></i>'+STG[s][0]+'<b>'+ni(n)+'<small>'+pc(n,o.t,0)+'</small></b></div>'}).join('');
  return '<div class="sg"><h4>PROJECT STAGE<span>where the '+ni(o.t)+' projects claiming this goal stand</span></h4><div class="sb">'+seg+'</div><div class="lg">'+lg+'</div>'
   +'<div class="ft">Stage is read from each registry’s own status text. A goal claimed by a project that never reaches issuance delivers nothing yet.</div></div>';
}
"""
OLD_END = "list('TOP COUNTRIES','country'))+'</div></div>';"
NEW_END = "list('TOP COUNTRIES','country'))+'</div>'+stageBlock()+'</div>';"
OLD_TXT = 'Click a goal to see its sectors, registries and countries or states.'
NEW_TXT = 'Click a goal to see its sectors, registries, countries or states, and the stage its projects have reached (issuing credits, registered, listed or stopped).'
H_PX, H_UNITS = 770, 108


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        import patch_v99p_sdg as P
        sl = db.session.query(Slice).filter(Slice.slice_name == NAME).first()
        if sl is None or OLD_END not in P.CONST_JS:
            print('v99zm: chart or template not found')
            return
        p = json.loads(sl.params)
        if MARK not in (p.get('handlebarsTemplate') or '').replace('&#10;', '\n') and MARK not in (p.get('handlebarsTemplate') or ''):
            js = EXTRA_JS + P.CONST_JS.replace(OLD_END, NEW_END)
            p['handlebarsTemplate'] = P.frame(NAME, P.CONST_CSS + EXTRA_CSS, js, H_PX)
            sl.params = json.dumps(p)
            sl.query_context = None
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            n = 0
            for row in ('ROW-sdg-stage-m', 'ROW-sdg-stage-c'):
                if row in pos:
                    for c in list(pos[row].get('children') or []):
                        pos.pop(c, None)
                    pos[row]['children'] = []
                    n += remove_comp(pos, row)
            if 'CHART-sdg-const' in pos:
                pos['CHART-sdg-const']['meta']['height'] = H_UNITS
            m = pos.get('MARKDOWN-sdg-const')
            if m and OLD_TXT in m['meta'].get('code', ''):
                m['meta']['code'] = m['meta']['code'].replace(OLD_TXT, NEW_TXT)
            used = {v['meta'].get('chartId') for v in pos.values() if isinstance(v, dict) and v.get('type') == 'CHART'}
            d.position_json = json.dumps(pos)
            d.slices = [s for s in d.slices if s.id in used]
            print('v99zm: stage strip added to the 17-goals chart; stage chart rows removed', n)
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zm: skipped:', exc)
