#!/bin/sh
# Backend entrypoint.
#
# Default behavior: start the HTTP server (Gunicorn + UvicornWorker in prod,
# uvicorn reload in dev).
#
# Migrations are NOT run here in production — a dedicated `migrate` service
# in compose runs them once and the backend depends on its success.
# In dev (RUN_MIGRATIONS=1), they run inline so a fresh `docker compose up`
# works without an extra step.
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running Alembic migrations (RUN_MIGRATIONS=1)..."
  alembic upgrade head
fi

if [ "${USE_GUNICORN:-1}" = "1" ] && [ -z "${UVICORN_RELOAD:-}" ]; then
  WORKERS="${GUNICORN_WORKERS:-4}"
  TIMEOUT="${GUNICORN_TIMEOUT:-60}"
  GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-30}"
  KEEP_ALIVE="${GUNICORN_KEEP_ALIVE:-30}"
  MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-10000}"
  MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-1000}"
  BIND="${GUNICORN_BIND:-0.0.0.0:8000}"

  echo "Starting Gunicorn (workers=${WORKERS}, bind=${BIND})..."
  exec gunicorn api:app \
    --workers "${WORKERS}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "${BIND}" \
    --timeout "${TIMEOUT}" \
    --graceful-timeout "${GRACEFUL_TIMEOUT}" \
    --keep-alive "${KEEP_ALIVE}" \
    --max-requests "${MAX_REQUESTS}" \
    --max-requests-jitter "${MAX_REQUESTS_JITTER}" \
    --access-logfile - \
    --error-logfile - \
    "$@"
else
  echo "Starting uvicorn (dev mode)..."
  exec uvicorn api:app --host 0.0.0.0 --port 8000 ${UVICORN_RELOAD:+--reload} "$@"
fi
