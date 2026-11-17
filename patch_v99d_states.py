"""C-GEM v99d online site: the chart "Top 10 states by project count, and India's sector landscape" becomes an interactive league table of all Indian states:
sortable by projects / credits issued / credits retired, bars coloured by IPCC sector, credits per project against the national average,
and a click-to-open detail with the state's sub-sectors and how much each is over- or under-represented compared with India as a whole. Pure CSS."""
import json

VIEW = 'ov_state_view'
CLS = 'cgxst100'
NAME = "Top 10 states by project count, and India's sector landscape"
GRP = {1: ('Energy', '#C98A1F'), 2: ('Industry and products', '#4F7CA3'), 3: ('Land and agriculture', '#2C7A3D'), 4: ('Waste', '#B85829')}
SORT = {1: 'Projects', 2: 'Credits issued', 3: 'Credits retired'}
MAXN = 40


def fmt(x):
    return (f"(CASE WHEN {x} >= 1e9 THEN printf('%.2f bn', {x} / 1e9) WHEN {x} >= 1e6 THEN printf('%.1f M', {x} / 1e6) "
            f"WHEN {x} >= 1e3 THEN printf('%.0f K', {x} / 1e3) ELSE printf('%d', CAST({x} AS INTEGER)) END)")


def gcol(g):
    return "CASE " + g + " " + ' '.join(f"WHEN {k} THEN '{v[1]}'" for k, v in GRP.items()) + " END"


