"""v99t: pipeline tab trim.
- vintage block (text + 'Vintage at a glance' strip) comes off
- 'The project pipeline in four numbers' keeps only total projects and expected annual reductions
- 'When do crediting periods end?' chart and its text come off"""
import json
import re

NAME_KPI = 'The project pipeline in four numbers'
NAME_END = 'When do crediting periods end? Projects per 5-year period, by sector'
NAME_VST = 'Vintage at a glance'


def remove_comp(pos, comp):
    """take a component out of every parent; drop rows left empty"""
    if comp not in pos:
        return False
    for k in [k for k, v in pos.items() if isinstance(v, dict) and comp in (v.get('children') or [])]:
        pos[k]['children'].remove(comp)
        if not pos[k]['children'] and k.startswith('ROW-'):
            remove_comp(pos, k)
            pos.pop(k, None)
    pos.pop(comp, None)
    return True


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        gone_ids = set()
        for nm in (NAME_END, NAME_VST):
            for sl in db.session.query(Slice).filter(Slice.slice_name == nm).all():
                gone_ids.add(sl.id)
        kpi = db.session.query(Slice).filter(Slice.slice_name == NAME_KPI).first()
        if kpi is not None:
            p = json.loads(kpi.params)
            t = p.get('handlebarsTemplate', '')
            t2 = re.sub(r'<div class="kb kq"><b>\{\{b\}\}</b><span>Projects with credit issuance</span></div>', '', t)
            t2 = re.sub(r'<div class="kb kq"><b>\{\{c\}\}</b><span>Total credits issued</span></div>', '', t2)
            t2 = t2.replace('--n:4', '--n:2')
            if t2 != t:
                p['handlebarsTemplate'] = t2
                kpi.params = json.dumps(p)
                kpi.slice_name = 'The project pipeline in two numbers'
                print('v99t: pipeline KPIs trimmed')
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            n = 0
            for k, v in list(pos.items()):
                if not isinstance(v, dict):
                    continue
                m = v.get('meta') or {}
                if v.get('type') == 'CHART' and m.get('chartId') in gone_ids:
                    n += remove_comp(pos, k)
                elif v.get('type') == 'MARKDOWN':
                    code = m.get('code') or ''
                    if 'Vintage year: When did the emission' in code or 'Project timelines: When are projects' in code:
                        n += remove_comp(pos, k)
            d.position_json = json.dumps(pos)
            d.slices = [s for s in d.slices if s.id not in gone_ids]
            print('v99t: removed components', n)
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99t: skipped:', exc)
