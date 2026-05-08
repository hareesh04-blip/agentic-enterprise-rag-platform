from enum import Enum

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import check_knowledge_base_access, get_current_user, require_permission
from app.db.database import get_db
from app.services.ingestion_service import ingestion_service

router = APIRouter(prefix="/ingestion")


class DocumentType(str, Enum):
    api = "api"
    product = "product"
    hr = "hr"


@router.post("/ingest-docx")
async def ingest_docx(
    project_id: int = Form(...),
    knowledge_base_id: int = Form(...),
    document_type: DocumentType = Form(DocumentType.api),
    source_domain: str | None = Form(default=None),
    product_name: str | None = Form(default=None),
    version: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("ingestion.run")),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        kb_exists = db.execute(
            text("SELECT id FROM knowledge_bases WHERE id = :knowledge_base_id AND is_active = TRUE"),
            {"knowledge_base_id": knowledge_base_id},
        ).scalar()
        if not kb_exists:
            raise HTTPException(status_code=404, detail="Knowledge base not found or inactive")
        has_access = check_knowledge_base_access(
            db=db,
            user_id=current_user["id"],
            knowledge_base_id=knowledge_base_id,
            access_level="write",
        )
        if not has_access:
            raise HTTPException(status_code=403, detail="Knowledge base access denied")

        return await ingestion_service.ingest_docx(
            db,
            project_id=project_id,
            knowledge_base_id=knowledge_base_id,
            document_type=document_type.value,
            source_domain=source_domain,
            product_name=product_name,
            version=version,
            file_name=file.filename,
            file_bytes=file_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@router.get("/jobs/{job_id}")
def get_ingestion_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("ingestion.run")),
) -> dict:
    result = db.execute(
        text(
            """
            SELECT
                id,
                project_id,
                document_id,
                status,
                total_endpoints,
                processed_chunks,
                error_message,
                started_at,
                completed_at
            FROM ingestion_jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": job_id},
    )
    job = result.mappings().first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found")
    return {
        "id": job["id"],
        "project_id": job["project_id"],
        "document_id": job["document_id"],
        "status": job["status"],
        "total_endpoints": job["total_endpoints"],
        "processed_chunks": job["processed_chunks"],
        "error_message": job["error_message"],
        "started_at": job["started_at"].isoformat() if job["started_at"] else None,
        "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
    }


@router.get("/documents/{document_id}/endpoints")
def get_document_endpoints(
    document_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("ingestion.run")),
) -> dict:
    result = db.execute(
        text(
            """
            SELECT
                api_reference_id,
                service_name,
                service_group,
                service_method,
                service_pattern,
                d.knowledge_base_id,
                kb.name AS knowledge_base_name
            FROM api_endpoints
            JOIN api_documents d ON d.id = api_endpoints.document_id
            LEFT JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
            WHERE api_endpoints.document_id = :document_id
            ORDER BY api_endpoints.id ASC
            """
        ),
        {"document_id": document_id},
    )
    endpoints = result.mappings().all()
    doc_row = db.execute(
        text(
            """
            SELECT
                d.id,
                d.file_name,
                d.document_type,
                d.source_domain,
                d.product_name,
                d.document_version,
                d.knowledge_base_id,
                kb.name AS knowledge_base_name,
                d.created_at
            FROM api_documents d
            LEFT JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
            WHERE d.id = :document_id
            """
        ),
        {"document_id": document_id},
    ).mappings().first()
    if doc_row is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return {
        "document_id": doc_row["id"],
        "file_name": doc_row["file_name"],
        "document_type": doc_row["document_type"],
        "source_domain": doc_row["source_domain"],
        "product_name": doc_row["product_name"],
        "document_version": doc_row["document_version"],
        "knowledge_base_id": doc_row["knowledge_base_id"],
        "knowledge_base_name": doc_row["knowledge_base_name"],
        "created_at": doc_row["created_at"].isoformat() if doc_row["created_at"] else None,
        "endpoints": [
            {
                "api_reference_id": endpoint["api_reference_id"],
                "service_name": endpoint["service_name"],
                "service_group": endpoint["service_group"],
                "service_method": endpoint["service_method"],
                "service_pattern": endpoint["service_pattern"],
            }
            for endpoint in endpoints
        ],
    }


@router.get("/documents")
def list_documents(
    document_type: DocumentType | None = None,
    product_name: str | None = None,
    knowledge_base_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    role_names = set(
        db.execute(
            text(
                """
                SELECT r.name
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = :user_id
                """
            ),
            {"user_id": current_user["id"]},
        ).scalars().all()
    )
    permission_codes = set(
        db.execute(
            text(
                """
                SELECT DISTINCT p.code
                FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = :user_id
                """
            ),
            {"user_id": current_user["id"]},
        ).scalars().all()
    )
    if not {"ingestion.run", "documents.upload", "query.ask"} & permission_codes:
        raise HTTPException(
            status_code=403,
            detail="Document listing requires one of: ingestion.run, documents.upload, query.ask",
        )
    is_platform_admin = "super_admin" in role_names or "knowledge_bases.manage" in permission_codes

    if knowledge_base_id is not None and not is_platform_admin:
        has_access = check_knowledge_base_access(
            db=db,
            user_id=current_user["id"],
            knowledge_base_id=knowledge_base_id,
            access_level="read",
        )
        if not has_access:
            raise HTTPException(status_code=403, detail="Knowledge base access denied")

    result = db.execute(
        text(
            """
            SELECT
                d.id,
                d.project_id,
                d.file_name,
                d.document_type,
                d.source_domain,
                d.product_name,
                d.document_version,
                d.knowledge_base_id,
                kb.name AS knowledge_base_name,
                d.created_at
            FROM api_documents d
            LEFT JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
            WHERE (:document_type IS NULL OR d.document_type = :document_type)
              AND (:knowledge_base_id IS NULL OR d.knowledge_base_id = :knowledge_base_id)
              AND (
                :is_platform_admin = TRUE
                OR EXISTS (
                    SELECT 1
                    FROM user_knowledge_base_access uka
                    WHERE uka.user_id = :user_id
                      AND uka.knowledge_base_id = d.knowledge_base_id
                )
              )
              AND (:product_name IS NULL OR LOWER(COALESCE(d.product_name, '')) = LOWER(:product_name))
            ORDER BY d.id DESC
            """
        ),
        {
            "document_type": document_type.value if document_type else None,
            "product_name": product_name,
            "knowledge_base_id": knowledge_base_id,
            "is_platform_admin": is_platform_admin,
            "user_id": current_user["id"],
        },
    ).mappings().all()
    return {
        "filters": {
            "document_type": document_type.value if document_type else None,
            "product_name": product_name,
            "knowledge_base_id": knowledge_base_id,
        },
        "documents": [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "file_name": row["file_name"],
                "document_type": row["document_type"],
                "source_domain": row["source_domain"],
                "product_name": row["product_name"],
                "document_version": row["document_version"],
                "knowledge_base_id": row["knowledge_base_id"],
                "knowledge_base_name": row["knowledge_base_name"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in result
        ],
    }
