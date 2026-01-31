"""Password reset flow — DoD §3.4.

This file mirrors the test style of the rest of the suite:

  * The **unit half** (`test_password_reset_token_*`) loads only
    `orbiteus_core.security.tokens` + dependencies. It runs anywhere
    `python -m pytest` runs and has no external dependencies.

  * The **integration half** (`test_e2e_*`) talks HTTP to a running
    backend on `BACKEND_URL` (default `http://localhost:8000`) — the
    same pattern as the other suites that exercise full FastAPI
    handlers. It is skipped when the backend isn't reachable, so
    `pytest -q` on a developer laptop without docker stays green.

The contract under test (DoD §3.4):
  1. `POST /password/request` always returns 200 (no enumeration).
  2. `POST /password/reset` rotates the bcrypt hash for a valid token.
  3. The same reset token can only be consumed once (single-use).
  4. Login with the new password works; the old password fails.
"""
from __future__ import annotations

import importlib
import os
import sys
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


# ---------------------------------------------------------------------------
# Unit half — pure JWT, no network
# ---------------------------------------------------------------------------

def _load_tokens():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("JWT_SECRET", "test-secret")
    # Force a fresh import so settings pick up the env var above.
    sys.modules.pop("orbiteus_core.security.tokens", None)
    return importlib.import_module("orbiteus_core.security.tokens")


def test_password_reset_token_roundtrip():
    tokens = _load_tokens()
    user_id = uuid.uuid4()
    raw = tokens.create_password_reset_token(user_id, ttl_minutes=5)
    decoded = tokens.decode_password_reset_token(raw)
    assert decoded["sub"] == str(user_id)
    assert decoded["type"] == "password_reset"
    assert "jti" in decoded
    assert "exp" in decoded


def test_password_reset_token_rejects_other_types():
    tokens = _load_tokens()
    access = tokens.create_access_token({"sub": str(uuid.uuid4())})
    with pytest.raises(ValueError):
        tokens.decode_password_reset_token(access)

    refresh = tokens.create_refresh_token({"sub": str(uuid.uuid4())})
    with pytest.raises(ValueError):
        tokens.decode_password_reset_token(refresh)


def test_password_reset_token_two_calls_have_different_jti():
    """Single-use guard hinges on each token having its own jti."""
    tokens = _load_tokens()
    user_id = uuid.uuid4()
    a = tokens.decode_password_reset_token(tokens.create_password_reset_token(user_id))
    b = tokens.decode_password_reset_token(tokens.create_password_reset_token(user_id))
    assert a["jti"] != b["jti"]


# ---------------------------------------------------------------------------
# Integration half — talks HTTP to a running backend
# ---------------------------------------------------------------------------

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _backend_alive() -> bool:
    try:
        import httpx
    except ImportError:
        return False
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=1.5)
        return r.status_code < 500
    except Exception:  # noqa: BLE001
        return False


pytestmark_integration = pytest.mark.skipif(
    not _backend_alive(),
    reason=f"Backend not reachable at {BACKEND_URL}",
)


def _fresh_email(prefix: str = "pwreset") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_via_backend(email: str, password: str = "Init1234!") -> None:
    import httpx

    payload = {
        "name": "Reset User",
        "email": email,
        "password": password,
        "tenant_name": f"Tenant {uuid.uuid4().hex[:6]}",
        "tenant_slug": f"t-{uuid.uuid4().hex[:8]}",
    }
    r = httpx.post(f"{BACKEND_URL}/api/auth/register", json=payload, timeout=10)
    assert r.status_code == 201, r.text


def _mint_reset_token_for(email: str) -> str:
    """Mint a reset JWT that the backend will accept.

    Uses the same `JWT_SECRET` and `Settings` the backend reads. We
    rely on `BACKEND_JWT_SECRET` env var; when running against `docker
    compose`, the host shell inherits the same `.env` so this works
    out of the box.
    """
    import httpx

    # 1) Look up the user's id via the public-but-non-revealing path:
    # log in once with the bootstrap password to read /api/auth/me, then
    # use that id to mint the JWT.
    login = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": "Init1234!"},
        timeout=10,
    )
    assert login.status_code == 200, login.text
    access = login.json()["access_token"]
    me = httpx.get(
        f"{BACKEND_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {access}"},
        timeout=10,
    )
    assert me.status_code == 200, me.text
    user_id = uuid.UUID(me.json()["id"])

    tokens = _load_tokens()
    return tokens.create_password_reset_token(user_id)


@pytestmark_integration
def test_e2e_request_unknown_email_returns_200():
    import httpx

    r = httpx.post(
        f"{BACKEND_URL}/api/auth/password/request",
        json={"email": _fresh_email("ghost")},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytestmark_integration
def test_e2e_full_reset_then_login_then_reuse_blocked():
    import httpx

    email = _fresh_email("real")
    _register_via_backend(email, password="Init1234!")

    # Public-facing request — observable side-effect is the mailer log.
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/password/request",
        json={"email": email},
        timeout=10,
    )
    assert r.status_code == 200

    # Mint our own reset token (same secret) to keep the test hermetic.
    token = _mint_reset_token_for(email)

    # 1) Reset succeeds.
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/password/reset",
        json={"token": token, "new_password": "Brand-new-9999"},
        timeout=10,
    )
    assert r.status_code == 200, r.text

    # 2) New password works.
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": "Brand-new-9999"},
        timeout=10,
    )
    assert r.status_code == 200, r.text

    # 3) Old password no longer works.
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": "Init1234!"},
        timeout=10,
    )
    assert r.status_code == 401

    # 4) Re-using the SAME reset token must be rejected (single-use).
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/password/reset",
        json={"token": token, "new_password": "Yet-another-1234"},
        timeout=10,
    )
    assert r.status_code == 401
    assert "already used" in r.json().get("detail", "").lower()


@pytestmark_integration
def test_e2e_reset_rejects_short_password():
    import httpx

    bogus_token = _load_tokens().create_password_reset_token(uuid.uuid4())
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/password/reset",
        json={"token": bogus_token, "new_password": "tiny"},
        timeout=10,
    )
    assert r.status_code == 400


@pytestmark_integration
def test_e2e_reset_rejects_garbage_token():
    import httpx

    r = httpx.post(
        f"{BACKEND_URL}/api/auth/password/reset",
        json={"token": "not.a.jwt", "new_password": "Long-enough-1"},
        timeout=10,
    )
    assert r.status_code == 401
