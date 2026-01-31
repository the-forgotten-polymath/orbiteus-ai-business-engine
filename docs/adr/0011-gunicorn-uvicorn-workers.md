# ADR-0011: Gunicorn + UvicornWorker as production HTTP server

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, ops, performance

## Context

`uvicorn` alone is fine for development but lacks the process-management
features we want in production: prefork, restart-on-N-requests, graceful
reload, worker isolation.

## Decision

Production deploys run **Gunicorn** as the process manager with
**UvicornWorker** as the worker class:

```
gunicorn api:app \
  -w <2*CPU+1> \
  -k uvicorn.workers.UvicornWorker \
  --max-requests 10000 --max-requests-jitter 1000 \
  --timeout 60 --graceful-timeout 30 --keep-alive 30
```

## Consequences

- Battle-tested process management; familiar to every senior Python dev.
- Workers restart after N requests, mitigating slow leaks.
- Graceful reload on SIGTERM with bounded drain time.
- Slightly higher memory footprint than single-process uvicorn — acceptable.

## Alternatives considered

- Bare uvicorn in prod — rejected for ops reasons.
- Hypercorn (HTTP/2/3) — not needed; rejected.
- Granian (Rust) — newer, smaller community; revisit when measurably needed.

## References

- `docs/02-architecture.md`
- `docs/17-deployment.md`
