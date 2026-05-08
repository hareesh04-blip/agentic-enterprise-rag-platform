from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password

DEFAULT_PERMISSIONS = [
    "documents.upload",
    "ingestion.run",
    "query.ask",
    "chat.read",
    "users.manage",
    "knowledge_bases.manage",
    "admin.read",
]

DEFAULT_ROLES = {
    "super_admin": DEFAULT_PERMISSIONS,
    "admin": ["documents.upload", "ingestion.run", "query.ask", "chat.read", "users.manage"],
    "analyst": ["query.ask", "chat.read"],
}


def ensure_seed_data(db: Session) -> None:
    for code in DEFAULT_PERMISSIONS:
        db.execute(
            text(
                """
                INSERT INTO permissions (code, description)
                VALUES (:code, :description)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"code": code, "description": f"Permission for {code}"},
        )

    for role_name in DEFAULT_ROLES.keys():
        db.execute(
            text(
                """
                INSERT INTO roles (name, description)
                VALUES (:name, :description)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": role_name, "description": f"Default role {role_name}"},
        )

    for role_name, permission_codes in DEFAULT_ROLES.items():
        role_id = db.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).scalar()
        for code in permission_codes:
            permission_id = db.execute(text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).scalar()
            if role_id and permission_id:
                exists = db.execute(
                    text(
                        """
                        SELECT 1 FROM role_permissions
                        WHERE role_id = :role_id AND permission_id = :permission_id
                        LIMIT 1
                        """
                    ),
                    {"role_id": role_id, "permission_id": permission_id},
                ).scalar()
                if not exists:
                    db.execute(
                        text(
                            """
                            INSERT INTO role_permissions (role_id, permission_id)
                            VALUES (:role_id, :permission_id)
                            """
                        ),
                        {"role_id": role_id, "permission_id": permission_id},
                    )

    admin_email = "superadmin@local"
    admin_user = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": admin_email}).scalar()
    if not admin_user:
        admin_id = db.execute(
            text(
                """
                INSERT INTO users (email, hashed_password, full_name, is_active)
                VALUES (:email, :hashed_password, :full_name, :is_active)
                RETURNING id
                """
            ),
            {
                "email": admin_email,
                "hashed_password": hash_password("SuperAdmin@123"),
                "full_name": "Default Super Admin",
                "is_active": True,
            },
        ).scalar()
        super_admin_role_id = db.execute(text("SELECT id FROM roles WHERE name = 'super_admin'")).scalar()
        if admin_id and super_admin_role_id:
            exists = db.execute(
                text(
                    """
                    SELECT 1 FROM user_roles
                    WHERE user_id = :user_id AND role_id = :role_id
                    LIMIT 1
                    """
                ),
                {"user_id": admin_id, "role_id": super_admin_role_id},
            ).scalar()
            if not exists:
                db.execute(
                    text(
                        """
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES (:user_id, :role_id)
                        """
                    ),
                    {"user_id": admin_id, "role_id": super_admin_role_id},
                )

    db.commit()
