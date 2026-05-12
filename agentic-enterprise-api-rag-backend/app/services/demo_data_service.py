from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.improvement_task import ImprovementTask
from app.models.knowledge_base import KnowledgeBase
from app.models.query_feedback import QueryFeedback
from app.models.user import User
from app.services.audit_log_service import record_audit_log

SEED_TAG = "DEMO_SEED_42"
SEED_MARKER = f"[{SEED_TAG}]"

FB_UP_Q = f"{SEED_MARKER} Was the appointment slots summary accurate?"
FB_DN1_Q = f"{SEED_MARKER} Slots response used wrong timezone for our region."
FB_DN2_Q = f"{SEED_MARKER} OAuth refresh token steps were incomplete in the answer."

TASK_OPEN_TITLE = f"{SEED_MARKER} Fix slots retrieval - wrong timezone (demo)"
TASK_RESOLVED_TITLE = f"{SEED_MARKER} Clarify OAuth refresh documentation (demo resolved)"


@dataclass
class DemoSeedContext:
    user_id: int
    user_email: str
    kb_id: int
    kb_name: str


def _load_user(db: Session, email: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise ValueError(f"User not found for DEMO_SEED_EMAIL={email!r}")
    if not user.is_active:
        raise ValueError(f"User {email!r} is inactive.")
    return user


def _load_kb(db: Session, kb_name: str | None) -> KnowledgeBase:
    if kb_name and kb_name.strip():
        kb = db.execute(
            select(KnowledgeBase).where(KnowledgeBase.name == kb_name.strip(), KnowledgeBase.is_active.is_(True)),
        ).scalar_one_or_none()
        if kb is None:
            raise ValueError(f"No active knowledge base named {kb_name.strip()!r}.")
        return kb
    kb = db.execute(
        select(KnowledgeBase).where(KnowledgeBase.is_active.is_(True)).order_by(KnowledgeBase.id.asc()).limit(1),
    ).scalar_one_or_none()
    if kb is None:
        raise ValueError("No active knowledge bases found; create or activate a KB first.")
    return kb


def _get_feedback(db: Session, *, user_id: int, knowledge_base_id: int, question_text: str) -> QueryFeedback | None:
    return db.execute(
        select(QueryFeedback).where(
            QueryFeedback.user_id == user_id,
            QueryFeedback.knowledge_base_id == knowledge_base_id,
            QueryFeedback.question_text == question_text,
        ),
    ).scalar_one_or_none()


def _get_task(db: Session, *, created_by: int, title: str) -> ImprovementTask | None:
    return db.execute(
        select(ImprovementTask).where(ImprovementTask.created_by == created_by, ImprovementTask.title == title),
    ).scalar_one_or_none()


def get_seed_status(db: Session) -> dict[str, Any]:
    like_pat = f"%{SEED_MARKER}%"
    feedback = int(
        db.execute(text("SELECT COUNT(*) FROM query_feedback WHERE question_text LIKE :pat"), {"pat": like_pat}).scalar_one()
    )
    tasks = int(
        db.execute(text("SELECT COUNT(*) FROM improvement_tasks WHERE title LIKE :pat"), {"pat": like_pat}).scalar_one()
    )
    audit = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM audit_logs
                WHERE metadata_json IS NOT NULL
                  AND (
                    (metadata_json->>'source') = :tag
                    OR CAST(metadata_json AS TEXT) LIKE :pat
                  )
                """
            ),
            {"tag": SEED_TAG, "pat": like_pat},
        ).scalar_one()
    )
    return {"seeded_feedback_count": feedback, "seeded_task_count": tasks, "seeded_audit_count": audit}


def seed_demo_data(db: Session, *, email: str, kb_name: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    user = _load_user(db, email)
    kb = _load_kb(db, kb_name)
    ctx = DemoSeedContext(user_id=int(user.id), user_email=user.email, kb_id=int(kb.id), kb_name=kb.name)

    feedback_created = feedback_skipped = feedback_planned = 0
    tasks_created = tasks_skipped = tasks_planned = 0
    audit_writes = 0

    def plan_or_insert_feedback(question_text: str, answer_text: str, rating: str, comment: str | None) -> None:
        nonlocal feedback_created, feedback_skipped, feedback_planned, audit_writes
        existing = _get_feedback(db, user_id=ctx.user_id, knowledge_base_id=ctx.kb_id, question_text=question_text)
        if existing is not None:
            feedback_skipped += 1
            return
        if dry_run:
            feedback_planned += 1
            return
        feedback_created += 1
        row = QueryFeedback(
            user_id=ctx.user_id,
            session_id=None,
            message_id=None,
            knowledge_base_id=ctx.kb_id,
            question_text=question_text,
            answer_text=answer_text,
            rating=rating,
            comment=comment,
        )
        db.add(row)
        db.flush()
        record_audit_log(
            None,
            ctx.user_id,
            "query_feedback.submitted",
            "query_feedback",
            int(row.id),
            ctx.kb_id,
            {"source": SEED_TAG},
        )
        audit_writes += 1

    plan_or_insert_feedback(
        FB_UP_Q,
        "Sample assistant answer: appointment slots are available Mon-Fri 9-5 via the Scheduling API.",
        "thumbs_up",
        "Seeded thumbs-up for demo analytics.",
    )
    plan_or_insert_feedback(
        FB_DN1_Q,
        "Sample answer referencing UTC only; customer expected America/Chicago.",
        "thumbs_down",
        "Timezone mismatch - demo seed.",
    )
    plan_or_insert_feedback(
        FB_DN2_Q,
        "High-level OAuth steps without refresh token rotation details.",
        "thumbs_down",
        "Need clearer refresh flow - demo seed.",
    )

    if not dry_run:
        db.flush()

    row_dn1 = _get_feedback(db, user_id=ctx.user_id, knowledge_base_id=ctx.kb_id, question_text=FB_DN1_Q)
    row_dn2 = _get_feedback(db, user_id=ctx.user_id, knowledge_base_id=ctx.kb_id, question_text=FB_DN2_Q)
    fb_dn1_id = int(row_dn1.id) if row_dn1 else None
    fb_dn2_id = int(row_dn2.id) if row_dn2 else None

    def plan_or_insert_task(
        title: str,
        description: str,
        status: str,
        priority: str,
        feedback_id: int | None,
        resolution_notes: str | None,
        resolved_at: datetime | None,
        resolved_by: int | None,
    ) -> None:
        nonlocal tasks_created, tasks_skipped, tasks_planned, audit_writes
        existing = _get_task(db, created_by=ctx.user_id, title=title)
        if existing is not None:
            tasks_skipped += 1
            return
        if dry_run:
            tasks_planned += 1
            return
        tasks_created += 1
        now = datetime.now(timezone.utc)
        row = ImprovementTask(
            feedback_id=feedback_id,
            knowledge_base_id=ctx.kb_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assigned_to=None,
            created_by=ctx.user_id,
            resolution_notes=resolution_notes,
            resolved_at=resolved_at,
            resolved_by=resolved_by,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        record_audit_log(
            None,
            ctx.user_id,
            "improvement_task.created",
            "improvement_task",
            int(row.id),
            ctx.kb_id,
            {"source": SEED_TAG, "status": row.status},
        )
        audit_writes += 1
        if status == "resolved":
            record_audit_log(
                None,
                ctx.user_id,
                "improvement_task.resolved",
                "improvement_task",
                int(row.id),
                ctx.kb_id,
                {"source": SEED_TAG},
            )
            audit_writes += 1

    plan_or_insert_task(
        TASK_OPEN_TITLE,
        "Demo seed: high-priority follow-up linked to negative feedback on slot timezone handling.",
        "open",
        "high",
        fb_dn1_id,
        None,
        None,
        None,
    )
    now = datetime.now(timezone.utc)
    plan_or_insert_task(
        TASK_RESOLVED_TITLE,
        "Demo seed: documentation task tied to OAuth feedback; marked resolved for presentation.",
        "resolved",
        "medium",
        fb_dn2_id,
        "Demo resolution: updated internal runbook section for refresh token rotation; verified in staging.",
        now,
        ctx.user_id,
    )

    return {
        "operation": "seed",
        "dry_run": dry_run,
        "user": {"id": ctx.user_id, "email": ctx.user_email},
        "knowledge_base": {"id": ctx.kb_id, "name": ctx.kb_name},
        "feedback": {
            "created": feedback_created,
            "planned": feedback_planned,
            "skipped": feedback_skipped,
        },
        "tasks": {
            "created": tasks_created,
            "planned": tasks_planned,
            "skipped": tasks_skipped,
        },
        "audit_log_inserts": audit_writes if not dry_run else 0,
        "status": get_seed_status(db),
    }


def reset_demo_data(db: Session, *, dry_run: bool = False) -> dict[str, Any]:
    like_pat = f"%{SEED_MARKER}%"
    task_rows = db.execute(
        text(
            """
            SELECT id, title, feedback_id
            FROM improvement_tasks
            WHERE title LIKE :pat
            ORDER BY id
            """
        ),
        {"pat": like_pat},
    ).mappings().all()

    fb_candidates = db.execute(
        text(
            """
            SELECT id, question_text
            FROM query_feedback
            WHERE question_text LIKE :pat
            ORDER BY id
            """
        ),
        {"pat": like_pat},
    ).mappings().all()

    fb_blocked: list[dict[str, Any]] = []
    fb_deletable: list[dict[str, Any]] = []
    for row in fb_candidates:
        fid = int(row["id"])
        blocked = db.execute(
            text(
                """
                SELECT t.id, t.title
                FROM improvement_tasks t
                WHERE t.feedback_id = :fid
                  AND t.title NOT LIKE :pat
                LIMIT 5
                """
            ),
            {"fid": fid, "pat": like_pat},
        ).mappings().all()
        if blocked:
            fb_blocked.append({"feedback_id": fid, "blocked_by_tasks": [dict(b) for b in blocked]})
        else:
            fb_deletable.append(dict(row))

    audit_rows = db.execute(
        text(
            """
            SELECT id, action, entity_type, entity_id
            FROM audit_logs
            WHERE metadata_json IS NOT NULL
              AND (
                (metadata_json->>'source') = :tag
                OR CAST(metadata_json AS TEXT) LIKE :pat
              )
            ORDER BY id
            """
        ),
        {"tag": SEED_TAG, "pat": like_pat},
    ).mappings().all()

    if not dry_run:
        def _delete_ids(table: str, ids: list[int]) -> None:
            if not ids:
                return
            id_list = ",".join(str(int(i)) for i in ids)
            db.execute(text(f"DELETE FROM {table} WHERE id IN ({id_list})"))

        _delete_ids("improvement_tasks", [int(r["id"]) for r in task_rows])
        _delete_ids("query_feedback", [int(r["id"]) for r in fb_deletable])
        _delete_ids("audit_logs", [int(r["id"]) for r in audit_rows])

    return {
        "operation": "reset",
        "dry_run": dry_run,
        "marker": SEED_MARKER,
        "task_rows": [dict(r) for r in task_rows],
        "feedback_rows": [dict(r) for r in fb_deletable],
        "audit_rows": [dict(r) for r in audit_rows],
        "skipped_unsafe_feedback": fb_blocked,
        "deleted_counts": {
            "tasks": 0 if dry_run else len(task_rows),
            "feedback": 0 if dry_run else len(fb_deletable),
            "audit_logs": 0 if dry_run else len(audit_rows),
        },
        "status": get_seed_status(db),
    }

