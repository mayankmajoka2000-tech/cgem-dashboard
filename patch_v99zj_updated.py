"""v99zj: Overview: a note under 'About this dashboard' on how often the data is updated and when it was last updated.
The dates are read from the database that ships with each build (registry tracker log and data-source table), so they are always the real ones."""
import json
import sqlite3
from datetime import datetime

MID, RID = 'MARKDOWN-ov-updated', 'ROW-ov-updated'


def fmt(s):
    for f in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, f).strftime('%d %b %Y')
        except Exception:
            pass
    return s


def dates():
    con = sqlite3.connect('/app/cgem/cgem.db')
    chk = con.execute('SELECT MAX(run_at) FROM registry_log').fetchone()[0] or con.execute('SELECT MAX(last_checked) FROM data_sources').fetchone()[0]
    new = con.execute('SELECT MAX(last_new_data) FROM data_sources').fetchone()[0]
    con.close()
    return (fmt(chk) if chk else None), (fmt(new) if new else None)


def code(chk, new):
    when = []
    if chk:
        when.append('<b>Last registry check:</b> ' + chk)
    if new:
        when.append('<b>Last new registry data:</b> ' + new)
    return ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:4px 6px 8px\"><div style=\"background:#F3F4EF;border-left:4px solid #2C7A3D;border-radius:6px;padding:12px 16px;"
            "font-size:13.5px;line-height:1.6;color:#2b2b2b\"><div style=\"font-weight:700;color:#2C7A3D;margin-bottom:4px\">How often is the data updated?</div>"
            "The registry tracker checks the public registries every day and takes in new projects, status changes and credit totals. "
            "Registries that offer no automatic download are refreshed when their registry file is uploaded, so their figures are as recent as the last upload."
            + ("<div style=\"margin-top:6px\">" + ' &nbsp;&middot;&nbsp; '.join(when) + "</div>" if when else '') + "</div></div>")


def main():
    chk, new = dates()
    print('v99zj: last check', chk, 'last new data', new)
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            if 'ROW-ov-about' not in pos or MID in pos:
                print('v99zj: skipped (About block missing or already there)')
                continue
            kids = pos['TAB-0']['children']
            base = list(pos['TAB-0']['parents']) + ['TAB-0']
            pos[MID] = {'children': [], 'id': MID, 'meta': {'code': code(chk, new), 'height': 13, 'width': 12}, 'parents': base + [RID], 'type': 'MARKDOWN'}
            pos[RID] = {'children': [MID], 'id': RID, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
            kids.insert(kids.index('ROW-ov-about') + 1, RID)
            d.position_json = json.dumps(pos)
            print('v99zj: update note added')
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print('v99zj: skipped:', exc)
