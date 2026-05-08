from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.retrieval_service import EmbeddingUnavailableError, retrieval_service

router = APIRouter(prefix="/retrieval")


class RetrievalSearchRequest(BaseModel):
    project_id: int
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


@router.get("/vector-count")
def get_vector_count() -> dict:
    try:
        vectors_count = retrieval_service.get_vector_count()
        return {
            "collection": settings.QDRANT_COLLECTION,
            "vectors_count": vectors_count,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vector count check failed: {exc}") from exc


@router.post("/search")
async def retrieval_search(payload: RetrievalSearchRequest) -> dict:
    try:
        return await retrieval_service.retrieve(
            project_id=payload.project_id,
            question=payload.question,
            top_k=payload.top_k,
        )
    except EmbeddingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval search failed: {exc}") from exc
