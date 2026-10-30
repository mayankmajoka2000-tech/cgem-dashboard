"""C-GEM v52 update for the online site: new India Atlas, leaderboard, developer, stage and chatbot text."""
import html
import json
import re

HERE = '/app/cgem'
PAIRS = [["Indian states and union territories leaderboard: credits issued, retired and vintage", "States and union territories ranked by credits issued, with retirement and vintage"], ["<span>Credits issued, retired part dark</span>", "<span>Credits issued (dark share = retired)</span>"], ["Ranked by number of projects. UT = union territory. Retired badge: green at or above the 52.4% dataset benchmark.", "Ranked by number of projects. UT = union territory. Green badge: retirement rate at or above India's average of 34.5%."], ["Share of Indian projects by sector (bar on top). Icons show the type of activity.", "Share of Indian projects by sector. Icons show the type of activity."], ["Click a district to list its sectors and sub-sectors; point at one for its numbers. Use the buttons above to go back.", "Select a district to see its figures. Use \"Back to all states\" or select another state to return."], ["['Average vintage',T.v?(T.av/T.v).toFixed(1):'n/a','credit-weighted']", "['Average vintage',T.v?String(Math.round(T.av/T.v)):'n/a',T.v?'weighted by credits (about '+Math.round(2026-T.av/T.v)+' years old)':'weighted by credits']"], ["x.a.toFixed(1)+'<small>'", "Math.round(x.a)+'<small>'"], ["Being developed, listed or validated: no registration yet", "Being developed, listed or under validation. Not yet registered."], ["Registered with the programme; earning or waiting to verify credits", "Registered, and generating credits or awaiting verification."], ["Credits verified, issued or the project completed", "Credits verified or issued, or crediting completed."], ["'Withdrawn, rejected, cancelled, suspended or inactive'", "'Withdrawn, rejected, cancelled, suspended or inactive.'"], ["The registry does not show a usable status", "The registry record gives no clear status."], ["$('hd').innerHTML='<b>'+int(TOT)+'</b> projects in <b>'+main+'</b> main stages. Click a stage to list its projects below, then search, filter by registry status and sort.';", "var NU=(G['5']||[]).length;$('hd').innerHTML='<b>'+int(TOT)+'</b> projects across '+['zero','one','two','three','four'][main]+' main stages'+(NU?', plus <b>'+int(NU)+'</b> whose status is unclear':'')+'. Select a stage to list its projects, then search, filter by registry status or sort.';"], ["Ranked by credits issued. Developer = project proponent named on the registry; for Universal Carbon Registry projects, the named representative or aggregator. Generic entries (multiple proponents, not recorded) are left out.", "Ranked by credits issued. The developer is the project proponent named on the registry, or the named representative or aggregator for Universal Carbon Registry projects. Entries listed as \"multiple proponents\" or \"not recorded\" are excluded."], ["printf('%.1f', SUM(CASE WHEN lvl = 'v' THEN v_year * v_cred END) / ", "printf('%.0f', SUM(CASE WHEN lvl = 'v' THEN v_year * v_cred END) / "], ["printf('%.1f', SUM(SUM(CASE WHEN lvl = 'v'", "printf('%.0f', SUM(SUM(CASE WHEN lvl = 'v'"], ["printf('%.1f', SUM(vintage_year * credits_issued)", "printf('%.0f', SUM(vintage_year * credits_issued)"]]
RENAME = {"Top 15 Indian states and union territories: projects, credits issued and retired": "Top 15 states by number of projects: credits issued and retired", "What Indian projects do: projects by sector": "Indian projects by sector", "India: states and districts (click a state, then a district, to see its sectors and sub-sectors)": "India: projects by state and district (select a state to zoom in)", "Indian states and union territories leaderboard: credits issued, retired and vintage": "States and union territories ranked by credits issued, with retirement and vintage"}
MD = {"State by State": ["<div style=\"font-family:Geist,Inter,'Segoe UI',Arial,sans-serif;padding:6px 2px 8px;border-bottom:2px solid #C98A1F\"><div style=\"font-size:20px;font-weight:700;color:#0E1410\">Leading states and sectors</div><div style=\"font-size:14px;color:#555555;margin-top:3px\">The 15 states with the most carbon projects in C-GEM's dataset, the credits each has issued and the share already retired, alongside the activities Indian projects undertake.</div></div>", 14], "States and union territories leaderboard": ["<div style=\"font-family:Inter,Segoe UI,Arial,sans-serif;padding:6px 2px 8px;border-bottom:2px solid #C98A1F\"><div style=\"font-size:20px;font-weight:700;color:#2b2b2b\">State and union territory leaderboard</div><div style=\"font-size:14px;color:#5a5a5a;margin-top:2px\">India has 28 states and 8 union territories. C-GEM's dataset records carbon projects in 27 states (none yet in Mizoram) and 5 union territories: Chandigarh, Dadra and Nagar Haveli and Daman and Diu, Delhi, Jammu and Kashmir, and Ladakh. Each row is tagged as a state or union territory. Use the buttons to view one group.<div style=\"font-size:12.5px;color:#666;margin-top:5px\">These figures cover projects in C-GEM's dataset, compiled from 14 public registries up to October 2026. They are not a complete count of every carbon project in India, and coverage will widen as more sources are added.</div></div></div>", 19], "The organisations behind the projects": ["<div style=\"font-family:Inter,Segoe UI,Arial,sans-serif;padding:6px 2px 8px;border-bottom:2px solid #B85829\"><div style=\"font-size:20px;font-weight:700;color:#2b2b2b\">Top project developers</div><div style=\"font-size:14px;color:#5a5a5a;margin-top:2px\">The organisations whose projects have issued the most credits, in India and worldwide.</div></div>", 12]}
INSTATES = 'Top 15 states by number of projects: credits issued and retired'


