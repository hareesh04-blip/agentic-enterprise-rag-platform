from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embedding_service import embedding_service
from app.services.ingestion_service import _embedding_provider_label
from app.services.qdrant_client import qdrant_service

logger = logging.getLogger(__name__)


class DocumentGovernanceService:
    async def reindex_document(self, db: Session, *, document_id: int) -> dict[str, Any]:
        rows = db.execute(
            text(
                """
                SELECT id, chunk_text, chunk_type, qdrant_point_id
                FROM document_chunks
                WHERE document_id = :document_id
                ORDER BY id ASC
                """
            ),
            {"document_id": document_id},
        ).mappings().all()
        if not rows:
            raise ValueError(f"No chunks found for document_id={document_id}")

        old_point_ids = [str(r["qdrant_point_id"]) for r in rows if r.get("qdrant_point_id")]
        if old_point_ids:
            qdrant_service.delete_points(old_point_ids)

        chunks_payload: list[dict[str, Any]] = [
            {
                "chunk_text": r["chunk_text"],
                "chunk_type": r["chunk_type"],
                "metadata": {},
            }
            for r in rows
        ]
        embedded = await embedding_service.embed_chunks(chunks_payload)
        new_point_ids = qdrant_service.upsert_chunks(embedded)
        vectors_upserted = sum(1 for pid in new_point_ids if pid)
        chunks_embedding_failed = sum(
            1
            for c in embedded
            if (not isinstance(c.get("embedding"), list)) or (not c.get("embedding"))
        )

        if vectors_upserted != len(rows):
            logger.warning(
                "reindex_vector_partial document_id=%s chunks=%s vectors_upserted=%s chunks_embedding_failed=%s",
                document_id,
                len(rows),
                vectors_upserted,
                chunks_embedding_failed,
            )

        for chunk_row, point_id in zip(rows, new_point_ids, strict=True):
            if point_id:
                db.execute(
                    text("UPDATE document_chunks SET qdrant_point_id = :pid WHERE id = :cid"),
                    {"pid": point_id, "cid": chunk_row["id"]},
                )

        embed_prov = _embedding_provider_label()
        vector_collection_name = qdrant_service._active_collection_name()
        db.execute(
            text(
                """
                UPDATE api_documents
                SET ingestion_status = :st,
                    embedding_provider = :emb,
                    vector_collection_name = :vcoll,
                    uploaded_at = :ua
                WHERE id = :document_id
                """
            ),
            {
                "st": "completed",
                "emb": embed_prov,
                "vcoll": vector_collection_name,
                "ua": datetime.now(timezone.utc),
                "document_id": document_id,
            },
        )
        db.commit()

        return {
            "document_id": document_id,
            "chunks_reindexed": len(rows),
            "vectors_upserted": vectors_upserted,
            "chunks_embedding_failed": chunks_embedding_failed,
            "embedding_provider": embed_prov,
            "vector_collection_name": vector_collection_name,
        }

    def deactivate_document(self, db: Session, *, document_id: int) -> dict[str, Any]:
        db.execute(
            text("UPDATE api_documents SET is_active_document = FALSE WHERE id = :id"),
            {"id": document_id},
        )
        db.commit()
        return {"document_id": document_id, "is_active_document": False}

    def reactivate_document(self, db: Session, *, document_id: int) -> dict[str, Any]:
        db.execute(
            text("UPDATE api_documents SET is_active_document = TRUE WHERE id = :id"),
            {"id": document_id},
        )
        db.commit()
        return {"document_id": document_id, "is_active_document": True}

    def remove_vectors_only(self, db: Session, *, document_id: int) -> dict[str, Any]:
        rows = db.execute(
            text("SELECT id, qdrant_point_id FROM document_chunks WHERE document_id = :document_id"),
            {"document_id": document_id},
        ).mappings().all()
        point_ids = [str(r["qdrant_point_id"]) for r in rows if r.get("qdrant_point_id")]
        if point_ids:
            qdrant_service.delete_points(point_ids)
        db.execute(
            text("UPDATE document_chunks SET qdrant_point_id = NULL WHERE document_id = :document_id"),
            {"document_id": document_id},
        )
        db.execute(
            text(
                """
                UPDATE api_documents
                SET ingestion_status = :st
                WHERE id = :document_id
                """
            ),
            {"st": "vectors_removed", "document_id": document_id},
        )
        db.commit()
        return {"document_id": document_id, "vectors_removed": len(point_ids)}


document_governance_service = DocumentGovernanceService()
