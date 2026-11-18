"""v99zf: Registry & Market tab: "Quality labels and certifications": how many projects worldwide carry CCP, CORSIA, CCB, SDG+ and other labels.

Data: the certifications table (one row per project and label, as the registries publish them) is summarised into a small table (lab_tab).
Only labels that really are quality, integrity or co-benefit labels are counted; SDG goal names, tax and status entries are left out.
A project can carry several labels, so the rows overlap. Logs to /app/cgem/chat/v99zf.log."""
import copy
import json
import os

LOGF = '/app/cgem/chat/v99zf.log'
TABLE = 'lab_tab'
CLS = 'cgxlab01'
CHART_NAME = 'Quality labels and certifications carried by projects worldwide'
FONT = "font-family:Geist,Inter,'Segoe UI',Arial,sans-serif"


def LOG(*a):
    msg = ' '.join(str(x) for x in a)
    print('v99zf:', msg)
    try:
        os.makedirs(os.path.dirname(LOGF), exist_ok=True)
        with open(LOGF, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


# fam, label, description, SQL condition on certifications.label
LABELS = [
    ('integ', 'ICVCM Core Carbon Principles (CCP)', 'Approved by the Integrity Council for the Voluntary Carbon Market', "label = 'ICVCM CCP'"),
    ('integ', 'CORSIA eligible', "Eligible to offset airline emissions under ICAO's CORSIA", "label = 'CORSIA label'"),
    ('integ', 'Article 6 authorised', 'The host country has authorised use of the credits under Article 6 of the Paris Agreement',
     "label LIKE 'Article 6 Authorized%' OR label LIKE 'Article Six Authorization: Compliance%' OR label LIKE 'Article Six Authorization: Other Purpose%'"),
    ('integ', 'ICROA endorsed', 'Registry flags the project as meeting the ICROA code of best practice', "label LIKE 'ICROA%'"),
    ('integ', 'Carbon-tax offset eligible', 'Credits can be used against a national or local carbon tax', "label LIKE '%Carbon Tax%' OR label LIKE '%Green Tax%'"),
    ('cobe', 'S+ no-net-harm', 'Social no-net-harm safeguards label', "label = 'S+ no-net-harm'"),
    ('cobe', 'E+ no-net-harm', 'Environmental no-net-harm safeguards label', "label = 'E+ no-net-harm'"),
    ('cobe', 'CCB (Climate, Community and Biodiversity)', 'Community and biodiversity benefits verified on top of the carbon', "label = 'CCB'"),
    ('cobe', 'SDG+ label', 'SDG impact label, Bronze to Diamond tiers', "label LIKE '%SDG+ label'"),
    ('cobe', 'Social Carbon', 'Social Carbon methodology label', "label = 'Social Carbon'"),
    ('cobe', 'Gold Standard Gender Responsive', 'Project designed and reported to advance gender equality', "label = 'Gold Standard Gender Responsive'"),
    ('rate', 'Independent quality rating', 'A rating from MSCI or BeZero is listed for the project', "label LIKE 'MSCI rating%' OR label LIKE 'BeZero rating%'"),
]
FAM = {'integ': ('Integrity and market access', 'Labels that decide where a credit can be used or whether it meets an integrity benchmark'),
       'cobe': ('Social and environmental co-benefits', 'Labels that recognise benefits for people, communities and nature beyond the tonne'),
       'rate': ('Independent ratings', 'Third-party quality ratings')}
COLS = ['ord', 'kind', 'fam', 'label', 'note', 'reg', 'val', 'pct', 'w']


def build_table(con):
    con.execute(f'DROP TABLE IF EXISTS {TABLE}')
    con.execute(f'CREATE TABLE {TABLE} (ord INTEGER, kind TEXT, fam TEXT, label TEXT, note TEXT, reg TEXT, val TEXT, pct TEXT, w REAL)')
    tot = con.execute("SELECT COUNT(*) FROM projects WHERE registry <> 'Unknown registry'").fetchone()[0]
    ok = "(SELECT project_key FROM projects WHERE registry <> 'Unknown registry')"
    rows = []
    for fam, name, note, cond in LABELS:
        n = con.execute(f'SELECT COUNT(DISTINCT project_key) FROM certifications WHERE ({cond}) AND project_key IN {ok}').fetchone()[0]
        regs = con.execute(f'SELECT registry, COUNT(DISTINCT project_key) c FROM certifications WHERE ({cond}) AND project_key IN {ok} '
                           'AND registry IS NOT NULL GROUP BY 1 ORDER BY c DESC LIMIT 2').fetchall()
        rows.append((fam, name, note, n, regs))
    nmax = max([r[3] for r in rows] + [1])
    anyc = ' OR '.join('(%s)' % c for _f, _n, _d, c in LABELS)
    anyn, nreg = con.execute(f'SELECT COUNT(DISTINCT project_key), COUNT(DISTINCT registry) FROM certifications WHERE ({anyc}) AND project_key IN {ok}').fetchone()
    top = max(rows, key=lambda r: r[3])
    ins = []
    kp = [('Projects with at least one label', 'Counting only the labels listed below', f'{anyn:,}'),
          ('Share of all projects', f'Out of {tot:,} projects in the registry dataset', '%.1f%%' % (100.0 * anyn / max(tot, 1))),
          ('Registries involved', f'Most common label: {top[1]} ({top[3]:,} projects)', f'{nreg}')]
    for i, (t, d, v) in enumerate(kp):
        ins.append((i, 'kpi', 'kpi', t, d, '', v, '', 0))
    o = 10
    for fam in ('integ', 'cobe', 'rate'):
        ins.append((o, 'fam', fam, FAM[fam][0], FAM[fam][1], '', '', '', 0))
        o += 1
        for f, name, note, n, regs in sorted([r for r in rows if r[0] == fam], key=lambda r: -r[3]):
            reg = ('Mostly ' + ' and '.join(r[0] for r in regs)) if regs and n else ''
            ins.append((o, 'lab', fam, name, note, reg, f'{n:,}', '%.1f%% of projects' % (100.0 * n / max(tot, 1)),
                        round(max(100.0 * n / nmax, 1.2), 1) if n else 0))
            o += 1
    con.executemany(f'INSERT INTO {TABLE} VALUES (?,?,?,?,?,?,?,?,?)', ins)
    con.commit()
    return tot, anyn


TPL = ('<div class="' + CLS + '"><div class="g">{{#each data}}<div class="r {{kind}} {{fam}}">'
       '<div class="t"><b>{{label}}</b><small>{{note}}</small><small class="rg">{{reg}}</small></div>'
       '<div class="v">{{val}}</div><div class="p"><i style="width:{{w}}%"></i><em>{{pct}}</em></div></div>{{/each}}</div>'
       '<div class="nt">A project can carry several labels, so the rows overlap and do not add up. Labels come from what each registry publishes; '
       'the W+ (Women\'s Livelihood) label is not in the registry data collected so far, so it is not shown.</div></div>')

CSS = """
.C .g{%FONT%;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;color:#1b1b1b}
.C .r{min-width:0}
.C .kpi{--a:#2F6B1E;--b:#9CC46A;position:relative;overflow:hidden;background:#fff;border:1px solid #e3e6dc;border-radius:14px;padding:16px 16px 14px;box-shadow:0 1px 2px rgba(31,42,20,.05);display:block}
.C .kpi:nth-child(2){--a:#245a78;--b:#6FA8C8}
.C .kpi:nth-child(3){--a:#9A6A12;--b:#E7C46B}
.C .kpi:before{content:'';position:absolute;left:0;top:0;right:0;height:4px;background:linear-gradient(90deg,var(--a),var(--b))}
.C .kpi .t b{display:block;font-size:11.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#5a6152;margin-bottom:6px}
.C .kpi .v{font-size:32px;line-height:1.1;font-weight:700;letter-spacing:-.5px;color:var(--a);margin:0 0 6px}
.C .kpi .t{display:flex;flex-direction:column}
.C .kpi .t{order:1}
.C .kpi .v{order:0}
.C .kpi{display:flex;flex-direction:column}
.C .kpi .t small{font-size:11.5px;line-height:1.4;color:#5f6659}
.C .kpi .p,.C .kpi .rg{display:none}
.C .fam{grid-column:1/-1;margin-top:10px;padding:0 4px 8px;border-bottom:1px solid #e6e9df}
.C .fam .t b{display:block;font-size:15px;font-weight:700;color:#1f2a14}
.C .fam .t small{display:block;font-size:12px;color:#7b8374;margin-top:2px}
.C .fam .v,.C .fam .p,.C .fam .rg{display:none}
.C .lab{grid-column:1/-1;display:grid;grid-template-columns:minmax(380px,2.4fr) 70px minmax(200px,1.5fr);gap:16px;align-items:center;padding:7px 10px;border-bottom:1px solid #f1f3ec;border-radius:8px;transition:background .12s}
.C .lab:hover{background:#f3f8ec}
.C .lab .t{min-width:0}
.C .lab .t b{display:block;font-size:13.5px;font-weight:600;color:#1f2a14}
.C .lab .t small{display:inline;font-size:11.5px;line-height:1.35;color:#7b8374}
.C .lab .t small.rg{color:#9aa190}
.C .lab .t small.rg:not(:empty):before{content:' \\00b7  '}
.C .lab .v{font-size:17px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;color:#1f2a14}
.C .lab .p{position:relative;height:22px;display:flex;align-items:center;gap:10px;min-width:0}
.C .lab .p i{display:block;height:12px;border-radius:7px;min-width:3px;flex:none;max-width:70%}
.C .lab .p em{font-style:normal;font-size:12px;color:#6b7363;white-space:nowrap}
.C .lab.integ .p i{background:linear-gradient(90deg,#245a78,#6FA8C8)}
.C .lab.cobe .p i{background:linear-gradient(90deg,#2C7A3D,#8CC06A)}
.C .lab.rate .p i{background:linear-gradient(90deg,#9A6A12,#E7C46B)}
.C .nt{%FONT%;font-size:11.5px;line-height:1.45;color:#7b8374;margin:12px 4px 0}
@media (max-width:900px){.C .g{grid-template-columns:1fr}.C .lab{grid-template-columns:1fr 60px}.C .lab .p{grid-column:1/-1}}
""".replace('%FONT%', FONT).replace('.C ', '.' + CLS + ' ')

HEAD = ("<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:12px 6px 4px\"><div style=\"font-size:15px;font-weight:700;color:#2C7A3D;margin-bottom:10px;\">"
        'Quality labels and certifications</div><div style="font-size:15.5px;font-weight:700;color:#0E1410;margin-bottom:3px">'
        'How many projects carry a quality label?</div><p style="margin:0 0 7px;font-size:14px;line-height:1.55;color:#1b1b1b;text-align:justify">'
        'Beyond the registry itself, projects can earn extra labels: integrity approval such as the ICVCM Core Carbon Principles (CCP), '
        'eligibility for airline offsetting (CORSIA) or Article 6 authorisation, and co-benefit labels such as CCB, SDG+ or Gold Standard Gender Responsive. '
        'The chart counts the projects worldwide that carry each one.</p></div>')

H_HEAD, H_CHART = 17, 171


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
        tot, anyn = build_table(con)
        con.close()
        LOG('table built: %d projects, %d with a label' % (tot, anyn))
        dbo = db.session.query(Database).filter(Database.database_name == 'C-GEM mastersheet').first()
        tbl = db.session.query(SqlaTable).filter(SqlaTable.table_name == TABLE).first()
        if tbl is None:
            tbl = SqlaTable(table_name=TABLE, schema='main', database=dbo)
            db.session.add(tbl)
            db.session.commit()
        tbl.fetch_metadata()
        db.session.commit()
        ref = db.session.query(Slice).filter(Slice.slice_name == 'Registry intelligence: the leading registries side by side').first()
        sl = db.session.query(Slice).filter(Slice.slice_name == CHART_NAME).first()
        if sl is None:
            sl = Slice(slice_name=CHART_NAME, viz_type='handlebars', datasource_type='table', datasource_id=tbl.id)
            db.session.add(sl)
        p = json.loads(ref.params) if ref is not None else {'viz_type': 'handlebars'}
        for k in ('slice_id', 'handlebarsTemplate', 'timeseries_limit_metric', 'orderby', 'order_desc', 'extra_form_data'):
            p.pop(k, None)
        p.update({'viz_type': 'handlebars', 'datasource': f'{tbl.id}__table', 'query_mode': 'raw', 'all_columns': COLS, 'groupby': [], 'metrics': [],
                  'adhoc_filters': [], 'row_limit': 100, 'order_by_cols': ['["ord", true]'], 'handlebarsTemplate': TPL, 'styleTemplate': CSS})
        sl.params = json.dumps(p)
        sl.viz_type = 'handlebars'
        sl.datasource_type = 'table'
        sl.datasource_id = tbl.id
        sl.query_context = None
        sl.description = 'Registry and Market tab: projects with quality labels and certifications'
        db.session.commit()
        LOG('chart id', sl.id)
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            if sl not in d.slices:
                d.slices.append(sl)
            pos = json.loads(d.position_json)
            if 'CHART-labels' in pos:
                pos['CHART-labels']['meta']['height'] = H_CHART
                d.position_json = json.dumps(pos)
                LOG('already in layout, height set to', H_CHART)
                continue
            tab = None
            for k, v in pos.items():
                if isinstance(v, dict) and v.get('type') == 'TAB' and (v.get('meta') or {}).get('text') == 'Registry & Market':
                    tab = k
            anchor = None
            if tab:
                for r in pos[tab]['children']:
                    if 'CHART-cp_regcards' in (pos.get(r, {}).get('children') or []):
                        anchor = r
            if not tab or anchor is None:
                LOG('Registry & Market layout differs, chart created but not placed')
                continue
            base = list(pos[tab]['parents']) + [tab]
            mid, mrow, crow, cid = 'MARKDOWN-labels', 'ROW-labels-m', 'ROW-labels-c', 'CHART-labels'
            pos[mid] = {'children': [], 'id': mid, 'meta': {'code': HEAD, 'height': H_HEAD, 'width': 12}, 'parents': base + [mrow], 'type': 'MARKDOWN'}
            pos[mrow] = {'children': [mid], 'id': mrow, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
            comp = copy.deepcopy(pos['CHART-cp_regcards'])
            comp['id'] = cid
            comp['parents'] = base + [crow]
            comp['meta'] = {'chartId': sl.id, 'sliceName': sl.slice_name, 'height': H_CHART, 'width': 12, 'uuid': str(sl.uuid)}
            pos[cid] = comp
            pos[crow] = {'children': [cid], 'id': crow, 'meta': {'background': 'BACKGROUND_TRANSPARENT'}, 'parents': base, 'type': 'ROW'}
            ch = pos[tab]['children']
            at = ch.index(anchor) + 1
            ch[at:at] = [mrow, crow]
            d.position_json = json.dumps(pos)
            LOG('placed in tab', tab, 'after', anchor)
        db.session.commit()
        LOG('done')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        LOG('skipped:', traceback.format_exc())
