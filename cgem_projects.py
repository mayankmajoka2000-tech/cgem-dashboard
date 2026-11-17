"""C-GEM project workspace (/cgem-projects/): find a project, open its full profile, compare projects or countries side by side,
keep a shortlist and export it to Excel or PDF, follow projects on a watchlist with e-mail alerts, and see where every number
comes from. Also serves the EU link page at /eu-link and sends phones to a page made for small screens.

Loaded by superset_config.py. Reads cgem.db; the shortlist and watchlist live in cgem_admin.db (kept across updates).
"""
import datetime as dt
import html
import io
import json
import os
import re
import secrets
import sqlite3
from urllib.parse import quote, urlencode

from flask import Blueprint, Response, redirect, request, send_file, session

import cgem_mail as M
import cgem_sources
import cgem_watch

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint('cgem_projects', __name__)
E = lambda s: html.escape('' if s is None else str(s))
B = '/cgem-projects'
ONLINE = os.environ.get('CGEM_ONLINE') == '1'

COLS = ['project_key', 'registry', 'project_id', 'project_name', 'country', 'state', 'district', 'sector', 'sub_sector', 'project_type',
        'reduction_removal', 'registry_status', 'voluntary_status', 'methodology', 'developer', 'verifier', 'screening', 'flags',
        'annual_reductions', 'credits_issued', 'credits_retired', 'buffer_credits', 'unretired_supply', 'project_area_ha',
        'registration_date', 'first_issuance', 'latest_issuance', 'crediting_start', 'crediting_end', 'issuance_recency',
        'crediting_ends_in_12_months', 'icvcm_programme', 'icvcm_methodology', 'icvcm_methodology_detail', 'corsia_detail',
        'registry_page', 'pdd_link', 'source_link', 'has_review_flag', 'article_6_4_candidate', 'retired_issued', 'risk_signals',
        'risk_signal_count', 'certifications', 'sdgs_raw', 'project_completeness', 'missing_fields', 'is_india', 'price_category',
        'price_low_usd', 'price_mid_usd', 'price_high_usd', 'price_band', 'price_basis', 'price_confidence', 'quality_score',
        'quality_grade', 'quality_why', 'q_programme', 'q_method', 'q_type', 'q_record', 'q_transparency', 'q_risk', 'corsia_phase1',
        'article6_status', 'licensed_rating', 'licensed_price', 'credit_labels', 'model_credit_type', 'model_price_usd', 'model_p10_usd',
        'model_p90_usd', 'model_confidence', 'model_integrity', 'model_integrity_band', 'model_demand_score', 'model_sales_value_usd',
        'model_registry_factor', 'model_band', 'model_version', 'model_ccp', 'model_explain', 'model_price_online']


# ------------------------------------------------------------------ data and people
def data():
    c = sqlite3.connect(f'file:{M.DB}?mode=ro', uri=True, timeout=20)
    c.row_factory = sqlite3.Row
    return c


def get(c, key):
    have = {r[1] for r in c.execute('PRAGMA table_info(projects)')}
    cols = [x for x in COLS if x in have]
    r = c.execute(f'SELECT {", ".join(cols)} FROM projects WHERE project_key = ?', (key,)).fetchone()
    return dict(r) if r else None


def user():
    """(owner id, display name, signed in?) - the Superset user, or a private id for this browser"""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return 'user:' + current_user.username, current_user.username, True
    except Exception:
        pass
    g = session.get('cgem_guest')
    if not g:
        g = secrets.token_hex(8)
        session['cgem_guest'] = g
    return 'guest:' + g, 'this browser', False


def store():
    c = M.con()
    c.execute('CREATE TABLE IF NOT EXISTS shortlist (owner TEXT, project_key TEXT, added TEXT, note TEXT, PRIMARY KEY (owner, project_key))')
    return c


def shortlist_keys(owner):
    s = store()
    k = [r[0] for r in s.execute('SELECT project_key FROM shortlist WHERE owner = ? ORDER BY added', (owner,))]
    s.close()
    return k


def csrf():
    try:
        from flask_wtf.csrf import generate_csrf
        return f'<input type="hidden" name="csrf_token" value="{E(generate_csrf())}">'
    except Exception:
        return ''


# ------------------------------------------------------------------ formatting
def n(v, d=0):
    try:
        if v is None or v == '':
            return '-'
        return f'{float(v):,.{d}f}'
    except (TypeError, ValueError):
        return E(v)


def big(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '-'
    for lim, suf in ((1e9, ' bn'), (1e6, ' M'), (1e3, ' k')):
        if abs(v) >= lim:
            return f'{v / lim:,.1f}{suf}'
    return f'{v:,.0f}'


def day(v):
    if not v:
        return '-'
    s = str(v)[:10]
    try:
        return dt.date.fromisoformat(s).strftime('%d %b %Y')
    except ValueError:
        return E(v)


GRADE = {'A': 'ok', 'B': 'ok', 'C': 'warn', 'D': 'bad'}


def grade_pill(g, s=None):
    if not g:
        return '<span class="pill oth">Not graded</span>'
    return f'<span class="pill {GRADE.get(g, "oth")}">Grade {E(g)}{f" · {n(s)}/100" if s is not None else ""}</span>'


def plink(key, text=None):
    return f'<a href="{B}/p?key={quote(key, safe="")}">{E(text or key)}</a>'


def link(u, text):
    if not u or not str(u).startswith('http'):
        return '<span class="mut">not available</span>'
    return f'<a href="{E(u)}" target="_blank" rel="noopener">{E(text)}</a>'


# ------------------------------------------------------------------ page frame
CSS = '''
:root{--leaf:#2C7A3D;--leafd:#265E30;--harvest:#C98A1F;--clay:#B85829;--ink:#0E1410;--paper:#F6F7F2;--line:#e3e6dc;--mut:#5c6358;--card:#fff;--soft:#D8ECDC}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--ink:#EEF1EA;--paper:#121612;--line:#2b322b;--mut:#a5ad9f;--card:#1a1f1a;--soft:#22372a}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 Geist,Inter,"Segoe UI",Arial,sans-serif}
a{color:var(--leaf)}header{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.top{max-width:1240px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{font-weight:700;letter-spacing:.02em;white-space:nowrap}.brand span{color:var(--leaf)}
nav{display:flex;gap:2px;flex-wrap:wrap;margin-left:auto}nav a{padding:6px 10px;border-radius:8px;text-decoration:none;color:var(--ink);font-size:13px;white-space:nowrap}
nav a.on,nav a:hover{background:var(--soft);color:var(--leafd)}
main{max-width:1240px;margin:0 auto;padding:22px 16px 70px}
h1{font:600 28px/1.2 Newsreader,Georgia,serif;margin:0 0 6px}h2{font:600 17px/1.3 Geist,Inter,sans-serif;margin:0 0 12px}
h3{font:600 14px/1.3 Geist,Inter,sans-serif;margin:14px 0 8px}
.lead{color:var(--mut);margin:0 0 18px;max-width:820px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:0 0 16px;min-width:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:0 0 16px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.two>.card{margin:0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.tile .k{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--mut)}
.tile .v{font:700 22px/1.2 "Geist Mono",ui-monospace,Menlo,monospace;margin-top:4px;overflow-wrap:anywhere}.tile .s{font-size:12px;color:var(--mut)}
label{display:block;font-weight:600;font-size:12px;margin:0 0 4px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
input[type=text],input[type=email],input[type=search],select{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.filters{display:grid;grid-template-columns:2fr repeat(4,1fr) auto;gap:10px;align-items:end}
button,.btn{background:var(--leaf);color:#fff;border:0;border-radius:8px;padding:9px 14px;font:600 13px/1.2 inherit;font-family:inherit;cursor:pointer;
text-decoration:none;display:inline-block;white-space:nowrap}button:hover,.btn:hover{background:var(--leafd)}
button.sec,.btn.sec{background:transparent;color:var(--ink);border:1px solid var(--line)}button.bad,.btn.bad{background:var(--clay)}
.btns{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.msg{border-radius:10px;padding:10px 14px;margin:0 0 16px;border:1px solid}.msg.ok{background:#e9f4ec;border-color:#bcdcc5;color:#1f4f29}
.msg.warn{background:#fbf4e6;border-color:#ecd3a8;color:#6b4708}.msg.bad{background:#fbefe8;border-color:#efcdb9;color:#8a3b17}
table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);
padding:8px;border-bottom:1px solid var(--line);vertical-align:bottom}td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
td.n,th.n{text-align:right;font-family:"Geist Mono",ui-monospace,monospace;white-space:nowrap}.wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.kv td:first-child{color:var(--mut);width:38%}table.cmp td:first-child{color:var(--mut);width:22%;font-weight:600}table.cmp th{text-transform:none;letter-spacing:0;font-size:13px;color:var(--ink)}
.pill{display:inline-block;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:700;white-space:nowrap}.pill.ok{background:#D8ECDC;color:#265E30}
.pill.warn{background:#f6ead2;color:#8a5d10}.pill.bad{background:#f6e2d6;color:#B85829}.pill.oth{background:#e9ebe6;color:#555}
.mut{color:var(--mut)}.small{font-size:12px}.flag{border-left:3px solid var(--clay);padding:6px 10px;margin:0 0 6px;background:rgba(184,88,41,.06);border-radius:0 6px 6px 0}
.flag.ok{border-color:var(--leaf);background:rgba(44,122,61,.06)}.flag.warn{border-color:var(--harvest);background:rgba(201,138,31,.07)}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--leaf)}
.qrow{display:grid;grid-template-columns:190px 1fr 60px;gap:10px;align-items:center;margin:0 0 8px;font-size:13px}
.src{font-size:12px;color:var(--mut);border-top:1px dashed var(--line);margin-top:12px;padding-top:8px}
.chips a{display:inline-block;margin:0 6px 6px 0;padding:4px 10px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-size:12px}
svg text{font-family:"Geist Mono",ui-monospace,monospace}
@media (max-width:860px){.filters{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}.qrow{grid-template-columns:120px 1fr 52px}
 nav{margin-left:0;overflow-x:auto;flex-wrap:nowrap;width:100%}h1{font-size:23px}.hide-s{display:none}main{padding:16px 12px 60px}}
@media print{header,.noprint{display:none}body{background:#fff}.card{break-inside:avoid}}
'''


def frame(title, body, active='', lead=''):
    owner, name, signed = user()
    try:
        nsl = len(shortlist_keys(owner))
    except Exception:
        nsl = 0
    links = [('find', f'{B}/', 'Find projects'), ('compare', f'{B}/compare', 'Compare'), ('countries', f'{B}/countries', 'Countries'),
             ('shortlist', f'{B}/shortlist', f'Shortlist ({nsl})'), ('watch', f'{B}/watchlist', 'Watchlist'),
             ('ccts', f'{B}/ccts', 'India CCTS'), ('sources', f'{B}/sources', 'Data sources'), ('eu', '/eu-link', 'EU link'),
             ('dash', '/superset/dashboard/cgem/?desktop=1', 'Full dashboard')]
    nav = ''.join(f'<a class="{"on" if k == active else ""}" href="{u}">{E(t)}</a>' for k, u, t in links)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{E(title)} | C-GEM</title><link rel="icon" href="/cgem-static/cgem_bot_96.png"><style>{CSS}</style></head>'
            f'<body><header><div class="top"><div class="brand"><span>C-GEM</span> Projects</div><nav>{nav}</nav></div></header>'
            f'<main><h1>{E(title)}</h1>{f"<p class=lead>{lead}</p>" if lead else ""}{body}</main></body></html>')


