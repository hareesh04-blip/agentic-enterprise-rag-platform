from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.database import SessionLocal
from app.services.chunking_service import (
    generic_chunk_qualifies_as_response_fields,
    response_parameters_chunk_quality,
)
from app.services.embedding_service import embedding_service
from app.services.query_intent_service import detect_query_intents
from app.services.qdrant_client import qdrant_service

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(RuntimeError):
    pass


class RetrievalService:
    _last_parameter_promotion_applied: bool = False

    async def retrieve(
        self,
        project_id: int,
        knowledge_base_id: int,
        question: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        self._last_parameter_promotion_applied = False
        candidate_k = max(settings.HYBRID_VECTOR_TOP_K, top_k * 3, 12)
        collection_name = qdrant_service._active_collection_name()
        collection_exists_flag = qdrant_service.collection_exists()
        vectors_count = qdrant_service.collection_point_count() if collection_exists_flag else 0
        configured_dim = qdrant_service.get_configured_vector_size()

        embedding_provider = (getattr(settings, "EMBEDDING_PROVIDER", "ollama") or "ollama").strip().lower()
        active_embedding_model = (
            settings.OPENAI_EMBEDDING_MODEL
            if embedding_provider == "openai"
            else settings.OLLAMA_EMBEDDING_MODEL
        )

        vector_diag_base: dict[str, Any] = {
            "vector_collection_name": collection_name,
            "collection_exists": collection_exists_flag,
            "collection_point_count": vectors_count,
            "embedding_dimension_expected": settings.EMBEDDING_DIM,
            "configured_collection_embedding_dim": configured_dim,
            "embedding_dimension_matches_collection": qdrant_service.embedding_dim_matches_settings(),
            "embedding_attempted": False,
            "embedding_succeeded": False,
            "vector_search_attempted": False,
            "vector_search_succeeded": False,
            "vector_raw_hit_count": 0,
            "vector_results_count": 0,
            "candidate_pool_size": candidate_k,
            "vector_candidate_count": 0,
            "keyword_candidate_count": 0,
            "final_context_count": 0,
            "reranked_result_count": 0,
            "hybrid_fusion_used": False,
            "fusion_candidate_count": 0,
            "metadata_boost_applied": False,
            "detected_intents": [],
            "top_chunk_types": [],
            "applied_boosts": [],
            "top_combined_score": None,
            "rerank_strategy": "local_weighted_v1",
            "vector_confidence_bucket": None,
            "fallback_triggered": False,
            "fallback_reason": None,
            "vector_retrieval_outcome": "idle",
            "vector_hits_missing_db_row_filtered": 0,
            "vector_hits_project_mismatch_filtered": 0,
            "vector_hits_kb_mismatch_filtered": 0,
            "vector_hits_inactive_document_filtered": 0,
            "embedding_model": active_embedding_model,
            "embedding_endpoint": f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings",
            "embedding_text_length": len(question or ""),
            "embedding_exception_class": None,
        }

        if vectors_count == 0:
            reason = (
                "no_collection"
                if not collection_exists_flag
                else "no_vectors_in_collection"
            )
            fallback_results = self.fallback_keyword_search(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            )
            vector_diag_base.update(
                {
                    "fallback_triggered": True,
                    "fallback_reason": reason,
                    "vector_retrieval_outcome": "fallback",
                    "vector_results_count": len(fallback_results),
                }
            )
            logger.info(
                "retrieval_vector_diag project=%s kb=%s mode=db_keyword_fallback outcome=%s reason=%s raw_hits=%s",
                project_id,
                knowledge_base_id,
                vector_diag_base["vector_retrieval_outcome"],
                reason,
                0,
            )
            return {
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "top_k": top_k,
                "retrieval_mode": "vector_only",
                "message": (
                    "No vectors found. Using PostgreSQL keyword fallback retrieval."
                    if collection_exists_flag
                    else "Vector collection does not exist. Using PostgreSQL keyword fallback retrieval."
                ),
                "results": fallback_results,
                "vector_retrieval_diagnostics": vector_diag_base,
            }

        vector_diag_base["embedding_attempted"] = True
        try:
            question_embedding = await embedding_service.embed_text(question)
            vector_diag_base["embedding_succeeded"] = True
        except Exception as exc:
            vector_diag_base.update(
                {
                    "embedding_succeeded": False,
                    "fallback_triggered": True,
                    "fallback_reason": "embedding_failed",
                    "vector_retrieval_outcome": "fallback_embedding",
                    "vector_results_count": 0,
                    "embedding_exception_class": exc.__class__.__name__,
                }
            )
            fallback_results = self.fallback_keyword_search(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            )
            vector_diag_base["vector_results_count"] = len(fallback_results)
            logger.info(
                "retrieval_vector_diag project=%s kb=%s mode=db_keyword_fallback outcome=%s reason=embedding_failed "
                "embed_len=%s err_class=%s err=%s",
                project_id,
                knowledge_base_id,
                vector_diag_base["vector_retrieval_outcome"],
                vector_diag_base["embedding_text_length"],
                vector_diag_base["embedding_exception_class"],
                exc,
            )
            return {
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "top_k": top_k,
                "retrieval_mode": "vector_only",
                "message": f"Embedding service unavailable ({exc}). Using PostgreSQL keyword fallback retrieval.",
                "results": fallback_results,
                "vector_retrieval_diagnostics": vector_diag_base,
            }

        vector_diag_base["vector_search_attempted"] = True
        try:
            hits = qdrant_service.search_points(question_embedding, max(candidate_k, 1))
            vector_diag_base["vector_search_succeeded"] = True
        except Exception as exc:
            vector_diag_base.update(
                {
                    "vector_search_succeeded": False,
                    "fallback_triggered": True,
                    "fallback_reason": "qdrant_search_failed",
                    "vector_retrieval_outcome": "fallback_qdrant",
                    "vector_results_count": 0,
                }
            )
            fallback_results = self.fallback_keyword_search(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            )
            vector_diag_base["vector_results_count"] = len(fallback_results)
            logger.info(
                "retrieval_vector_diag project=%s kb=%s mode=db_keyword_fallback outcome=%s reason=qdrant_search_failed err=%s",
                project_id,
                knowledge_base_id,
                vector_diag_base["vector_retrieval_outcome"],
                exc,
            )
            return {
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "top_k": top_k,
                "retrieval_mode": "vector_only",
                "message": f"Vector retrieval unavailable ({exc}). Using PostgreSQL keyword fallback retrieval.",
                "results": fallback_results,
                "vector_retrieval_diagnostics": vector_diag_base,
            }

        raw_hits_count = len(hits)
        vector_diag_base["vector_raw_hit_count"] = raw_hits_count

        if not hits:
            vector_diag_base.update(
                {
                    "vector_retrieval_outcome": "vector_empty",
                    "vector_results_count": 0,
                    "fallback_triggered": False,
                    "fallback_reason": None,
                }
            )
            logger.info(
                "retrieval_vector_diag project=%s kb=%s mode=vector outcome=vector_empty raw_hits=0",
                project_id,
                knowledge_base_id,
            )
            return {
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "top_k": top_k,
                "retrieval_mode": "vector_only",
                "message": None,
                "results": [],
                "vector_retrieval_diagnostics": vector_diag_base,
            }

        point_ids = [str(hit.id) for hit in hits]
        rows_by_point: dict[str, dict[str, Any]] = {}
        with SessionLocal() as db:
            query_result = db.execute(
                text(
                    """
                    SELECT
                        dc.qdrant_point_id,
                        d.id AS document_id,
                        d.project_id,
                        d.knowledge_base_id,
                        d.file_name,
                        d.document_type,
                        d.source_domain,
                        d.product_name,
                        d.document_version,
                        d.uploaded_at,
                        d.ingestion_run_id,
                        d.is_active_document,
                        kb.name AS knowledge_base_name,
                        e.id AS endpoint_id,
                        e.api_reference_id,
                        e.service_name,
                        e.service_group,
                        e.service_method,
                        e.service_pattern
                    FROM document_chunks dc
                    JOIN api_documents d ON d.id = dc.document_id
                    LEFT JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
                    LEFT JOIN api_endpoints e ON e.id = dc.endpoint_id
                    WHERE dc.qdrant_point_id = ANY(:point_ids)
                    """
                ),
                {"point_ids": point_ids},
            )
            for row in query_result.mappings().all():
                rows_by_point[str(row["qdrant_point_id"])] = dict(row)

        vector_candidates: list[dict[str, Any]] = []
        missing_db = project_mismatch = kb_mismatch = inactive_filtered = 0

        for hit in hits:
            point_id = str(hit.id)
            row = rows_by_point.get(point_id)
            if not row:
                missing_db += 1
                continue
            if row.get("project_id") != project_id:
                project_mismatch += 1
                continue
            if row.get("knowledge_base_id") != knowledge_base_id:
                kb_mismatch += 1
                continue
            if row.get("is_active_document") is False:
                inactive_filtered += 1
                continue
            payload = hit.payload or {}
            metadata = payload.get("metadata") or {}
            section_title = metadata.get("section_title")
            document_type_val = row.get("document_type")
            product_name_val = row.get("product_name")
            document_version_val = row.get("document_version")
            kb_id_val = row.get("knowledge_base_id")

            vector_candidates.append(
                {
                    "source_type": "vector",
                    "score": float(hit.score),
                    "vector_score_raw": float(hit.score),
                    "fallback_score_raw": None,
                    "chunk_text": payload.get("chunk_text"),
                    "chunk_type": payload.get("chunk_type"),
                    "section_title": section_title,
                    "document_id": row.get("document_id"),
                    "endpoint_id": row.get("endpoint_id"),
                    "api_reference_id": row.get("api_reference_id") or metadata.get("api_reference_id"),
                    "service_name": row.get("service_name") or metadata.get("service_name"),
                    "service_group": row.get("service_group") or metadata.get("service_group"),
                    "service_method": row.get("service_method") or metadata.get("service_method"),
                    "service_pattern": row.get("service_pattern") or metadata.get("service_pattern"),
                    "file_name": row.get("file_name"),
                    "document_type": document_type_val,
                    "source_domain": row.get("source_domain"),
                    "product_name": product_name_val,
                    "document_version": document_version_val,
                    "knowledge_base_id": kb_id_val,
                    "knowledge_base_name": row.get("knowledge_base_name"),
                    "upload_timestamp": row.get("uploaded_at").isoformat()
                    if row.get("uploaded_at") is not None and hasattr(row.get("uploaded_at"), "isoformat")
                    else None,
                    "ingestion_run_id": row.get("ingestion_run_id"),
                    "is_active_document": row.get("is_active_document")
                    if row.get("is_active_document") is not None
                    else True,
                }
            )
        vector_diag_base["vector_hits_inactive_document_filtered"] = inactive_filtered
        vector_diag_base["vector_candidate_count"] = len(vector_candidates)

        detected_intents = detect_query_intents(question)
        vector_diag_base["detected_intents"] = detected_intents
        retrieval_mode = "vector_only"
        keyword_count = 0
        applied_boosts: list[str] = []
        try:
            combined_candidates = list(vector_candidates)
            if settings.ENABLE_HYBRID_RETRIEVAL:
                keyword_candidates = self.fallback_keyword_search(
                    project_id=project_id,
                    knowledge_base_id=knowledge_base_id,
                    question=question,
                    top_k=max(settings.HYBRID_KEYWORD_TOP_K, top_k),
                )
                normalized_keyword_candidates: list[dict[str, Any]] = []
                for item in keyword_candidates:
                    candidate = dict(item)
                    candidate["source_type"] = "keyword"
                    candidate["vector_score_raw"] = None
                    candidate["fallback_score_raw"] = float(item.get("score", 0.0) or 0.0)
                    normalized_keyword_candidates.append(candidate)
                keyword_count = len(normalized_keyword_candidates)
                if normalized_keyword_candidates:
                    combined_candidates = self._merge_candidates(
                        vector_candidates=vector_candidates,
                        keyword_candidates=normalized_keyword_candidates,
                    )
                    vector_diag_base["hybrid_fusion_used"] = True
                    vector_diag_base["fusion_candidate_count"] = len(combined_candidates)
                    retrieval_mode = "hybrid_metadata_rerank"

            if settings.ENABLE_METADATA_RERANKING:
                combined_candidates = self._rerank_candidates(
                    candidates=combined_candidates,
                    question=question,
                    intents=detected_intents,
                )
            else:
                combined_candidates = sorted(combined_candidates, key=lambda x: float(x.get("score") or 0.0), reverse=True)

            combined_candidates = self._promote_matching_request_parameter_chunks(
                combined_candidates,
                question,
                detected_intents,
            )
        except Exception as exc:
            logger.warning("hybrid_rerank_failed project=%s kb=%s err=%s", project_id, knowledge_base_id, exc)
            retrieval_mode = "vector_only"
            combined_candidates = sorted(vector_candidates, key=lambda x: float(x.get("score") or 0.0), reverse=True)
            vector_diag_base["hybrid_fusion_used"] = False
            vector_diag_base["fusion_candidate_count"] = 0

        vector_diag_base["request_parameter_chunk_promoted"] = self._last_parameter_promotion_applied

        metadata_boost_applied = any((item.get("_metadata_boost", 0.0) or 0.0) > 0 for item in combined_candidates)
        top_combined_score = combined_candidates[0].get("_combined_score") if combined_candidates else None
        for item in combined_candidates[:3]:
            for boost in item.get("_applied_boosts", []):
                if boost not in applied_boosts:
                    applied_boosts.append(boost)

        top_vector_score = vector_candidates[0]["vector_score_raw"] if vector_candidates else 0.0
        vector_meta_coverage = self._metadata_coverage_ratio(vector_candidates)
        vector_confidence_bucket = self._vector_confidence_bucket(
            top_vector_score=top_vector_score,
            vector_results_count=len(vector_candidates),
            top_k=top_k,
        )
        final_top_k = min(max(top_k, 1), settings.FINAL_CONTEXT_TOP_K if settings.FINAL_CONTEXT_TOP_K > 0 else top_k)
        results = [self._strip_internal_score_fields(item) for item in combined_candidates[:final_top_k]]
        top_chunk_types = [item.get("chunk_type") for item in combined_candidates[:final_top_k] if item.get("chunk_type")]

        vector_diag_base.update(
            {
                "vector_hits_missing_db_row_filtered": missing_db,
                "vector_hits_project_mismatch_filtered": project_mismatch,
                "vector_hits_kb_mismatch_filtered": kb_mismatch,
                "vector_results_count": len(results),
                "keyword_candidate_count": keyword_count,
                "final_context_count": len(results),
                "reranked_result_count": len(results),
                "metadata_boost_applied": metadata_boost_applied,
                "top_chunk_types": top_chunk_types,
                "applied_boosts": applied_boosts,
                "top_combined_score": round(float(top_combined_score), 6) if top_combined_score is not None else None,
                "vector_confidence_bucket": vector_confidence_bucket,
                "fallback_triggered": False,
                "fallback_reason": None,
            }
        )

        if results:
            vector_diag_base["vector_retrieval_outcome"] = "vector_success"
        elif raw_hits_count > 0:
            vector_diag_base["vector_retrieval_outcome"] = "vector_kb_filtered_empty"
        else:
            vector_diag_base["vector_retrieval_outcome"] = "vector_empty"

        logger.info(
            "retrieval_vector_diag project=%s kb=%s mode=vector outcome=%s raw_hits=%s results=%s "
            "filtered_missing_db=%s filtered_project=%s filtered_kb=%s",
            project_id,
            knowledge_base_id,
            vector_diag_base["vector_retrieval_outcome"],
            raw_hits_count,
            len(results),
            missing_db,
            project_mismatch,
            kb_mismatch,
        )

        return {
            "project_id": project_id,
            "knowledge_base_id": knowledge_base_id,
            "question": question,
            "top_k": top_k,
                "retrieval_mode": retrieval_mode,
            "message": None,
            "results": results,
            "vector_retrieval_diagnostics": vector_diag_base,
        }

    def _strip_internal_score_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(item)
        for key in (
            "_combined_score",
            "_vector_norm",
            "_keyword_norm",
            "_lexical_score",
            "_metadata_boost",
            "_source_type_boost",
            "source_type",
            "vector_score_raw",
            "fallback_score_raw",
        ):
            cleaned.pop(key, None)
        return cleaned

    def _merge_candidates(
        self,
        *,
        vector_candidates: list[dict[str, Any]],
        keyword_candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for candidate in vector_candidates + keyword_candidates:
            key = self._candidate_key(candidate)
            existing = merged.get(key)
            if existing is None:
                merged[key] = dict(candidate)
                continue
            if candidate.get("vector_score_raw") is not None:
                existing["vector_score_raw"] = max(
                    float(existing.get("vector_score_raw") or 0.0),
                    float(candidate.get("vector_score_raw") or 0.0),
                )
            if candidate.get("fallback_score_raw") is not None:
                existing["fallback_score_raw"] = max(
                    float(existing.get("fallback_score_raw") or 0.0),
                    float(candidate.get("fallback_score_raw") or 0.0),
                )
            existing["score"] = max(float(existing.get("score") or 0.0), float(candidate.get("score") or 0.0))
        return list(merged.values())

    def _candidate_key(self, item: dict[str, Any]) -> str:
        parts = [
            str(item.get("document_id") or ""),
            str(item.get("endpoint_id") or ""),
            str(item.get("api_reference_id") or ""),
            str(item.get("section_title") or ""),
            (item.get("chunk_text") or "")[:180].strip().lower(),
        ]
        return "|".join(parts)

    def _promote_matching_request_parameter_chunks(
        self,
        candidates: list[dict[str, Any]],
        question: str,
        intents: list[str],
    ) -> list[dict[str, Any]]:
        """
        Move the best-matching api_request_parameters_chunk to rank 1 when the question asks for
        mandatory/required/request inputs for a named API (hybrid pool may still rank metadata higher).
        """
        self._last_parameter_promotion_applied = False
        if "parameter_intent" not in intents or not candidates:
            return candidates
        q = (question or "").lower()
        best_idx: int | None = None
        best_score = -1.0
        for idx, item in enumerate(candidates):
            if (item.get("chunk_type") or "") != "api_request_parameters_chunk":
                continue
            sn = (item.get("service_name") or "").lower()
            ar = (item.get("api_reference_id") or "").lower()
            txt = (item.get("chunk_text") or "").lower()
            score = 0.0
            if sn and sn in q:
                score += 5.0
            if ar and ar in q:
                score += 4.0
            for tok in self._tokenize(question):
                if len(tok) >= 6 and tok in txt:
                    score += 0.35
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx is None or best_score < 2.0:
            return candidates
        if best_idx == 0:
            return candidates
        promoted = candidates[best_idx]
        others = [c for i, c in enumerate(candidates) if i != best_idx]
        self._last_parameter_promotion_applied = True
        return [promoted] + others

    def _rerank_candidates(self, *, candidates: list[dict[str, Any]], question: str, intents: list[str]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        terms = self._tokenize(question)
        vector_scores = [float(item.get("vector_score_raw") or 0.0) for item in candidates if item.get("vector_score_raw") is not None]
        keyword_scores = [float(item.get("fallback_score_raw") or 0.0) for item in candidates if item.get("fallback_score_raw") is not None]
        for item in candidates:
            vector_norm = self._normalize_score(float(item.get("vector_score_raw") or 0.0), vector_scores)
            keyword_norm = self._normalize_score(float(item.get("fallback_score_raw") or 0.0), keyword_scores)
            keyword_boost = self._lexical_overlap_score(item, terms) * 0.25
            metadata_boost, chunk_type_boost, boost_labels = self._intent_boosts(item, question, intents)
            combined_score = vector_norm + metadata_boost + keyword_boost + chunk_type_boost
            item["_vector_norm"] = vector_norm
            item["_keyword_norm"] = keyword_norm
            item["_lexical_score"] = keyword_boost
            item["_metadata_boost"] = metadata_boost
            item["_source_type_boost"] = chunk_type_boost
            item["_applied_boosts"] = boost_labels
            item["_combined_score"] = combined_score
        return sorted(candidates, key=lambda x: x.get("_combined_score", 0.0), reverse=True)

    def _normalize_score(self, value: float, values: list[float]) -> float:
        if not values:
            return 0.0
        lo = min(values)
        hi = max(values)
        if hi <= lo:
            return 1.0 if value > 0 else 0.0
        return (value - lo) / (hi - lo)

    def _lexical_overlap_score(self, item: dict[str, Any], terms: list[str]) -> float:
        if not terms:
            return 0.0
        fields = [
            item.get("chunk_text") or "",
            item.get("product_name") or "",
            item.get("section_title") or "",
            item.get("document_type") or "",
            item.get("api_reference_id") or "",
            item.get("service_name") or "",
        ]
        searchable = " ".join(fields).lower()
        matched = sum(1 for term in terms if term in searchable)
        return matched / max(len(terms), 1)

    def _intent_boosts(self, item: dict[str, Any], question: str, intents: list[str]) -> tuple[float, float, list[str]]:
        text = " ".join(
            [
                str(item.get("chunk_text") or ""),
                str(item.get("chunk_type") or ""),
                str(item.get("service_name") or ""),
                str(item.get("api_reference_id") or ""),
                str(item.get("service_pattern") or ""),
            ]
        ).lower()
        chunk_type = (item.get("chunk_type") or "").lower()
        metadata_boost = 0.0
        chunk_type_boost = 0.0
        labels: list[str] = []

        if "authentication_intent" in intents:
            if chunk_type == "authentication_chunk":
                # Step 55: expiry-specific questions should rank auth_semantic_summary_chunk above thin preamble chunks.
                auth_boost = 0.22 if "token_expiry_intent" in intents else 0.75
                chunk_type_boost += auth_boost
                labels.append("authentication_chunk")
            if chunk_type == "auth_semantic_summary_chunk":
                chunk_type_boost += 0.35
                labels.append("auth_semantic_summary_chunk")
            if any(token in text for token in ["token", "oauth2", "client credentials", "jwt", "getsso", "bearer"]):
                metadata_boost += 0.25
                labels.append("auth_tokens")

        if "error_intent" in intents:
            if chunk_type in {"api_sample_failed_response_chunk", "api_error_codes_chunk"}:
                chunk_type_boost += 0.35
                labels.append("failed_response_chunk")
            if any(token in text for token in ["failed response", "returncode", "returnmsg", "incorrect", "invalid"]):
                metadata_boost += 0.25
                labels.append("error_tokens")

        if "response_field_intent" in intents:
            if chunk_type == "endpoint_response_chunk":
                chunk_type_boost += 0.55
                labels.append("response_field_chunk_type")
            if chunk_type == "api_sample_success_response_chunk":
                chunk_type_boost += 0.48
                labels.append("response_field_chunk_type")
                tail = ""
                if "sample success response:" in text:
                    tail = text.split("sample success response:", 1)[-1].strip()[:240]
                if not tail or tail.lower().startswith("n/a") or tail.lower() == "n/a":
                    chunk_type_boost -= 0.78
                    labels.append("empty_sample_success_penalty")
            if chunk_type == "api_sample_failed_response_chunk":
                chunk_type_boost += 0.35
                ftail = ""
                if "sample failed response:" in text:
                    ftail = text.split("sample failed response:", 1)[-1].strip()[:240]
                elif "failed response:" in text:
                    ftail = text.split("failed response:", 1)[-1].strip()[:240]
                if not ftail or ftail.lower().startswith("n/a") or ftail.lower() == "n/a":
                    chunk_type_boost -= 0.78
                    labels.append("empty_sample_failed_penalty")
            if chunk_type == "api_response_parameters_chunk":
                q = response_parameters_chunk_quality(str(item.get("chunk_text") or ""))
                if q.get("boost_ok"):
                    chunk_type_boost += 0.62
                    labels.append("structured_response_boost")
                else:
                    chunk_type_boost -= 0.82
                    labels.append("weak_response_chunk_penalty")
            if chunk_type == "generic_section_chunk":
                if generic_chunk_qualifies_as_response_fields(str(item.get("chunk_text") or "")):
                    chunk_type_boost += 0.62
                    labels.append("generic_response_fields_boost")
                else:
                    chunk_type_boost -= 0.15
                    labels.append("response_intent_generic_penalty")
            if chunk_type == "api_semantic_summary_chunk":
                if any(
                    k in text
                    for k in (
                        "success response fields",
                        "responseinfo",
                        "qrtext",
                        "transactionid",
                        "correlationid",
                        "errorcode",
                        "errormsg",
                    )
                ):
                    chunk_type_boost += 0.40
                    labels.append("api_semantic_summary_response_fields")

        if "async_intent" in intents:
            if chunk_type in {"api_metadata_chunk", "api_overview_chunk"}:
                chunk_type_boost += 0.28
                labels.append("async_chunk_type")
            if any(token in text for token in ["asynch", "asynchronous", "callback"]):
                metadata_boost += 0.28
                labels.append("async_tokens")
            pattern = str(item.get("service_pattern") or "").lower()
            if "asynch" in pattern or "callback" in pattern:
                metadata_boost += 1.2
                labels.append("async_service_pattern")

        if "api_lookup_intent" in intents:
            if chunk_type in {"api_metadata_chunk", "api_overview_chunk"}:
                chunk_type_boost += 0.22
                labels.append("api_lookup_chunk_type")
            if item.get("service_name") and item.get("api_reference_id"):
                metadata_boost += 0.2
                labels.append("service_and_ref")

        if "parameter_intent" in intents:
            if chunk_type in {
                "api_request_parameters_chunk",
                "api_response_parameters_chunk",
                "api_header_parameters_chunk",
                "api_query_parameters_chunk",
                "api_jwt_payload_chunk",
                "api_semantic_summary_chunk",
                "api_table_flattened_chunk",
            }:
                boost = 0.32
                if chunk_type == "api_request_parameters_chunk":
                    boost = 0.55
                    qlow = (question or "").lower()
                    sn = (item.get("service_name") or "").lower()
                    ar = (item.get("api_reference_id") or "").lower()
                    if sn and sn in qlow:
                        boost += 0.95
                        labels.append("request_param_service_name_match")
                    if ar and ar in qlow:
                        boost += 0.75
                        labels.append("request_param_api_ref_match")
                    ctx = (item.get("chunk_text") or "").lower()
                    if "request parameters" in ctx and any(
                        w in ctx for w in ("mandatory", "required", "name", "type", "description")
                    ):
                        boost += 0.2
                        labels.append("request_param_table_signal")
                chunk_type_boost += boost
                labels.append("parameter_chunk_type")
            if "response_field_intent" not in intents and chunk_type == "api_error_codes_chunk":
                chunk_type_boost += 0.30
                labels.append("parameter_chunk_type")

        if "header_parameter_intent" in intents:
            if chunk_type in {"api_semantic_summary_chunk", "api_table_flattened_chunk", "api_header_parameters_chunk"}:
                if any(k in text for k in ["header", "authorization", "transactionid", "required header"]):
                    chunk_type_boost += 1.18
                    labels.append("header_semantic_boost")

        if "token_expiry_intent" in intents:
            if chunk_type == "auth_semantic_summary_chunk":
                if any(k in text for k in ["540", "60", "expires", "expiry", "expire", "prod", "token", "non-prod", "nonprod"]):
                    chunk_type_boost += 1.25
                    labels.append("token_expiry_semantic_boost")
            elif chunk_type == "authentication_chunk":
                if any(k in text for k in ["540", "60", "expires", "expiry", "expire", "prod", "token", "non-prod", "nonprod"]):
                    chunk_type_boost += 0.45
                    labels.append("token_expiry_authentication_chunk")

        if "request_structure_intent" in intents:
            if chunk_type in {
                "api_semantic_summary_chunk",
                "api_table_flattened_chunk",
                "api_sample_request_chunk",
                "api_query_parameters_chunk",
                "api_request_parameters_chunk",
            }:
                chunk_type_boost += 0.44
                labels.append("request_structure_boost")

        if "overview_intent" in intents:
            if chunk_type in {"document_overview_chunk", "generic_section_chunk"}:
                chunk_type_boost += 0.30
                labels.append("overview_chunk_type")

        if "timeslotcategory" in question.lower():
            if "timeslotcategory" in text and any(token in text for token in ["failed response", "returncode", "returnmsg", "incorrect"]):
                metadata_boost += 0.9
                labels.append("timeslot_error_focus")

        if chunk_type in {"raw_fallback_chunk", "integration_flow_chunk", "endpoint_sample_chunk"}:
            chunk_type_boost -= 0.2
            labels.append("legacy_chunk_penalty")

        metadata_boost = max(min(metadata_boost, 1.5), -0.2)
        chunk_type_boost = max(min(chunk_type_boost, 1.2), -1.15)
        return metadata_boost, chunk_type_boost, labels

    def _metadata_coverage_ratio(self, candidates: list[dict[str, Any]]) -> float:
        if not candidates:
            return 0.0
        covered = 0
        for item in candidates:
            if any(
                item.get(field) not in (None, "")
                for field in ("product_name", "section_title", "api_reference_id", "service_name")
            ):
                covered += 1
        return covered / len(candidates)

    def _vector_confidence_bucket(self, *, top_vector_score: float, vector_results_count: int, top_k: int) -> str:
        if vector_results_count >= top_k and top_vector_score >= 0.45:
            return "high"
        if vector_results_count >= max(2, top_k // 2) and top_vector_score >= 0.25:
            return "medium"
        return "low"

    def fallback_keyword_search(
        self,
        project_id: int,
        knowledge_base_id: int,
        question: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        terms = self._tokenize(question)
        if not terms:
            return []

        with SessionLocal() as db:
            query_result = db.execute(
                text(
                    """
                    SELECT
                        dc.chunk_text,
                        dc.chunk_type,
                        d.id AS document_id,
                        d.file_name,
                        d.document_type,
                        d.source_domain,
                        d.product_name,
                        d.document_version,
                        d.uploaded_at,
                        d.ingestion_run_id,
                        d.is_active_document,
                        d.knowledge_base_id,
                        kb.name AS knowledge_base_name,
                        e.api_reference_id,
                        e.service_name,
                        e.service_group,
                        e.service_description,
                        e.service_method,
                        e.service_pattern
                    FROM document_chunks dc
                    JOIN api_documents d ON d.id = dc.document_id
                    LEFT JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
                    LEFT JOIN api_endpoints e ON e.id = dc.endpoint_id
                    WHERE d.project_id = :project_id
                      AND d.knowledge_base_id = :knowledge_base_id
                      AND (d.is_active_document IS NULL OR d.is_active_document IS TRUE)
                      AND (
                        LOWER(COALESCE(dc.chunk_text, '')) LIKE ANY(:like_terms)
                        OR LOWER(COALESCE(e.api_reference_id, '')) LIKE ANY(:like_terms)
                        OR LOWER(COALESCE(e.service_name, '')) LIKE ANY(:like_terms)
                        OR LOWER(COALESCE(e.service_description, '')) LIKE ANY(:like_terms)
                        OR LOWER(COALESCE(e.service_method, '')) LIKE ANY(:like_terms)
                        OR LOWER(COALESCE(e.service_pattern, '')) LIKE ANY(:like_terms)
                        OR LOWER(COALESCE(d.file_name, '')) LIKE ANY(:like_terms)
                      )
                    """
                ),
                {
                    "project_id": project_id,
                    "knowledge_base_id": knowledge_base_id,
                    "like_terms": [f"%{term}%" for term in terms],
                },
            )
            rows = query_result.mappings().all()

        scored: list[dict[str, Any]] = []
        for row in rows:
            row_dict = dict(row)
            score = self._fallback_score(row_dict, terms)
            if score <= 0:
                continue
            scored.append(
                {
                    "score": float(score),
                    "chunk_type": row_dict.get("chunk_type"),
                    "section_title": None,
                    "api_reference_id": row_dict.get("api_reference_id"),
                    "service_name": row_dict.get("service_name"),
                    "service_group": row_dict.get("service_group"),
                    "service_method": row_dict.get("service_method"),
                    "service_pattern": row_dict.get("service_pattern"),
                    "file_name": row_dict.get("file_name"),
                    "document_type": row_dict.get("document_type"),
                    "source_domain": row_dict.get("source_domain"),
                    "product_name": row_dict.get("product_name"),
                    "document_version": row_dict.get("document_version"),
                    "chunk_text": row_dict.get("chunk_text"),
                    "knowledge_base_id": row_dict.get("knowledge_base_id"),
                    "knowledge_base_name": row_dict.get("knowledge_base_name"),
                    "document_id": row_dict.get("document_id"),
                    "upload_timestamp": row_dict.get("uploaded_at").isoformat()
                    if row_dict.get("uploaded_at") is not None and hasattr(row_dict.get("uploaded_at"), "isoformat")
                    else None,
                    "ingestion_run_id": row_dict.get("ingestion_run_id"),
                    "is_active_document": row_dict.get("is_active_document")
                    if row_dict.get("is_active_document") is not None
                    else True,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def get_vector_count(self) -> int:
        return qdrant_service.collection_point_count()

    def _tokenize(self, question: str) -> list[str]:
        return [token for token in re.findall(r"[a-zA-Z0-9_]+", question.lower()) if len(token) > 1]

    def _fallback_score(self, row: dict[str, Any], terms: list[str]) -> float:
        chunk_text = (row.get("chunk_text") or "").lower()
        service_name = (row.get("service_name") or "").lower()
        api_reference_id = (row.get("api_reference_id") or "").lower()
        service_description = (row.get("service_description") or "").lower()
        service_method = (row.get("service_method") or "").lower()
        service_pattern = (row.get("service_pattern") or "").lower()
        file_name = (row.get("file_name") or "").lower()
        chunk_type = (row.get("chunk_type") or "").lower()

        score = 0.0
        searchable = " ".join(
            [
                chunk_text,
                service_name,
                api_reference_id,
                service_description,
                service_method,
                service_pattern,
                file_name,
            ]
        )
        for term in terms:
            if term in searchable:
                score += 1.0
            if term in service_name:
                score += 1.25
            if term in api_reference_id:
                score += 1.5
        if chunk_type in {"endpoint_summary_chunk", "api_metadata_chunk", "api_overview_chunk"}:
            score += 1.0
        param_hint_terms = {
            "mandatory",
            "required",
            "request",
            "parameter",
            "parameters",
            "input",
            "payload",
            "body",
            "fields",
        }
        if chunk_type == "api_request_parameters_chunk" and param_hint_terms.intersection(set(terms)):
            score += 2.8
        return score


retrieval_service = RetrievalService()
