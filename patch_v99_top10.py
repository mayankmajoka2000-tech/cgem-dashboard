"""C-GEM v99 online site: the chart "Top 10 countries by number of total projects" redesigned.
Each country's bar is split by IPCC sector (Energy, Industrial processes and product use, Agriculture/forestry/land use, Waste), with the
share retired shown next to it; a small table below shows how C-GEM sectors map to IPCC categories."""
import json

# C-GEM sector / sub-sector -> IPCC 2006 sector (1 Energy, 2 IPPU, 3 AFOLU, 4 Waste, 5 Other and not classified)
IPCC = [
 # (sector, sub_sector or None, group)
 ('Industrial & Commercial', 'Fossil Fuel Ops', 1), ('Industrial & Commercial', 'Materials & Manufacturing', 2),
 ('Industrial & Commercial', 'Methane Capture', 4),
 ('Carbon Capture & Storage', 'Industrial CCS', 1), ('Carbon Capture & Storage', None, 5),
 ('Renewable Energy', None, 1), ('Renewable Thermal Energy', None, 1), ('Household & Community', None, 1), ('Transport', None, 1),
 ('Industrial & Commercial', None, 1),
 ('Chemical Processes', None, 2),
 ('Forestry & Land Use', None, 3), ('Agriculture', None, 3),
 ('Waste Management', None, 4),
 ('Carbon Removal (Tech)', None, 5), ('Not classified', None, 5),
]
def q(s): return "'" + s.replace("'", "''") + "'"
def case():
    parts = []
    for sec, sub, g in IPCC:
        cond = f"sector = {q(sec)}" + (f" AND sub_sector = {q(sub)}" if sub else '')
        parts.append(f"WHEN {cond} THEN {g}")
    return "CASE " + ' '.join(parts) + " ELSE 5 END"


NAME = 'Top 10 countries by number of total projects, with credits issued and retired'
CLS = 'cgxipcc99'
COL = {1: '#C98A1F', 2: '#4F7CA3', 3: '#2C7A3D', 4: '#B85829', 5: '#B9BDB0'}
LAB = {1: 'Energy', 2: 'Industry and products', 3: 'Land and agriculture', 4: 'Waste', 5: 'Other, not classified'}
CODE = {1: 'IPCC 1', 2: 'IPPU, IPCC 2', 3: 'AFOLU, IPCC 3', 4: 'IPCC 4', 5: ''}


VIEW = 'ov_ipcc_view'


def view_sql():
    """one row per country, IPCC sector, C-GEM sector and sub-sector; the sub-sector bar of each row is prepared here (no sub-queries in the chart)"""
    colors = ' '.join(f'WHEN {i} THEN \'{COL[i]}\'' for i in COL)
    return (f"CREATE VIEW {VIEW} AS WITH b AS (SELECT country, {case()} AS grp, sector, sub_sector, SUM(credits_issued) AS credits_issued, "
            "SUM(credits_retired) AS credits_retired, SUM(CASE WHEN credits_retired IS NOT NULL THEN credits_issued END) AS issued_with_retired, "
            "COUNT(DISTINCT project_key) AS projects FROM projects WHERE country IS NOT NULL AND country NOT IN ('', 'Not recorded') "
            "GROUP BY country, 2, sector, sub_sector), r AS (SELECT *, 100.0 * credits_issued / NULLIF(SUM(credits_issued) OVER (PARTITION BY country, grp), 0) AS pct, "
            "ROW_NUMBER() OVER (PARTITION BY country, grp ORDER BY credits_issued DESC) AS rk FROM b) "
            "SELECT country, grp, sector, sub_sector, credits_issued, credits_retired, issued_with_retired, projects, rk, "
            "'<div class=\"ss\" style=\"order:' || rk || '\"><span>' || sub_sector || '<small>' || sector || '</small></span><i><u style=\"width:' || "
            f"printf('%.0f', MAX(COALESCE(pct, 0), 2)) || '%;background:' || CASE grp {colors} END || '\"></u></i><em>' || printf('%.0f', COALESCE(pct, 0)) || '%</em></div>' AS html FROM r")


def _fmt(col):
    return (f"CASE WHEN COALESCE(SUM({col}),0) = 0 THEN '0' WHEN SUM({col}) >= 1e9 THEN printf('%.2f bn', SUM({col})/1e9) "
            f"WHEN SUM({col}) >= 1e6 THEN printf('%.1f M', SUM({col})/1e6) WHEN SUM({col}) >= 1e3 THEN printf('%.1f K', SUM({col})/1e3) "
            f"ELSE printf('%d', CAST(SUM({col}) AS INTEGER)) END")


