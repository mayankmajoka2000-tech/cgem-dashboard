"""C-GEM v100 online site: inequality (Lorenz) curve + Gini for the host countries, placed on the Global Market Overview tab."""
import json

VIEW = 'ov_lorenz_view'
CLS = 'cgxlor100'
NAME = 'How unevenly are carbon projects spread across host countries? (inequality curve)'
COLS = {1: '#245A2C', 2: '#C98A1F', 3: '#4F7CA3'}
NOUN = {1: 'projects', 2: 'credits issued', 3: 'credits retired'}
TAB = {1: 'Projects registered', 2: 'Credits issued', 3: 'Credits retired'}
CONT_COL = {'Asia': '#C98A1F', 'Africa': '#B85829', 'Europe': '#4F7CA3', 'North America': '#245A2C', 'South America': '#6B9E4A', 'Oceania': '#7A5BA6', 'Other': '#B9BDB0'}


def view_sql():
    pts_col = "CASE m WHEN 1 THEN '#245A2C' WHEN 2 THEN '#C98A1F' ELSE '#4F7CA3' END"
    lab = ("CASE WHEN rn > n - 3 THEN '<circle cx=\"' || printf('%.1f', 50 + x * 4) || '\" cy=\"' || printf('%.1f', 20 + (100 - y) * 4) || '\" r=\"4.5\" fill=\"' || "
           + pts_col + " || '\" stroke=\"#fff\" stroke-width=\"1.5\"/><text x=\"' || printf('%.1f', 42 + x * 4) || '\" y=\"' || printf('%.1f', 24 + (100 - y) * 4) || "
           "'\" text-anchor=\"end\" class=\"lb\">' || REPLACE(country, 'United States of America', 'USA') || '</text>' END")
    cc = ' '.join(f"WHEN '{k}' THEN '{v}'" for k, v in CONT_COL.items())
    return (
        f"CREATE VIEW {VIEW} AS WITH b AS (SELECT country, CASE WHEN continent IS NULL OR continent IN ('Seven seas (open ocean)', 'Not mapped') THEN 'Other' ELSE continent END AS cont, "
        "COUNT(DISTINCT project_key) AS p, COALESCE(SUM(credits_issued), 0) AS i, COALESCE(SUM(credits_retired), 0) AS r FROM projects "
        "WHERE country IS NOT NULL AND country NOT IN ('', 'Not recorded') GROUP BY country), "
        "a AS (SELECT 1 AS m, country, cont, p AS v FROM b UNION ALL SELECT 2, country, cont, i FROM b UNION ALL SELECT 3, country, cont, r FROM b), "
        "c AS (SELECT m, country, cont, v, ROW_NUMBER() OVER (PARTITION BY m ORDER BY v, country) AS rn, "
        "SUM(v) OVER (PARTITION BY m ORDER BY v, country ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum, "
        "COUNT(*) OVER (PARTITION BY m) AS n, SUM(v) OVER (PARTITION BY m) AS tot FROM a), "
        "d AS (SELECT *, 100.0 * rn / n AS x, 100.0 * cum / NULLIF(tot, 0) AS y FROM c), "
        "e AS (SELECT *, COALESCE(LAG(x) OVER (PARTITION BY m ORDER BY rn), 0) AS xp, COALESCE(LAG(y) OVER (PARTITION BY m ORDER BY rn), 0) AS yp FROM d), "
        "k AS (SELECT cont, COUNT(*) AS nc, SUM(p) AS sp, SUM(i) AS si FROM b GROUP BY cont), "
        "kk AS (SELECT *, ROW_NUMBER() OVER (ORDER BY sp DESC) AS rn FROM k) "
        f"SELECT m, country, cont, v, rn, n, x, y, xp, yp, {lab} AS lab, NULL AS html FROM e "
        "UNION ALL SELECT 4, cont, cont, sp, rn, nc, 100.0 * nc / (SELECT COUNT(*) FROM b), 100.0 * sp / (SELECT SUM(p) FROM b), 100.0 * si / (SELECT SUM(i) FROM b), 0, NULL, "
        "'<div class=\"cr\" style=\"order:' || rn || '\"><div class=\"cn\"><i style=\"background:' || CASE cont " + cc + " END || '\"></i>' || cont || '<small>' || nc || ' countries, ' || printf('%,d', sp) || ' projects</small></div>"
        "<div class=\"bs\"><div class=\"b1\"><u style=\"width:' || printf('%.1f', MIN(100, 1.6 * 100.0 * nc / (SELECT COUNT(*) FROM b))) || '%\"></u><span>' || printf('%.0f', 100.0 * nc / (SELECT COUNT(*) FROM b)) || '% of host countries</span></div>"
        "<div class=\"b2\"><u style=\"width:' || printf('%.1f', MIN(100, 1.6 * 100.0 * sp / (SELECT SUM(p) FROM b))) || '%;background:' || CASE cont " + cc + " END || '\"></u><span>' || printf('%.0f', 100.0 * sp / (SELECT SUM(p) FROM b)) || '% of projects</span></div></div></div>' AS html FROM kk "
        "ORDER BY 1, 5")


