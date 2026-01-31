"""Pure unit tests for outbox helpers — no DB."""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTBOX = REPO_ROOT / "backend" / "orbiteus_core" / "outbox.py"
DISPATCHER = REPO_ROOT / "backend" / "orbiteus_core" / "outbox_dispatcher.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def outbox():
    return _load("orbiteus_outbox", OUTBOX)


def test_status_constants(outbox):
    assert outbox.OutboxStatus.PENDING == "pending"
    assert outbox.OutboxStatus.PROCESSING == "processing"
    assert outbox.OutboxStatus.DONE == "done"
    assert outbox.OutboxStatus.DEAD == "dead"


def test_serialize_uuid_to_string(outbox):
    rid = uuid4()
    out = outbox._serialize({"id": rid, "name": "x"})
    assert out == {"id": str(rid), "name": "x"}


def test_serialize_datetime_to_iso(outbox):
    dt = datetime(2026, 5, 3, 12, 34, 56, tzinfo=timezone.utc)
    out = outbox._serialize({"ts": dt})
    assert out["ts"] == "2026-05-03T12:34:56+00:00"


def test_serialize_recurses_into_nested_structures(outbox):
    rid = uuid4()
    payload = {
        "outer": {
            "id": rid,
            "items": [{"id": rid}, {"value": 1}],
        }
    }
    out = outbox._serialize(payload)
    assert out["outer"]["id"] == str(rid)
    assert out["outer"]["items"][0]["id"] == str(rid)
    assert out["outer"]["items"][1]["value"] == 1


def test_serialize_passes_through_primitives(outbox):
    payload = {"a": 1, "b": "two", "c": True, "d": None, "e": 3.14}
    assert outbox._serialize(payload) == payload


def test_dispatcher_register_is_idempotent():
    """Calling register_dispatchers twice must not double-subscribe."""
    # Stub `event_bus` so we don't import the real one (avoids backend cycles).
    fake_bus_subscriptions: dict[str, list] = {"counter": 0}

    class _FakeBus:
        def subscribe(self, name, handler):
            fake_bus_subscriptions["counter"] += 1

    fake_module = type(sys)("orbiteus_core.events")
    fake_module.event_bus = _FakeBus()
    sys.modules["orbiteus_core.events"] = fake_module

    # Force fresh import of the dispatcher with our fake bus.
    sys.modules.pop("orbiteus_dispatcher_test", None)
    mod = _load("orbiteus_dispatcher_test", DISPATCHER)
    mod._REGISTERED = False  # reset internal flag
    mod.register_dispatchers()
    assert fake_bus_subscriptions["counter"] == 3
    mod.register_dispatchers()  # second call is a no-op
    assert fake_bus_subscriptions["counter"] == 3


def test_dispatcher_make_handler_tags_event_name():
    sys.modules.pop("orbiteus_dispatcher_test2", None)
    fake_module = type(sys)("orbiteus_core.events")

    class _Bus:
        def subscribe(self, *a, **kw):
            pass

    fake_module.event_bus = _Bus()
    sys.modules["orbiteus_core.events"] = fake_module

    mod = _load("orbiteus_dispatcher_test2", DISPATCHER)
    handler = mod._make_handler("record.updated")

    captured: dict = {}

    async def fake_on_record_event(payload):
        captured.update(payload)

    mod._on_record_event = fake_on_record_event

    import asyncio
    asyncio.run(handler({"foo": "bar"}))
    assert captured["__event_name__"] == "record.updated"
    assert captured["foo"] == "bar"
