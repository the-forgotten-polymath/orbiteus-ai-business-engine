"""Action dataclass — the unit of business logic for the Command Palette."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionCategory(str, Enum):
    NAVIGATE = "navigate"   # open a view / page
    CREATE   = "create"     # open a creation form
    REPORT   = "report"     # open a report / analytics view
    EXECUTE  = "execute"    # call API directly, no form (e.g. send email)
    SEARCH   = "search"     # open a view with a pre-set filter


@dataclass
class Action:
    """Declarative description of a single business action.

    Registered by each module's actions.py via ActionRegistry.
    Resolved by ActionResolver (RapidFuzz, no LLM in happy path).
    Executed by:
      - the frontend (Command Palette path): `router.push(target_url)`
        or an API call shaped from `target_url`,
      - the AI dispatcher (tool-call path): a Python handler
        registered through `orbiteus_core.ai.dispatcher.register_handler`.
        See `docs/15-ai-layer.md` "Tool execution" for the contract.
    """
    id: str                          # unique: "crm.customer.create"
    label: str                       # displayed in Command Palette
    keywords: list[str] = field(default_factory=list)   # extra search terms
    description: str = ""
    category: ActionCategory = ActionCategory.NAVIGATE
    target: str = "navigate"         # "navigate" | "modal" | "execute" | "api"
    target_url: str = ""             # path for navigate / modal
    requires_feature: str = ""       # RBAC feature flag (empty = always visible)
    icon: str = ""                   # tabler icon name e.g. "user-plus"
    module: str = ""                 # set automatically by ActionRegistry
    # JSON-schema-style description of the arguments the AI must
    # provide when invoking this action as a tool. Empty dict =>
    # "no arguments" (we still emit an empty `parameters` object so
    # provider-side function calling has a stable shape).
    parameters_schema: dict[str, Any] = field(default_factory=dict)