def metrics():
    m = []
    def add(label, sql): m.append({'expressionType': 'SQL', 'sqlExpression': sql, 'label': label})
    add('nn', "MAX(CASE WHEN m = 1 THEN n END)")
    add('tp', "printf('%,d', SUM(CASE WHEN m = 1 THEN v END))")
    for k in (1, 2, 3):
        add(f'c{k}', f"group_concat(CASE WHEN m = {k} THEN printf('%.1f,%.1f', 50 + x * 4, 20 + (100 - y) * 4) END, ' ')")
        add(f'lab{k}', f"COALESCE(group_concat(CASE WHEN m = {k} THEN lab END, ''), '')")
        add(f'g{k}', f"printf('%.2f', 1 - SUM(CASE WHEN m = {k} THEN (x - xp) * (y + yp) END) / 10000.0)")
        add(f'gp{k}', f"printf('%.0f', 100 * (1 - SUM(CASE WHEN m = {k} THEN (x - xp) * (y + yp) END) / 10000.0))")
        add(f'bot{k}', f"printf('%.1f', SUM(CASE WHEN m = {k} AND rn = CAST(n / 2 AS INTEGER) THEN y END))")
        add(f'bx{k}', f"printf('%.1f', 50 + 4 * SUM(CASE WHEN m = {k} AND rn = CAST(n / 2 AS INTEGER) THEN x END))")
        add(f'by{k}', f"printf('%.1f', 20 + (100 - SUM(CASE WHEN m = {k} AND rn = CAST(n / 2 AS INTEGER) THEN y END)) * 4)")
        add(f't3{k}', f"printf('%.0f', 100 - SUM(CASE WHEN m = {k} AND rn = n - 3 THEN y END))")
        add(f't10{k}', f"printf('%.0f', 100 - SUM(CASE WHEN m = {k} AND rn = n - 10 THEN y END))")
        add(f'k50{k}', f"MAX(CASE WHEN m = {k} THEN n END) - COUNT(CASE WHEN m = {k} AND y <= 50 THEN 1 END)")
        add(f'zero{k}', f"COUNT(CASE WHEN m = {k} AND v = 0 THEN 1 END)")
    add('cont', "COALESCE(group_concat(CASE WHEN m = 4 THEN html END, ''), '')")
    return m


def _blk(tpl, k):
    return tpl.replace('@K', str(k)).replace('@COL', COLS[k]).replace('@NOUN', NOUN[k]).replace('@TAB', TAB[k])