def msg(text, kind='ok'):
    return f'<div class="msg {kind}">{text}</div>'


# ------------------------------------------------------------------ phones: the dashboard is made for big screens
MOBILE = re.compile(r'iPhone|Android.+Mobile|Mobile Safari|Windows Phone|iPod', re.I)


@bp.before_app_request
def _phones():
    p = request.path
    if p.startswith('/superset/dashboard/') and request.method == 'GET' and MOBILE.search(request.headers.get('User-Agent', '')) \
            and request.args.get('desktop') != '1' and request.cookies.get('cgem_desktop') != '1':
        return redirect(f'{B}/?phone=1')
    if p.startswith('/superset/dashboard/') and request.args.get('desktop') == '1':
        session['cgem_desktop'] = 1
    return None


@bp.after_app_request
def _desktop_cookie(r):
    if request.args.get('desktop') == '1' and request.path.startswith('/superset/dashboard/'):
        r.set_cookie('cgem_desktop', '1', max_age=30 * 86400, samesite='Lax')
    return r


# ------------------------------------------------------------------ find projects
def _opts(c, col, where='1=1', limit=400):
    return [r[0] for r in c.execute(f'SELECT {col} FROM projects WHERE {col} IS NOT NULL AND length({col}) > 0 AND {where} '
                                    f'GROUP BY {col} ORDER BY COUNT(*) DESC LIMIT {limit}')]


def _select(name, values, cur, first='All'):
    o = ''.join(f'<option value="{E(v)}"{" selected" if v == cur else ""}>{E(v)}</option>' for v in values)
    return f'<select name="{name}"><option value="">{first}</option>{o}</select>'


def _search(c, a, limit=100):
    where, args = ['1=1'], []
    q = (a.get('q') or '').strip()
    if q:
        where.append('(project_name LIKE ? OR project_id LIKE ? OR developer LIKE ? OR methodology LIKE ?)')
        args += [f'%{q}%'] * 4
    for f, col in (('country', 'country'), ('registry', 'registry'), ('type', 'price_category'), ('grade', 'quality_grade')):
        if a.get(f):
            where.append(f'{col} = ?')
            args.append(a.get(f))
    if a.get('india') == '1':
        where.append("is_india = 'India'")
    order = {'issued': 'credits_issued DESC', 'retired': 'credits_retired DESC', 'score': 'quality_score DESC',
             'supply': 'unretired_supply DESC', 'name': 'project_name'}.get(a.get('sort') or 'issued', 'credits_issued DESC')
    sql = (f'SELECT project_key, registry, project_id, project_name, country, price_category, quality_grade, quality_score, '
           f'credits_issued, credits_retired, price_band, corsia_phase1, model_price_usd, model_p10_usd, model_p90_usd FROM projects WHERE {" AND ".join(where)} '
           f'ORDER BY {order} NULLS LAST LIMIT {int(limit)}')
    total = c.execute(f'SELECT COUNT(*) FROM projects WHERE {" AND ".join(where)}', args).fetchone()[0]
    return c.execute(sql, args).fetchall(), total


def _price_cell(r):
    keys = r.keys() if hasattr(r, 'keys') else []
    if 'model_price_usd' in keys and r['model_price_usd'] is not None:
        return (f'<b>US${r["model_price_usd"]:,.2f}</b> <span class="mut">model, P10-P90 {r["model_p10_usd"]:,.2f}-{r["model_p90_usd"]:,.2f}</span>')
    return E(r['price_band'] or '-')


def _result_table(rows, owner, checkboxes=True):
    sl = set(shortlist_keys(owner))
    tr = []
    for r in rows:
        cb = (f'<td><input type="checkbox" name="k" value="{E(r["project_key"])}" aria-label="select"></td>' if checkboxes else '')
        tr.append(f'<tr>{cb}<td>{plink(r["project_key"], r["project_name"] or r["project_id"])}'
                  f'<div class="small mut">{E(r["registry"])} · {E(r["project_id"])}{" · on shortlist" if r["project_key"] in sl else ""}</div></td>'
                  f'<td>{E(r["country"])}</td><td class="hide-s">{E(r["price_category"] or "")}</td>'
                  f'<td>{grade_pill(r["quality_grade"], r["quality_score"])}</td><td class="n">{big(r["credits_issued"])}</td>'
                  f'<td class="n hide-s">{big(r["credits_retired"])}</td><td class="hide-s small">{_price_cell(r)}</td></tr>')
    head = ('<th></th>' if checkboxes else '') + ('<th>Project</th><th>Country</th><th class="hide-s">Type</th><th>Quality</th>'
                                                  '<th class="n">Issued</th><th class="n hide-s">Retired</th><th class="hide-s">Price (US$ per credit)</th>')
    return f'<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(tr)}</tbody></table></div>'


@bp.route(f'{B}/')
def find():
    owner, name, signed = user()
    c = data()
    a = request.args
    rows, total = _search(c, a)
    top = ''
    if a.get('phone') == '1' or not a:
        t = c.execute('SELECT COUNT(*), SUM(credits_issued), SUM(credits_retired), COUNT(DISTINCT country), COUNT(DISTINCT registry), '
                      "SUM(CASE WHEN is_india = 'India' THEN 1 ELSE 0 END) FROM projects").fetchone()
        top = (f'<div class="grid"><div class="tile"><div class="k">Projects</div><div class="v">{n(t[0])}</div><div class="s">{n(t[4])} registries</div></div>'
               f'<div class="tile"><div class="k">Credits issued</div><div class="v">{big(t[1])}</div><div class="s">{big(t[2])} retired</div></div>'
               f'<div class="tile"><div class="k">Countries</div><div class="v">{n(t[3])}</div><div class="s">{n(t[5])} projects in India</div></div></div>')
        if a.get('phone') == '1':
            top = msg('This page is made for phones. The full dashboard has 160 charts and works best on a laptop: '
                      '<a href="/superset/dashboard/cgem/?desktop=1">open it anyway</a>.', 'warn') + top
    sort = a.get('sort') or 'issued'
    form = (f'<form class="card noprint" method="get" action="{B}/"><div class="filters">'
            f'<div><label>Search</label><input type="search" name="q" value="{E(a.get("q", ""))}" placeholder="Name, ID, developer or method"></div>'
            f'<div><label>Country</label>{_select("country", _opts(c, "country"), a.get("country"))}</div>'
            f'<div><label>Registry</label>{_select("registry", _opts(c, "registry"), a.get("registry"))}</div>'
            f'<div><label>Type</label>{_select("type", _opts(c, "price_category"), a.get("type"))}</div>'
            f'<div><label>Grade</label>{_select("grade", ["A", "B", "C", "D"], a.get("grade"))}</div>'
            f'<div class="btns"><button>Find</button></div></div>'
            f'<div class="btns small" style="margin-top:10px"><label style="margin:0">Sort</label>'
            + ''.join(f'<a class="btn sec" style="padding:4px 10px{";background:var(--soft)" if sort == k else ""}" href="{B}/?{urlencode({**a.to_dict(), "sort": k})}">{t}</a>'
                      for k, t in (('issued', 'Most issued'), ('retired', 'Most retired'), ('supply', 'Most unsold'), ('score', 'Best score'), ('name', 'Name')))
            + f'<label style="margin:0 0 0 10px"><input type="checkbox" name="india" value="1"{" checked" if a.get("india") == "1" else ""} onchange="this.form.submit()"> India only</label></div></form>')
    acts = (f'<div class="btns noprint" style="margin:0 0 10px"><span class="small mut">With the ticked projects:</span>'
            f'<button formaction="{B}/compare" formmethod="get">Compare (2 or 3)</button>'
            f'<button class="sec" formaction="{B}/shortlist/add" formmethod="post">Add to shortlist</button>'
            f'<button class="sec" formaction="{B}/watch/add" formmethod="post">Watch for changes</button></div>')
    body = (top + form + f'<form class="card" method="post">{csrf()}<h2>{n(total)} projects{" (first 100 shown)" if total > 100 else ""}</h2>'
            + acts + _result_table(rows, owner) + '</form>')
    c.close()
    return frame('Find a project', body, 'find', 'Search every project in C-GEM. Open a project for its full profile, tick two or three to compare '
                 'them, put them on your shortlist for an Excel or PDF report, or watch them for new issuance and retirements.')


