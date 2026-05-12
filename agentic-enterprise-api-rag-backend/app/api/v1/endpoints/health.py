from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_or_super_admin
from app.core.config import settings
from app.core.runtime_metadata import get_runtime_metadata
from app.db.database import check_db_connection
from app.services.qdrant_client import qdrant_service

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "runtime": get_runtime_metadata(),
    }


def _llm_model_name() -> str:
    if (settings.LLM_PROVIDER or "ollama").strip().lower() == "openai":
        return settings.OPENAI_LLM_MODEL
    return settings.OLLAMA_LLM_MODEL


def _embedding_model_name() -> str:
    if (settings.EMBEDDING_PROVIDER or "ollama").strip().lower() == "openai":
        return settings.OPENAI_EMBEDDING_MODEL
    return settings.OLLAMA_EMBEDDING_MODEL


def _build_platform_status() -> dict[str, Any]:
    backend_ok = True
    backend = {
        "status": "ok" if backend_ok else "error",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }

    database: dict[str, Any] = {"status": "unknown", "message": None}
    try:
        check_db_connection()
        database = {"status": "ok", "message": None}
    except Exception as exc:
        database = {"status": "error", "message": str(exc)}

    qdrant: dict[str, Any] = {
        "status": "unknown",
        "url": settings.QDRANT_URL,
        "collection_name": None,
        "collection_exists": False,
        "point_count": 0,
        "embedding_dimension_configured": None,
        "embedding_dimension_matches": None,
        "message": None,
    }
    try:
        qdrant["collection_name"] = qdrant_service._active_collection_name()
        exists = qdrant_service.collection_exists()
        qdrant["collection_exists"] = exists
        qdrant["point_count"] = qdrant_service.collection_point_count() if exists else 0
        qdrant["embedding_dimension_configured"] = qdrant_service.get_configured_vector_size()
        qdrant["embedding_dimension_matches"] = qdrant_service.embedding_dim_matches_settings()
        qdrant["status"] = "ok"
    except Exception as exc:
        qdrant["status"] = "error"
        qdrant["message"] = str(exc)

    providers = {
        "llm_provider": (settings.LLM_PROVIDER or "ollama").strip().lower(),
        "embedding_provider": (settings.EMBEDDING_PROVIDER or "ollama").strip().lower(),
        "llm_model": _llm_model_name(),
        "embedding_model": _embedding_model_name(),
        "vector_collection": qdrant.get("collection_name"),
    }

    feature_flags = {
        "ENABLE_HYBRID_RETRIEVAL": bool(settings.ENABLE_HYBRID_RETRIEVAL),
        "ENABLE_METADATA_RERANKING": bool(settings.ENABLE_METADATA_RERANKING),
        "ENABLE_SUGGESTED_QUESTIONS": bool(settings.ENABLE_SUGGESTED_QUESTIONS),
        "ENABLE_CONFIDENCE_SCORING": bool(settings.ENABLE_CONFIDENCE_SCORING),
        "ENABLE_IMPACT_ANALYSIS": bool(settings.ENABLE_IMPACT_ANALYSIS),
    }

    issues: list[str] = []
    if database["status"] != "ok":
        issues.append("database_unavailable")
    if qdrant["status"] != "ok":
        issues.append("qdrant_unavailable")
    elif qdrant.get("embedding_dimension_matches") is False:
        issues.append("vector_dimension_mismatch")

    if database["status"] != "ok" or qdrant["status"] != "ok":
        overall = "unhealthy"
    elif issues:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "overall_status": overall,
        "backend": backend,
        "database": database,
        "qdrant": qdrant,
        "providers": providers,
        "feature_flags": feature_flags,
        "issues": issues,
        "runtime": get_runtime_metadata(),
    }


@router.get("/status")
def platform_status(_: dict[str, Any] = Depends(require_admin_or_super_admin)) -> dict[str, Any]:
    """
    Admin/super-admin only: full platform health for operations dashboard.
    """
    return _build_platform_status()
