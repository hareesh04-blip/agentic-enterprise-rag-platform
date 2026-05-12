from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


def record_audit_log(
    db: Session | None,
    actor_user_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    knowledge_base_id: int | None = None,
    metadata_json: dict[str, Any] | list[Any] | None = None,
) -> None:
    """
    Persist an audit row in its own short-lived session so callers are not affected
    by outer transaction boundaries or rollbacks.
    """
    meta_str: str | None
    if metadata_json is None:
        meta_str = None
    else:
        try:
            meta_str = json.dumps(metadata_json, default=str)
        except (TypeError, ValueError) as exc:
            logger.warning("audit_log metadata serialization failed: %s", exc)
            meta_str = json.dumps({"serialization_error": str(exc)})

    try:
        with SessionLocal() as session:
            session.execute(
                text(
                    """
                    INSERT INTO audit_logs (
                      actor_user_id, action, entity_type, entity_id,
                      knowledge_base_id, metadata_json
                    )
                    VALUES (
                      :actor_user_id, :action, :entity_type, :entity_id,
                      :knowledge_base_id, CAST(:metadata_json AS JSON)
                    )
                    """
                ),
                {
                    "actor_user_id": actor_user_id,
                    "action": action[:128],
                    "entity_type": entity_type[:64],
                    "entity_id": entity_id,
                    "knowledge_base_id": knowledge_base_id,
                    "metadata_json": meta_str if meta_str is not None else "null",
                },
            )
            session.commit()
    except Exception as exc:
        logger.warning("audit_log insert failed action=%s entity=%s: %s", action, entity_type, exc)

    _ = db  # reserved for future same-session logging