# ------------------------------------------------------------------ project profile
def _svg_vintages(vs):
    if not vs:
        return '<p class="mut">No issuance by vintage recorded for this project.</p>'
    w, h, pad = 760, 190, 34
    mx = max(v for _, v in vs) or 1
    bw = (w - pad - 10) / len(vs)
    bars = []
    for i, (y, v) in enumerate(vs):
        bh = (h - 44) * v / mx
        x = pad + i * bw
        bars.append(f'<rect x="{x + 2:.1f}" y="{h - 24 - bh:.1f}" width="{max(bw - 4, 2):.1f}" height="{bh:.1f}" rx="2" fill="#2C7A3D">'
                    f'<title>{y}: {v:,.0f} credits</title></rect>')
        if len(vs) <= 16 or i % max(1, len(vs) // 12) == 0:
            bars.append(f'<text x="{x + bw / 2:.1f}" y="{h - 8}" font-size="10" text-anchor="middle" fill="currentColor" opacity=".65">{y}</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Credits issued by vintage year" style="max-height:220px">'
            f'<text x="{pad}" y="12" font-size="10" fill="currentColor" opacity=".65">max {big(mx)}</text>'
            f'<line x1="{pad}" x2="{w - 8}" y1="{h - 24}" y2="{h - 24}" stroke="currentColor" opacity=".25"/>{"".join(bars)}</svg>')


def _model_card(p):
    return ''   # C-GEM pricing model is not published online
    if p.get('model_price_usd') is None:
        if p.get('country') == 'India':
            return ('<div class="card" style="margin-top:16px"><h2>C-GEM India price model</h2><p class="mut">The model has no price for this '
                    'project yet. <a href="/price-model/calculator.html#price">Price it in the calculator</a>.</p></div>')
        return ''
    lo, mid, hi = p['model_p10_usd'], p['model_price_usd'], p['model_p90_usd']
    span = max(hi or 0, (p.get('price_high_usd') or 0)) or 1
    def mark(v, col):
        return f'<i style="position:absolute;left:{100 * v / span:.1f}%;top:-3px;width:3px;height:14px;background:{col}"></i>'
    scale = (f'<div style="position:relative;height:8px;background:var(--line);border-radius:4px;margin:18px 0 6px">'
             f'<span style="position:absolute;left:{100 * lo / span:.1f}%;width:{100 * (hi - lo) / span:.1f}%;height:8px;background:#9ccaa6;border-radius:4px"></span>'
             f'{mark(mid, "#265E30")}</div><div class="small mut" style="display:flex;justify-content:space-between"><span>US$0</span>'
             f'<span>P10 {lo:,.2f} · model {mid:,.2f} · P90 {hi:,.2f}</span><span>US${span:,.0f}</span></div>')
    rows = [('Credit type in the model', p.get('model_credit_type')), ('Model price (US$ per credit)', f'{mid:,.2f}'),
            ('Range (P10 to P90)', f'{lo:,.2f} to {hi:,.2f}'), ('Confidence for this type', p.get('model_confidence')),
            ('Registry factor', n(p.get('model_registry_factor'), 2)),
            ('Integrity score (model)', f'{n(p.get("model_integrity"))}/100, band {p.get("model_integrity_band") or "-"}'),
            ('Demand score', n(p.get('model_demand_score'), 1)), ('Expected sales value a year', f'US${n(p.get("model_sales_value_usd"))}'),
            ('EOM offer band for the type (for comparison)', p.get('price_band') or '-')]
    tab = '<table class="kv">' + ''.join(f'<tr><td>{E(a)}</td><td>{E(b) if b not in (None, "") else "-"}</td></tr>' for a, b in rows) + '</table>'
    wf = ''
    try:
        steps = json.loads(p.get('model_explain') or '[]')
    except ValueError:
        steps = []
    if steps:
        top = max(s_[2] for s_ in steps) or 1
        prev = 0.0
        items = []
        for i, (lab, mlt, run) in enumerate(steps):
            lo_, hi_ = (0, run) if i == 0 else (min(prev, run), max(prev, run))
            col = '#2C7A3D' if i == 0 else ('#6FA779' if run >= prev else '#B85829')
            eff = 'starting price' if i == 0 else (f'x{mlt:,.2f}  ({"+" if run >= prev else "-"}US${abs(run - prev):,.2f})')
            items.append(f'<div class="qrow" style="grid-template-columns:minmax(150px,280px) 1fr 150px"><span class="small">{E(lab)}</span>'
                         f'<div style="position:relative;height:14px;background:var(--line);border-radius:3px">'
                         f'<i style="position:absolute;left:{100 * lo_ / top:.1f}%;width:{max(100 * (hi_ - lo_) / top, .6):.1f}%;height:14px;background:{col};border-radius:3px"></i></div>'
                         f'<span class="small" style="text-align:right">{E(eff)}</span></div>')
            prev = run
        wf = (f'<h3>Why this price: each factor of the model</h3>{"".join(items)}'
              f'<div class="small mut">Ends at US${steps[-1][2]:,.2f}. Green raises the price, clay lowers it.</div>')
    ver = p.get('model_version') or ''
    onl = p.get('model_price_online')
    vnote = (f'<p class="small mut" style="margin:10px 0 0">Model {E(ver)} on this computer (re-fitted by C-GEM: lower error in every test). '
             f'The online price platform (v22) gives US${onl:,.2f}.</p>') if onl and ver and ver != 'v22' else ''
    return (f'<div class="card" style="margin-top:16px"><h2>C-GEM India price model: US${mid:,.2f} per credit</h2>{scale}{wf}{vnote}{tab}'
            f'<div class="btns noprint" style="margin-top:10px"><a class="btn sec" href="/price-model/calculator.html#price">Price it with other settings</a>'
            f'<a class="btn sec" href="/price-model/calculator.html#quote">Check a quote</a><a class="btn sec" href="/price-model/lab.html?p={quote(p["project_key"], safe="")}">Open in the Price Lab</a><a class="btn sec" href="/price-model/methodology.html">How the model works</a></div>'
            f'<div class="src">C-GEM India carbon credit price model (log-price regression on public deal, offer and listing prices; '
            f'median error on Indian deals about 23% in C-GEM tests). A screening estimate, not investment advice.</div></div>')


def _flags(p, vx):
    out = []
    for s in [x.strip() for x in re.split(r';|\|', p.get('risk_signals') or '') if x.strip()]:
        out.append(('bad', s))
    for s in [x.strip() for x in re.split(r';|\|', p.get('flags') or '') if x.strip()]:
        if s not in [o[1] for o in out]:
            out.append(('warn', s))
    if p.get('has_review_flag') in (1, '1', 'Yes', True):
        out.append(('warn', 'The C-GEM data review flagged this record: check figures against the registry page.'))
    if str(p.get('retired_issued') or '') == 'Yes':
        out.append(('bad', 'More credits retired than issued in the data: a data error or a registry correction.'))
    if p.get('crediting_ends_in_12_months') in (1, '1', 'Yes'):
        out.append(('warn', 'The crediting period ends within 12 months.'))
    if vx and (vx.get('reversals_not_covered') or 0) > 0:
        out.append(('bad', f'{n(vx["reversals_not_covered"])} credits of carbon losses not covered by the buffer pool (Berkeley offsets database).'))
    if (p.get('screening') or '').strip():
        out.append(('warn' if any(w in p['screening'].lower() for w in ('dormant', 'inactive', 'withdrawn', 'review')) else 'ok',
                    f'C-GEM screening: {p["screening"]}'))
    if not out:
        out.append(('ok', 'No risk signals recorded in the public data.'))
    return ''.join(f'<div class="flag {k}">{E(t)}</div>' for k, t in out)


@bp.route(f'{B}/p')
def profile():
    key = request.args.get('key', '')
    c = data()
    p = get(c, key)
    if not p:
        c.close()
        return frame('Project not found', msg('No project with that key. <a href="' + B + '/">Search again</a>.', 'warn'), 'find'), 404
    owner, _, signed = user()
    vs = [(r[0], r[1] or 0) for r in c.execute('SELECT vintage_year, SUM(credits_issued) FROM vintages WHERE project_key = ? AND vintage_year IS NOT NULL '
                                              'GROUP BY vintage_year ORDER BY vintage_year', (key,))]
    buyers = c.execute('SELECT COALESCE(buyer_clean, buyer), SUM(credits_retired) FROM buyers WHERE project_key = ? GROUP BY 1 ORDER BY 2 DESC LIMIT 15',
                       (key,)).fetchall()
    sdgs = [r[0] for r in c.execute('SELECT DISTINCT sdg FROM sdgs WHERE project_key = ? ORDER BY sdg_number', (key,))]
    labels = [r[0] for r in c.execute('SELECT DISTINCT label FROM certifications WHERE project_key = ?', (key,))]
    changes = c.execute('SELECT run_at, field, old_value, new_value, source FROM registry_changes WHERE project_key = ? ORDER BY run_at DESC LIMIT 20',
                        (key,)).fetchall()
    vx = None
    try:
        r = c.execute('SELECT certifications, first_vintage, buffer_deposits, reversals_not_covered, verifier, as_of FROM vrod_extra '
                      'WHERE registry = ? AND project_id = ?', ({'Verified Carbon Standard': 'VCS', 'Gold Standard': 'GS'}.get(p['registry'], p['registry']),
                                                                p['project_id'])).fetchone()
        vx = dict(r) if r else None
    except sqlite3.Error:
        pass
    prov = cgem_sources.project(c, key, p['registry'])
    on_sl = key in shortlist_keys(owner)
    watched = any(r[0] == key for r in cgem_watch.rows(owner))
    c.close()

    iss, ret = p.get('credits_issued') or 0, p.get('credits_retired') or 0
    pct = f'{100 * ret / iss:.0f}% of issued' if iss else ''
    tiles = [('Credits issued', big(iss), f'latest issuance {day(p.get("latest_issuance"))}'),
             ('Credits retired', big(ret), pct),
             ('Not yet retired', big(p.get('unretired_supply')), 'credits still on the market'),
             ('Quality score', f'{n(p.get("quality_score"))}/100' if p.get('quality_score') is not None else '-', f'Grade {p.get("quality_grade") or "-"} (C-GEM, public data)'),
             (('Model price (C-GEM India v22)', f'US${n(p.get("model_price_usd"), 2)}',
               f'P10 US${n(p.get("model_p10_usd"), 2)} to P90 US${n(p.get("model_p90_usd"), 2)}; {p.get("model_confidence") or "-"} confidence')
              if p.get('model_price_usd') is not None else
              ('Indicative price', f'US${n(p.get("price_mid_usd"), 2)}' if p.get('price_mid_usd') else '-', p.get('price_band') or 'no band for this type')),
             ('Yearly reductions', big(p.get('annual_reductions')), 't CO2e a year, as registered')]
    tiles_h = ''.join(f'<div class="tile"><div class="k">{E(k)}</div><div class="v">{v}</div><div class="s">{E(s)}</div></div>' for k, v, s in tiles)
    facts = [('Registry', p['registry']), ('Project ID', p['project_id']), ('Country', p['country']),
             ('State / district', ' / '.join(x for x in [p.get('state'), p.get('district')] if x) or '-'),
             ('Type', p.get('project_type')), ('Sector', ' / '.join(x for x in [p.get('sector'), p.get('sub_sector')] if x)),
             ('Reduction or removal', p.get('reduction_removal')), ('Method', p.get('methodology')), ('Developer', p.get('developer')),
             ('Verifier', p.get('verifier') or (vx or {}).get('verifier')), ('Registry status', p.get('registry_status')),
             ('Registered', day(p.get('registration_date'))), ('Crediting period', f'{day(p.get("crediting_start"))} to {day(p.get("crediting_end"))}'),
             ('First issuance', day(p.get('first_issuance'))), ('Buffer credits', n(p.get('buffer_credits'))),
             ('Area', f'{n(p.get("project_area_ha"))} ha' if p.get('project_area_ha') else '-'),
             ('Data complete', f'{n((p.get("project_completeness") or 0) * (100 if (p.get("project_completeness") or 0) <= 1 else 1))}%'
              + (f' (missing: {p["missing_fields"]})' if p.get('missing_fields') else ''))]
    facts_h = '<table class="kv">' + ''.join(f'<tr><td>{E(k)}</td><td>{E(v) if v not in (None, "") else "-"}</td></tr>' for k, v in facts) + '</table>'
    parts = [('ICVCM programme', 'q_programme', 15), ('ICVCM method (CCP)', 'q_method', 25), ('Type and its record', 'q_type', 20),
             ('Issuance record', 'q_record', 15), ('Data published', 'q_transparency', 15), ('Warning signs', 'q_risk', 10)]
    q_h = ''.join(f'<div class="qrow"><span>{E(t)}</span><div class="bar"><i style="width:{100 * (p.get(k) or 0) / mx:.0f}%"></i></div>'
                  f'<span class="small" style="text-align:right">{n(p.get(k))}/{mx}</span></div>' for t, k, mx in parts)
    market = [('CORSIA first phase (2024-2026)', p.get('corsia_phase1')), ('Article 6', p.get('article6_status')),
              ('ICVCM programme', p.get('icvcm_programme')), ('ICVCM method', p.get('icvcm_methodology_detail') or p.get('icvcm_methodology')),
              ('Labels on the credits', p.get('credit_labels') or ', '.join(labels) or '-'),
              ('Licensed rating', p.get('licensed_rating') or 'none uploaded'), ('Licensed price', p.get('licensed_price') or 'none uploaded'),
              ('Price basis', f'{p.get("price_basis") or "-"} ({p.get("price_confidence") or "-"})')]
    market_h = '<table class="kv">' + ''.join(f'<tr><td>{E(k)}</td><td>{E(v) if v else "-"}</td></tr>' for k, v in market) + '</table>'
    docs = [('Registry page', p.get('registry_page')), ('Project document (PDD)', p.get('pdd_link')), ('Source record', p.get('source_link'))]
    docs_h = ''.join(f'<tr><td>{E(k)}</td><td style="overflow-wrap:anywhere">{link(u, u if u and len(u) < 90 else "Open")}</td></tr>' for k, u in docs)
    docs_h = f'<table class="kv">{docs_h}</table>'
    if sdgs:
        docs_h += f'<h3>Sustainable development goals claimed</h3><p class="small">{E(", ".join(sdgs))}</p>'
    buy_h = ('<div class="wrap"><table><tr><th>Retired by (beneficiary)</th><th class="n">Credits</th></tr>'
             + ''.join(f'<tr><td>{E(b)}</td><td class="n">{n(v)}</td></tr>' for b, v in buyers) + '</table></div>') if buyers else \
        '<p class="mut">The registry does not name who retired these credits.</p>'
    ch_h = ('<div class="wrap"><table><tr><th>When</th><th>What</th><th class="n">Before</th><th class="n">Now</th><th class="hide-s">Source</th></tr>'
            + ''.join(f'<tr><td>{E(r[0])}</td><td>{E(r[1].replace("_", " "))}</td><td class="n">{n(r[2]) if re.match(r"^-?[0-9.]+$", str(r[2] or "")) else E(r[2])}</td>'
                      f'<td class="n">{n(r[3]) if re.match(r"^-?[0-9.]+$", str(r[3] or "")) else E(r[3])}</td><td class="hide-s small">{E(r[4])}</td></tr>' for r in changes)
            + '</table></div>') if changes else '<p class="mut">No change recorded by the registry tracker yet.</p>'
    prov_h = '<table class="kv">' + ''.join(f'<tr><td>{E(a)}</td><td>{E(b)}</td></tr>' for a, b in prov) + '</table>'
    vt = ''.join(f'<tr><td>{y}</td><td class="n">{n(v)}</td></tr>' for y, v in vs)
    k = E(key)
    actions = (f'<form method="post" class="btns noprint" style="margin:6px 0 18px">{csrf()}<input type="hidden" name="k" value="{k}">'
               + (f'<a class="btn sec" href="{B}/shortlist">On your shortlist</a>' if on_sl else f'<button formaction="{B}/shortlist/add">Add to shortlist</button>')
               + (f'<a class="btn sec" href="{B}/watchlist">Watching</a>' if watched else f'<button class="sec" formaction="{B}/watch/add">Watch for changes</button>')
               + f'<a class="btn sec" href="{B}/?{urlencode({"country": p["country"] or "", "type": p.get("price_category") or ""})}">Similar projects</a>'
               + f'<a class="btn sec" href="{B}/compare?k={quote(key, safe="")}">Compare with others</a>'
               + f'<a class="btn sec" href="{B}/shortlist/pdf?k={quote(key, safe="")}">PDF of this profile</a>'
               + '<button type="button" class="sec" onclick="window.print()">Print</button></form>')
    head = (f'<p class="lead">{E(p["registry"])} · {E(p["project_id"])} · {E(p["country"])} &nbsp; {grade_pill(p.get("quality_grade"), p.get("quality_score"))} '
            f'<span class="pill oth">{E(p.get("registry_status") or "status unknown")}</span></p>')
    body = (head + actions + f'<div class="grid">{tiles_h}</div>'
            f'<div class="card"><h2>Issuance history: credits issued by vintage year</h2>{_svg_vintages(vs)}'
            + (f'<details><summary class="small">Show the numbers</summary><table style="max-width:360px"><tr><th>Vintage</th><th class="n">Credits issued</th></tr>{vt}</table></details>' if vs else '')
            + '<div class="src">Source: the project\'s registry, through the C-GEM master data and the registry tracker. See "Where these figures come from" below.</div></div>'
            f'<div class="two"><div class="card"><h2>Risk flags</h2>{_flags(p, vx)}<div class="src">From public data only. A flag is a reason to look closer, not a verdict.</div></div>'
            f'<div class="card"><h2>Quality score: {n(p.get("quality_score"))}/100, grade {E(p.get("quality_grade") or "-")}</h2>{q_h}'
            f'<p class="small mut">{E(p.get("quality_why") or "")}</p><div class="src">C-GEM Quality Score, from public data. It screens projects; it is not a credit rating.</div></div></div>'
            + _model_card(p) +
            f'<div class="two" style="margin-top:16px"><div class="card"><h2>Project facts</h2>{facts_h}</div>'
            f'<div class="card"><h2>Rating, labels and market access</h2>{market_h}</div></div>'
            f'<div class="two" style="margin-top:16px"><div class="card"><h2>Documents and links</h2>{docs_h}</div>'
            f'<div class="card"><h2>Who retired the credits</h2>{buy_h}</div></div>'
            f'<div class="card" style="margin-top:16px"><h2>Changes recorded by the registry tracker</h2>{ch_h}</div>'
            f'<div class="card"><h2>Where these figures come from</h2>{prov_h}</div>')
    return frame(p.get('project_name') or p['project_id'], body, 'find')


# ------------------------------------------------------------------ compare projects
CMP = [('Registry and ID', lambda p: f'{p["registry"]} · {p["project_id"]}'), ('Country', lambda p: p['country']),
       ('Type', lambda p: p.get('project_type')), ('Reduction or removal', lambda p: p.get('reduction_removal')),
       ('Developer', lambda p: p.get('developer')), ('Registry status', lambda p: p.get('registry_status')),
       ('Credits issued', lambda p: n(p.get('credits_issued'))), ('Credits retired', lambda p: n(p.get('credits_retired'))),
       ('Retired share', lambda p: f'{100 * (p.get("credits_retired") or 0) / p["credits_issued"]:.0f}%' if p.get('credits_issued') else '-'),
       ('Not yet retired', lambda p: n(p.get('unretired_supply'))), ('Latest issuance', lambda p: day(p.get('latest_issuance'))),
       ('Crediting period ends', lambda p: day(p.get('crediting_end'))), ('Quality score', lambda p: f'{n(p.get("quality_score"))}/100, grade {p.get("quality_grade") or "-"}'),
       ('ICVCM method', lambda p: p.get('icvcm_methodology')),
       ('EOM offer band (US$)', lambda p: p.get('price_band') or '-'),
       ('CORSIA 2024-2026', lambda p: p.get('corsia_phase1')), ('Article 6', lambda p: p.get('article6_status')),
       ('Labels', lambda p: p.get('credit_labels') or '-'), ('Licensed rating', lambda p: p.get('licensed_rating') or '-'),
       ('Risk signals', lambda p: p.get('risk_signals') or 'none'), ('Data complete', lambda p: f'{n((p.get("project_completeness") or 0) * (100 if (p.get("project_completeness") or 0) <= 1 else 1))}%')]


@bp.route(f'{B}/compare')
def compare():
    if 'csrf_token' in request.args:
        return redirect(f'{B}/compare?' + urlencode([(a, v) for a, v in request.args.items(multi=True) if a != 'csrf_token']))
    keys = [k for k in request.args.getlist('k') if k][:3]
    owner, _, _ = user()
    c = data()
    ps = [p for p in (get(c, k) for k in keys) if p]
    picker_rows, _t = (_search(c, request.args, 30) if request.args.get('q') else ([], 0))
    c.close()
    keep = ''.join(f'<input type="hidden" name="k" value="{E(p["project_key"])}">' for p in ps)
    sl = shortlist_keys(owner)
    pick = (f'<form class="card noprint" method="get" action="{B}/compare">{keep}<h2>Add a project to the comparison</h2>'
            f'<div class="btns"><input type="search" name="q" value="{E(request.args.get("q", ""))}" placeholder="Name or ID" style="max-width:360px"><button>Find</button>'
            + (f'<a class="btn sec" href="{B}/compare?{urlencode([("k", k) for k in sl[:3]])}">Compare my shortlist (first 3)</a>' if len(sl) >= 2 else '')
            + '</div>')
    if picker_rows:
        pick += '<div class="wrap" style="margin-top:10px"><table>' + ''.join(
            f'<tr><td>{E(r["project_name"])}<div class="small mut">{E(r["registry"])} · {E(r["project_id"])} · {E(r["country"])}</div></td>'
            f'<td><a class="btn sec" href="{B}/compare?{urlencode([("k", p["project_key"]) for p in ps][:2] + [("k", r["project_key"])])}">Add</a></td></tr>'
            for r in picker_rows) + '</table></div>'
    pick += '</form>'
    if len(ps) < 2:
        return frame('Compare projects', pick + msg('Pick two or three projects: tick them on <a href="' + B + '/">Find projects</a>, or search above.', 'warn'),
                     'compare', 'Two or three projects side by side, row by row.')
    head = '<tr><th></th>' + ''.join(f'<th>{plink(p["project_key"], p.get("project_name") or p["project_id"])}'
                                     f'<div class="small"><a href="{B}/compare?{urlencode([("k", q["project_key"]) for q in ps if q is not p])}">remove</a></div></th>'
                                     for p in ps) + '</tr>'
    body = ''.join(f'<tr><td>{E(t)}</td>' + ''.join(f'<td>{E(f(p)) if f(p) not in (None, "") else "-"}</td>' for p in ps) + '</tr>' for t, f in CMP)
    vbar = '<tr><td>Issuance by vintage</td>' + ''.join(f'<td><a href="{B}/p?key={quote(p["project_key"], safe="")}">see profile</a></td>' for p in ps) + '</tr>'
    xl = f'{B}/shortlist/xlsx?{urlencode([("k", p["project_key"]) for p in ps])}'
    pdf = f'{B}/shortlist/pdf?{urlencode([("k", p["project_key"]) for p in ps])}'
    out = (f'<div class="btns noprint" style="margin:0 0 12px"><a class="btn" href="{xl}">Excel</a><a class="btn sec" href="{pdf}">PDF</a>'
           f'<button type="button" class="sec" onclick="window.print()">Print</button></div>'
           f'<div class="card"><div class="wrap"><table class="cmp"><thead>{head}</thead><tbody>{body}{vbar}</tbody></table></div>'
           f'<div class="src">Figures from the registries through C-GEM; quality score and price band calculated by C-GEM from public data. '
           f'<a href="{B}/sources">Where every number comes from</a>.</div></div>')
    return frame('Compare projects', out + pick, 'compare', 'Two or three projects side by side, row by row.')


# ------------------------------------------------------------------ compare countries
def _country(c, name):
    r = c.execute('SELECT COUNT(*), SUM(credits_issued), SUM(credits_retired), SUM(unretired_supply), AVG(quality_score), '
                  "SUM(CASE WHEN quality_grade IN ('A','B') THEN 1 ELSE 0 END), COUNT(DISTINCT registry), AVG(price_mid_usd), "
                  "SUM(CASE WHEN corsia_phase1 LIKE 'Yes%' OR corsia_phase1 LIKE 'Likely%' THEN 1 ELSE 0 END), "
                  "SUM(CASE WHEN registry_status LIKE '%egister%' OR registry_status LIKE '%ctive%' THEN 1 ELSE 0 END), "
                  'MAX(latest_issuance) FROM projects WHERE country = ?', (name,)).fetchone()
    if not r or not r[0]:
        return None
    types = c.execute('SELECT price_category, COUNT(*) FROM projects WHERE country = ? AND price_category IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 3',
                      (name,)).fetchall()
    regs = c.execute('SELECT registry, COUNT(*) FROM projects WHERE country = ? GROUP BY 1 ORDER BY 2 DESC LIMIT 3', (name,)).fetchall()
    try:
        a6 = c.execute('SELECT role, partners, buys_from, a62_activities, pacm_activities FROM article6_hosts WHERE country = ?', (name,)).fetchone()
    except sqlite3.Error:
        a6 = None
    vint = c.execute('SELECT vintage_year, SUM(credits_issued) FROM vintages WHERE country = ? AND vintage_year >= 2015 GROUP BY 1 ORDER BY 1', (name,)).fetchall()
    return dict(projects=r[0], issued=r[1], retired=r[2], supply=r[3], score=r[4], good=r[5], registries=r[6], price=r[7], corsia=r[8],
                latest=r[10], types=types, regs=regs, a6=a6, vint=vint)


@bp.route(f'{B}/countries')
def countries():
    names = [x for x in request.args.getlist('c') if x][:3]
    c = data()
    allc = _opts(c, 'country', limit=300)
    if not names:
        names = ['India', 'Brazil', 'Kenya']
    ds = [(nm, _country(c, nm)) for nm in names]
    c.close()
    sel = ''.join(f'<div><label>Country {i + 1}</label>{_select("c", allc, names[i] if i < len(names) else "", "None")}</div>' for i in range(3))
    form = (f'<form class="card noprint" method="get"><div class="filters" style="grid-template-columns:repeat(3,1fr) auto">{sel}'
            f'<div class="btns"><button>Compare</button></div></div></form>')
    ds = [(nm, d) for nm, d in ds if d]
    rows = [('Projects', lambda d: n(d['projects'])), ('Credits issued', lambda d: big(d['issued'])), ('Credits retired', lambda d: big(d['retired'])),
            ('Retired share', lambda d: f'{100 * (d["retired"] or 0) / d["issued"]:.0f}%' if d['issued'] else '-'),
            ('Not yet retired (supply)', lambda d: big(d['supply'])), ('Average quality score', lambda d: f'{n(d["score"])}/100'),
            ('Projects graded A or B', lambda d: f'{n(d["good"])} ({100 * d["good"] / d["projects"]:.0f}%)'),
            ('Average indicative price', lambda d: f'US${n(d["price"], 2)}' if d['price'] else '-'),
            ('Could be CORSIA-eligible (yes or likely)', lambda d: n(d['corsia'])), ('Registries used', lambda d: n(d['registries'])),
            ('Main registries', lambda d: ', '.join(f'{r} ({c_:,})' for r, c_ in d['regs'])),
            ('Main project types', lambda d: ', '.join(f'{t} ({c_:,})' for t, c_ in d['types'])),
            ('Latest issuance', lambda d: day(d['latest'])),
            ('Article 6.2: role', lambda d: d['a6'][0] if d['a6'] else 'No deal recorded'),
            ('Article 6.2: sells to', lambda d: (d['a6'][1] or '-') if d['a6'] else '-'),
            ('Article 6.2: buys from', lambda d: (d['a6'][2] or '-') if d['a6'] else '-'),
            ('Article 6 activities (6.2 / 6.4)', lambda d: f'{d["a6"][3] or 0} / {d["a6"][4] or 0}' if d['a6'] else '-')]
    head = '<tr><th></th>' + ''.join(f'<th><a href="{B}/?country={quote(nm)}">{E(nm)}</a></th>' for nm, _ in ds) + '</tr>'
    body = ''.join(f'<tr><td>{E(t)}</td>' + ''.join(f'<td>{E(f(d))}</td>' for _, d in ds) + '</tr>' for t, f in rows)
    years = sorted({y for _, d in ds for y, _v in d['vint']})
    trend = ''
    if years:
        cols = ['#2C7A3D', '#C98A1F', '#B85829']
        mx = max([v or 0 for _, d in ds for _y, v in d['vint']] or [1]) or 1
        w, h, pad = 760, 200, 40
        step = (w - pad - 10) / max(len(years) - 1, 1)
        lines = []
        for i, (nm, d) in enumerate(ds):
            m = dict(d['vint'])
            pts = ' '.join(f'{pad + years.index(y) * step:.1f},{h - 26 - (h - 50) * (m.get(y) or 0) / mx:.1f}' for y in years)
            lines.append(f'<polyline points="{pts}" fill="none" stroke="{cols[i]}" stroke-width="2.5"/>'
                         f'<text x="{pad + 8 + i * 170}" y="14" font-size="11" fill="{cols[i]}">{E(nm)}</text>')
        ticks = ''.join(f'<text x="{pad + i * step:.1f}" y="{h - 8}" font-size="10" text-anchor="middle" fill="currentColor" opacity=".6">{y}</text>'
                        for i, y in enumerate(years) if i % 2 == 0)
        trend = (f'<div class="card"><h2>Credits issued by vintage year, 2015 onward</h2><svg viewBox="0 0 {w} {h}" width="100%" style="max-height:230px">'
                 f'<text x="{pad}" y="32" font-size="10" fill="currentColor" opacity=".6">max {big(mx)}</text>{"".join(lines)}{ticks}</svg></div>')
    out = form + (f'<div class="card"><div class="wrap"><table class="cmp"><thead>{head}</thead><tbody>{body}</tbody></table></div>'
                  f'<div class="src">Registries through C-GEM; Article 6 from the UNEP Copenhagen Climate Centre Article 6 Pipeline. '
                  f'<a href="{B}/sources">All sources and dates</a>.</div></div>' if ds else msg('Pick at least one country.', 'warn')) + trend
    return frame('Compare countries', out, 'countries', 'Up to three countries side by side: supply, quality, price, CORSIA and Article 6 deals.')


# ------------------------------------------------------------------ shortlist and export
def _keys_from_request():
    ks = request.values.getlist('k')
    return [k for k in ks if k]


@bp.route(f'{B}/shortlist/add', methods=['POST'])
def shortlist_add():
    owner, _, _ = user()
    ks = _keys_from_request()
    s = store()
    s.executemany('INSERT OR IGNORE INTO shortlist VALUES (?,?,?,NULL)', [(owner, k, M.ts()) for k in ks])
    s.commit()
    s.close()
    return redirect(f'{B}/shortlist?added={len(ks)}')


@bp.route(f'{B}/shortlist/remove', methods=['POST'])
def shortlist_remove():
    owner, _, _ = user()
    s = store()
    ks = _keys_from_request()
    if request.form.get('all') == '1':
        s.execute('DELETE FROM shortlist WHERE owner = ?', (owner,))
    else:
        s.executemany('DELETE FROM shortlist WHERE owner = ? AND project_key = ?', [(owner, k) for k in ks])
    s.commit()
    s.close()
    return redirect(f'{B}/shortlist')


@bp.route(f'{B}/shortlist')
def shortlist():
    owner, name, signed = user()
    keys = shortlist_keys(owner)
    c = data()
    rows = []
    for k in keys:
        r = c.execute('SELECT project_key, registry, project_id, project_name, country, price_category, quality_grade, quality_score, '
                      'credits_issued, credits_retired, price_band, corsia_phase1, model_price_usd, model_p10_usd, model_p90_usd '
                      'FROM projects WHERE project_key = ?', (k,)).fetchone()
        if r:
            rows.append(r)
    c.close()
    top = msg(f'{request.args["added"]} project(s) added.') if request.args.get('added') else ''
    if not signed:
        top += msg('You are not signed in to the dashboard, so this shortlist is kept for this browser only. '
                   '<a href="/login/?next=' + quote(f'{B}/shortlist') + '">Sign in</a> to keep it with your name.', 'warn')
    if not rows:
        return frame('Shortlist', top + msg(f'Your shortlist is empty. Tick projects on <a href="{B}/">Find projects</a> and press Add to shortlist.', 'warn'),
                     'shortlist', 'Projects you are considering. Export them for a buyer as Excel or PDF.')
    exp = (f'<div class="btns noprint" style="margin:0 0 12px"><a class="btn" href="{B}/shortlist/xlsx">Download Excel</a>'
           f'<a class="btn" href="{B}/shortlist/pdf">Download PDF report</a>'
           f'<a class="btn sec" href="{B}/compare?{urlencode([("k", r["project_key"]) for r in rows[:3]])}">Compare the first three</a></div>')
    body = (top + exp + f'<form class="card" method="post">{csrf()}<h2>{len(rows)} projects on your shortlist</h2>'
            f'<div class="btns noprint" style="margin:0 0 10px"><span class="small mut">With the ticked projects:</span>'
            f'<button formaction="{B}/compare" formmethod="get">Compare</button>'
            f'<button class="sec" formaction="{B}/watch/add">Watch for changes</button>'
            f'<button class="sec bad" formaction="{B}/shortlist/remove">Remove</button></div>'
            + _result_table(rows, owner) + '</form>')
    return frame('Shortlist', body, 'shortlist', 'Projects you are considering. Export them for a buyer as Excel or PDF.')


def _export_rows(keys):
    c = data()
    ps = [p for p in (get(c, k) for k in keys) if p]
    vint = {}
    for p in ps:
        vint[p['project_key']] = c.execute('SELECT vintage_year, SUM(credits_issued) FROM vintages WHERE project_key = ? AND vintage_year IS NOT NULL '
                                           'GROUP BY 1 ORDER BY 1', (p['project_key'],)).fetchall()
    prov = {p['project_key']: cgem_sources.project(c, p['project_key'], p['registry']) for p in ps}
    c.close()
    return ps, vint, prov


XCOLS = [('Project', 'project_name', 42), ('Registry', 'registry', 24), ('Project ID', 'project_id', 14), ('Country', 'country', 16),
         ('State', 'state', 16), ('Type', 'project_type', 30), ('Price category', 'price_category', 22), ('Developer', 'developer', 28),
         ('Registry status', 'registry_status', 16), ('Credits issued', 'credits_issued', 15), ('Credits retired', 'credits_retired', 15),
         ('Not yet retired', 'unretired_supply', 15), ('Latest issuance', 'latest_issuance', 14), ('Crediting end', 'crediting_end', 14),
         ('Quality score', 'quality_score', 10), ('Grade', 'quality_grade', 8), ('Why this score', 'quality_why', 60),
         ('EOM low US$', 'price_low_usd', 11), ('EOM median US$', 'price_mid_usd', 11), ('EOM high US$', 'price_high_usd', 11),
         ('CORSIA 2024-2026', 'corsia_phase1', 34), ('Article 6', 'article6_status', 40), ('Labels', 'credit_labels', 26),
         ('Licensed rating', 'licensed_rating', 18), ('Licensed price', 'licensed_price', 18), ('Risk signals', 'risk_signals', 40),
         ('Registry page', 'registry_page', 40), ('Project document', 'pdd_link', 40)]


@bp.route(f'{B}/shortlist/xlsx')
def shortlist_xlsx():
    owner, _, _ = user()
    keys = _keys_from_request() or shortlist_keys(owner)
    ps, vint, prov = _export_rows(keys)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = 'Shortlist'
    ws['A1'] = 'C-GEM shortlist'
    ws['A1'].font = Font(bold=True, size=14, color='265E30')
    ws['A2'] = f'Exported {dt.datetime.now():%d %b %Y %H:%M}. {len(ps)} projects. Quality score and price band: C-GEM, from public data; not a credit rating or a quote.'
    ws['A2'].font = Font(italic=True, size=9, color='5C6358')
    hdr = PatternFill('solid', fgColor='2C7A3D')
    for j, (t, _, w) in enumerate(XCOLS, 1):
        cell = ws.cell(row=4, column=j, value=t)
        cell.font, cell.fill = Font(bold=True, color='FFFFFF'), hdr
        cell.alignment = Alignment(wrap_text=True, vertical='center')
        ws.column_dimensions[get_column_letter(j)].width = w
    for i, p in enumerate(ps, 5):
        for j, (_, k, _) in enumerate(XCOLS, 1):
            v = p.get(k)
            cell = ws.cell(row=i, column=j, value=v)
            if k in ('credits_issued', 'credits_retired', 'unretired_supply'):
                cell.number_format = '#,##0'
            elif k.endswith('_usd'):
                cell.number_format = '0.00'
            if k in ('registry_page', 'pdd_link') and v and str(v).startswith('http'):
                cell.hyperlink, cell.font = v, Font(color='2C7A3D', underline='single')
            cell.alignment = Alignment(vertical='top', wrap_text=k in ('quality_why', 'article6_status', 'corsia_phase1', 'risk_signals'))
    ws.freeze_panes = 'B5'
    ws.auto_filter.ref = f'A4:{get_column_letter(len(XCOLS))}{4 + len(ps)}'
    v2 = wb.create_sheet('Issuance by vintage')
    v2.append(['Project', 'Registry', 'Project ID', 'Vintage year', 'Credits issued'])
    for p in ps:
        for y, v in vint[p['project_key']]:
            v2.append([p['project_name'], p['registry'], p['project_id'], y, v])
    s3 = wb.create_sheet('Sources')
    s3.append(['Project', 'Item', 'Source and date'])
    for p in ps:
        for a, b in prov[p['project_key']]:
            s3.append([p['project_name'], a, b])
    for sh in (v2, s3):
        for cell in sh[1]:
            cell.font, cell.fill = Font(bold=True, color='FFFFFF'), hdr
        for col, w in zip('ABCDE', (42, 26, 14, 30, 16)):
            sh.column_dimensions[col].width = w
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name=f'CGEM_shortlist_{dt.date.today():%Y%m%d}.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _lat(s):
    import unicodedata
    s = '' if s is None else str(s)
    s = s.replace('–', '-').replace('—', '-').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.replace('·', '-').replace('•', '-').replace('CO₂', 'CO2')
    s = unicodedata.normalize('NFKD', s)
    return s.encode('latin-1', 'ignore').decode('latin-1')


@bp.route(f'{B}/shortlist/pdf')
def shortlist_pdf():
    owner, _, _ = user()
    keys = _keys_from_request() or shortlist_keys(owner)
    ps, vint, prov = _export_rows(keys)
    try:
        from fpdf import FPDF
    except ImportError:
        return frame('PDF not available', msg('The PDF maker is not installed on this computer yet. Run update_dashboard.command once, '
                                              'or use Print on the compare or profile page and choose "Save as PDF".', 'warn'), 'shortlist')
    leaf, ink, mut = (44, 122, 61), (14, 20, 16), (92, 99, 88)

    class Doc(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*leaf)
            self.cell(0, 6, 'C-GEM CARBON CREDIT INTELLIGENCE', new_x='LMARGIN', new_y='NEXT')
            self.set_draw_color(*leaf)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(3)

        def footer(self):
            self.set_y(-12)
            self.set_font('Helvetica', '', 7)
            self.set_text_color(*mut)
            self.cell(0, 5, _lat(f'Exported {dt.datetime.now():%d %b %Y %H:%M}. Prices: EOM offer band. '
                                 f'Screening estimates from public data, not a rating or a price quote. Page {self.page_no()}'), align='C')

    pdf = Doc(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(True, 16)
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*ink)
    pdf.cell(0, 10, 'Project shortlist' if len(ps) > 1 else _lat(ps[0]['project_name'] if ps else 'Project'), new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*mut)
    tot_i = sum(p.get('credits_issued') or 0 for p in ps)
    tot_s = sum(p.get('unretired_supply') or 0 for p in ps)
    pdf.cell(0, 6, _lat(f'{len(ps)} project(s) - {tot_i:,.0f} credits issued - {tot_s:,.0f} not yet retired'), new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)
    cols = [('Project', 64), ('ID and registry', 44), ('Country', 22), ('Type', 28), ('Score', 13), ('Issued', 22), ('Retired', 22),
            ('   Price US$ mid (range)', 39), ('CORSIA 24-26', 23)]
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(*leaf)
    pdf.set_text_color(255, 255, 255)
    for t, w in cols:
        pdf.cell(w, 7, t, border=0, fill=True, align='R' if t in ('Issued', 'Retired') else 'L')
    pdf.ln()
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(*ink)
    for i, p in enumerate(ps):
        if p.get('model_price_usd') is not None:
            band = f'   {p["model_price_usd"]:.2f} ({p["model_p10_usd"]:.2f}-{p["model_p90_usd"]:.2f}) M'
        else:
            band = f'   {p["price_mid_usd"]:.2f} ({p["price_low_usd"]:.2f}-{p["price_high_usd"]:.2f})' if p.get('price_mid_usd') else '   -'
        vals = [p.get('project_name'), f'{p["project_id"]} ({p["registry"].split("(")[0].strip()})', p.get('country'),
                p.get('price_category') or p.get('project_type'), f'{n(p.get("quality_score"))} {p.get("quality_grade") or ""}',
                n(p.get('credits_issued')), n(p.get('credits_retired')), band, (p.get('corsia_phase1') or '-').split(':')[0].split('(')[0].split(' for ')[0]]
        pdf.set_fill_color(*((240, 244, 238) if i % 2 else (255, 255, 255)))
        for (t, w), v in zip(cols, vals):
            s = _lat(v)
            while s and pdf.get_string_width(s + '..') > w - 2:
                s = s[:-1]
            pdf.cell(w, 6.5, s + ('' if s == _lat(v) else '..'), fill=True, align='R' if t in ('Issued', 'Retired') else 'L')
        pdf.ln()
    for p in ps:
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*ink)
        pdf.multi_cell(0, 7, _lat(p.get('project_name') or p['project_id']), new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*mut)
        pdf.cell(0, 5, _lat(f'{p["registry"]} - {p["project_id"]} - {p.get("country") or ""} - {p.get("registry_status") or ""}'), new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)
        facts = [('Type', p.get('project_type')), ('Developer', p.get('developer')), ('Method', p.get('methodology')),
                 ('Credits issued / retired', f'{n(p.get("credits_issued"))} / {n(p.get("credits_retired"))}'),
                 ('Not yet retired', n(p.get('unretired_supply'))), ('Latest issuance', day(p.get('latest_issuance'))),
                 ('Crediting period', f'{day(p.get("crediting_start"))} to {day(p.get("crediting_end"))}'),
                 ('Quality score', f'{n(p.get("quality_score"))}/100, grade {p.get("quality_grade") or "-"}'),
                 ('Why this score', p.get('quality_why')), 
                 ('EOM offer band', p.get('price_band')),
                 ('CORSIA 2024-2026', p.get('corsia_phase1')), ('Article 6', p.get('article6_status')), ('Labels', p.get('credit_labels')),
                 ('Licensed rating', p.get('licensed_rating')), ('Risk signals', p.get('risk_signals') or 'none recorded'),
                 ('Registry page', p.get('registry_page')), ('Project document', p.get('pdd_link'))]
        for k, v in facts:
            pdf.set_font('Helvetica', 'B', 8.5)
            pdf.set_text_color(*mut)
            y = pdf.get_y()
            pdf.cell(48, 5, _lat(k))
            pdf.set_font('Helvetica', '', 8.5)
            pdf.set_text_color(*ink)
            pdf.multi_cell(0, 5, _lat(v if v not in (None, '') else '-'), new_x='LMARGIN', new_y='NEXT')
            if pdf.get_y() < y + 5:
                pdf.set_y(y + 5)
        vs = vint[p['project_key']]
        if vs and pdf.get_y() < 150:
            pdf.ln(3)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 6, 'Credits issued by vintage year', new_x='LMARGIN', new_y='NEXT')
            x0, y0, wch, hch = pdf.l_margin, pdf.get_y() + 2, 200, 30
            mx = max(v or 0 for _, v in vs) or 1
            bw = wch / len(vs)
            pdf.set_fill_color(*leaf)
            pdf.set_font('Helvetica', '', 6)
            for i, (yr, v) in enumerate(vs):
                bh = hch * (v or 0) / mx
                pdf.rect(x0 + i * bw + 0.4, y0 + hch - bh, max(bw - 0.8, 0.5), bh, style='F')
                if len(vs) <= 20 or i % 3 == 0:
                    pdf.text(x0 + i * bw + 0.4, y0 + hch + 3.5, str(yr))
            pdf.set_y(y0 + hch + 6)
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 7.5)
        pdf.set_text_color(*mut)
        for a, b in prov[p['project_key']]:
            pdf.multi_cell(0, 4, _lat(f'Source - {a}: {b}'), new_x='LMARGIN', new_y='NEXT')
    out = bytes(pdf.output())
    return Response(out, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename=CGEM_{"shortlist" if len(ps) > 1 else "project"}_{dt.date.today():%Y%m%d}.pdf'})


# ------------------------------------------------------------------ watchlist
@bp.route(f'{B}/watch/add', methods=['POST'])
def watch_add():
    owner, _, signed = user()
    c = data()
    k = cgem_watch.add(c, owner, _keys_from_request())
    c.close()
    return redirect(f'{B}/watchlist?added={k}')


@bp.route(f'{B}/watch/remove', methods=['POST'])
def watch_remove():
    owner, _, _ = user()
    cgem_watch.remove(owner, _keys_from_request())
    return redirect(f'{B}/watchlist')


@bp.route(f'{B}/watch/email', methods=['POST'])
def watch_email():
    if ONLINE:   # no e-mail alerts on the public site
        return redirect(f'{B}/watchlist')
    owner, _, _ = user()
    e = M.norm_email(request.form.get('email', ''))
    if e and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e):
        return redirect(f'{B}/watchlist?bad=1')
    cgem_watch.set_email(owner, e)
    return redirect(f'{B}/watchlist?saved=1')


