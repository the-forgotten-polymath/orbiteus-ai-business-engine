"""TOTP recovery codes.

Generate a small set of one-time backup codes that bypass TOTP when the
authenticator app is unavailable. Codes are hashed at rest (bcrypt) and
single-use — verification revokes the matched code.

Public API:

    from orbiteus_core.security.recovery_codes import (
        generate_codes,         # returns (plain_codes, hashed_codes)
        verify_and_consume,     # bool — also returns updated hashed list
    )
"""
from __future__ import annotations

import logging
import secrets
import string

import bcrypt

logger = logging.getLogger(__name__)


CODE_COUNT = 10
CODE_LENGTH = 10  # 10 chars (alphabet 32) ≈ 50 bits entropy per code
ALPHABET = string.digits + "ABCDEFGHJKMNPQRSTUVWXYZ"  # no I, L, O — readability


def _new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def _hash_code(code: str) -> str:
    """Bcrypt-hash a recovery code; cost 10 is plenty for short tokens."""
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def generate_codes(count: int = CODE_COUNT) -> tuple[list[str], list[str]]:
    """Return (plain_codes, hashed_codes). The plain list is shown once."""
    plain = [_new_code() for _ in range(count)]
    hashed = [_hash_code(c) for c in plain]
    return plain, hashed


def verify_and_consume(code: str, hashed_codes: list[str]) -> tuple[bool, list[str]]:
    """If `code` matches any hashed entry, return (True, list-with-match-removed).

    Otherwise return (False, original list). Constant-time-friendly: compare
    against every hash even after a match (we don't early-return) to avoid
    leaking which slot was consumed.
    """
    if not code or not hashed_codes:
        return False, hashed_codes

    matched_index = -1
    for idx, h in enumerate(hashed_codes):
        try:
            if bcrypt.checkpw(code.encode("utf-8"), h.encode("utf-8")):
                if matched_index == -1:
                    matched_index = idx
        except (ValueError, TypeError):
            continue

    if matched_index == -1:
        return False, hashed_codes

    remaining = list(hashed_codes)
    remaining.pop(matched_index)
    return True, remaining


def normalize(code: str) -> str:
    """Strip whitespace, uppercase, remove dashes — what users actually type."""
    return code.replace("-", "").replace(" ", "").upper().strip()
