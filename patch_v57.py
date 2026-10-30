"""C-GEM v57 update for the online site: title case headings, long-lived chart cache (live data refreshes every 30 minutes)."""
import json

from superset.app import create_app

TITLES = [('Understanding the Global Carbon Market', 'Understanding The Global Carbon Market'),
          ('Market Players and Transactions', 'Market Players And Transactions'),
          ('From Project Development to Future Supply', 'From Project Development To Future Supply'),
          ('What It Costs to Emit a Tonne of CO2 Around the World', 'What It Costs To Emit A Tonne Of CO2 Around The World'),
          ('>Project explorer<', '>Project Explorer<')]

p = '/app/cgem/superset_config.py'
s = open(p).read()
if 'CGEM_CACHE_30D' not in s:
    s += ("\n# CGEM_CACHE_30D: chart results stay cached; datasets with live prices use their own 30-minute timeout\n"
          "DATA_CACHE_CONFIG = {'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': '/app/superset_home/cache', "
          "'CACHE_DEFAULT_TIMEOUT': 30 * 86400, 'CACHE_THRESHOLD': 5000}\n")
    open(p, 'w').write(s)

app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.dashboard import Dashboard
    from superset.connectors.sqla.models import SqlaTable
    for dash in db.session.query(Dashboard).all():
        q = dash.position_json or ''
        for a, b in TITLES:
            q = q.replace(a, b)
        dash.position_json = q
    n = 0
    for t in db.session.query(SqlaTable).all():
        if t.table_name.startswith('live') or t.table_name.startswith('vcm_india'):
            t.cache_timeout = 1800
            n += 1
    db.session.commit()
    print('v57 patch: titles updated, live datasets with 30-minute cache:', n)