@bp.route(f'{B}/watch/check', methods=['POST'])
def watch_check():
    if ONLINE:   # no e-mail alerts on the public site
        return redirect(f'{B}/watchlist')
    owner, _, _ = user()
    c = sqlite3.connect(M.DB, timeout=20)
    n_ = cgem_watch.check(c, request.host_url.rstrip('/'))
    c.close()
    return redirect(f'{B}/watchlist?checked={n_}')


@bp.route(f'{B}/watchlist')
def watchlist():
    owner, name, signed = user()
    ws = cgem_watch.rows(owner)
    c = data()
    rows = []
    for key, email, iss, ret, st, added, last in ws:
        p = c.execute('SELECT project_name, registry, project_id, credits_issued, credits_retired, registry_status FROM projects WHERE project_key = ?',
                      (key,)).fetchone()
        rows.append((key, p, iss, ret, st, added, last))
    c.close()
    email = ws[0][1] if ws else ''
    a = request.args
    top = ''
    if a.get('added'):
        top += msg(f'{a["added"]} project(s) are now on your watchlist.')
    if a.get('saved'):
        top += msg('E-mail saved.')
    if a.get('bad'):
        top += msg('That does not look like an e-mail address.', 'bad')
    if a.get('checked') is not None and a.get('checked') != '':
        top += msg(f'Checked now: {a["checked"]} change(s) found.' + (' E-mails sent where an address is set.' if a['checked'] != '0' else ''))
    if not signed:
        top += msg('You are not signed in, so this watchlist belongs to this browser only. <a href="/login/?next=' + quote(f'{B}/watchlist')
                   + '">Sign in</a> to keep it with your name.', 'warn')
    if not M.mail_ready():
        top += msg('E-mail is not set up on this computer yet, so changes are listed below but no e-mail goes out. The dashboard admin sets it '
                   'on the <a href="/cgem-admin/settings">Settings page of the company data page</a>.', 'warn')
    em = (f'<form class="card noprint" method="post" action="{B}/watch/email">{csrf()}<h2>Send alerts to</h2><div class="btns">'
          f'<input type="email" name="email" value="{E(email)}" placeholder="name@company.com" style="max-width:340px"><button>Save</button></div>'
          f'<p class="small mut" style="margin:8px 0 0">An e-mail goes out after each registry update (every day on this computer) when a watched project has new '
          f'credits issued, credits retired, or a new registry status.</p></form>')
    if not rows:
        return frame('Watchlist', top + em + msg(f'You are not watching any project. On <a href="{B}/">Find projects</a> or a project profile, '
                                                 f'press Watch for changes.', 'warn'), 'watch',
                     'Follow projects and get an e-mail when they issue or retire credits.')
    tr = ''.join(f'<tr><td><input type="checkbox" name="k" value="{E(k)}"></td><td>{plink(k, p[0] if p else k)}'
                 f'<div class="small mut">{E(p[1]) if p else "no longer in the data"} · {E(p[2]) if p else ""}</div></td>'
                 f'<td class="n">{n(p[3]) if p else "-"}</td><td class="n">{n(p[4]) if p else "-"}</td><td class="hide-s">{E(p[5]) if p else "-"}</td>'
                 f'<td class="small hide-s">{E(added)}</td><td class="small">{E(last or "no change yet")}</td></tr>' for k, p, iss, ret, st, added, last in rows)
    tab = (f'<form class="card" method="post">{csrf()}<h2>{len(rows)} watched project(s)</h2><div class="btns noprint" style="margin:0 0 10px">'
           f'<button formaction="{B}/watch/check">Check now</button><button class="sec bad" formaction="{B}/watch/remove">Stop watching ticked</button></div>'
           f'<div class="wrap"><table><tr><th></th><th>Project</th><th class="n">Issued</th><th class="n">Retired</th><th class="hide-s">Status</th>'
           f'<th class="hide-s">Watching since</th><th>Last change</th></tr>{tr}</table></div></form>')
    lg = cgem_watch.log(owner)
    lg_h = ('<div class="card"><h2>Changes found</h2><div class="wrap"><table><tr><th>When</th><th>Project</th><th>What changed</th><th class="hide-s">E-mail</th></tr>'
            + ''.join(f'<tr><td class="small">{E(a_)}</td><td>{E(p_)}</td><td>{E(w_)}</td><td class="small hide-s">{E(s_ or "no address")}</td></tr>' for a_, p_, w_, s_ in lg)
            + '</table></div></div>') if lg else ''
    return frame('Watchlist', top + em + tab + lg_h, 'watch', 'Follow projects and get an e-mail when they issue or retire credits.')


