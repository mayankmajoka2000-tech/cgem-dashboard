"""v99za: Overview headline strip: five matching cards in the same style."""
import json

NAME = 'One consolidated view of the global carbon market'
C = 'cgx1e3408fa'
TPL = ('<div class="' + C + '"><div class="mk">{{#each data}}<div class="kg">'
       '<div class="kc a1"><h4>Unique project records</h4><b>{{p}}</b><p>Distinct projects across all the registries in the dataset.</p></div>'
       '<div class="kc a2"><h4>Registries covered</h4><b>{{r}}</b><p>Registries and crediting schemes that list at least one project.</p></div>'
       '<div class="kc a3"><h4>Host countries</h4><b>{{c}}</b><p>Countries that host at least one carbon project.</p></div>'
       '<div class="kc a4"><h4>Credits issued</h4><b>{{i}}</b><p>Credits a registry has actually created for a project after its results were verified.</p></div>'
       '<div class="kc a5"><h4>Credits retired (used)</h4><b>{{t}}</b><p>Credits permanently cancelled in the registry so that their owner can claim the reduction; they can never be resold.</p></div>'
       '</div>{{/each}}</div></div>')
CSS = """
.cgx1e3408fa .mk{font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;color:#1b1b1b;padding:2px}
.cgx1e3408fa .kg{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:stretch}
.cgx1e3408fa .kc{--a:#3F6A1C;--b:#9CC46A;position:relative;overflow:hidden;background:#fff;border:1px solid #e3e6dc;border-radius:14px;padding:18px 16px 14px;box-shadow:0 1px 2px rgba(31,42,20,.05);transition:transform .15s,box-shadow .15s}
.cgx1e3408fa .kc:hover{transform:translateY(-2px);box-shadow:0 10px 22px -10px rgba(31,42,20,.35)}
.cgx1e3408fa .kc:before{content:'';position:absolute;left:0;top:0;right:0;height:4px;background:linear-gradient(90deg,var(--a),var(--b))}
.cgx1e3408fa .kc:after{content:'';position:absolute;right:-30px;bottom:-40px;width:110px;height:110px;border-radius:50%;background:var(--a);opacity:.07}
.cgx1e3408fa .kc h4{margin:0 0 6px;font-size:11.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#5a6152}
.cgx1e3408fa .kc b{display:block;font-size:32px;line-height:1.1;font-weight:700;letter-spacing:-.5px;color:var(--a)}
.cgx1e3408fa .kc p{position:relative;z-index:1;margin:8px 0 0;font-size:11.5px;line-height:1.4;color:#5f6659}
.cgx1e3408fa .a1{--a:#2F6B1E;--b:#9CC46A}
.cgx1e3408fa .a2{--a:#245a78;--b:#6FA8C8}
.cgx1e3408fa .a3{--a:#0E7C86;--b:#6CC3C9}
.cgx1e3408fa .a4{--a:#8C3B1F;--b:#D9A441}
.cgx1e3408fa .a5{--a:#9A6A12;--b:#E7C46B}
@media (max-width:1100px){.cgx1e3408fa .kg{grid-template-columns:repeat(2,1fr)}}
"""
UNITS = 22


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        sl = db.session.query(Slice).filter(Slice.slice_name == NAME).first()
        if sl is None:
            print('v99za: chart not found')
            return
        p = json.loads(sl.params)
        if C not in p.get('handlebarsTemplate', ''):
            print('v99za: unexpected template, skipped')
            return
        p['handlebarsTemplate'] = TPL
        p['styleTemplate'] = CSS
        sl.params = json.dumps(p)
        sl.query_context = None
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            for v in pos.values():
                if isinstance(v, dict) and v.get('type') == 'CHART' and (v.get('meta') or {}).get('chartId') == sl.id:
                    v['meta']['height'] = UNITS
            d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99za: overview cards restyled')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99za: skipped:', exc)
