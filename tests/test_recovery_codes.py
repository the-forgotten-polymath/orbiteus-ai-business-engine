"""TOTP recovery codes — pure logic tests, no DB."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


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
def rc():
    return _load(
        "orbiteus_recovery_codes",
        BACKEND / "orbiteus_core" / "security" / "recovery_codes.py",
    )


def test_generate_default_count(rc):
    plain, hashed = rc.generate_codes()
    assert len(plain) == rc.CODE_COUNT
    assert len(hashed) == rc.CODE_COUNT
    assert all(len(c) == rc.CODE_LENGTH for c in plain)
    assert len(set(plain)) == len(plain)  # unique


def test_generate_custom_count(rc):
    plain, hashed = rc.generate_codes(count=3)
    assert len(plain) == 3 and len(hashed) == 3


def test_codes_use_unambiguous_alphabet(rc):
    plain, _ = rc.generate_codes(count=5)
    forbidden = set("ILO")
    for code in plain:
        assert not (set(code) & forbidden)


def test_verify_consumes_match_only(rc):
    plain, hashed = rc.generate_codes(count=4)
    target = plain[2]
    ok, remaining = rc.verify_and_consume(target, hashed)
    assert ok is True
    assert len(remaining) == 3
    # Re-using the same code must fail.
    ok2, remaining2 = rc.verify_and_consume(target, remaining)
    assert ok2 is False
    assert remaining == remaining2


def test_verify_rejects_wrong_code(rc):
    plain, hashed = rc.generate_codes(count=2)
    ok, remaining = rc.verify_and_consume("WRONGCODE0", hashed)
    assert ok is False
    assert remaining == hashed


def test_verify_rejects_empty(rc):
    plain, hashed = rc.generate_codes(count=2)
    ok, _ = rc.verify_and_consume("", hashed)
    assert ok is False


def test_normalize_strips_dashes_and_spaces(rc):
    assert rc.normalize("abcd-1234 5") == "ABCD12345"
    assert rc.normalize("  XYZ ") == "XYZ"


def test_hashes_are_unique_per_code(rc):
    plain, hashed = rc.generate_codes(count=4)
    assert len(set(hashed)) == 4
    # Even when the same plaintext is hashed twice, hashes differ (different salts).
    other_hashed = [rc._hash_code(c) for c in plain]
    assert hashed != other_hashed