# ------------------------------------------------------------------ data sources
@bp.route(f'{B}/sources')
def sources():
    c = data()
    try:
        rows = c.execute('SELECT area, dataset, source, how_updated, last_checked, last_new_data, last_change, coverage, link FROM data_sources').fetchall()
    except sqlite3.Error:
        rows = []
    st = None
    try:
        st = c.execute('SELECT last_run, last_new_data FROM registry_tracker_status_raw').fetchone()
    except sqlite3.Error:
        pass
    try:
        sc = c.execute('SELECT run_at, ok, item, problem FROM selfcheck').fetchall()
    except sqlite3.Error:
        sc = []
    c.close()
    top = ''
    if sc:
        if sc[0][1] == 1:
            top += msg(f'Dashboard self-check on {E(sc[0][0])}: every chart, column, filter and page checked, no problems found.')
        else:
            top += msg(f'Dashboard self-check on {E(sc[0][0])} found {len(sc)} problem(s): '
                       + '; '.join(f'{E(r[2])}: {E(r[3])}' for r in sc[:8]) + ('...' if len(sc) > 8 else ''), 'bad')
    if st:
        top = (f'<div class="grid"><div class="tile"><div class="k">Registry tracker last ran</div><div class="v" style="font-size:18px">{E(st[0])}</div></div>'
               f'<div class="tile"><div class="k">Last new registry data</div><div class="v" style="font-size:18px">{E(st[1])}</div></div>'
               f'<div class="tile"><div class="k">Datasets listed</div><div class="v">{len(rows)}</div></div></div>')
    groups = {}
    for r in rows:
        groups.setdefault(r[0], []).append(r)
    out = top
    for g, rs in groups.items():
        tr = ''.join(f'<tr><td>{link(r[8], r[1]) if r[8] else E(r[1])}<div class="small mut">{E(r[7])}</div></td><td>{E(r[2])}</td>'
                     f'<td class="small">{E(r[3])}</td><td class="small">{E(r[4] or "-")}</td><td class="small">{E(r[6] or r[5] or "-")}</td></tr>' for r in rs)
        out += (f'<div class="card"><h2>{E(g)}</h2><div class="wrap"><table><tr><th>Data</th><th>Source</th><th>How it is updated</th>'
                f'<th>Last checked</th><th>Last change</th></tr>{tr}</table></div></div>')
    if not rows:
        out += msg('The list of sources is made after the next registry update.', 'warn')
    return frame('Where every number comes from', out, 'sources',
                 'Each dataset in C-GEM, where it comes from, how it is updated and when it last changed. Each project profile also shows the source '
                 'and date of its own figures.')



