# ADR-0016: npm workspaces with `packages/ui` (superseded)

- **Status:** Superseded (2026-05-04)
- **Date:** 2026-05-03
- **Context tags:** frontend, monorepo

## Original decision

`admin-ui` and `portal-ui` shared widgets and AI components via an npm workspace
`packages/ui` published in-repo as `@orbiteus/ui`.

## Superseding change

The workspace package was **removed**. Shared React code now lives under
`admin-ui/src/orbiteus-ui/` (widgets + AI). `portal-ui` is a separate app with
no npm link to that tree; when the portal needs the same components, **copy**
the relevant files there (explicit duplication over a hidden shared package).

Root `package.json` workspaces are only `admin-ui` and `portal-ui`.

## Consequences (current)

- Docker build context still uses the monorepo root for `npm install`, but no
  longer copies a `packages/` tree.
- Fewer moving parts for contributors who think in “backend / admin / portal”
  only.

## References

- `admin-ui/src/orbiteus-ui/`
- `docs/10-design-system.md`
