# 29 — Observability

Three pillars: **logs**, **metrics**, **traces**. All correlated by `request_id`.

## Logs

- Format: structured **JSON** lines on stdout.
- Library: stdlib `logging` with a custom formatter; no third-party logging frameworks.
- Required fields per record:

  ```
  ts, level, logger, msg, request_id, tenant_id, user_id, actor, route, latency_ms
  ```

- `request_id` injected by middleware (`X-Request-Id`), propagated to downstream
  HTTP calls via `httpx` events.
- Secret redaction is applied **before** the formatter (helper
  `redact()` in `orbiteus_core.logging.redaction`).

## Metrics

- Library: `prometheus_client` (sync + async wrappers).
- Endpoint: `GET /metrics` (auth-gated; only Prometheus scraper allowed via
  network policy or basic auth).
- Required series:
  - HTTP: `orbiteus_http_requests_total{route,method,status}`,
    `orbiteus_http_request_duration_seconds_bucket{...}`
  - DB: `orbiteus_db_query_duration_seconds`, `orbiteus_db_pool_in_use`
  - Redis: `orbiteus_redis_commands_total`, `orbiteus_redis_latency_seconds`
  - Celery: `orbiteus_celery_task_duration_seconds`,
    `orbiteus_celery_tasks_total{status}`
  - Outbox: `orbiteus_outbox_pending`, `orbiteus_outbox_dead`
  - AI: `orbiteus_ai_calls_total{provider,model,status}`,
    `orbiteus_ai_tokens_total{provider,direction}`
  - Realtime: `orbiteus_sse_active_connections`,
    `orbiteus_pubsub_messages_total{topic_kind}`

## Traces

- OpenTelemetry SDK; export via OTLP HTTP.
- Opt-in (`OTEL_EXPORTER_OTLP_ENDPOINT` set in env).
- Auto-instrumentation: FastAPI, asyncpg, redis-py, httpx, Celery.
- Span attributes: `tenant_id`, `user_id`, `actor`, `module`.
- AI tool calls produce a child span per call.

## Correlation

- `X-Request-Id` is the join key.
- Workers receive `request_id` as a Celery header and propagate it.
- Logs / metrics / traces all carry it.

## Alerts (recommended baseline)

- p95 of `/api/*` > 500 ms for 5 min → page.
- DB pool saturation > 90% for 2 min → page.
- Outbox `pending` > 1 000 for 10 min → warn.
- Outbox `dead` > 0 → warn.
- Celery task failure rate > 5% for 10 min → warn.
- AI provider error rate > 10% for 5 min → warn.
- SSE active connections drops by > 50% in 1 min → warn.

## Local dev

- Docker compose `dev` profile mounts logs as plain console.
- Optional `monitor` profile spins up Prometheus + Grafana sidecars with
  pre-built dashboards (planned).

## What you do not do

- Do not log secrets or full PII.
- Do not depend on log levels for control flow.
- Do not invent custom metric names; follow the list above and extend it
  consistently.
