"""v99z: Overview heading reads 'Understanding the Voluntary Carbon Market'."""
import json

OLD = 'Understanding the Global Carbon Market'
NEW = 'Understanding the Voluntary Carbon Market'
HI = 'स्वैच्छिक कार्बन बाज़ार को समझना'
OLD2 = 'Welcome to the global carbon market'
NEW2 = 'Welcome to the voluntary carbon market'


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
                    if OLD in code or OLD2 in code:
                        v['meta']['code'] = code.replace(OLD, NEW).replace(OLD2, NEW2)
                        n += 1
            d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99z: headings changed', n)
    try:
        p = '/app/cgem/chat/i18n_hi.json'
        dic = json.load(open(p, encoding='utf-8'))
        ex = dic.setdefault('exact', {})
        ex[NEW] = HI
        for k, v in list(ex.items()):
            if OLD2 in k:
                ex[k.replace(OLD2, NEW2)] = v.replace('वैश्विक कार्बन बाज़ार', 'स्वैच्छिक कार्बन बाज़ार')
        json.dump(dic, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        print('v99z: Hindi line added')
    except Exception as e:
        print('v99z: i18n skipped', e)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99z: skipped:', exc)
