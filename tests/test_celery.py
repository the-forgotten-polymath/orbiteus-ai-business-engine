"""Pure unit tests for Celery config and webhook signing — no Redis, no DB."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


@pytest.fixture(scope="module")
def celery_app():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location("orbiteus_celery_app", BACKEND / "celery_app.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orbiteus_celery_app"] = mod
    spec.loader.exec_module(mod)
    return mod.app


def test_celery_uses_redis_broker(celery_app):
    assert celery_app.conf.broker_url.startswith("redis://")


def test_celery_includes_outbox_and_webhook_tasks(celery_app):
    assert "tasks.outbox_tasks" in celery_app.conf.include
    assert "tasks.webhook_tasks" in celery_app.conf.include


def test_celery_uses_json_serializer(celery_app):
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content


def test_celery_acks_late_for_durability(celery_app):
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_celery_beat_drains_outbox_periodically(celery_app):
    schedule = celery_app.conf.beat_schedule
    assert "drain-outbox-every-5s" in schedule
    assert schedule["drain-outbox-every-5s"]["task"] == "tasks.outbox_tasks.drain_outbox"


def test_celery_beat_releases_stuck_processing(celery_app):
    schedule = celery_app.conf.beat_schedule
    assert "release-stuck-processing-every-minute" in schedule


def test_outbox_backoff_grows_with_retries():
    spec = importlib.util.spec_from_file_location(
        "orbiteus_outbox_tasks", BACKEND / "tasks" / "outbox_tasks.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orbiteus_outbox_tasks"] = mod
    spec.loader.exec_module(mod)

    assert mod._backoff_seconds(0) == 60
    assert mod._backoff_seconds(1) == 120
    assert mod._backoff_seconds(2) == 240
    # cap at one hour
    assert mod._backoff_seconds(20) == 3600


def test_webhook_hmac_signing_is_stable():
    spec = importlib.util.spec_from_file_location(
        "orbiteus_webhook_tasks", BACKEND / "tasks" / "webhook_tasks.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orbiteus_webhook_tasks"] = mod
    spec.loader.exec_module(mod)

    sig1 = mod._sign("topsecret", b'{"a":1}')
    sig2 = mod._sign("topsecret", b'{"a":1}')
    sig3 = mod._sign("different", b'{"a":1}')
    assert sig1 == sig2
    assert sig1 != sig3
    assert len(sig1) == 64  # hex-sha256
