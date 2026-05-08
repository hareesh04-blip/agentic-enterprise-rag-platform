from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import hash_password
from app.db.database import get_db

router = APIRouter(prefix="/users")


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class UpdateUserRolesRequest(BaseModel):
    role_names: list[str]


class UpdateUserAccessRequest(BaseModel):
    knowledge_base_id: int
    access_level: str = "read"


@router.post("")
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users.manage")),
) -> dict:
    existing = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": payload.email}).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="User email already exists")
    user_id = db.execute(
        text(
            """
            INSERT INTO users (email, hashed_password, full_name, is_active)
            VALUES (:email, :hashed_password, :full_name, :is_active)
            RETURNING id
            """
        ),
        {
            "email": payload.email,
            "hashed_password": hash_password(payload.password),
            "full_name": payload.full_name,
            "is_active": True,
        },
    ).scalar()
    db.commit()
    return {"id": user_id, "email": payload.email, "full_name": payload.full_name, "is_active": True}


@router.get("")
def list_users(db: Session = Depends(get_db), _: dict = Depends(require_permission("users.manage"))) -> list[dict]:
    rows = db.execute(text("SELECT id, email, full_name, is_active, created_at FROM users ORDER BY id ASC")).mappings().all()
    return [
        {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "is_active": row["is_active"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("users.manage"))) -> dict:
    row = db.execute(
        text("SELECT id, email, full_name, is_active, created_at FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users.manage")),
) -> dict:
    user = db.execute(text("SELECT id, email, full_name, is_active FROM users WHERE id = :user_id"), {"user_id": user_id}).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    full_name = payload.full_name if payload.full_name is not None else user["full_name"]
    is_active = payload.is_active if payload.is_active is not None else user["is_active"]
    db.execute(
        text("UPDATE users SET full_name = :full_name, is_active = :is_active WHERE id = :user_id"),
        {"full_name": full_name, "is_active": is_active, "user_id": user_id},
    )
    db.commit()
    return {"id": user_id, "email": user["email"], "full_name": full_name, "is_active": is_active}


@router.put("/{user_id}/roles")
def update_user_roles(
    user_id: int,
    payload: UpdateUserRolesRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users.manage")),
) -> dict:
    exists = db.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="User not found")
    db.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id})
    for role_name in payload.role_names:
        role_id = db.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).scalar()
        if role_id:
            db.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
                {"user_id": user_id, "role_id": role_id},
            )
    db.commit()
    return {"user_id": user_id, "roles": payload.role_names}


@router.put("/{user_id}/access")
def update_user_access(
    user_id: int,
    payload: UpdateUserAccessRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users.manage")),
) -> dict:
    exists = db.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="User not found")
    kb_exists = db.execute(text("SELECT id FROM knowledge_bases WHERE id = :id"), {"id": payload.knowledge_base_id}).scalar()
    if not kb_exists:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    db.execute(
        text(
            """
            DELETE FROM user_knowledge_base_access
            WHERE user_id = :user_id AND knowledge_base_id = :knowledge_base_id
            """
        ),
        {"user_id": user_id, "knowledge_base_id": payload.knowledge_base_id},
    )
    db.execute(
        text(
            """
            INSERT INTO user_knowledge_base_access (user_id, knowledge_base_id, access_level)
            VALUES (:user_id, :knowledge_base_id, :access_level)
            """
        ),
        {
            "user_id": user_id,
            "knowledge_base_id": payload.knowledge_base_id,
            "access_level": payload.access_level,
        },
    )
    db.commit()
    return {
        "user_id": user_id,
        "knowledge_base_id": payload.knowledge_base_id,
        "access_level": payload.access_level,
    }
