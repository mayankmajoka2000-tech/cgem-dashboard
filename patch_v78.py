"""C-GEM v78 online site settings: longer chart timeout on the small free server, chart results kept in a file cache
(datasets with live prices refresh every 30 minutes)."""
p = '/app/cgem/superset_config.py'
s = open(p).read()
if 'CGEM_ONLINE_CACHE' not in s:
    s += ("\n# CGEM_ONLINE_CACHE: online site settings\n"
          "if _os.environ.get('CGEM_ONLINE') == '1':\n"
          "    SUPERSET_WEBSERVER_TIMEOUT = 170\n"
          "    DATA_CACHE_CONFIG = {'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': '/app/superset_home/cache', "
          "'CACHE_DEFAULT_TIMEOUT': 30 * 86400, 'CACHE_THRESHOLD': 5000}\n")
    open(p, 'w').write(s)

from superset.app import create_app

app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.connectors.sqla.models import SqlaTable
    n = 0
    for t in db.session.query(SqlaTable).all():
        if t.table_name.startswith('live') or t.table_name.startswith('vcm_india'):
            t.cache_timeout = 1800
            n += 1
    db.session.commit()
    print('v78 online settings: live datasets with a 30-minute cache:', n)
