"""Portal mutations — pure logic tests for permission gating.

Avoids DB by exercising `_require_permission` directly against scenarios.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
PORTAL = BACKEND / "orbiteus_core" / "portal_router.py"


def _load():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    # `tests/test_repository_diff.py` stubs `orbiteus_core.db` to short-circuit
    # SQLAlchemy. Drop the stub so portal_router resolves the real module.
    for cached in (
        "orbiteus_core.db",
        "orbiteus_core.portal_router",
        "orbiteus_portal_router_logic",
    ):
        sys.modules.pop(cached, None)

    spec = importlib.util.spec_from_file_location("orbiteus_portal_router_logic", PORTAL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orbiteus_portal_router_logic"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_require_permission_passes_when_present():
    mod = _load()
    # No exception → no return value.
    mod._require_permission(["read", "comment"], "comment")


def test_require_permission_raises_403_when_missing():
    mod = _load()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        mod._require_permission(["read"], "comment")
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "portal.permission_denied"
    assert exc.value.detail["required"] == "comment"


def test_require_permission_raises_for_attach_when_only_read():
    mod = _load()
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        mod._require_permission(["read", "comment"], "attach_file")


def test_router_exposes_comment_and_attachment_routes():
    mod = _load()
    paths = {r.path for r in mod.router.routes}
    assert "/api/portal/exchange" in paths
    assert "/api/portal/comment" in paths
    assert "/api/portal/attachment" in paths
