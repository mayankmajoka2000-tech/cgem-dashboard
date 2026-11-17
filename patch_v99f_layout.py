"""C-GEM v99f online site: "Top 10 project developers in India" (slice 9) and "Top 10 buyers of Indian credits" (slice 40) move to the
India Market Atlas tab, each under a short heading; "Projects by year of registration" (slice 36) is taken off the dashboard."""
import json

DEV, BUY, REMOVE = 'CHART-dev_in', 'CHART-buy_in', 'CHART-reg_year'
HEAD = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:12px 6px 4px\"><div style=\"font-size:15px;font-weight:700;"
        "color:#2C7A3D;margin-bottom:10px;\">%s</div><p style=\"margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify\">%s</p></div>")
ITEMS = [(DEV, 'dev', 'Who is developing carbon projects in India', 'The ten organisations with the most carbon projects in India, as recorded in C-GEM\'s dataset.'),
         (BUY, 'buy', 'Who is buying Indian credits', 'The ten largest buyers of credits from Indian projects, as recorded in C-GEM\'s dataset.')]


def parent_of(pos, cid):
    for k, v in pos.items():
        if isinstance(v, dict) and cid in (v.get('children') or []):
            return k


def rearrange(pos, tab='TAB-1'):
    """Returns True if anything changed."""
    changed = False
    t = pos[tab]
    for cid, key, title, text in ITEMS:
        if cid not in pos:
            continue
        old_row = parent_of(pos, cid)
        if old_row and parent_of(pos, old_row) == tab:
            continue  # already in the India tab
        if old_row:  # take it out of its old row; a row left empty goes too, and a lone neighbour fills the width
            pos[old_row]['children'].remove(cid)
            rest = pos[old_row]['children']
            if not rest:
                par = parent_of(pos, old_row)
                pos[par]['children'].remove(old_row)
                del pos[old_row]
            else:
                for o in rest:
                    pos[o]['meta']['width'] = 12
        md, row, crow = f'MARKDOWN-1-{key}-0', f'ROW-1-{key}h', f'ROW-1-{key}c'
        base = ['ROOT_ID', 'GRID_ID', 'TABS-main', tab]
        pos[md] = {'children': [], 'id': md, 'meta': {'code': HEAD % (title, text), 'height': 16, 'width': 12}, 'parents': base + [row], 'type': 'MARKDOWN'}
        pos[row] = {'children': [md], 'id': row, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
        pos[cid]['meta']['width'] = 12
        pos[cid]['parents'] = base + [crow]
        pos[crow] = {'children': [cid], 'id': crow, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
        t['children'] += [row, crow]
        changed = True
    if REMOVE in pos:
        row = parent_of(pos, REMOVE)
        pos[row]['children'].remove(REMOVE)
        del pos[REMOVE]
        if not pos[row]['children']:
            par = parent_of(pos, row)
            pos[par]['children'].remove(row)
            del pos[row]
        changed = True
    return changed


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        n = 0
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            if rearrange(pos):
                d.position_json = json.dumps(pos)
                d.slices = [s for s in d.slices if s.id != 36]
                n += 1
        db.session.commit()
        print('v99f: India atlas layout updated:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for a layout tweak
        import traceback
        traceback.print_exc()
        print('v99f: skipped:', exc)
