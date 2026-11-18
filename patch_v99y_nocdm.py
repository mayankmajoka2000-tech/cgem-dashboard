"""v99y: Registry & Market tab: the CDM card (and its selector pill) comes off 'Registry intelligence: the leading registries side by side'."""
import json
import re
import html as H

NAME = 'Registry intelligence: the leading registries side by side'


def LOG(msg):
    print('v99y:', msg)
    try:
        import os
        os.makedirs('/app/cgem/chat', exist_ok=True)
        with open('/app/cgem/chat/v99y.log', 'a', encoding='utf-8') as f:
            f.write(str(msg) + '\n')
    except Exception:
        pass


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        sl = db.session.query(Slice).filter(Slice.slice_name == NAME).first()
        if sl is None:
            LOG('chart not found')
            return
        p = json.loads(sl.params)
        t = p['handlebarsTemplate']
        m = re.search(r'srcdoc="(.*?)" style="[^"]*"', t, re.S)
        if not m:
            LOG('srcdoc not found')
            return
        doc = H.unescape(m.group(1))
        doc2, n = re.subn(r"\{k:'Clean Development Mechanism \(UNFCCC\)'.*?(?=\{k:'Verified Carbon Standard')", '', doc, count=1, flags=re.S)
        LOG('removed entries: %d' % n)
        if n != 1:
            return
        attr = H.escape(doc2, quote=True).replace('\n', '&#10;')
        p['handlebarsTemplate'] = t[:m.start(1)] + attr + t[m.end(1):]
        sl.params = json.dumps(p)
        sl.query_context = None
        db.session.commit()
        LOG('done')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        LOG(traceback.format_exc())
