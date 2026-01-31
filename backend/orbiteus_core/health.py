"""Health check endpoints for orchestrators (compose, k8s).

- `/api/health/live` — liveness: process is up; never touches dependencies.
- `/api/health/ready` — readiness: DB and Redis ping must succeed.

Status responses follow the convention used by k8s probes:
- 200 OK with JSON body when healthy
- 503 Service Unavailable when not ready
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/api/health/live", include_in_schema=False)
async def live() -> dict:
    """Liveness probe: returns immediately, no I/O."""
    return {"status": "ok"}


@router.get("/api/health/ready", include_in_schema=False)
async def ready(response: Response) -> dict:
    """Readiness probe: checks DB and (optionally) Redis."""
    checks: dict[str, str] = {}

    # Database
    try:
        from sqlalchemy import text

        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        logger.warning("readiness: db ping failed", extra={"error": str(exc)})
        checks["db"] = "fail"

    # Redis (optional in dev — only required if REDIS_URL is set).
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        try:
            import redis.asyncio as redis_async

            client = redis_async.from_url(redis_url, encoding="utf-8", decode_responses=True)
            try:
                await client.ping()
                checks["redis"] = "ok"
            finally:
                await client.aclose()
        except Exception as exc:
            logger.warning("readiness: redis ping failed", extra={"error": str(exc)})
            checks["redis"] = "fail"
    else:
        checks["redis"] = "skipped"

    healthy = all(v == "ok" for k, v in checks.items() if v != "skipped")
    if not healthy:
        response.status_code = 503

    return {"status": "ok" if healthy else "degraded", "checks": checks}
