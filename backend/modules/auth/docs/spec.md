# `auth` module — spec

> **Superseded by `docs/`.** Authoritative documentation lives in the
> top-level chapters. Pointers below.
>
> **Canonical sources:**
> - `docs/06-auth.md` — tokens, endpoints, session model
> - `docs/adr/0017-httponly-cookie-session.md` — Admin UI session
> - `docs/30-rate-limiting.md` — per-endpoint rate budgets

## Purpose

User-facing authentication: login, refresh, logout, password reset, TOTP
2FA with recovery codes, and portal share-link exchange.

## Endpoints

| Method | Path                              | Notes                                     |
|--------|-----------------------------------|-------------------------------------------|
| POST   | `/api/auth/login`                 | Email + password → JWT pair + cookies     |
| POST   | `/api/auth/select-company`        | Multi-company users pick the active one   |
| POST   | `/api/auth/refresh`               | Body or `orbiteus_refresh` cookie         |
| POST   | `/api/auth/logout`                | Revokes JTI in Redis, clears cookies      |
| GET    | `/api/auth/me`                    | Current user profile                      |
| POST   | `/api/auth/register`              | Public registration (when enabled)        |
| POST   | `/api/auth/2fa/enroll`            | TOTP secret + provisioning URI            |
| POST   | `/api/auth/2fa/verify`            | One-time code; promotes session           |
| POST   | `/api/auth/2fa/recovery-codes`    | Regenerate one-time recovery codes        |

## Session model (browser)

Two httpOnly cookies are written on login:

| Cookie               | Path           | TTL                  |
|----------------------|----------------|----------------------|
| `orbiteus_token`     | `/`            | 15 min (access)      |
| `orbiteus_refresh`   | `/api/auth`    | 7 days (refresh)     |

`SameSite=Lax` always; `Secure` flips on automatically when
`settings.environment == "production"`. Non-browser clients keep using
`Authorization: Bearer …` — the body of `/api/auth/login` still ships
both tokens.

The Admin UI Edge proxy (`admin-ui/src/proxy.ts`, Next 16 successor of
`middleware.ts`) gates every protected route: missing cookie → 307 to
`/login?next=<path>`. This eliminates the Flash Of Authenticated Content
the previous client-only gate produced (ADR-0017).

## TOTP 2FA + recovery codes

- Secrets are stored in `users.totp_secret` (encrypted at rest).
- 10 single-use recovery codes are bcrypt-hashed and stored in
  `users.recovery_codes_hashed`.
- Login accepts either a TOTP code or a recovery code; consumed codes
  are removed from the list.
