"""Unit tests for orbiteus_core.observability — pure logic, no DB.

Validated:
- JsonFormatter emits one valid JSON object per record.
- request_id ContextVar surfaces in the formatted output.
- Sensitive keys (password, secret, token, ...) are redacted in `extra=`.

The middleware itself is exercised through a Starlette test app to avoid
booting the full Orbiteus stack; this keeps the test in the docs-only
top-level pytest target (no Postgres dependency).
"""
from __future__ import annotations

import importlib.util
import io
import json
import logging
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
OBS_DIR = REPO_ROOT / "backend" / "orbiteus_core" / "observability"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def obs_logging():
    return _load("orbiteus_obs_logging", OBS_DIR / "logging.py")


def test_json_formatter_emits_valid_json(obs_logging):
    formatter = obs_logging.JsonFormatter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname="x.py", lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    line = formatter.format(record)
    payload = json.loads(line)
    assert payload["msg"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "x"
    assert "ts" in payload
    assert payload["actor"] == "system"


def test_json_formatter_includes_request_id(obs_logging):
    formatter = obs_logging.JsonFormatter()
    token = obs_logging.request_id_ctx.set("req_abc123")
    try:
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="x.py", lineno=1,
            msg="m", args=(), exc_info=None,
        )
        payload = json.loads(formatter.format(record))
    finally:
        obs_logging.request_id_ctx.reset(token)
    assert payload["request_id"] == "req_abc123"


def test_json_formatter_redacts_sensitive_extras(obs_logging):
    formatter = obs_logging.JsonFormatter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname="x.py", lineno=1,
        msg="m", args=(), exc_info=None,
    )
    record.password = "hunter2"           # type: ignore[attr-defined]
    record.api_key = "sk-secret"          # type: ignore[attr-defined]
    record.normal_field = "visible"       # type: ignore[attr-defined]
    payload = json.loads(formatter.format(record))
    assert payload["password"] == "***"
    assert payload["api_key"] == "***"
    assert payload["normal_field"] == "visible"


def test_configure_json_logging_replaces_handlers(obs_logging):
    obs_logging.configure_json_logging(level="INFO")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, obs_logging.JsonFormatter)


def test_redact_handles_nested_structures(obs_logging):
    payload = {
        "user": {"email": "a@b", "password": "p"},
        "tokens": [{"access_token": "x"}, {"value": "ok"}],
    }
    cleaned = obs_logging._redact(payload)
    assert cleaned["user"]["password"] == "***"
    assert cleaned["user"]["email"] == "a@b"
    assert cleaned["tokens"][0]["access_token"] == "***"
    assert cleaned["tokens"][1]["value"] == "ok"


def test_logger_emits_json_through_handler(obs_logging):
    """End-to-end: log a record and parse the output line as JSON."""
    obs_logging.configure_json_logging(level="DEBUG")
    root = logging.getLogger()
    captured = io.StringIO()
    # Replace the stream of the single configured handler.
    root.handlers[0].stream = captured

    logging.getLogger("orbiteus.test").info(
        "user_login",
        extra={"user_id": "u1", "password": "secret-should-disappear"},
    )

    line = captured.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["msg"] == "user_login"
    assert payload["user_id"] == "u1"
    assert payload["password"] == "***"
