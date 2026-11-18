"""v99zc: SDG matrix header shows only the official UN SDG icon (no generic green tile, no duplicate small icon)."""
import json

NAME = 'SDGs claimed by projects, by sector (number of projects)'
C = 'cgx395072d5'
MARK = '/* v99zc */'


def css():
    s = MARK + '\n'
    for n in range(1, 18):
        s += ('.%s .sm th .sg%d{background-image:url(https://sdgs.un.org/sites/default/files/goals/E_SDG_Icons-%02d.jpg)!important;'
              'background-size:cover!important;background-color:transparent!important;width:46px;height:46px;border-radius:6px}\n' % (C, n, n))
    s += '.%s .sm th .sn img{display:none!important}\n' % C
    return s


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        sl = db.session.query(Slice).filter(Slice.slice_name == NAME).first()
        if sl is None:
            print('v99zc: chart not found')
            return
        p = json.loads(sl.params)
        st = p.get('styleTemplate') or ''
        if MARK in st or C not in st:
            print('v99zc: already done or unexpected css')
            return
        p['styleTemplate'] = st + '\n' + css()
        sl.params = json.dumps(p)
        sl.query_context = None
        db.session.commit()
        print('v99zc: SDG matrix icons are UN logos only')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zc: skipped:', exc)