# ------------------------------------------------------------------ India CCTS: obligated entities and their emission intensity targets
def _ccts_rows(c, a):
    where, args = ['1=1'], []
    q = (a.get('q') or '').strip()
    if q:
        where.append('(entity LIKE ? OR company LIKE ? OR reg_no LIKE ?)')
        args += [f'%{q}%'] * 3
    for key, col in (('sector', 'sector'), ('state', 'state')):
        if a.get(key):
            where.append(f'{col} = ?')
            args.append(a[key])
    order = {'reduction': 'reduction_pct DESC', 'output': 'output_t DESC', 'name': 'company'}.get(a.get('sort') or 'reduction', 'reduction_pct DESC')
    sql = ('SELECT reg_no, company, entity, sector, sub_sector, state, output_t, output_unit, baseline_gei, target_2025_26, target_2026_27, '
           f'reduction_pct, notification FROM ccts_entities WHERE {" AND ".join(where)} ORDER BY {order} NULLS LAST')
    return c.execute(sql, args).fetchall()


@bp.route(f'{B}/ccts')
def ccts():
    c = data()
    try:
        tot = c.execute('SELECT COUNT(*), COUNT(DISTINCT sector), COUNT(DISTINCT state), AVG(reduction_pct) FROM ccts_entities').fetchone()
    except sqlite3.Error:
        c.close()
        return frame('India CCTS', msg('The CCTS table is not in this database yet.', 'warn'), 'ccts')
    a = request.args
    rows = _ccts_rows(c, a)
    if a.get('csv') == '1':
        c.close()
        out = io.StringIO()
        import csv
        w = csv.writer(out)
        w.writerow(['Registration no', 'Company', 'Entity (as notified)', 'Sector', 'Sub-sector', 'State', 'Output', 'Unit', 'Baseline GEI',
                    'Target 2025-26', 'Target 2026-27', 'Reduction by 2026-27 (%)', 'Notification'])
        for r in rows:
            w.writerow(list(r))
        return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=cgem_india_ccts_entities.csv'})
    sectors = [r[0] for r in c.execute('SELECT sector FROM ccts_entities WHERE sector IS NOT NULL GROUP BY sector ORDER BY COUNT(*) DESC')]
    states = [r[0] for r in c.execute('SELECT state FROM ccts_entities WHERE state IS NOT NULL AND state != "" GROUP BY state ORDER BY COUNT(*) DESC')]
    sec = c.execute('SELECT sector, COUNT(*), AVG(reduction_pct), MIN(reduction_pct), MAX(reduction_pct), SUM(output_t), MAX(output_unit), COUNT(DISTINCT state) '
                    'FROM ccts_entities GROUP BY sector ORDER BY COUNT(*) DESC').fetchall()
    st = c.execute('SELECT state, COUNT(*), COUNT(DISTINCT sector) FROM ccts_entities WHERE state IS NOT NULL AND state != "" '
                   'GROUP BY state ORDER BY COUNT(*) DESC LIMIT 12').fetchall()
    notes = c.execute('SELECT notification, COUNT(*) FROM ccts_entities GROUP BY notification ORDER BY COUNT(*) DESC').fetchall()
    c.close()
    mx = max([r[1] for r in sec] or [1])
    tiles = (f'<div class="grid"><div class="tile"><div class="k">Obligated entities</div><div class="v">{n(tot[0])}</div><div class="s">plants and units named in the notifications</div></div>'
             f'<div class="tile"><div class="k">Sectors</div><div class="v">{n(tot[1])}</div><div class="s">cement, textiles, paper, refining and more</div></div>'
             f'<div class="tile"><div class="k">States and UTs</div><div class="v">{n(tot[2])}</div><div class="s">where the plants are</div></div>'
             f'<div class="tile"><div class="k">Average reduction asked</div><div class="v">{n(tot[3], 1)}%</div><div class="s">emission intensity, baseline to 2026-27</div></div></div>')
    sec_rows = ''.join(
        f'<tr><td><a href="{B}/ccts?sector={quote(r[0])}#list">{E(r[0])}</a></td><td class="n">{n(r[1])}</td>'
        f'<td><div class="bar"><i style="width:{100 * r[1] / mx:.0f}%"></i></div></td><td class="n">{n(r[2], 1)}%</td>'
        f'<td class="n hide-s">{n(r[3], 1)}% to {n(r[4], 1)}%</td><td class="n hide-s">{big(r[5])} {"MBBLS" if (r[6] or "").startswith("thousand") else "t"}</td>'
        f'<td class="n hide-s">{n(r[7])}</td></tr>' for r in sec)
    st_rows = ''.join(f'<tr><td><a href="{B}/ccts?state={quote(r[0])}#list">{E(r[0])}</a></td><td class="n">{n(r[1])}</td><td class="n">{n(r[2])}</td></tr>' for r in st)
    form = (f'<form class="card noprint" id="list" method="get"><div class="filters" style="grid-template-columns:2fr 1fr 1fr 1fr auto">'
            f'<div><label>Search company, plant or registration no.</label><input type="search" name="q" value="{E(a.get("q", ""))}"></div>'
            f'<div><label>Sector</label>{_select("sector", sectors, a.get("sector", ""))}</div>'
            f'<div><label>State</label>{_select("state", states, a.get("state", ""))}</div>'
            f'<div><label>Sort by</label><select name="sort">'
            + ''.join(f'<option value="{k}"{" selected" if (a.get("sort") or "reduction") == k else ""}>{t}</option>'
                      for k, t in (('reduction', 'Biggest reduction asked'), ('output', 'Largest output'), ('name', 'Company name')))
            + f'</select></div><div class="btns"><button>Show</button><a class="btn sec" href="{B}/ccts">Reset</a></div></div></form>')
    shown = rows[:300]
    body = ''.join(
        f'<tr><td><b>{E(r[1])}</b><div class="small mut">{E(r[0])}{" · " + E(r[4]) if r[4] else ""}</div></td><td>{E(r[3])}</td><td>{E(r[5] or "-")}</td>'
        f'<td class="n hide-s">{n(r[6])} {"MBBLS" if (r[7] or "").startswith("thousand") else "t"}</td><td class="n">{n(r[8], 3)}</td>'
        f'<td class="n hide-s">{n(r[9], 3)}</td><td class="n">{n(r[10], 3)}</td><td class="n"><span class="pill {"ok" if (r[11] or 0) >= 10 else "warn"}">{n(r[11], 1)}%</span></td></tr>'
        for r in shown)
    tbl = (f'<div class="card"><div class="btns noprint" style="justify-content:space-between;margin-bottom:8px"><h2 style="margin:0">{len(rows):,} entities'
           f'{" (first 300 shown)" if len(rows) > 300 else ""}</h2><a class="btn sec" href="{B}/ccts?{urlencode({**{k: v for k, v in a.items() if k != "csv"}, "csv": "1"})}">Download CSV</a></div>'
           f'<div class="wrap"><table><thead><tr><th>Entity</th><th>Sector</th><th>State</th><th class="n hide-s">Output</th><th class="n">Baseline GEI</th>'
           f'<th class="n hide-s">Target 2025-26</th><th class="n">Target 2026-27</th><th class="n">Reduction</th></tr></thead><tbody>{body or "<tr><td colspan=8>No entity matches.</td></tr>"}</tbody></table></div>'
           f'<div class="src">GEI = greenhouse gas emission intensity (tonnes CO2e per unit of output). Reduction = fall from the baseline to the 2026-27 target.</div></div>')
    src = ''.join(f'<li>{E(r[0])}: {r[1]:,} entities</li>' for r in notes)
    out = (tiles + f'<div class="two" style="grid-template-columns:3fr 2fr"><div class="card"><h2>By sector</h2><div class="wrap"><table><thead><tr><th>Sector</th><th class="n">Entities</th><th></th>'
           f'<th class="n">Avg reduction</th><th class="n hide-s">Range</th><th class="n hide-s">Output</th><th class="n hide-s">States</th></tr></thead><tbody>{sec_rows}</tbody></table></div></div>'
           f'<div class="card"><h2>Top states by number of entities</h2><div class="wrap"><table><thead><tr><th>State</th><th class="n">Entities</th><th class="n">Sectors</th></tr></thead>'
           f'<tbody>{st_rows}</tbody></table></div></div></div><div style="height:16px"></div>' + form + tbl +
           f'<div class="card"><h2>Where this comes from</h2><p class="mut small" style="margin:0 0 8px">Obligated entities and targets of the Indian Carbon Credit Trading Scheme (compliance market), '
           f'read from the Ministry of Environment, Forest and Climate Change gazette notifications:</p><ul class="small">{src}</ul>'
           f'<p class="small mut" style="margin:8px 0 0">Targets are intensity targets per unit of output, not total emission caps. Check the gazette before you rely on a figure.</p></div>')
    return frame('India CCTS', out, 'ccts', 'Companies and plants that must cut emission intensity under the Indian Carbon Credit Trading Scheme, with their baseline and targets.')


