# `project` module — spec (planned)

> **Status: PLANNED.** Not part of the v1.0 engine release.
>
> **Canonical sources for the engine surface this module would use:**
> - `docs/03-modules.md` — module convention
> - `docs/09-portal-ui.md` — external partner views (read-only project
>   trees, comments)

## Intent (when implemented)

Project + Task hierarchy with calendar / kanban / Gantt views, and
read-only / comment-only access for external clients via the Portal UI
(`portal-ui/`) using share-link tokens with `scope=portal`.

## Why deferred

Same reason as `hr`: CRM already covers every framework primitive in
v1.0. Project would mostly demonstrate the Portal scope of RBAC, which
is already exercised by the share-link flow in `auth`.
