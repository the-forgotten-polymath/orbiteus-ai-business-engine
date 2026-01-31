# ADR-0006: Realtime default: Server-Sent Events

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, frontend, realtime

## Context

Live updates are required so users see each other's changes without refresh.
WebSockets, long-polling, and SSE are the candidates.

## Decision

SSE is the default and required transport. WebSockets remain an opt-in for
bidirectional cases (collaborative cursors). Long-polling is only a fallback
when SSE is broken at the network layer.

## Consequences

- Simple to implement (`text/event-stream`); senior devs can `curl` to debug.
- Survives many corporate proxies that block WebSocket upgrades.
- One-way only — bidirectional flows still go via REST + SSE feedback.
- Need `proxy_buffering off` in nginx and Redis Pub/Sub for fan-out across
  replicas.

## Alternatives considered

- WebSockets first — more complex, more failure modes; rejected for default.
- Long-polling primary — wasteful at scale, harder to get right; rejected.

## References

- `docs/11-realtime.md`
- `docs/adr/0014-redis-pubsub-as-realtime-backplane.md`
