"""FK resolution `?expand=field1,field2` — DoD §9.4.

Contract:
  * `GET /api/<module>/<model>?expand=<fk_field>` adds a sibling
    `<fk_field>__name` key in every list item, resolved to the target
    model's display column (the first of "name", "label", "title",
    "email", "code" that the target table actually has).
  * Lookup is tenant-scoped: a row whose FK points at a record outside
    the caller's tenant resolves to `None`, never the foreign label.
  * Without `?expand`, the response is unchanged (back-compat).
  * `expand=` of an unknown field, or one whose target model is not
    registered, is silently ignored — no 4xx, just no extra key.

Skipped when the dev compose backend isn't reachable, mirroring the
rest of the integration suite.
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


def _login_admin() -> str:
    import httpx

    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": "admin@example.com", "password": "admin1234"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


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


def _create_lead(token: str, *, name: str, person_id: str | None) -> str:
    import httpx

    body: dict = {"name": name, "expected_revenue": 12345}
    if person_id:
        body["person_id"] = person_id
    r = httpx.post(
        f"{BACKEND_URL}/api/crm/lead",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code in (200, 201), r.text
    return str(r.json()["id"])


def _list_leads(token: str, *, expand: str | None = None) -> list[dict]:
    import httpx

    params: dict = {"limit": 200}
    if expand:
        params["expand"] = expand
    r = httpx.get(
        f"{BACKEND_URL}/api/crm/lead",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json().get("items", [])


# ---------------------------------------------------------------------------
# 1) `?expand=person_id` resolves the display name
# ---------------------------------------------------------------------------

def test_expand_resolves_person_name():
    token = _login_admin()
    nonce = uuid.uuid4().hex[:8]
    person_name = f"FK target {nonce}"
    pid = _create_person(token, name=person_name)
    lead_name = f"FK lead {nonce}"
    lid = _create_lead(token, name=lead_name, person_id=pid)

    items = _list_leads(token, expand="person_id")
    target = next((r for r in items if r["id"] == lid), None)
    assert target is not None, "freshly created lead missing from list"
    assert target.get("person_id") == pid
    assert target.get("person_id__name") == person_name


# ---------------------------------------------------------------------------
# 2) Without expand, no `__name` key is leaked
# ---------------------------------------------------------------------------

def test_no_expand_returns_no_name_key():
    token = _login_admin()
    nonce = uuid.uuid4().hex[:8]
    pid = _create_person(token, name=f"NoExpand person {nonce}")
    lid = _create_lead(token, name=f"NoExpand lead {nonce}", person_id=pid)

    items = _list_leads(token)  # no expand
    target = next((r for r in items if r["id"] == lid), None)
    assert target is not None
    assert target.get("person_id") == pid
    # The __name key MUST NOT appear without an explicit expand.
    assert "person_id__name" not in target


# ---------------------------------------------------------------------------
# 3) NULL FK leaves __name as None / absent
# ---------------------------------------------------------------------------

def test_null_fk_resolves_to_none():
    token = _login_admin()
    nonce = uuid.uuid4().hex[:8]
    lid = _create_lead(token, name=f"NullFK lead {nonce}", person_id=None)

    items = _list_leads(token, expand="person_id")
    target = next((r for r in items if r["id"] == lid), None)
    assert target is not None
    assert target.get("person_id") is None
    # Either absent or explicitly None — both are acceptable for a
    # NULL FK.
    assert target.get("person_id__name") in (None,)


# ---------------------------------------------------------------------------
# 4) Unknown / non-FK column in `expand` is ignored gracefully
# ---------------------------------------------------------------------------

def test_unknown_expand_field_is_silently_ignored():
    token = _login_admin()
    nonce = uuid.uuid4().hex[:8]
    pid = _create_person(token, name=f"UnknownField person {nonce}")
    lid = _create_lead(token, name=f"UnknownField lead {nonce}", person_id=pid)

    items = _list_leads(token, expand="person_id,not_a_real_column")
    target = next((r for r in items if r["id"] == lid), None)
    assert target is not None
    # Real FK still resolved.
    assert target.get("person_id__name") is not None
    # Bogus column did not produce an entry.
    assert "not_a_real_column__name" not in target
