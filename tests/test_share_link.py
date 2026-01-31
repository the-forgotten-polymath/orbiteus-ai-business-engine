"""Share-link token tests (PR 12) — pure JWT, no DB."""
from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
SHARING = BACKEND / "orbiteus_core" / "sharing.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sharing():
    return _load("orbiteus_sharing", SHARING)


def test_issue_and_decode_roundtrip(sharing):
    tenant = uuid.uuid4()
    issuer = uuid.uuid4()
    rid = uuid.uuid4()
    token = sharing.issue(
        resource_model="crm.lead",
        resource_id=rid,
        tenant_id=tenant,
        issued_by=issuer,
        permissions=["read", "comment"],
        ttl_days=3,
    )
    decoded = sharing.decode(token)
    assert decoded.resource_model == "crm.lead"
    assert decoded.resource_id == rid
    assert decoded.tenant_id == tenant
    assert decoded.issued_by == issuer
    assert sorted(decoded.permissions) == ["comment", "read"]


def test_issue_rejects_bad_permission(sharing):
    with pytest.raises(ValueError):
        sharing.issue(
            resource_model="crm.lead",
            resource_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            issued_by=uuid.uuid4(),
            permissions=["delete"],
        )


def test_issue_rejects_bad_ttl(sharing):
    with pytest.raises(ValueError):
        sharing.issue(
            resource_model="crm.lead",
            resource_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            issued_by=uuid.uuid4(),
            ttl_days=0,
        )
    with pytest.raises(ValueError):
        sharing.issue(
            resource_model="crm.lead",
            resource_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            issued_by=uuid.uuid4(),
            ttl_days=180,
        )


def test_decode_rejects_garbage(sharing):
    with pytest.raises(ValueError):
        sharing.decode("not-a-jwt")


def test_decode_rejects_admin_scope_token(sharing):
    """Tokens not minted via `issue()` (different `type`/`scope`) are refused."""
    from jose import jwt

    from orbiteus_core.config import settings

    bad = jwt.encode({"type": "access", "scope": "internal"}, settings.secret_key,
                     algorithm=settings.algorithm)
    with pytest.raises(ValueError):
        sharing.decode(bad)