def fix(obj, pairs):
    """Replace text inside every string of a decoded JSON value (plain and HTML-escaped forms)."""
    if isinstance(obj, str):
        for a, b in pairs:
            obj = obj.replace(a, b)
            ha, hb = html.escape(a, quote=True), html.escape(b, quote=True)
            if ha != a:
                obj = obj.replace(ha, hb)
        return obj
    if isinstance(obj, list):
        return [fix(x, pairs) for x in obj]
    if isinstance(obj, dict):
        return {k: fix(v, pairs) for k, v in obj.items()}
    return obj


from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard
    n = 0
    for sl in db.session.query(Slice).all():
        if sl.slice_name in RENAME:
            sl.slice_name = RENAME[sl.slice_name]
        p = sl.params or ''
        if not p:
            continue
        pairs = PAIRS + ([[">= 0.524 THEN 'hi'", ">= 0.345 THEN 'hi'"]] if sl.slice_name == INSTATES else [])
        d = json.loads(p)
        d2 = fix(d, pairs)
        if d2 != d:
            sl.params = json.dumps(d2)
            n += 1
    for dash in db.session.query(Dashboard).all():
        pos = json.loads(dash.position_json or '{}')
        names = {s.id: s.slice_name for s in db.session.query(Slice).all()}
        for k, v in pos.items():
            if not isinstance(v, dict):
                continue
            meta = v.get('meta') or {}
            if v.get('type') == 'MARKDOWN':
                for match, (code, h) in MD.items():
                    if match in (meta.get('code') or ''):
                        meta['code'] = code
                        meta['height'] = h
            if v.get('type') == 'CHART' and (names.get(meta.get('chartId')) or '').startswith('Top 10 project developers'):
                meta['height'] = 106
        dash.position_json = json.dumps(pos)
    db.session.commit()
    print('v52 patch: charts updated', n)


