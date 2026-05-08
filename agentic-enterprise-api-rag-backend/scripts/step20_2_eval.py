from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.database import SessionLocal
from app.services.embedding_service import embedding_service
from app.services.qdrant_client import qdrant_service
from app.services.rag_service import rag_service
from app.services.retrieval_service import retrieval_service


QUERY_SET: list[dict[str, Any]] = [
    {"kb": 1, "category": "api_lookup", "q": "API-REST-NOK-01 endpoint details"},
    {"kb": 1, "category": "api_lookup", "q": "API-REST-SAC-01 method and pattern"},
    {"kb": 1, "category": "api_semantic", "q": "What is the endpoint for claims status API?"},
    {"kb": 1, "category": "api_semantic", "q": "How can I submit order creation request?"},
    {"kb": 1, "category": "mixed_semantic", "q": "Which API is used for claims portal order update flow?"},
    {"kb": 1, "category": "api_workflow", "q": "Explain the integration flow for order service."},
    {"kb": 1, "category": "api_lookup", "q": "Unknown Service APIs in KK-Order-Service_v0.1.docx"},
    {"kb": 2, "category": "product_workflow", "q": "How do I configure notifications in Claims Portal workflow?"},
    {"kb": 2, "category": "product_workflow", "q": "How do users start a new claim in Claims Portal?"},
    {"kb": 2, "category": "product_semantic", "q": "Claims Portal section about approval steps"},
    {"kb": 2, "category": "product_semantic", "q": "Where is Claims Portal test doc section guidance?"},
    {"kb": 2, "category": "mixed_semantic", "q": "Claims Portal API integration prerequisites"},
    {"kb": 2, "category": "product_lookup", "q": "Claims Portal v20.1-openai content"},
    {"kb": 2, "category": "product_workflow", "q": "Workflow to validate order before submission"},
    {"kb": 2, "category": "product_semantic", "q": "Section title for notifications in product docs"},
]


def _top_source_signature(item: dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("file_name") or ""),
            str(item.get("document_type") or ""),
            str(item.get("product_name") or ""),
            str(item.get("section_title") or ""),
            str(item.get("api_reference_id") or ""),
            str(item.get("service_name") or ""),
            str(item.get("chunk_type") or ""),
        ]
    )


