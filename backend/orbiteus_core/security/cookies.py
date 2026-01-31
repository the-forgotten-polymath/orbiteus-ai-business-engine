"""Auth cookie helpers.

Centralises the cookie names + attributes so login / refresh / logout
all stay in sync (and so the SSR middleware in `admin-ui` and `portal-ui`
sees the same name).

Cookies are httpOnly + SameSite=Lax. `Secure` is enabled automatically in
production (`settings.environment == "production"`).

See `docs/06-auth.md` and `docs/adr/0017-httponly-cookie-session.md`.
"""
from __future__ import annotations

from fastapi import Response

from orbiteus_core.config import settings


ACCESS_COOKIE = "orbiteus_token"
REFRESH_COOKIE = "orbiteus_refresh"


def _is_secure() -> bool:
    return settings.environment.lower() == "production"


def set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
        path="/",
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    """Refresh cookie scoped to the refresh endpoint to minimise exposure."""
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
        path="/api/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