def template():
    tabs = ''.join(_blk('<label for="lt@K" class="tb tb@K">@TAB</label>', k) for k in (1, 2, 3))
    radios = '<input type="radio" name="lm" id="lt1" class="t1" checked><input type="radio" name="lm" id="lt2" class="t2"><input type="radio" name="lm" id="lt3" class="t3">'
    grid = ''
    for t in (25, 50, 75):
        grid += f'<line x1="50" x2="450" y1="{420 - t * 4}" y2="{420 - t * 4}" class="gl"/><line y1="20" y2="420" x1="{50 + t * 4}" x2="{50 + t * 4}" class="gl"/>'
    for t in (0, 25, 50, 75, 100):
        grid += f'<text x="44" y="{424 - t * 4}" text-anchor="end" class="ax">{t}%</text><text y="438" x="{50 + t * 4}" text-anchor="middle" class="ax">{t}%</text>'
    curves = ''.join(_blk(
        '<g class="gm gm@K"><polygon points="50,420 {{{c@K}}}" fill="@COL" fill-opacity=".15"/>'
        '<polyline points="50,420 {{{c@K}}}" fill="none" stroke="@COL" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>'
        '<path d="M50,{{by@K}} H{{bx@K}} V420" class="mk"/><circle cx="{{bx@K}}" cy="{{by@K}}" r="4.5" fill="#fff" stroke="@COL" stroke-width="2.4"/>'
        '<text x="{{bx@K}}" y="{{by@K}}" dx="-9" dy="-9" text-anchor="end" class="mt">Bottom half of countries: {{bot@K}}%</text>{{{lab@K}}}</g>', k) for k in (1, 2, 3))
    svg = ('<svg viewBox="0 0 470 470" class="sv" role="img" aria-label="Lorenz curve of host countries">' + grid +
           '<line x1="50" y1="420" x2="450" y2="20" class="eq"/><text x="262" y="262" class="eqt" transform="rotate(-45 262 262)">perfect equality</text>'
           + curves +
           '<text x="250" y="462" text-anchor="middle" class="ax2">Host countries, ranked from the fewest to the most (cumulative %)</text>'
           '<text transform="rotate(-90 12 220)" x="12" y="220" text-anchor="middle" class="ax2">Cumulative share held</text></svg>')
    stats = ''.join(_blk(
        '<div class="st st@K"><div class="ins">Just <b>{{k50@K}}</b> of the {{nn}} host countries hold half of all @NOUN. The <b>{{bot@K}}%</b> held by the bottom half of countries is almost nothing.</div>'
        '<div class="gn"><span class="gv">{{g@K}}</span><span class="gl2">Gini index<br><small>0 = perfectly equal, 1 = one country has everything</small></span></div>'
        '<div class="gb"><i style="left:{{gp@K}}%"></i></div>'
        '<div class="cd"><div><b>{{t3@K}}%</b><small>held by the top 3 countries</small></div><div><b>{{t10@K}}%</b><small>held by the top 10</small></div>'
        '<div><b>{{bot@K}}%</b><small>held by the bottom half</small></div><div><b>{{zero@K}}</b><small>countries with none</small></div></div></div>', k) for k in (1, 2, 3))
    return ('{{#each data}}' + f'<div class="{CLS}">{radios}<div class="hd">How unevenly are carbon projects spread across host countries?</div>'
            '<div class="sb">The <b>inequality curve</b> (Lorenz curve) lines up every host country from the fewest to the most, then asks how much of the market the lower part holds. '
            'If every country held the same, the curve would follow the dashed diagonal. <b>The further it sags below the diagonal, the more concentrated the market.</b></div>'
            f'<div class="tabs">{tabs}</div><div class="grid"><div class="pl">{svg}</div><div class="rt">{stats}</div></div>'
            '<div class="h2">Who gets the projects? Share of host countries against share of projects, by continent</div>'
            '<div class="cl"><span><i class="s1"></i>Share of host countries</span><span><i class="s2"></i>Share of projects</span></div>'
            '<div class="cw">{{{cont}}}</div>'
            '<div class="nt">Counted over {{nn}} host countries and {{tp}} projects with a recorded country. Gini index = 1 minus twice the area under the curve (the standard inequality measure). '
            'The curve was introduced by Max Lorenz; it is often confused with the Kuznets curve, which is a different idea (income against inequality).</div></div>' + '{{/each}}')


def _on(k):
    return (f'.{CLS} .t{k}:checked~.tabs .tb{k}{{background:{COLS[k]};color:#fff;border-color:{COLS[k]}}}'
            f'.{CLS} .t{k}:checked~.grid .gm{k},.{CLS} .t{k}:checked~.grid .st{k}{{display:block}}')


