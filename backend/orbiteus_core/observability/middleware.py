"""ASGI middleware: request_id propagation + access log + Prometheus metrics."""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging import request_id_ctx
from .metrics import request_count, request_duration

logger = logging.getLogger("orbiteus.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject `X-Request-Id`, log access, and record HTTP metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:16]}"
        token = request_id_ctx.set(rid)

        route = self._route_template(request)
        method = request.method
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            request_count.labels(method=method, route=route, status="500").inc()
            request_duration.labels(method=method, route=route).observe(elapsed_ms / 1000.0)
            logger.exception(
                "Unhandled exception",
                extra={"method": method, "route": route, "latency_ms": elapsed_ms},
            )
            request_id_ctx.reset(token)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        status = str(response.status_code)
        request_count.labels(method=method, route=route, status=status).inc()
        request_duration.labels(method=method, route=route).observe(elapsed_ms / 1000.0)

        response.headers["x-request-id"] = rid
        logger.info(
            "request",
            extra={
                "method": method,
                "route": route,
                "status": status,
                "latency_ms": round(elapsed_ms, 2),
            },
        )
        request_id_ctx.reset(token)
        return response

    @staticmethod
    def _route_template(request: Request) -> str:
        """Best-effort: prefer the matched route template, fall back to path."""
        try:
            scope_route = request.scope.get("route")
            if scope_route is not None and getattr(scope_route, "path", None):
                return scope_route.path
        except Exception:
            pass
        return request.url.path
