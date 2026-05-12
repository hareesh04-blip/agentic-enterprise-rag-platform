from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import check_knowledge_base_access, get_db, require_admin_or_super_admin, require_permission
from app.services.audit_log_service import record_audit_log

router = APIRouter()


def _feedback_kb_date_filters(
    knowledge_base_id: int | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[str, dict[str, Any]]:
    conditions: list[str] = ["1=1"]
    params: dict[str, Any] = {}
    if knowledge_base_id is not None:
        conditions.append("qf.knowledge_base_id = :knowledge_base_id")
        params["knowledge_base_id"] = knowledge_base_id
    if from_date is not None:
        conditions.append("qf.created_at >= :from_date")
        params["from_date"] = from_date
    if to_date is not None:
        conditions.append("qf.created_at <= :to_date")
        params["to_date"] = to_date
    return " AND ".join(conditions), params


def _rate(up: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(float(up) / float(total), 4)


class QueryFeedbackCreate(BaseModel):
    knowledge_base_id: int = Field(..., ge=1)
    question_text: str = Field(..., min_length=1, max_length=50000)
    answer_text: str = Field(..., min_length=1, max_length=100000)
    rating: Literal["thumbs_up", "thumbs_down"]
    comment: str | None = Field(None, max_length=4000)
    session_id: int | None = Field(None, ge=1)
    message_id: int | None = Field(None, ge=1)


def _verify_session_for_user(
    db: Session,
    *,
    user_id: int,
    session_id: int,
    knowledge_base_id: int,
) -> bool:
    row = db.execute(
        text(
            """
            SELECT 1
            FROM chat_sessions s
            JOIN user_knowledge_base_access uka
              ON uka.knowledge_base_id = s.knowledge_base_id AND uka.user_id = :user_id
            WHERE s.id = :session_id
              AND s.user_id = :user_id
              AND s.knowledge_base_id = :knowledge_base_id
            LIMIT 1
            """
        ),
        {
            "user_id": user_id,
            "session_id": session_id,
            "knowledge_base_id": knowledge_base_id,
        },
    ).scalar()
    return bool(row)


def _verify_message_for_user(
    db: Session,
    *,
    user_id: int,
    message_id: int,
    knowledge_base_id: int,
    session_id: int | None,
) -> bool:
    row = db.execute(
        text(
            """
            SELECT s.id, s.knowledge_base_id, s.user_id
            FROM chat_messages m
            JOIN chat_sessions s ON s.id = m.session_id
            WHERE m.id = :message_id
            LIMIT 1
            """
        ),
        {"message_id": message_id},
    ).mappings().first()
    if row is None:
        return False
    if row["knowledge_base_id"] != knowledge_base_id:
        return False
    if row["user_id"] != user_id:
        return False
    if session_id is not None and row["id"] != session_id:
        return False
    access = db.execute(
        text(
            """
            SELECT 1
            FROM user_knowledge_base_access uka
            WHERE uka.user_id = :user_id AND uka.knowledge_base_id = :kb_id
            LIMIT 1
            """
        ),
        {"user_id": user_id, "kb_id": knowledge_base_id},
    ).scalar()
    return bool(access)


@router.post("/query", status_code=status.HTTP_201_CREATED)
def submit_query_feedback(
    body: QueryFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_permission("query.ask")),
) -> dict[str, Any]:
    if not check_knowledge_base_access(db, int(current_user["id"]), body.knowledge_base_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Knowledge base access denied")

    if body.session_id is not None:
        if not _verify_session_for_user(
            db,
            user_id=int(current_user["id"]),
            session_id=body.session_id,
            knowledge_base_id=body.knowledge_base_id,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session for this knowledge base")

    if body.message_id is not None:
        if not _verify_message_for_user(
            db,
            user_id=int(current_user["id"]),
            message_id=body.message_id,
            knowledge_base_id=body.knowledge_base_id,
            session_id=body.session_id,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid message for this session or knowledge base")

    row = db.execute(
        text(
            """
            INSERT INTO query_feedback (
              user_id, session_id, message_id, knowledge_base_id,
              question_text, answer_text, rating, comment
            )
            VALUES (
              :user_id, :session_id, :message_id, :knowledge_base_id,
              :question_text, :answer_text, :rating, :comment
            )
            RETURNING id, created_at
            """
        ),
        {
            "user_id": current_user["id"],
            "session_id": body.session_id,
            "message_id": body.message_id,
            "knowledge_base_id": body.knowledge_base_id,
            "question_text": body.question_text,
            "answer_text": body.answer_text,
            "rating": body.rating,
            "comment": body.comment,
        },
    ).mappings().first()
    db.commit()
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store feedback")
    fid = int(row["id"])
    record_audit_log(
        db,
        int(current_user["id"]),
        "query_feedback.submitted",
        "query_feedback",
        entity_id=fid,
        knowledge_base_id=int(body.knowledge_base_id),
        metadata_json={
            "rating": body.rating,
            "has_comment": bool((body.comment or "").strip()),
            "has_session_id": body.session_id is not None,
        },
    )
    return {"id": fid, "created_at": row["created_at"].isoformat() if row["created_at"] else None}


@router.get("/query")
def list_query_feedback(
    db: Session = Depends(get_db),
    _current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
    knowledge_base_id: int | None = Query(None, ge=1),
    rating: Literal["thumbs_up", "thumbs_down"] | None = Query(None),
    from_date: datetime | None = Query(None, description="ISO date/time; feedback on or after this instant"),
    to_date: datetime | None = Query(None, description="ISO date/time; feedback on or before this instant"),
) -> dict[str, Any]:
    conditions: list[str] = ["1=1"]
    params: dict[str, Any] = {}
    if knowledge_base_id is not None:
        conditions.append("qf.knowledge_base_id = :knowledge_base_id")
        params["knowledge_base_id"] = knowledge_base_id
    if rating is not None:
        conditions.append("qf.rating = :rating")
        params["rating"] = rating
    if from_date is not None:
        conditions.append("qf.created_at >= :from_date")
        params["from_date"] = from_date
    if to_date is not None:
        conditions.append("qf.created_at <= :to_date")
        params["to_date"] = to_date

    where_sql = " AND ".join(conditions)
    rows = db.execute(
        text(
            f"""
            SELECT
              qf.id,
              qf.user_id,
              qf.session_id,
              qf.message_id,
              qf.knowledge_base_id,
              qf.question_text,
              qf.answer_text,
              qf.rating,
              qf.comment,
              qf.created_at,
              u.email AS submitter_email,
              u.full_name AS submitter_name,
              kb.name AS knowledge_base_name
            FROM query_feedback qf
            JOIN users u ON u.id = qf.user_id
            JOIN knowledge_bases kb ON kb.id = qf.knowledge_base_id
            WHERE {where_sql}
            ORDER BY qf.created_at DESC
            LIMIT 500
            """
        ),
        params,
    ).mappings().all()

    return {
        "items": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "session_id": r["session_id"],
                "message_id": r["message_id"],
                "knowledge_base_id": r["knowledge_base_id"],
                "knowledge_base_name": r["knowledge_base_name"],
                "question_text": r["question_text"],
                "answer_text": r["answer_text"],
                "answer_preview": (r["answer_text"] or "")[:280] + ("…" if len(r["answer_text"] or "") > 280 else ""),
                "rating": r["rating"],
                "comment": r["comment"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "submitted_by": r["submitter_name"] or r["submitter_email"],
                "submitter_email": r["submitter_email"],
            }
            for r in rows
        ]
    }


@router.get("/analytics")
def feedback_analytics(
    db: Session = Depends(get_db),
    _current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
    knowledge_base_id: int | None = Query(None, ge=1),
    from_date: datetime | None = Query(None, description="ISO date/time; feedback on or after this instant"),
    to_date: datetime | None = Query(None, description="ISO date/time; feedback on or before this instant"),
) -> dict[str, Any]:
    where_sql, params = _feedback_kb_date_filters(knowledge_base_id, from_date, to_date)

    total_row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) AS total,
              COALESCE(SUM(CASE WHEN qf.rating = 'thumbs_up' THEN 1 ELSE 0 END), 0) AS thumbs_up_count,
              COALESCE(SUM(CASE WHEN qf.rating = 'thumbs_down' THEN 1 ELSE 0 END), 0) AS thumbs_down_count
            FROM query_feedback qf
            WHERE {where_sql}
            """
        ),
        params,
    ).mappings().first()

    total = int(total_row["total"] or 0) if total_row else 0
    up = int(total_row["thumbs_up_count"] or 0) if total_row else 0
    down = int(total_row["thumbs_down_count"] or 0) if total_row else 0

    by_kb_rows = db.execute(
        text(
            f"""
            SELECT
              qf.knowledge_base_id,
              kb.name AS knowledge_base_name,
              COUNT(*) AS total,
              COALESCE(SUM(CASE WHEN qf.rating = 'thumbs_up' THEN 1 ELSE 0 END), 0) AS thumbs_up,
              COALESCE(SUM(CASE WHEN qf.rating = 'thumbs_down' THEN 1 ELSE 0 END), 0) AS thumbs_down
            FROM query_feedback qf
            JOIN knowledge_bases kb ON kb.id = qf.knowledge_base_id
            WHERE {where_sql}
            GROUP BY qf.knowledge_base_id, kb.name
            ORDER BY qf.knowledge_base_id
            """
        ),
        params,
    ).mappings().all()

    neg_rows = db.execute(
        text(
            f"""
            SELECT
              qf.id,
              qf.knowledge_base_id,
              kb.name AS knowledge_base_name,
              qf.question_text,
              qf.answer_text,
              qf.comment,
              qf.created_at
            FROM query_feedback qf
            JOIN knowledge_bases kb ON kb.id = qf.knowledge_base_id
            WHERE {where_sql} AND qf.rating = 'thumbs_down'
            ORDER BY qf.created_at DESC
            LIMIT 25
            """
        ),
        params,
    ).mappings().all()

    return {
        "total_feedback": total,
        "thumbs_up_count": up,
        "thumbs_down_count": down,
        "thumbs_up_rate": _rate(up, total),
        "by_knowledge_base": [
            {
                "knowledge_base_id": r["knowledge_base_id"],
                "knowledge_base_name": r["knowledge_base_name"] or "",
                "total": int(r["total"] or 0),
                "thumbs_up": int(r["thumbs_up"] or 0),
                "thumbs_down": int(r["thumbs_down"] or 0),
                "thumbs_up_rate": _rate(int(r["thumbs_up"] or 0), int(r["total"] or 0)),
            }
            for r in by_kb_rows
        ],
        "recent_negative_feedback": [
            {
                "id": r["id"],
                "knowledge_base_id": r["knowledge_base_id"],
                "knowledge_base_name": r["knowledge_base_name"] or "",
                "question_text": r["question_text"],
                "answer_preview": (r["answer_text"] or "")[:280] + ("…" if len(r["answer_text"] or "") > 280 else ""),
                "comment": r["comment"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in neg_rows
        ],
    }
