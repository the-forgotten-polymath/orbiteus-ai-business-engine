"""In-process EventBus.

Synchronous async pub/sub within a single request lifecycle. Subscribers
that must persist beyond the request go through the Postgres Outbox
(introduced in PR 4) — never block the request handler on remote I/O.

Usage:

    from orbiteus_core.events import event_bus

    @event_bus.on("record.created")
    async def on_record_created(payload: dict) -> None:
        ...

    await event_bus.publish("record.created", {"model": "crm.lead", ...})

Subscriber errors are isolated: an exception in one handler does not stop
others. Errors are logged with the event name + handler name.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


Handler = Callable[[dict[str, Any]], Awaitable[None] | None]


class EventBus:
    """Tiny async-aware event bus.

    Both sync and async handlers are supported. Sync handlers are wrapped
    so the bus always returns awaitable results.
    """

    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event: str) -> Callable[[Handler], Handler]:
        """Decorator to subscribe a handler to an event."""

        def deco(fn: Handler) -> Handler:
            self.subscribe(event, fn)
            return fn

        return deco

    def subscribe(self, event: str, handler: Handler) -> None:
        self._subs[event].append(handler)

    def unsubscribe(self, event: str, handler: Handler) -> None:
        if handler in self._subs.get(event, ()):
            self._subs[event].remove(handler)

    def clear(self, event: str | None = None) -> None:
        """Drop subscribers (mostly for tests)."""
        if event is None:
            self._subs.clear()
        else:
            self._subs.pop(event, None)

    def subscribers(self, event: str) -> list[Handler]:
        return list(self._subs.get(event, ()))

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        """Dispatch all handlers in registration order, isolating errors."""
        for handler in list(self._subs.get(event, ())):
            try:
                result = handler(payload)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: BLE001
                logger.exception(
                    "event_bus.handler_failed",
                    extra={"event": event, "handler": getattr(handler, "__name__", repr(handler))},
                )


# Module-level singleton — preferred handle for app code.
event_bus = EventBus()


async def publish(event: str, payload: dict[str, Any]) -> None:
    """Convenience wrapper used by `BaseRepository` hooks."""
    await event_bus.publish(event, payload)
