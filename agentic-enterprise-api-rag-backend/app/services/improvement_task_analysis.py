from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.openai_client import openai_client
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

RecommendedAction = str  # update_kb_content | improve_prompt | improve_retrieval | mark_as_unclear


def _promptish_comment(comment: str) -> bool:
    c = comment.lower()
    keys = (
        "prompt",
        "hallucin",
        "wrong answer",
        "not accurate",
        "misleading",
        "tone",
        "format",
        "doesn't follow",
        "ignored",
        "instruction",
    )
    return any(k in c for k in keys)


def _pick_action_and_reason(
    *,
    has_linked_negative: bool,
    comment: str | None,
    question: str,
    chunk_count: int | None,
    include_retrieval: bool,
    retrieval_error: str | None,
) -> tuple[RecommendedAction, str]:
    q = (question or "").strip()
    c = (comment or "").strip()

    if include_retrieval and retrieval_error:
        return (
            "mark_as_unclear",
            f"Retrieval test did not complete successfully: {retrieval_error}. "
            "Resolve access or KB configuration, then re-run analysis.",
        )

    if include_retrieval and chunk_count is not None:
        if chunk_count == 0:
            return (
                "improve_retrieval",
                "Diagnostics retrieval returned no chunks for this question in the selected knowledge base. "
                "Indexing, hybrid settings, or query-to-chunk alignment may need attention before changing prompts.",
            )
        if has_linked_negative:
            if not c:
                return (
                    "mark_as_unclear",
                    "Thumbs-down feedback was recorded without a comment while retrieval did return chunks. "
                    "The issue may be answer quality, missing KB facts, or prompt behavior—clarify with the user before picking a single fix.",
                )
            if _promptish_comment(c):
                return (
                    "improve_prompt",
                    "Retrieval returned relevant-looking chunks and the user comment suggests the model response or prompt behavior is at fault.",
                )
            return (
                "update_kb_content",
                "Chunks were retrieved for the question but the user still rated the answer negatively with a substantive comment—likely gaps or errors in source material.",
            )
        return (
            "update_kb_content",
            "Retrieval returned chunks for this task question. Review whether documentation or chunk boundaries should be updated.",
        )

    if has_linked_negative and not c:
        return (
            "mark_as_unclear",
            "Linked negative feedback has no user comment and no retrieval test was run; run analysis with retrieval test or gather more detail.",
        )
    if has_linked_negative:
        if _promptish_comment(c):
            return "improve_prompt", "User comment (without live retrieval in this run) suggests prompt or generation issues."
        return "update_kb_content", "User comment suggests factual or coverage gaps in the knowledge base content."

    return (
        "mark_as_unclear",
        "This task is not linked to thumbs-down feedback. Run a retrieval test or attach feedback to narrow the remediation path.",
    )


def _suggested_kb_update(action: RecommendedAction, question: str, chunk_count: int | None) -> str:
    q = (question or "").strip()[:240]
    if action == "improve_retrieval":
        return (
            "Verify documents are ingested for this KB, confirm chunk metadata (knowledge_base_id) matches, "
            "and review hybrid / keyword / vector weights for this query class. "
            f"Example query to trace: {q!r}"
        )
    if action == "improve_prompt":
        return (
            "Review RAG answer prompts and post-retrieval instructions for this domain; add guardrails for "
            "unsupported claims and align tone with enterprise standards. "
            f"Anchor question: {q!r}"
        )
    if action == "update_kb_content":
        return (
            "Locate authoritative sources for the user question, update or add documents, re-run ingestion, "
            "and validate chunk boundaries around the missing fact. "
            f"Anchor question: {q!r}"
        )
    return (
        "Collect a short user comment or reproduction steps, then re-run analysis with retrieval test enabled. "
        f"Question snapshot: {q!r}"
    )


def _suggested_test_questions(question: str) -> list[str]:
    q = (question or "").strip()
    if not q:
        return [
            "What is the expected behavior for this workflow?",
            "List the prerequisites and API steps involved.",
            "What error codes or edge cases apply?",
        ]
    return [
        f"Re-run verbatim: {q}",
        f"Ask a narrower variant focusing on one entity mentioned in: {q[:120]}",
        f"Follow-up: what inputs or headers are required for: {q[:100]}",
    ]


async def _maybe_llm_refine_reasoning(heuristic_summary: str, action: str, question: str) -> str:
    if not settings.ENABLE_IMPROVEMENT_LLM_ANALYSIS:
        return heuristic_summary
    if not settings.OPENAI_API_KEY:
        logger.info("ENABLE_IMPROVEMENT_LLM_ANALYSIS is on but OPENAI_API_KEY is unset; skipping LLM refinement.")
        return heuristic_summary
    prompt = (
        "You are assisting an admin triaging an internal RAG improvement task. "
        "Given the heuristic classification and notes, add at most 2 short sentences of practical guidance. "
        "Do not invent product facts. Stay under 120 words total including the original summary.\n\n"
        f"Heuristic action: {action}\n"
        f"User question (truncated): {question[:500]!r}\n"
        f"Heuristic summary:\n{heuristic_summary}\n"
    )
    try:
        extra = await openai_client.generate(prompt)
        if extra:
            return f"{heuristic_summary}\n\nLLM refinement:\n{extra.strip()}"
    except Exception as exc:
        logger.warning("Improvement LLM refinement failed: %s", exc)
    return heuristic_summary


