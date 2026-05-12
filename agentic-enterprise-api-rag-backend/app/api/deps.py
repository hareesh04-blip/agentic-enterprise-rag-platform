from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="Paste JWT access token returned by /api/v1/auth/login",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    row = db.execute(
        text("SELECT id, email, full_name, is_active FROM users WHERE id = :user_id"),
        {"user_id": int(user_id)},
    ).mappings().first()
    if row is None or not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return dict(row)


def require_role(role_name: str):
    def dependency(current_user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = :user_id AND r.name = :role_name
                LIMIT 1
                """
            ),
            {"user_id": current_user["id"], "role_name": role_name},
        ).scalar()
        if not exists:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role required: {role_name}")
        return current_user

    return dependency


def require_permission(permission_code: str):
    def dependency(current_user: dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = :user_id AND p.code = :permission_code
                LIMIT 1
                """
            ),
            {"user_id": current_user["id"], "permission_code": permission_code},
        ).scalar()
        if not exists:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {permission_code}")
        return current_user

    return dependency


def require_knowledge_base_access(access_level: str = "read"):
    def dependency(
        knowledge_base_id: int,
        current_user: dict[str, Any] = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        has_access = db.execute(
            text(
                """
                SELECT 1
                FROM user_knowledge_base_access uka
                WHERE uka.user_id = :user_id
                  AND uka.knowledge_base_id = :knowledge_base_id
                  AND (
                    (:access_level = 'read' AND uka.access_level IN ('read', 'write', 'admin'))
                    OR (:access_level = 'write' AND uka.access_level IN ('write', 'admin'))
                    OR (:access_level = 'admin' AND uka.access_level = 'admin')
                  )
                LIMIT 1
                """
            ),
            {
                "user_id": current_user["id"],
                "knowledge_base_id": knowledge_base_id,
                "access_level": access_level,
            },
        ).scalar()
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Knowledge base access denied")
        return current_user

    return dependency


def require_admin_or_super_admin(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Restrict routes to users with role `super_admin` or `admin` only.
    """
    allowed = db.execute(
        text(
            """
            SELECT 1
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = :user_id
              AND r.name IN ('super_admin', 'admin')
            LIMIT 1
            """
        ),
        {"user_id": current_user["id"]},
    ).scalar()
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or super admin role required",
        )
    return current_user


def check_knowledge_base_access(db: Session, user_id: int, knowledge_base_id: int, access_level: str = "read") -> bool:
    has_access = db.execute(
        text(
            """
            SELECT 1
            FROM user_knowledge_base_access uka
            WHERE uka.user_id = :user_id
              AND uka.knowledge_base_id = :knowledge_base_id
              AND (
                (:access_level = 'read' AND uka.access_level IN ('read', 'write', 'admin'))
                OR (:access_level = 'write' AND uka.access_level IN ('write', 'admin'))
                OR (:access_level = 'admin' AND uka.access_level = 'admin')
              )
            LIMIT 1
            """
        ),
        {
            "user_id": user_id,
            "knowledge_base_id": knowledge_base_id,
            "access_level": access_level,
        },
    ).scalar()
    return bool(has_access)
