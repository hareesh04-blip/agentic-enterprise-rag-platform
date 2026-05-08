from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.services.seed_service import ensure_seed_data

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    ensure_seed_data(db)
    user = db.execute(
        text("SELECT id, email, full_name, hashed_password, is_active FROM users WHERE email = :email"),
        {"email": payload.email},
    ).mappings().first()
    if user is None or not user["is_active"] or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user["email"], extra_claims={"user_id": user["id"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
        },
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    roles = db.execute(
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
    permissions = db.execute(
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
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "is_active": current_user["is_active"],
        "roles": roles,
        "permissions": permissions,
    }
