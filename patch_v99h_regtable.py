"""C-GEM v99h online site: the table "Registries: projects, credits issued and retired, and host countries" now lists only the registries that
have projects in India, with every number counted for Indian projects; the last column becomes Indian states covered."""
import json

OLD = 'Registries: projects, credits issued and retired, and host countries'
NEW = 'Registries active in India: projects, credits issued and retired, and states covered'
FLT = {'clause': 'WHERE', 'expressionType': 'SQL', 'sqlExpression': "is_india = 'India'"}


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        n = 0
        for sl in db.session.query(Slice).filter(Slice.slice_name == OLD).all():
            p = json.loads(sl.params)
            if FLT in p.get('adhoc_filters', []):
                continue
            p['adhoc_filters'] = p.get('adhoc_filters', []) + [FLT]
            for m in p['metrics']:
                if m['label'] == 'w3':
                    m['sqlExpression'] = "ROUND(100.0 * COALESCE(COUNT(DISTINCT adm1_name),0) / NULLIF(MAX(COALESCE(COUNT(DISTINCT adm1_name),0)) OVER (), 0), 1)"
                elif m['label'] == 't3':
                    m['sqlExpression'] = "printf('%,d', COUNT(DISTINCT adm1_name))"
            t = p['handlebarsTemplate']
            t = t.replace('<span>Host countries</span>', '<span>Indian states</span>')
            t = t.replace('Ranked by number of projects.', 'Indian projects only, ranked by number of projects. Credits and retirements are those of Indian projects.')
            p['handlebarsTemplate'] = t
            sl.params = json.dumps(p)
            sl.slice_name = NEW
            sl.query_context = None
            sl.description = 'Registries that have projects in India: Indian projects, credits issued and retired, and Indian states covered.'
            n += 1
        db.session.commit()
        print('v99h: India registry table:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tweak
        import traceback
        traceback.print_exc()
        print('v99h: skipped:', exc)
