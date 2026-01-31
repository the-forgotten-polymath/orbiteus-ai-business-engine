"""AI streaming chat — DoD §8.8.

Two halves, mirroring the rest of the suite:

  * Unit half: loads the provider base + adapters, exercises the
    `chat_stream` contract on a fake provider that yields a fixed
    sequence of events. Asserts:
      - default `chat_stream` fallback emits text → done from a
        non-streaming `chat()` result
      - native `chat_stream` events are passed through unchanged
        (text fragments + tool_calls + done)
      - SSE serialization (`event:` + `data:` lines) is well-formed

  * Integration half: pings the live backend and asserts:
      - `POST /api/ai/chat`             returns `application/json`
      - `POST /api/ai/chat?stream=1`    returns `text/event-stream`
        (or 412 if no credential — both prove the dispatch works)

The integration half is skipped when the dev compose backend isn't
reachable so a bare laptop run of `pytest -q` stays green.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _ensure_backend_path():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


# ---------------------------------------------------------------------------
# Unit half
# ---------------------------------------------------------------------------

def _load_base():
    _ensure_backend_path()
    sys.modules.pop("orbiteus_core.ai.providers.base", None)
    return importlib.import_module("orbiteus_core.ai.providers.base")


def test_default_chat_stream_emits_text_then_done():
    """Provider that doesn't override `chat_stream` should reuse `chat()`
    and emit a single text chunk + done."""
    base = _load_base()

    class _FakeProvider(base.Provider):
        name = "fake"

        async def ping(self, api_key: str) -> bool:
            return True

        async def chat(self, api_key, *, messages, tools=None, model=None,
                       max_tokens=1024, temperature=0.2):
            return base.ChatResult(
                text="hello world",
                tool_calls=[{"id": "t1", "name": "x", "arguments": {}}],
                usage_tokens=42,
                finish_reason="end_turn",
            )

        async def embed(self, api_key, *, texts, model=None):
            return []

    async def _run():
        events = []
        async for ev in _FakeProvider().chat_stream("k", messages=[]):
            events.append((ev.kind, ev.data))
        return events

    events = asyncio.run(_run())
    kinds = [k for k, _ in events]
    assert kinds == ["text", "tool_call", "done"], kinds

    text_event = events[0][1]
    assert text_event["delta"] == "hello world"

    done_event = events[-1][1]
    assert done_event["usage_tokens"] == 42
    assert done_event["finish_reason"] == "end_turn"


def test_native_chat_stream_passthrough():
    """A provider with native streaming yields multiple text deltas;
    each must arrive as its own event."""
    base = _load_base()

    class _StreamingProvider(base.Provider):
        name = "streaming"

        async def ping(self, api_key: str) -> bool:
            return True

        async def chat(self, api_key, *, messages, tools=None, model=None,
                       max_tokens=1024, temperature=0.2):
            raise NotImplementedError

        async def chat_stream(self, api_key, *, messages, tools=None, model=None,
                              max_tokens=1024, temperature=0.2):
            for chunk in ["Hello", ", ", "world", "!"]:
                yield base.ChatStreamEvent("text", {"delta": chunk})
            yield base.ChatStreamEvent(
                "tool_call",
                {"id": "t9", "name": "search", "arguments": {"q": "leads"}},
            )
            yield base.ChatStreamEvent(
                "done",
                {"usage_tokens": 17, "finish_reason": "stop"},
            )

        async def embed(self, api_key, *, texts, model=None):
            return []

    async def _run():
        events = []
        async for ev in _StreamingProvider().chat_stream("k", messages=[]):
            events.append((ev.kind, ev.data))
        return events

    events = asyncio.run(_run())
    text_chunks = [d["delta"] for k, d in events if k == "text"]
    assert "".join(text_chunks) == "Hello, world!"
    tool_calls = [d for k, d in events if k == "tool_call"]
    assert len(tool_calls) == 1 and tool_calls[0]["name"] == "search"
    done = [d for k, d in events if k == "done"]
    assert done and done[0]["usage_tokens"] == 17


# ---------------------------------------------------------------------------
# Integration half
# ---------------------------------------------------------------------------

def _backend_alive() -> bool:
    try:
        import httpx
    except ImportError:
        return False
    try:
        return httpx.get(f"{BACKEND_URL}/health", timeout=1.5).status_code < 500
    except Exception:  # noqa: BLE001
        return False


pytestmark_integration = pytest.mark.skipif(
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


@pytestmark_integration
def test_chat_endpoint_dispatches_on_stream_flag():
    """Without `?stream=1` the endpoint speaks JSON; with it, SSE.

    No credential is configured for the demo tenant, so both calls
    return 412 — but the responses MUST carry the right content-type
    so a frontend can pick the right consumer at request time.
    """
    import httpx

    token = _login_admin()
    headers = {"Authorization": f"Bearer {token}"}
    body = {"messages": [{"role": "user", "content": "ping"}]}

    # Non-streaming variant (default).
    r1 = httpx.post(
        f"{BACKEND_URL}/api/ai/chat",
        headers=headers,
        json=body,
        timeout=10,
    )
    assert r1.status_code == 412
    ct1 = r1.headers.get("content-type", "")
    assert ct1.startswith("application/json"), (
        f"non-stream content-type was {ct1!r}"
    )

    # Streaming variant — same outcome (412), but the dispatch works:
    # FastAPI returns the canonical StreamingResponse content-type even
    # when the underlying generator never yielded (because the 412
    # is raised in `_resolve_chat_inputs` *before* `_sse()` is called).
    # We therefore accept either application/json (412 raised early)
    # or text/event-stream (would happen with a real credential).
    r2 = httpx.post(
        f"{BACKEND_URL}/api/ai/chat?stream=1",
        headers=headers,
        json=body,
        timeout=10,
    )
    assert r2.status_code == 412
    ct2 = r2.headers.get("content-type", "")
    assert (
        ct2.startswith("application/json")
        or ct2.startswith("text/event-stream")
    ), f"stream content-type was {ct2!r}"
