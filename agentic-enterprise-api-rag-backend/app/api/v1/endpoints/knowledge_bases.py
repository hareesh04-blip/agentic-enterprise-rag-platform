from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.database import get_db
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate

router = APIRouter(prefix="/knowledge-bases")
ALLOWED_ACCESS_LEVELS = {"read", "write", "admin"}


class KnowledgeBaseAccessCreate(BaseModel):
    user_id: int
    access_level: str


class KnowledgeBaseAccessUpdate(BaseModel):
    access_level: str


@router.post("")
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    existing = db.execute(text("SELECT id FROM knowledge_bases WHERE name = :name"), {"name": payload.name}).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="Knowledge base name already exists")
    kb_id = db.execute(
        text(
            """
            INSERT INTO knowledge_bases (name, description, domain_type, is_active, created_by)
            VALUES (:name, :description, :domain_type, :is_active, :created_by)
            RETURNING id
            """
        ),
        {
            "name": payload.name,
            "description": payload.description,
            "domain_type": payload.domain_type,
            "is_active": payload.is_active,
            "created_by": current_user["id"],
        },
    ).scalar()
    db.execute(
        text(
            """
            INSERT INTO user_knowledge_base_access (user_id, knowledge_base_id, access_level)
            VALUES (:user_id, :knowledge_base_id, :access_level)
            """
        ),
        {"user_id": current_user["id"], "knowledge_base_id": kb_id, "access_level": "admin"},
    )
    db.commit()
    row = db.execute(
        text(
            """
            SELECT id, name, description, domain_type, is_active, created_by, created_at
            FROM knowledge_bases WHERE id = :id
            """
        ),
        {"id": kb_id},
    ).mappings().first()
    return _kb_response(row)


@router.get("")
def list_knowledge_bases(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id, name, description, domain_type, is_active, created_by, created_at
            FROM knowledge_bases
            ORDER BY id ASC
            """
        )
    ).mappings().all()
    return [_kb_response(row) for row in rows]


@router.get("/me")
def list_my_knowledge_bases(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    role_names = db.execute(
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
    permissions = set(
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
    is_platform_admin = ("super_admin" in role_names) or ("knowledge_bases.manage" in permissions)

    if is_platform_admin:
        rows = db.execute(
            text(
                """
                SELECT
                    kb.id,
                    kb.name,
                    kb.description,
                    kb.domain_type,
                    kb.is_active,
                    kb.created_by,
                    kb.created_at,
                    'admin'::text AS access_level,
                    (
                        SELECT COUNT(*)
                        FROM api_documents d
                        WHERE d.knowledge_base_id = kb.id
                    )::int AS document_count
                FROM knowledge_bases kb
                ORDER BY kb.id ASC
                """
            )
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                """
                SELECT
                    kb.id,
                    kb.name,
                    kb.description,
                    kb.domain_type,
                    kb.is_active,
                    kb.created_by,
                    kb.created_at,
                    uka.access_level,
                    (
                        SELECT COUNT(*)
                        FROM api_documents d
                        WHERE d.knowledge_base_id = kb.id
                    )::int AS document_count
                FROM user_knowledge_base_access uka
                JOIN knowledge_bases kb ON kb.id = uka.knowledge_base_id
                WHERE uka.user_id = :user_id
                ORDER BY kb.id ASC
                """
            ),
            {"user_id": current_user["id"]},
        ).mappings().all()

    return [_my_kb_response(dict(row), permissions) for row in rows]


@router.get("/{knowledge_base_id:int}")
def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    row = db.execute(
        text(
            """
            SELECT id, name, description, domain_type, is_active, created_by, created_at
            FROM knowledge_bases
            WHERE id = :id
            """
        ),
        {"id": knowledge_base_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return _kb_response(row)


@router.put("/{knowledge_base_id:int}")
def update_knowledge_base(
    knowledge_base_id: int,
    payload: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    existing = db.execute(
        text(
            """
            SELECT id, name, description, domain_type, is_active
            FROM knowledge_bases
            WHERE id = :id
            """
        ),
        {"id": knowledge_base_id},
    ).mappings().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    next_name = payload.name if payload.name is not None else existing["name"]
    if payload.name is not None:
        duplicate = db.execute(
            text("SELECT id FROM knowledge_bases WHERE name = :name AND id <> :id"),
            {"name": payload.name, "id": knowledge_base_id},
        ).scalar()
        if duplicate:
            raise HTTPException(status_code=409, detail="Knowledge base name already exists")

    db.execute(
        text(
            """
            UPDATE knowledge_bases
            SET name = :name,
                description = :description,
                domain_type = :domain_type,
                is_active = :is_active
            WHERE id = :id
            """
        ),
        {
            "id": knowledge_base_id,
            "name": next_name,
            "description": payload.description if payload.description is not None else existing["description"],
            "domain_type": payload.domain_type if payload.domain_type is not None else existing["domain_type"],
            "is_active": payload.is_active if payload.is_active is not None else existing["is_active"],
        },
    )
    db.commit()
    row = db.execute(
        text(
            """
            SELECT id, name, description, domain_type, is_active, created_by, created_at
            FROM knowledge_bases
            WHERE id = :id
            """
        ),
        {"id": knowledge_base_id},
    ).mappings().first()
    return _kb_response(row)


@router.delete("/{knowledge_base_id:int}")
def delete_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    existing = db.execute(text("SELECT id FROM knowledge_bases WHERE id = :id"), {"id": knowledge_base_id}).scalar()
    if not existing:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    db.execute(text("DELETE FROM user_knowledge_base_access WHERE knowledge_base_id = :id"), {"id": knowledge_base_id})
    db.execute(text("DELETE FROM knowledge_bases WHERE id = :id"), {"id": knowledge_base_id})
    db.commit()
    return {"status": "deleted", "id": knowledge_base_id}


@router.get("/{knowledge_base_id:int}/users")
def list_knowledge_base_users(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    _ensure_knowledge_base_exists(db, knowledge_base_id)
    rows = db.execute(
        text(
            """
            SELECT
                u.id AS user_id,
                u.email,
                u.full_name,
                uka.access_level,
                uka.created_at AS granted_at
            FROM user_knowledge_base_access uka
            JOIN users u ON u.id = uka.user_id
            WHERE uka.knowledge_base_id = :knowledge_base_id
            ORDER BY uka.id ASC
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    ).mappings().all()
    return {
        "knowledge_base_id": knowledge_base_id,
        "users": [
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "access_level": row["access_level"],
                "granted_at": row["granted_at"].isoformat() if row["granted_at"] else None,
            }
            for row in rows
        ],
    }


