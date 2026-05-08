from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.database import get_db

router = APIRouter(prefix="/db")


@router.get("/health")
def db_health(
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("admin.read")),
) -> dict:
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "healthy",
            "database": "PostgreSQL",
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {exc}") from exc
