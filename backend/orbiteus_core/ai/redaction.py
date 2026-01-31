"""PII redaction for prompts before remote provider calls."""
from __future__ import annotations

import re
from typing import Any

# Conservative defaults; modules can extend per ai.py declarations.
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b\+?\d[\d\s\-()]{7,}\d\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b")


def redact_text(text: str) -> str:
    text = EMAIL_RE.sub("[email]", text)
    text = PHONE_RE.sub("[phone]", text)
    text = IBAN_RE.sub("[iban]", text)
    return text


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {k: redact_payload(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [redact_payload(v) for v in payload]
    if isinstance(payload, str):
        return redact_text(payload)
    return payload
