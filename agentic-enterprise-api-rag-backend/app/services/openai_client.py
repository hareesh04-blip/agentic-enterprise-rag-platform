from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self) -> None:
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=10.0)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def embed_text(self, text: str, *, model: str | None = None) -> list[float]:
        used_model = model or settings.OPENAI_EMBEDDING_MODEL
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": used_model,
            "input": text,
        }
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=True) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        items = data.get("data") or []
        if not items or not isinstance(items, list):
            raise RuntimeError("Invalid OpenAI embeddings response: missing data[0]")
        embedding = items[0].get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Invalid OpenAI embeddings response: missing embedding list")
        return embedding

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        used_model = model or settings.OPENAI_LLM_MODEL
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": used_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=True) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        choices = data.get("choices") or []
        if not choices or not isinstance(choices, list):
            raise RuntimeError("Invalid OpenAI chat response: missing choices[0]")
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Invalid OpenAI chat response: missing message.content")
        return content.strip()

    async def generate_stream(self, prompt: str, *, model: str | None = None) -> AsyncIterator[str]:
        used_model = model or settings.OPENAI_LLM_MODEL
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": used_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=True) as client:
            async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk: dict[str, Any] = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0] or {}).get("delta") or {}
                    content = delta.get("content") or ""
                    if isinstance(content, str) and content:
                        yield content


openai_client = OpenAIClient()