async def _baseline_retrieve(project_id: int, knowledge_base_id: int, question: str, top_k: int) -> dict[str, Any]:
    collection_exists = qdrant_service.collection_exists()
    vectors_count = qdrant_service.collection_point_count() if collection_exists else 0
    if vectors_count == 0:
        return {
            "retrieval_mode": "db_keyword_fallback",
            "results": retrieval_service.fallback_keyword_search(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            ),
            "vector_results_count": 0,
            "fallback_triggered": True,
            "hybrid_fusion_used": False,
        }

    try:
        embedding = await embedding_service.embed_text(question)
    except Exception:
        return {
            "retrieval_mode": "db_keyword_fallback",
            "results": retrieval_service.fallback_keyword_search(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            ),
            "vector_results_count": 0,
            "fallback_triggered": True,
            "hybrid_fusion_used": False,
        }

    try:
        hits = qdrant_service.search_points(embedding, max(top_k, 1))
    except Exception:
        return {
            "retrieval_mode": "db_keyword_fallback",
            "results": retrieval_service.fallback_keyword_search(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            ),
            "vector_results_count": 0,
            "fallback_triggered": True,
            "hybrid_fusion_used": False,
        }

    if not hits:
        return {
            "retrieval_mode": "vector",
            "results": [],
            "vector_results_count": 0,
            "fallback_triggered": False,
            "hybrid_fusion_used": False,
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

    results: list[dict[str, Any]] = []
    for hit in hits:
        point_id = str(hit.id)
        row = rows_by_point.get(point_id)
        if not row:
            continue
        if row.get("project_id") != project_id or row.get("knowledge_base_id") != knowledge_base_id:
            continue
        payload = hit.payload or {}
        metadata = payload.get("metadata") or {}
        results.append(
            {
                "score": float(hit.score),
                "chunk_text": payload.get("chunk_text"),
                "chunk_type": payload.get("chunk_type"),
                "section_title": metadata.get("section_title"),
                "document_id": row.get("document_id"),
                "endpoint_id": row.get("endpoint_id"),
                "api_reference_id": row.get("api_reference_id") or metadata.get("api_reference_id"),
                "service_name": row.get("service_name") or metadata.get("service_name"),
                "service_group": row.get("service_group") or metadata.get("service_group"),
                "service_method": row.get("service_method") or metadata.get("service_method"),
                "service_pattern": row.get("service_pattern") or metadata.get("service_pattern"),
                "file_name": row.get("file_name"),
                "document_type": row.get("document_type"),
                "source_domain": row.get("source_domain"),
                "product_name": row.get("product_name"),
                "document_version": row.get("document_version"),
                "knowledge_base_id": row.get("knowledge_base_id"),
                "knowledge_base_name": row.get("knowledge_base_name"),
            }
        )
        if len(results) >= top_k:
            break

    return {
        "retrieval_mode": "vector",
        "results": results,
        "vector_results_count": len(results),
        "fallback_triggered": False,
        "hybrid_fusion_used": False,
    }


async def _current_retrieve(project_id: int, knowledge_base_id: int, question: str, top_k: int) -> dict[str, Any]:
    return await retrieval_service.retrieve(
        project_id=project_id,
        knowledge_base_id=knowledge_base_id,
        question=question,
        top_k=top_k,
    )


async def run_eval(provider: str = "openai", top_k: int = 5) -> dict[str, Any]:
    os.environ["EMBEDDING_PROVIDER"] = provider
    os.environ["LLM_PROVIDER"] = provider
    settings.EMBEDDING_PROVIDER = provider
    settings.LLM_PROVIDER = provider

    rows: list[dict[str, Any]] = []
    baseline_fallback = 0
    current_fallback = 0
    hybrid_activated = 0
    moved_top1 = 0

    for item in QUERY_SET:
        project_id = 1
        kb_id = item["kb"]
        question = item["q"]

        baseline = await _baseline_retrieve(project_id=project_id, knowledge_base_id=kb_id, question=question, top_k=top_k)
        current = await _current_retrieve(project_id=project_id, knowledge_base_id=kb_id, question=question, top_k=top_k)

        baseline_results = baseline.get("results", []) or []
        current_results = current.get("results", []) or []
        diagnostics = current.get("vector_retrieval_diagnostics", {}) or {}

        b_top1 = _top_source_signature(baseline_results[0]) if baseline_results else ""
        c_top1 = _top_source_signature(current_results[0]) if current_results else ""
        top1_changed = bool(b_top1 and c_top1 and b_top1 != c_top1)
        if top1_changed:
            moved_top1 += 1

        baseline_fallback += 1 if baseline.get("fallback_triggered") else 0
        current_fallback += 1 if diagnostics.get("fallback_triggered") else 0
        hybrid_activated += 1 if diagnostics.get("hybrid_fusion_used") else 0

        answer = await rag_service.answer_question(
            project_id=project_id,
            knowledge_base_id=kb_id,
            question=question,
            top_k=top_k,
            debug=True,
        )
        answer_text = (answer.get("answer") or "").strip()
        answer_quality = "grounded"
        if answer_text == "I could not find enough information in the uploaded API documentation.":
            answer_quality = "insufficient_context"
        elif len(answer_text) < 40:
            answer_quality = "weak_short"

        rows.append(
            {
                "kb": kb_id,
                "category": item["category"],
                "question": question,
                "baseline_mode": baseline.get("retrieval_mode"),
                "after_mode": current.get("retrieval_mode"),
                "baseline_vector_results_count": baseline.get("vector_results_count"),
                "after_vector_results_count": diagnostics.get("vector_results_count"),
                "hybrid_fusion_used": diagnostics.get("hybrid_fusion_used"),
                "fallback_triggered_after": diagnostics.get("fallback_triggered"),
                "top1_changed": top1_changed,
                "baseline_top_sources": [_top_source_signature(x) for x in baseline_results[:3]],
                "after_top_sources": [_top_source_signature(x) for x in current_results[:3]],
                "answer_quality": answer_quality,
            }
        )

    return {
        "provider": provider,
        "query_count": len(QUERY_SET),
        "baseline_fallback_count": baseline_fallback,
        "after_fallback_count": current_fallback,
        "hybrid_activation_count": hybrid_activated,
        "top1_changed_count": moved_top1,
        "rows": rows,
    }


async def main() -> None:
    provider = os.environ.get("STEP202_PROVIDER", "openai").strip().lower()
    result = await run_eval(provider=provider)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
