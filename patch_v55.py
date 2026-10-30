"""C-GEM v55 update for the online site: adds the tracker update log to Live Prices."""
import json
import uuid

from superset.app import create_app

NAME = "Every tracker run, by source (newest first)"
DESC = "When the price tracker last ran and whether each source updated: one row per source per run, newest first."
VIZ = "handlebars"
PARAMS = json.loads("{\"query_mode\": \"aggregate\", \"groupby\": [\"run_at\", \"series\", \"status\", \"rows\", \"latest_date\", \"message\"], \"metrics\": [{\"expressionType\": \"SQL\", \"sqlExpression\": \"CASE MAX(series) WHEN 'CARBONMARK' THEN 'Carbonmark live offers' WHEN 'CME_VCM' THEN 'CME offset futures (NYMEX)' WHEN 'USDINR=X' THEN 'US dollar to rupee' ELSE MAX(series) END\", \"label\": \"src\"}, {\"expressionType\": \"SQL\", \"sqlExpression\": \"CASE MAX(series) WHEN 'CARBONMARK' THEN 'api.carbonmark.com' WHEN 'CME_VCM' THEN 'CME Group Daily Environmental Report' WHEN 'USDINR=X' THEN 'Yahoo Finance' ELSE '' END\", \"label\": \"srcw\"}, {\"expressionType\": \"SQL\", \"sqlExpression\": \"CASE WHEN MAX(status) = 'Updated' THEN 'ok' WHEN MAX(status) LIKE 'Failed%' THEN 'bad' ELSE 'oth' END\", \"label\": \"sc\"}, {\"expressionType\": \"SQL\", \"sqlExpression\": \"strftime('%d', MAX(run_at)) || ' ' || CASE strftime('%m', MAX(run_at)) WHEN '01' THEN 'Jan' WHEN '02' THEN 'Feb' WHEN '03' THEN 'Mar' WHEN '04' THEN 'Apr' WHEN '05' THEN 'May' WHEN '06' THEN 'Jun' WHEN '07' THEN 'Jul' WHEN '08' THEN 'Aug' WHEN '09' THEN 'Sep' WHEN '10' THEN 'Oct' WHEN '11' THEN 'Nov' ELSE 'Dec' END || ' ' || strftime('%Y', MAX(run_at))\", \"label\": \"day\"}, {\"expressionType\": \"SQL\", \"sqlExpression\": \"strftime('%H:%M', MAX(run_at))\", \"label\": \"hm\"}, {\"expressionType\": \"SQL\", \"sqlExpression\": \"CASE WHEN ROW_NUMBER() OVER (PARTITION BY MAX(run_at) ORDER BY MAX(series) DESC) = 1 THEN 1 END\", \"label\": \"newrun\"}, {\"expressionType\": \"SQL\", \"sqlExpression\": \"MAX(run_at) || MAX(series)\", \"label\": \"o\"}], \"row_limit\": 200, \"timeseries_limit_metric\": {\"expressionType\": \"SQL\", \"sqlExpression\": \"MAX(run_at) || MAX(series)\", \"label\": \"ord\"}, \"order_desc\": true, \"handlebarsTemplate\": \"<div class=\\\"cgx9fc17890\\\"><div class=\\\"tl\\\"><div class=\\\"th\\\"><span>Run (time of update)</span><span>Source</span><span>Status</span><span>Rows</span><span>Latest data</span><span>Details</span></div>{{#each data}}<div class=\\\"tr{{#if newrun}} nr{{/if}}\\\"><span class=\\\"tt\\\">{{#if newrun}}<b>{{day}}</b> {{hm}}{{/if}}</span><span><b>{{src}}</b><small>{{srcw}}</small></span><span><i class=\\\"b {{sc}}\\\">{{status}}</i></span><span class=\\\"n\\\">{{rows}}</span><span class=\\\"n\\\">{{latest_date}}</span><span class=\\\"m\\\">{{message}}</span></div>{{/each}}<div class=\\\"tk\\\">Newest run first; the tracker keeps its last 30 runs. \\\"Failed (kept previous data)\\\" means the source could not be reached at that run, so the earlier prices stay on the page.</div></div></div>\", \"styleTemplate\": \".cgx9fc17890 .tl{font-family:Geist,Inter,Segoe UI,Arial,sans-serif;font-size:12.5px;color:#0E1410}\\n.cgx9fc17890 .th,.cgx9fc17890 .tr{display:grid;grid-template-columns:150px 220px 190px 50px 100px 1fr;gap:12px;align-items:center;padding:7px 10px}\\n.cgx9fc17890 .th{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:#555;border-bottom:1px solid #e3e6dc;background:#F4F4EF;border-radius:8px 8px 0 0}\\n.cgx9fc17890 .tr{border-bottom:1px solid #eef0e9}\\n.cgx9fc17890 .tr.nr{border-top:2px solid #D8ECDC}\\n.cgx9fc17890 .tr:hover{background:#F6F7F2}\\n.cgx9fc17890 .tt{font-family:Geist Mono,ui-monospace,Menlo,monospace;font-size:12px;color:#333}\\n.cgx9fc17890 .tt b{font-weight:700;color:#0E1410}\\n.cgx9fc17890 .tr small{display:block;font-size:10.5px;color:#888}\\n.cgx9fc17890 .n{font-family:Geist Mono,ui-monospace,Menlo,monospace;font-size:12px}\\n.cgx9fc17890 .m{font-size:12px;color:#555}\\n.cgx9fc17890 .b{font-style:normal;font-weight:700;font-size:10.5px;border-radius:999px;padding:2px 9px;white-space:nowrap}\\n.cgx9fc17890 .b.ok{background:#D8ECDC;color:#265E30}\\n.cgx9fc17890 .b.bad{background:#f6e2d6;color:#B85829}\\n.cgx9fc17890 .b.oth{background:#eee;color:#555}\\n.cgx9fc17890 .tk{font-size:11px;color:#888;margin-top:8px}\", \"viz_type\": \"handlebars\", \"color_scheme\": \"cgemEarth\", \"adhoc_filters\": []}")
MD_CODE = "<div style=\"font-family:Inter,Segoe UI,Arial,sans-serif;padding:6px 2px 8px;border-bottom:2px solid #2C7A3D\"><div style=\"font-size:20px;font-weight:700;color:#2b2b2b\">Tracker update log</div><div style=\"font-size:14px;color:#5a5a5a;margin-top:2px\">When the price tracker last ran and whether each source updated, newest run first.</div></div>"
ANCHOR = 'C-GEM price tracker, combining Carbonmark'

