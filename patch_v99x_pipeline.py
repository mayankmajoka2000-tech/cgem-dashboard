"""v99x: project pipeline tab: a proper hero strip for the headline numbers, and chart frames trimmed to their content."""
import json
import re

KPI = 'The project pipeline in two numbers'
C = 'cgxhero'
CSS = """
.cgxhero .hg{display:grid;grid-template-columns:1.35fr 1.35fr 1fr 1fr 1fr;gap:14px;font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:2px}
.cgxhero .hc{position:relative;overflow:hidden;border-radius:14px;padding:18px 18px 15px;background:#fff;border:1px solid #e3e6dc;box-shadow:0 1px 2px rgba(31,42,20,.05);transition:transform .15s,box-shadow .15s}
.cgxhero .hc:hover{transform:translateY(-2px);box-shadow:0 10px 22px -10px rgba(31,42,20,.35)}
.cgxhero .hc:before{content:'';position:absolute;left:0;top:0;right:0;height:4px;background:linear-gradient(90deg,#3F6A1C,#9CC46A)}
.cgxhero .hc b{display:block;font-size:30px;line-height:1.1;color:#173F0F;font-weight:700;letter-spacing:-.5px}
.cgxhero .hc span{display:block;margin-top:7px;font-size:12.5px;line-height:1.3;color:#5a6152}
.cgxhero .h1,.cgxhero .h2{border:none;color:#fff}
.cgxhero .h1{background:linear-gradient(135deg,#173F0F 0%,#2F6B1E 62%,#4E8A2E 100%)}
.cgxhero .h2{background:linear-gradient(135deg,#8C3B1F 0%,#B5651D 58%,#D9A441 100%)}
.cgxhero .h1:before,.cgxhero .h2:before{background:rgba(255,255,255,.35)}
.cgxhero .h1:after,.cgxhero .h2:after{content:'';position:absolute;right:-34px;bottom:-44px;width:130px;height:130px;border-radius:50%;background:rgba(255,255,255,.10)}
.cgxhero .h1 b,.cgxhero .h2 b{color:#fff;font-size:38px}
.cgxhero .h1 span,.cgxhero .h2 span{color:rgba(255,255,255,.86);font-weight:600}
.cgxhero .h3:before{background:linear-gradient(90deg,#3F6A1C,#9CC46A)}
.cgxhero .h4:before{background:linear-gradient(90deg,#D9A441,#B5651D)}
.cgxhero .h5:before{background:linear-gradient(90deg,#245a78,#6FA8C8)}
@media (max-width:1000px){.cgxhero .hg{grid-template-columns:1fr 1fr}.cgxhero .h1 b,.cgxhero .h2 b{font-size:30px}}
"""
TPL = ('<div class="cgxhero">{{#each data}}<div class="hg">'
       '<div class="hc h1"><b>{{a}}</b><span>Total projects in the pipeline</span></div>'
       '<div class="hc h2"><b>{{d}}</b><span>Expected annual emission reductions</span></div>'
       '<div class="hc h3"><b>{{e}}</b><span>Countries with projects</span></div>'
       '<div class="hc h4"><b>{{f}}</b><span>Sectors covered</span></div>'
       '<div class="hc h5"><b>{{g}}</b><span>Share of projects located in India</span></div>'
       '</div>{{/each}}</div>')
HEIGHTS = {63: 56, 48: 48, 29: 48, 28: 50, 15: 50}
KPI_UNITS = 15


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        sl = db.session.query(Slice).filter(Slice.slice_name == KPI).first()
        if sl is None:
            print('v99x: KPI chart not found')
            return
        p = json.loads(sl.params)
        ms = p.get('metrics') or []
        byl = {m.get('label'): m for m in ms if isinstance(m, dict)}
        if 'a' not in byl or 'd' not in byl:
            print('v99x: unexpected metrics')
            return

        def m(label, sql):
            return {'expressionType': 'SQL', 'sqlExpression': sql, 'label': label}
        new = [byl['a'], byl['d'],
               m('e', "printf('%d', COUNT(DISTINCT CASE WHEN country IS NOT NULL AND country NOT IN ('Not recorded','Multiple Locations','International') THEN country END))"),
               m('f', "printf('%d', COUNT(DISTINCT CASE WHEN sector IS NOT NULL AND sector NOT IN ('Not classified','Not recorded') THEN sector END))"),
               m('g', "printf('%.0f%%', 100.0 * COUNT(DISTINCT CASE WHEN country = 'India' THEN project_key END) / MAX(1, COUNT(DISTINCT project_key)))")]
        p['metrics'] = new
        p['handlebarsTemplate'] = TPL
        p['styleTemplate'] = CSS
        sl.params = json.dumps(p)
        sl.query_context = None
        sl.slice_name = 'The project pipeline at a glance'
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            for v in pos.values():
                if isinstance(v, dict) and v.get('type') == 'CHART':
                    meta = v.get('meta') or {}
                    cid = meta.get('chartId')
                    if cid == sl.id:
                        meta['height'] = KPI_UNITS
                    elif cid in HEIGHTS:
                        meta['height'] = HEIGHTS[cid]
            d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99x: pipeline hero done')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99x: skipped:', exc)
