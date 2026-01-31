# ADR-0008: CRM-MVP rename — Person / Lead / Stage / Team

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** product, data, breaking change

## Context

The current CRM models (`Customer`, `Opportunity`, `Pipeline`, `Stage`) are
heavier than needed for the MVP that demonstrates the engine. We want a
simpler, more flexible shape and a cleaner story for canonical example status.

## Decision

Rename and restructure:

- `crm.customer` → `crm.person` with `kind ∈ {lead, customer, contact}`
- `crm.opportunity` → `crm.lead`
- `crm.pipeline` removed from MVP (re-introduce in v0.3+ if needed)
- `crm.stage` kept
- `crm.team` added (leader + members)

## Consequences

- Smaller, more flexible model footprint.
- Migration path documented (expand → migrate → contract).
- Frontend hardcoded CRM pages are removed; auto-rendered routes apply.
- Existing tests rewritten for the new schema.

## Alternatives considered

- Keep current models — rejected: too heavy as canonical example.
- Skip rename, only rename in docs — rejected: real risk of confusion.

## References

- `docs/26-canonical-crm.md`
- `docs/22-implementation-plan.md` (Wave 4)
