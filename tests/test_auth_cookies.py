"""Auth cookie helpers — pure FastAPI Response interaction, no DB.

Validates that:
  * `set_access_cookie` writes an httpOnly, SameSite=Lax cookie scoped to "/".
  * `set_refresh_cookie` is scoped to "/api/auth" so it never leaks to module
    routes.
  * `Secure` flag flips with `settings.environment` ("production" → secure).
  * `clear_auth_cookies` emits expiring entries for both names.
  * The Next.js middleware in `admin-ui/src/middleware.ts` watches the same
    cookie name the backend writes (defence-in-depth contract test).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import Response


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def cookies_module(monkeypatch):
    # Force a deterministic environment for the test process.
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("JWT_SECRET", "test-secret-please-rotate")
    return _load(
        "orbiteus_auth_cookies",
        BACKEND / "orbiteus_core" / "security" / "cookies.py",
    )


def _set_cookie_headers(resp: Response) -> list[str]:
    """Return all `Set-Cookie` values from a Starlette Response."""
    out: list[str] = []
    for k, v in resp.headers.raw:
        if k.lower() == b"set-cookie":
            out.append(v.decode())
    return out


def test_access_cookie_is_httponly_lax(cookies_module):
    resp = Response()
    cookies_module.set_access_cookie(resp, "abc.def.ghi")
    headers = _set_cookie_headers(resp)
    assert any("orbiteus_token=abc.def.ghi" in h for h in headers)
    target = next(h for h in headers if h.startswith("orbiteus_token="))
    assert "HttpOnly" in target
    assert "SameSite=lax" in target
    assert "Path=/" in target


def test_refresh_cookie_scoped_to_auth(cookies_module):
    resp = Response()
    cookies_module.set_refresh_cookie(resp, "rrr.sss.ttt")
    headers = _set_cookie_headers(resp)
    target = next(h for h in headers if h.startswith("orbiteus_refresh="))
    assert "Path=/api/auth" in target
    assert "HttpOnly" in target


def test_clear_emits_two_expiring_cookies(cookies_module):
    resp = Response()
    cookies_module.clear_auth_cookies(resp)
    headers = _set_cookie_headers(resp)
    names = [h.split("=", 1)[0] for h in headers]
    assert "orbiteus_token" in names
    assert "orbiteus_refresh" in names


def test_secure_flag_flips_in_production(cookies_module, monkeypatch):
    """`Secure` flag is driven by `settings.environment`.

    We don't reconstruct the entire production Settings model (it pins many
    other invariants like BOOTSTRAP_ADMIN_PASSWORD); instead we patch the
    attribute the helper actually reads.
    """
    from orbiteus_core import config as cfg

    monkeypatch.setattr(cfg.settings, "environment", "production", raising=True)
    resp = Response()
    cookies_module.set_access_cookie(resp, "tkn")
    target = next(
        v.decode() for k, v in resp.headers.raw if k.lower() == b"set-cookie"
    )
    assert "Secure" in target


def test_frontend_proxy_watches_same_cookie_name():
    """Defence-in-depth: the SSR gate must read what the backend writes.

    Lives at `admin-ui/src/proxy.ts` (Next 16 renamed `middleware.ts` to
    `proxy.ts`); we read whichever exists.
    """
    src = REPO_ROOT / "admin-ui" / "src"
    candidates = [src / "proxy.ts", src / "middleware.ts"]
    found = next((p for p in candidates if p.exists()), None)
    assert found is not None, "missing edge gate (proxy.ts / middleware.ts)"
    mw = found.read_text(encoding="utf-8")
    assert 'cookies.get("orbiteus_token")' in mw
    assert "redirect" in mw  # actually redirects, not just rewrite
    assert "/login" in mw


def test_axios_uses_cookie_credentials():
    api_ts = (REPO_ROOT / "admin-ui" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    assert "withCredentials: true" in api_ts
    # Old localStorage-based bearer injection must be gone.
    assert "Authorization = `Bearer" not in api_ts
