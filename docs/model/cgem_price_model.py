"""C-GEM India carbon market model, version 14.

Price (US$ per tCO2e, 2026 market level) for an Indian voluntary carbon credit:
  * ML model v7 : 0.2 x hierarchical hedonic model with literature priors + 0.8 x robust Huber
                  regression (one linear equation), trained on 443 public prices 2020-2026
  * v2 model    : expert multiplicative formula, kept as a cross-check
  * Recommended : v2^w x ML^(1-w) x learned CCP premium if CCP-approved; w = 0 from cross-validation
Plus investor, CCTS and CBAM tools that match the Excel workbook.

    from cgem_price_model import price, project_finance, ccts_balance, cbam_cost, ccc_auction,
                                 portfolio_risk, scenario_2030, rating_value, integrity_score,
                                 monte_carlo_npv
C-GEM Research Team, 8 Nov 2026. Parameters are read from price_model.json.
"""
import json, math, os

_P = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'price_model.json')))
ML, V2 = _P['ml'], _P['v2']
TYPES = list(ML['types'])


def _f(name_start):
    for k, v in V2['factors'].items():
        if k.startswith(name_start):
            return v
    raise KeyError(name_start)


def ml_price(credit_type, vintage=None, rating=None, authorised=False, basis_year=2026):
    """ML v7 estimate for an Indian credit (wholesale). Returns (middle, p10, p90)."""
    t, c = ML['types'][credit_type], ML['const']
    lnp = ML['intercept'] + c['year_2026'] + c['reg_asia'] + c['india'] + t['type_effect'] + c['vint_recent']
    if t['removal']: lnp += c['removal']
    if vintage is not None and basis_year - vintage > 5: lnp += t['old_vintage_adj']
    if rating == 'high': lnp += t['high_rating_effect']
    if rating == 'low': lnp += c['rating_low']
    if authorised: lnp += c['authorised']
    mid = math.exp(lnp)
    return mid, mid * math.exp(t['p10_log']), mid * math.exp(t['p90_log'])


def v2_price(credit_type, vintage=None, cobenefit=False, ccp=False, rating=None, corsia=False, cdm=False, basis_year=2025):
    """v2 expert formula model (cross-check). Returns (middle, p10, p90)."""
    cat = V2['categories'][credit_type]
    parts = [_f('Market level')]
    cut = _f('Vintage cut-off')['central']
    parts.append(_f('Vintage: older') if (vintage is not None and basis_year - vintage > cut) else _f('Vintage: recent'))
    for flag, name in [(cobenefit, 'Co-benefit'), (ccp, 'ICVCM CCP'), (rating == 'high', 'Rating: high'), (rating == 'low', 'Rating: low'), (corsia, 'CORSIA'), (cdm, 'Registry: CDM')]:
        if flag: parts.append(_f(name))
    mid = cat['base'] * cat['india_factor'] * math.prod(p['central'] for p in parts)
    sig = math.sqrt(cat['sigma_base'] ** 2 + cat['sigma_india'] ** 2 + sum(p['sigma'] ** 2 for p in parts))
    z = V2['z80']
    return mid, mid * math.exp(-z * sig), mid * math.exp(z * sig)


def price(credit_type, vintage=None, cobenefit=False, ccp=False, rating=None, corsia=False, cdm=False):
    """Recommended price with P10/P90, plus the two model estimates and a confidence label."""
    v = v2_price(credit_type, vintage, cobenefit, ccp, rating, corsia, cdm)
    m = ml_price(credit_type, vintage, rating, corsia)
    w, prem = ML['w_v2'], (ML['ccp_premium'] if ccp else 1.0)
    rec = tuple(a ** w * b ** (1 - w) * prem for a, b in zip(v, m))
    return {'recommended': rec, 'ml': m, 'v2': v, 'confidence': ML['types'][credit_type]['confidence']}


def project_finance(price, est_annual, realisation=0.77, delay=2, years=10, growth=0.03, buffer=0.0, share=0.10,
                    capex=300000, opex=25000, verification=25000, fee=0.20, rate=0.12, offtake_price=None,
                    default_prob=0.05, p10=None, p90=None):
    """Same logic as the 'Investor calculator' sheet. Returns NPV, IRR, LCOC, offtake PV and VaR."""
    T = delay + years
    q = [est_annual * realisation * (1 - buffer) if delay < t <= T else 0.0 for t in range(T + 1)]
    pr = [price * (1 + growth) ** max(t - 1, 0) for t in range(T + 1)]
    rev = [q[t] * pr[t] * (1 - share) for t in range(T + 1)]
    cost = [capex if t == 0 else opex + ((verification + fee * q[t]) if q[t] > 0 else 0) for t in range(T + 1)]
    cf = [a - b for a, b in zip(rev, cost)]
    df = [(1 + rate) ** -t for t in range(T + 1)]
    npv = sum(a * b for a, b in zip(cf, df))
    lcoc = sum(a * b for a, b in zip(cost, df)) / sum(q[t] * (1 - share) * df[t] for t in range(T + 1))
    irr = None
    lo, hi = -0.99, 10.0
    f = lambda r: sum(cf[t] / (1 + r) ** t for t in range(T + 1))
    if f(lo) * f(hi) < 0:
        for _ in range(200):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
        irr = (lo + hi) / 2
    F = offtake_price if offtake_price is not None else 0.85 * price
    off_pv = sum(q[t] * F * (1 - default_prob) ** t * df[t] for t in range(T + 1))
    out = {'npv': npv, 'irr': irr, 'lcoc': lcoc, 'credits': sum(q), 'offtake_pv': off_pv,
           'prepay_discount': 1 - off_pv / (F * sum(q)) if sum(q) else None}
    if p10 and p90:
        sig = (math.log(p90) - math.log(p10)) / (2 * 1.2816)
        out['sigma'] = sig; out['var95_1y'] = max(rev) * (1 - math.exp(-1.645 * sig))
    return out