def view_sql():
    where = "pr.is_india = 'India' AND pr.adm1_name IS NOT NULL AND pr.adm1_name <> ''"
    sg = ', '.join(f"COUNT(DISTINCT CASE WHEN ic.grp = {i} THEN pr.project_key END) AS g{i}" for i in (1, 2, 3, 4))
    tot = '(g1 + g2 + g3 + g4)'
    dom = "(CASE WHEN g1 >= MAX(g2, g3, g4) THEN 1 WHEN g3 >= MAX(g2, g4) THEN 3 WHEN g2 >= g4 THEN 2 ELSE 4 END)"
    domname = "(CASE " + dom + " WHEN 1 THEN 'Energy-led' WHEN 2 THEN 'Industry-led' WHEN 3 THEN 'Land and agriculture-led' ELSE 'Waste-led' END)"
    mixbar = ' || '.join(f"'<s style=\"flex:' || g{i} || ';background:{GRP[i][1]}\"></s>'" for i in (1, 2, 3, 4))
    mixtxt = " || ' · ' || ".join(f"'{GRP[i][0]} ' || printf('%.0f', 100.0 * g{i} / NULLIF({tot}, 0)) || '%'" for i in (1, 2, 3, 4))
    mixleg = ' || '.join(f"'<span><i style=\"background:{GRP[i][1]}\"></i>{GRP[i][0]} ' || printf('%.0f', 100.0 * g{i} / NULLIF({tot}, 0)) || '%</span>'" for i in (1, 2, 3, 4))
    cpp = "(i / NULLIF(p, 0))"
    ratio = f"({cpp} / (SELECT ti / tp FROM t))"
    row = (
        "'<div class=\"st a' || rp || ' b' || ri || ' c' || rr || '\"><input type=\"radio\" name=\"sg\" id=\"st' || rp || '\">"
        "<label class=\"rw\" for=\"st' || rp || '\"><span class=\"rk\"><b class=\"k1\">' || rp || '</b><b class=\"k2\">' || ri || '</b><b class=\"k3\">' || rr || '</b></span>"
        "<span class=\"nm\"><b>' || REPLACE(st, '&', '&amp;') || '</b><small>' || " + domname + " || ', ' || printf('%.0f', 100.0 * MAX(g1, g2, g3, g4) / NULLIF(" + tot + ", 0)) || '% of projects</small></span>"
        "<span class=\"pj\"><span class=\"mx\" style=\"width:' || printf('%.1f', MAX(3, 100.0 * p / (SELECT mp FROM t))) || '%\" title=\"' || " + mixtxt + " || '\">' || " + mixbar + " || '</span><em>' || printf('%,d', p) || '</em></span>"
        "<span class=\"cr\"><em>' || " + fmt('i') + " || '</em><i><u style=\"width:' || printf('%.1f', MAX(2, 100.0 * i / (SELECT mi FROM t))) || '%\"></u></i></span>"
        "<span class=\"rt\">' || CASE WHEN iw > 0 THEN '<i><u style=\"width:' || printf('%.0f', MIN(100, 100.0 * r / iw)) || '%\"></u></i><em>' || printf('%.0f', 100.0 * r / iw) || '%</em>' ELSE '<em>-</em>' END || '</span>"
        "<span class=\"pp ' || CASE WHEN i = 0 THEN 'z' WHEN " + ratio + " >= 1.25 THEN 'up' WHEN " + ratio + " <= 0.75 THEN 'dn' ELSE 'eq' END || '\"><em>' || CASE WHEN i = 0 THEN '-' ELSE " + fmt(cpp) + " END || '</em><small>' || CASE WHEN i = 0 THEN '' ELSE printf('%.1f', " + ratio + ") || '× India' END || '</small></span></label>"
        "<div class=\"dt\"><div class=\"dh\"><h4>' || REPLACE(st, '&', '&amp;') || '</h4><small>' || printf('%.1f', 100.0 * p / (SELECT tp FROM t)) || '% of India''s state-tagged projects, ' || printf('%.1f', 100.0 * i / (SELECT ti FROM t)) || '% of its credits issued</small><label class=\"x\" for=\"st0\">close &#10005;</label></div>"
        "<div class=\"dm\">What kind of projects <small>(IPCC sector, share of projects)</small></div><div class=\"mx big\">' || " + mixbar + " || '</div><div class=\"ml\">' || " + mixleg + " || '</div>"
        "<div class=\"dm\">Sub-sectors <small>(share of the state''s projects; tag = more than 1.5 times the India-wide share)</small></div><div class=\"sl\">' || COALESCE((SELECT subs FROM subh WHERE subh.st = rk.st), '') || '</div></div></div>'")
    return (
        f"CREATE VIEW {VIEW} AS WITH s AS (SELECT pr.adm1_name AS st, COUNT(DISTINCT pr.project_key) AS p, COALESCE(SUM(pr.credits_issued), 0) AS i, COALESCE(SUM(pr.credits_retired), 0) AS r, "
        "COALESCE(SUM(CASE WHEN pr.credits_retired IS NOT NULL THEN pr.credits_issued END), 0) AS iw, " + sg + " "
        f"FROM projects pr JOIN ipcc_class ic ON ic.project_key = pr.project_key WHERE {where} GROUP BY pr.adm1_name), "
        "t AS (SELECT SUM(p) AS tp, SUM(i) AS ti, MAX(p) AS mp, MAX(i) AS mi, SUM(r) AS tr, SUM(iw) AS tiw FROM s), "
        "rk AS (SELECT *, ROW_NUMBER() OVER (ORDER BY p DESC, st) AS rp, ROW_NUMBER() OVER (ORDER BY i DESC, st) AS ri, ROW_NUMBER() OVER (ORDER BY r DESC, st) AS rr FROM s), "
        f"sub0 AS (SELECT pr.adm1_name AS st, ic.sub AS sub, ic.grp AS grp, COUNT(DISTINCT pr.project_key) AS n FROM projects pr JOIN ipcc_class ic ON ic.project_key = pr.project_key WHERE {where} GROUP BY pr.adm1_name, ic.sub, ic.grp), "
        "sub1 AS (SELECT *, 100.0 * n / SUM(n) OVER (PARTITION BY st) AS sh, 100.0 * SUM(n) OVER (PARTITION BY sub) / SUM(n) OVER () AS ish, ROW_NUMBER() OVER (PARTITION BY st ORDER BY n DESC, sub) AS k FROM sub0), "
        "subh AS (SELECT st, group_concat('<div class=\"sr\" style=\"order:' || k || '\"><span class=\"sn\">' || REPLACE(sub, '&', '&amp;') || '<small>' || n || ' projects</small></span><i><u style=\"width:' || printf('%.1f', MAX(2, sh)) || '%;background:' || " + gcol('grp') + " || '\"></u></i>"
        "<em>' || printf('%.0f', sh) || '%</em>' || CASE WHEN n >= 3 AND sh / ish >= 1.5 THEN '<b class=\"lq\">' || printf('%.1f', sh / ish) || '× India</b>' ELSE '' END || '</div>', '') AS subs FROM sub1 WHERE k <= 6 GROUP BY st) "
        "SELECT 1 AS kind, st, p, i, r, iw, rp, ri, rr, " + row + " AS html FROM rk "
        "UNION ALL SELECT 3, 'unlocated', COUNT(DISTINCT project_key), COALESCE(SUM(credits_issued), 0), 0, 0, 0, 0, 0, '' FROM projects WHERE is_india = 'India' AND (adm1_name IS NULL OR adm1_name = '') "
        "ORDER BY 1, 7")


