from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from app.core.security import hash_password
from app.db.database import SessionLocal


@dataclass
class DemoUserSeed:
    email: str
    full_name: str
    password: str
    role: str
    kb_name: str
    access_level: str


SEEDS = [
    DemoUserSeed(
        email="qa@local",
        full_name="QA Demo User",
        password="QaDemo@123",
        role="qa",
        kb_name="Product Documentation",
        access_level="read",
    ),
    DemoUserSeed(
        email="hr@local",
        full_name="HR Demo User",
        password="HrDemo@123",
        role="hr_basic",
        kb_name="HR Resume Screening",
        access_level="read",
    ),
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "qa": ["query.ask", "chat.read", "admin.read"],
    "hr_basic": ["query.ask", "chat.read"],
}


def ensure_role_with_permissions(db, role_name: str, permission_codes: list[str]) -> int:
    role_id = db.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).scalar()
    if not role_id:
        role_id = db.execute(
            text(
                """
                INSERT INTO roles (name, description)
                VALUES (:name, :description)
                RETURNING id
                """
            ),
            {"name": role_name, "description": f"Demo role: {role_name}"},
        ).scalar()

    for code in permission_codes:
        permission_id = db.execute(text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).scalar()
        if not permission_id:
            continue
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM role_permissions
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
    return int(role_id)


def upsert_demo_user(db, seed: DemoUserSeed) -> None:
    user_row = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": seed.email},
    ).first()
    if user_row:
        user_id = int(user_row[0])
    else:
        user_id = int(
            db.execute(
                text(
                    """
                    INSERT INTO users (email, hashed_password, full_name, is_active)
                    VALUES (:email, :hashed_password, :full_name, :is_active)
                    RETURNING id
                    """
                ),
                {
                    "email": seed.email,
                    "hashed_password": hash_password(seed.password),
                    "full_name": seed.full_name,
                    "is_active": True,
                },
            ).scalar()
        )

    role_id = ensure_role_with_permissions(db, seed.role, ROLE_PERMISSIONS[seed.role])
    db.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id})
    db.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
        {"user_id": user_id, "role_id": role_id},
    )

    kb_id = db.execute(text("SELECT id FROM knowledge_bases WHERE name = :name"), {"name": seed.kb_name}).scalar()
    if not kb_id:
        raise RuntimeError(f"Knowledge base not found: {seed.kb_name}")

    db.execute(
        text(
            """
            DELETE FROM user_knowledge_base_access
            WHERE user_id = :user_id AND knowledge_base_id = :kb_id
            """
        ),
        {"user_id": user_id, "kb_id": kb_id},
    )
    db.execute(
        text(
            """
            INSERT INTO user_knowledge_base_access (user_id, knowledge_base_id, access_level)
            VALUES (:user_id, :kb_id, :access_level)
            """
        ),
        {"user_id": user_id, "kb_id": kb_id, "access_level": seed.access_level},
    )


def main() -> None:
    db = SessionLocal()
    try:
        for seed in SEEDS:
            upsert_demo_user(db, seed)
        db.commit()
        print("Seeded demo users: qa@local, hr@local")
    finally:
        db.close()


if __name__ == "__main__":
    main()
