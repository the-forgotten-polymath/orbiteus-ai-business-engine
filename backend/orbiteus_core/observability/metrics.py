"""Prometheus metrics primitives — DoD §13.2 / docs/29-observability.md.

Exposed at `/metrics`. Registered globally so multiple workers share
the same scrape endpoint shape (label sets are stable).

Every series declared in `docs/29-observability.md` lives here. The
canonical scrape contract is:

    orbiteus_http_requests_total{method,route,status}
    orbiteus_http_request_duration_seconds_bucket{method,route, le="..."}

    orbiteus_db_query_duration_seconds_bucket{operation, le="..."}
    orbiteus_db_pool_in_use{pool}

    orbiteus_redis_commands_total{command,status}
    orbiteus_redis_latency_seconds_bucket{command, le="..."}

    orbiteus_celery_task_duration_seconds_bucket{task, le="..."}
    orbiteus_celery_tasks_total{task,status}
    orbiteus_celery_queue_depth{queue}

    orbiteus_outbox_pending
    orbiteus_outbox_dead

    orbiteus_ai_calls_total{provider,model,status}
    orbiteus_ai_tokens_total{provider,direction}
    orbiteus_ai_provider_latency_seconds_bucket{provider,model, le="..."}

    orbiteus_sse_active_connections
    orbiteus_pubsub_messages_total{topic_kind}

Modules `import` the metric they need from this module — there is
exactly one place where the label set / name pair is defined.
"""
from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

request_count = Counter(
    "orbiteus_http_requests_total",
    "Total HTTP requests served",
    labelnames=("method", "route", "status"),
)

request_duration = Histogram(
    "orbiteus_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

db_query_duration = Histogram(
    "orbiteus_db_query_duration_seconds",
    "Time spent in a single SQLAlchemy query",
    labelnames=("operation",),  # "select" | "insert" | "update" | "delete" | "ddl"
    buckets=(0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

db_pool_in_use = Gauge(
    "orbiteus_db_pool_in_use",
    "Number of in-use connections per asyncpg pool",
    labelnames=("pool",),  # "primary" | "celery" | ...
)


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

redis_commands_total = Counter(
    "orbiteus_redis_commands_total",
    "Total Redis commands issued",
    labelnames=("command", "status"),  # status ∈ {"ok", "error"}
)

redis_latency = Histogram(
    "orbiteus_redis_latency_seconds",
    "Redis command round-trip latency",
    labelnames=("command",),
    buckets=(0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

celery_task_duration = Histogram(
    "orbiteus_celery_task_duration_seconds",
    "Celery task wall-clock duration",
    labelnames=("task",),
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0),
)

celery_tasks_total = Counter(
    "orbiteus_celery_tasks_total",
    "Celery task outcomes",
    labelnames=("task", "status"),  # status ∈ {"success", "failure", "retry"}
)

celery_queue_depth = Gauge(
    "orbiteus_celery_queue_depth",
    "Number of queued tasks waiting for a worker",
    labelnames=("queue",),  # "default" | "outbox" | "embeddings" | ...
)


# ---------------------------------------------------------------------------
# Outbox
# ---------------------------------------------------------------------------

outbox_pending = Gauge(
    "orbiteus_outbox_pending",
    "Outbox rows in `pending` status (waiting for the drainer)",
)

outbox_dead = Gauge(
    "orbiteus_outbox_dead",
    "Outbox rows in `dead` status (terminal failure)",
)


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

ai_calls_total = Counter(
    "orbiteus_ai_calls_total",
    "AI provider calls (chat + embed)",
    labelnames=("provider", "model", "status"),
)

ai_tokens_total = Counter(
    "orbiteus_ai_tokens_total",
    "AI tokens consumed",
    labelnames=("provider", "direction"),  # direction ∈ {"input", "output"}
)

ai_provider_latency = Histogram(
    "orbiteus_ai_provider_latency_seconds",
    "AI provider call latency",
    labelnames=("provider", "model"),
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)


# ---------------------------------------------------------------------------
# Realtime
# ---------------------------------------------------------------------------

sse_active_connections = Gauge(
    "orbiteus_sse_active_connections",
    "Currently connected SSE clients (`/api/realtime/subscribe`)",
)

pubsub_messages_total = Counter(
    "orbiteus_pubsub_messages_total",
    "Realtime backplane messages published",
    labelnames=("topic_kind",),  # "list" | "record"
)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

async def metrics_endpoint() -> Response:
    """Return the Prometheus exposition format payload."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
