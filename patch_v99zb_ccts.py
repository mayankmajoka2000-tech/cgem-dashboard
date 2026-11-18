"""v99zb: CCTS tab redesign: one hero banner (heading + button merged), five matching KPI cards, polished sector
and state tables (state list shows the top 5 and scrolls, all 24 states now included), and the plant table
replaced by a clean scrolling list. Edits Superset metadata only; logs to /app/cgem/chat/v99zb.log."""
import json
import os

LOGF = '/app/cgem/chat/v99zb.log'


def LOG(*a):
    msg = ' '.join(str(x) for x in a)
    print('v99zb:', msg)
    try:
        os.makedirs(os.path.dirname(LOGF), exist_ok=True)
        with open(LOGF, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


FONT = "Geist,Inter,'Segoe UI',Arial,sans-serif"

HERO = (
    '<div style="font-family:' + FONT + ';position:relative;overflow:hidden;border-radius:16px;padding:24px 28px;color:#1b1b1b;'
    'background:#fff;border:1px solid #e3e6dc;border-top:4px solid #2F6B1E;box-shadow:0 1px 3px rgba(31,42,20,.06)">'
    '<div style="font-size:11.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#2F6B1E;margin-bottom:8px">'
    "India's compliance market &middot; CCTS</div>"
    '<div style="font-size:25px;line-height:1.2;font-weight:700;letter-spacing:-.3px;color:#0E1410;margin-bottom:10px">'
    'Which Indian plants must cut emissions under CCTS?</div>'
    '<p style="margin:0 0 14px;max-width:880px;font-size:14px;line-height:1.6;color:#3d4536">'
    "Under the Carbon Credit Trading Scheme, plants in heavy industry get a target for emissions per tonne of product. "
    "Plants that beat it earn carbon credit certificates; plants that miss it must buy them. "
    "490 plants are covered so far, across seven sectors.</p>"
    '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">'
    '<span style="padding:5px 11px;border-radius:999px;font-size:12px;color:#265E30;background:#eef4e6;border:1px solid #d6e3c6">'
    'G.S.R. 739(E) &middot; 8 Oct 2025 &middot; 282 plants</span>'
    '<span style="padding:5px 11px;border-radius:999px;font-size:12px;color:#265E30;background:#eef4e6;border:1px solid #d6e3c6">'
    'G.S.R. 25(E) &middot; 13 Jan 2026 &middot; 208 plants</span>'
    '<span style="padding:5px 11px;border-radius:999px;font-size:12px;color:#265E30;background:#eef4e6;border:1px solid #d6e3c6">'
    'G.S.R. 794(E) &middot; 7 Sep 2026 &middot; refinery and textile amendment</span></div>'
    '<a href="/cgem-projects/ccts" target="_blank" style="display:inline-block;padding:10px 18px;border-radius:9px;background:#2C7A3D;'
    'color:#fff;font-size:14px;font-weight:700;text-decoration:none">Open the full CCTS list: search, filter, download &rarr;</a>'
    '<div style="margin-top:12px;font-size:11.5px;color:#7b8374">Source: Ministry of Environment notifications, Gazette of India.</div>'
    '</div>')

# ------------------------------------------------------------------ KPI cards (chart 37)
KC = 'cgx927636dc'
KPI_TPL = ('<div class="' + KC + '"><div class="mk">{{#each data}}<div class="kg">'
           '<div class="kc a1"><h4>Plants with a target</h4><b>{{a}}</b><p>Obligated entities that must meet an emission intensity target.</p></div>'
           '<div class="kc a2"><h4>Sectors covered</h4><b>{{b}}</b><p>Aluminium, cement, chlor-alkali, pulp and paper, refining, petrochemicals and textiles.</p></div>'
           '<div class="kc a3"><h4>States and union territories</h4><b>{{c}}</b><p>Where the obligated plants are located.</p></div>'
           '<div class="kc a4"><h4>Average cut by 2026-27</h4><b>{{d}}</b><p>Reduction in emissions per tonne of product, from the 2023-24 baseline.</p></div>'
           '<div class="kc a5"><h4>Plants that buy if they miss</h4><b>{{e}}</b><p>A plant that misses its target buys certificates; one that beats it can sell them.</p></div>'
           '</div>{{/each}}</div></div>')
KPI_CSS = """
.cgx927636dc .mk{font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;color:#1b1b1b;padding:2px}
.cgx927636dc .kg{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:stretch}
.cgx927636dc .kc{--a:#3F6A1C;--b:#9CC46A;position:relative;overflow:hidden;background:#fff;border:1px solid #e3e6dc;border-radius:14px;padding:18px 16px 14px;box-shadow:0 1px 2px rgba(31,42,20,.05);transition:transform .15s,box-shadow .15s}
.cgx927636dc .kc:hover{transform:translateY(-2px);box-shadow:0 10px 22px -10px rgba(31,42,20,.35)}
.cgx927636dc .kc:before{content:'';position:absolute;left:0;top:0;right:0;height:4px;background:linear-gradient(90deg,var(--a),var(--b))}
.cgx927636dc .kc:after{content:'';position:absolute;right:-30px;bottom:-40px;width:110px;height:110px;border-radius:50%;background:var(--a);opacity:.07}
.cgx927636dc .kc h4{margin:0 0 6px;font-size:11.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#5a6152}
.cgx927636dc .kc b{display:block;font-size:32px;line-height:1.1;font-weight:700;letter-spacing:-.5px;color:var(--a)}
.cgx927636dc .kc p{position:relative;z-index:1;margin:8px 0 0;font-size:11.5px;line-height:1.4;color:#5f6659}
.cgx927636dc .a1{--a:#2F6B1E;--b:#9CC46A}
.cgx927636dc .a2{--a:#245a78;--b:#6FA8C8}
.cgx927636dc .a3{--a:#0E7C86;--b:#6CC3C9}
.cgx927636dc .a4{--a:#8C3B1F;--b:#D9A441}
.cgx927636dc .a5{--a:#9A6A12;--b:#E7C46B}
@media (max-width:1100px){.cgx927636dc .kg{grid-template-columns:repeat(2,1fr)}}
"""


# ------------------------------------------------------------------ bar tables (charts 69 sector, 47 state)
def bar_css(c, cols, scroll=None, dots=False):
    s = """
.C .bl{font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;font-size:13px;color:#2b2b2b;background:#fff;border:1px solid #e6e9df;border-radius:14px;padding:6px 10px 10px;box-shadow:0 1px 2px rgba(31,42,20,.04)}
.C .bh,.C .br{display:grid;grid-template-columns:COLS;gap:14px;align-items:center}
.C .bh{position:sticky;top:0;z-index:2;background:#fff;font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#7a8270;padding:10px 10px 8px;border-bottom:1px solid #e9ece2}
.C .br{padding:10px 10px;border-bottom:1px solid #f1f3ec;border-radius:8px;transition:background .12s}
.C .br:hover{background:#f3f8ec}
.C .bn{display:flex;align-items:center;gap:10px;min-width:0}
.C .bn b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;color:#1f2a14}
.C .bn i{font-style:normal;flex:none;width:24px;height:24px;border-radius:50%;background:#eef2e8;color:#265E30;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}
.C .bv{display:flex;align-items:center;gap:8px;min-width:0}
.C .bv span{display:block;height:10px;border-radius:6px;min-width:3px;flex:none}
.C .bv b{font-size:12.5px;font-weight:600;white-space:nowrap;font-variant-numeric:tabular-nums}
.C .m1 span{background:linear-gradient(90deg,#2C7A3D,#8CC06A)}
.C .m2 span{background:linear-gradient(90deg,#B66F12,#E7B659)}
.C .m3 span{background:linear-gradient(90deg,#9E4521,#DE8A5A)}
.C .bk{font-size:11.5px;line-height:1.45;color:#7b8374;margin:10px 4px 0}
"""
    if dots:
        s += """.C .bn:before{content:'';flex:none;width:10px;height:10px;border-radius:50%;background:var(--c,#2C7A3D)}
.C .sc .br:nth-child(7n+1){--c:#2F6B1E}.C .sc .br:nth-child(7n+2){--c:#245a78}.C .sc .br:nth-child(7n+3){--c:#0E7C86}
.C .sc .br:nth-child(7n+4){--c:#8C3B1F}.C .sc .br:nth-child(7n+5){--c:#9A6A12}.C .sc .br:nth-child(7n+6){--c:#6A4C93}.C .sc .br:nth-child(7n+7){--c:#4B6B7A}
"""
    if scroll:
        s += (".C .sc{max-height:%dpx;overflow-y:auto;padding-right:4px}.C .sc::-webkit-scrollbar{width:6px}"
              ".C .sc::-webkit-scrollbar-thumb{background:#c9d2bb;border-radius:3px}\n" % scroll)
    return s.replace('.C ', '.' + c + ' ').replace('COLS', cols)


SEC_C = 'cgx1af1c610'
SEC_TPL = ('<div class="' + SEC_C + '"><div class="bl"><div class="bh"><span>Sector</span><span>Plants</span>'
           '<span>Average cut by 2026-27</span><span>Product output a year (2023-24)</span></div><div class="sc">'
           '{{#each data}}<div class="br"><div class="bn"><b>{{nm}}</b></div>'
           '<div class="bv m1"><span style="width:calc({{w0}}% * .62)"></span><b>{{t0}}</b></div>'
           '<div class="bv m2"><span style="width:calc({{w1}}% * .62)"></span><b>{{t1}}</b></div>'
           '<div class="bv m3"><span style="width:calc({{w2}}% * .62)"></span><b>{{t2}}</b></div></div>{{/each}}</div>'
           '<div class="bk">Targets cut emissions per tonne of product (emission intensity), not total emissions. Compare plants within one sector: '
           'each sector has its own unit of product (refineries: thousand barrels of crude processed). Refineries and textile plants have no 2025-26 '
           'target after the September 2026 amendment; their first target year is 2026-27.</div></div></div>')
SEC_CSS = bar_css(SEC_C, '220px 1fr 1fr 1fr', None, True)

ST_C = 'cgx0f77ce10'
ST_TPL = ('<div class="' + ST_C + '"><div class="bl"><div class="bh"><span>State</span><span>Plants</span><span>Sectors</span>'
          '<span>Average cut by 2026-27</span></div><div class="sc">'
          '{{#each data}}<div class="br"><div class="bn"><i>{{rid}}</i><b>{{nm}}</b></div>'
          '<div class="bv m1"><span style="width:calc({{w0}}% * .62)"></span><b>{{t0}}</b></div>'
          '<div class="bv m2"><span style="width:calc({{w1}}% * .62)"></span><b>{{t1}}</b></div>'
          '<div class="bv m3"><span style="width:calc({{w2}}% * .62)"></span><b>{{t2}}</b></div></div>{{/each}}</div>'
          '<div class="bk">Showing the top 5; scroll inside the list for the rest. These plants either cut their emissions per tonne or buy '
          'carbon credit certificates: they are the first buyers in the compliance market.</div></div></div>')
ST_CSS = bar_css(ST_C, "220px 1fr 1fr 1fr", 228)

# ------------------------------------------------------------------ plant list (chart 12 becomes a handlebars list)
PL_C = 'cgxcc7512'
PL_TPL = ('<div class="' + PL_C + '"><div class="bl"><div class="bh"><span>#</span><span>Plant</span><span>Sector</span><span>State</span>'
          '<span>Baseline</span><span>Target 2026-27</span><span>Cut</span></div><div class="sc">'
          '{{#each data}}<div class="br"><i>{{rid}}</i><div class="pn"><b title="{{nm}}">{{nm}}</b><small>{{sub}}</small></div>'
          '<span>{{sc}}</span><span>{{st}}</span><span class="nu">{{bs}}</span><span class="nu">{{tg}}</span>'
          '<div class="bv"><span style="width:calc({{w}}% * .6)"></span><b>{{cut}}</b></div></div>{{/each}}</div>'
          '<div class="bk">The 490 plants ranked by the cut they must make by 2026-27 (per tonne of product, against the 2023-24 baseline). '
          'Showing the top 5; scroll inside the list for the rest. Use the full CCTS list above to search, filter and download.</div></div></div>')
PL_CSS = """
.C .bl{font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;font-size:13px;color:#2b2b2b;background:#fff;border:1px solid #e6e9df;border-radius:14px;padding:6px 10px 10px;box-shadow:0 1px 2px rgba(31,42,20,.04)}
.C .bh,.C .br{display:grid;grid-template-columns:34px 2.6fr 1.1fr 1.1fr .8fr .9fr 1.5fr;gap:12px;align-items:center}
.C .bh{position:sticky;top:0;z-index:2;background:#fff;font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#7a8270;padding:10px 10px 8px;border-bottom:1px solid #e9ece2}
.C .br{padding:9px 10px;border-bottom:1px solid #f1f3ec;border-radius:8px;transition:background .12s}
.C .br:hover{background:#f3f8ec}
.C .br>i{font-style:normal;width:24px;height:24px;border-radius:50%;background:#eef2e8;color:#265E30;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}
.C .pn{min-width:0}
.C .pn b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;color:#1f2a14}
.C .pn small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:11px;color:#8a9281}
.C .br>span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#3d4536}
.C .nu{font-variant-numeric:tabular-nums}
.C .bv{display:flex;align-items:center;gap:8px;min-width:0}
.C .bv span{display:block;height:10px;border-radius:6px;min-width:3px;flex:none;background:linear-gradient(90deg,#8C3B1F,#DE8A5A)}
.C .bv b{font-size:12.5px;font-weight:700;color:#8C3B1F;white-space:nowrap;font-variant-numeric:tabular-nums}
.C .sc{max-height:250px;overflow-y:auto;padding-right:4px}.C .sc::-webkit-scrollbar{width:6px}.C .sc::-webkit-scrollbar-thumb{background:#c9d2bb;border-radius:3px}
.C .bk{font-size:11.5px;line-height:1.45;color:#7b8374;margin:10px 4px 0}
""".replace('.C ', '.' + PL_C + ' ')


def met(label, sql):
    return {'expressionType': 'SQL', 'sqlExpression': sql, 'label': label, 'hasCustomLabel': True, 'optionName': 'metric_' + label}


def num(col, fmt):
    return "CASE WHEN MAX(%s) IS NULL THEN 'n/a' ELSE printf('%s', MAX(%s)) END" % (col, fmt, col)


PL_METRICS = [
    met('rid', 'ROW_NUMBER() OVER (ORDER BY MAX(reduction_pct) DESC, MAX(company))'),
    met('nm', 'MAX(company)'), met('sub', 'MAX(COALESCE(sub_sector, sector))'),
    met('sc', 'MAX(sector)'), met('st', 'MAX(state)'),
    met('bs', num('baseline_gei', '%.2f')), met('tg', num('target_2026_27', '%.2f')),
    met('cut', num('reduction_pct', '%.1f') .replace("printf('%.1f'", "printf('%.1f%%'")),
    met('w', 'ROUND(100.0 * COALESCE(MAX(reduction_pct), 0) / NULLIF(MAX(MAX(reduction_pct)) OVER (), 0), 1)'),
]

H_HERO, H_KPI, H_PLANTS = 38, 22, 46   # frame heights in 8px units (tuned after a screenshot)
H_SEC, H_STATE = 52, 44


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard

        def sl(name):
            return db.session.query(Slice).filter(Slice.slice_name == name).first()

        s37 = sl("India's carbon market (CCTS): companies with emission targets")
        s69 = sl('CCTS targets by sector')
        s47 = sl('CCTS plants by state')
        s12 = sl('Every CCTS plant with its baseline and targets')
        if not all((s37, s69, s47, s12)):
            LOG('a chart is missing, nothing changed')
            return
        ids = {}
        # KPI
        p = json.loads(s37.params)
        if KC in p.get('handlebarsTemplate', ''):
            p['handlebarsTemplate'], p['styleTemplate'] = KPI_TPL, KPI_CSS
            s37.params = json.dumps(p)
            s37.query_context = None
            LOG('kpi cards restyled')
        # sector
        p = json.loads(s69.params)
        if SEC_C in p.get('handlebarsTemplate', ''):
            p['handlebarsTemplate'], p['styleTemplate'] = SEC_TPL, SEC_CSS
            s69.params = json.dumps(p)
            s69.query_context = None
            LOG('sector table restyled')
        # state: all states, top 5 visible, rest scrolls
        p = json.loads(s47.params)
        if ST_C in p.get('handlebarsTemplate', ''):
            p['handlebarsTemplate'], p['styleTemplate'] = ST_TPL, ST_CSS
            p['row_limit'] = 60
            s47.params = json.dumps(p)
            s47.query_context = None
            LOG('state table restyled, row_limit 60')
        # plant list
        p = json.loads(s12.params)
        if p.get('viz_type') != 'handlebars':
            q = {'query_mode': 'aggregate', 'groupby': [{'expressionType': 'SQL', 'sqlExpression': 'reg_no', 'label': 'g'}],
                 'metrics': PL_METRICS, 'row_limit': 600, 'adhoc_filters': [], 'timeseries_limit_metric': met('o', 'MAX(COALESCE(reduction_pct, -1))'), 'order_desc': True,
                 'handlebarsTemplate': PL_TPL, 'styleTemplate': PL_CSS, 'viz_type': 'handlebars',
                 'datasource': p.get('datasource'), 'color_scheme': p.get('color_scheme', 'cgemEarth'), 'annotation_layers': []}
            s12.params = json.dumps(q)
            s12.viz_type = 'handlebars'
            s12.query_context = None
            LOG('plant list converted to handlebars')
        ids = {'hero': None, 37: s37.id, 69: s69.id, 47: s47.id, 12: s12.id}
        heights = {s37.id: H_KPI, s69.id: H_SEC, s47.id: H_STATE, s12.id: H_PLANTS}
        for d in db.session.query(Dashboard).filter(Dashboard.slug == 'cgem').all():
            pos = json.loads(d.position_json)
            md = pos.get('MARKDOWN-1-14-0')
            if md is None or 'TAB-ccts' not in pos:
                LOG('ccts layout differs, layout untouched')
                continue
            md['meta']['code'] = HERO
            md['meta']['height'] = H_HERO
            # the button now lives in the banner
            if 'ROW-ccts-btn' in pos:
                for k in ('ROW-ccts-btn', 'MARKDOWN-ccts-btn'):
                    pos.pop(k, None)
                ch = pos['TAB-ccts']['children']
                if 'ROW-ccts-btn' in ch:
                    ch.remove('ROW-ccts-btn')
                LOG('separate button row removed')
            for v in pos.values():
                if isinstance(v, dict) and v.get('type') == 'CHART':
                    cid = (v.get('meta') or {}).get('chartId')
                    if cid in heights:
                        v['meta']['height'] = heights[cid]
            d.position_json = json.dumps(pos)
            LOG('layout updated')
        db.session.commit()
        LOG('done')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        LOG('skipped:', traceback.format_exc())
