from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.services.chunking_service import api_chunking_service
from app.services.docx_parser_service import docx_parser_service
from app.services.embedding_service import embedding_service
from app.services.openai_client import openai_client

router = APIRouter(prefix="/embedding")


class EmbedTextRequest(BaseModel):
    text: str


@router.post("/embed-text-test")
async def embed_text_test(payload: EmbedTextRequest) -> dict:
    try:
        embedding = await embedding_service.embed_text(payload.text)
        provider = (settings.EMBEDDING_PROVIDER or "ollama").strip().lower()
        model = (
            settings.OPENAI_EMBEDDING_MODEL
            if provider == "openai"
            else settings.OLLAMA_EMBEDDING_MODEL
        )
        return {
            "provider": provider,
            "model": model,
            "embedding_dimension": len(embedding),
            "first_5_values": embedding[:5],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Text embedding failed: {exc}") from exc


@router.post("/embed-docx-chunks-preview")
async def embed_docx_chunks_preview(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        parsed = docx_parser_service.parse_preview(file.filename, file_bytes)
        chunks = api_chunking_service.create_chunks(parsed)
        chunks_to_embed = chunks[:3]
        embedded = await embedding_service.embed_chunks(chunks_to_embed)

        return {
            "file_name": parsed.get("file_name"),
            "total_chunks": len(chunks),
            "embedded_chunks": len(embedded),
            "preview": [
                {
                    "chunk_type": item.get("chunk_type"),
                    "api_reference_id": (item.get("metadata") or {}).get("api_reference_id"),
                    "service_name": (item.get("metadata") or {}).get("service_name"),
                    "embedding_dimension": len(item.get("embedding", [])),
                    "first_5_values": item.get("embedding", [])[:5],
                }
                for item in embedded
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DOCX chunk embedding preview failed: {exc}") from exc
