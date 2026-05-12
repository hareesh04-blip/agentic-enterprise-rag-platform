"""
KB-scoped test data cleanup for ingestion/query E2E resets.

Does not delete users, roles, permissions, or knowledge_bases rows.
Demo seed feedback/tasks are skipped unless ``include_demo_seed`` is true.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services.demo_data_service import SEED_MARKER
from app.services.qdrant_client import qdrant_service

logger = logging.getLogger(__name__)

SEED_LIKE = f"%{SEED_MARKER}%"


@dataclass
class CleanupFlags:
    knowledge_base_id: int
    delete_documents: bool
    delete_vectors: bool
    delete_chat_sessions: bool
    delete_feedback: bool
    delete_improvement_tasks: bool
    include_demo_seed: bool
    delete_audit_logs: bool
    dry_run: bool


def _ensure_kb_exists(db: Session, kb_id: int) -> None:
    row = db.execute(text("SELECT id FROM knowledge_bases WHERE id = :id"), {"id": kb_id}).scalar()
    if row is None:
        raise ValueError(f"Knowledge base {kb_id} not found")


def _document_ids_for_kb(db: Session, kb_id: int) -> list[int]:
    rows = db.execute(
        text("SELECT id FROM api_documents WHERE knowledge_base_id = :kb_id ORDER BY id"),
        {"kb_id": kb_id},
    ).fetchall()
    return [int(r[0]) for r in rows]


def _collect_point_ids(db: Session, document_ids: list[int]) -> list[str]:
    if not document_ids:
        return []
    stmt = (
        text(
            """
            SELECT DISTINCT qdrant_point_id
            FROM document_chunks
            WHERE document_id IN :ids
              AND qdrant_point_id IS NOT NULL
              AND qdrant_point_id <> ''
            """
        )
        .bindparams(bindparam("ids", expanding=True))
    )
    rows = db.execute(stmt, {"ids": document_ids}).fetchall()
    return [str(r[0]) for r in rows if r[0]]


def _delete_qdrant_points(point_ids: list[str]) -> int:
    if not point_ids:
        return 0
    if not qdrant_service.collection_exists():
        return 0
    collection = qdrant_service._active_collection_name()
    deleted = 0
    batch_size = 128
    from qdrant_client.models import PointIdsList

    for i in range(0, len(point_ids), batch_size):
        batch = point_ids[i : i + batch_size]
        qdrant_service.client.delete(
            collection_name=collection,
            wait=True,
            points_selector=PointIdsList(points=batch),
        )
        deleted += len(batch)
    return deleted


def _count_feedback_to_delete(db: Session, kb_id: int, include_demo_seed: bool) -> int:
    if include_demo_seed:
        return int(
            db.execute(
                text("SELECT COUNT(*) FROM query_feedback WHERE knowledge_base_id = :kb_id"),
                {"kb_id": kb_id},
            ).scalar_one()
        )
    return int(
        db.execute(
            text("SELECT COUNT(*) FROM query_feedback WHERE knowledge_base_id = :kb_id AND question_text NOT LIKE :sl"),
            {"kb_id": kb_id, "sl": SEED_LIKE},
        ).scalar_one()
    )


def _count_tasks_to_delete(db: Session, kb_id: int, flags: CleanupFlags) -> int:
    if not flags.delete_improvement_tasks:
        return 0
    if flags.delete_feedback:
        if flags.include_demo_seed:
            return int(
                db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM improvement_tasks t
                        WHERE t.knowledge_base_id = :kb_id
                          AND (
                            t.feedback_id IN (
                              SELECT qf.id FROM query_feedback qf
                              WHERE qf.knowledge_base_id = :kb_id
                            )
                            OR t.title LIKE :sl
                          )
                        """
                    ),
                    {"kb_id": kb_id, "sl": SEED_LIKE},
                ).scalar_one()
            )
        return int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM improvement_tasks t
                    WHERE t.knowledge_base_id = :kb_id
                      AND (
                        t.feedback_id IN (
                          SELECT qf.id FROM query_feedback qf
                          WHERE qf.knowledge_base_id = :kb_id
                            AND qf.question_text NOT LIKE :sl
                        )
                      )
                    """
                ),
                {"kb_id": kb_id, "sl": SEED_LIKE},
            ).scalar_one()
        )
    if flags.include_demo_seed:
        return int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM improvement_tasks t
                    WHERE t.knowledge_base_id = :kb_id AND t.title LIKE :sl
                    """
                ),
                {"kb_id": kb_id, "sl": SEED_LIKE},
            ).scalar_one()
        )
    return 0


def _count_audit_to_delete(db: Session, kb_id: int, include_demo_seed: bool) -> int:
    if include_demo_seed:
        return int(
            db.execute(
                text("SELECT COUNT(*) FROM audit_logs WHERE knowledge_base_id = :kb_id"),
                {"kb_id": kb_id},
            ).scalar_one()
        )
    return int(
        db.execute(
            text(
                """
                SELECT COUNT(*) FROM audit_logs
                WHERE knowledge_base_id = :kb_id
                  AND (metadata_json->>'source' IS DISTINCT FROM 'DEMO_SEED_42')
                """
            ),
            {"kb_id": kb_id},
        ).scalar_one()
    )


