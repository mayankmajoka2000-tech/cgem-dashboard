"""C-GEM v99j online site: "Sectors: credits issued, retired and vintage" loses its vintage parts (KPI tile, hover text, mini chart column and legend)."""
import json
import re

OLD = 'Sectors: credits issued, retired and vintage'
NEW = 'Sectors: credits issued and retired'


def strip(t, css):
    t = re.sub(r'<div class="k v">.*?</div></div>(?=</div>\{\{/if\}\})', '', t, count=1, flags=re.S)
    t = t.replace(' Mini chart = credits by vintage period, from old (brown) to recent (green).', '')
    t = re.sub(r'\{\{#unless novint\}\}<span>average vintage.*?\{\{/if\}\}(?=</div>\{\{/each\}\})', '', t, count=1, flags=re.S)
    t = t.replace('<span>Vintage profile</span>', '')
    t = re.sub(r'<div class="fv">.*?</div></div>(?=</div>\{\{/each\}\}<div class="flg">)', '', t, count=1, flags=re.S)
    t = re.sub(r'<span class="vb">.*?</span>(?=</div></div></div>$)', '', t, count=1, flags=re.S)
    css = css.replace('grid-template-columns:repeat(4,1fr)', 'grid-template-columns:repeat(3,1fr)').replace('250px 1fr 96px 170px', '250px 1fr 96px')
    return t, css


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        n = 0
        for sl in db.session.query(Slice).filter(Slice.slice_name == OLD).all():
            p = json.loads(sl.params)
            p['handlebarsTemplate'], p['styleTemplate'] = strip(p['handlebarsTemplate'], p['styleTemplate'])
            sl.params = json.dumps(p)
            sl.slice_name = NEW
            sl.query_context = None
            n += 1
        db.session.commit()
        print('v99j: sector chart without vintage:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tweak
        import traceback
        traceback.print_exc()
        print('v99j: skipped:', exc)
