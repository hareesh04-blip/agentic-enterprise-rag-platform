from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.services.embedding_text_prepare import (
    average_normalized_vectors,
    prepare_embedding_text_segments,
)
from app.services.ollama_client import ollama_client
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)


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

            segments, prep_meta = prepare_embedding_text_segments(chunk)
            prepared_vectors: list[list[float]] = []
            part_errors: list[str] = []

            for si, segment in enumerate(segments):
                try:
                    vec = await self.embed_text(segment)
                    prepared_vectors.append(vec)
                    logger.debug(
                        "embedding_ok chunk_type=%s api_reference_id=%s part=%s/%s chars=%s",
                        chunk_type,
                        api_reference_id,
                        si + 1,
                        len(segments),
                        len(segment),
                    )
                except Exception as exc:
                    msg = str(exc)
                    part_errors.append(msg)
                    logger.warning(
                        "embedding_part_failed chunk_type=%s api_reference_id=%s part=%s/%s chars=%s err=%s",
                        chunk_type,
                        api_reference_id,
                        si + 1,
                        len(segments),
                        len(segment),
                        msg[:300],
                    )

            chunk_with_embedding = dict(chunk)
            if prepared_vectors:
                if len(prepared_vectors) == 1:
                    chunk_with_embedding["embedding"] = prepared_vectors[0]
                else:
                    chunk_with_embedding["embedding"] = average_normalized_vectors(prepared_vectors)
                chunk_with_embedding["_embedding_segments"] = len(prepared_vectors)
                chunk_with_embedding["_embedding_prep_meta"] = prep_meta
            else:
                chunk_with_embedding["embedding"] = None
                chunk_with_embedding["_embedding_error"] = "; ".join(part_errors) if part_errors else "embedding_failed"
                logger.warning(
                    "embedding_chunk_failed chunk_type=%s api_reference_id=%s original_chars=%s segments_tried=%s err=%s",
                    chunk_type,
                    api_reference_id,
                    prep_meta.get("original_chars"),
                    len(segments),
                    ("; ".join(part_errors))[:400],
                )

            embedded_chunks.append(chunk_with_embedding)
        return embedded_chunks


embedding_service = EmbeddingService()
