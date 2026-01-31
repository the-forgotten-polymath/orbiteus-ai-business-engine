# ADR-0007: Portal UI as a separate Next.js app

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** frontend, security, architecture

## Context

External partners (clients, contractors) need limited access to selected
resources. The threat model and UX are different from the admin UI.

## Decision

`portal-ui/` is a separate Next.js 16 application; shared UX is copied from
`admin-ui/src/orbiteus-ui/` when the portal adopts the same widgets.
with `admin-ui`. Separate domain (`portal.example.com`), separate cookies,
separate CSP, separate routes. JWTs carry `scope=portal` and are never
accepted by admin-ui.

## Consequences

- Smaller bundles in portal (no module sidebar, no admin widgets).
- Stricter CSP without breaking admin features.
- Two Next.js builds; npm workspaces keep dev experience tight.
- Authentication flows diverge (share-link, magic link, portal login) —
  documented in `06-auth.md`.

## Alternatives considered

- Single app with a portal route group — simpler infra, but one CSP, one
  cookie, and per-route guards everywhere; rejected for security blast
  radius.
- Static portal pages without backend interaction — fails the "comments,
  limited interaction" requirement.

## References

- `docs/09-portal-ui.md`
- `docs/25-tree-spec-portal-ui.md`
