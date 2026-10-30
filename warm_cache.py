"""C-GEM online site: opens every dashboard tab once while the image is built, so chart results are already
in the file cache when the first visitor arrives. Run as part of the Docker build (see Dockerfile)."""
import os
import subprocess
import sys
import time
import urllib.request

PORT = 8091
env = dict(os.environ, SUPERSET_PORT=str(PORT))
srv = subprocess.Popen(['gunicorn', '--bind', f'127.0.0.1:{PORT}', '--workers', '2', '--worker-class', 'gthread',
                        '--threads', '8', '--timeout', '300', 'superset.app:create_app()'], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(120):
        try:
            if urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=5).read() == b'OK':
                break
        except Exception:
            time.sleep(2)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('CGEM_CHROME') or None)
        pg = b.new_page(viewport={'width': 1600, 'height': 2400})
        pending = set()
        pg.on('request', lambda r: pending.add(r) if '/api/v1/chart/data' in r.url else None)
        pg.on('requestfinished', lambda r: pending.discard(r))
        pg.on('requestfailed', lambda r: pending.discard(r))

        def settle(limit=120):
            t0 = time.time()
            pg.wait_for_timeout(1500)
            while pending and time.time() - t0 < limit:
                pg.wait_for_timeout(500)

        pg.goto(f'http://127.0.0.1:{PORT}/superset/dashboard/cgem/', wait_until='domcontentloaded', timeout=300000)
        pg.wait_for_selector('.ant-tabs-tab-btn', timeout=300000)
        settle()
        tabs = pg.evaluate("[...document.querySelectorAll('.ant-tabs-tab-btn')].map(e => e.innerText.trim())")
        for name in tabs:
            pg.evaluate("n => [...document.querySelectorAll('.ant-tabs-tab-btn')].find(e => e.innerText.trim() == n).click()", name)
            settle()
            last = -1
            for _ in range(40):   # scroll down step by step so every chart is drawn
                pg.mouse.wheel(0, 2000)
                settle()
                y = pg.evaluate("Math.round(document.scrollingElement.scrollTop)")
                if y == last:
                    break
                last = y
            pg.evaluate("window.scrollTo(0, 0)")
            print('warmed tab:', name, flush=True)
        b.close()
finally:
    srv.terminate()
    try:
        srv.wait(30)
    except Exception:
        srv.kill()
print('cache warm-up finished')
