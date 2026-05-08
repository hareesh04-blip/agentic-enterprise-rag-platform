from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import Depends

from app.api.deps import require_permission
from app.services.docx_parser_service import docx_parser_service

router = APIRouter(prefix="/parser")


@router.post("/parse-docx-preview")
async def parse_docx_preview(
    file: UploadFile = File(...),
    _: dict = Depends(require_permission("documents.upload")),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        return docx_parser_service.parse_preview(file.filename, file_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DOCX parsing failed: {exc}") from exc
