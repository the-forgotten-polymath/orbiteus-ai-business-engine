# ADR-0014: Redis Pub/Sub as realtime backplane

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, realtime

## Context

With multiple FastAPI replicas, an SSE event emitted on one replica must reach
clients connected to another replica. Without a backplane, only clients on the
emitting replica see the event.

## Decision

Use **Redis Pub/Sub** as the cross-replica fan-out for realtime topics. Each
replica subscribes to channels matching active topics; emitters publish once,
Redis fans out.

For replay/durability we keep the Postgres Outbox (separate concern). SSE
clients reconnecting fetch fresh state from REST; replay is unnecessary at
the realtime layer.

## Consequences

- Simple, low-latency fan-out; senior devs and AI assistants understand it.
- Pub/Sub is fire-and-forget — fine because reconnect resolves missed events.
- Channel names mirror topic names (`tenant:{id}:model:{m}:record:{id}`).

## Alternatives considered

- **Redis Streams** — durable + replay, but adds complexity not needed here.
  Revisit if we need server-side replay (e.g. for AI backfill).
- **NATS / Kafka** — overkill for our scale; rejected.

## References

- `docs/11-realtime.md`
- `docs/13-cache.md`
