from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.chunking_service import create_document_chunks
from app.services.docx_parser_service import docx_parser_service
from app.services.embedding_service import embedding_service
from app.services.qdrant_client import qdrant_service

logger = logging.getLogger(__name__)


class IngestionService:
    async def ingest_docx(
        self,
        db: Session,
        *,
        project_id: int,
        knowledge_base_id: int,
        document_type: str = "api",
        source_domain: str | None = None,
        product_name: str | None = None,
        version: str | None = None,
        file_name: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        project_row = db.execute(
            text("SELECT id FROM api_projects WHERE id = :project_id"),
            {"project_id": project_id},
        ).fetchone()
        if project_row is None:
            raise ValueError(f"Project {project_id} does not exist")

        try:
            parsed = docx_parser_service.parse_preview(file_name, file_bytes)
            chunks = create_document_chunks(
                parsed,
                document_type=document_type,
                product_name=product_name,
            )
        except Exception as exc:
            raise ValueError(f"docx_extraction_failed: {exc}") from exc
        apis = parsed.get("apis_full", [])
        chunk_type_counts = Counter((chunk.get("chunk_type") or "unknown") for chunk in chunks)
        detected_api_reference_ids = [api.get("api_reference_id") for api in apis if api.get("api_reference_id")]
        first_five_chunk_summaries = [
            {
                "chunk_type": chunk.get("chunk_type"),
                "title": ((chunk.get("chunk_text") or "").splitlines()[0] if (chunk.get("chunk_text") or "").strip() else "N/A"),
            }
            for chunk in chunks[:5]
        ]
        logger.info(
            "ingestion_chunking_summary document_id=pending kb_id=%s total_chunks=%s chunk_type_counts=%s "
            "detected_api_count=%s detected_api_reference_ids=%s first_5_chunks=%s",
            knowledge_base_id,
            len(chunks),
            dict(chunk_type_counts),
            len(detected_api_reference_ids),
            detected_api_reference_ids,
            first_five_chunk_summaries,
        )
        if len(file_bytes) > 100 * 1024 and len(chunks) < 10:
            logger.warning(
                "low_chunk_count_warning file_name=%s file_size_bytes=%s total_chunks=%s knowledge_base_id=%s",
                file_name,
                len(file_bytes),
                len(chunks),
                knowledge_base_id,
            )
        now = datetime.now(timezone.utc)
        job_row = db.execute(
            text(
                """
                INSERT INTO ingestion_jobs (project_id, status, total_endpoints, processed_chunks, started_at)
                VALUES (:project_id, :status, :total_endpoints, :processed_chunks, :started_at)
                RETURNING id
                """
            ),
            {
                "project_id": project_id,
                "status": "processing",
                "total_endpoints": len(apis),
                "processed_chunks": 0,
                "started_at": now,
            },
        ).fetchone()
        ingestion_job_id = job_row[0]

        try:
            document_row = db.execute(
                text(
                    """
                    INSERT INTO api_documents (
                        project_id, knowledge_base_id, file_name, source_type, document_type, source_domain, product_name,
                        document_title, document_version, raw_file_path
                    )
                    VALUES (
                        :project_id, :knowledge_base_id, :file_name, :source_type, :document_type, :source_domain, :product_name,
                        :document_title, :document_version, :raw_file_path
                    )
                    RETURNING id
                    """
                ),
                {
                    "project_id": project_id,
                    "knowledge_base_id": knowledge_base_id,
                    "file_name": file_name,
                    "source_type": "docx",
                    "document_type": document_type,
                    "source_domain": source_domain,
                    "product_name": product_name,
                    "document_title": (parsed.get("document_title") or file_name)[:255],
                    "document_version": version,
                    "raw_file_path": f"uploaded://{file_name}",
                },
            ).fetchone()
            document_id = document_row[0]
            logger.info(
                "ingestion_chunking_persist_summary document_id=%s knowledge_base_id=%s total_chunks=%s "
                "chunk_type_counts=%s detected_api_count=%s detected_api_reference_ids=%s first_5_chunks=%s",
                document_id,
                knowledge_base_id,
                len(chunks),
                dict(chunk_type_counts),
                len(detected_api_reference_ids),
                detected_api_reference_ids,
                first_five_chunk_summaries,
            )
            db.execute(
                text("UPDATE ingestion_jobs SET document_id = :document_id WHERE id = :job_id"),
                {"document_id": document_id, "job_id": ingestion_job_id},
            )

            endpoint_by_ref: dict[str, int] = {}
            for api in apis:
                endpoint_row = db.execute(
                    text(
                        """
                        INSERT INTO api_endpoints (
                            document_id, api_reference_id, service_name, service_group, service_description,
                            service_method, service_type, service_pattern, max_timeout, api_gateway,
                            authentication_type, swagger_urls_json, service_urls_json, environment_urls_json
                        )
                        VALUES (
                            :document_id, :api_reference_id, :service_name, :service_group, :service_description,
                            :service_method, :service_type, :service_pattern, :max_timeout, :api_gateway,
                            :authentication_type, CAST(:swagger_urls_json AS JSON), CAST(:service_urls_json AS JSON), CAST(:environment_urls_json AS JSON)
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "document_id": document_id,
                        "api_reference_id": (api.get("api_reference_id") or "UNKNOWN")[:100],
                        "service_name": (api.get("service_name") or "Unknown Service")[:255],
                        "service_group": (api.get("service_group") or None),
                        "service_description": api.get("service_description"),
                        "service_method": (api.get("service_method") or None),
                        "service_type": (api.get("service_type") or None),
                        "service_pattern": (api.get("service_pattern") or None),
                        "max_timeout": (api.get("service_max_timeout") or None),
                        "api_gateway": (api.get("api_gateway") or None),
                        "authentication_type": (api.get("api_authentication") or None),
                        "swagger_urls_json": self._json_or_none({"primary": api.get("service_swagger")} if api.get("service_swagger") else None),
                        "service_urls_json": self._json_or_none({"primary": api.get("service_url")} if api.get("service_url") else None),
                        "environment_urls_json": None,
                    },
                ).fetchone()
                endpoint_id = endpoint_row[0]
                endpoint_by_ref[(api.get("api_reference_id") or "UNKNOWN")[:100]] = endpoint_id

                self._persist_parameters(db, endpoint_id, "header", api.get("header_parameters", []))
                self._persist_parameters(db, endpoint_id, "input", api.get("input_parameters", []))
                self._persist_parameters(db, endpoint_id, "output_success", api.get("output_response_success", []))
                self._persist_samples(db, endpoint_id, api)

            db_chunk_ids: list[int] = []
            for chunk in chunks:
                metadata = chunk.get("metadata") or {}
                api_reference_id = metadata.get("api_reference_id")
                endpoint_id = endpoint_by_ref.get(api_reference_id) if api_reference_id else None
                chunk_row = db.execute(
                    text(
                        """
                        INSERT INTO document_chunks (document_id, endpoint_id, chunk_type, chunk_text, qdrant_point_id)
                        VALUES (:document_id, :endpoint_id, :chunk_type, :chunk_text, :qdrant_point_id)
                        RETURNING id
                        """
                    ),
                    {
                        "document_id": document_id,
                        "endpoint_id": endpoint_id,
                        "chunk_type": (chunk.get("chunk_type") or "unknown")[:100],
                        "chunk_text": chunk.get("chunk_text") or "",
                        "qdrant_point_id": None,
                    },
                ).fetchone()
                db_chunk_ids.append(chunk_row[0])

            qdrant_points_created = 0
            embedding_error: str | None = None
            vector_store_status = "skipped_no_embedding"
            vector_collection_name = qdrant_service._active_collection_name()
            vector_embedding_dimension: int | None = None
            vector_db_chunk_count_expected = len(db_chunk_ids)
            vector_point_count_delta_ok: bool | None = None
            vector_sample_verified: bool | None = None
            collection_embedding_dim: int | None = None
            embedding_dim_matches_collection: bool | None = None

            try:
                embedded_chunks = await embedding_service.embed_chunks(chunks)
                if embedded_chunks:
                    vec0 = embedded_chunks[0].get("embedding")
                    if isinstance(vec0, list):
                        vector_embedding_dimension = len(vec0)
                qdrant_point_ids = qdrant_service.upsert_chunks(embedded_chunks)
                vector_point_count_delta_ok = len(qdrant_point_ids) == len(db_chunk_ids) == len(
                    embedded_chunks,
                )

                if not vector_point_count_delta_ok:
                    vector_store_status = "persisted_partial_count_mismatch"
                    logger.warning(
                        "ingestion_vector_count_mismatch document_id=%s chunks=%s embedded=%s points=%s",
                        document_id,
                        len(db_chunk_ids),
                        len(embedded_chunks),
                        len(qdrant_point_ids),
                    )
                else:
                    vector_store_status = "persisted_ok"
                    sample_diag = qdrant_service.verify_sample_points_retrievable(qdrant_point_ids)
                    vector_sample_verified = bool(sample_diag.get("sample_verified"))
                    if not vector_sample_verified and qdrant_point_ids:
                        vector_store_status = "persisted_sample_verify_failed"
                        logger.warning(
                            "ingestion_vector_sample_verify_failed document_id=%s sample_diag=%s",
                            document_id,
                            sample_diag,
                        )

                collection_embedding_dim = qdrant_service.get_configured_vector_size()
                embedding_dim_matches_collection = qdrant_service.embedding_dim_matches_settings()

                logger.info(
                    "ingestion_vector_persist document_id=%s kb_id=%s status=%s collection=%s "
                    "point_count=%s chunk_expected=%s embed_dim=%s collection_dim=%s dim_match_settings=%s sample_ok=%s",
                    document_id,
                    knowledge_base_id,
                    vector_store_status,
                    vector_collection_name,
                    len(qdrant_point_ids),
                    vector_db_chunk_count_expected,
                    vector_embedding_dimension,
                    collection_embedding_dim,
                    embedding_dim_matches_collection,
                    vector_sample_verified,
                )
                for chunk_id, point_id in zip(db_chunk_ids, qdrant_point_ids, strict=False):
                    db.execute(
                        text("UPDATE document_chunks SET qdrant_point_id = :point_id WHERE id = :chunk_id"),
                        {"point_id": point_id, "chunk_id": chunk_id},
                    )
                qdrant_points_created = len(qdrant_point_ids)
            except Exception as exc:
                embedding_error = str(exc)
                vector_store_status = "embedding_failed"
                logger.warning(
                    "ingestion_embedding_failed document_id=%s kb_id=%s error=%s",
                    document_id,
                    knowledge_base_id,
                    exc,
                )

            db.execute(
                text(
                    """
                    UPDATE ingestion_jobs
                    SET status = :status,
                        processed_chunks = :processed_chunks,
                        error_message = :error_message,
                        completed_at = :completed_at
                    WHERE id = :job_id
                    """
                ),
                {
                    "status": "completed_with_warnings" if embedding_error else "completed",
                    "processed_chunks": len(db_chunk_ids),
                    "error_message": embedding_error,
                    "completed_at": datetime.now(timezone.utc),
                    "job_id": ingestion_job_id,
                },
            )
            db.commit()

            return {
                "ingestion_job_id": ingestion_job_id,
                "project_id": project_id,
                "document_id": document_id,
                "document_type": document_type,
                "source_domain": source_domain,
                "product_name": product_name,
                "version": version,
                "api_count": len(apis),
                "chunk_count": len(db_chunk_ids),
                "qdrant_points_created": qdrant_points_created,
                "embedding_status": (
                    "embedding_retry_failed"
                    if embedding_error and "retry_failed" in embedding_error.lower()
                    else ("embedding_skipped" if embedding_error else "stored")
                ),
                "embedding_error": embedding_error,
                "vector_store_status": vector_store_status,
                "vector_point_count": qdrant_points_created,
                "vector_collection_name": vector_collection_name,
                "vector_db_chunk_count_expected": vector_db_chunk_count_expected,
                "vector_embedding_dimension": vector_embedding_dimension,
                "vector_configured_collection_embedding_dim": collection_embedding_dim,
                "embedding_dim_matches_collection": embedding_dim_matches_collection,
                "embedding_dim_expected": settings.EMBEDDING_DIM,
                "vector_sample_verified": vector_sample_verified,
                "vector_point_count_matches_chunks": vector_point_count_delta_ok,
            }
        except Exception as exc:
            db.rollback()
            db.execute(
                text(
                    """
                    UPDATE ingestion_jobs
                    SET status = :status,
                        error_message = :error_message,
                        completed_at = :completed_at
                    WHERE id = :job_id
                    """
                ),
                {
                    "status": "failed",
                    "error_message": str(exc),
                    "completed_at": datetime.now(timezone.utc),
                    "job_id": ingestion_job_id,
                },
            )
            db.commit()
            raise

    def _persist_parameters(
        self,
        db: Session,
        endpoint_id: int,
        parameter_location: str,
        params: list[dict[str, Any]],
    ) -> None:
        for param in params:
            name = (param.get("param_name") or "").strip()
            if not name:
                continue
            db.execute(
                text(
                    """
                    INSERT INTO api_parameters (endpoint_id, parameter_location, param_name, param_type, mandatory_optional, description)
                    VALUES (:endpoint_id, :parameter_location, :param_name, :param_type, :mandatory_optional, :description)
                    """
                ),
                {
                    "endpoint_id": endpoint_id,
                    "parameter_location": parameter_location,
                    "param_name": name[:255],
                    "param_type": (param.get("param_type") or None),
                    "mandatory_optional": (param.get("mandatory_optional") or None),
                    "description": (param.get("description") or None),
                },
            )

    def _persist_samples(self, db: Session, endpoint_id: int, api: dict[str, Any]) -> None:
        sample_initial = api.get("sample_initial")
        if sample_initial:
            db.execute(
                text(
                    "INSERT INTO api_samples (endpoint_id, sample_type, sample_text) VALUES (:endpoint_id, :sample_type, :sample_text)"
                ),
                {
                    "endpoint_id": endpoint_id,
                    "sample_type": "sample_initial",
                    "sample_text": str(sample_initial),
                },
            )
        sample_token_exist = api.get("sample_token_exist")
        if sample_token_exist:
            db.execute(
                text(
                    "INSERT INTO api_samples (endpoint_id, sample_type, sample_text) VALUES (:endpoint_id, :sample_type, :sample_text)"
                ),
                {
                    "endpoint_id": endpoint_id,
                    "sample_type": "sample_token_exist",
                    "sample_text": str(sample_token_exist),
                },
            )

    def _json_or_none(self, value: dict[str, Any] | None) -> str | None:
        if value is None:
            return None
        import json

        return json.dumps(value)


ingestion_service = IngestionService()
