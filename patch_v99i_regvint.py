"""C-GEM v99i online site: "Registries: credits issued, retired and vintage" counts only Indian projects, so it lists the registries that matter for India."""
import json

OLD = 'Registries: credits issued, retired and vintage'
NEW = 'Registries active in India: credits issued, retired and vintage'
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
            t = p['handlebarsTemplate']
            t = t.replace('all registries together</div>', 'all registries together, Indian projects only</div>')
            t = t.replace('Point at a row for its full numbers.', 'Indian projects only. Point at a row for its full numbers.')
            p['handlebarsTemplate'] = t
            sl.params = json.dumps(p)
            sl.slice_name = NEW
            sl.query_context = None
            sl.description = 'Registries that have projects in India: credits issued and retired by Indian projects, retirement rate and vintage profile.'
            n += 1
        db.session.commit()
        print('v99i: India registry credits and vintage:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tweak
        import traceback
        traceback.print_exc()
        print('v99i: skipped:', exc)
