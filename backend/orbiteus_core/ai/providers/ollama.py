"""Ollama (local) adapter — no HTTP retries, simple JSON over httpx."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .base import ChatResult, Provider, ProviderError

logger = logging.getLogger(__name__)


class OllamaProvider(Provider):
    name = "ollama"
    default_chat_model = "llama3"
    default_embed_model = "nomic-embed-text"

    @staticmethod
    def _url(api_key_unused: str) -> str:
        return os.environ.get("OLLAMA_URL", "http://localhost:11434")

    async def ping(self, api_key: str) -> bool:
        url = self._url(api_key)
        async with httpx.AsyncClient(timeout=5.0) as http:
            try:
                r = await http.get(f"{url}/api/tags")
                return r.status_code == 200
            except Exception as exc:  # noqa: BLE001
                logger.warning("ollama.ping_failed", extra={"error": str(exc)[:200]})
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
        url = self._url(api_key)
        body = {
            "model": model or self.default_chat_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            body["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as http:
            r = await http.post(f"{url}/api/chat", json=body)
            r.raise_for_status()
            data = r.json()

        text = (data.get("message") or {}).get("content", "")
        tool_calls = []
        for tc in (data.get("message") or {}).get("tool_calls", []):
            tool_calls.append(
                {"id": tc.get("id", ""), "name": tc.get("function", {}).get("name", ""),
                 "arguments": tc.get("function", {}).get("arguments", {})}
            )
        return ChatResult(
            text=text,
            tool_calls=tool_calls,
            usage_tokens=data.get("eval_count", 0),
            finish_reason="stop",
            raw=data,
        )

    async def embed(
        self,
        api_key: str,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        url = self._url(api_key)
        out: list[list[float]] = []
        async with httpx.AsyncClient(timeout=60.0) as http:
            for text in texts:
                r = await http.post(
                    f"{url}/api/embeddings",
                    json={"model": model or self.default_embed_model, "prompt": text},
                )
                r.raise_for_status()
                out.append(r.json().get("embedding", []))
        return out
