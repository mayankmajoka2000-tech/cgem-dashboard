"""Retrain the C-GEM price model (v20: v18 structure plus CIX India agri-carbon averages; Article 6 / CORSIA effect differs in 2026 and for cookstoves) (0.2 x hierarchical model with literature priors + 0.8 x robust Huber regression) from training_data.csv and rewrite the 'ml' block of price_model.json.

Model: weighted generalised ridge on ln(price). Each block of coefficients has its own penalty
(= a mixed model with random intercepts by credit type and type x Asia, and random slopes for vintage
and rating by type). Weights = sqrt(volume) x price-class weight (avg / deal / list).
Intervals: normalised split-conformal from leave-one-out residuals on deal prices.
Run:  python train_price_model.py
"""
import csv, json, math, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, 'price_model.json'))); ML0 = P['ml']
LAM, SCH = ML0['lam'], ML0['scheme']; LAM.setdefault('auth_x', 1.0)
TYPES = ['forestry','re','industrial','household','waste','agri','ee','transport','redd','ifm','arr','agroforestry','blue','biochar','rice','soil']
STD = ['VCS','ACR','GS','CDM','CAR','PlanVivo','UKWCC','CSA','Cercarbono']; REG = ['latam','namerica','asia','africa','europe','oceania']; YRS = range(2020, 2027)
SLOPE_T = ['re','household','forestry','arr','redd','biochar','agri','waste']
BL = {'fixed': [f'year_{y}' for y in YRS] + ['removal','reduction','vint_recent','vint_old','rating_high','rating_low','authorised','ccp','kind_offer','kind_forward','platts_mc','small_lot','channel_onchain','channel_retail','auth_2026'],
      'std': [f'std_{s}' for s in STD], 'region': [f'reg_{r}' for r in REG] + ['india'], 'type': [f'type_{t}' for t in TYPES],
      'type_x_asia': [f'type_{t}*asia' for t in SLOPE_T], 'slope_vint': [f'vint_old*type_{t}' for t in SLOPE_T],
      'slope_rating': [f'rating_high*type_{t}' for t in SLOPE_T],
      'auth_x': ['authorised*type_household'],
      'india_x_type': [f'india*type_{t}' for t in ['re','biochar','household','agri','forestry','waste']],
      'slope_time': [f'time*type_{t}' for t in ['re','household']],
      'chan_x': [f'{c}*{t}' for c in ['channel_onchain','channel_retail'] for t in ['type_re','type_household','type_forestry','type_arr','type_redd','type_agri','type_waste','type_biochar','india','reg_asia','vint_old']]}
COLS = [c for b in BL.values() for c in b]; BOF = {c: b for b, cs in BL.items() for c in cs}
CATMAP = {'Renewable energy':['re'],'Household devices (cookstoves, lighting, water)':['household'],'Waste (methane, composting, waste-to-energy)':['waste'],'Rice methane (AWD, DSR, SRI)':['agri','rice'],'Soil carbon / regenerative agriculture':['agri','soil'],'Livestock and other agriculture methane':['agri'],'Energy efficiency and fuel switching':['ee'],'Industrial and chemical processes':['industrial'],'Transport':['transport'],'Afforestation / reforestation (ARR)':['forestry','arr'],'Agroforestry':['forestry','agroforestry'],'REDD+ (avoided deforestation)':['forestry','redd'],'Blue carbon (mangrove, wetland)':['forestry','blue'],'Biochar and engineered removal':['biochar'],'Other / not classified':[]}
REMCAT = {'Soil carbon / regenerative agriculture','Afforestation / reforestation (ARR)','Agroforestry','Blue carbon (mangrove, wetland)','Biochar and engineered removal'}


def vec(r):
    x = dict.fromkeys(COLS, 0.0)
    if r['year']: x[f"year_{int(float(r['year']))}"] = 1
    for t in filter(None, r['types'].split('|')): x['type_' + t] = 1
    if r['standard']: x['std_' + r['standard']] = 1
    if r['region']: x['reg_' + r['region']] = 1
    if r['removal'] == '1': x['removal'] = 1
    if r['removal'] == '0': x['reduction'] = 1
    if r['vintage'] in ('recent', 'old'): x['vint_' + r['vintage']] = 1
    if r['india'] == '1': x['india'] = 1
    if r['rating'] in ('high', 'low'): x['rating_' + r['rating']] = 1
    if r['authorised'] == '1': x['authorised'] = 1
    if r.get('ccp') == '1': x['ccp'] = 1
    if r.get('price_kind') in ('offer', 'forward'): x['kind_' + r['price_kind']] = 1
    if r.get('platts_mc') == '1': x['platts_mc'] = 1
    if r.get('small_lot') == '1': x['small_lot'] = 1
    if r['channel']: x['channel_' + r['channel']] = 1
    asia = x['reg_asia'] or x['india']
    for t in SLOPE_T:
        x[f'type_{t}*asia'] = x['type_' + t] * asia; x[f'vint_old*type_{t}'] = x['vint_old'] * x['type_' + t]; x[f'rating_high*type_{t}'] = x['rating_high'] * x['type_' + t]
    for t in ['re','biochar','household','agri','forestry','waste']: x[f'india*type_{t}'] = x['india'] * x['type_' + t]
    tn = ((float(r['year']) - 2023) / 3.0) if r['year'] else 0.0
    for t in ['re','household']: x[f'time*type_{t}'] = tn * x['type_' + t]
    x['authorised*type_household'] = x['authorised'] * x['type_household']
    x['auth_2026'] = x['authorised'] * (1 if r['year'] and int(float(r['year'])) == 2026 else 0)
    for c in BL['chan_x']:
        a, b = c.split('*'); x[c] = x[a] * x[b]
    return np.array([x[c] for c in COLS])