def metrics():
    m = []
    def add(label, sql): m.append({'expressionType': 'SQL', 'sqlExpression': sql, 'label': label})
    add('rows', "COALESCE(group_concat(CASE WHEN kind = 1 THEN html END, ''), '')")
    add('tp', "printf('%,d', SUM(CASE WHEN kind = 1 THEN p END))")
    add('ns', "COUNT(CASE WHEN kind = 1 THEN 1 END)")
    add('ti', fmt("SUM(CASE WHEN kind = 1 THEN i END)"))
    add('rtd', "printf('%.0f', 100.0 * SUM(CASE WHEN kind = 1 THEN r END) / NULLIF(SUM(CASE WHEN kind = 1 THEN iw END), 0))")
    add('t3', "printf('%.0f', 100.0 * SUM(CASE WHEN kind = 1 AND rp <= 3 THEN p END) / SUM(CASE WHEN kind = 1 THEN p END))")
    add('t3i', "printf('%.0f', 100.0 * SUM(CASE WHEN kind = 1 AND ri <= 3 THEN i END) / SUM(CASE WHEN kind = 1 THEN i END))")
    add('t3n', "group_concat(CASE WHEN kind = 1 AND rp <= 3 THEN st END, ', ')")
    add('t3in', "group_concat(CASE WHEN kind = 1 AND ri <= 3 THEN st END, ', ')")
    add('un', "printf('%,d', SUM(CASE WHEN kind = 3 THEN p END))")
    add('unp', "printf('%.0f', 100.0 * SUM(CASE WHEN kind = 3 THEN p END) / (SUM(CASE WHEN kind = 3 THEN p END) + SUM(CASE WHEN kind = 1 THEN p END)))")
    return m


def template():
    radios = ('<input type="radio" name="so" id="so1" class="s1" checked><input type="radio" name="so" id="so2" class="s2"><input type="radio" name="so" id="so3" class="s3">'
              '<input type="radio" name="sg" id="st0" class="z" checked>')
    tabs = ''.join(f'<label for="so{k}" class="tb tb{k}">{v}</label>' for k, v in SORT.items())
    leg = ''.join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in GRP.values())
    return ('{{#each data}}' + f'<div class="{CLS}">{radios}<div class="hd">India state by state: where the projects are, and what kind they are</div>'
            '<div class="sb">Every Indian state and union territory with a registered project, ranked. <b>Click a state</b> to open its sub-sectors and see which ones it is unusually strong in.</div>'
            '<div class="kp"><div><b>{{tp}}</b><small>projects with a recorded state</small></div><div><b>{{ns}}</b><small>states and union territories</small></div>'
            '<div><b>{{ti}}</b><small>credits issued</small></div><div><b>{{rtd}}%</b><small>of issued credits retired</small></div>'
            '<div class="hl"><b>{{t3}}%</b><small>of projects sit in just 3 states: {{t3n}}</small></div>'
            '<div class="hl"><b>{{t3i}}%</b><small>of credits issued come from 3 states: {{t3in}}</small></div></div>'
            f'<div class="tabs"><span class="tl">Rank by</span>{tabs}</div><div class="lg">{leg}</div>'
            '<div class="lh"><span>#</span><span>State</span><span>Projects, coloured by IPCC sector</span><span>Credits issued</span><span>Retired</span><span>Credits per project</span></div>'
            '<div class="hn">Showing the top 5. Scroll inside the list to see all {{ns}} states &#8595;</div><div class="tbl">{{{rows}}}</div>'
            '<div class="nt">Bar length = number of projects. Credits per project is compared with the India average (▲ above, ▼ below). {{un}} projects ({{unp}}%) have no state recorded in the registry and are not in this ranking. '
            'Sectors follow the IPCC 2006 Guidelines.</div></div>' + '{{/each}}')


def _css():
    c = []
    for k in (1, 2, 3):
        letter = 'abc'[k - 1]
        c.append(f'.{CLS} .s{k}:checked~.tbl .k{k}{{display:inline}}.{CLS} .s{k}:checked~.tabs .tb{k}{{background:#245A2C;color:#fff;border-color:#245A2C}}')
        c.append(''.join(f'.{CLS} .s{k}:checked~.tbl .{letter}{n}{{order:{n}}}' for n in range(1, MAXN + 1)))
    return ''.join(c)


