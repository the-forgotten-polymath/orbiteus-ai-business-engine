"""Realtime: topic helpers + RBAC checks. No real Redis."""
from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
RT = BACKEND / "orbiteus_core" / "realtime.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rt():
    return _load("orbiteus_realtime", RT)


def test_topic_for_record_format(rt):
    tid = uuid.uuid4()
    rid = uuid.uuid4()
    t = rt.topic_for_record(tid, "crm.lead", rid)
    assert t == f"tenant:{tid}:model:crm.lead:record:{rid}"


def test_topic_for_list_format(rt):
    tid = uuid.uuid4()
    t = rt.topic_for_list(tid, "crm.lead")
    assert t == f"tenant:{tid}:model:crm.lead:list"


def test_parse_tenant_from_topic(rt):
    tid = uuid.uuid4()
    assert rt.parse_tenant_from_topic(f"tenant:{tid}:model:crm.lead:list") == str(tid)
    assert rt.parse_tenant_from_topic("garbage") is None
    assert rt.parse_tenant_from_topic("") is None


def test_topic_allowed_for_matching_tenant(rt):
    from orbiteus_core.context import RequestContext

    tid = uuid.uuid4()
    ctx = RequestContext(tenant_id=tid, user_id=uuid.uuid4())
    topic = rt.topic_for_record(tid, "crm.lead", uuid.uuid4())
    assert rt.topic_is_allowed(ctx, topic) is True


def test_topic_forbidden_for_other_tenant(rt):
    from orbiteus_core.context import RequestContext

    ctx = RequestContext(tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
    topic = rt.topic_for_record(uuid.uuid4(), "crm.lead", uuid.uuid4())
    assert rt.topic_is_allowed(ctx, topic) is False


def test_topic_allowed_for_superadmin_anywhere(rt):
    from orbiteus_core.context import RequestContext

    ctx = RequestContext(is_superadmin=True)
    topic = rt.topic_for_record(uuid.uuid4(), "crm.lead", uuid.uuid4())
    assert rt.topic_is_allowed(ctx, topic) is True


def test_register_publishers_is_idempotent(rt, monkeypatch):
    counter = {"n": 0}

    class _FakeBus:
        def subscribe(self, name, handler):
            counter["n"] += 1

    fake_module = type(sys)("orbiteus_core.events")
    fake_module.event_bus = _FakeBus()
    sys.modules["orbiteus_core.events"] = fake_module

    sys.modules.pop("orbiteus_realtime_register", None)
    rt2 = _load("orbiteus_realtime_register", RT)
    rt2._REGISTERED = False
    rt2.register_realtime_publishers()
    rt2.register_realtime_publishers()
    assert counter["n"] == 3  # not 6 — second call is a no-op
