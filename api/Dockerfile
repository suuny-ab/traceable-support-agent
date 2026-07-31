ARG PYTHON_IMAGE=python:3.13-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64

FROM ${PYTHON_IMAGE} AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api/src \
    TRACEABLE_PUBLIC_HOST=0.0.0.0 \
    TRACEABLE_PUBLIC_PORT=8000 \
    TRACEABLE_PUBLIC_DB=/var/lib/traceable/public.sqlite3 \
    TRACEABLE_PUBLIC_LIVE_ENABLED=false
WORKDIR /app
RUN groupadd --gid 10001 traceable \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin traceable \
    && mkdir -p /var/lib/traceable \
    && chown -R traceable:traceable /var/lib/traceable

FROM ${PYTHON_IMAGE} AS replay-dependencies
WORKDIR /build
COPY api/requirements-base.lock ./requirements-base.lock
RUN python -m pip install --disable-pip-version-check --no-cache-dir --no-deps --require-hashes \
    --prefix=/install -r requirements-base.lock

FROM runtime-base AS replay
ARG VCS_REF=unknown
RUN python -c "import os,pathlib,re,sys; value=os.environ['VCS_REF']; re.fullmatch(r'(?:[0-9a-f]{40}|local)',value) or sys.exit('vcs_ref_invalid'); pathlib.Path('/app/release-sha').write_text(value+'\n',encoding='utf-8')"
LABEL org.opencontainers.image.source="https://github.com/suuny-ab/traceable-support-agent" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="traceable-support-agent-api-replay"
COPY --from=replay-dependencies /install /usr/local
COPY --chown=traceable:traceable api/src/traceable_support/__init__.py /app/api/src/traceable_support/__init__.py
COPY --chown=traceable:traceable api/src/traceable_support/api /app/api/src/traceable_support/api
COPY --chown=traceable:traceable api/src/traceable_support/product/__init__.py /app/api/src/traceable_support/product/__init__.py
COPY --chown=traceable:traceable api/src/traceable_support/product/boundaries.py /app/api/src/traceable_support/product/boundaries.py
COPY --chown=traceable:traceable api/src/traceable_support/product/types.py /app/api/src/traceable_support/product/types.py
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import json,pathlib,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=2)); assert data['status']=='ok' and data['live_experience']=='replay_only' and data['release_sha']==pathlib.Path('/app/release-sha').read_text().strip()"]
CMD ["python", "-m", "traceable_support.api.http"]

FROM ${PYTHON_IMAGE} AS live-dependencies
WORKDIR /build
COPY api/requirements-base.lock ./requirements-base.lock
COPY api/requirements-live.lock ./requirements-live.lock
RUN python -m pip install --disable-pip-version-check --no-cache-dir --no-deps --require-hashes \
    --prefix=/install -r requirements-base.lock \
    && python -m pip install --disable-pip-version-check --no-cache-dir --no-deps --require-hashes \
    --prefix=/install -r requirements-live.lock

FROM ${PYTHON_IMAGE} AS live-model
WORKDIR /build
COPY deploy/download_embedding_model.py ./download_embedding_model.py
COPY api/src/traceable_support/retrieval/bge-small-zh-v1.5-fastembed.json ./model-manifest.json
RUN python download_embedding_model.py --manifest model-manifest.json --root /model

FROM runtime-base AS live
ARG VCS_REF=unknown
RUN python -c "import os,pathlib,re,sys; value=os.environ['VCS_REF']; re.fullmatch(r'(?:[0-9a-f]{40}|local)',value) or sys.exit('vcs_ref_invalid'); pathlib.Path('/app/release-sha').write_text(value+'\n',encoding='utf-8')"
LABEL org.opencontainers.image.source="https://github.com/suuny-ab/traceable-support-agent" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="traceable-support-agent-api-live-offline-candidate"
COPY --from=live-dependencies /install /usr/local
COPY --from=live-model /model /opt/traceable-model
COPY --chown=traceable:traceable api/src/traceable_support /app/api/src/traceable_support
COPY --chown=traceable:traceable data /app/data
ENV TRACEABLE_MODEL_ROOT=/opt/traceable-model/artifacts/models/fastembed/fast-bge-small-zh-v1.5 \
    TRACEABLE_PUBLIC_LIVE_ENABLED=true
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import json,pathlib,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=2)); assert data['status']=='ok' and data['live_experience']=='available' and data['release_sha']==pathlib.Path('/app/release-sha').read_text().strip()"]
CMD ["python", "-m", "traceable_support.api.http"]