def ccts_balance(output, gei_baseline, target_cut, gei_actual, ccc_price_inr):
    """CCTS obligated entity: CCCs earned (+) or needed (-), their value and the penalty (2x price) if a shortfall is not covered."""
    target = gei_baseline * (1 - target_cut)
    cccs = (target - gei_actual) * output
    return {'target_gei': target, 'cccs': cccs, 'value_inr': cccs * ccc_price_inr,
            'penalty_inr': -2 * ccc_price_inr * cccs if cccs < 0 else 0.0}


def ccc_auction(bids, offers, floor=None, ceiling=None, step=50, pmax=3000):
    """Uniform-price double auction. bids/offers = [(price, qty)]. Returns (clearing price, matched volume)."""
    grid = [i * step for i in range(pmax // step + 1)]
    matched = [min(sum(q for p, q in bids if p >= g), sum(q for p, q in offers if p <= g)) for g in grid]
    best = max(matched)
    pc = sum(g for g, m in zip(grid, matched) if m == best) / matched.count(best)
    if floor is not None: pc = max(pc, floor)
    if ceiling is not None: pc = min(pc, ceiling)
    return pc, best


def cbam_cost(tonnes, embedded, benchmark=0.0, factor=0.975, cbam_price=82.32, paid=0.0):
    """EU CBAM cost (EUR) = max(0, embedded - factor x benchmark) x tonnes x (CBAM price - carbon price paid)."""
    certs = max(0.0, embedded - factor * benchmark) * tonnes
    cost = certs * max(0.0, cbam_price - paid)
    return {'certificates': certs, 'cost_eur': cost, 'cost_per_tonne_eur': cost / tonnes}


TYPE_RISK = {
 "Renewable energy": 0.2,
 "Household devices (cookstoves, lighting, water)": 0.4,
 "Energy efficiency and fuel switching": 0.45,
 "Industrial and chemical processes": 0.5,
 "Transport": 0.5,
 "Waste (methane, composting, waste-to-energy)": 0.7,
 "Livestock and other agriculture methane": 0.7,
 "Rice methane (AWD, DSR, SRI)": 0.6,
 "Soil carbon / regenerative agriculture": 0.5,
 "Afforestation / reforestation (ARR)": 0.7,
 "Agroforestry": 0.65,
 "REDD+ (avoided deforestation)": 0.4,
 "Blue carbon (mangrove, wetland)": 0.7,
 "Biochar and engineered removal": 0.9,
 "Other / not classified": 0.5
}
INTEGRITY_WEIGHTS = {
 "Additionality and over-crediting risk of the credit type": 30,
 "ICVCM CCP status of the methodology": 20,
 "Delivery record (realisation ratio)": 15,
 "Vintage age": 10,
 "Co-benefit label": 10,
 "Activity status": 10,
 "India Article 6 list match": 5
}


def integrity_score(credit_type, ccp_status='not assessed', realisation=None, latest_vintage=None, cobenefit=False,
                    status='active', article6_match=False, basis_year=2026):
    """C-GEM screening score 0-100 (same rules as the 'Integrity score' sheet). ccp_status: approved / under assessment /
    not assessed / does not meet. status: active / no credits / slowing / dormant / withdrawn."""
    p = {}
    p['Additionality and over-crediting risk of the credit type'] = TYPE_RISK.get(credit_type, 0.5)
    p['ICVCM CCP status of the methodology'] = {'approved': 1.0, 'under assessment': 0.6, 'not assessed': 0.5, 'does not meet': 0.1}[ccp_status]
    p['Delivery record (realisation ratio)'] = 0.6 if realisation is None else (1.0 if 0.6 <= realisation <= 1.3 else (0.5 if realisation < 0.6 else 0.6))
    age = None if latest_vintage is None else basis_year - latest_vintage
    p['Vintage age'] = 1.0 if (age is None or age <= 5) else (0.5 if age <= 10 else 0.2)
    p['Co-benefit label'] = 1.0 if cobenefit else 0.4
    p['Activity status'] = {'active': 1.0, 'slowing': 1.0, 'no credits': 0.6, 'dormant': 0.3, 'withdrawn': 0.0}[status]
    p["India Article 6 list match"] = 1.0 if article6_match else 0.3
    score = sum(INTEGRITY_WEIGHTS[k] * v for k, v in p.items())
    return score, ('A' if score >= 70 else 'B' if score >= 50 else 'C')


def portfolio_risk(weights, budget=1_000_000, rho=0.5):
    """weights = {credit_type: share of budget}. Returns tonnes, average price, sigma, 95% VaR (as the 'Portfolio builder' sheet)."""
    tonnes = sig_terms = 0.0; s2 = 0.0; s1 = 0.0
    for t, w in weights.items():
        ty = ML['types'][t]; mid = ml_price(t)[0]; sig = (ty['p90_log'] - ty['p10_log']) / (2 * 1.2816)
        tonnes += budget * w / mid; s2 += (w * sig) ** 2; s1 += w * sig
    sigma = math.sqrt((1 - rho) * s2 + rho * s1 ** 2)
    return {'tonnes': tonnes, 'avg_price': budget / tonnes, 'sigma': sigma, 'var95': budget * (1 - math.exp(-1.645 * sigma))}


def scenario_2030(price_2026, demand_growth=0.06, supply_growth=0.04, elasticity=1.5, years=4):
    """Balance scenario (as the 'Supply and demand' sheet): P2030 = P2026 x [(1+gd)/(1+gs)]^(years/elasticity)."""
    return price_2026 * ((1 + demand_growth) / (1 + supply_growth)) ** (years / elasticity)


def rating_value(credit_type, volume, rating_cost=20000):
    """Extra revenue per year from a high rating vs no rating (as the 'Rating translator' sheet)."""
    base = ml_price(credit_type)[0]; high = ml_price(credit_type, rating='high')[0]
    return {'no_rating': base, 'high_rating': high, 'extra_revenue': (high - base) * volume, 'net_gain': (high - base) * volume - rating_cost}


def monte_carlo_npv(price, est_annual, realisation=0.77, delay=2, years=10, growth=0.03, buffer=0.0, share=0.10, capex=300000,
                    opex=25000, verification=25000, fee=0.20, rate=0.12, sigma_price=None, p10=None, p90=None,
                    sigma_realisation=0.494, max_extra_delay=2, n=1000, seed=42):
    """Same method as the 'Risk simulation' sheet: random price, realisation ratio and extra delay -> NPV distribution."""
    import numpy as np
    if sigma_price is None:
        sigma_price = (math.log(p90) - math.log(p10)) / (2 * 1.2816)
    rng = np.random.default_rng(seed); z1, z2, u = rng.standard_normal(n), rng.standard_normal(n), rng.random(n)
    p = price * np.exp(sigma_price * z1); R = np.minimum(1.5, realisation * np.exp(sigma_realisation * z2)); d = delay + np.floor(u * (max_extra_delay + 1))
    Q = est_annual * R * (1 - buffer); a = (1 + growth) / (1 + rate); AN = (1 - (1 + rate) ** -years) / rate
    S = a ** (d + 1) * (1 - a ** years) / (1 - a) / (1 + growth)
    npv = Q * p * (1 - share) * S - (capex + opex * (1 - (1 + rate) ** -(d + years)) / rate + (verification + fee * Q) * (1 + rate) ** -d * AN)
    return {'p_positive': float((npv > 0).mean()), 'mean': float(npv.mean()), 'p10': float(np.percentile(npv, 10)),
            'p50': float(np.percentile(npv, 50)), 'p90': float(np.percentile(npv, 90))}


if __name__ == '__main__':
    r = price('Household devices (cookstoves, lighting, water)', vintage=2024, cobenefit=True)
    print('confidence:', r.pop('confidence'))
    for k, (mid, lo, hi) in r.items():
        print(f'{k:12s} middle ${mid:6.2f}   P10 ${lo:6.2f}   P90 ${hi:6.2f}')
    m, lo, hi = r['recommended']
    pf = project_finance(m, 25000, p10=lo, p90=hi)
    print({k: round(v, 2) if isinstance(v, float) else v for k, v in pf.items()})
    print(ccts_balance(1_000_000, 0.80, 0.03, 0.785, 800))
    print(ccc_auction([(1500, 20000), (1200, 30000), (1000, 40000), (900, 25000), (800, 30000), (700, 20000), (600, 15000), (500, 10000)],
                      [(450, 15000), (550, 25000), (650, 30000), (750, 30000), (850, 25000), (950, 20000), (1100, 20000), (1300, 15000)], 300, 2000))
    print(cbam_cost(10000, 2.2))
    print(rating_value('Household devices (cookstoves, lighting, water)', 50000))
    print(portfolio_risk({'Afforestation / reforestation (ARR)': 0.5, 'Household devices (cookstoves, lighting, water)': 0.5}))
    print(monte_carlo_npv(m, 25000, realisation=0.7709, p10=lo, p90=hi))
    print(integrity_score('Rice methane (AWD, DSR, SRI)', 'approved', 0.9, 2025, True))