STYLE = (
    f'.{CLS}{{font-family:Geist,Inter,Segoe UI,Arial,sans-serif;color:#1b1b1b;padding:2px 6px 6px}}'
    f'.{CLS} input{{position:absolute;opacity:0;width:0;height:0;pointer-events:none}}'
    f'.{CLS} .hd{{font-size:17px;font-weight:700;margin:2px 0 4px}}.{CLS} .sb{{font-size:13px;color:#555;line-height:1.5;max-width:900px;margin:0 0 12px}}'
    f'.{CLS} .tabs{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}}'
    f'.{CLS} .tb{{cursor:pointer;font-size:13px;font-weight:600;padding:6px 14px;border:1px solid #D5D8CF;border-radius:999px;background:#fff;color:#333;transition:background .15s}}'
    f'.{CLS} .tb:hover{{background:#F1F3EC}}'
    + _on(1) + _on(2) + _on(3) +
    f'.{CLS} .grid{{display:flex;flex-wrap:wrap;gap:18px 28px;align-items:flex-start}}'
    f'.{CLS} .pl{{flex:1 1 360px;max-width:560px;min-width:280px}}.{CLS} .rt{{flex:1 1 300px;min-width:260px;padding-top:6px}}'
    f'.{CLS} .sv{{width:100%;height:auto;display:block;background:#FBFCF8;border:1px solid #E3E5DE;border-radius:10px}}'
    f'.{CLS} .gl{{stroke:#E6E8E0;stroke-width:1}}.{CLS} .eq{{stroke:#8A8E84;stroke-width:1.6;stroke-dasharray:6 5}}'
    f'.{CLS} .ax{{font-size:10.5px;fill:#777}}.{CLS} .ax2{{font-size:11px;fill:#555;font-weight:600}}.{CLS} .eqt{{font-size:10.5px;fill:#8A8E84;text-anchor:middle}}'
    f'.{CLS} .lb{{font-size:11.5px;font-weight:600;fill:#222;paint-order:stroke;stroke:#FBFCF8;stroke-width:3px}}.{CLS} .mt{{font-size:11px;fill:#333;font-weight:600;paint-order:stroke;stroke:#FBFCF8;stroke-width:3px}}'
    f'.{CLS} .mk{{fill:none;stroke:#555;stroke-width:1.2;stroke-dasharray:3 3}}'
    f'.{CLS} .gm,.{CLS} .st{{display:none}}'
    f'.{CLS} .ins{{font-size:14.5px;line-height:1.5;margin:0 0 14px}}.{CLS} .ins b{{font-size:17px}}'
    f'.{CLS} .gn{{display:flex;align-items:center;gap:12px}}.{CLS} .gv{{font-size:40px;font-weight:800;line-height:1;color:#245A2C}}'
    f'.{CLS} .gl2{{font-size:13px;font-weight:600;line-height:1.3}}.{CLS} .gl2 small{{font-weight:400;color:#777;font-size:11px}}'
    f'.{CLS} .gb{{position:relative;height:8px;border-radius:4px;margin:10px 0 16px;background:linear-gradient(90deg,#9CC49A,#E8C36A,#C0502B)}}'
    f'.{CLS} .gb i{{position:absolute;top:-4px;width:4px;height:16px;border-radius:2px;background:#1b1b1b;margin-left:-2px}}'
    f'.{CLS} .cd{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.{CLS} .cd>div{{background:#F7F8F3;border:1px solid #E3E5DE;border-radius:8px;padding:8px 10px}}'
    f'.{CLS} .cd b{{font-size:21px;display:block}}.{CLS} .cd small{{font-size:11.5px;color:#666}}'
    f'.{CLS} .h2{{font-size:14.5px;font-weight:700;margin:20px 0 6px}}'
    f'.{CLS} .cl{{display:flex;gap:18px;font-size:12px;color:#555;margin:0 0 8px}}.{CLS} .cl i{{display:inline-block;width:14px;height:8px;border-radius:2px;margin-right:6px}}'
    f'.{CLS} .s1{{background:#CFD3C7}}.{CLS} .s2{{background:#245A2C}}'
    f'.{CLS} .cw{{display:flex;flex-direction:column;gap:9px}}.{CLS} .cr{{display:grid;grid-template-columns:190px 1fr;gap:14px;align-items:center}}'
    f'.{CLS} .cn{{font-size:13px;font-weight:600}}.{CLS} .cn i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px}}.{CLS} .cn small{{display:block;font-weight:400;color:#888;font-size:11px;margin-left:17px}}'
    f'.{CLS} .bs>div{{display:flex;align-items:center;height:16px;margin:2px 0}}.{CLS} .bs u{{display:block;height:100%;min-width:2px;border-radius:4px;background:#CFD3C7;text-decoration:none}}'
    f'.{CLS} .bs span{{margin-left:8px;white-space:nowrap;font-size:11px;font-weight:600;color:#333}}'
    f'.{CLS} .nt{{font-size:11px;color:#888;margin-top:14px;line-height:1.5}}'
    '@media (max-width:760px){' + f'.{CLS} .cr{{grid-template-columns:1fr}}' + '}')


