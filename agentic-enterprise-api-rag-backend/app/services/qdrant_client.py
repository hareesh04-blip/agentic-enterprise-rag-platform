from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointIdsList, PointStruct, VectorParams

from app.core.config import settings
from app.services.vector_dimension_resolver import get_active_vector_size

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self) -> None:
        self.url = settings.QDRANT_URL
        self.client = QdrantClient(url=self.url, timeout=30)

    def _active_collection_name(self) -> str:
        """Return collection name based on current embedding provider."""
        provider = (getattr(settings, "EMBEDDING_PROVIDER", "ollama") or "ollama").strip().lower()
        if provider == "openai":
            return getattr(settings, "QDRANT_COLLECTION_OPENAI", "enterprise_api_docs_openai")
        return settings.QDRANT_COLLECTION

    def _expected_vector_size(self) -> int:
        """Expected vector dimension for the current embedding provider."""
        return get_active_vector_size()

    def _ensure_collection_with_correct_dim(self) -> None:
        """
        Ensure the active collection exists with the expected vector size.

        For OpenAI provider, if the collection exists but has a mismatched size,
        delete only the OpenAI collection and recreate it with the correct size.
        """
        collection_name = self._active_collection_name()
        provider = (getattr(settings, "EMBEDDING_PROVIDER", "ollama") or "ollama").strip().lower()
        expected_size = self._expected_vector_size()

        collections = self.client.get_collections().collections
        existing = next((c for c in collections if c.name == collection_name), None)
        if existing is None:
            # Create new collection with provider-specific size
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=expected_size,
                    distance=Distance.COSINE,
                ),
            )
            return

        # If collection exists, check size; only adjust automatically for OpenAI collection.
        info = self.client.get_collection(collection_name=collection_name)
        vectors = info.config.params.vectors
        configured_size: int | None = None
        if vectors is not None:
            if isinstance(vectors, dict):
                first = next(iter(vectors.values()), None)
                configured_size = int(getattr(first, "size", 0) or 0) if first is not None else None
            else:
                configured_size = int(getattr(vectors, "size", 0) or 0)

        if configured_size and configured_size != expected_size and provider == "openai":
            logger.warning(
                "qdrant_collection_dim_mismatch provider=%s collection=%s configured=%s expected=%s; "
                "recreating provider-specific collection only",
                provider,
                collection_name,
                configured_size,
                expected_size,
            )
            # Delete and recreate only the OpenAI-specific collection
            self.client.delete_collection(collection_name=collection_name)
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=expected_size,
                    distance=Distance.COSINE,
                ),
            )

    def health_check(self) -> bool:
        self.client.get_collections()
        return True

    def collection_exists(self) -> bool:
        collection_name = self._active_collection_name()
        collections = self.client.get_collections().collections
        return any(collection.name == collection_name for collection in collections)

    def create_collection_if_not_exists(self) -> None:
        # For provider-specific logic, always ensure collection exists with correct dim.
        self._ensure_collection_with_correct_dim()

    def upsert_chunks(self, chunks_with_embeddings: list[dict[str, Any]]) -> list[str | None]:
        """
        Upsert vectors for chunks that have a non-empty embedding list.

        Returns a list aligned with the input: UUID string for upserted points, None where skipped.
        """
        self.create_collection_if_not_exists()
        collection_name = self._active_collection_name()
        points: list[PointStruct] = []
        aligned_ids: list[str | None] = []

        for chunk in chunks_with_embeddings:
            embedding = chunk.get("embedding")
            if embedding is None or not isinstance(embedding, list) or len(embedding) == 0:
                aligned_ids.append(None)
                logger.warning(
                    "qdrant_skip_chunk_no_embedding chunk_type=%s",
                    chunk.get("chunk_type"),
                )
                continue

            point_id = str(uuid.uuid4())
            metadata = chunk.get("metadata") or {}
            payload = {
                "chunk_type": chunk.get("chunk_type"),
                "chunk_text": chunk.get("chunk_text"),
                "metadata": metadata,
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )
            aligned_ids.append(point_id)

        if points:
            self.client.upsert(collection_name=collection_name, points=points)
        return aligned_ids

    def delete_points(self, point_ids: list[str]) -> None:
        """Remove vectors by point id (does not delete DB chunk rows)."""
        if not point_ids:
            return
        collection_name = self._active_collection_name()
        if not self.collection_exists():
            return
        self.client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=point_ids),
        )

    def collection_point_count(self) -> int:
        collection_name = self._active_collection_name()
        if not self.collection_exists():
            return 0
        count_result = self.client.count(collection_name=collection_name, exact=True)
        return int(count_result.count)

    def get_configured_vector_size(self) -> int | None:
        """Return embedding vector size configured on the collection, if it exists."""
        if not self.collection_exists():
            return None
        collection_name = self._active_collection_name()
        info = self.client.get_collection(collection_name=collection_name)
        vectors = info.config.params.vectors
        if vectors is None:
            return None
        if isinstance(vectors, dict):
            first = next(iter(vectors.values()), None)
            if first is None:
                return None
            size = getattr(first, "size", None)
            return int(size) if size is not None else None
        size = getattr(vectors, "size", None)
        return int(size) if size is not None else None

    def embedding_dim_matches_settings(self) -> bool | None:
        """None if collection missing; True/False if size matches active provider dimension."""
        configured = self.get_configured_vector_size()
        if configured is None:
            return None
        expected = self._expected_vector_size()
        return configured == expected

    def verify_sample_points_retrievable(self, point_ids: list[str | None], sample: int = 5) -> dict[str, Any]:
        """Lightweight post-upsert check: retrieve a small sample of point IDs."""
        point_ids = [pid for pid in point_ids if pid]
        if not point_ids:
            return {"sample_size": 0, "retrieved_count": 0, "sample_verified": True}
        if not self.collection_exists():
            return {"sample_size": 0, "retrieved_count": 0, "sample_verified": False, "error": "collection_missing"}
        collection_name = self._active_collection_name()
        sample_ids = point_ids[: min(sample, len(point_ids))]
        try:
            records = self.client.retrieve(
                collection_name=collection_name,
                ids=sample_ids,
                with_payload=False,
                with_vectors=False,
            )
        except Exception as exc:
            logger.warning("qdrant_sample_retrieve_failed collection=%s error=%s", self.collection_name, exc)
            return {
                "sample_size": len(sample_ids),
                "retrieved_count": 0,
                "sample_verified": False,
                "error": str(exc),
            }
        return {
            "sample_size": len(sample_ids),
            "retrieved_count": len(records),
            "sample_verified": len(records) == len(sample_ids),
        }

    def search_points(self, query_vector: list[float], limit: int) -> list[Any]:
        """Version-compatible vector search for qdrant-client APIs."""
        collection_name = self._active_collection_name()
        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
            )

        response = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        return list(getattr(response, "points", []) or [])


qdrant_service = QdrantService()
