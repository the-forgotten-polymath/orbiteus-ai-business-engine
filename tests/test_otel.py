"""OTel auto-wire — verify gating logic without spinning a real exporter."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
TRACING = BACKEND / "orbiteus_core" / "observability" / "tracing.py"


def _load():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location("orbiteus_otel_test", TRACING)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orbiteus_otel_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_disabled_when_env_not_set(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    mod = _load()
    assert mod.is_enabled() is False
    # No-op: setup_tracing returns immediately and never raises.
    mod.setup_tracing(app=None)


def test_enabled_when_env_set(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318/v1/traces")
    mod = _load()
    assert mod.is_enabled() is True


def test_setup_tracing_is_idempotent(monkeypatch):
    """Even if the deps aren't installed in this Python, setup must not raise."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318/v1/traces")
    mod = _load()
    mod._INSTALLED = True
    mod.setup_tracing(app=None)  # no exception