# chatbot files
FILE_PAIRS = {"cgem_chat.py": [["    ent_view = {k: v for k, v in ent.items() if k != '_rest'}\n", "    ent_view = {k: v for k, v in ent.items() if k != '_rest'}\n    if has(qn, 'ccts', 'carbon credit trading scheme', 'carbon market of india', \"india's carbon market\", 'indias carbon market', 'india carbon market', 'bharat carbon market'):\n        return ans(\"India's carbon market (CCTS)\",\n                   \"India's Carbon Credit Trading Scheme (CCTS), notified on 28 June 2023, sets up a domestic carbon market with a compliance route for obligated industries \"\n                   'and an offset route under which voluntary projects in India can earn Carbon Credit Certificates.',\n                   points=['**Who runs it:** Bureau of Energy Efficiency (administrator) and Grid Controller of India (registry); trading is planned on the power exchanges.',\n                           '**Price:** no exchange price has been published yet.',\n                           '**Why it matters:** domestic demand and Article 6 authorisations are the main ways for Indian credits to reach the premium end of the market.'],\n                   meaning='CCTS credits are separate from the voluntary registry credits counted in this dashboard; projects may move between the two routes as the rules develop.',\n                   source='Bureau of Energy Efficiency (beeindia.gov.in), CCTS notifications; status as of mid-2026. Not part of the C-GEM project dataset.',\n                   kind='term', followups=['Credits issued in India', 'Top 10 states by credits retired', 'What is Article 6.4?']), 0.95\n"], ["\nSCRIPT_TAG = '<script src=\"/cgem-static/cgem_chat.js?v=25\" defer></script>'\n", "\nSCRIPT_TAG = '<script src=\"/cgem-static/cgem_chat.js?v=26\" defer></script>'\n"]], "chat/cgem_chat.js": [["  var btn = el('div', 'cgs-btn'); btn.title = 'Ask C-GEM Saathi';\n  var hello = el('div', 'cgs-hello', '<b>Namaste! I am C-GEM Saathi.</b><span>Ask me anything about carbon credits and this dashboard.</span>');\n", "  var btn = el('div', 'cgs-btn'); btn.title = 'Ask C-GEM Saathi';\n  var hello = el('div', 'cgs-hello', \"<b>Namaste! I'm C-GEM Saathi.</b><span>Ask me about carbon credits and I'll answer with figures from this dashboard.</span>\");\n"], ["      if (r.source) h += '<div class=\"cgs-sec\"><h5>Source</h5><div class=\"cgs-src\">' + inl(r.source) + '</div></div>';\n      if (r.followups && r.followups.length) h += '<div class=\"cgs-sec\"><h5>You can also ask</h5>' + chips(r.followups) + '</div>';\n", "      if (r.source) h += '<div class=\"cgs-sec\"><h5>Source</h5><div class=\"cgs-src\">' + inl(r.source) + '</div></div>';\n      if (r.followups && r.followups.length) h += '<div class=\"cgs-sec\"><h5>' + esc(r.fuTitle || 'You can also ask') + '</h5>' + chips(r.followups) + '</div>';\n"], ["    var b = botWrap();\n    render(b, { kind: 'help', title: 'Namaste! I am C-GEM Saathi', answer: 'I answer questions about carbon credits with numbers from this dashboard, always in the same order: **answer, key numbers, what it means, source** and **next questions**.',\n      points: ['Hindi, Hinglish and English all work.', '**Dashboard data** mode needs no key. **AI** mode answers any question (set it up in Settings).'],\n      followups: ['Credits issued in India', 'Top 10 Indian states by credits retired', 'India vs China', 'Live price of Indian credits', 'What is vintage?', 'Top 20 buyers of Indian credits'] });\n", "    var b = botWrap();\n    render(b, { kind: 'help', title: \"Namaste! I'm C-GEM Saathi.\", answer: \"Ask me about carbon credits and I'll answer with figures from this dashboard, showing the source each time.\",\n      points: ['Ask in Hindi, Hinglish or English.', \"Dashboard data answers come from C-GEM's dataset. AI mode answers general questions and does not check them against our data.\"],\n      fuTitle: 'Try asking',\n      followups: ['Credits issued in India', 'Top 10 states by credits retired', 'India vs China: projects and credits', 'What is vintage?', 'Top 20 named buyers of Indian credits', \"What is India's carbon market (CCTS)?\"] });\n"]]}
for fn, ps in FILE_PAIRS.items():
    path = HERE + '/' + fn
    s = open(path).read()
    for a, b in ps:
        if a in s:
            s = s.replace(a, b, 1)
    open(path, 'w').write(s)
print('v52 patch: chatbot files updated')
