"""EventBus tests — pure logic, no DB."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = REPO_ROOT / "backend" / "orbiteus_core" / "events.py"


@pytest.fixture(scope="module")
def events_mod():
    spec = importlib.util.spec_from_file_location("orbiteus_events", EVENTS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orbiteus_events"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_subscribe_and_publish_async(events_mod):
    bus = events_mod.EventBus()
    received: list[dict] = []

    async def handler(payload):
        received.append(payload)

    bus.subscribe("record.created", handler)
    asyncio.run(bus.publish("record.created", {"x": 1}))
    assert received == [{"x": 1}]


def test_subscribe_and_publish_sync(events_mod):
    bus = events_mod.EventBus()
    received: list[dict] = []

    def handler(payload):
        received.append(payload)

    bus.subscribe("e", handler)
    asyncio.run(bus.publish("e", {"v": "ok"}))
    assert received == [{"v": "ok"}]


def test_handlers_run_in_registration_order(events_mod):
    bus = events_mod.EventBus()
    order: list[int] = []

    bus.subscribe("e", lambda p: order.append(1))
    bus.subscribe("e", lambda p: order.append(2))
    bus.subscribe("e", lambda p: order.append(3))

    asyncio.run(bus.publish("e", {}))
    assert order == [1, 2, 3]


def test_handler_error_does_not_break_others(events_mod):
    bus = events_mod.EventBus()
    survived: list[str] = []

    async def boom(payload):
        raise RuntimeError("handler exploded")

    async def survives(payload):
        survived.append("ok")

    bus.subscribe("e", boom)
    bus.subscribe("e", survives)

    asyncio.run(bus.publish("e", {}))
    assert survived == ["ok"]


def test_decorator_subscribes(events_mod):
    bus = events_mod.EventBus()

    @bus.on("login")
    def on_login(payload):
        payload["seen"] = True

    bag = {}
    asyncio.run(bus.publish("login", bag))
    assert bag == {"seen": True}


def test_unsubscribe(events_mod):
    bus = events_mod.EventBus()
    received: list = []

    def h(payload):
        received.append(1)

    bus.subscribe("e", h)
    bus.unsubscribe("e", h)
    asyncio.run(bus.publish("e", {}))
    assert received == []


def test_clear_all(events_mod):
    bus = events_mod.EventBus()
    bus.subscribe("a", lambda p: None)
    bus.subscribe("b", lambda p: None)
    bus.clear()
    assert bus.subscribers("a") == []
    assert bus.subscribers("b") == []


def test_clear_specific_event(events_mod):
    bus = events_mod.EventBus()
    bus.subscribe("a", lambda p: None)
    bus.subscribe("b", lambda p: None)
    bus.clear("a")
    assert bus.subscribers("a") == []
    assert len(bus.subscribers("b")) == 1


def test_module_singleton_is_an_eventbus(events_mod):
    assert isinstance(events_mod.event_bus, events_mod.EventBus)
