"""C-GEM v98 online site only: a separate CCTS tab in the dashboard (after INDIA MARKET ATLAS).
The compliance market charts move there from the India tab, with a button to the full list at /cgem-projects/ccts."""
import json
MOVE = ['ROW-1-14', 'ROW-1-15', 'ROW-1-16', 'ROW-1-17', 'ROW-1-18']
NEW = 'TAB-ccts'
BTN = ('<div style="font-family:Geist,Inter,\'Segoe UI\',Arial,sans-serif;padding:6px 6px 2px"><a href="/cgem-projects/ccts" target="_blank" '
       'style="display:inline-block;padding:9px 16px;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;background:#2C7A3D;color:#fff">'
       'Open the full CCTS list: search, filter and download</a></div>')
from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.dashboard import Dashboard
    for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
        pos = json.loads(d.position_json)
        if NEW in pos or not all(r in pos for r in MOVE) or 'TAB-1' not in pos:
            print('v98: CCTS tab not added (already there or layout different)')
            continue
        path = ['ROOT_ID', 'GRID_ID', 'TABS-main', NEW]
        pos[NEW] = {'children': [], 'id': NEW, 'meta': {'defaultText': 'CCTS', 'text': 'CCTS'}, 'parents': path[:3], 'type': 'TAB'}
        pos['ROW-ccts-btn'] = {'children': ['MARKDOWN-ccts-btn'], 'id': 'ROW-ccts-btn', 'meta': {'background': 'BACKGROUND_TRANSPARENT'},
                               'parents': path, 'type': 'ROW'}
        pos['MARKDOWN-ccts-btn'] = {'children': [], 'id': 'MARKDOWN-ccts-btn', 'meta': {'code': BTN, 'height': 12, 'width': 12},
                                    'parents': path + ['ROW-ccts-btn'], 'type': 'MARKDOWN'}
        rows = []
        for r in MOVE:
            pos['TAB-1']['children'].remove(r)
            pos[r]['parents'] = path
            for c in pos[r]['children']:
                pos[c]['parents'] = path + [r]
            rows.append(r)
        # heading first, then the button, then the charts
        pos[NEW]['children'] = [MOVE[0], 'ROW-ccts-btn'] + MOVE[1:]
        tabs = pos['TABS-main']['children']
        tabs.insert(tabs.index('TAB-1') + 1, NEW)
        d.position_json = json.dumps(pos)
        # the dashboard's tab settings list the tabs too
        try:
            meta = json.loads(d.json_metadata or '{}')
            d.json_metadata = json.dumps(meta)
        except Exception:
            pass
        db.session.commit()
        print('v98: CCTS tab added with', len(MOVE), 'rows moved')
