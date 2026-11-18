"""v99zl: SDG tab: four charts and their headings come off (goals progress, sector heat map, who gets projects, state gap)."""
import json
from patch_v99t_trim import remove_comp

ROWS = [f"ROW-sdg-{k}-{s}" for k in ("prog", "heat", "who", "opp") for s in ("m", "c")]


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            n = 0
            for row in ROWS:
                if row not in pos:
                    continue
                for c in list(pos[row].get('children') or []):
                    pos.pop(c, None)
                pos[row]['children'] = []
                n += remove_comp(pos, row)
            used = {v['meta'].get('chartId') for v in pos.values() if isinstance(v, dict) and v.get('type') == 'CHART'}
            d.position_json = json.dumps(pos)
            d.slices = [s for s in d.slices if s.id in used]
            print('v99zl: SDG tab: 4 charts removed', n)
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zl: skipped:', exc)
