"""Static checks on the Playwright E2E setup (no browser launched here)."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADMIN_UI = REPO_ROOT / "admin-ui"
SPEC = ADMIN_UI / "e2e" / "critical-path.spec.ts"
CONFIG = ADMIN_UI / "playwright.config.ts"


def test_playwright_config_exists():
    assert CONFIG.exists()


def test_critical_path_spec_exists():
    assert SPEC.exists()


def test_spec_covers_five_scenarios():
    """docs/35 §15 mandates ≥ 5 Playwright scenarios on the critical path."""
    text = SPEC.read_text()
    # `test(` calls per spec — exclude `test.describe`.
    occurrences = text.count("\n  test(")
    assert occurrences >= 5, f"expected ≥ 5 e2e scenarios, found {occurrences}"


def test_spec_covers_required_paths():
    text = SPEC.read_text()
    for needle in ("/login", "/crm/person/new", "/crm/lead?view=kanban", "/api/health/live"):
        assert needle in text, f"e2e missing coverage for {needle}"


def test_admin_ui_has_e2e_script():
    text = (ADMIN_UI / "package.json").read_text()
    assert '"e2e"' in text and "playwright test" in text


def test_playwright_dependency_pinned():
    text = (ADMIN_UI / "package.json").read_text()
    assert "@playwright/test" in text
