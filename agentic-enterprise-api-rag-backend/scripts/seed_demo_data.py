"""
Step 42 — Idempotent demo data seeder (feedback, improvement tasks, audit trail).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_BACKEND_ROOT = str(Path(__file__).resolve().parents[1])
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.db.database import SessionLocal  # noqa: E402
from app.services.demo_data_service import seed_demo_data  # noqa: E402


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo feedback, tasks, and audit activity (idempotent).")
    parser.add_argument("--dry-run", action="store_true", help="No writes; plan only.")
    args = parser.parse_args()
    dry_run = bool(args.dry_run) or _truthy_env("DEMO_SEED_DRY_RUN")
    email = os.environ.get("DEMO_SEED_EMAIL", "superadmin@local").strip()
    kb_name = os.environ.get("DEMO_SEED_KB_NAME", "").strip() or None

    with SessionLocal() as db:
        result = seed_demo_data(db, email=email, kb_name=kb_name, dry_run=dry_run)
        if dry_run:
            db.rollback()
        else:
            db.commit()

    mode = "DRY-RUN (no changes)" if dry_run else "APPLY"
    print(f"Demo data seed - {mode}")
    print(f"  User: {result['user']['email']} (id={result['user']['id']})")
    print(f"  Knowledge base: {result['knowledge_base']['name']!r} (id={result['knowledge_base']['id']})")
    print("  Feedback rows:")
    if dry_run:
        print(f"    would create: {result['feedback']['planned']}")
        print(f"    skipped (already present): {result['feedback']['skipped']}")
    else:
        print(f"    created: {result['feedback']['created']}")
        print(f"    skipped (already present): {result['feedback']['skipped']}")
    print("  Improvement tasks:")
    if dry_run:
        print(f"    would create: {result['tasks']['planned']}")
        print(f"    skipped (already present): {result['tasks']['skipped']}")
    else:
        print(f"    created: {result['tasks']['created']}")
        print(f"    skipped (already present): {result['tasks']['skipped']}")
    print(f"  Audit log inserts: {result['audit_log_inserts'] if not dry_run else 0}")
    if dry_run:
        print("  (Dry-run: no database inserts and no audit writes were performed.)")


if __name__ == "__main__":
    main()