def metrics(old):
    m = [old[0]]                              # country name
    for i in range(1, 6):
        share = f"COALESCE(100.0 * SUM(CASE WHEN grp = {i} THEN credits_issued END) / NULLIF(SUM(credits_issued), 0), 0)"
        m.append({'expressionType': 'SQL', 'sqlExpression': f'ROUND({share}, 1)', 'label': f'p{i}'})
        m.append({'expressionType': 'SQL', 'sqlExpression': f"CASE WHEN {share} >= 11 THEN printf('%.0f%%', {share}) ELSE '' END", 'label': f'l{i}'})
    m.append({'expressionType': 'SQL', 'sqlExpression': "COALESCE(ROUND(100.0 * SUM(credits_retired) / NULLIF(SUM(issued_with_retired), 0)), 0)", 'label': 'rr'})
    m.append({'expressionType': 'SQL', 'sqlExpression': "printf('%,d', SUM(projects)) || ' projects'", 'label': 'pj'})
    m.append({'expressionType': 'SQL', 'sqlExpression': _fmt('credits_issued'), 'label': 'iss'})
    m.append({'expressionType': 'SQL', 'sqlExpression': _fmt('credits_retired'), 'label': 'ret'})
    for i in range(1, 6):                     # sub-sector rows of each IPCC sector (top 6); the order comes from the CSS "order" of each row
        m.append({'expressionType': 'SQL', 'label': f'q{i}', 'sqlExpression':
                  f"COALESCE(group_concat(CASE WHEN grp = {i} AND rk <= 6 THEN html END, ''), '<div class=\"ss\"><span>No credits issued here</span></div>')"})
    return m


def template():
    leg = ''.join(f'<span><i style="background:{COL[i]}"></i>{LAB[i]}{" <small>(" + CODE[i] + ")</small>" if CODE[i] else ""}</span>' for i in range(1, 6))
    segs = ''.join(f'<label for="k{{{{@index}}}}_{i}" style="flex:{{{{p{i}}}}};background:{COL[i]}" title="{LAB[i]}: {{{{p{i}}}}}% of the credits issued. Click to see the sub-sectors."><b>{{{{l{i}}}}}</b></label>' for i in range(1, 6))
    pans = ''.join(f'<div class="bl" style="border-top:3px solid {COL[i]}"><label class="x" for="k{{{{@index}}}}_0">close &#10005;</label><h5>{LAB[i]}: sub-sectors <small>(share of this sector\'s credits in the country)</small></h5>{{{{{{q{i}}}}}}}</div>' for i in range(1, 6))
    ins = '<input type="radio" class="z" name="g{{@index}}" id="k{{@index}}_0" checked>' + ''.join(f'<input type="radio" name="g{{{{@index}}}}" id="k{{{{@index}}}}_{i}">' for i in range(1, 6))
    return (f'<div class="{CLS}"><div class="hd">The ten countries with the most carbon projects, and what kind of projects they are</div>'
            f'<div class="sb">Each bar shows the mix of a country\'s credits by IPCC sector. <b>Click a colour to open its sub-sectors</b>; press close to hide them.</div>'
            f'<div class="lg">{leg}</div>'
            '<div class="rw th"><div></div><div>Mix of credits issued, by sector</div><div class="c">Credits issued</div><div class="c">Retired</div></div>'
            '{{#each data}}<div class="ro">' + ins + '<div class="rw"><div class="nm">{{nm}}<small>{{pj}}</small></div><div class="br">' + segs + '</div>'
            '<div class="c"><b>{{iss}}</b></div><div class="c"><span class="mt"><u style="width:{{rr}}%"></u></span><em>{{rr}}%</em></div></div>'
            '<div class="pn">' + pans + '</div></div>{{/each}}'
            '<div class="nt">Sectors follow the IPCC 2006 Guidelines for National Greenhouse Gas Inventories. Retired = credits already used by a buyer, as a share of credits issued.</div></div>')


