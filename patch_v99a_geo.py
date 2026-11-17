"""C-GEM v99a online site: one continent for every country (tables ov_country_cont for host countries, ov_geo_cont for every map shape).
Used by the inequality curve and by the continent map. Plain sqlite, no Superset needed."""
import sqlite3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# continents of territories and small states that have no project (or an unmapped continent) in the mastersheet
EXTRA = {
    'Africa': 'MUS SYC SHN ESH GNQ ATF SOL',
    'Asia': 'MDV IOT TKM MAC CYN',
    'Europe': 'GIB XKX VAT JEY GGY IMN SVN SMR MCO MLT ALA FRO AND',
    'North America': 'VIR PRI AIA CYM BMU VGB TCA MSR VCT LCA KNA CUW GRD SPM MAF BLM GRL ATG SXM',
    'South America': 'VEN SGS FLK',
    'Oceania': 'TUV UMI FSM MHL MNP ASM PCN TON WSM NIU COK NRU KIR WLF PYF NFK',
}
FORCE = {'MDV', 'MUS'}      # the mastersheet has these two as "Seven seas (open ocean)"
OTHER = {i: c for c, v in EXTRA.items() for i in v.split()}


def main():
    con = sqlite3.connect('/app/cgem/cgem.db')
    con.execute('DROP TABLE IF EXISTS ov_country_cont')
    con.execute('DROP TABLE IF EXISTS ov_geo_cont')
    con.execute('CREATE TABLE ov_country_cont (country TEXT PRIMARY KEY, iso3 TEXT, continent TEXT)')
    con.execute('CREATE TABLE ov_geo_cont (iso3 TEXT PRIMARY KEY, continent TEXT)')
    rows = con.execute("SELECT country, MAX(country_iso3), MAX(continent) FROM projects WHERE country IS NOT NULL AND country NOT IN ('', 'Not recorded') GROUP BY country").fetchall()
    host = {}
    for country, iso, cont in rows:
        if iso in FORCE:
            cont = OTHER[iso]
        elif cont is None or cont in ('Seven seas (open ocean)', 'Not mapped'):
            cont = OTHER.get(iso, 'Other')
        host[country] = (iso, cont)
    con.executemany('INSERT INTO ov_country_cont VALUES (?,?,?)', [(c, i, k) for c, (i, k) in host.items()])
    geo = {}
    import patch_v99a_geodata as G
    for iso, in con.execute('SELECT iso3 FROM geo_world'):
        geo[iso] = OTHER.get(iso)
    for iso in G.PATHS:
        geo.setdefault(iso, OTHER.get(iso))
    for iso, cont in host.values():
        if iso:
            geo[iso] = cont
    for iso in FORCE:
        geo[iso] = OTHER[iso]
    con.executemany('INSERT INTO ov_geo_cont VALUES (?,?)', [(i, k) for i, k in geo.items() if k])
    con.execute('DROP TABLE IF EXISTS ov_geo_path')
    con.execute('CREATE TABLE ov_geo_path (iso3 TEXT PRIMARY KEY, d TEXT)')
    con.executemany('INSERT INTO ov_geo_path VALUES (?,?)', list(G.PATHS.items()))
    con.commit()
    left = [i for i, k in geo.items() if not k]
    print('v99a: continents set for', len(host), 'host countries and', len(geo) - len(left), 'map shapes; no continent for', left)
    con.close()


try:
    main()
except Exception as exc:
    print('v99a: skipped:', exc)
