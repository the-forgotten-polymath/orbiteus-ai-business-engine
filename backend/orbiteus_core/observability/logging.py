"""Structured JSON logging with request_id correlation.

Senior-friendly: stdlib `logging` only. Output one JSON object per line.

Usage in `api.py`:

    from orbiteus_core.observability import configure_json_logging

    configure_json_logging(level="INFO")

The `request_id` field is automatically injected by `RequestIdMiddleware`
through a `contextvars.ContextVar`, so any log call inside a request scope
gets it for free.
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Context vars — set by middleware, read by the formatter.
# ---------------------------------------------------------------------------

request_id_ctx: ContextVar[str | None] = ContextVar("orbiteus_request_id", default=None)
tenant_id_ctx: ContextVar[str | None] = ContextVar("orbiteus_tenant_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("orbiteus_user_id", default=None)
actor_ctx: ContextVar[str] = ContextVar("orbiteus_actor", default="system")

_REDACT_KEYS = {
    "password",
    "password_hash",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "secret_key",
    "ai_secret_key",
}


def _redact(obj: Any) -> Any:
    """Recursively replace values whose key looks sensitive with '***'."""
    if isinstance(obj, dict):
        return {
            k: ("***" if k.lower() in _REDACT_KEYS else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


class JsonFormatter(logging.Formatter):
    """Format every record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Context vars
        rid = request_id_ctx.get()
        if rid:
            payload["request_id"] = rid
        tid = tenant_id_ctx.get()
        if tid:
            payload["tenant_id"] = tid
        uid = user_id_ctx.get()
        if uid:
            payload["user_id"] = uid
        payload["actor"] = actor_ctx.get()

        # Allow ad-hoc structured fields via `logger.info("...", extra={"k": v})`
        reserved = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "message", "module",
            "msecs", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in reserved and not k.startswith("_")
        }
        if extras:
            payload.update(_redact(extras))

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_json_logging(level: str = "INFO") -> None:
    """Replace existing handlers with a single JSON stdout handler.

    Idempotent — safe to call multiple times.
    """
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Quiet down noisy libraries that log INFO at every connection.
    for noisy in ("uvicorn.access", "uvicorn.error", "asyncio"):
        logging.getLogger(noisy).setLevel("WARNING")
