"""Dockerfile.prod sanity checks (ADR-0011)."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DOCKERFILE_PROD = REPO_ROOT / "backend" / "Dockerfile.prod"
ENTRYPOINT = REPO_ROOT / "backend" / "entrypoint.sh"
ENTRYPOINT_MIGRATE = REPO_ROOT / "backend" / "entrypoint-migrate.sh"
PYPROJECT = REPO_ROOT / "backend" / "pyproject.toml"


def test_dockerfile_prod_uses_latest_stable_python():
    """We pin to python:3.13-slim — latest stable as of 2026-05."""
    assert "python:3.13-slim" in BACKEND_DOCKERFILE_PROD.read_text()


def test_dockerfile_prod_exposes_8000():
    assert "EXPOSE 8000" in BACKEND_DOCKERFILE_PROD.read_text()


def test_entrypoint_runs_gunicorn_with_uvicorn_worker():
    text = ENTRYPOINT.read_text()
    assert "gunicorn" in text
    assert "uvicorn.workers.UvicornWorker" in text
    assert "GUNICORN_WORKERS" in text


def test_entrypoint_skips_migrations_by_default_in_prod():
    """RUN_MIGRATIONS is opt-in (dev sets it to 1); prod uses the migrate service."""
    text = ENTRYPOINT.read_text()
    assert 'RUN_MIGRATIONS:-0' in text


def test_migrate_entrypoint_runs_alembic_upgrade_head():
    text = ENTRYPOINT_MIGRATE.read_text()
    assert "alembic upgrade head" in text


def test_pyproject_pins_gunicorn_redis_prometheus():
    text = PYPROJECT.read_text()
    for needle in ("gunicorn>=", "redis>=", "prometheus-client>="):
        assert needle in text, f"backend deps missing: {needle}"
