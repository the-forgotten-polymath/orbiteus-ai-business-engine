# ADR-0012: PgBouncer in front of Postgres

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, ops, performance

## Context

With multiple Gunicorn workers across replicas, each holding a small async
pool of asyncpg connections, total backend connections scale quickly. Default
Postgres `max_connections=100` becomes a bottleneck.

## Decision

Run **PgBouncer** in `transaction` pooling mode in front of Postgres in all
production deployments. Connection string in app env points to PgBouncer.

## Consequences

- Hundreds of in-app pool connections multiplexed onto tens of real Postgres
  connections.
- Some Postgres features that depend on session state (e.g. session-level
  `LISTEN/NOTIFY`) need to be moved to per-transaction patterns or a dedicated
  connection — already done since we use Redis Pub/Sub for realtime.
- One additional service in compose.

## Alternatives considered

- Direct connections — works at small scale, breaks under load.
- Per-tenant pool sizing in app — complexity without solving the core issue.
- pgcat / Odyssey — newer poolers; revisit if PgBouncer hits a wall.

## References

- `docs/02-architecture.md`
- `docs/17-deployment.md`