async def _run_retrieval_test_summary(
    db: Session,
    *,
    user_id: int,
    knowledge_base_id: int,
    question: str,
    top_k: int = 6,
) -> dict[str, Any]:
    from app.api.v1.endpoints.diagnostics import (
        _aggregate_from_results,
        _build_chunks_payload,
        _ensure_kb_readable_for_admin_test,
        _resolve_project_id_for_kb,
    )

    try:
        _ensure_kb_readable_for_admin_test(
            db=db,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )
        project_id = _resolve_project_id_for_kb(db, knowledge_base_id)
    except HTTPException as exc:
        return {
            "error": str(exc.detail),
            "knowledge_base_id": knowledge_base_id,
            "question": question.strip(),
            "retrieved_chunk_count": 0,
            "retrieval_mode": None,
        }

    retrieval_data = await retrieval_service.retrieve(
        project_id=project_id,
        knowledge_base_id=knowledge_base_id,
        question=question.strip(),
        top_k=top_k,
    )
    results = list(retrieval_data.get("results") or [])
    agg = _aggregate_from_results(results, knowledge_base_id)
    chunks = _build_chunks_payload(db, knowledge_base_id=knowledge_base_id, results=results)

    diagnostics = retrieval_data.get("vector_retrieval_diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    diagnostics = {
        **diagnostics,
        "retrieval_mode": retrieval_data.get("retrieval_mode"),
        "retrieval_notice": retrieval_data.get("message"),
    }

    top_types = []
    for ch in chunks[:5]:
        ct = ch.get("chunk_type")
        if ct and ct not in top_types:
            top_types.append(str(ct))

    return {
        "knowledge_base_id": knowledge_base_id,
        "question": question.strip(),
        "retrieval_mode": retrieval_data.get("retrieval_mode") or "unknown",
        "retrieved_chunk_count": agg["retrieved_chunk_count"],
        "dominant_document_type": agg["dominant_document_type"],
        "dominant_product_name": agg["dominant_product_name"],
        "section_coverage_count": agg["section_coverage_count"],
        "kb_match_verified": agg["kb_match_verified"],
        "top_chunk_types": top_types,
        "chunks_sample": chunks[:3],
        "diagnostics": diagnostics,
    }


def _fetch_task_analysis_row(db: Session, task_id: int) -> dict[str, Any] | None:
    return db.execute(
        text(
            """
            SELECT
              t.id,
              t.title,
              t.description,
              t.knowledge_base_id,
              t.feedback_id,
              qf.question_text AS qf_question,
              qf.answer_text AS qf_answer,
              qf.comment AS qf_comment,
              qf.rating AS qf_rating
            FROM improvement_tasks t
            LEFT JOIN query_feedback qf ON qf.id = t.feedback_id
            WHERE t.id = :tid
            """
        ),
        {"tid": task_id},
    ).mappings().first()


async def run_improvement_task_analysis(
    db: Session,
    *,
    user_id: int,
    task_id: int,
    include_retrieval_test: bool,
) -> dict[str, Any]:
    row = _fetch_task_analysis_row(db, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    kb_id = int(row["knowledge_base_id"])
    has_fb = row["feedback_id"] is not None
    qf_q = row["qf_question"]
    qf_a = row["qf_answer"] or ""
    qf_c = row["qf_comment"]
    qf_rating = row["qf_rating"]

    if has_fb and qf_q:
        question = str(qf_q).strip()
        answer_preview = (str(qf_a) or "")[:400] + ("…" if len(str(qf_a) or "") > 400 else "")
        comment = str(qf_c).strip() if qf_c else None
        has_linked_negative = str(qf_rating or "") == "thumbs_down"
    else:
        question = str(row["title"] or "").strip() or (row["description"] or "")[:500]
        answer_preview = ""
        comment = None
        has_linked_negative = False

    retrieval_test: dict[str, Any] | None = None
    chunk_count: int | None = None
    retrieval_error: str | None = None

    if include_retrieval_test:
        retrieval_test = await _run_retrieval_test_summary(
            db,
            user_id=user_id,
            knowledge_base_id=kb_id,
            question=question or " ",
            top_k=6,
        )
        err = retrieval_test.get("error")
        if err:
            retrieval_error = str(err)
            chunk_count = None
        else:
            chunk_count = int(retrieval_test.get("retrieved_chunk_count") or 0)

    action, heuristic_reason = _pick_action_and_reason(
        has_linked_negative=has_linked_negative,
        comment=comment,
        question=question,
        chunk_count=chunk_count,
        include_retrieval=include_retrieval_test,
        retrieval_error=retrieval_error,
    )

    parts = [heuristic_reason]
    if has_fb:
        parts.append(f"Linked feedback rating: {qf_rating}.")
        if answer_preview:
            parts.append(f"Answer snapshot: {answer_preview[:280]!r}")
        if comment:
            parts.append(f"User comment: {comment[:400]!r}")
    else:
        parts.append("No linked query_feedback row; using task title/description as the working question.")

    reasoning = " ".join(parts)
    reasoning = await _maybe_llm_refine_reasoning(reasoning, action, question)

    suggested_kb = _suggested_kb_update(action, question, chunk_count)
    questions = _suggested_test_questions(question)

    if not include_retrieval_test:
        retrieval_test = None

    return {
        "task_id": task_id,
        "recommended_action": action,
        "reasoning_summary": reasoning,
        "suggested_kb_update": suggested_kb,
        "suggested_test_questions": questions,
        "retrieval_test": retrieval_test,
    }
