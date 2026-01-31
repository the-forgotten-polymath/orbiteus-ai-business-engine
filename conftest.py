"""Repo-root pytest configuration.

Restricts collection to the docs tests so that running `pytest` from the repo
root does not require backend dependencies (Postgres, app imports). Backend
tests live under `backend/tests/` with their own `conftest.py` and database.
"""
from __future__ import annotations

collect_ignore_glob = ["backend/*", "admin-ui/*"]
