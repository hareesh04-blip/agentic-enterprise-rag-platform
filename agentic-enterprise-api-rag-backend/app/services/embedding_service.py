from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.ollama_client import ollama_client
from app.services.openai_client import openai_client


class EmbeddingService:
    async def embed_text(self, text: str) -> list[float]:
        provider = (settings.EMBEDDING_PROVIDER or "ollama").strip().lower()
        if provider == "openai":
            embedding = await openai_client.embed_text(text, model=settings.OPENAI_EMBEDDING_MODEL)
            if not isinstance(embedding, list):
                raise RuntimeError("OpenAI embedding response is missing a valid embedding list")
            return embedding

        if provider != "ollama":
            raise RuntimeError(f"Unsupported EMBEDDING_PROVIDER: {provider}")

        response = await ollama_client.embedding_test(text)
        embedding = response.get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Embedding response is missing a valid 'embedding' list")
        if len(embedding) != settings.EMBEDDING_DIM:
            raise RuntimeError(f"Embedding dimension mismatch: expected {settings.EMBEDDING_DIM}, got {len(embedding)}")
        return embedding

    async def embed_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        embedded_chunks: list[dict[str, Any]] = []
        for chunk in chunks:
            chunk_type = chunk.get("chunk_type", "unknown")
            metadata = chunk.get("metadata", {}) or {}
            api_reference_id = metadata.get("api_reference_id", "N/A")
            try:
                embedding = await self.embed_text(chunk.get("chunk_text", ""))
            except Exception as exc:
                raise RuntimeError(
                    f"Embedding generation failed for chunk_type={chunk_type}, "
                    f"api_reference_id={api_reference_id}: {exc}"
                ) from exc
            chunk_with_embedding = dict(chunk)
            chunk_with_embedding["embedding"] = embedding
            embedded_chunks.append(chunk_with_embedding)
        return embedded_chunks


embedding_service = EmbeddingService()
