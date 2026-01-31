"""Compose file structure tests.

We can't run docker compose in unit tests, but we can assert that:
- both compose files parse as YAML
- required services are declared
- production compose wires the migrate/backend dependency correctly
- pgvector image is used (ADR-0005)

These guard against accidental regressions when editing compose files.
"""
from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")  # PyYAML; comes with backend deps


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV = REPO_ROOT / "docker-compose.yml"
PROD = REPO_ROOT / "docker-compose.prod.yml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_dev_compose_has_required_services():
    doc = _load(DEV)
    services = set(doc["services"])
    assert {"postgres", "redis", "backend", "frontend"} <= services


def test_dev_compose_uses_pgvector_image():
    doc = _load(DEV)
    assert doc["services"]["postgres"]["image"].startswith("pgvector/pgvector:")


def test_dev_backend_runs_with_uvicorn_reload():
    doc = _load(DEV)
    env = doc["services"]["backend"]["environment"]
    assert env.get("USE_GUNICORN") in ("0", 0, False, "false")
    assert env.get("UVICORN_RELOAD") == "1"


def test_prod_compose_has_required_services():
    doc = _load(PROD)
    services = set(doc["services"])
    must = {"postgres", "pgbouncer", "redis", "migrate", "backend", "frontend", "worker", "beat", "nginx"}
    missing = must - services
    assert not missing, f"prod compose missing services: {missing}"


def test_prod_compose_uses_pgvector_image():
    doc = _load(PROD)
    assert doc["services"]["postgres"]["image"].startswith("pgvector/pgvector:")


def test_prod_backend_depends_on_successful_migrate():
    doc = _load(PROD)
    deps = doc["services"]["backend"]["depends_on"]
    assert "migrate" in deps
    assert deps["migrate"]["condition"] == "service_completed_successfully"


def test_prod_backend_uses_gunicorn():
    doc = _load(PROD)
    env = doc["services"]["backend"]["environment"]
    assert env.get("USE_GUNICORN") == "1"


def test_prod_pgbouncer_in_transaction_mode():
    doc = _load(PROD)
    env = doc["services"]["pgbouncer"]["environment"]
    assert env["POOL_MODE"] == "transaction"


def test_prod_worker_and_beat_run_by_default():
    """Celery worker + beat are core in prod — no profile gating."""
    doc = _load(PROD)
    assert "profiles" not in doc["services"]["worker"]
    assert "profiles" not in doc["services"]["beat"]


def test_prod_worker_runs_celery_worker():
    doc = _load(PROD)
    entrypoint = doc["services"]["worker"]["entrypoint"]
    assert any("celery -A celery_app worker" in part for part in entrypoint)


def test_prod_beat_runs_celery_beat():
    doc = _load(PROD)
    entrypoint = doc["services"]["beat"]["entrypoint"]
    assert any("celery -A celery_app beat" in part for part in entrypoint)


def test_prod_nginx_is_profile_gated():
    doc = _load(PROD)
    assert doc["services"]["nginx"].get("profiles") == ["nginx"]
