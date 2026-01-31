"""Token-bucket-style rate limiter (Redis counters, per-minute window).

Buckets:
- `rl:tenant:{id}:{minute}`     → tenant-scoped quota
- `rl:user:{id}:{minute}`       → per-user quota
- `rl:ip:{ip}:{minute}`         → per-IP quota
- `rl:anon:{route}:{ip}:{minute}` → anonymous-route quota

Each `INCR` sets EXPIRE only if absent (NX) so the TTL aligns with the
minute window. When the count exceeds the limit, middleware returns
HTTP 429 with `Retry-After`.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from orbiteus_core.cache import get_redis

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60


def _minute_bucket(now: float | None = None) -> int:
    return int((now if now is not None else time.time()) // WINDOW_SECONDS)


@dataclass
class RateDecision:
    allowed: bool
    bucket: str
    count: int
    limit: int
    retry_after: int  # seconds until the next minute window


async def check(bucket_name: str, limit: int) -> RateDecision:
    """Atomically increment + return decision."""
    minute = _minute_bucket()
    key = f"rl:{bucket_name}:{minute}"
    client = get_redis()
    pipe = client.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, WINDOW_SECONDS, nx=True)
    result = await pipe.execute()
    count = int(result[0])

    retry_after = WINDOW_SECONDS - (int(time.time()) % WINDOW_SECONDS)
    return RateDecision(
        allowed=count <= limit,
        bucket=bucket_name,
        count=count,
        limit=limit,
        retry_after=retry_after,
    )
