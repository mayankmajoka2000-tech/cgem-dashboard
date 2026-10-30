"""C-GEM v54 update for the online site: registry counts match on every page (17 named registries)."""
import json

from superset.app import create_app

REG_OLD = 'COUNT(DISTINCT registry)'
REG_NEW = "COUNT(DISTINCT CASE WHEN registry <> 'Unknown registry' THEN registry END)"
KS_OLD = '{{t_n}} projects</div>'
KS_NEW = '{{t_n}} projects with a named registry</div>'
MD_PAIRS = [('across 18 registries and 166 host countries', 'across 17 registries and 166 host countries'),
            ('16,818 project records from 18 registries', '16,818 project records from 17 registries')]


def fix(obj, a, b):
    if isinstance(obj, str):
        return obj.replace(a, b)
    if isinstance(obj, list):
        return [fix(x, a, b) for x in obj]
    if isinstance(obj, dict):
        return {k: fix(v, a, b) for k, v in obj.items()}
    return obj


app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard
    n = 0
    for sl in db.session.query(Slice).all():
        if not sl.params:
            continue
        d = json.loads(sl.params)
        d2 = d
        if sl.slice_name == 'Headline numbers':
            d2 = fix(d2, REG_OLD, REG_NEW)
        if sl.slice_name and sl.slice_name.startswith('Registries: credits issued'):
            d2 = fix(d2, KS_OLD, KS_NEW)
        if sl.slice_name and sl.slice_name.startswith('Sectors: credits issued'):
            d2 = fix(d2, KS_OLD, KS_NEW.replace('registry', 'sector'))
        if d2 != d:
            sl.params = json.dumps(d2)
            n += 1
    for dash in db.session.query(Dashboard).all():
        p = dash.position_json or ''
        for a, b in MD_PAIRS:
            p = p.replace(a, b)
        dash.position_json = p
    db.session.commit()
    print('v54 patch: charts updated', n)
