# `hr` module — spec (planned)

> **Status: PLANNED.** Not part of the v1.0 engine release. The CRM
> module (`backend/modules/crm/`) is the only canonical product example
> shipped at v1.0; HR is reserved as a teaching example for future
> waves.
>
> **Canonical sources for the engine surface this module would use:**
> - `docs/03-modules.md` — module convention (manifest / model / controller / view)
> - `docs/04-data-model.md` — `BaseModel`
> - `docs/15-ai-layer.md` — `ai.py` registration

## Intent (when implemented)

Employee lifecycle (Employee, Department, JobTitle, TimeOff). Distinction
between `User` (login identity, in `base`) and `Employee` (HR record).

`Employee.user_id` is a nullable FK to `User` so external workers can be
tracked without consuming a login seat.

## Why deferred

CRM already exercises every framework primitive end-to-end. Adding HR at
v1.0 would only repeat the pattern without exercising new engine
surface area. HR is a strong candidate for the first community-driven
module after v1.0.
