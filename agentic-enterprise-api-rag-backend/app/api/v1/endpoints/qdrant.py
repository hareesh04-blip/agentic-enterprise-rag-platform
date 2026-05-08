from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_permission
from app.core.config import settings
from app.services.qdrant_client import qdrant_service

router = APIRouter(prefix="/qdrant")


@router.get("/health")
def qdrant_health(_: dict = Depends(require_permission("admin.read"))) -> dict:
    try:
        qdrant_service.health_check()
        exists = qdrant_service.collection_exists()
        return {
            "status": "healthy",
            "url": settings.QDRANT_URL,
            "collection": settings.QDRANT_COLLECTION,
            "collection_exists": exists,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant health check failed: {exc}") from exc


@router.post("/init-collection")
def qdrant_init_collection(_: dict = Depends(require_permission("admin.read"))) -> dict:
    try:
        qdrant_service.create_collection_if_not_exists()
        return {
            "status": "success",
            "collection": settings.QDRANT_COLLECTION,
            "vector_size": settings.EMBEDDING_DIM,
            "distance": "Cosine",
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant collection initialization failed: {exc}") from exc
