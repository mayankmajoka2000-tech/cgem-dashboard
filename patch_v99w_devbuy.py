"""v99w: India tab: 'Top 10 project developers in India' and 'Top 10 buyers of Indian credits' sit side by side; top 5 visible, the rest scrolls."""
import json
import re

DEV = 'Top 10 project developers in India'
BUY = 'Top 10 buyers of Indian credits'
SCROLL = '.%s .tt{max-height:300px;overflow-y:auto;padding-right:4px}.%s .tt::-webkit-scrollbar{width:6px}.%s .tt::-webkit-scrollbar-thumb{background:#c9d2bb;border-radius:3px}'
UNITS = 50


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        ids = {}
        for nm in (DEV, BUY):
            sl = db.session.query(Slice).filter(Slice.slice_name == nm).first()
            if sl is None:
                print('v99w: missing', nm)
                return
            p = json.loads(sl.params)
            m = re.search(r'class="(cgx[0-9a-f]+)"', p.get('handlebarsTemplate', ''))
            if not m:
                print('v99w: no class for', nm)
                return
            c = m.group(1)
            st = p.get('styleTemplate') or ''
            if 'max-height:300px' not in st:
                p['styleTemplate'] = st + '\n' + (SCROLL % (c, c, c))
                sl.params = json.dumps(p)
            ids[nm] = sl.id
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            need = ['TAB-1', 'ROW-1-devh', 'ROW-1-devc', 'ROW-1-buyh', 'ROW-1-buyc', 'CHART-dev_in', 'CHART-buy_in', 'MARKDOWN-1-dev-0', 'MARKDOWN-1-buy-0']
            if any(k not in pos for k in need):
                print('v99w: layout differs, skipped')
                continue
            dev_par = list(pos['CHART-dev_in'].get('parents') or [])
            md_par = list(pos['MARKDOWN-1-dev-0'].get('parents') or [])
            pos['ROW-1-devh']['children'] = ['MARKDOWN-1-dev-0', 'MARKDOWN-1-buy-0']
            pos['ROW-1-devc']['children'] = ['CHART-dev_in', 'CHART-buy_in']
            for k, par in (('MARKDOWN-1-dev-0', md_par), ('MARKDOWN-1-buy-0', md_par), ('CHART-dev_in', dev_par), ('CHART-buy_in', dev_par)):
                pos[k]['parents'] = par
                pos[k]['meta']['width'] = 6
                if k.startswith('MARKDOWN'):
                    pos[k]['meta']['height'] = 20
                else:
                    pos[k]['meta']['height'] = UNITS
            tab = pos['TAB-1']['children']
            for r in ('ROW-1-buyh', 'ROW-1-buyc'):
                if r in tab:
                    tab.remove(r)
                pos.pop(r, None)
            d.position_json = json.dumps(pos)
            print('v99w: developers and buyers side by side')
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99w: skipped:', exc)