app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.core import Database
    ds = db.session.query(SqlaTable).filter_by(table_name='live_prices_log').first()
    if ds is None:
        dbo = db.session.query(Database).filter_by(database_name='C-GEM mastersheet').first()
        if dbo is not None:
            ds = SqlaTable(table_name='live_prices_log', database=dbo)
            db.session.add(ds)
            db.session.flush()
            try:
                ds.fetch_metadata()
            except Exception as e:
                print('v55 patch: column refresh failed', e)
    sl = db.session.query(Slice).filter_by(slice_name=NAME).first()
    if ds is None:
        print('v55 patch: dataset live_prices_log not found, skipped')
    elif sl is None:
        prm = dict(PARAMS, datasource=f'{ds.id}__table')
        sl = Slice(slice_name=NAME, viz_type=VIZ, datasource_type='table', datasource_id=ds.id, params=json.dumps(prm), description=DESC)
        db.session.add(sl)
        db.session.flush()
        for dash in db.session.query(Dashboard).all():
            pos = json.loads(dash.position_json or '{}')
            tab = next((k for k, v in pos.items() if isinstance(v, dict) and v.get('type') == 'TAB'
                        and (v.get('meta') or {}).get('text') == 'Live Prices'), None)
            anchor = next((k for k, v in pos.items() if isinstance(v, dict) and v.get('type') == 'MARKDOWN'
                           and ANCHOR in ((v.get('meta') or {}).get('code') or '')), None)
            if not tab or not anchor:
                continue
            arow = pos[anchor]['parents'][-1]
            base = pos[tab]['parents'] + [tab]
            r1, m1, r2, c1 = 'ROW-trk-1', 'MARKDOWN-trk-1', 'ROW-trk-2', 'CHART-trk-1'
            pos[r1] = {'type': 'ROW', 'id': r1, 'children': [m1], 'parents': base, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}}
            pos[m1] = {'type': 'MARKDOWN', 'id': m1, 'children': [], 'parents': base + [r1], 'meta': {'code': MD_CODE, 'width': 12, 'height': 12}}
            pos[r2] = {'type': 'ROW', 'id': r2, 'children': [c1], 'parents': base, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}}
            pos[c1] = {'type': 'CHART', 'id': c1, 'children': [], 'parents': base + [r2],
                       'meta': {'chartId': sl.id, 'width': 12, 'height': 60, 'uuid': str(sl.uuid), 'sliceName': NAME}}
            kids = pos[tab]['children']
            i = kids.index(arow) + 1 if arow in kids else len(kids)
            pos[tab]['children'] = kids[:i] + [r1, r2] + kids[i:]
            dash.position_json = json.dumps(pos)
            dash.slices = list(dash.slices) + [sl]
            md = json.loads(dash.json_metadata or '{}')
            for f in md.get('native_filter_configuration', []):
                sc = f.setdefault('scope', {'rootPath': ['ROOT_ID'], 'excluded': []})
                sc.setdefault('excluded', []).append(sl.id)
            dash.json_metadata = json.dumps(md)
        db.session.commit()
        print('v55 patch: tracker log added')
    else:
        print('v55 patch: already present')
