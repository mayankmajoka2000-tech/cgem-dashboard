"""C-GEM v99l online site: the three registry / sector tables show their top 5 rows first and the rest by scrolling inside the list
(header stays pinned while scrolling)."""
import json
import re

HINT = 'Showing the top 5. Scroll inside the list to see the rest.'
CHARTS = {
    'Registries active in India: projects, credits issued and retired, and states covered': ('bh', '.br', 180, 38),
    'Registries active in India: credits issued, retired and vintage': ('fh', '.fr', 342, 76),
    'Sectors: credits issued and retired': ('fh', '.fr', 342, 76),
}


def edit(t, css, head, maxh):
    cls = re.search(r'class="(cgx[0-9a-f]+)"', t).group(1)
    t = t.replace(f'<div class="{head}">', f'<div class="sc"><div class="{head}">', 1)
    end = '{{/each}}<div class="bk">' if head == 'bh' else '{{/each}}<div class="flg">'
    keep = end.replace('{{/each}}', '', 1)
    t = t.replace(end, '{{/each}}</div><div class="hn">' + HINT + '</div>' + keep, 1)
    css += (f'\n.{cls} .sc{{max-height:{maxh}px;overflow-y:auto;border-bottom:1px solid #eef0e9}}'
            f'\n.{cls} .sc .{head}{{position:sticky;top:0;background:#fff;z-index:2}}'
            f'\n.{cls} .hn{{font-size:11px;color:#888;margin:6px 0 0}}')
    return t, css


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        n = 0
        for name, (head, _row, maxh, units) in CHARTS.items():
            for sl in db.session.query(Slice).filter(Slice.slice_name == name).all():
                p = json.loads(sl.params)
                t = p.get('handlebarsTemplate') or ''
                if 'class="sc"' in t:
                    continue
                p['handlebarsTemplate'], p['styleTemplate'] = edit(t, p.get('styleTemplate') or '', head, maxh)
                sl.params = json.dumps(p)
                sl.query_context = None
                n += 1
                for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
                    pos = json.loads(d.position_json)
                    for comp in pos.values():
                        if isinstance(comp, dict) and comp.get('meta', {}).get('chartId') == sl.id:
                            comp['meta']['height'] = units
                    d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99l: top-5 scroll lists:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tweak
        import traceback
        traceback.print_exc()
        print('v99l: skipped:', exc)