PRIOR = ML0.get('prior', {}); PS = ML0.get('prior_strength', 3); BW = ML0.get('blend', {'w_prior': 0.2, 'w_huber': 0.8})


def fit_prior(X, y, w):
    pen = np.array([LAM[BOF[c]] * (PS if BOF[c] == 'fixed' else 1) for c in COLS]); mu = np.array([PRIOR.get(c, 0.0) for c in COLS])
    Xm = np.hstack([np.ones((len(y), 1)), X]); P_ = np.concatenate([[0], pen]); M_ = np.concatenate([[0], mu])
    return np.linalg.solve(Xm.T @ (Xm * w[:, None]) + np.diag(P_), Xm.T @ (w * y) + P_ * M_)


def fit(X, y, w):
    from sklearn.linear_model import HuberRegressor
    bp = fit_prior(X, y, w)
    h = HuberRegressor(alpha=0.3, epsilon=1.35, max_iter=3000).fit(X, y, sample_weight=w)
    return np.concatenate([[BW['w_prior'] * bp[0] + BW['w_huber'] * h.intercept_], BW['w_prior'] * bp[1:] + BW['w_huber'] * h.coef_])


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'training_data.csv'), encoding='utf-8')))
    X = np.array([vec(r) for r in rows]); y = np.log([float(r['price_usd']) for r in rows])
    cw = {'avg': SCH[0], 'deal': SCH[1], 'list': SCH[2]} if SCH != 'v5' else {'avg': 1, 'deal': 1, 'list': 1}
    dec = ML0.get('time_decay', 1.0)
    yrs = np.array([int(float(r['year'])) if r['year'] else 2024 for r in rows])
    w = np.sqrt([float(r['weight']) for r in rows]) * np.array([cw[r['price_class']] for r in rows]) * dec ** np.clip(2026 - yrs, 0, None)
    beta = fit(X, y, w); c = dict(zip(COLS, beta[1:]))
    # leave-one-out residuals -> normalised conformal interval by evidence group
    n = len(rows); p = np.zeros(n)
    for i in range(n):
        k = np.ones(n, bool); k[i] = False; b = fit(X[k], y[k], w[k]); p[i] = b[0] + X[i] @ b[1:]
    spec = lambda r: (r['types'].split('|')[-1] if r['types'] else None)
    nwh = {t: sum(1 for r in rows if r['price_class'] != 'list' and spec(r) == t) for t in TYPES}
    grp = np.array(['high' if (spec(r) is None or nwh.get(spec(r), 0) >= 6) else 'low' for r in rows])
    deal = np.array([r['price_class'] == 'deal' for r in rows]); res = y - p
    SC = {g: float(np.median(np.abs(res[deal & (grp == g)]))) for g in ('high', 'low')}
    SC['low'] = float(min(max(SC['low'], SC['high']), ML0.get('low_scale_cap', 1.5) * SC['high']))
    z = res / np.array([SC[g] for g in grp]); zq = np.quantile(z[deal], [0.1, 0.9])
    Q = {g: [float(zq[0] * SC[g]), float(zq[1] * SC[g])] for g in SC}
    types = {}
    for cat, ts in CATMAP.items():
        g = 'high' if (not ts or nwh.get(ts[-1], 0) >= 6) else 'low'
        old = min(c['vint_old'] + sum(c.get(f'vint_old*type_{t}', 0) for t in ts) - c['vint_recent'], 0.0)
        prev = ML0['types'].get(cat, {})
        types[cat] = {'type_effect': float(sum(c['type_' + t] + c.get(f'type_{t}*asia', 0) + c.get(f'india*type_{t}', 0) + c.get(f'time*type_{t}', 0) for t in ts)), 'removal': cat in REMCAT,
                      'old_vintage_adj': float(old), 'high_rating_effect': float(c['rating_high'] + sum(c.get(f'rating_high*type_{t}', 0) for t in ts)),
                      'p10_log': Q[g][0], 'p90_log': Q[g][1], 'auth_extra': float(c['authorised*type_household']) if cat.startswith('Household') else 0.0, 'confidence': prev.get('confidence', 'Low'),
                      'n_wholesale': nwh.get(ts[-1], 0) if ts else 0, 'ci90': prev.get('ci90')}
    ML0.update({'intercept': float(beta[0]), 'coef': {k: float(v) for k, v in c.items()}, 'types': types,
                'const': dict({k: float(c[k]) for k in ['year_2026','reg_asia','india','removal','vint_recent','rating_low']}, authorised=float(c['authorised'] + c['auth_2026'])), 'ccp_premium': round(float(np.exp(c['ccp'])), 3)})
    json.dump(P, open(os.path.join(HERE, 'price_model.json'), 'w'), indent=1)
    print(f'trained on {n} prices; LOO median error on deal prices {np.median(np.abs(np.exp(-res[deal]) - 1)):.1%}')


if __name__ == '__main__':
    main()
