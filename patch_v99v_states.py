"""v99v: 'States and union territories ranked by credits issued' loses its vintage columns, shows the top 5 rows and scrolls for the rest."""
import json
import re
import html as H

OLD_NAME = 'States and union territories ranked by credits issued, with retirement and vintage'
NEW_NAME = 'States and union territories ranked by credits issued, with retirement'
FRAME_PX = 440
UNITS = 66


def LOG(*a):
    msg = ' '.join(str(x) for x in a)
    print(msg)
    try:
        import os
        os.makedirs('/app/cgem/chat', exist_ok=True)
        with open('/app/cgem/chat/v99v.log', 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def edit(doc):
    log = []

    def sub(label, pat, rep, flags=0):
        nonlocal doc
        new, n = re.subn(pat, lambda m: rep, doc, count=1, flags=flags)
        log.append((label, n))
        doc = new
    sub('kpgrid', r'grid-template-columns:repeat\(5,1fr\)', 'grid-template-columns:repeat(3,1fr)')
    sub('wrap', r'max-height:calc\(100vh - 160px\)', 'max-height:290px')
    sub('kpis', r"\],\s*\['Vintage credits',num\(T\.v\).*?\]\]\.map\(", ']].map(', re.S)
    sub('legend', r'<span><i style="background:#D9A441"></i>Vintage credits</span><span><i style="background:linear-gradient\(90deg,#B5651D,#7FAE4E\)"></i>Vintage range, mark = average</span>', '')
    sub('cols', r",\['v','Vintage credits'\],\['o','Vintage range \('\+Y0\+' to '\+Y1\+'\)'\],\['a','Average vintage'\]\];", '];')
    sub('cells', r"\+\s*'<td><div class=mb><span class=v>'\+num\(x\.v\).*?'</td></tr>';", "+'</tr>';", re.S)
    sub('colspan', r'colspan=7', 'colspan=4')
    return doc, log


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        sl = db.session.query(Slice).filter(Slice.slice_name.like('States and union territories ranked by credits issued%')).first()
        LOG('found', sl and sl.id, sl and sl.slice_name)
        if sl is None:
            LOG('chart not found')
            return
        p = json.loads(sl.params)
        t = p['handlebarsTemplate']
        m = re.search(r'srcdoc="(.*?)" style="[^"]*"', t, re.S)
        LOG('srcdoc match', bool(m))
        doc = H.unescape(m.group(1))
        doc2, log = edit(doc)
        LOG('edit log', log, 'doc len', len(doc), 'tpl len', len(t))
        if any(n != 1 for _, n in log):
            LOG('piece did not match')
            return
        attr = H.escape(doc2, quote=True).replace('\n', '&#10;')
        t2 = t[:m.start()] + 'srcdoc="' + attr + '" style="width:100%;height:' + str(FRAME_PX) + 'px;border:0;display:block"' + t[m.end():]
        p['handlebarsTemplate'] = t2
        sl.params = json.dumps(p)
        sl.slice_name = NEW_NAME
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            for v in pos.values():
                if isinstance(v, dict) and v.get('type') == 'CHART' and (v.get('meta') or {}).get('chartId') == sl.id:
                    v['meta']['height'] = UNITS
                    v['meta']['sliceName'] = NEW_NAME
            d.position_json = json.dumps(pos)
        db.session.commit()
        LOG('done')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        import io
        LOG(traceback.format_exc())
        LOG('skipped', repr(exc))
