"""Share-link tokens for the external portal (PR 12, ADR-0007).

Encodes a portal-scoped JWT bound to a single resource (`<model>/<id>`) with
a configurable TTL and allowed actions (read, comment, attach_file, …).

Issuance is gated by `require_auth` on the issuing endpoint; the resulting
token has `scope=portal` and is never accepted on admin-ui endpoints.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from orbiteus_core.config import settings


VALID_PERMS = {"read", "comment", "attach_file", "update_status"}


@dataclass
class ShareLinkPayload:
    resource_model: str
    resource_id: uuid.UUID
    permissions: list[str]
    tenant_id: uuid.UUID
    issued_by: uuid.UUID
    jti: str
    exp: datetime


def issue(
    *,
    resource_model: str,
    resource_id: uuid.UUID,
    tenant_id: uuid.UUID,
    issued_by: uuid.UUID,
    permissions: list[str] | None = None,
    ttl_days: int = 7,
) -> str:
    """Mint a portal-scoped JWT for the given resource."""
    perms = sorted(set(permissions or ["read"]))
    bad = [p for p in perms if p not in VALID_PERMS]
    if bad:
        raise ValueError(f"invalid permissions: {bad}")
    if ttl_days <= 0 or ttl_days > 90:
        raise ValueError("ttl_days must be 1..90")

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "type": "portal_share",
        "scope": "portal",
        "aud": f"{resource_model}/{resource_id}",
        "tenant_id": str(tenant_id),
        "issued_by": str(issued_by),
        "perms": perms,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(days=ttl_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode(token: str) -> ShareLinkPayload:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise ValueError(f"invalid share-link token: {exc}") from exc

    if payload.get("type") != "portal_share" or payload.get("scope") != "portal":
        raise ValueError("not a share-link token")

    aud = payload.get("aud") or ""
    if "/" not in aud:
        raise ValueError("malformed share-link token (missing aud)")
    model, raw_id = aud.split("/", 1)

    return ShareLinkPayload(
        resource_model=model,
        resource_id=uuid.UUID(raw_id),
        permissions=list(payload.get("perms") or ["read"]),
        tenant_id=uuid.UUID(payload["tenant_id"]),
        issued_by=uuid.UUID(payload["issued_by"]),
        jti=payload.get("jti") or "",
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )
