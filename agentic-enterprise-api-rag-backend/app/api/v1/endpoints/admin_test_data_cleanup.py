from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_super_admin
from app.services.test_data_cleanup_service import CleanupFlags, plan_and_execute

router = APIRouter()
logger = logging.getLogger(__name__)


class TestDataCleanupRequest(BaseModel):
    knowledge_base_id: int = Field(..., ge=1)
    delete_documents: bool = True
    delete_vectors: bool = True
    delete_chat_sessions: bool = True
    delete_feedback: bool = False
    delete_improvement_tasks: bool = False
    dry_run: bool = True
    include_demo_seed: bool = False
    delete_audit_logs: bool = False


@router.post("/test-data/cleanup")
def post_test_data_cleanup(
    body: TestDataCleanupRequest,
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    """
    KB-scoped cleanup for ingestion/query E2E resets. Does not delete users, roles, KB rows, or
    demo-seeded feedback/tasks unless ``include_demo_seed`` is true.
    """
    flags = CleanupFlags(
        knowledge_base_id=body.knowledge_base_id,
        delete_documents=body.delete_documents,
        delete_vectors=body.delete_vectors,
        delete_chat_sessions=body.delete_chat_sessions,
        delete_feedback=body.delete_feedback,
        delete_improvement_tasks=body.delete_improvement_tasks,
        include_demo_seed=body.include_demo_seed,
        delete_audit_logs=body.delete_audit_logs,
        dry_run=body.dry_run,
    )
    try:
        return plan_and_execute(db, flags)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[admin.demo] test-data cleanup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cleanup failed; see server logs.",
        ) from exc
