"""C-GEM v99k online site: the stage chart "Project stage on the registry: 4 main stages" keeps its stage cards but loses the
"In the pipeline: every project" list (search box, status chips, project table, Show more) that opened below them."""
import html as H
import json
import re

NAME = 'Project stage on the registry: 4 main stages'
MARK = 'cgx-nolist'


def strip(t):
    m = re.search(r'srcdoc="(.*?)" style="', t, re.S)
    doc = H.unescape(m.group(1))
    doc = doc.replace('</style></head>', '#panel{display:none!important}.g,.gs{cursor:default}.g:hover{box-shadow:none}.gs:hover{background:none}/*' + MARK + '*/</style></head>', 1)
    doc = doc.replace(' Select a stage to list its projects, then search, filter by registry status or sort.', '')
    doc = doc.replace('h.onclick=function(){pick(h.dataset.k);};', '')
    doc = doc.replace('if(keys.length)pick(keys[0]);', '')
    attr = H.escape(doc, quote=True).replace('\n', '&#10;')
    out = t[:m.start(1)] + attr + t[m.end(1):]
    return re.sub(r'height:\d+px;border:0', 'height:300px;border:0', out)


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        n = 0
        for sl in db.session.query(Slice).filter(Slice.slice_name == NAME).all():
            p = json.loads(sl.params)
            t = p.get('handlebarsTemplate') or ''
            if MARK in H.unescape(t) or 'srcdoc=' not in t:
                continue
            p['handlebarsTemplate'] = strip(t)
            sl.params = json.dumps(p)
            sl.query_context = None
            n += 1
            for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
                pos = json.loads(d.position_json)
                for comp in pos.values():
                    if isinstance(comp, dict) and comp.get('meta', {}).get('chartId') == sl.id:
                        comp['meta']['height'] = 38
                d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99k: stage chart without project list:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tweak
        import traceback
        traceback.print_exc()
        print('v99k: skipped:', exc)
