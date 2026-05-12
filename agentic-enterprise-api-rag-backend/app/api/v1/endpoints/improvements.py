from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_super_admin
from app.services.audit_log_service import record_audit_log
from app.services.improvement_task_analysis import run_improvement_task_analysis

router = APIRouter()

TaskStatus = Literal["open", "in_progress", "resolved", "dismissed"]
TaskPriority = Literal["low", "medium", "high"]


def _prefill_from_feedback(question: str, answer: str, comment: str | None, feedback_id: int) -> tuple[str, str]:
    q = (question or "").strip()
    title = (q[:500] if q else f"Improvement from feedback #{feedback_id}").strip() or f"Improvement from feedback #{feedback_id}"
    parts = ["Source: query feedback (thumbs down).", "", "User question:", q or "(empty)", "", "Assistant answer:", (answer or "").strip() or "(empty)"]
    if comment and str(comment).strip():
        parts.extend(["", "User comment:", str(comment).strip()])
    description = "\n".join(parts)
    return title, description


class ImprovementTaskCreate(BaseModel):
    feedback_id: int | None = Field(None, ge=1)
    knowledge_base_id: int | None = Field(None, ge=1)
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=50000)
    status: TaskStatus = "open"
    priority: TaskPriority = "medium"
    assigned_to: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def require_fields(self) -> ImprovementTaskCreate:
        if self.feedback_id is None:
            if self.knowledge_base_id is None:
                raise ValueError("knowledge_base_id is required when feedback_id is omitted")
            t = (self.title or "").strip()
            d = (self.description or "").strip()
            if not t or not d:
                raise ValueError("title and description are required when feedback_id is omitted")
        return self


