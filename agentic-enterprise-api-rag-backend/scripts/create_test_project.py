from sqlalchemy import text

from app.db.database import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        row = db.execute(text("SELECT id FROM api_projects ORDER BY id LIMIT 1")).fetchone()
        print("existing_project_id=", row[0] if row else None)
        if row is None:
            created = db.execute(
                text(
                    "INSERT INTO api_projects (name, description) "
                    "VALUES ('Test API Project', 'POC test project') "
                    "RETURNING id"
                )
            ).fetchone()
            db.commit()
            print("created_project_id=", created[0] if created else None)
    finally:
        db.close()


if __name__ == "__main__":
    main()
