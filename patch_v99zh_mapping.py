"""v99zh: Overview banner: heading 'Mapping the Voluntary Carbon Market' with a single new introduction paragraph."""
import json
import re

OLD = 'Understanding the Voluntary Carbon Market'
NEW = 'Mapping the Voluntary Carbon Market'
HI = 'स्वैच्छिक कार्बन बाज़ार का मानचित्रण'
PARA = ('Thousands of projects worldwide cut emissions and pull carbon from the atmosphere, and each generates credits. '
        'This dashboard follows that supply from start to finish: where projects are located, which sectors drive them, '
        'how credits are issued, and how many are actually retired.')
P = '<p style="margin:0 0 10px;font-size:14px;line-height:1.55;color:#1b1b1b">' + PARA + '</p>'


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        n = 0
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            for v in pos.values():
                if isinstance(v, dict) and v.get('type') == 'MARKDOWN':
                    code = (v.get('meta') or {}).get('code') or ''
                    if OLD in code and 'Welcome to the' in code:
                        i, j = code.index('<p '), code.rindex('</p>') + 4
                        v['meta']['code'] = code[:i].replace(OLD, NEW) + P + code[j:]
                        n += 1
            d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99zh: overview banner changed', n)
    try:
        p = '/app/cgem/chat/i18n_hi.json'
        dic = json.load(open(p, encoding='utf-8'))
        dic.setdefault('exact', {})[NEW] = HI
        json.dump(dic, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception as e:
        print('v99zh: i18n skipped', e)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zh: skipped:', exc)
