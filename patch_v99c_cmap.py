"""C-GEM v99c online site: continent map on the Global Market Overview tab. Click a continent: the countries in it open with their projects,
credits and project mix (IPCC sectors). Pure CSS (radio buttons), so it works without scripts."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VIEW = 'ov_cmap_view'
CLS = 'cgxmap100'
NAME = 'Explore the carbon market by continent'
CONTS = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania']
COL = {'Africa': '#B85829', 'Asia': '#C98A1F', 'Europe': '#4F7CA3', 'North America': '#245A2C', 'South America': '#6B9E4A', 'Oceania': '#7A5BA6'}
GRP = {1: ('Energy', '#C98A1F'), 2: ('Industry', '#4F7CA3'), 3: ('Land and agriculture', '#2C7A3D'), 4: ('Waste', '#B85829')}
# where each continent name sits on the map, in % of the map box (Natural Earth projection of a representative point)
TAG = {'Africa': (53.0, 56.0), 'Asia': (72.0, 27.0), 'Europe': (52.5, 17.5), 'North America': (22.0, 27.0), 'South America': (32.0, 66.0), 'Oceania': (87.0, 66.0)}


def fmt(x):
    return (f"(CASE WHEN {x} >= 1e9 THEN printf('%.2f bn', {x} / 1e9) WHEN {x} >= 1e6 THEN printf('%.1f M', {x} / 1e6) "
            f"WHEN {x} >= 1e3 THEN printf('%.0f K', {x} / 1e3) ELSE printf('%d', CAST({x} AS INTEGER)) END)")


def colour(cont='cont'):
    return "CASE " + cont + " " + ' '.join(f"WHEN '{k}' THEN '{v}'" for k, v in COL.items()) + " END"


def ix(cont='cont'):
    return "CASE " + cont + " " + ' '.join(f"WHEN '{k}' THEN {i + 1}" for i, k in enumerate(CONTS)) + " END"


def mix(g, tag='s'):
    """stacked bar of the four IPCC groups from project counts g1..g4 (columns of the current row)"""
    segs = ' || '.join(f"'<s style=\"flex:' || {g[i]} || ';background:{GRP[i][1]}\"></s>'" for i in (1, 2, 3, 4))
    return segs


def mix_text(g):
    tot = ' + '.join(g[i] for i in (1, 2, 3, 4))
    return ' || \' · \' || '.join(f"'{GRP[i][0]} ' || printf('%.0f', 100.0 * {g[i]} / NULLIF({tot}, 0)) || '%'" for i in (1, 2, 3, 4))


def view_sql():
    gc = {i: f'g{i}' for i in (1, 2, 3, 4)}
    sg = ', '.join(f"COUNT(DISTINCT CASE WHEN ic.grp = {i} THEN pr.project_key END) AS g{i}" for i in (1, 2, 3, 4))
    sgt = ', '.join(f"SUM(g{i}) AS g{i}" for i in (1, 2, 3, 4))
    names = {i: i for i in range(1, 5)}
    ctry = (
        "'<div class=\"cy\" style=\"order:' || rk || '\"><div class=\"cnm\"><b>' || REPLACE(country, '&', '&amp;') || '</b><small>' || " + fmt('i') + " || ' credits issued' || "
        "CASE WHEN iw > 0 THEN ', ' || printf('%.0f', 100.0 * r / iw) || '% retired' ELSE '' END || '</small></div>"
        "<div class=\"pb\"><u style=\"width:' || printf('%.1f', MAX(2, 100.0 * p / mx)) || '%;background:' || " + colour() + " || '\"></u><span>' || printf('%,d', p) || '</span></div>"
        "<div class=\"mx\" title=\"' || " + mix_text(gc) + " || '\">' || " + mix(gc) + " || '</div></div>'")
    panel = (
        "'<div class=\"ph\"><i style=\"background:' || " + colour() + " || '\"></i><div><h3>' || cont || '</h3><small>' || nc || ' host countries with registered projects</small></div>"
        "<label class=\"x\" for=\"mc0\">show all &#10005;</label></div><div class=\"tl\"><div><b>' || nc || '</b><small>host countries</small></div>"
        "<div><b>' || printf('%,d', p) || '</b><small>projects, ' || printf('%.0f', 100.0 * p / (SELECT p FROM w)) || '% of the world</small></div>"
        "<div><b>' || " + fmt('i') + " || '</b><small>credits issued, ' || printf('%.0f', 100.0 * i / (SELECT i FROM w)) || '% of the world</small></div>"
        "<div><b>' || CASE WHEN iw > 0 THEN printf('%.0f', 100.0 * r / iw) || '%' ELSE '-' END || '</b><small>of issued credits already retired</small></div></div>"
        "<div class=\"mh\">What kind of projects <small>(IPCC sector, share of projects)</small></div><div class=\"mx big\">' || " + mix(gc) + " || '</div>"
        "<div class=\"ml\">' || " + ' || '.join(f"'<span><i style=\"background:{GRP[i][1]}\"></i>{GRP[i][0]} ' || printf('%.0f', 100.0 * g{i} / NULLIF(g1 + g2 + g3 + g4, 0)) || '%</span>'" for i in (1, 2, 3, 4)) + " || '</div>'")
    ovl = (
        "'<label class=\"ov\" for=\"mc' || " + ix() + " || '\" style=\"order:' || rk || '\"><i style=\"background:' || " + colour() + " || '\"></i><b>' || cont || '</b><small>' || nc || ' countries</small>"
        "<span class=\"ob\"><u style=\"width:' || printf('%.1f', 100.0 * p / (SELECT MAX(p) FROM t)) || '%;background:' || " + colour() + " || '\"></u></span><em>' || printf('%,d', p) || ' projects</em></label>'")
    return (
        f"CREATE VIEW {VIEW} AS WITH h AS (SELECT cc.continent AS cont, pr.country AS country, COUNT(DISTINCT pr.project_key) AS p, COALESCE(SUM(pr.credits_issued), 0) AS i, "
        "COALESCE(SUM(pr.credits_retired), 0) AS r, COALESCE(SUM(CASE WHEN pr.credits_retired IS NOT NULL THEN pr.credits_issued END), 0) AS iw, " + sg + " "
        "FROM projects pr JOIN ipcc_class ic ON ic.project_key = pr.project_key JOIN ov_country_cont cc ON cc.country = pr.country "
        "WHERE pr.country IS NOT NULL AND pr.country NOT IN ('', 'Not recorded') AND cc.continent <> 'Other' GROUP BY cc.continent, pr.country), "
        "t AS (SELECT cont, COUNT(*) AS nc, SUM(p) AS p, SUM(i) AS i, SUM(r) AS r, SUM(iw) AS iw, " + sgt + " FROM h GROUP BY cont), "
        "w AS (SELECT SUM(p) AS p, SUM(i) AS i FROM t), "
        "hr AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY cont ORDER BY p DESC, country) AS rk, MAX(p) OVER (PARTITION BY cont) AS mx FROM h), "
        "tr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY p DESC) AS rk FROM t), "
        "geo AS (SELECT gc.continent AS cont, group_concat(gp.d, '') AS d FROM ov_geo_path gp JOIN ov_geo_cont gc ON gc.iso3 = gp.iso3 GROUP BY gc.continent) "
        "SELECT " + ix() + " AS ix, 1 AS kind, cont, (SELECT d FROM geo WHERE geo.cont = tr.cont) AS d, " + panel + " AS html FROM tr "
        "UNION ALL SELECT " + ix() + ", 2, cont, NULL, " + ctry.replace('i)', 'i)') + " FROM hr "
        "UNION ALL SELECT " + ix() + ", 3, cont, NULL, " + ovl + " FROM tr")


def metrics():
    m = []
    def add(label, sql): m.append({'expressionType': 'SQL', 'sqlExpression': sql, 'label': label})
    for k in range(1, 7):
        add(f'd{k}', f"MAX(CASE WHEN kind = 1 AND ix = {k} THEN d END)")
        add(f'hd{k}', f"COALESCE(MAX(CASE WHEN kind = 1 AND ix = {k} THEN html END), '')")
        add(f'ls{k}', f"COALESCE(group_concat(CASE WHEN kind = 2 AND ix = {k} THEN html END, ''), '')")
    add('ovl', "COALESCE(group_concat(CASE WHEN kind = 3 THEN html END, ''), '')")
    add('wc', "COUNT(CASE WHEN kind = 2 THEN 1 END)")
    return m


def template():
    from patch_v99a_geodata import VIEW_H
    radios = '<input type="radio" name="mc" id="mc0" class="r0" checked>' + ''.join(f'<input type="radio" name="mc" id="mc{k}" class="r{k}">' for k in range(1, 7))
    maps = ''.join(f'<label for="mc{k}" class="cm cm{k}" title="{c}: click to open its countries"><svg viewBox="0 0 1000 {VIEW_H}" preserveAspectRatio="xMidYMid meet"><path d="{{{{{{d{k}}}}}}}" fill="{COL[c]}"/></svg></label>'
                   for k, c in enumerate(CONTS, 1))
    tags = ''.join(f'<span class="tg tg{k}" style="left:{TAG[c][0]}%;top:{TAG[c][1]}%">{c}</span>' for k, c in enumerate(CONTS, 1))
    pans = ''.join(f'<div class="pv pv{k}">{{{{{{hd{k}}}}}}}<div class="lh"><span>Host country</span><span>Projects</span><span>Mix of project types</span></div><div class="ls">{{{{{{ls{k}}}}}}}</div></div>'
                   for k in range(1, 7))
    return ('{{#each data}}' + f'<div class="{CLS}">{radios}<div class="hd">Explore the carbon market by continent</div>'
            '<div class="sb"><b>Click a continent on the map</b> to open the countries inside it, with their projects, credits and the kind of projects they host. You can also pick a continent from the list.</div>'
            f'<div class="grid"><div class="mp"><div class="oc" style="padding-bottom:{round(VIEW_H / 10, 2)}%">{maps}{tags}</div>'
            '<div class="hint">Hover a continent to highlight it. Each colour is one continent.</div></div>'
            '<div class="rp"><div class="pv pv0"><div class="ovh">Where the projects are</div>{{{ovl}}}<div class="ovn">Click a row, or a continent on the map, to see its countries.</div></div>'
            + pans + '</div></div></div>' + '{{/each}}')


def _sel(k):
    return (f'.{CLS} .r{k}:checked~.grid .pv{k}{{display:block}}'
            f'.{CLS} .r{k}:checked~.grid .cm:not(.cm{k}) path{{opacity:.22}}'
            f'.{CLS} .r{k}:checked~.grid .cm{k} path{{stroke:#fff;stroke-width:.8;stroke-linejoin:round;filter:drop-shadow(0 2px 5px rgba(0,0,0,.45))}}'
            f'.{CLS} .r{k}:checked~.grid .tg{k}{{font-size:13px;color:#fff;background:rgba(17,17,17,.78)}}')


STYLE = (
    f'.{CLS}{{font-family:Geist,Inter,Segoe UI,Arial,sans-serif;color:#1b1b1b;padding:2px 6px 6px}}'
    f'.{CLS} input{{position:absolute;opacity:0;width:0;height:0;pointer-events:none}}'
    f'.{CLS} .hd{{font-size:17px;font-weight:700;margin:2px 0 4px}}.{CLS} .sb{{font-size:13px;color:#555;line-height:1.5;max-width:880px;margin:0 0 14px}}'
    f'.{CLS} .grid{{display:flex;flex-wrap:wrap;gap:18px 26px;align-items:flex-start}}'
    f'.{CLS} .mp{{flex:1.3 1 460px;min-width:300px}}.{CLS} .rp{{flex:1 1 420px;min-width:300px}}'
    f'.{CLS} .oc{{position:relative;width:100%;height:0;border-radius:14px;overflow:hidden;background:radial-gradient(ellipse at 50% 40%,#F4F8F6 0%,#E3ECEA 100%);border:1px solid #D8E1DE}}'
    f'.{CLS} .cm{{position:absolute;inset:0;pointer-events:none;display:block}}.{CLS} .cm svg{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}}'
    f'.{CLS} .cm path{{pointer-events:auto;cursor:pointer;stroke:#fff;stroke-width:.5;transition:opacity .2s,filter .2s}}.{CLS} .cm path:hover{{filter:brightness(1.14) saturate(1.1)}}'
    f'.{CLS} .tg{{position:absolute;transform:translate(-50%,-50%);font-size:11.5px;font-weight:700;color:#fff;padding:2px 8px;border-radius:999px;background:rgba(17,17,17,.38);pointer-events:none;white-space:nowrap;letter-spacing:.02em;transition:all .2s}}'
    f'.{CLS} .hint{{font-size:11.5px;color:#888;margin:8px 2px 0}}'
    f'.{CLS} .pv{{display:none}}.{CLS} .r0:checked~.grid .pv0{{display:block}}'
    + ''.join(_sel(k) for k in range(1, 7)) +
    f'.{CLS} .ovh{{font-size:14px;font-weight:700;margin:2px 0 10px}}.{CLS} .pv0{{}}'
    f'.{CLS} .ov{{display:grid;grid-template-columns:14px 118px 1fr 104px;align-items:center;gap:8px;padding:7px 8px;border-radius:9px;cursor:pointer;border:1px solid transparent;transition:background .15s}}'
    f'.{CLS} .ov:hover{{background:#F4F6F0;border-color:#E3E5DE}}.{CLS} .ov i{{width:11px;height:11px;border-radius:50%;display:block}}'
    f'.{CLS} .ov b{{font-size:13.5px}}.{CLS} .ov small{{display:none}}.{CLS} .ob{{height:10px;border-radius:5px;background:#EEF0E9;overflow:hidden;display:block}}.{CLS} .ob u{{display:block;height:100%;border-radius:5px;text-decoration:none}}'
    f'.{CLS} .ov em{{font-style:normal;font-size:12px;color:#555;text-align:right;font-weight:600}}.{CLS} .ovn{{font-size:11.5px;color:#888;margin:10px 4px 0}}'
    f'.{CLS} .ph{{display:flex;align-items:center;gap:10px;margin:0 0 12px}}.{CLS} .ph>i{{width:14px;height:34px;border-radius:5px;display:block}}'
    f'.{CLS} .ph h3{{margin:0;font-size:20px;line-height:1.1;font-weight:800}}.{CLS} .ph small{{color:#777;font-size:12px}}'
    f'.{CLS} .x{{margin-left:auto;cursor:pointer;font-size:12px;font-weight:600;color:#555;padding:5px 11px;border:1px solid #D5D8CF;border-radius:999px;background:#fff}}.{CLS} .x:hover{{background:#F1F3EC}}'
    f'.{CLS} .tl{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 14px}}.{CLS} .tl>div{{background:#F7F8F3;border:1px solid #E3E5DE;border-radius:9px;padding:8px 10px}}'
    f'.{CLS} .tl b{{font-size:19px;display:block;line-height:1.2}}.{CLS} .tl small{{font-size:10.5px;color:#777;line-height:1.3;display:block;margin-top:2px}}'
    f'.{CLS} .mh{{font-size:12.5px;font-weight:700;margin:0 0 6px}}.{CLS} .mh small{{font-weight:400;color:#888}}'
    f'.{CLS} .mx{{display:flex;height:12px;border-radius:6px;overflow:hidden;background:#E3E5DE}}.{CLS} .mx s{{display:block;min-width:0}}.{CLS} .mx.big{{height:16px;border-radius:8px}}'
    f'.{CLS} .ml{{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11.5px;color:#444;margin:7px 0 14px}}.{CLS} .ml i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}}'
    f'.{CLS} .lh{{display:grid;grid-template-columns:175px 1fr 120px;gap:12px;font-size:10.5px;color:#888;text-transform:uppercase;letter-spacing:.05em;padding:0 8px 6px;border-bottom:1px solid #E3E5DE}}'
    f'.{CLS} .ls{{display:flex;flex-direction:column;max-height:330px;overflow-y:auto;padding-right:4px}}'
    f'.{CLS} .cy{{display:grid;grid-template-columns:175px 1fr 120px;gap:12px;align-items:center;padding:7px 8px;border-bottom:1px solid #F0F1EA}}.{CLS} .cy:hover{{background:#FAFBF6}}'
    f'.{CLS} .cnm b{{font-size:13px;display:block;line-height:1.2}}.{CLS} .cnm small{{font-size:10.5px;color:#888}}'
    f'.{CLS} .pb{{display:flex;align-items:center;gap:8px;height:14px}}.{CLS} .pb u{{display:block;height:100%;border-radius:4px;text-decoration:none;min-width:2px}}.{CLS} .pb span{{font-size:12px;font-weight:700;white-space:nowrap}}'
    '@media (max-width:760px){' + f'.{CLS} .tl{{grid-template-columns:1fr 1fr}}.{CLS} .lh,.{CLS} .cy{{grid-template-columns:110px 1fr 70px}}.{CLS} .ov{{grid-template-columns:14px 100px 1fr}}.{CLS} .ov em{{display:none}}' + '}')


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
        sl.description = 'Continent map: click a continent to see its host countries, projects, credits and project mix.'
        db.session.commit()
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            if sl not in d.slices:
                d.slices.append(sl)
            pos = json.loads(d.position_json)
            if 'CHART-ov_cmap' not in pos and 'CHART-ov_top10' in pos:
                comp = copy.deepcopy(pos['CHART-ov_top10'])
                comp['id'] = 'CHART-ov_cmap'
                comp['parents'] = ['ROOT_ID', 'GRID_ID', 'TABS-main', 'TAB-0', 'ROW-ov_cmap']
                comp['meta'].update({'chartId': sl.id, 'sliceName': NAME, 'height': 96, 'width': 12})
                comp['meta'].pop('sliceNameOverride', None)
                if 'uuid' in comp['meta']:
                    comp['meta']['uuid'] = str(sl.uuid)
                pos['CHART-ov_cmap'] = comp
                pos['ROW-ov_cmap'] = {'children': ['CHART-ov_cmap'], 'id': 'ROW-ov_cmap', 'meta': {'background': 'BACKGROUND_TRANSPARENT'},
                                      'parents': ['ROOT_ID', 'GRID_ID', 'TABS-main', 'TAB-0'], 'type': 'ROW'}
                kids = pos['TAB-0']['children']
                anchor = 'ROW-0-5' if 'ROW-0-5' in kids else kids[0]
                kids.insert(kids.index(anchor) + 1, 'ROW-ov_cmap')
                d.position_json = json.dumps(pos)
                print('v99c: continent map added to the overview tab')
        db.session.commit()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional chart
        import traceback
        traceback.print_exc()
        print('v99c: skipped:', exc)
