"""Server-Sent Events realtime layer (ADR-0006, ADR-0014, docs/11-realtime.md).

Architecture:
- BaseRepository publishes `record.created/updated/deleted` on the EventBus
  (PR 3). A small subscriber here re-publishes those events to Redis Pub/Sub
  channels named after the topic.
- The `/api/realtime/subscribe` endpoint accepts one or more `topic=` query
  params, validates each topic against the request's `RequestContext`, and
  streams matching messages from Redis Pub/Sub to the client as SSE.
- Topics are namespaced by tenant; cross-tenant subscriptions are rejected.

Topic grammar (docs/11-realtime.md):

    tenant:{tenant_id}:model:{model}:record:{record_id}
    tenant:{tenant_id}:model:{model}:list
    tenant:{tenant_id}:user:{user_id}:notify
    tenant:{tenant_id}:presence:model:{model}:record:{record_id}
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from orbiteus_core.cache import get_redis
from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Topic helpers
# ---------------------------------------------------------------------------

def topic_for_record(tenant_id, model: str, record_id) -> str:
    return f"tenant:{tenant_id}:model:{model}:record:{record_id}"


def topic_for_list(tenant_id, model: str) -> str:
    return f"tenant:{tenant_id}:model:{model}:list"


def parse_tenant_from_topic(topic: str) -> str | None:
    """Return the tenant_id segment from a topic, or None if malformed."""
    parts = topic.split(":")
    if len(parts) >= 2 and parts[0] == "tenant":
        return parts[1]
    return None


def topic_is_allowed(ctx: RequestContext, topic: str) -> bool:
    """Reject topics whose tenant_id does not match the request context.

    Superadmins may subscribe across tenants.
    """
    if ctx.is_superadmin:
        return True
    tid = parse_tenant_from_topic(topic)
    if tid is None:
        return False
    if ctx.tenant_id is None:
        return False
    return str(ctx.tenant_id) == tid


# ---------------------------------------------------------------------------
# EventBus → Redis Pub/Sub bridge
# ---------------------------------------------------------------------------

_REGISTERED = False


def register_realtime_publishers() -> None:
    """Subscribe the realtime publisher to BaseRepository events. Idempotent."""
    global _REGISTERED
    if _REGISTERED:
        return

    from orbiteus_core.events import event_bus

    for name in ("record.created", "record.updated", "record.deleted"):
        event_bus.subscribe(name, _make_publisher(name))
    _REGISTERED = True
    logger.info("realtime.publishers_registered")


def _make_publisher(event_name: str):
    async def _publish(payload: dict) -> None:
        tenant_id = payload.get("tenant_id")
        model = payload.get("model")
        record_id = payload.get("id")
        if not tenant_id or not model or not record_id:
            return
        msg = json.dumps(
            {
                "event": event_name,
                "model": model,
                "record_id": str(record_id),
                "tenant_id": str(tenant_id),
                "actor": payload.get("actor"),
                "request_id": payload.get("request_id"),
                "ts": payload.get("ts"),
                "diff": payload.get("diff"),
            },
            default=str,
        )
        client = get_redis()
        await client.publish(topic_for_record(tenant_id, model, record_id), msg)
        await client.publish(topic_for_list(tenant_id, model), msg)

    _publish.__name__ = f"realtime_publish_{event_name.replace('.', '_')}"
    return _publish


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------

PING_INTERVAL_SECONDS = 25


async def stream_topics(topics: list[str]) -> AsyncIterator[bytes]:
    """Yield SSE-formatted bytes for messages on any of `topics`.

    Sends a `: ping` comment every PING_INTERVAL_SECONDS to keep proxies
    from closing the connection.
    """
    if not topics:
        # Nothing to subscribe to — short-circuit.
        yield b": no topics\n\n"
        return

    client = get_redis()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(*topics)
        last_ping = asyncio.get_event_loop().time()

        while True:
            try:
                message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0)
            except asyncio.TimeoutError:
                message = None

            if message is not None and message.get("type") == "message":
                data = message.get("data") or ""
                yield f"event: message\ndata: {data}\n\n".encode("utf-8")

            now = asyncio.get_event_loop().time()
            if now - last_ping >= PING_INTERVAL_SECONDS:
                yield b": ping\n\n"
                last_ping = now
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:  # noqa: BLE001
            pass
