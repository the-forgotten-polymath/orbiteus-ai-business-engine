# ADR-0002: Mantine as the only design system

- **Status:** Accepted
- **Date:** 2026-05-03 (current version: Mantine 9)
- **Context tags:** frontend, design system

## Context

Senior teams want a complete, themeable component set with strong defaults,
TypeScript types, dark/light mode, and an active community. Multiple design
systems in one codebase is a maintenance nightmare.

## Decision

Mantine is the **only** design system used by `admin-ui` and `portal-ui`.
Cross-cutting widgets live in `admin-ui/src/orbiteus-ui/` (copy to portal-ui
when needed). No shadcn/ui, MUI, Chakra, Ant Design, or
raw Tailwind is allowed without a superseding ADR.

## Version policy

This ADR locks the *choice of Mantine*, **not** a specific major version.
Rolling Mantine forward (e.g. 8 → 9 → 10) is a routine maintenance task and
does **not** require a new ADR; it requires:

- Bumping `@mantine/*` peers in `admin-ui/package.json` and `portal-ui/package.json`.
- Running the migration codemod when Mantine ships one.
- Adjusting `theme.ts` if breaking changes touch tokens.
- Updating `docs/10-design-system.md`, `docs/02-architecture.md`,
  `docs/pre-prompt.md`, and other places that name a specific major.

A new ADR (superseding this one) is only needed if the team proposes
*replacing* Mantine with another design system, or *adding* a second one.

The repository is currently on **Mantine 9** (manifests:
`admin-ui/package.json`, `portal-ui/package.json`).

## Consequences

- Senior devs can reuse Mantine knowledge across both apps.
- Theming and branding go through one provider.
- AI assistants see consistent component shapes; less hallucination.
- Custom widgets must integrate with Mantine theming tokens.

## Alternatives considered

- **shadcn/ui** — high quality but copy-paste model creates drift; rejected.
- **MUI** — heavier, less idiomatic with Next.js App Router; rejected.
- **Chakra UI** — fewer components than Mantine for our needs; rejected.
- **Tailwind raw** — no component library; would force us to re-invent forms,
  modals, tables; rejected.

## References

- `docs/10-design-system.md`
