# C-GEM Carbon Credit Intelligence - online site (any Docker host: Render, Koyeb, a cloud VM)
FROM apache/superset:6.1.0
USER root
ENV SUPERSET_CONFIG_PATH=/app/cgem/superset_config.py \
    CGEM_ONLINE=1 \
    SERVER_WORKER_AMOUNT=1 \
    SERVER_THREADS_AMOUNT=4 \
    GUNICORN_TIMEOUT=180 \
    HOME=/app/superset_home
COPY part_* /tmp/bundle/
RUN (python -m pip install --no-cache-dir --quiet pypdf || uv pip install --python "$(command -v python)" pypdf || true) \
 && mkdir -p /app/cgem /app/superset_home \
 && cat /tmp/bundle/part_* | base64 -d > /tmp/cgem.tgz \
 && tar -xzf /tmp/cgem.tgz -C /app/cgem && rm -rf /tmp/bundle /tmp/cgem.tgz \
 && cd /app/cgem \
 && python -c "import zipfile;[zipfile.ZipFile(f).extractall('.') for f in ('cgem_db.zip','cgem_geo.zip')]" \
 && rm -f cgem_db.zip cgem_geo.zip \
 && chown -R 1000:1000 /app/cgem /app/superset_home \
 && chmod +x /app/cgem/space_start.sh
USER 1000
# the dashboard is set up while the image is built, so the site starts fast
RUN bash /app/cgem/space_start.sh --build
# v50 and later small updates (patch_*.py in the repository)
COPY --chown=1000:1000 patch_*.py /app/cgem/
RUN export SUPERSET_SECRET_KEY="$(cat /app/superset_home/.cgem_key)" && for f in /app/cgem/patch_*.py; do python "$f"; done
# fast first visit: open every tab once during the build so chart results are already cached
USER root
COPY --chown=1000:1000 warm_cache.py /app/cgem/
RUN set +e; (python -m pip install --no-cache-dir --quiet playwright==1.48.0 || uv pip install --python "$(command -v python)" playwright==1.48.0 || (python -m ensurepip && python -m pip install --no-cache-dir --quiet playwright==1.48.0)); python -c "import playwright; print('playwright ready')"; python -m playwright install --with-deps chromium; \
    cd /app/cgem && SUPERSET_SECRET_KEY="$(cat /app/superset_home/.cgem_key)" python /app/cgem/warm_cache.py; \
    rm -rf /app/superset_home/.cache/ms-playwright /root/.cache/ms-playwright; \
    chown -R 1000:1000 /app/superset_home /app/cgem; true
USER 1000
EXPOSE 8088
CMD ["bash", "/app/cgem/space_start.sh"]
