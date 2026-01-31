"""Pure unit tests for cache / jti / rate-limit primitives.

We use `fakeredis` if installed; otherwise we mock the client surface. No real
Redis or backend imports beyond the targeted modules.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
CACHE = BACKEND / "orbiteus_core" / "cache.py"
JTI = BACKEND / "orbiteus_core" / "security" / "jti.py"
RL = BACKEND / "orbiteus_core" / "security" / "rate_limit.py"
TOKENS = BACKEND / "orbiteus_core" / "security" / "tokens.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeRedis:
    """Minimal in-memory async stand-in for tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    # --- pipeline used by Cache.incr / rate_limit.check
    def pipeline(self):
        outer = self

        class _Pipe:
            def __init__(self) -> None:
                self.ops: list = []

            def incr(self, key, n=1):
                self.ops.append(("incr", key, n))
                return self

            def expire(self, key, ttl, nx=False):
                self.ops.append(("expire", key, ttl, nx))
                return self

            async def execute(self) -> list:
                results = []
                for op in self.ops:
                    if op[0] == "incr":
                        _, k, n = op
                        cur = int(outer.store.get(k, "0"))
                        cur += n
                        outer.store[k] = str(cur)
                        results.append(cur)
                    elif op[0] == "expire":
                        results.append(True)
                return results

        return _Pipe()

    async def set(self, key, value, ex=None):
        self.store[key] = str(value)
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n

    async def exists(self, *keys):
        return sum(1 for k in keys if k in self.store)

    async def incr(self, key, n=1):
        cur = int(self.store.get(key, "0")) + n
        self.store[key] = str(cur)
        return cur

    async def expire(self, key, ttl, nx=False):
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    cache_mod = _load("orbiteus_cache_test", CACHE)
    monkeypatch.setattr(cache_mod, "_client", fake, raising=False)
    monkeypatch.setattr(cache_mod, "get_redis", lambda: fake)

    # Refresh modules that already imported `get_redis`.
    sys.modules.pop("orbiteus_jti_test", None)
    sys.modules.pop("orbiteus_rl_test", None)
    return fake, cache_mod


def test_cache_set_get_delete(fake_redis):
    _, cache_mod = fake_redis
    cache = cache_mod.get_cache()

    asyncio.run(cache.set("k1", {"a": 1}, ttl=60))
    assert asyncio.run(cache.get("k1")) == {"a": 1}
    assert asyncio.run(cache.exists("k1")) is True

    asyncio.run(cache.delete("k1"))
    assert asyncio.run(cache.get("k1")) is None


def test_cache_incr(fake_redis):
    _, cache_mod = fake_redis
    cache = cache_mod.get_cache()
    n1 = asyncio.run(cache.incr("counter", ttl=60))
    n2 = asyncio.run(cache.incr("counter", ttl=60))
    assert (n1, n2) == (1, 2)


def test_jti_revoke_and_check(fake_redis, monkeypatch):
    fake, _ = fake_redis
    jti_mod = _load("orbiteus_jti_test", JTI)
    monkeypatch.setattr(jti_mod, "get_redis", lambda: fake)

    import time
    asyncio.run(jti_mod.revoke("abc", time.time() + 60))
    assert asyncio.run(jti_mod.is_revoked("abc")) is True
    assert asyncio.run(jti_mod.is_revoked("never-issued")) is False


def test_rate_limit_allow_then_block(fake_redis, monkeypatch):
    fake, _ = fake_redis
    rl_mod = _load("orbiteus_rl_test", RL)
    monkeypatch.setattr(rl_mod, "get_redis", lambda: fake)

    decisions = []
    for _ in range(3):
        decisions.append(asyncio.run(rl_mod.check("ip:1.2.3.4", limit=2)))

    assert decisions[0].allowed is True
    assert decisions[1].allowed is True
    assert decisions[2].allowed is False
    assert decisions[2].retry_after >= 0


def test_jwt_tokens_carry_jti():
    tokens = _load("orbiteus_tokens_test", TOKENS)
    access = tokens.create_access_token({"sub": "u1"})
    payload = tokens.decode_access_token(access)
    assert "jti" in payload and len(payload["jti"]) > 16
    assert payload["type"] == "access"


def test_settings_defaults_are_15_min_and_7_days():
    """PR 6 binds tighter defaults; envs override."""
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from orbiteus_core.config import Settings

    s = Settings(_env_file=None)
    assert s.access_token_expire_minutes == 15
    assert s.refresh_token_expire_days == 7
