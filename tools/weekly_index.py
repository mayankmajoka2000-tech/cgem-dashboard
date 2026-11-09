"""Publish one weekly issue of the C-GEM India Carbon Index from the current model (docs/api/latest.json)
and the project register (docs/data/projects.csv).

Run every Monday:  python3 tools/weekly_index.py [YYYY-MM-DD]
Writes docs/api/weekly/<date>.json, updates docs/api/weekly/index.json (the archive) and latest.json.

Index definitions
- Type price: model price for an Indian credit of that type, recent vintage, no rating (US$/tCO2e).
- India Basket: geometric mean of type prices weighted by each type's share of risk-adjusted annual
  credits across the 5,013 Indian projects (what India actually supplies).
- Sub-indices: the same weighted mean over removal types, avoidance types, and nature-based types.
- Level: basket price relative to issue 1 (= 100).
"""
import csv, json, math, os, sys, datetime
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs')
date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
api = json.load(open(os.path.join(ROOT, 'api', 'latest.json')))
types = api['types']
vol = {}
for p in csv.DictReader(open(os.path.join(ROOT, 'data', 'projects.csv'), encoding='utf-8')):
    try: vol[p['credit_type']] = vol.get(p['credit_type'], 0) + float(p['risk_adjusted_credits'] or 0)
    except ValueError: pass
NATURE = {'Afforestation / reforestation (ARR)', 'Agroforestry', 'REDD+ (avoided deforestation)', 'Blue carbon (mangrove, wetland)', 'Soil carbon / regenerative agriculture'}

def basket(names):
    w = {t: vol.get(t, 0) for t in names if t in types and t != 'Other / not classified'}
    tot = sum(w.values())
    if tot <= 0: return None
    return math.exp(sum(v / tot * math.log(types[t]['price']) for t, v in w.items()))

subs = {
    'India Basket': basket(types),
    'Removals': basket([t for t in types if types[t]['removal']]),
    'Avoidance': basket([t for t in types if not types[t]['removal']]),
    'Nature-based': basket([t for t in types if t in NATURE]),
}
wdir = os.path.join(ROOT, 'api', 'weekly'); os.makedirs(wdir, exist_ok=True)
arch_f = os.path.join(wdir, 'index.json')
arch = json.load(open(arch_f)) if os.path.exists(arch_f) else {'issues': []}
arch['issues'] = [i for i in arch['issues'] if i['date'] != date]
prev = arch['issues'][-1] if arch['issues'] else None
base = arch['issues'][0]['basket_price'] if arch['issues'] else subs['India Basket']
issue = {
    'index': 'C-GEM India Carbon Index', 'issue': len(arch['issues']) + 1, 'date': date, 'model_version': api['version'],
    'basket_price': round(subs['India Basket'], 4), 'level': round(100 * subs['India Basket'] / base, 2),
    'sub_indices': {k: round(v, 4) for k, v in subs.items() if v},
    'weights': {t: round(vol.get(t, 0) / sum(vol.get(x, 0) for x in types if x != 'Other / not classified'), 4) for t in types if t != 'Other / not classified'},
    'types': {t: {k: types[t][k] for k in ('price', 'p10', 'p90', 'confidence')} for t in types},
    'change_vs_previous': None,
    'notes': 'Model-based index from public data; not a traded price. Method: docs/methodology.html.',
}
if prev:
    pv = json.load(open(os.path.join(wdir, prev['date'] + '.json')))
    issue['change_vs_previous'] = {'basket': round(issue['basket_price'] / pv['basket_price'] - 1, 4),
                                   'types': {t: round(issue['types'][t]['price'] / pv['types'][t]['price'] - 1, 4) for t in issue['types'] if t in pv['types']},
                                   'model_changed': pv['model_version'] != issue['model_version']}
json.dump(issue, open(os.path.join(wdir, date + '.json'), 'w'), indent=1)
json.dump(issue, open(os.path.join(wdir, 'latest.json'), 'w'), indent=1)
arch['issues'].append({'issue': issue['issue'], 'date': date, 'model_version': issue['model_version'], 'basket_price': issue['basket_price'], 'level': issue['level']})
json.dump(arch, open(arch_f, 'w'), indent=1)
print(json.dumps({k: issue[k] for k in ('issue', 'date', 'model_version', 'basket_price', 'level', 'sub_indices')}, indent=1))
