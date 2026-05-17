# Chronos ingest — Python 3.11 on Debian slim.
# Multi-stage so the runtime image carries no build tooling.

FROM python:3.11-slim-bookworm AS build
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libjpeg-dev zlib1g-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY chronos_ingest ./chronos_ingest
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip wheel --no-cache-dir --wheel-dir=/wheels .

# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg poppler-utils libjpeg62-turbo zlib1g clamav-daemon \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 chronos \
    && useradd -u 1000 -g 1000 -m -s /usr/sbin/nologin chronos

COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --find-links=/wheels chronos-ingest \
    && rm -rf /wheels

WORKDIR /app
COPY --chown=chronos:chronos chronos_ingest /app/chronos_ingest

USER 1000:1000
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8001

# Default: run the FastAPI admin API. Override CMD in compose for cron mode.
CMD ["uvicorn", "chronos_ingest.admin_api:app", \
     "--host", "0.0.0.0", "--port", "8001", "--no-server-header"]
