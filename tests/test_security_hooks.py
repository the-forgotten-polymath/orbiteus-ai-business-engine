"""Static checks for the security hardening hooks (docs/18-security.md)."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pre_commit_config_exists_and_lists_detect_secrets():
    cfg = (REPO_ROOT / ".pre-commit-config.yaml").read_text()
    assert "detect-secrets" in cfg
    assert ".secrets.baseline" in cfg


def test_pre_commit_excludes_known_noise():
    """The exclude regex must list the canonical noisy paths (escaped dots OK)."""
    cfg = (REPO_ROOT / ".pre-commit-config.yaml").read_text()
    # Collapse backslashes so we can check pretty paths regardless of regex escaping.
    flat = cfg.replace("\\.", ".")
    for path in (
        "node_modules",
        "package-lock.json",
        "backend/.venv",
        "backend/migrations/versions",
    ):
        assert path in flat, f"pre-commit exclude missing: {path}"


def test_secrets_baseline_is_valid_json():
    baseline = json.loads((REPO_ROOT / ".secrets.baseline").read_text())
    assert baseline["version"].startswith("1.")
    assert "plugins_used" in baseline
    assert isinstance(baseline["results"], dict)


def test_secrets_baseline_includes_jwt_detector():
    baseline = json.loads((REPO_ROOT / ".secrets.baseline").read_text())
    plugin_names = {p["name"] for p in baseline["plugins_used"]}
    for must_have in ("JwtTokenDetector", "PrivateKeyDetector", "OpenAIDetector"):
        assert must_have in plugin_names, f"missing detector: {must_have}"


def test_github_actions_secrets_workflow_present():
    wf = (REPO_ROOT / ".github" / "workflows" / "secrets.yml").read_text()
    assert "detect-secrets" in wf
    assert ".secrets.baseline" in wf
    assert "actions/checkout@v4" in wf
