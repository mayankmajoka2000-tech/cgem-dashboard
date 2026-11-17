"""C-GEM v99o online site: "Credits issued by vintage year: India and the rest of the world" (slice 59) and
"Vintage map: credits issued by sector and vintage year" (slice 72) come off the dashboard."""
import json

GONE = {'CHART-pl_vbubble': 59, 'CHART-vint_dna': 72}


def drop(pos):
    ids = set()
    for comp, cid in GONE.items():
        if comp not in pos:
            continue
        row = next((k for k, v in pos.items() if isinstance(v, dict) and comp in (v.get('children') or [])), None)
        del pos[comp]
        ids.add(cid)
        if row:
            pos[row]['children'].remove(comp)
            if not pos[row]['children']:
                par = next((k for k, v in pos.items() if isinstance(v, dict) and row in (v.get('children') or [])), None)
                if par:
                    pos[par]['children'].remove(row)
                del pos[row]
    return ids


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        n = 0
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            gone = drop(pos)
            if gone:
                d.position_json = json.dumps(pos)
                d.slices = [s for s in d.slices if s.id not in gone]
                n += 1
        db.session.commit()
        print('v99o: vintage charts removed:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for a layout tweak
        import traceback
        traceback.print_exc()
        print('v99o: skipped:', exc)
