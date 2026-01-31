"""AIModuleConfig + AIRegistry — declarative AI surface per module.

A module declares its AI surface in `modules/<name>/ai.py`:

    AI = AIModuleConfig(
        enabled=True,
        system_prompt="You are an assistant for {{ tenant.name }}.",
        accessible_models=["crm.person", "crm.lead"],
        callable_actions=["crm.lead.create"],
        embed_models=["crm.lead"],
        suggested_prompts=[PromptTemplate(id="hot_leads", label="Hot leads")],
        dashboard=True,
    )

`AIRegistry` collects them at registry bootstrap, so the AI router can
build a tenant-scoped tool list when serving `/api/ai/chat`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    id: str
    label: str
    body: str = ""


@dataclass
class AIModuleConfig:
    enabled: bool = False
    system_prompt: str = ""
    accessible_models: list[str] = field(default_factory=list)
    callable_actions: list[str] = field(default_factory=list)
    embed_models: list[str] = field(default_factory=list)
    suggested_prompts: list[PromptTemplate] = field(default_factory=list)
    dashboard: bool = False


class AIRegistry:
    def __init__(self) -> None:
        self._configs: dict[str, AIModuleConfig] = {}

    def register(self, module_name: str, config: AIModuleConfig) -> None:
        self._configs[module_name] = config

    def get(self, module_name: str) -> AIModuleConfig | None:
        return self._configs.get(module_name)

    def all(self) -> dict[str, AIModuleConfig]:
        return dict(self._configs)

    def accessible_models(self) -> set[str]:
        out: set[str] = set()
        for cfg in self._configs.values():
            if cfg.enabled:
                out.update(cfg.accessible_models)
        return out

    def callable_actions(self) -> set[str]:
        out: set[str] = set()
        for cfg in self._configs.values():
            if cfg.enabled:
                out.update(cfg.callable_actions)
        return out

    def embed_models(self) -> set[str]:
        out: set[str] = set()
        for cfg in self._configs.values():
            if cfg.enabled:
                out.update(cfg.embed_models)
        return out


ai_registry = AIRegistry()