def main():

    from superset.app import create_app
    app = create_app()
    with app.app_context():
        import copy
        import sqlite3
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.core import Database
        con = sqlite3.connect('/app/cgem/cgem.db')
        con.execute(f'DROP VIEW IF EXISTS {VIEW}')
        con.execute(view_sql())
        con.commit()
        con.close()
        dbo = db.session.query(Database).filter(Database.database_name == 'C-GEM mastersheet').first()
        tbl = db.session.query(SqlaTable).filter(SqlaTable.table_name == VIEW).first()
        if tbl is None:
            tbl = SqlaTable(table_name=VIEW, schema='main', database=dbo)
            db.session.add(tbl)
            db.session.commit()
        tbl.fetch_metadata()
        db.session.commit()
        top = db.session.query(Slice).filter(Slice.slice_name.like('Top 10 countries by number of total projects%')).first()
        sl = db.session.query(Slice).filter(Slice.slice_name == NAME).first()
        if sl is None:
            sl = Slice(slice_name=NAME, viz_type='handlebars', datasource_type='table', datasource_id=tbl.id)
            db.session.add(sl)
        p = json.loads(top.params) if top is not None else {'viz_type': 'handlebars'}
        for key in ('slice_id', 'timeseries_limit_metric', 'orderby', 'order_desc', 'extra_form_data'):
            p.pop(key, None)
        p.update({'viz_type': 'handlebars', 'datasource': f'{tbl.id}__table', 'query_mode': 'aggregate', 'groupby': [], 'all_columns': [],
                  'metrics': metrics(), 'adhoc_filters': [], 'row_limit': 10, 'handlebarsTemplate': template(), 'styleTemplate': STYLE})
        sl.params = json.dumps(p)
        sl.viz_type = 'handlebars'
        sl.datasource_type = 'table'
        sl.datasource_id = tbl.id
        sl.query_context = None
        sl.description = 'Lorenz (inequality) curve and Gini index of how projects, credits issued and credits retired are spread across host countries.'
        db.session.commit()
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            if sl not in d.slices:
                d.slices.append(sl)
            pos = json.loads(d.position_json)
            if 'CHART-ov_lorenz' not in pos and 'CHART-ov_top10' in pos:
                comp = copy.deepcopy(pos['CHART-ov_top10'])
                comp['id'] = 'CHART-ov_lorenz'
                comp['parents'] = ['ROOT_ID', 'GRID_ID', 'TABS-main', 'TAB-0', 'ROW-ov_lorenz']
                comp['meta'].update({'chartId': sl.id, 'sliceName': NAME, 'height': 132, 'width': 12})
                comp['meta'].pop('sliceNameOverride', None)
                if 'uuid' in comp['meta']:
                    comp['meta']['uuid'] = str(sl.uuid)
                pos['CHART-ov_lorenz'] = comp
                pos['ROW-ov_lorenz'] = {'children': ['CHART-ov_lorenz'], 'id': 'ROW-ov_lorenz', 'meta': {'background': 'BACKGROUND_TRANSPARENT'},
                                        'parents': ['ROOT_ID', 'GRID_ID', 'TABS-main', 'TAB-0'], 'type': 'ROW'}
                kids = pos['TAB-0']['children']
                anchor = 'ROW-ipcc-note' if 'ROW-ipcc-note' in kids else 'ROW-0-7'
                kids.insert(kids.index(anchor) + 1, 'ROW-ov_lorenz')
                d.position_json = json.dumps(pos)
                print('v99b: inequality curve added to the overview tab')
        db.session.commit()



try:
    main()
except Exception as exc:  # never break the site build for an optional chart
    import traceback
    traceback.print_exc()
    print('v99b: skipped:', exc)