@router.post("/{knowledge_base_id:int}/users")
def grant_knowledge_base_access(
    knowledge_base_id: int,
    payload: KnowledgeBaseAccessCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    _ensure_knowledge_base_exists(db, knowledge_base_id)
    _ensure_user_exists(db, payload.user_id)
    access_level = _normalize_and_validate_access_level(payload.access_level)
    _upsert_kb_access(
        db=db,
        knowledge_base_id=knowledge_base_id,
        user_id=payload.user_id,
        access_level=access_level,
    )
    db.commit()
    return _get_kb_user_access_response(db, knowledge_base_id, payload.user_id)


@router.put("/{knowledge_base_id:int}/users/{user_id:int}")
def update_knowledge_base_access(
    knowledge_base_id: int,
    user_id: int,
    payload: KnowledgeBaseAccessUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    _ensure_knowledge_base_exists(db, knowledge_base_id)
    _ensure_user_exists(db, user_id)
    access_level = _normalize_and_validate_access_level(payload.access_level)
    existing = db.execute(
        text(
            """
            SELECT id
            FROM user_knowledge_base_access
            WHERE knowledge_base_id = :knowledge_base_id
              AND user_id = :user_id
            ORDER BY id ASC
            """
        ),
        {"knowledge_base_id": knowledge_base_id, "user_id": user_id},
    ).scalars().all()
    if not existing:
        raise HTTPException(status_code=404, detail="Knowledge base access mapping not found")
    db.execute(
        text(
            """
            UPDATE user_knowledge_base_access
            SET access_level = :access_level
            WHERE id = :id
            """
        ),
        {"access_level": access_level, "id": existing[0]},
    )
    if len(existing) > 1:
        db.execute(
            text("DELETE FROM user_knowledge_base_access WHERE id = ANY(:duplicate_ids)"),
            {"duplicate_ids": existing[1:]},
        )
    db.commit()
    return _get_kb_user_access_response(db, knowledge_base_id, user_id)


@router.delete("/{knowledge_base_id:int}/users/{user_id:int}")
def delete_knowledge_base_access(
    knowledge_base_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("knowledge_bases.manage")),
) -> dict:
    _ensure_knowledge_base_exists(db, knowledge_base_id)
    _ensure_user_exists(db, user_id)
    deleted = db.execute(
        text(
            """
            DELETE FROM user_knowledge_base_access
            WHERE knowledge_base_id = :knowledge_base_id
              AND user_id = :user_id
            """
        ),
        {"knowledge_base_id": knowledge_base_id, "user_id": user_id},
    )
    if deleted.rowcount == 0:
        raise HTTPException(status_code=404, detail="Knowledge base access mapping not found")
    db.commit()
    return {"status": "deleted", "knowledge_base_id": knowledge_base_id, "user_id": user_id}


def _ensure_knowledge_base_exists(db: Session, knowledge_base_id: int) -> None:
    exists = db.execute(text("SELECT id FROM knowledge_bases WHERE id = :id"), {"id": knowledge_base_id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


def _ensure_user_exists(db: Session, user_id: int) -> None:
    exists = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="User not found")


def _normalize_and_validate_access_level(access_level: str) -> str:
    normalized = access_level.strip().lower()
    if normalized not in ALLOWED_ACCESS_LEVELS:
        raise HTTPException(status_code=422, detail="access_level must be one of: read, write, admin")
    return normalized


def _upsert_kb_access(db: Session, knowledge_base_id: int, user_id: int, access_level: str) -> None:
    existing = db.execute(
        text(
            """
            SELECT id
            FROM user_knowledge_base_access
            WHERE knowledge_base_id = :knowledge_base_id
              AND user_id = :user_id
            ORDER BY id ASC
            """
        ),
        {"knowledge_base_id": knowledge_base_id, "user_id": user_id},
    ).scalars().all()
    if not existing:
        db.execute(
            text(
                """
                INSERT INTO user_knowledge_base_access (user_id, knowledge_base_id, access_level)
                VALUES (:user_id, :knowledge_base_id, :access_level)
                """
            ),
            {
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "access_level": access_level,
            },
        )
        return
    db.execute(
        text(
            """
            UPDATE user_knowledge_base_access
            SET access_level = :access_level
            WHERE id = :id
            """
        ),
        {"access_level": access_level, "id": existing[0]},
    )
    if len(existing) > 1:
        db.execute(
            text("DELETE FROM user_knowledge_base_access WHERE id = ANY(:duplicate_ids)"),
            {"duplicate_ids": existing[1:]},
        )


def _get_kb_user_access_response(db: Session, knowledge_base_id: int, user_id: int) -> dict:
    row = db.execute(
        text(
            """
            SELECT
                u.id AS user_id,
                u.email,
                u.full_name,
                uka.knowledge_base_id,
                uka.access_level,
                uka.created_at AS granted_at
            FROM user_knowledge_base_access uka
            JOIN users u ON u.id = uka.user_id
            WHERE uka.knowledge_base_id = :knowledge_base_id
              AND uka.user_id = :user_id
            ORDER BY uka.id ASC
            LIMIT 1
            """
        ),
        {"knowledge_base_id": knowledge_base_id, "user_id": user_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge base access mapping not found")
    return {
        "knowledge_base_id": row["knowledge_base_id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "access_level": row["access_level"],
        "granted_at": row["granted_at"].isoformat() if row["granted_at"] else None,
    }


def _kb_response(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "domain_type": row["domain_type"],
        "is_active": row["is_active"],
        "created_by": row["created_by"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _my_kb_response(row: dict, permissions: set[str]) -> dict:
    access_level = str(row.get("access_level") or "read")
    can_query = ("query.ask" in permissions) and (access_level in {"read", "write", "admin"})
    can_upload = (("documents.upload" in permissions) or ("ingestion.run" in permissions)) and (
        access_level in {"write", "admin"}
    )
    can_manage = ("knowledge_bases.manage" in permissions) or (access_level == "admin")
    can_view_documents = (
        ("ingestion.run" in permissions) or ("documents.upload" in permissions) or ("query.ask" in permissions)
    ) and (access_level in {"read", "write", "admin"})
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "domain_type": row.get("domain_type"),
        "is_active": row["is_active"],
        "created_by": row["created_by"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "access_level": access_level,
        "can_query": can_query,
        "can_upload": can_upload,
        "can_manage": can_manage,
        "can_view_documents": can_view_documents,
        "document_count": int(row.get("document_count") or 0),
    }
