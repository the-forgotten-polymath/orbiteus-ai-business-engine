# ADR-0001: Engine vs Framework vs Product positioning

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** strategy, architecture

## Context

Orbiteus could be positioned as a pure framework (build everything yourself),
a finished product (one shape, hard to bend), or somewhere in between. We need
clarity for both internal contributors and adopters.

## Decision

Orbiteus is an **engine**: framework primitives + opinionated batteries
(auth, RBAC, multitenancy, audit, realtime, AI layer) + **one canonical product
example** (CRM-MVP). Adopters can keep, replace, or remove the canonical example
without affecting the engine.

## Consequences

- Documentation, tests, and CI must distinguish FRAMEWORK vs PRODUCT layers.
- The canonical CRM ships with the engine and is maintained as a first-class
  citizen.
- Breaking changes in the framework layer require a major version bump;
  changes in the canonical example are minor with a migration note.
- Sample modules (`hr`, `project`, `social`) are explicitly optional and have
  no SLA.

## Alternatives considered

- **Pure framework** — rejected: senior teams would still need 3–4 months
  before producing real value.
- **Finished product** — rejected: defeats the goal of building custom
  business apps.
- **Plug-in marketplace** — premature; revisit after v1.0 when adopter base
  exists.

## References

- `docs/01-engine-positioning.md`
- `docs/26-canonical-crm.md`
