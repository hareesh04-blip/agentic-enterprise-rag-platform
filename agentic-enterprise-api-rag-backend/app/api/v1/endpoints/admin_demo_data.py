from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_super_admin
from app.api.v1.admin_demo_logging import log_demo_endpoint_failure
from app.services.demo_data_service import get_seed_status, reset_demo_data, seed_demo_data

router = APIRouter()
logger = logging.getLogger(__name__)


class DemoDataOperationRequest(BaseModel):
    dry_run: bool = False
    email: str = "superadmin@local"
    knowledge_base_name: str | None = None


@router.get("/demo-data/status")
def demo_data_status(
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    try:
        return get_seed_status(db)
    except Exception:
        log_demo_endpoint_failure(logger, "GET /admin/demo-data/status")
        raise


@router.post("/demo-data/seed")
def demo_data_seed(
    body: DemoDataOperationRequest,
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    try:
        result = seed_demo_data(
            db,
            email=body.email.strip() or "superadmin@local",
            kb_name=(body.knowledge_base_name or "").strip() or None,
            dry_run=body.dry_run,
        )
        if body.dry_run:
            db.rollback()
        else:
            db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/demo-data/reset")
def demo_data_reset(
    body: DemoDataOperationRequest,
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    try:
        result = reset_demo_data(db, dry_run=body.dry_run)
        if body.dry_run:
            db.rollback()
        else:
            db.commit()
        return result
    except Exception:
        db.rollback()
        raise

