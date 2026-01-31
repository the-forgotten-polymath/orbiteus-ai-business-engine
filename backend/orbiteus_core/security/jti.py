"""JWT `jti` revocation list (Redis-backed).

Logout, password change, and refresh rotation all add the previous token's
`jti` to the revocation list with TTL = remaining `exp`. Middleware checks
the list on every request.

Keys: `jti:revoked:<jti>` → "1"  (TTL = remaining seconds)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from orbiteus_core.cache import get_redis

logger = logging.getLogger(__name__)

REVOKED_PREFIX = "jti:revoked:"


def _key(jti: str) -> str:
    return f"{REVOKED_PREFIX}{jti}"


async def revoke(jti: str, exp_unix: int | float) -> None:
    """Add `jti` to the blacklist for the remaining TTL.

    Called on logout, refresh-rotate, and on suspected compromise.
    """
    if not jti:
        return
    now = datetime.now(timezone.utc).timestamp()
    ttl = max(int(exp_unix - now), 1)
    client = get_redis()
    await client.set(_key(jti), "1", ex=ttl)
    logger.debug("jti.revoked", extra={"jti": jti, "ttl_s": ttl})


async def is_revoked(jti: str) -> bool:
    if not jti:
        return False
    client = get_redis()
    return bool(await client.exists(_key(jti)))
