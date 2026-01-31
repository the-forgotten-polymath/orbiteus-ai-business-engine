"""RBAC cache — Redis-backed L2 + cross-replica invalidation (DoD §2.4 / §7.1).

These tests use a real Redis (the `redis:7-alpine` container the dev
compose already runs) — see `pyproject.toml` `testpaths = ["tests"]`.
They exercise the contract that:

  * `reload_access_cache` writes the access matrix to Redis (`rbac:access`,
    `rbac:rules`, `rbac:version`) and bumps the version monotonically.
  * The L1 in-process cache (`_l1_access`, `_l1_rules`, exported as
    `_model_access` / `_record_rules` for backward compat) mirrors what
    was just persisted.
  * `_refresh_from_redis()` rehydrates the L1 from Redis — this is what
    the pub/sub listener (`_invalidator_loop`) calls when another
    replica publishes `rbac.invalidate`.
  * `check_model_access` denies when L1 is empty + Redis is empty
    (closed-fail), allows when superadmin, and respects the per-role
    permission bits otherwise.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


def _load_backend_modules():
    """Import the backend RBAC + cache modules with `backend/` on sys.path."""
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    # Force a fresh import so each test sees a clean L1 state.
    for name in [
        "orbiteus_core.security.rbac",
        "orbiteus_core.cache",
        "orbiteus_core.config",
    ]:
        sys.modules.pop(name, None)
    rbac = importlib.import_module("orbiteus_core.security.rbac")
    cache = importlib.import_module("orbiteus_core.cache")
    return rbac, cache


def _redis_url() -> str:
    """Match dev compose: redis-cli on host port 6379."""
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest_asyncio.fixture()
async def rbac():
    """Yield a freshly-imported rbac module bound to a clean Redis namespace."""
    os.environ["REDIS_URL"] = _redis_url()
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://orbiteus:orbiteus@localhost:5433/orbiteus",
    )
    rbac_mod, cache_mod = _load_backend_modules()

    client = cache_mod.get_redis()
    # Reset the keys this suite owns.
    await client.delete("rbac:access", "rbac:rules", "rbac:version")
    rbac_mod._l1_access.clear()
    rbac_mod._l1_rules.clear()
    rbac_mod._l1_version = 0

    yield rbac_mod

    await client.delete("rbac:access", "rbac:rules", "rbac:version")
    rbac_mod._l1_access.clear()
    rbac_mod._l1_rules.clear()
    await cache_mod.close_redis()


def _ctx(rbac_mod, *, is_superadmin: bool = False, roles: list[str] | None = None):
    return rbac_mod.RequestContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=roles or [],
        is_superadmin=is_superadmin,
    ) if hasattr(rbac_mod, "RequestContext") else None


@pytest.mark.asyncio
async def test_reload_persists_to_redis_and_bumps_version(rbac):
    from orbiteus_core.cache import get_redis
    client = get_redis()

    access_entries = [
        {"role_name": "test_role", "model_name": "x.foo",
         "perm_read": True, "perm_write": False,
         "perm_create": False, "perm_unlink": False},
    ]
    await rbac.reload_access_cache(access_entries, [])

    raw = await client.get("rbac:access")
    assert raw is not None
    decoded = json.loads(raw)
    assert decoded["test_role"]["x.foo"]["read"] is True
    assert decoded["test_role"]["x.foo"]["write"] is False

    version = int(await client.get("rbac:version"))
    assert version >= 1

    # L1 mirrors what we just wrote.
    assert rbac._l1_access["test_role"]["x.foo"]["read"] is True
    # Backwards-compat alias points at the same dict.
    assert rbac._model_access is rbac._l1_access


@pytest.mark.asyncio
async def test_second_reload_bumps_version_again(rbac):
    from orbiteus_core.cache import get_redis
    client = get_redis()

    await rbac.reload_access_cache([], [])
    v1 = int(await client.get("rbac:version"))

    await rbac.reload_access_cache([], [])
    v2 = int(await client.get("rbac:version"))
    assert v2 == v1 + 1


@pytest.mark.asyncio
async def test_refresh_from_redis_replays_into_l1(rbac):
    from orbiteus_core.security.rbac import _refresh_from_redis
    from orbiteus_core.cache import get_redis

    # Replica A populates Redis directly.
    client = get_redis()
    payload = {"role_a": {"model.x": {"read": True, "write": False,
                                       "create": False, "unlink": False}}}
    await client.set("rbac:access", json.dumps(payload))
    await client.set("rbac:rules", json.dumps({"model.x": []}))
    await client.set("rbac:version", "42")

    # Replica B starts with empty L1, then refreshes.
    rbac._l1_access.clear()
    rbac._l1_rules.clear()
    rbac._l1_version = 0
    refreshed = await _refresh_from_redis()
    assert refreshed is True
    assert rbac._l1_access["role_a"]["model.x"]["read"] is True
    assert rbac._l1_version == 42


@pytest.mark.asyncio
async def test_check_model_access_closed_fail_when_empty(rbac):
    """Empty L1 + empty Redis should DENY (never accidentally bypass RBAC)."""
    ctx = type("Ctx", (), {"is_superadmin": False, "roles": ["any"]})()
    allowed = await rbac.check_model_access(ctx, "nope.model", "read")
    assert allowed is False


@pytest.mark.asyncio
async def test_check_model_access_superadmin_bypass(rbac):
    ctx = type("Ctx", (), {"is_superadmin": True, "roles": []})()
    allowed = await rbac.check_model_access(ctx, "nope.model", "unlink")
    assert allowed is True


@pytest.mark.asyncio
async def test_check_model_access_per_role(rbac):
    await rbac.reload_access_cache(
        [
            {"role_name": "reader", "model_name": "doc.entry",
             "perm_read": True, "perm_write": False,
             "perm_create": False, "perm_unlink": False},
            {"role_name": "writer", "model_name": "doc.entry",
             "perm_read": True, "perm_write": True,
             "perm_create": True, "perm_unlink": False},
        ],
        [],
    )

    reader_ctx = type("Ctx", (), {"is_superadmin": False, "roles": ["reader"]})()
    writer_ctx = type("Ctx", (), {"is_superadmin": False, "roles": ["writer"]})()

    assert await rbac.check_model_access(reader_ctx, "doc.entry", "read") is True
    assert await rbac.check_model_access(reader_ctx, "doc.entry", "write") is False
    assert await rbac.check_model_access(writer_ctx, "doc.entry", "write") is True
    assert await rbac.check_model_access(writer_ctx, "doc.entry", "unlink") is False


@pytest.mark.asyncio
async def test_pubsub_invalidate_refreshes_l1(rbac):
    """Replica A bumps Redis directly + publishes invalidate; Replica B's
    `_invalidator_loop` should refresh its L1 within a short window.

    Caveat: any backend container subscribed to `rbac.invalidate` on the
    same Redis instance WILL receive this notification and reload its
    own L1 from the synthetic payload below. After the assertion we
    therefore restore the real RBAC state by hitting the canonical
    `/api/base/rbac/reload` endpoint on the running backend, so a
    follow-up test (e.g. `tests/test_multi_tenant_isolation.py`) doesn't
    inherit a one-role world.
    """
    import asyncio

    from orbiteus_core.cache import get_redis

    # Start the invalidator (Replica B background task).
    await rbac.start_invalidator()
    try:
        # Give the subscription a moment to register on the channel.
        await asyncio.sleep(0.2)

        # Replica A publishes a fresh access matrix straight to Redis +
        # notifies on the channel.
        client = get_redis()
        payload = {"newrole": {"model.y": {"read": True, "write": True,
                                            "create": True, "unlink": True}}}
        await client.set("rbac:access", json.dumps(payload))
        await client.set("rbac:rules", json.dumps({"model.y": []}))
        await client.incr("rbac:version")
        await client.publish("rbac.invalidate", "ext-bump")

        # Wait up to 1s for Replica B to refresh.
        for _ in range(20):
            await asyncio.sleep(0.05)
            if "newrole" in rbac._l1_access:
                break

        assert "newrole" in rbac._l1_access, (
            "Pub/Sub invalidation did not refresh L1 within 1s"
        )
        assert rbac._l1_access["newrole"]["model.y"]["unlink"] is True
    finally:
        await rbac.stop_invalidator()
        # Restore the real RBAC matrix on every backend replica that
        # subscribed to our synthetic notification. Best-effort —
        # if the dev compose backend isn't reachable we silently move
        # on; the only consequence is that a later integration test
        # might see an empty cache, which is exactly what
        # `_flush_buckets_before_each_test` and the hard-coded
        # superadmin path already cover.
        try:
            import httpx

            backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
            login = httpx.post(
                f"{backend_url}/api/auth/login",
                json={"email": "admin@example.com", "password": "admin1234"},
                timeout=5,
            )
            if login.status_code == 200:
                token = login.json()["access_token"]
                httpx.post(
                    f"{backend_url}/api/base/rbac/reload",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
        except Exception:  # noqa: BLE001
            pass
