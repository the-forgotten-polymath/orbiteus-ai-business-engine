# ADR-0013: Celery 5 instead of arq / dramatiq / RQ

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, queues, ergonomics

## Context

We need a task runner for the Outbox drainer, scheduled jobs (Celery Beat),
embeddings refresh, webhook delivery, and AI background calls. Async-native
options (arq) are tempting but have smaller communities.

## Decision

Use **Celery 5** with Redis broker and Redis result backend. Celery Beat for
schedules. Workers run in a dedicated `worker` service in compose.

Async work (httpx to LLM providers, etc.) runs via `asyncio.run(coro)` inside
synchronous Celery tasks — boring and well-understood.

## Consequences

- Largest Python community for task queues — every senior dev knows Celery.
- Excellent docs, tooling (flower), and AI fluency in code generation.
- Slightly more memory per worker than arq.
- Async-inside-sync pattern is a known idiom.

## Alternatives considered

- **arq** — nice async-first design, smaller community; rejected on "boring tech".
- **dramatiq** — solid, but smaller than Celery; rejected.
- **RQ** — sync-only, weaker scheduling; rejected.

## References

- `docs/12-events-and-queues.md`
- `docs/adr/0010-eventbus-postgres-outbox.md`
