"""C-GEM v58 update for the online site: the district explorer drop-down lists districts (grouped by state)."""
import html
import json

from superset.app import create_app

PAIRS = json.loads("[[\"$('fs').innerHTML='<option value=\\\"\\\">All states ('+states.length+')</option>'+states.map(function(s){return '<option>'+esc(s)+'</option>';}).join('');\", \"var DN=DL.filter(function(g){return !g.nr;});var byst={};DN.forEach(function(g){(byst[g.st]=byst[g.st]||[]).push(g);});\\n$('fs').innerHTML='<option value=\\\"\\\">All districts ('+DN.length+')</option>'+Object.keys(byst).sort().map(function(s){return '<optgroup label=\\\"'+esc(s)+'\\\">'+byst[s].sort(function(a,b){return a.di.localeCompare(b.di);}).map(function(g){return '<option value=\\\"'+esc(g.k)+'\\\">'+esc(g.di)+'</option>';}).join('')+'</optgroup>';}).join('');\"], [\"if(fs&&g.st!==fs)return false;\", \"if(fs&&g.k!==fs)return false;\"]]")


def fix(obj):
    if isinstance(obj, str):
        for a, b in PAIRS:
            obj = obj.replace(a, b)
            obj = obj.replace(html.escape(a, quote=True), html.escape(b, quote=True))
            obj = obj.replace(html.escape(a, quote=True).replace('\n', '&#10;'), html.escape(b, quote=True).replace('\n', '&#10;'))
        return obj
    if isinstance(obj, list):
        return [fix(x) for x in obj]
    if isinstance(obj, dict):
        return {k: fix(v) for k, v in obj.items()}
    return obj


app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    n = 0
    for sl in db.session.query(Slice).all():
        if not sl.params or 'All states (' not in sl.params:
            continue
        d = json.loads(sl.params)
        d2 = fix(d)
        if d2 != d:
            sl.params = json.dumps(d2)
            n += 1
    db.session.commit()
    print('v58 patch: district explorer updated', n)