class ImprovementTaskPatch(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=50000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to: int | None = None
    resolution_notes: str | None = Field(None, max_length=20000)


class ImprovementTaskAnalyzeRequest(BaseModel):
    include_retrieval_test: bool = True


def _user_exists(db: Session, user_id: int) -> bool:
    row = db.execute(text("SELECT 1 FROM users WHERE id = :id AND is_active = true"), {"id": user_id}).scalar()
    return bool(row)


def _kb_exists(db: Session, kb_id: int) -> bool:
    return bool(db.execute(text("SELECT 1 FROM knowledge_bases WHERE id = :id"), {"id": kb_id}).scalar())


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_improvement_task(
    body: ImprovementTaskCreate,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    feedback_id = body.feedback_id
    knowledge_base_id = body.knowledge_base_id
    title = (body.title or "").strip() if body.title else None
    description = (body.description or "").strip() if body.description else None
    assigned_to = body.assigned_to

    if feedback_id is not None:
        fb = db.execute(
            text(
                """
                SELECT id, knowledge_base_id, question_text, answer_text, comment, rating
                FROM query_feedback
                WHERE id = :fid
                """
            ),
            {"fid": feedback_id},
        ).mappings().first()
        if fb is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
        if fb["rating"] != "thumbs_down":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only thumbs-down feedback can be linked to an improvement task",
            )
        knowledge_base_id = int(fb["knowledge_base_id"])
        if title is None or not title:
            title, auto_desc = _prefill_from_feedback(
                str(fb["question_text"] or ""),
                str(fb["answer_text"] or ""),
                fb["comment"],
                feedback_id,
            )
            if description is None or not description:
                description = auto_desc
        elif description is None or not description:
            _, description = _prefill_from_feedback(
                str(fb["question_text"] or ""),
                str(fb["answer_text"] or ""),
                fb["comment"],
                feedback_id,
            )
    else:
        knowledge_base_id = int(knowledge_base_id)  # type: ignore[assignment]
        title = title or ""
        description = description or ""

    if not _kb_exists(db, int(knowledge_base_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge base not found")

    if assigned_to is not None and not _user_exists(db, int(assigned_to)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assigned_to user not found or inactive")

    row = db.execute(
        text(
            """
            INSERT INTO improvement_tasks (
              feedback_id, knowledge_base_id, title, description, status, priority,
              assigned_to, created_by, created_at, updated_at
            )
            VALUES (
              :feedback_id, :knowledge_base_id, :title, :description, :status, :priority,
              :assigned_to, :created_by, now(), now()
            )
            RETURNING id, created_at, updated_at
            """
        ),
        {
            "feedback_id": feedback_id,
            "knowledge_base_id": knowledge_base_id,
            "title": title[:500],
            "description": description,
            "status": body.status,
            "priority": body.priority,
            "assigned_to": assigned_to,
            "created_by": current_user["id"],
        },
    ).mappings().first()
    db.commit()
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task")
    tid = int(row["id"])
    record_audit_log(
        db,
        int(current_user["id"]),
        "improvement_task.created",
        "improvement_task",
        entity_id=tid,
        knowledge_base_id=int(knowledge_base_id),
        metadata_json={
            "feedback_id": feedback_id,
            "title_preview": (title or "")[:160],
        },
    )
    return _get_task_by_id(db, tid)


@router.get("/tasks")
def list_improvement_tasks(
    db: Session = Depends(get_db),
    _current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
    status_filter: TaskStatus | None = Query(None, alias="status"),
    priority: TaskPriority | None = Query(None),
) -> dict[str, Any]:
    conditions: list[str] = ["1=1"]
    params: dict[str, Any] = {}
    if status_filter is not None:
        conditions.append("t.status = :status")
        params["status"] = status_filter
    if priority is not None:
        conditions.append("t.priority = :priority")
        params["priority"] = priority
    where_sql = " AND ".join(conditions)

    rows = db.execute(
        text(
            f"""
            SELECT
              t.id,
              t.feedback_id,
              t.knowledge_base_id,
              kb.name AS knowledge_base_name,
              t.title,
              t.description,
              t.status,
              t.priority,
              t.assigned_to,
              au.email AS assigned_to_email,
              au.full_name AS assigned_to_name,
              t.created_by,
              cu.email AS created_by_email,
              cu.full_name AS created_by_name,
              t.created_at,
              t.updated_at,
              t.resolution_notes,
              t.resolved_at,
              t.resolved_by,
              ru.email AS resolved_by_email,
              ru.full_name AS resolved_by_name,
              qf.id AS qf_id,
              qf.rating AS qf_rating,
              qf.question_text AS qf_question,
              qf.answer_text AS qf_answer,
              qf.comment AS qf_comment,
              qf.created_at AS qf_created_at
            FROM improvement_tasks t
            JOIN knowledge_bases kb ON kb.id = t.knowledge_base_id
            JOIN users cu ON cu.id = t.created_by
            LEFT JOIN users au ON au.id = t.assigned_to
            LEFT JOIN users ru ON ru.id = t.resolved_by
            LEFT JOIN query_feedback qf ON qf.id = t.feedback_id
            WHERE {where_sql}
            ORDER BY t.created_at DESC
            LIMIT 500
            """
        ),
        params,
    ).mappings().all()

    return {"items": [_row_to_item(r) for r in rows]}


def _row_to_item(r: Any) -> dict[str, Any]:
    linked = None
    if r["feedback_id"] is not None and r["qf_id"] is not None:
        ans = r["qf_answer"] or ""
        linked = {
            "id": r["qf_id"],
            "rating": r["qf_rating"],
            "question_text": r["qf_question"],
            "answer_preview": ans[:280] + ("…" if len(ans) > 280 else ""),
            "comment": r["qf_comment"],
            "created_at": r["qf_created_at"].isoformat() if r["qf_created_at"] else None,
        }
    return {
        "id": r["id"],
        "feedback_id": r["feedback_id"],
        "knowledge_base_id": r["knowledge_base_id"],
        "knowledge_base_name": r["knowledge_base_name"] or "",
        "title": r["title"],
        "description": r["description"],
        "status": r["status"],
        "priority": r["priority"],
        "assigned_to": r["assigned_to"],
        "assigned_to_label": (r["assigned_to_name"] or r["assigned_to_email"]) if r["assigned_to"] else None,
        "created_by": r["created_by"],
        "created_by_label": r["created_by_name"] or r["created_by_email"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        "resolution_notes": r["resolution_notes"],
        "resolved_at": r["resolved_at"].isoformat() if r["resolved_at"] else None,
        "resolved_by": r["resolved_by"],
        "resolved_by_label": (r["resolved_by_name"] or r["resolved_by_email"]) if r["resolved_by"] else None,
        "linked_feedback": linked,
    }


def _get_task_by_id(db: Session, task_id: int) -> dict[str, Any]:
    r = db.execute(
        text(
            """
            SELECT
              t.id,
              t.feedback_id,
              t.knowledge_base_id,
              kb.name AS knowledge_base_name,
              t.title,
              t.description,
              t.status,
              t.priority,
              t.assigned_to,
              au.email AS assigned_to_email,
              au.full_name AS assigned_to_name,
              t.created_by,
              cu.email AS created_by_email,
              cu.full_name AS created_by_name,
              t.created_at,
              t.updated_at,
              t.resolution_notes,
              t.resolved_at,
              t.resolved_by,
              ru.email AS resolved_by_email,
              ru.full_name AS resolved_by_name,
              qf.id AS qf_id,
              qf.rating AS qf_rating,
              qf.question_text AS qf_question,
              qf.answer_text AS qf_answer,
              qf.comment AS qf_comment,
              qf.created_at AS qf_created_at
            FROM improvement_tasks t
            JOIN knowledge_bases kb ON kb.id = t.knowledge_base_id
            JOIN users cu ON cu.id = t.created_by
            LEFT JOIN users au ON au.id = t.assigned_to
            LEFT JOIN users ru ON ru.id = t.resolved_by
            LEFT JOIN query_feedback qf ON qf.id = t.feedback_id
            WHERE t.id = :tid
            """
        ),
        {"tid": task_id},
    ).mappings().first()
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _row_to_item(r)


@router.post("/tasks/{task_id}/analyze")
async def analyze_improvement_task(
    task_id: int,
    body: ImprovementTaskAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    result = await run_improvement_task_analysis(
        db,
        user_id=int(current_user["id"]),
        task_id=task_id,
        include_retrieval_test=body.include_retrieval_test,
    )
    kb_row = db.execute(
        text("SELECT knowledge_base_id FROM improvement_tasks WHERE id = :id"),
        {"id": task_id},
    ).scalar()
    record_audit_log(
        db,
        int(current_user["id"]),
        "improvement_task.analyzed",
        "improvement_task",
        entity_id=task_id,
        knowledge_base_id=int(kb_row) if kb_row is not None else None,
        metadata_json={
            "recommended_action": result.get("recommended_action"),
            "include_retrieval_test": body.include_retrieval_test,
        },
    )
    return result


@router.patch("/tasks/{task_id}")
def patch_improvement_task(
    task_id: int,
    body: ImprovementTaskPatch,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    existing = db.execute(
        text("SELECT id, status FROM improvement_tasks WHERE id = :id"),
        {"id": task_id},
    ).mappings().first()
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    current_status = str(existing["status"] or "")

    data = body.model_dump(exclude_unset=True)
    if not data:
        return _get_task_by_id(db, task_id)

    if "assigned_to" in data and data["assigned_to"] is not None:
        if int(data["assigned_to"]) < 1 or not _user_exists(db, int(data["assigned_to"])):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assigned_to user not found or inactive")

    sets: list[str] = []
    params: dict[str, Any] = {"tid": task_id}
    if "title" in data:
        t = (data["title"] or "").strip()[:500]
        if not t:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title cannot be empty")
        sets.append("title = :title")
        params["title"] = t
    if "description" in data:
        d = (data["description"] or "").strip()
        if not d:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="description cannot be empty")
        sets.append("description = :description")
        params["description"] = d
    if "priority" in data and data["priority"] is not None:
        sets.append("priority = :priority")
        params["priority"] = data["priority"]
    if "assigned_to" in data:
        sets.append("assigned_to = :assigned_to")
        params["assigned_to"] = data["assigned_to"]

    if "resolution_notes" in data:
        raw = data["resolution_notes"]
        notes_val: str | None
        if raw is None:
            notes_val = None
        else:
            stripped = str(raw).strip()
            notes_val = stripped if stripped else None
        sets.append("resolution_notes = :resolution_notes")
        params["resolution_notes"] = notes_val

    if "status" in data and data["status"] is not None:
        new_status = str(data["status"])
        sets.append("status = :status")
        params["status"] = new_status
        if new_status == "resolved" and current_status != "resolved":
            sets.append("resolved_at = COALESCE(resolved_at, now())")
            sets.append("resolved_by = :resolved_by")
            params["resolved_by"] = int(current_user["id"])
        elif new_status != "resolved" and current_status == "resolved":
            sets.append("resolved_at = NULL")
            sets.append("resolved_by = NULL")

    if not sets:
        return _get_task_by_id(db, task_id)

    sets.append("updated_at = now()")
    db.execute(text(f"UPDATE improvement_tasks SET {', '.join(sets)} WHERE id = :tid"), params)
    db.commit()
    out = _get_task_by_id(db, task_id)
    kb = int(out["knowledge_base_id"])
    resolved_transition = bool(
        "status" in data and str(data["status"]) == "resolved" and current_status != "resolved",
    )
    if resolved_transition:
        record_audit_log(
            db,
            int(current_user["id"]),
            "improvement_task.resolved",
            "improvement_task",
            entity_id=task_id,
            knowledge_base_id=kb,
            metadata_json={"previous_status": current_status, "fields": sorted(data.keys())},
        )
    else:
        record_audit_log(
            db,
            int(current_user["id"]),
            "improvement_task.updated",
            "improvement_task",
            entity_id=task_id,
            knowledge_base_id=kb,
            metadata_json={"fields": sorted(data.keys())},
        )
    return out
