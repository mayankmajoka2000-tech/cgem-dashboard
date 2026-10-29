"""C-GEM v51 update for the online site: removes the live futures chart, Pipeline indicators, Buyer demand
and both waiting-time charts, and the word "story" from the card hint."""
import json

from superset.app import create_app

DROP_CHARTS = {'Pipeline indicators', 'Buyer demand', 'Waiting time to first credits: India vs the rest',
               'Waiting time to first credits, by registry'}
DROP_MD = ('Live chart: voluntary offset futures', 'TradingView chart widget')
HINT_OLD = 'Point at a card for the definition, analyst reading and story'
HINT_NEW = 'Point at a card for the definition and analyst reading'

app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard
    for sl in db.session.query(Slice).all():
        if sl.params and HINT_OLD in sl.params:
            sl.params = sl.params.replace(HINT_OLD, HINT_NEW)
    for dash in db.session.query(Dashboard).all():
        if not dash.position_json:
            continue
        pos = json.loads(dash.position_json)
        names = {s.id: s.slice_name for s in db.session.query(Slice).all()}
        uuids = {str(s.uuid): s.slice_name for s in db.session.query(Slice).all()}
        gone = set()
        for k, v in pos.items():
            if not isinstance(v, dict):
                continue
            meta = v.get('meta') or {}
            nm = meta.get('sliceName') or names.get(meta.get('chartId')) or uuids.get(str(meta.get('uuid')))
            if v.get('type') == 'CHART' and nm in DROP_CHARTS:
                gone.add(k)
            if v.get('type') == 'MARKDOWN' and any(t in (meta.get('code') or '') for t in DROP_MD):
                gone.add(k)
        changed = True
        while changed:   # remove the components, then any row left empty
            changed = False
            for k, v in list(pos.items()):
                if not isinstance(v, dict) or k in gone:
                    continue
                kids = v.get('children')
                if kids is None:
                    continue
                new = [c for c in kids if c not in gone]
                if new != kids:
                    v['children'] = new
                    changed = True
                if v.get('type') == 'ROW' and not v['children']:
                    gone.add(k)
                    changed = True
        for k in gone:
            pos.pop(k, None)
        dash.position_json = json.dumps(pos)
        dash.slices = [s for s in dash.slices if s.slice_name not in DROP_CHARTS]
    db.session.commit()
    print('v51 patch: removed', len(gone), 'layout items')