# ------------------------------------------------------------------ EU link page, inside the dashboard's site
@bp.route('/eu-link')
@bp.route('/eu-link/')
def eu_link():
    p = os.path.join(HERE, 'chat', 'eu-link.html')
    if not os.path.exists(p):
        return frame('EU link', msg('The EU link page file is missing. Run update_dashboard.command again.', 'bad'), 'eu')
    s = open(p, encoding='utf-8').read()
    bar = ('<div style="position:sticky;top:0;z-index:9999;background:#0E1410;color:#F6F7F2;font:600 13px/1 Geist,Arial,sans-serif;'
           'padding:9px 14px;display:flex;gap:16px;align-items:center;flex-wrap:wrap"><span style="color:#8fd19e">C-GEM</span>'
           '<a href="/superset/dashboard/cgem/?desktop=1" style="color:#F6F7F2">Back to the dashboard</a>'
           f'<a href="{B}/" style="color:#F6F7F2">Find projects</a><a href="{B}/countries" style="color:#F6F7F2">Compare countries</a></div>')
    s = re.sub(r'(<body[^>]*>)', r'\1' + bar.replace('\\', '\\\\'), s, count=1)
    return Response(s, mimetype='text/html')


# ------------------------------------------------------------------ the C-GEM India price platform, served from the folder price_model/
@bp.route('/price-model')
def price_model_root():
    return frame('Not found', msg('This page is not available here.', 'warn')), 404
    return redirect('/price-model/')


