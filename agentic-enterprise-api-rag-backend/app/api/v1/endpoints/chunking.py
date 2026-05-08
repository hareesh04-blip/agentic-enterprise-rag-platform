from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import require_permission
from app.services.chunking_service import api_chunking_service
from app.services.docx_parser_service import docx_parser_service

router = APIRouter(prefix="/chunking")


@router.post("/preview-docx-chunks")
async def preview_docx_chunks(
    file: UploadFile = File(...),
    _: dict = Depends(require_permission("documents.upload")),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        parsed = docx_parser_service.parse_preview(file.filename, file_bytes)
        chunks = api_chunking_service.create_chunks(parsed)

        return {
            "file_name": parsed.get("file_name"),
            "document_title": parsed.get("document_title"),
            "api_count": parsed.get("api_count", 0),
            "chunk_count": len(chunks),
            "chunks_preview": [
                {
                    "chunk_type": chunk["chunk_type"],
                    "api_reference_id": chunk["metadata"].get("api_reference_id"),
                    "service_name": chunk["metadata"].get("service_name"),
                    "text_preview": (chunk["chunk_text"][:240] + "...") if len(chunk["chunk_text"]) > 240 else chunk["chunk_text"],
                }
                for chunk in chunks
            ],
            "chunks_full": chunks,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chunking preview failed: {exc}") from exc
