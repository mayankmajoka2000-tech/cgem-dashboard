"""C-GEM v86 online site: the EU link page at a short address, /eu-link (old /cgem-static/eu-link.html forwards there)."""
p = '/app/cgem/superset_config.py'
s = open(p).read()
if 'CGEM_EU_LINK' not in s:
    s += '''
# CGEM_EU_LINK: EU link page at /eu-link
_cgem_eu_prev = globals().get('FLASK_APP_MUTATOR')

def _cgem_eu_mutator(app):
    from flask import send_file as _sf, redirect as _rd, request as _rq
    _page = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'chat', 'eu-link.html')

    def _cgem_eu_page():
        return _sf(_page, mimetype='text/html', max_age=600)
    app.add_url_rule('/eu-link', 'cgem_eu_link', _cgem_eu_page)

    @app.before_request
    def _cgem_eu_short():
        if _rq.path in ('/eu-link/', '/cgem-static/eu-link.html'):
            return _rd('/eu-link', 301)
    return _cgem_eu_prev(app) if _cgem_eu_prev else app
FLASK_APP_MUTATOR = _cgem_eu_mutator
'''
    open(p, 'w').write(s)
print('v86: EU link page at /eu-link')
