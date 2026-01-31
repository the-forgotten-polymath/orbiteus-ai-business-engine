"""Observability primitives: structured JSON logs, request IDs, Prometheus metrics.

Public API:

    from orbiteus_core.observability import (
        configure_json_logging,
        RequestIdMiddleware,
        metrics_endpoint,
        request_duration,
        request_count,
    )
"""
from __future__ import annotations

from .logging import configure_json_logging
from .metrics import metrics_endpoint, request_count, request_duration
from .middleware import RequestIdMiddleware

__all__ = [
    "RequestIdMiddleware",
    "configure_json_logging",
    "metrics_endpoint",
    "request_count",
    "request_duration",
]
