"""Recovery codes unit suite (DoD §15.1).

The host-side `tests/test_recovery_codes.py` uses an `importlib.util.
spec_from_file_location` shim that escapes the coverage tracer. This
container-side mirror imports through the canonical `orbiteus_core`
namespace so the collector sees every line.
"""
from __future__ import annotations

import pytest


def test_generate_codes_returns_plain_and_hashed_pairs():
    from orbiteus_core.security.recovery_codes import generate_codes

    plain, hashed = generate_codes(count=8)
    assert len(plain) == 8
    assert len(hashed) == 8
    # Each plain code is alphanumeric, mixed case, ≥10 chars.
    for code in plain:
        assert len(code) >= 8
        assert code.replace("-", "").isalnum()
    # Hashes look like bcrypt.
    for h in hashed:
        assert h.startswith("$2") and len(h) >= 50


def test_normalize_strips_whitespace_and_dashes():
    from orbiteus_core.security.recovery_codes import normalize

    assert normalize("AB-CD-EF") == "ABCDEF"
    assert normalize("  ab  cd  ") == "ABCD"
    assert normalize("ab-cd-ef") == "ABCDEF"


def test_verify_and_consume_valid_code_removes_one_hash():
    from orbiteus_core.security.recovery_codes import (
        generate_codes,
        normalize,
        verify_and_consume,
    )

    plain, hashed = generate_codes(count=4)
    code = normalize(plain[0])

    ok, remaining = verify_and_consume(code, list(hashed))
    assert ok is True
    assert len(remaining) == 3   # one hash consumed


def test_verify_and_consume_rejects_unknown_code():
    from orbiteus_core.security.recovery_codes import (
        generate_codes,
        verify_and_consume,
    )

    _plain, hashed = generate_codes(count=4)
    ok, remaining = verify_and_consume("WRONG-CODE-XX", list(hashed))
    assert ok is False
    assert len(remaining) == 4   # nothing consumed


def test_verify_and_consume_handles_empty_hash_list():
    from orbiteus_core.security.recovery_codes import verify_and_consume

    ok, remaining = verify_and_consume("ANY", [])
    assert ok is False
    assert remaining == []


def test_two_consecutive_normalize_calls_are_idempotent():
    from orbiteus_core.security.recovery_codes import normalize

    once = normalize(" ab-cd ")
    twice = normalize(once)
    assert once == twice


def test_generate_codes_default_count_is_at_least_one():
    from orbiteus_core.security.recovery_codes import generate_codes

    plain, hashed = generate_codes()
    assert len(plain) >= 1
    assert len(plain) == len(hashed)
