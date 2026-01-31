# Admin UI — spec

> **Superseded by `docs/`.** Authoritative documentation lives in the
> top-level `docs/` chapters. This file is kept next to the source for
> in-tree readability.
>
> **Canonical sources:**
> - `docs/08-admin-ui.md` — design + dynamic renderer
> - `docs/24-tree-spec-admin-ui.md` — implementation tree-spec
> - `docs/10-design-system.md` — Mantine 9 + `src/orbiteus-ui/`
> - `docs/adr/0017-httponly-cookie-session.md` — auth transport

> **Status:** IMPLEMENTED at v1.0
> **Stack:** Next.js 16 (App Router) + React 19 + Mantine 9 + axios 1
> **Edge auth gate:** `admin-ui/src/proxy.ts` (Next 16 successor of
> `middleware.ts`)

## Purpose

Generic, white-label admin UI for the engine. Branding (name, logo,
favicon) comes from `GET /api/base/branding`. Every backend module
automatically gets list / form / kanban / calendar screens through the
dynamic catch-all routes (`[module]/[model]`) that read
`GET /api/base/ui-config` — adding a module never requires writing new
TSX files.

## Repository layout (current)

```
admin-ui/src/
├── proxy.ts                       # Next 16 Edge gate (httpOnly cookie)
├── orbiteus-ui/                   # Cross-cutting widgets + AI surfaces
│   ├── ai/
│   └── widgets/
├── app/
│   ├── api/
│   │   └── [[...path]]/route.ts   # Server proxy → FastAPI (forwards Set-Cookie)
│   ├── layout.tsx                 # MantineProvider + BrandingProvider
│   ├── page.tsx                   # Dashboard (PromptInput + AIDashboard)
│   ├── login/page.tsx             # Welcome + login form (cookie-based)
│   └── [module]/[model]/          # Dynamic list / form / kanban
├── components/
│   ├── AppShellLayout.tsx         # Sidebar + Header (Mantine AppShell)
│   ├── ResourceList.tsx           # Generic list view (auto-CRUD)
│   ├── ResourceForm.tsx           # Generic create / edit form
│   ├── ResourceKanban.tsx         # Generic kanban (dnd-kit)
│   ├── ResourceCalendar.tsx       # Generic calendar
│   ├── CommandPalette.tsx         # Cmd+K (uses /api/ai/actions)
│   └── PageBreadcrumbs.tsx
└── lib/
    ├── api.ts                     # axios with `withCredentials: true`
    └── branding.tsx               # BrandingContext + useBranding()
```

The `crm/` / `base/` / `technical/` *static* page directories that the
old version of this spec listed have been removed (PR 12); everything
flows through the dynamic catch-all routes now.

## Routing convention

```
/                                  → dashboard
/login                             → welcome + login (public)
/{module}/{model}                  → list  (e.g. /crm/lead)
/{module}/{model}/new              → create form
/{module}/{model}/{id}             → view / edit form
/{module}/{model}/kanban           → kanban view (when arch is declared)
/{module}/{model}/calendar         → calendar view (when arch is declared)
```

## Auth flow (browser)

1. The Edge proxy (`proxy.ts`) reads the `orbiteus_token` cookie. No
   cookie → 307 redirect to `/login?next=<path>` *before* SSR runs (no
   Flash Of Authenticated Content).
2. `POST /api/auth/login` returns the JWT pair in the body **and** sets
   `orbiteus_token` (`Path=/`, 15 min) plus `orbiteus_refresh`
   (`Path=/api/auth`, 7 days) as `HttpOnly`, `SameSite=Lax`. `Secure`
   flips on automatically in production.
3. axios is configured with `withCredentials: true`; the browser sends
   the cookie on every same-origin `/api/*` call. There is no Bearer
   header injected from `localStorage` — the previous transport.
4. `POST /api/auth/logout` revokes the JTI in Redis and clears both
   cookies.

See `docs/06-auth.md` and ADR-0017 for the full rationale.

## Branding

```
GET /api/base/branding → { name, logo_url, favicon_url }
        ↓
BrandingContext (React Context)
        ↓
useBranding() hook
        ↓
AppShellLayout (header)  /  Login page (title)  /  metadata title

Fallback: NEXT_PUBLIC_APP_NAME from .env.local
```

## Design system

- **Framework:** Mantine 9
- **Theme:** dark by default (Mantine `dark` palette); user-toggleable
  light mode persists in `localStorage` (UI preference, not auth).
- **Primary color:** monochrome (black / white).
- **Icons:** `@tabler/icons-react`
- **Font:** Inter
- **Charts:** Recharts 3 (rendered through `<AIDashboard>`)

### Mantine dark palette tokens (current theme)

```
dark-9: #101113   main background
dark-8: #141517   sidebar, header
dark-7: #1A1B1E   table background
dark-6: #25262b   borders
dark-5: #2C2E33   input borders
gray-2: #C1C2C5   primary text
gray-4: #909296   secondary / dimmed text
```

## Status

100% Definition of Done at v1.0. Open follow-ups (post-v1.0):

| Feature                                         | Priority |
|-------------------------------------------------|----------|
| Field-level RBAC in form components             | High     |
| Multi-company switcher in header                | Medium   |
| Calendar drag-to-reschedule                     | Medium   |
| AI streaming (`/api/ai/chat` SSE)               | Medium   |
| Light-mode toggle in header                     | Low      |
