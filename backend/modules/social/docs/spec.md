# `social` module — spec (planned)

> **Status: PLANNED.** Not part of the v1.0 engine release. Activities
> / chatter is listed as MISSING in `docs/34-inventory-and-status.md`.
>
> **Canonical sources for the engine surface this module would use:**
> - `docs/03-modules.md` — module convention
> - `docs/12-events-and-queues.md` — EventBus subscriptions
> - `docs/14-audit.md` — relationship to audit log (chatter ≠ audit)

## Intent (when implemented)

A generic social layer (followers, comments, mentions, activity stream)
attachable to any business model via a polymorphic FK. Designed to plug
into the EventBus so module authors do not have to wire chatter
manually.

## Why deferred

Adds substantial UI surface (timeline, mention parser, notification
fan-out) and is best built once at least one external module beyond CRM
has shipped, so its API can be validated against more than one shape.
