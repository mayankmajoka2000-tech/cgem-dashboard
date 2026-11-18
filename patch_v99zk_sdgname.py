"""v99zk: SDG tab renamed 'SDG and socio-economic co-benefits'; its heading and introduction rewritten."""
import json
from patch_v99ze_sdgtext import need_units

TAB = 'SDG and socio-economic co-benefits'
TITLE = 'Beyond the Tonne: SDG and Social Claims'
BODY = ('Every carbon credit represents one tonne of CO₂e avoided or removed, but many projects also claim benefits for people and places, '
        'such as clean energy, better health, jobs, gender equality, water and land. This tab maps which of the 17 UN Sustainable Development Goals '
        'projects claim, by sector and geography. It then tests whether the market rewards those claims: are credits from projects with social '
        'co-benefits or labels retired at higher rates?')
CODE = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:12px 6px 4px\"><div style=\"font-size:15px;font-weight:700;color:#2C7A3D;margin-bottom:10px;\">"
        + TITLE + "</div><p style=\"margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify\">" + BODY + "</p></div>")


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            if 'TAB-sdg' in pos:
                pos['TAB-sdg']['meta']['text'] = TAB
                pos['TAB-sdg']['meta']['defaultText'] = TAB
            m = pos.get('MARKDOWN-sdg-intro')
            if m:
                m['meta']['code'] = CODE
                m['meta']['height'] = max(m['meta'].get('height', 0), need_units(CODE))
            d.position_json = json.dumps(pos)
            print('v99zk: SDG tab renamed', bool(m))
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zk: skipped:', exc)
