from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaRequestError(RuntimeError):
    def __init__(self, operation: str, url: str, attempts: int, elapsed_ms: int, original_error: Exception) -> None:
        self.operation = operation
        self.url = url
        self.attempts = attempts
        self.elapsed_ms = elapsed_ms
        self.original_error = original_error
        super().__init__(
            f"{operation}_retry_failed after {attempts} attempts in {elapsed_ms}ms for {url}: {original_error}"
        )


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.llm_model = settings.OLLAMA_LLM_MODEL
        self.embedding_model = settings.OLLAMA_EMBEDDING_MODEL
        self.timeout = httpx.Timeout(
            connect=settings.OLLAMA_TIMEOUT_CONNECT_SECONDS,
            read=settings.OLLAMA_TIMEOUT_READ_SECONDS,
            write=settings.OLLAMA_TIMEOUT_WRITE_SECONDS,
            pool=settings.OLLAMA_TIMEOUT_POOL_SECONDS,
        )
        self.retry_count = max(settings.OLLAMA_RETRY_COUNT, 0)
        self.retry_delay_seconds = max(settings.OLLAMA_RETRY_DELAY_SECONDS, 0.0)

    async def _get(self, url: str) -> dict[str, Any]:
        return await self._request_with_retry("GET", url)

    async def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_with_retry("POST", url, payload=payload)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attempts = self.retry_count + 1
        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            attempt_started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    if method == "GET":
                        response = await client.get(url)
                    else:
                        response = await client.post(url, json=payload)
                    response.raise_for_status()
                    elapsed_ms = int((time.perf_counter() - attempt_started) * 1000)
                    logger.info(
                        "ollama_%s_success url=%s attempt=%s/%s elapsed_ms=%s",
                        method.lower(),
                        url,
                        attempt,
                        attempts,
                        elapsed_ms,
                    )
                    return response.json()
            except Exception as exc:
                last_error = exc
                elapsed_ms = int((time.perf_counter() - attempt_started) * 1000)
                logger.warning(
                    "ollama_%s_failure url=%s attempt=%s/%s elapsed_ms=%s error_class=%s error=%s",
                    method.lower(),
                    url,
                    attempt,
                    attempts,
                    elapsed_ms,
                    exc.__class__.__name__,
                    exc,
                )
                if attempt < attempts:
                    backoff = self.retry_delay_seconds * attempt
                    await asyncio.sleep(backoff)
        total_elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "ollama_%s_retry_failed url=%s attempts=%s elapsed_ms=%s last_error_class=%s last_error=%s",
            method.lower(),
            url,
            attempts,
            total_elapsed_ms,
            (last_error.__class__.__name__ if last_error else "unknown"),
            (last_error if last_error else "unknown"),
        )
        raise OllamaRequestError(
            operation=f"ollama_{method.lower()}",
            url=url,
            attempts=attempts,
            elapsed_ms=total_elapsed_ms,
            original_error=last_error or RuntimeError("unknown ollama failure"),
        )

    async def health_check(self) -> dict[str, Any]:
        root_url = f"{self.base_url}/"
        tags_url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                root_response = await client.get(root_url)
                root_response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f"Failed GET {root_url}: {exc}") from exc

        tags_data = await self._get(tags_url)
        model_entries = tags_data.get("models", [])
        model_names = [model.get("name") for model in model_entries if model.get("name")]
        return {
            "status": "healthy",
            "base_url": self.base_url,
            "root_status": root_response.status_code,
            "root_response": root_response.text[:200],
            "models": model_names,
        }

    async def generate_test(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": settings.OLLAMA_LLM_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        generate_url = f"{self.base_url}/api/generate"
        return await self._post(generate_url, payload)

    async def embedding_test(self, text: str) -> dict[str, Any]:
        payload = {
            "model": settings.OLLAMA_EMBEDDING_MODEL,
            "prompt": text,
        }
        embedding_url = f"{self.base_url}/api/embeddings"
        data = await self._post(embedding_url, payload)
        if "embedding" not in data:
            raise RuntimeError(f"Invalid embedding response from {embedding_url}: missing 'embedding'")
        return data


ollama_client = OllamaClient()
