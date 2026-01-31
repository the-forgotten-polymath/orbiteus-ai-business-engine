"""OpenAI adapter."""
from __future__ import annotations

import logging
from typing import Any

from .base import ChatResult, Provider, ProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    name = "openai"
    default_chat_model = "gpt-4o-mini"
    default_embed_model = "text-embedding-3-small"

    async def ping(self, api_key: str) -> bool:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderError("openai SDK not installed") from exc
        client = AsyncOpenAI(api_key=api_key)
        try:
            await client.chat.completions.create(
                model=self.default_chat_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("openai.ping_failed", extra={"error": str(exc)[:200]})
            return False

    async def chat(
        self,
        api_key: str,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ChatResult:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderError("openai SDK not installed") from exc

        client = AsyncOpenAI(api_key=api_key)
        kwargs: dict[str, Any] = {
            "model": model or self.default_chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls: list[dict[str, Any]] = []
        for tc in (msg.tool_calls or []):
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            )
        usage = getattr(resp, "usage", None)
        usage_tokens = (getattr(usage, "total_tokens", 0) if usage else 0)
        return ChatResult(
            text=msg.content or "",
            tool_calls=tool_calls,
            usage_tokens=usage_tokens,
            finish_reason=choice.finish_reason or "stop",
            raw={"id": resp.id, "model": resp.model},
        )

    async def embed(
        self,
        api_key: str,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderError("openai SDK not installed") from exc

        client = AsyncOpenAI(api_key=api_key)
        resp = await client.embeddings.create(
            model=model or self.default_embed_model,
            input=texts,
        )
        return [d.embedding for d in resp.data]
