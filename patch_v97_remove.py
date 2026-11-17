"""C-GEM v97 online site only: removes some charts (and their intro text) from the website copy of the dashboard.
The registry tracker tables (change log, run log, sources) and a few overview charts are not shown online."""
import json
DROP_ROWS = {
    'TAB-0': ['ROW-0-8', 'ROW-0-9', 'ROW-0-10', 'ROW-0-11'],   # countries bubble chart, vintage/sector chart (with intros)
    'TAB-1': ['ROW-1-7', 'ROW-1-8', 'ROW-1-9'],                # top 15 states + sector list, states bubble chart (with intro)
    'TAB-2': ['ROW-2-18', 'ROW-2-19', 'ROW-2-20', 'ROW-2-21'],  # registry tracker tables
}
from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.dashboard import Dashboard
    for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
        pos = json.loads(d.position_json)
        gone = 0
        for tab, rows in DROP_ROWS.items():
            for r in rows:
                node = pos.get(r)
                if not node:
                    print('not found:', r)
                    continue
                for c in node.get('children', []):
                    pos.pop(c, None)
                pos.pop(r, None)
                if r in pos.get(tab, {}).get('children', []):
                    pos[tab]['children'].remove(r)
                gone += 1
        d.position_json = json.dumps(pos)
        db.session.commit()
        print('v97: rows removed from the online dashboard:', gone)
