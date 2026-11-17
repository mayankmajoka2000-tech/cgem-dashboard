"""C-GEM v99n online site: the compliance "Carbon Prices" tab (carbon taxes and emissions trading systems) is removed from the dashboard,
leaving the voluntary prices on the "Live Prices" tab."""
import json

TAB = 'TAB-4'


def drop_tab(pos):
    if TAB not in pos or pos[TAB].get('meta', {}).get('text') != 'Carbon Prices':
        return set()
    charts = set()

    def walk(k):
        v = pos.pop(k, None)
        if not v:
            return
        if v.get('type') == 'CHART':
            charts.add(v['meta']['chartId'])
        for c in v.get('children') or []:
            walk(c)

    for k, v in pos.items():
        if isinstance(v, dict) and TAB in (v.get('children') or []):
            v['children'].remove(TAB)
            break
    walk(TAB)
    return charts


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        n = 0
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            gone = drop_tab(pos)
            if gone:
                d.position_json = json.dumps(pos)
                d.slices = [s for s in d.slices if s.id not in gone]
                n += 1
        db.session.commit()
        print('v99n: Carbon Prices tab removed:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for a layout tweak
        import traceback
        traceback.print_exc()
        print('v99n: skipped:', exc)
