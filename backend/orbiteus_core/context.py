"""Request context – tenant, company, and user information per request.

Extended fields (PR 3 onward) used by audit and observability:
- `actor`: who is calling — `user`, `ai`, or `system`. Audit rows record this.
- `request_id`: correlates logs and audit; mirrors X-Request-Id header.
- `scope`: JWT scope — `internal`, `portal`, or `ai` (upper bound on access).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    """Carries authenticated request context through the system."""

    tenant_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    roles: list[str] = field(default_factory=list)
    is_superadmin: bool = False
    actor: str = "system"          # "user" | "ai" | "system"
    request_id: str | None = None
    scope: str = "internal"        # "internal" | "portal" | "ai"

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    def has_role(self, role: str) -> bool:
        return role in self.roles or self.is_superadmin