STYLE = (
    f'.{CLS}{{font-family:Geist,Inter,Segoe UI,Arial,sans-serif;color:#1b1b1b;padding:2px 4px}}'
    f'.{CLS} .hd{{font-size:15px;font-weight:700;margin:0 0 2px}}.{CLS} .sb{{font-size:12.5px;color:#666;margin:0 0 10px}}'
    f'.{CLS} .lg{{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0 0 14px;font-size:12.5px}}'
    f'.{CLS} .lg i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}.{CLS} .lg small{{color:#888}}'
    f'.{CLS} .rw{{display:grid;grid-template-columns:150px 1fr 96px 104px;column-gap:14px;align-items:center;margin:0 0 9px}}'
    f'.{CLS} .th{{font-size:11px;color:#777;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}}'
    f'.{CLS} .nm{{text-align:right;font-size:13.5px;font-weight:600;color:#222;line-height:1.2}}.{CLS} .nm small{{display:block;font-size:11px;font-weight:400;color:#888;margin-top:2px}}'
    f'.{CLS} .br{{display:flex;height:32px;border-radius:8px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.12);background:#E3E5DE}}'
    f'.{CLS} .br label{{display:flex;align-items:center;justify-content:center;min-width:0;overflow:hidden}}'
    f'.{CLS} .br b{{font-size:11.5px;font-weight:700;color:#fff;white-space:nowrap}}.{CLS} .br label:nth-child(5) b{{color:#333}}'
    f'.{CLS} .c{{text-align:right;font-size:13px}}.{CLS} .c b{{font-size:14px}}.{CLS} .th .c{{text-align:right}}'
    f'.{CLS} .c em{{font-style:normal;font-size:12px;color:#444;margin-left:8px;font-weight:600}}'
    f'.{CLS} .mt{{display:inline-block;width:46px;height:7px;border-radius:4px;background:#E3E5DE;overflow:hidden;vertical-align:middle}}'
    f'.{CLS} .mt u{{display:block;height:100%;background:#245A2C;text-decoration:none}}'
    f'.{CLS} .nt{{font-size:11px;color:#888;margin-top:8px}}'
    f'.{CLS} .br label{{cursor:pointer;transition:opacity .15s,filter .15s}}.{CLS} .br label:hover{{filter:brightness(1.1)}}'
    f'.{CLS} input{{position:absolute;opacity:0;width:0;height:0;pointer-events:none}}.{CLS} .pn,.{CLS} .bl{{display:none}}.{CLS} .ro input:not(.z):checked~.pn{{display:block}}'
    + ''.join(f'.{CLS} .ro input:nth-of-type({i+1}):checked~.pn .bl:nth-child({i}){{display:flex}}.{CLS} .ro input:nth-of-type({i+1}):checked~.rw .br label:not(:nth-child({i})){{opacity:.4}}.{CLS} .ro input:nth-of-type({i+1}):checked~.rw .br label:nth-child({i}){{outline:2px solid #1b1b1b;outline-offset:-2px}}' for i in range(1,6)) +
    f'.{CLS} .x{{align-self:flex-end;cursor:pointer;font-size:11px;color:#777;order:-2}}.{CLS} .x:hover{{color:#000}}'
        f'.{CLS} .pn{{margin:2px 0 6px 162px;background:#F7F8F3;border:1px solid #E3E5DE;border-radius:8px;padding:8px 12px 10px}}'
    f'.{CLS} .bl{{flex-direction:column}}.{CLS} .bl h5{{order:-1;margin:6px 0 8px;font-size:12.5px}}.{CLS} .bl h5 small{{font-weight:400;color:#888}}'
    f'.{CLS} .ss{{display:grid;grid-template-columns:230px 1fr 44px;gap:10px;align-items:center;margin:0 0 6px;font-size:12.5px}}'
    f'.{CLS} .ss span small{{display:block;font-size:10.5px;color:#999}}'
    f'.{CLS} .ss i{{display:block;height:10px;border-radius:5px;background:#E3E5DE;overflow:hidden}}.{CLS} .ss u{{display:block;height:100%;text-decoration:none}}'
    f'.{CLS} .ss em{{font-style:normal;font-weight:600;text-align:right}}'
    '@media (max-width:760px){' + f'.{CLS} .rw{{grid-template-columns:1fr 70px 80px}}.{CLS} .nm{{text-align:left;grid-column:1/-1}}.{CLS} .br{{grid-column:1/-1}}.{CLS} .th{{display:none}}.{CLS} .pn{{margin-left:0}}.{CLS} .ss{{grid-template-columns:1fr 1fr 40px}}.{CLS} .c{{text-align:left}}' + '}')

