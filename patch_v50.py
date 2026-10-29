"""C-GEM v50 update for the online site: removes "The story" and "Chapter" text everywhere."""
import json
import re
import sqlite3

HERE = '/app/cgem'

# 1. glossary data: drop the "Chapter N." prefixes
c = sqlite3.connect(HERE + '/cgem.db')
for rid, st in c.execute('select rowid, story from glossary_story').fetchall():
    if st and re.match(r'(?i)\s*chapter\s+\d+\.\s*', st):
        c.execute('update glossary_story set story=? where rowid=?', (re.sub(r'(?i)^\s*chapter\s+\d+\.\s*', '', st), rid))
c.commit()
c.close()

# 2. chatbot: no "The story" line in glossary answers
p = HERE + '/cgem_chat.py'
s = open(p).read()
s = s.replace("    if story:\n        pts.append(f'**The story:** {story[2]}')\n", '')
open(p, 'w').write(s)

# 3. dashboard charts
from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard
    OLD = 'The life of one tonne: every term as a chapter (click a card)'
    NEW = 'Every term explained (click a card)'
    n = 0
    for sl in db.session.query(Slice).all():
        ps = sl.params or ''
        if 'The story' not in ps and sl.slice_name != OLD:
            continue
        d = json.loads(ps)
        t = d.get('handlebarsTemplate', '')
        t = re.sub(r'<div class="sec story"><b>The story</b>.*?</div>', '', t, flags=re.S)
        t = t.replace('<p><b>The story:</b> {{this.story}}</p>', '')
        d['handlebarsTemplate'] = t
        if sl.slice_name == OLD:
            sl.slice_name = NEW
            sl.description = ('Every term explained in plain words for someone new to carbon markets, '
                              'plus why it matters and what to be careful about.')
        sl.params = json.dumps(d)
        n += 1
    for dash in db.session.query(Dashboard).all():
        if dash.position_json and OLD in dash.position_json:
            dash.position_json = dash.position_json.replace(OLD, NEW)
    db.session.commit()
    print(f'v50 patch: {n} charts updated')