@bp.route('/price-model/')
@bp.route('/price-model/<path:fn>')
def price_model(fn='index.html'):
    return frame('Not found', msg('This page is not available here.', 'warn')), 404
    from flask import send_from_directory
    root = os.path.join(HERE, 'price_model')
    if fn.endswith('/'):
        fn += 'index.html'
    p = os.path.normpath(os.path.join(root, fn))
    if not p.startswith(root + os.sep) or not os.path.isfile(p):
        return frame('Not found', msg('This page of the price platform is not on this computer. Run update_dashboard.command, or open the '
                                      '<a href="https://cgem-price-model.onrender.com/">online price platform</a>.', 'warn')), 404
    if fn.endswith('.html'):
        s = open(p, encoding='utf-8').read()
        bar = ('<div style="background:#0E1410;color:#F6F7F2;font:600 13px/1 Geist,Arial,sans-serif;padding:9px 14px;display:flex;gap:16px;'
               'align-items:center;flex-wrap:wrap"><span style="color:#8fd19e">C-GEM</span>'
               '<a href="/superset/dashboard/cgem/?desktop=1" style="color:#F6F7F2">Back to the dashboard</a>'
               f'<a href="{B}/" style="color:#F6F7F2">Find projects</a><a href="/eu-link" style="color:#F6F7F2">EU link</a>'
               '<span style="margin-left:auto;font-weight:400;opacity:.7">India price model, copy on this computer</span></div>')
        s = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + bar, s, count=1)
        if 'href="lab.html"' not in s:                  # the Price Lab (this computer only) in the platform's menu
            s = s.replace('<a class="l" href="weekly.html"', '<a class="l" href="lab.html">Price Lab</a><a class="l" href="weekly.html"', 1)
        return Response(s, mimetype='text/html')
    return send_from_directory(root, fn, max_age=600)
