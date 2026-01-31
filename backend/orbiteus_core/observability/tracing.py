"""OpenTelemetry instrumentation — opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`.

When the env var is set we register the OTLP HTTP exporter, attach a Resource
that includes the service name + tenant context, and instrument the libraries
the engine uses (FastAPI, SQLAlchemy, redis-py, httpx).

When unset, this module is a no-op — engine still starts cleanly without
the OTel deps installed (lazy import inside `setup_tracing`).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


_INSTALLED = False


def is_enabled() -> bool:
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def setup_tracing(app) -> None:
    """Configure tracer provider and instrument libraries. Idempotent."""
    global _INSTALLED
    if _INSTALLED or not is_enabled():
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("otel.deps_missing — install opentelemetry-* packages to enable tracing")
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "orbiteus-backend")
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()  # Reads OTEL_EXPORTER_OTLP_ENDPOINT
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument libraries.
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception:  # noqa: BLE001
        logger.exception("otel.fastapi_failed")
    try:
        from orbiteus_core.db import engine

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except Exception:  # noqa: BLE001
        logger.exception("otel.sqlalchemy_failed")
    try:
        RedisInstrumentor().instrument()
    except Exception:  # noqa: BLE001
        logger.exception("otel.redis_failed")
    try:
        HTTPXClientInstrumentor().instrument()
    except Exception:  # noqa: BLE001
        logger.exception("otel.httpx_failed")

    _INSTALLED = True
    logger.info("otel.installed", extra={"service_name": service_name})
