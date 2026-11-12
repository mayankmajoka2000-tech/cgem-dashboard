"""C-GEM online site: 3D globe controls fixed (dragging with the mouse turns the globe again; turn and zoom buttons work with mouse, touch and keyboard;
Start rotation works at any zoom; the buttons move clear of the profile panel)."""
import json, html as _h
FIX = [
("function grab(){busy=true;touched=true;clearTimeout(resumeT);map.stop();var h=$('drag');if(h)h.style.opacity=0;}",
 "function grab(){busy=true;touched=true;clearTimeout(resumeT);var h=$('drag');if(h)h.style.opacity=0;}"),
("[].forEach.call(document.querySelectorAll('#pad button'),function(b){var t=null;b.onmousedown=function(e){e.preventDefault();turn(b.dataset.k);if(['left','right','up','down'].indexOf(b.dataset.k)>=0)t=setInterval(function(){turn(b.dataset.k);},380);};\n b.onmouseup=b.onmouseleave=function(){clearInterval(t);};});",
 "[].forEach.call(document.querySelectorAll('#pad button'),function(b){var t=null;function end(){clearInterval(t);t=null;b.classList.remove('dn');}\n b.addEventListener('pointerdown',function(e){e.preventDefault();e.stopPropagation();b._pd=Date.now();b.classList.add('dn');turn(b.dataset.k);var h=$('drag');if(h)h.style.opacity=0;clearInterval(t);if(['left','right','up','down'].indexOf(b.dataset.k)>=0)t=setInterval(function(){turn(b.dataset.k);},380);});\n ['pointerup','pointerleave','pointercancel','blur'].forEach(function(v){b.addEventListener(v,end);});\n b.addEventListener('click',function(e){if(Date.now()-(b._pd||0)>700)turn(b.dataset.k);});});"),
("$('bSpin').onclick=function(){if(spinning)stopSpin();else{spinning=true;this.classList.add('on');this.textContent='Stop rotation';spin();}};",
 "$('bSpin').onclick=function(){if(spinning)stopSpin();else{spinning=true;busy=false;this.classList.add('on');this.textContent='Stop rotation';if(map.getZoom()>4.5)map.easeTo({zoom:2,pitch:0,bearing:0,duration:1500});else spin();}};\nnew MutationObserver(function(){document.body.classList.toggle('pfo',$('prof').classList.contains('on'));}).observe($('prof'),{attributes:true,attributeFilter:['class']});"),
("#pad button:hover{background:#eef4e6;border-color:#2C7A3D}",
 "#pad button:hover{background:#eef4e6;border-color:#2C7A3D}#pad button{touch-action:none;user-select:none;-webkit-user-select:none}#pad button.dn{background:#2C7A3D;color:#fff;border-color:#2C7A3D}\nbody.pfo #pad{right:442px}body.pfo #tools{right:486px}body.pfo #legend{display:none}\n@media (max-width:900px){body.pfo #pad,body.pfo #tools{display:none}}"),
]

def _esc(x):
    return _h.escape(x, quote=True).replace('\r', '').replace('\n', '&#10;')

from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.slice import Slice
    done = 0
    for s in db.session.query(Slice).all():
        try:
            p = json.loads(s.params or '{}')
        except Exception:
            continue
        t = p.get('handlebarsTemplate') or ''
        if 'title="3D globe"' not in t:
            continue
        n = 0
        for a, b in FIX:
            ea, eb = _esc(a), _esc(b)
            if eb in t:
                continue
            if ea in t:
                t = t.replace(ea, eb); n += 1
            else:
                print('globe fix: text not found, skipped:', a[:50])
        if n:
            p['handlebarsTemplate'] = t
            s.params = json.dumps(p)
            done += 1
    db.session.commit()
    print('globe controls fix applied to', done, 'chart(s)')
