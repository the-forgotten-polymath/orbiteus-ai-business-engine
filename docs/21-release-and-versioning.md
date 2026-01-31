# 21 — Release & Versioning

## Versioning scheme

Orbiteus follows **SemVer** (`MAJOR.MINOR.PATCH`).

| Change | Bump |
|---|---|
| Breaking change in framework public API | MAJOR |
| New framework feature, backward compatible | MINOR |
| Breaking change in canonical CRM | MINOR (with migration note) |
| Sample module changes (HR, project, social) | PATCH |
| Documentation only | PATCH |
| Bug fix | PATCH |

## Branches

- `main` — release-ready, protected. Merges only via PR with green CI.
- `feat/*`, `fix/*`, `chore/*`, `docs/*` — short-lived feature branches.
- `release/x.y` — prepared release branches, no new features.

## Commit messages

Conventional Commits:

- `feat(scope): summary` — new feature
- `fix(scope): summary` — bug fix
- `chore(scope): summary` — internal change
- `docs(scope): summary` — documentation
- `refactor(scope): summary` — no behavior change
- `test(scope): summary` — tests only
- `perf(scope): summary` — performance

`scope` is the module or area, e.g. `feat(crm): rename customer to person`.

## Pull request requirements

- Linked issue or ADR if architectural.
- All CI checks green (see `20-testing.md`).
- One reviewer minimum; two for framework-layer changes.
- Migration steps documented in PR description if schema changes.
- Updates to relevant `docs/` and tree-specs included in the same PR.

## Release process

1. Decide on version bump from changes since last tag.
2. Update `CHANGELOG.md` (Keep a Changelog format).
3. Bump versions in `backend/pyproject.toml` and `package.json`.
4. Cut a `release/x.y` branch if needed.
5. Tag `vX.Y.Z` after merging release notes.
6. CI builds Docker images and pushes to the registry.
7. Demo deployment auto-updates on `vX.Y.Z` tag (where configured).

## Migration policy

### Database

- Every migration must include a working `downgrade()`.
- Breaking column changes follow the expand → migrate → contract pattern:
  1. Add new column (nullable).
  2. Backfill in a Celery task.
  3. Switch reads/writes to new column (keep dual-write briefly).
  4. Drop old column in a later release.

### API

- New required parameters → MAJOR if no default; MINOR if default added.
- Removed fields → deprecated in MINOR (return `Deprecation:` header), removed
  in next MAJOR.

### UI

- Removed widget → MINOR with deprecation warning in console; removed in MAJOR.
- New required field → MINOR; PUT requests with the missing field accept
  the engine default.

## Deprecation timeline

- Announced: in CHANGELOG of the release that introduces the deprecation.
- Deprecation notice appears for at least 1 MINOR.
- Removal: in next MAJOR.

## Release notes template (CHANGELOG.md)

```
## [0.2.0] - 2026-MM-DD

### Added
- ...

### Changed
- ...

### Deprecated
- ...

### Removed
- ...

### Fixed
- ...

### Security
- ...

### Migration
- See migration guide: docs/migrations/0.1-to-0.2.md
```
