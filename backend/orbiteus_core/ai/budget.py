"""Tenant-level AI token budget — Redis counter per (tenant, yyyymm)."""
from __future__ import annotations

from datetime import datetime, timezone

from orbiteus_core.cache import get_redis


def _bucket_key(tenant_id, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"ai:budget:tenant:{tenant_id}:{now.strftime('%Y%m')}"


async def usage_this_month(tenant_id) -> int:
    client = get_redis()
    raw = await client.get(_bucket_key(tenant_id))
    return int(raw) if raw else 0


async def has_budget(tenant_id, monthly_token_budget: int | None) -> bool:
    if monthly_token_budget is None:
        return True
    return (await usage_this_month(tenant_id)) < monthly_token_budget


async def increment(tenant_id, tokens: int) -> int:
    if tokens <= 0:
        return await usage_this_month(tenant_id)
    client = get_redis()
    pipe = client.pipeline()
    key = _bucket_key(tenant_id)
    pipe.incrby(key, tokens)
    pipe.expire(key, 60 * 60 * 24 * 35, nx=True)  # 35 days; covers month rollover
    out = await pipe.execute()
    return int(out[0])
