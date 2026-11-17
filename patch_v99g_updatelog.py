"""C-GEM v99g online site: the "Registry update log" block (heading text + status chart, slice 27) moves from the Registry tab to the end of the Overview tab."""
import json

ROWS = ['ROW-2-16', 'ROW-2-17']  # heading markdown, status chart
SRC, DST = 'TAB-2', 'TAB-0'


def move(pos):
    if DST not in pos or SRC not in pos or any(r not in pos for r in ROWS):
        return False
    if any(r in pos[DST]['children'] for r in ROWS):
        return False
    for r in ROWS:
        pos[SRC]['children'].remove(r)
        pos[DST]['children'].append(r)
        for k, v in pos.items():
            if isinstance(v, dict) and v.get('parents') and r in v['parents'] or k == r:
                v['parents'] = [DST if x == SRC else x for x in v['parents']]
    return True


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        n = 0
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            if move(pos):
                d.position_json = json.dumps(pos)
                n += 1
        db.session.commit()
        print('v99g: registry update log moved to Overview:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for a layout tweak
        import traceback
        traceback.print_exc()
        print('v99g: skipped:', exc)
