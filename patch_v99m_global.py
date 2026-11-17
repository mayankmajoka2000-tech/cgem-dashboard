"""C-GEM v99m online site: "Top 10 project developers globally" and "Top 10 buyers globally" sit side by side (Registry tab), each showing
its top 5 rows first and the rest by scrolling inside the list."""
import json
import re

HINT = 'Showing the top 5. Scroll inside the list to see the rest.'
NAMES = ['Top 10 project developers globally', 'Top 10 buyers globally']
ROW_DEV, ROW_BUY_HEAD, ROW_BUY, ROW_HEAD, DEV, BUY = 'ROW-2-13', 'ROW-2-14', 'ROW-2-15', 'ROW-2-12', 'CHART-dev_gl', 'CHART-buy_gl'
HEAD_CODE = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:12px 6px 4px\"><div style=\"font-size:15px;font-weight:700;color:#2C7A3D;"
             "margin-bottom:10px;\">Who is generating the supply, and who is using the credits<span style=\"color:#0E1410\">?</span></div>"
             "<div style=\"display:flex;gap:28px\"><div style=\"flex:1\"><div style=\"font-size:15.5px;font-weight:700;color:#0E1410;margin-bottom:3px\">Project developers</div>"
             "<p style=\"margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify\">Project developers design and implement carbon projects, manage project activities and coordinate "
             "the processes required to register, monitor and verify emission reductions or removals. The list shows the leading developers globally.</p></div>"
             "<div style=\"flex:1\"><div style=\"font-size:15.5px;font-weight:700;color:#0E1410;margin-bottom:3px\">Credit buyers</div>"
             "<p style=\"margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify\">Credit buyers acquire credits for different purposes, including voluntary climate commitments and "
             "other eligible uses. Retirement records show the organisations using credits, where the registry discloses the buyer.</p></div></div></div>")


def edit_chart(t, css):
    cls = re.search(r'class="(cgx[0-9a-f]+)"', t).group(1)
    t = t.replace('<div class="tt">{{#each data}}', '<div class="tt"><div class="sc">{{#each data}}', 1)
    t = t.replace('{{/each}}{{#each data}}{{#if @first}}', '{{/each}}</div><div class="hn">' + HINT + '</div>{{#each data}}{{#if @first}}', 1)
    css += (f'\n.{cls} .sc{{max-height:312px;overflow-y:auto}}\n.{cls} .hn{{font-size:11px;color:#888;margin:6px 0 0}}')
    return t, css


def parent_of(pos, cid):
    for k, v in pos.items():
        if isinstance(v, dict) and cid in (v.get('children') or []):
            return k


def layout(pos):
    if DEV not in pos or BUY not in pos or parent_of(pos, BUY) == parent_of(pos, DEV):
        return False
    old = parent_of(pos, BUY)
    pos[old]['children'].remove(BUY)
    pos[ROW_DEV]['children'].append(BUY)
    pos[BUY]['parents'] = pos[DEV]['parents']
    for c in (DEV, BUY):
        pos[c]['meta']['width'] = 6
        pos[c]['meta']['height'] = 52
    tab = parent_of(pos, old)
    for r in (old, ROW_BUY_HEAD):
        if r in pos and tab and r in pos[tab]['children']:
            pos[tab]['children'].remove(r)
            for ch in pos[r].get('children', []):
                pos.pop(ch, None)
            del pos[r]
    md = pos.get('MARKDOWN-2-12-0')
    if md:
        md['meta']['code'] = HEAD_CODE
    return True


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        n = 0
        for name in NAMES:
            for sl in db.session.query(Slice).filter(Slice.slice_name == name).all():
                p = json.loads(sl.params)
                t = p.get('handlebarsTemplate') or ''
                if 'class="sc"' in t:
                    continue
                p['handlebarsTemplate'], p['styleTemplate'] = edit_chart(t, p.get('styleTemplate') or '')
                sl.params = json.dumps(p)
                sl.query_context = None
                n += 1
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            if layout(pos):
                d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99m: global developers and buyers side by side:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional tweak
        import traceback
        traceback.print_exc()
        print('v99m: skipped:', exc)
