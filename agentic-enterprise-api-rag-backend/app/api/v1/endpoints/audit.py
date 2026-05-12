from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_super_admin

router = APIRouter()


@router.get("/logs")
def list_audit_logs(
    db: Session = Depends(get_db),
    _current_user: dict[str, Any] = Depends(require_admin_or_super_admin),
    action: str | None = Query(None, max_length=128),
    entity_type: str | None = Query(None, max_length=64),
    knowledge_base_id: int | None = Query(None, ge=1),
    actor_user_id: int | None = Query(None, ge=1),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> dict[str, Any]:
    conditions: list[str] = ["1=1"]
    params: dict[str, Any] = {}
    if action:
        conditions.append("a.action = :action")
        params["action"] = action
    if entity_type:
        conditions.append("a.entity_type = :entity_type")
        params["entity_type"] = entity_type
    if knowledge_base_id is not None:
        conditions.append("a.knowledge_base_id = :knowledge_base_id")
        params["knowledge_base_id"] = knowledge_base_id
    if actor_user_id is not None:
        conditions.append("a.actor_user_id = :actor_user_id")
        params["actor_user_id"] = actor_user_id
    if from_date is not None:
        conditions.append("a.created_at >= :from_date")
        params["from_date"] = from_date
    if to_date is not None:
        conditions.append("a.created_at <= :to_date")
        params["to_date"] = to_date

    where_sql = " AND ".join(conditions)
    rows = db.execute(
        text(
            f"""
            SELECT
              a.id,
              a.actor_user_id,
              u.email AS actor_email,
              u.full_name AS actor_name,
              a.action,
              a.entity_type,
              a.entity_id,
              a.knowledge_base_id,
              kb.name AS knowledge_base_name,
              a.metadata_json,
              a.created_at
            FROM audit_logs a
            JOIN users u ON u.id = a.actor_user_id
            LEFT JOIN knowledge_bases kb ON kb.id = a.knowledge_base_id
            WHERE {where_sql}
            ORDER BY a.created_at DESC
            LIMIT 500
            """
        ),
        params,
    ).mappings().all()

    items: list[dict[str, Any]] = []
    for r in rows:
        meta = r["metadata_json"]
        preview: str | None = None
        if meta is not None:
            try:
                raw = json.dumps(meta, default=str)
                preview = raw[:400] + ("…" if len(raw) > 400 else "")
            except (TypeError, ValueError):
                preview = str(meta)[:400]
        items.append(
            {
                "id": r["id"],
                "actor_user_id": r["actor_user_id"],
                "actor_summary": (r["actor_name"] or r["actor_email"] or "").strip() or str(r["actor_user_id"]),
                "actor_email": r["actor_email"],
                "action": r["action"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "knowledge_base_id": r["knowledge_base_id"],
                "knowledge_base_name": r["knowledge_base_name"],
                "metadata_preview": preview or None,
                "metadata_json": meta,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )

    return {"items": items}
