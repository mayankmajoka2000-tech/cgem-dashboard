"""v99ze: SDG tab: intro/heading text blocks get enough height so no sentence is cut off (only ever taller)."""
import json
import math
import re


def need_units(code):
    txt = re.sub(r'<[^>]+>', ' ', code)
    n = len(re.sub(r'\s+', ' ', txt).strip())
    lines = math.ceil(n / 125.0)          # conservative: ~125 characters a line on a laptop screen
    px = 12 + 30 + lines * 23 + 16
    return int(math.ceil((px + 16) / 8.0))


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            n = 0
            for k, v in pos.items():
                if k.startswith('MARKDOWN-sdg-') and isinstance(v, dict):
                    h = need_units(v['meta'].get('code', ''))
                    if h > v['meta'].get('height', 0):
                        v['meta']['height'] = h
                        n += 1
            d.position_json = json.dumps(pos)
            print('v99ze: SDG text blocks made taller:', n)
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99ze: skipped:', exc)
