"""C-GEM v56 update for the online site: give slow chart queries more time on the small free server."""
p = '/app/cgem/superset_config.py'
s = open(p).read()
if 'SUPERSET_WEBSERVER_TIMEOUT' not in s:
    s += ('\n# online site: the free server is small, so charts may need more than the default 60 seconds\n'
          'SUPERSET_WEBSERVER_TIMEOUT = 170\n'
          "DATA_CACHE_CONFIG = {'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': '/app/superset_home/cache', 'CACHE_DEFAULT_TIMEOUT': 3600}\n")
    open(p, 'w').write(s)
print('v56 patch: longer chart timeout and file cache')
