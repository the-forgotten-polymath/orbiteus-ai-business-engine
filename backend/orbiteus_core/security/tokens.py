"""JWT token creation and validation.

PR 6 changes:
- Access TTL default 15 min (was 60). Configurable via env.
- Refresh TTL default 7 days (was 30). Configurable via env.
- Every token carries a `jti` (JWT ID) used by the Redis revocation list.
- Refresh tokens rotate on use — the old `jti` lands in the blacklist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from orbiteus_core.config import settings


def _new_jti() -> str:
    return uuid.uuid4().hex


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = dict(data)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload.setdefault("jti", _new_jti())
    payload["exp"] = expire
    payload["type"] = "access"
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    payload = dict(data)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload.setdefault("jti", _new_jti())
    payload["exp"] = expire
    payload["type"] = "refresh"
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise JWTError("Not an access token")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid refresh token: {e}") from e


# ---------------------------------------------------------------------------
# Password reset tokens (single-use, short-lived)
# ---------------------------------------------------------------------------
#
# Single-use is enforced by the regular `jti` revocation list in Redis: the
# moment a reset token is consumed by `POST /api/auth/password/reset`, its
# `jti` is added to `jti:revoked:*` for the remaining TTL. A second attempt
# with the same token therefore returns 401 "Token revoked".
#
# Default TTL is 30 minutes (configurable via `password_reset_ttl_minutes`)
# — long enough for a user to read the email, short enough to bound the
# blast radius of a stolen mailbox.

def create_password_reset_token(user_id: uuid.UUID, *, ttl_minutes: int | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "type": "password_reset",
        "jti": _new_jti(),
        "exp": datetime.now(timezone.utc) + timedelta(
            minutes=ttl_minutes or getattr(settings, "password_reset_ttl_minutes", 30),
        ),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_password_reset_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "password_reset":
            raise JWTError("Not a password-reset token")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid password-reset token: {e}") from e