def plan_and_execute(db: Session, flags: CleanupFlags) -> dict[str, Any]:
    _ensure_kb_exists(db, flags.knowledge_base_id)
    kb_id = flags.knowledge_base_id
    doc_ids = _document_ids_for_kb(db, kb_id)

    documents_found = len(doc_ids)
    chunks_found = int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM document_chunks dc "
                "JOIN api_documents d ON d.id = dc.document_id "
                "WHERE d.knowledge_base_id = :kb_id"
            ),
            {"kb_id": kb_id},
        ).scalar_one()
    )
    point_ids = _collect_point_ids(db, doc_ids)
    vectors_found = len(point_ids)

    ingestion_jobs_found = int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM ingestion_jobs ij "
                "JOIN api_documents d ON d.id = ij.document_id "
                "WHERE d.knowledge_base_id = :kb_id"
            ),
            {"kb_id": kb_id},
        ).scalar_one()
    )

    chat_sessions_found = int(
        db.execute(
            text("SELECT COUNT(*) FROM chat_sessions WHERE knowledge_base_id = :kb_id"),
            {"kb_id": kb_id},
        ).scalar_one()
    )
    chat_messages_found = int(
        db.execute(
            text(
                """
                SELECT COUNT(*) FROM chat_messages cm
                JOIN chat_sessions cs ON cs.id = cm.session_id
                WHERE cs.knowledge_base_id = :kb_id
                """
            ),
            {"kb_id": kb_id},
        ).scalar_one()
    )

    feedback_found = _count_feedback_to_delete(db, kb_id, flags.include_demo_seed) if flags.delete_feedback else 0
    tasks_found = _count_tasks_to_delete(db, kb_id, flags) if flags.delete_improvement_tasks else 0
    audit_logs_found = _count_audit_to_delete(db, kb_id, flags.include_demo_seed) if flags.delete_audit_logs else 0

    will_delete = {
        "documents": documents_found if flags.delete_documents else 0,
        "chunks": chunks_found if flags.delete_documents else 0,
        "vectors": vectors_found if flags.delete_vectors else 0,
        "ingestion_jobs": ingestion_jobs_found if flags.delete_documents else 0,
        "chat_sessions": chat_sessions_found if flags.delete_chat_sessions else 0,
        "chat_messages": chat_messages_found if flags.delete_chat_sessions else 0,
        "feedback": feedback_found if flags.delete_feedback else 0,
        "tasks": tasks_found if flags.delete_improvement_tasks else 0,
        "audit_logs": audit_logs_found if flags.delete_audit_logs else 0,
    }

    result: dict[str, Any] = {
        "dry_run": flags.dry_run,
        "knowledge_base_id": kb_id,
        "documents_found": documents_found,
        "chunks_found": chunks_found,
        "vectors_found": vectors_found,
        "ingestion_jobs_found": ingestion_jobs_found,
        "chat_sessions_found": chat_sessions_found,
        "chat_messages_found": chat_messages_found,
        "feedback_found": feedback_found,
        "tasks_found": tasks_found,
        "audit_logs_found": audit_logs_found,
        "will_delete": will_delete,
    }

    if flags.dry_run:
        result["applied"] = False
        return result

    deleted_vectors = 0
    try:
        # 1) Improvement tasks (references query_feedback)
        if flags.delete_improvement_tasks and tasks_found > 0:
            if flags.delete_feedback:
                if flags.include_demo_seed:
                    db.execute(
                        text(
                            """
                            DELETE FROM improvement_tasks t
                            WHERE t.knowledge_base_id = :kb_id
                              AND (
                                t.feedback_id IN (
                                  SELECT qf.id FROM query_feedback qf
                                  WHERE qf.knowledge_base_id = :kb_id
                                )
                                OR t.title LIKE :sl
                              )
                            """
                        ),
                        {"kb_id": kb_id, "sl": SEED_LIKE},
                    )
                else:
                    db.execute(
                        text(
                            """
                            DELETE FROM improvement_tasks t
                            WHERE t.knowledge_base_id = :kb_id
                              AND t.feedback_id IN (
                                SELECT qf.id FROM query_feedback qf
                                WHERE qf.knowledge_base_id = :kb_id
                                  AND qf.question_text NOT LIKE :sl
                              )
                            """
                        ),
                        {"kb_id": kb_id, "sl": SEED_LIKE},
                    )
            elif flags.include_demo_seed:
                db.execute(
                    text(
                        """
                        DELETE FROM improvement_tasks t
                        WHERE t.knowledge_base_id = :kb_id AND t.title LIKE :sl
                        """
                    ),
                    {"kb_id": kb_id, "sl": SEED_LIKE},
                )

        # 2) Query feedback (break FK to chat_messages)
        if flags.delete_feedback and feedback_found > 0:
            if flags.include_demo_seed:
                db.execute(
                    text("UPDATE query_feedback SET message_id = NULL WHERE knowledge_base_id = :kb_id"),
                    {"kb_id": kb_id},
                )
                db.execute(
                    text("DELETE FROM query_feedback WHERE knowledge_base_id = :kb_id"),
                    {"kb_id": kb_id},
                )
            else:
                db.execute(
                    text(
                        """
                        UPDATE query_feedback SET message_id = NULL
                        WHERE knowledge_base_id = :kb_id AND question_text NOT LIKE :sl
                        """
                    ),
                    {"kb_id": kb_id, "sl": SEED_LIKE},
                )
                db.execute(
                    text(
                        """
                        DELETE FROM query_feedback
                        WHERE knowledge_base_id = :kb_id AND question_text NOT LIKE :sl
                        """
                    ),
                    {"kb_id": kb_id, "sl": SEED_LIKE},
                )

        # 3) Chat sessions / messages
        if flags.delete_chat_sessions:
            if not flags.delete_feedback:
                db.execute(
                    text(
                        """
                        UPDATE query_feedback qf
                        SET session_id = NULL
                        WHERE qf.knowledge_base_id = :kb_id
                          AND qf.session_id IN (
                            SELECT id FROM chat_sessions WHERE knowledge_base_id = :kb_id
                          )
                        """
                    ),
                    {"kb_id": kb_id},
                )
                db.execute(
                    text(
                        """
                        UPDATE query_feedback qf
                        SET message_id = NULL
                        WHERE qf.knowledge_base_id = :kb_id
                          AND qf.message_id IN (
                            SELECT cm.id FROM chat_messages cm
                            JOIN chat_sessions cs ON cs.id = cm.session_id
                            WHERE cs.knowledge_base_id = :kb_id
                          )
                        """
                    ),
                    {"kb_id": kb_id},
                )
            db.execute(
                text(
                    """
                    DELETE FROM chat_messages
                    WHERE session_id IN (SELECT id FROM chat_sessions WHERE knowledge_base_id = :kb_id)
                    """
                ),
                {"kb_id": kb_id},
            )
            db.execute(
                text("DELETE FROM chat_sessions WHERE knowledge_base_id = :kb_id"),
                {"kb_id": kb_id},
            )

        # 4) Qdrant vectors (by DB point ids only; never drops collection)
        if flags.delete_vectors and point_ids:
            deleted_vectors = _delete_qdrant_points(point_ids)
        if flags.delete_vectors and not flags.delete_documents and doc_ids:
            stmt = (
                text("UPDATE document_chunks SET qdrant_point_id = NULL WHERE document_id IN :ids")
                .bindparams(bindparam("ids", expanding=True))
            )
            db.execute(stmt, {"ids": doc_ids})

        # 5) Documents + relational rows
        if flags.delete_documents and doc_ids:
            for doc_id in doc_ids:
                db.execute(text("DELETE FROM document_chunks WHERE document_id = :did"), {"did": doc_id})
                db.execute(
                    text(
                        """
                        DELETE FROM api_parameters
                        WHERE endpoint_id IN (SELECT id FROM api_endpoints WHERE document_id = :did)
                        """
                    ),
                    {"did": doc_id},
                )
                db.execute(
                    text(
                        """
                        DELETE FROM api_samples
                        WHERE endpoint_id IN (SELECT id FROM api_endpoints WHERE document_id = :did)
                        """
                    ),
                    {"did": doc_id},
                )
                db.execute(
                    text(
                        """
                        DELETE FROM api_error_codes
                        WHERE endpoint_id IN (SELECT id FROM api_endpoints WHERE document_id = :did)
                           OR document_id = :did
                        """
                    ),
                    {"did": doc_id},
                )
                db.execute(text("DELETE FROM api_endpoints WHERE document_id = :did"), {"did": doc_id})
                db.execute(text("DELETE FROM ingestion_jobs WHERE document_id = :did"), {"did": doc_id})
                db.execute(text("DELETE FROM api_auth_profiles WHERE document_id = :did"), {"did": doc_id})
                db.execute(text("DELETE FROM api_documents WHERE id = :did"), {"did": doc_id})

        if flags.delete_audit_logs and audit_logs_found > 0:
            if flags.include_demo_seed:
                db.execute(text("DELETE FROM audit_logs WHERE knowledge_base_id = :kb_id"), {"kb_id": kb_id})
            else:
                db.execute(
                    text(
                        """
                        DELETE FROM audit_logs
                        WHERE knowledge_base_id = :kb_id
                          AND (metadata_json->>'source' IS DISTINCT FROM 'DEMO_SEED_42')
                        """
                    ),
                    {"kb_id": kb_id},
                )

        db.commit()
        result["applied"] = True
        result["vectors_deleted_from_qdrant"] = deleted_vectors
        result["deleted"] = will_delete.copy()
    except Exception:
        db.rollback()
        raise

    return result
