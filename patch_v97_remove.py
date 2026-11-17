"""C-GEM v97 online site only: removes some charts (and their intro text) from the website copy of the dashboard.
The registry tracker tables (change log, run log, sources) and a few overview charts are not shown online."""
import json
DROP_ROWS = {
    'TAB-0': ['ROW-0-8', 'ROW-0-9', 'ROW-0-10', 'ROW-0-11'],   # countries bubble chart, vintage/sector chart (with intros)
    'TAB-1': ['ROW-1-7', 'ROW-1-8', 'ROW-1-9'],                # top 15 states + sector list, states bubble chart (with intro)
    'TAB-2': ['ROW-2-18', 'ROW-2-19', 'ROW-2-20', 'ROW-2-21'],  # registry tracker tables
}
DROP_CHARTS = {
    'Credits issued by vintage period and sector', 'Every registry tracker run (newest first)',
    'Registry sources: which ones the tracker can read', 'Indian projects by sector',
    'Do more projects mean more credits? Indian states and union territories',
    'Every registry tracker run, by source (newest first)', 'Every change the tracker made (newest first)',
    'Top 15 states by number of projects: credits issued and retired', 'Do more projects mean more credits? Countries',
}   # charts that are still linked to the dashboard are added back at the bottom of the page, so they are unlinked too
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
        before = len(d.slices)
        d.slices = [sl for sl in d.slices if sl.slice_name not in DROP_CHARTS]
        print('charts unlinked from the dashboard:', before - len(d.slices))
        db.session.commit()
        print('v97: rows removed from the online dashboard:', gone)