NOTE = (
    '<div style="font-family:Geist,Inter,\'Segoe UI\',Arial,sans-serif;padding:4px 6px 10px"><div style="font-size:14px;font-weight:700;margin-bottom:6px">'
    'How C-GEM project types map to IPCC sectors</div><table style="width:100%;border-collapse:collapse;font-size:12.5px;line-height:1.45">'
    '<tr style="text-align:left;color:#666"><th style="padding:5px 6px">IPCC sector</th><th style="padding:5px 6px">IPCC category</th><th style="padding:5px 6px">C-GEM project groups</th></tr>'
    + ''.join(f'<tr style="border-top:1px solid #E3E5DE"><td style="padding:5px 6px;white-space:nowrap"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{COL[g]};margin-right:6px"></span>{a}</td>'
              f'<td style="padding:5px 6px">{b}</td><td style="padding:5px 6px">{c}</td></tr>' for g, a, b, c in [
        (1, '1 Energy', '1A1 Energy industries', 'Renewable Energy: grid-scale, distributed, hydropower, bioenergy'),
        (1, '1 Energy', '1A2 Manufacturing industries', 'Industrial &amp; Commercial: energy efficiency'),
        (1, '1 Energy', '1A3 Transport', 'Transport: electrification, efficiency and shift'),
        (1, '1 Energy', '1A4 Other sectors (homes, commercial)', 'Household &amp; Community: clean cooking, efficient lighting, water and health; Renewable Thermal Energy'),
        (1, '1 Energy', '1B Fugitive emissions from fuels / 1C CO2 storage', 'Industrial &amp; Commercial: fossil fuel operations; Carbon Capture &amp; Storage: industrial CCS'),
        (2, '2 Industrial processes and product use (IPPU)', '2B Chemical industry, 2F Refrigerants, 2A/2C Minerals and metals', 'Chemical Processes: gas destruction, refrigerant management; Industrial &amp; Commercial: materials and manufacturing'),
        (3, '3 Agriculture, forestry and other land use (AFOLU)', '3A Livestock, 3C Non-CO2 sources on land', 'Agriculture: livestock and methane, soil and crop management, water management'),
        (3, '3 Agriculture, forestry and other land use (AFOLU)', '3B Land (forest land, cropland)', 'Forestry &amp; Land Use: restoration, land management, conservation'),
        (4, '4 Waste', '4A Solid waste, 4B Biological treatment, 4C Incineration, 4D Wastewater', 'Waste Management: methane capture, circular economy, advanced recovery, waste to energy'),
        (5, 'Other', 'Outside the IPCC inventory sectors', 'Carbon Removal (Tech), engineered removal, projects not yet classified')])
    + '</table><div style="font-size:11.5px;color:#777;margin-top:8px">The IPCC sectors are made for national inventories. C-GEM groups each project by what it does, '
      'so a project is placed in the closest IPCC category and its true category can differ.</div></div>')

from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard
    import sqlite3
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.core import Database
    CGEM_DB = '/app/cgem/cgem.db'
    con = sqlite3.connect(CGEM_DB)
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
    n = 0
    for s in db.session.query(Slice).filter(Slice.slice_name == NAME).all():
        p = json.loads(s.params)
        if CLS in (p.get('handlebarsTemplate') or ''):
            continue
        p['metrics'] = metrics(p['metrics'])
        p['timeseries_limit_metric'] = {'expressionType': 'SQL', 'sqlExpression': 'SUM(projects)', 'label': 'o'}
        p['datasource'] = f'{tbl.id}__table'
        p['handlebarsTemplate'] = template()
        p['styleTemplate'] = STYLE
        s.params = json.dumps(p)
        s.datasource_id = tbl.id
        s.datasource_type = 'table'
        s.query_context = None
        s.description = 'The ten countries hosting the most projects. Bar length = credits issued; colours = IPCC sector (Energy, Industry, Land and agriculture, Waste).'
        n += 1
    print('v99: top 10 countries chart redesigned:', n)
    for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
        pos = json.loads(d.position_json)
        if 'CHART-ov_top10' not in pos or 'ROW-ipcc-note' in pos:
            continue
        pos['CHART-ov_top10']['meta']['height'] = 98
        path = ['ROOT_ID', 'GRID_ID', 'TABS-main', 'TAB-0']
        pos['ROW-ipcc-note'] = {'children': ['MARKDOWN-ipcc-note'], 'id': 'ROW-ipcc-note', 'meta': {'background': 'BACKGROUND_TRANSPARENT'},
                                'parents': path, 'type': 'ROW'}
        pos['MARKDOWN-ipcc-note'] = {'children': [], 'id': 'MARKDOWN-ipcc-note', 'meta': {'code': NOTE, 'height': 58, 'width': 12},
                                     'parents': path + ['ROW-ipcc-note'], 'type': 'MARKDOWN'}
        kids = pos['TAB-0']['children']
        kids.insert(kids.index('ROW-0-7') + 1, 'ROW-ipcc-note')
        d.position_json = json.dumps(pos)
        print('v99: IPCC mapping table added under the chart')
    db.session.commit()
