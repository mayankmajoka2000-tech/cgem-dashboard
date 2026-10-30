"""C-GEM v59 update for the online site: removes the "Supporting data note" from INDIA MARKET ATLAS."""
import json

from superset.app import create_app

app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.dashboard import Dashboard
    for dash in db.session.query(Dashboard).all():
        pos = json.loads(dash.position_json or '{}')
        gone = {k for k, v in pos.items() if isinstance(v, dict) and v.get('type') == 'MARKDOWN'
                and 'Supporting data note' in ((v.get('meta') or {}).get('code') or '')}
        changed = True
        while changed:
            changed = False
            for k, v in list(pos.items()):
                if not isinstance(v, dict) or k in gone or v.get('children') is None:
                    continue
                new = [c for c in v['children'] if c not in gone]
                if new != v['children']:
                    v['children'] = new
                    changed = True
                if v.get('type') == 'ROW' and not v['children']:
                    gone.add(k)
                    changed = True
        for k in gone:
            pos.pop(k, None)
        dash.position_json = json.dumps(pos)
    db.session.commit()
    print('v59 patch: supporting data note removed')