STYLE = (
    f'.{CLS}{{font-family:Geist,Inter,Segoe UI,Arial,sans-serif;color:#1b1b1b;padding:2px 6px 6px}}'
    f'.{CLS} input{{position:absolute;opacity:0;width:0;height:0;pointer-events:none}}'
    f'.{CLS} .hd{{font-size:17px;font-weight:700;margin:2px 0 4px}}.{CLS} .sb{{font-size:13px;color:#555;line-height:1.5;max-width:900px;margin:0 0 12px}}'
    f'.{CLS} .kp{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:0 0 14px}}.{CLS} .kp>div{{background:#F7F8F3;border:1px solid #E3E5DE;border-radius:9px;padding:8px 11px}}'
    f'.{CLS} .kp b{{font-size:21px;display:block;line-height:1.2}}.{CLS} .kp small{{font-size:11px;color:#777;line-height:1.35;display:block;margin-top:2px}}.{CLS} .kp .hl{{background:#EEF4EA;border-color:#D3E2CC}}'
    f'.{CLS} .tabs{{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 8px}}.{CLS} .tl{{font-size:12px;color:#777;font-weight:600}}'
    f'.{CLS} .tb{{cursor:pointer;font-size:12.5px;font-weight:600;padding:5px 13px;border:1px solid #D5D8CF;border-radius:999px;background:#fff;color:#333}}.{CLS} .tb:hover{{background:#F1F3EC}}'
    f'.{CLS} .lg{{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:12px;color:#444;margin:0 0 10px}}.{CLS} .lg i,.{CLS} .ml i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}}'
    f'.{CLS} .lh,.{CLS} .rw{{display:grid;grid-template-columns:34px 190px minmax(160px,1fr) 108px 96px 112px;gap:12px;align-items:center}}'
    f'.{CLS} .lh{{font-size:10.5px;color:#888;text-transform:uppercase;letter-spacing:.05em;padding:0 8px 6px;border-bottom:1px solid #E3E5DE}}'
    f'.{CLS} .tbl{{display:flex;flex-direction:column;max-height:262px;overflow-y:scroll;padding-right:6px;scrollbar-width:thin;scrollbar-color:#9DB894 #EEF0E9;border-bottom:1px solid #E3E5DE}}'
    f'.{CLS} .tbl:has(.st input:checked){{max-height:440px}}.{CLS} .hn{{font-size:12px;color:#245A2C;font-weight:600;margin:0 0 6px}}'
    f'.{CLS} .st{{border-bottom:1px solid #F0F1EA}}.{CLS} .rw{{padding:8px;cursor:pointer;border-radius:8px;transition:background .15s}}.{CLS} .rw:hover{{background:#F6F8F1}}'
    f'.{CLS} .rk b{{display:none;font-size:12px;color:#888;font-weight:700}}.{CLS} .k1{{display:inline!important}}.{CLS} .s2:checked~.tbl .k1,.{CLS} .s3:checked~.tbl .k1{{display:none!important}}'
    f'.{CLS} .nm b{{font-size:13.5px;display:block;line-height:1.2}}.{CLS} .nm small{{font-size:10.5px;color:#888}}'
    f'.{CLS} .pj{{display:flex;align-items:center;gap:8px}}.{CLS} .mx{{display:flex;height:16px;border-radius:5px;overflow:hidden;background:#E3E5DE;min-width:6px}}.{CLS} .mx s{{display:block;min-width:0}}'
    f'.{CLS} .pj em,.{CLS} .cr em,.{CLS} .rt em,.{CLS} .pp em{{font-style:normal;font-size:12.5px;font-weight:700;white-space:nowrap}}'
    f'.{CLS} .cr,.{CLS} .rt{{display:flex;flex-direction:column;gap:3px}}.{CLS} .rt{{flex-direction:row;align-items:center;gap:7px}}'
    f'.{CLS} .cr i,.{CLS} .rt i{{display:block;height:6px;border-radius:3px;background:#EEF0E9;overflow:hidden;flex:1}}.{CLS} .rt i{{min-width:40px}}.{CLS} .cr i u,.{CLS} .rt i u{{display:block;height:100%;border-radius:3px;background:#245A2C;text-decoration:none}}'
    f'.{CLS} .cr i u{{background:#C98A1F}}'
    f'.{CLS} .pp small{{display:block;font-size:10.5px;font-weight:600}}.{CLS} .pp.up small{{color:#2C7A3D}}.{CLS} .pp.up small:before{{content:"\\25B2 "}}.{CLS} .pp.dn small{{color:#B85829}}.{CLS} .pp.dn small:before{{content:"\\25BC "}}.{CLS} .pp.eq small{{color:#888}}'
    f'.{CLS} .dt{{display:none;margin:2px 8px 12px 46px;background:#F7F8F3;border:1px solid #E3E5DE;border-radius:10px;padding:12px 16px 14px}}.{CLS} .st input:checked~.dt{{display:block}}'
    f'.{CLS} .st input:checked~.rw{{background:#EEF4EA}}'
    f'.{CLS} .dh{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 10px}}.{CLS} .dh h4{{margin:0;font-size:17px}}.{CLS} .dh small{{color:#777;font-size:12px}}'
    f'.{CLS} .x{{margin-left:auto;cursor:pointer;font-size:12px;font-weight:600;color:#555;padding:4px 11px;border:1px solid #D5D8CF;border-radius:999px;background:#fff}}'
    f'.{CLS} .dm{{font-size:12.5px;font-weight:700;margin:6px 0 6px}}.{CLS} .dm small{{font-weight:400;color:#888}}.{CLS} .mx.big{{height:16px;border-radius:8px}}'
    f'.{CLS} .ml{{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11.5px;color:#444;margin:7px 0 10px}}'
    f'.{CLS} .sl{{display:flex;flex-direction:column}}.{CLS} .sr{{display:grid;grid-template-columns:230px 1fr 42px 74px;gap:10px;align-items:center;margin:0 0 6px;font-size:12.5px}}'
    f'.{CLS} .sn small{{display:block;font-size:10.5px;color:#999}}.{CLS} .sr i{{display:block;height:10px;border-radius:5px;background:#E3E5DE;overflow:hidden}}.{CLS} .sr u{{display:block;height:100%;text-decoration:none}}'
    f'.{CLS} .sr em{{font-style:normal;font-weight:700;text-align:right}}.{CLS} .lq{{font-size:10.5px;color:#245A2C;background:#E2EFDC;border-radius:999px;padding:2px 8px;white-space:nowrap;text-align:center}}'
    f'.{CLS} .nt{{font-size:11px;color:#888;margin-top:12px;line-height:1.5}}'
    + _css() +
    '@media (max-width:820px){' + f'.{CLS} .lh{{display:none}}.{CLS} .rw{{grid-template-columns:28px 1fr 80px;gap:8px 10px}}.{CLS} .pj{{grid-column:2/-1}}.{CLS} .cr{{grid-column:2}}.{CLS} .rt{{grid-column:3}}.{CLS} .pp{{display:none}}.{CLS} .dt{{margin-left:8px}}.{CLS} .sr{{grid-template-columns:1fr 1fr 40px}}.{CLS} .lq{{display:none}}' + '}')


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
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
        n = 0
        for sl in db.session.query(Slice).filter(Slice.slice_name == NAME).all():
            p = json.loads(sl.params)
            if CLS in (p.get('handlebarsTemplate') or ''):
                continue
            for key in ('timeseries_limit_metric', 'orderby', 'order_desc', 'extra_form_data'):
                p.pop(key, None)
            p.update({'datasource': f'{tbl.id}__table', 'query_mode': 'aggregate', 'groupby': [], 'all_columns': [], 'metrics': metrics(),
                      'adhoc_filters': [], 'row_limit': 10, 'handlebarsTemplate': template(), 'styleTemplate': STYLE})
            sl.params = json.dumps(p)
            sl.datasource_id = tbl.id
            sl.datasource_type = 'table'
            sl.query_context = None
            sl.description = 'League table of every Indian state: projects by IPCC sector, credits issued and retired, credits per project against the India average, and a click-to-open sub-sector view.'
            n += 1
            for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
                pos = json.loads(d.position_json)
                for comp in pos.values():
                    if isinstance(comp, dict) and comp.get('meta', {}).get('chartId') == sl.id:
                        comp['meta']['height'] = 98
                d.position_json = json.dumps(pos)
        db.session.commit()
        print('v99d: India state league table:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # never break the site build for an optional chart
        import traceback
        traceback.print_exc()
        print('v99d: skipped:', exc)
