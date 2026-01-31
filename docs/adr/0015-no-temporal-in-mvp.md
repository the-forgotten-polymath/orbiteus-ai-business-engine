# ADR-0015: No Temporal in MVP

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, scope

## Context

Temporal.io is a strong durable workflow engine, but adds: own server, own DB,
own SDK with version-sensitive quirks. Senior Python fluency in Temporal is
uneven; AI assistants vary in correctness across SDK versions.

## Decision

MVP does **not** include Temporal. Durable side effects use the Postgres
Outbox + Celery worker pattern (ADR-0010, ADR-0013). Long-running orchestrations
are implemented as small state machines in service code, persisted in
business tables.

Temporal returns as an opt-in compose profile in v1.x if real sagas appear
(multi-step billing, multi-week onboarding) where Outbox alone becomes
unwieldy.

## Consequences

- Smaller operational footprint for adopters.
- Familiar tools across the team.
- Some advanced workflow patterns require more code than they would with
  Temporal — acceptable trade-off at MVP scope.

## Alternatives considered

- Ship Temporal as a default — rejected on "boring tech" filter.
- Use a custom mini-saga library — reinvents the wheel; rejected.

## References

- `docs/12-events-and-queues.md`
- `docs/22-implementation-plan.md`
