"""Cross-tenant isolation negative tests — DoD §2.2 / §2.3 / §6.3.

We bring up two completely separate tenants via `/api/auth/register`,
have tenant A create a record, and assert that tenant B's user can
NEVER:

  * read     the record   (`GET /<resource>/<id>`)             → 404
  * list     it           (`GET /<resource>`)                   → not in items
  * write    it           (`PUT /<resource>/<id>`)              → 404
  * delete   it           (`DELETE /<resource>/<id>`)           → 404
  * subscribe to its tenant's realtime topics
                          (`/api/realtime/subscribe?topic=...`) → 403

The 404-on-cross-tenant-read is deliberate — returning 403 would leak
the existence of a record outside the tenant. This is the canonical
"Odoo-style" tenant-scoped data isolation contract.

Skipped when the dev compose backend isn't reachable.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _backend_alive() -> bool:
    try:
        import httpx
    except ImportError:
        return False
    try:
        return httpx.get(f"{BACKEND_URL}/health", timeout=1.5).status_code < 500
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _backend_alive(),
    reason=f"Backend not reachable at {BACKEND_URL}",
)


def _register(prefix: str = "iso") -> tuple[str, dict[str, object]]:
    """Bootstrap a fresh tenant + first user. Returns (access_token, user_dict)."""
    import httpx

    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = "Init1234!"
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/register",
        json={
            "name": "Iso User",
            "email": email,
            "password": password,
            "tenant_name": f"Tenant {uuid.uuid4().hex[:6]}",
            "tenant_slug": f"t-{uuid.uuid4().hex[:8]}",
        },
        timeout=10,
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    # Look up user_id + tenant_id via /me — we need them for the realtime
    # topic assertion below.
    me = httpx.get(
        f"{BACKEND_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert me.status_code == 200, me.text
    return token, me.json()


def _create_person(token: str, *, name: str) -> str:
    import httpx

    r = httpx.post(
        f"{BACKEND_URL}/api/crm/person",
        json={"name": name, "kind": "individual"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code in (200, 201), r.text
    return str(r.json()["id"])


# ---------------------------------------------------------------------------
# 1) READ a foreign record → 404 (NOT 403, to avoid leaking existence)
# ---------------------------------------------------------------------------

def test_read_other_tenants_record_returns_404():
    import httpx

    token_a, _ = _register("iso_a")
    token_b, _ = _register("iso_b")

    secret_id = _create_person(token_a, name=f"Secret {uuid.uuid4().hex[:6]}")

    r = httpx.get(
        f"{BACKEND_URL}/api/crm/person/{secret_id}",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10,
    )
    assert r.status_code == 404, (
        f"cross-tenant read should be 404 (existence leak otherwise), got {r.status_code}: {r.text}"
    )


# ---------------------------------------------------------------------------
# 2) LIST never includes a foreign record
# ---------------------------------------------------------------------------

def test_list_never_returns_other_tenants_records():
    import httpx

    token_a, _ = _register("iso_a_list")
    token_b, _ = _register("iso_b_list")

    nonce = uuid.uuid4().hex[:6]
    secret_name = f"Tenant-A-Only {nonce}"
    secret_id = _create_person(token_a, name=secret_name)

    r = httpx.get(
        f"{BACKEND_URL}/api/crm/person?limit=200",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10,
    )
    assert r.status_code == 200
    items = r.json().get("items", [])
    leaked = [it for it in items if str(it.get("id")) == secret_id or it.get("name") == secret_name]
    assert not leaked, f"tenant B saw tenant A's record: {leaked!r}"


# ---------------------------------------------------------------------------
# 3) WRITE a foreign record → 404
# ---------------------------------------------------------------------------

def test_write_other_tenants_record_returns_404():
    import httpx

    token_a, _ = _register("iso_a_w")
    token_b, _ = _register("iso_b_w")

    secret_id = _create_person(token_a, name=f"Hijack target {uuid.uuid4().hex[:4]}")

    r = httpx.put(
        f"{BACKEND_URL}/api/crm/person/{secret_id}",
        json={"name": "Hijacked!"},
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10,
    )
    assert r.status_code == 404, (
        f"cross-tenant write should be 404, got {r.status_code}: {r.text}"
    )

    # And of course tenant A's record is unchanged.
    a_view = httpx.get(
        f"{BACKEND_URL}/api/crm/person/{secret_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=10,
    )
    assert a_view.status_code == 200
    assert a_view.json()["name"].startswith("Hijack target")


# ---------------------------------------------------------------------------
# 4) DELETE a foreign record → 404
# ---------------------------------------------------------------------------

def test_delete_other_tenants_record_returns_404():
    import httpx

    token_a, _ = _register("iso_a_d")
    token_b, _ = _register("iso_b_d")

    secret_id = _create_person(token_a, name=f"Delete target {uuid.uuid4().hex[:4]}")

    r = httpx.delete(
        f"{BACKEND_URL}/api/crm/person/{secret_id}",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10,
    )
    assert r.status_code == 404, (
        f"cross-tenant delete should be 404, got {r.status_code}: {r.text}"
    )

    # Tenant A still sees the record alive.
    a_view = httpx.get(
        f"{BACKEND_URL}/api/crm/person/{secret_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        timeout=10,
    )
    assert a_view.status_code == 200


# ---------------------------------------------------------------------------
# 5) SSE subscribe to a foreign tenant's topic → 403
# ---------------------------------------------------------------------------

def test_subscribe_to_other_tenants_topic_returns_403():
    import httpx

    token_a, me_a = _register("iso_a_sse")
    token_b, _ = _register("iso_b_sse")

    foreign_topic = f"tenant:{me_a['tenant_id']}:model:crm.person:list"

    # Tenant B tries to subscribe to A's topic. We use a small read
    # timeout so the test doesn't block on a successful (long-running)
    # SSE stream — but the assertion is on the HTTP STATUS.
    with httpx.Client(timeout=2.0) as http:
        r = http.get(
            f"{BACKEND_URL}/api/realtime/subscribe",
            params=[("topic", foreign_topic)],
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert r.status_code == 403, (
        f"cross-tenant SSE subscribe should be 403, got {r.status_code}: {r.text}"
    )


# ---------------------------------------------------------------------------
# 6) Defensive: own tenant's topic IS allowed (no false positives above)
# ---------------------------------------------------------------------------

def test_subscribe_to_own_tenants_topic_is_allowed():
    """If the previous test refused everything we'd never know.
    This positive control proves the 403 above is real."""
    import httpx

    token, me = _register("iso_self")
    own_topic = f"tenant:{me['tenant_id']}:model:crm.person:list"

    with httpx.Client(timeout=2.0) as http:
        try:
            r = http.get(
                f"{BACKEND_URL}/api/realtime/subscribe",
                params=[("topic", own_topic)],
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.ReadTimeout:
            # SSE established and we read past the keep-alive — that
            # alone proves the topic is allowed.
            return

    # We may also get a clean 200 with content-type text/event-stream
    # if the server returns headers fast enough. Both are acceptable.
    assert r.status_code == 200, (
        f"own-tenant SSE subscribe should be 200, got {r.status_code}: {r.text[:200]}"
    )
    assert r.headers.get("content-type", "").startswith("text/event-stream")
