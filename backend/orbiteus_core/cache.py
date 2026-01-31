"""Redis-backed cache abstraction (ADR-0003).

Single async Redis client per process, lazily created. Public API:

    from orbiteus_core.cache import get_cache

    cache = get_cache()
    await cache.set("k", "v", ttl=60)
    value = await cache.get("k")

The same client is reused for cache, JWT jti revocation, rate limit
buckets, idempotency keys, presence sets, AI budget counters, and the
realtime pub/sub backplane. Each consumer scopes its keys with a prefix.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis_async

from orbiteus_core.config import settings

logger = logging.getLogger(__name__)

_client: redis_async.Redis | None = None


def get_redis() -> redis_async.Redis:
    """Return the process-wide async Redis client (lazy)."""
    global _client
    if _client is None:
        _client = redis_async.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return _client


async def close_redis() -> None:
    """Close the cached client (used in tests + lifespan shutdown)."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None


class Cache:
    """Tiny async key-value cache wrapper with JSON serialization.

    For raw bytes/strings, use the underlying redis client via `get_redis()`.
    """

    def __init__(self, prefix: str = "orbiteus:") -> None:
        self.prefix = prefix

    def _k(self, key: str) -> str:
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Any:
        client = get_redis()
        raw = await client.get(self._k(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        client = get_redis()
        payload = json.dumps(value, default=str)
        if ttl is None:
            await client.set(self._k(key), payload)
        else:
            await client.set(self._k(key), payload, ex=ttl)

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        client = get_redis()
        return await client.delete(*(self._k(k) for k in keys))

    async def exists(self, key: str) -> bool:
        client = get_redis()
        return bool(await client.exists(self._k(key)))

    async def incr(self, key: str, ttl: int | None = None) -> int:
        client = get_redis()
        full = self._k(key)
        # Atomic INCR + (optional) EXPIRE only if the counter is fresh.
        pipe = client.pipeline()
        pipe.incr(full, 1)
        if ttl is not None:
            pipe.expire(full, ttl, nx=True)  # only set TTL if not already set
        result = await pipe.execute()
        return int(result[0])


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
