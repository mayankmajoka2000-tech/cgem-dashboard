"""v99zi: Overview: an 'About this dashboard' block directly under the banner."""
import json

TITLE = 'About this dashboard'
BODY = ('This dashboard draws on C-GEM’s database of voluntary carbon market projects from the major registries. '
        'It tracks where projects are located, which sectors and methodologies they use, how many credits they have issued, '
        'and how many of those credits have been retired. Policymakers, practitioners, grower organisations, researchers and academicians '
        'can use it to see how the market is actually working on the ground.')
CODE = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:12px 6px 4px\"><div style=\"font-size:15px;font-weight:700;color:#2C7A3D;margin-bottom:10px;\">"
        + TITLE + "</div><p style=\"margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify\">" + BODY + "</p></div>")
MID, RID = 'MARKDOWN-ov-about', 'ROW-ov-about'


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            if MID in pos or 'TAB-0' not in pos:
                print('v99zi: skipped (already there or layout differs)')
                continue
            kids = pos['TAB-0']['children']
            base = list(pos['TAB-0']['parents']) + ['TAB-0']
            at = 1
            for i, r in enumerate(kids):
                if 'MARKDOWN-0-0-0' in (pos.get(r, {}).get('children') or []):
                    at = i + 1
            pos[MID] = {'children': [], 'id': MID, 'meta': {'code': CODE, 'height': 14, 'width': 12}, 'parents': base + [RID], 'type': 'MARKDOWN'}
            pos[RID] = {'children': [MID], 'id': RID, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
            kids.insert(at, RID)
            d.position_json = json.dumps(pos)
            print('v99zi: About block added at', at)
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zi: skipped:', exc)
