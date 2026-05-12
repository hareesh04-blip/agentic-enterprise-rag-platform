from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import check_knowledge_base_access, require_admin_or_super_admin
from app.db.database import get_db
from app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/diagnostics")


class RetrievalTestRequest(BaseModel):
    knowledge_base_id: int = Field(..., ge=1)
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)


def _ensure_kb_readable_for_admin_test(
    *,
    db: Session,
    user_id: int,
    knowledge_base_id: int,
) -> None:
    kb = db.execute(
        text("SELECT id, is_active FROM knowledge_bases WHERE id = :kb_id"),
        {"kb_id": knowledge_base_id},
    ).mappings().first()
    if kb is None or not kb["is_active"]:
        raise HTTPException(status_code=404, detail="Knowledge base not found or inactive")

    role_names = db.execute(
        text(
            """
            SELECT r.name
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).scalars().all()
    permissions = set(
        db.execute(
            text(
                """
                SELECT DISTINCT p.code
                FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).scalars().all()
    )
    if "super_admin" in role_names or "knowledge_bases.manage" in permissions:
        return
    if not check_knowledge_base_access(
        db=db,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        access_level="read",
    ):
        raise HTTPException(status_code=403, detail="Knowledge base access denied")


def _resolve_project_id_for_kb(db: Session, knowledge_base_id: int) -> int:
    row = db.execute(
        text(
            """
            SELECT DISTINCT d.project_id
            FROM api_documents d
            WHERE d.knowledge_base_id = :knowledge_base_id
            LIMIT 1
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    ).mappings().first()
    if row is None or row.get("project_id") is None:
        raise HTTPException(
            status_code=400,
            detail="Knowledge base has no documents; cannot resolve project for retrieval test.",
        )
    return int(row["project_id"])


def _aggregate_from_results(results: list[dict[str, Any]], knowledge_base_id: int) -> dict[str, Any]:
    document_type_counts = Counter((item.get("document_type") or "unknown") for item in results)
    product_counts = Counter((item.get("product_name") or "N/A") for item in results)
    section_titles = {item.get("section_title") for item in results if item.get("section_title")}
    dominant_document_type = document_type_counts.most_common(1)[0][0] if document_type_counts else "unknown"
    dominant_product_name = product_counts.most_common(1)[0][0] if product_counts else None
    return {
        "retrieved_chunk_count": len(results),
        "dominant_document_type": dominant_document_type,
        "dominant_product_name": None if dominant_product_name == "N/A" else dominant_product_name,
        "section_coverage_count": len(section_titles),
        "kb_match_verified": all(item.get("knowledge_base_id") == knowledge_base_id for item in results)
        if results
        else True,
    }


def _resolve_chunk_id(
    db: Session,
    *,
    knowledge_base_id: int,
    document_id: int | None,
    chunk_type: str | None,
    chunk_text: str | None,
) -> str:
    if document_id is None or not chunk_text:
        return ""
    params: dict[str, Any] = {
        "kb_id": knowledge_base_id,
        "document_id": document_id,
        "chunk_text": chunk_text,
    }
    if chunk_type:
        sql = """
            SELECT dc.id
            FROM document_chunks dc
            JOIN api_documents ad ON ad.id = dc.document_id
            WHERE ad.knowledge_base_id = :kb_id
              AND dc.document_id = :document_id
              AND dc.chunk_type = :chunk_type
              AND dc.chunk_text = :chunk_text
            LIMIT 1
            """
        params["chunk_type"] = chunk_type
    else:
        sql = """
            SELECT dc.id
            FROM document_chunks dc
            JOIN api_documents ad ON ad.id = dc.document_id
            WHERE ad.knowledge_base_id = :kb_id
              AND dc.document_id = :document_id
              AND dc.chunk_text = :chunk_text
            LIMIT 1
            """
    row = db.execute(text(sql), params).scalar()
    return str(row) if row is not None else ""


def _build_chunks_payload(
    db: Session,
    *,
    knowledge_base_id: int,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for idx, item in enumerate(results, start=1):
        text_body = (item.get("chunk_text") or "").strip()
        preview = text_body[:320] + ("…" if len(text_body) > 320 else "")
        cid = _resolve_chunk_id(
            db,
            knowledge_base_id=knowledge_base_id,
            document_id=item.get("document_id"),
            chunk_type=item.get("chunk_type"),
            chunk_text=item.get("chunk_text"),
        )
        chunks.append(
            {
                "rank": idx,
                "document_id": item.get("document_id"),
                "document_name": item.get("file_name") or "",
                "chunk_id": cid or None,
                "chunk_type": item.get("chunk_type"),
                "document_type": item.get("document_type"),
                "product_name": item.get("product_name"),
                "section_title": item.get("section_title"),
                "score": float(item.get("score") or 0.0),
                "content_preview": preview or "",
            }
        )
    return chunks


@router.post("/retrieval-test")
async def retrieval_test(
    payload: RetrievalTestRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    """
    Admin/super-admin only: run retrieval for a KB without LLM generation (diagnostics console).
    """
    _ensure_kb_readable_for_admin_test(
        db=db,
        user_id=int(current_user["id"]),
        knowledge_base_id=payload.knowledge_base_id,
    )
    project_id = _resolve_project_id_for_kb(db, payload.knowledge_base_id)

    retrieval_data = await retrieval_service.retrieve(
        project_id=project_id,
        knowledge_base_id=payload.knowledge_base_id,
        question=payload.question.strip(),
        top_k=payload.top_k,
    )
    results = list(retrieval_data.get("results") or [])
    agg = _aggregate_from_results(results, payload.knowledge_base_id)
    chunks = _build_chunks_payload(db, knowledge_base_id=payload.knowledge_base_id, results=results)

    diagnostics = retrieval_data.get("vector_retrieval_diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    diagnostics = {
        **diagnostics,
        "retrieval_mode": retrieval_data.get("retrieval_mode"),
        "retrieval_notice": retrieval_data.get("message"),
    }

    return {
        "knowledge_base_id": payload.knowledge_base_id,
        "question": payload.question.strip(),
        "retrieval_mode": retrieval_data.get("retrieval_mode") or "unknown",
        "retrieved_chunk_count": agg["retrieved_chunk_count"],
        "dominant_document_type": agg["dominant_document_type"],
        "dominant_product_name": agg["dominant_product_name"],
        "section_coverage_count": agg["section_coverage_count"],
        "chunks": chunks,
        "diagnostics": diagnostics,
    }
