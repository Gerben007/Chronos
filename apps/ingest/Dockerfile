# Chronos ingest — Python 3.11 on Debian slim.
# Build context is the repo root (so we can copy db/seed and db/migrations).
#   docker build -t chronos-ingest:latest -f apps/ingest/Dockerfile .

FROM python:3.11-slim-bookworm AS build
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libjpeg-dev zlib1g-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/ingest/pyproject.toml ./
COPY apps/ingest/chronos_ingest ./chronos_ingest
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

# Bake the schema + seed data into the image so the seed command works
# without external volume mounts.
WORKDIR /app
COPY --chown=chronos:chronos apps/ingest/chronos_ingest /app/chronos_ingest
COPY --chown=chronos:chronos db /app/db
COPY apps/ingest/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Stay root so the entrypoint can chown the data volumes; it drops to 1000.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8001
ENTRYPOINT ["/entrypoint.sh"]

# Default: run the FastAPI admin API. Override CMD in compose for cron mode.
CMD ["uvicorn", "chronos_ingest.admin_api:app", \
     "--host", "0.0.0.0", "--port", "8001", "--no-server-header"]
