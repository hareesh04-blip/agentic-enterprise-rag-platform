"""
Step 43 — Remove only Step 42 demo-seeded rows ([DEMO_SEED_42] markers).

Does not delete users, KBs, or unrelated production data. Script-only.

Match rules:
  - query_feedback.question_text contains literal "[DEMO_SEED_42]"
  - improvement_tasks.title contains literal "[DEMO_SEED_42]"
  - audit_logs: metadata_json marks seed (JSON source == DEMO_SEED_42 or text contains marker)

Env:
  DEMO_RESET_DRY_RUN=true|false   (also: --dry-run)

Delete order (FK-safe):
  1) improvement_tasks (seed titles)
  2) query_feedback (seed questions, only if no remaining task references that row)
  3) audit_logs (seed metadata only)

Run from backend package root:
  python scripts/reset_demo_data.py --dry-run
  python scripts/reset_demo_data.py
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
from app.services.demo_data_service import SEED_MARKER, SEED_TAG, reset_demo_data  # noqa: E402


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove Step 42 demo seed data only (idempotent, transactional).")
    parser.add_argument("--dry-run", action="store_true", help="List rows to delete; no commits.")
    args = parser.parse_args()
    dry_run = bool(args.dry_run) or _truthy_env("DEMO_RESET_DRY_RUN")

    with SessionLocal() as db:
        result = reset_demo_data(db, dry_run=dry_run)
        task_rows = result["task_rows"]
        fb_deletable = result["feedback_rows"]
        fb_blocked = result["skipped_unsafe_feedback"]
        audit_rows = result["audit_rows"]

        print("Demo reset - DRY-RUN (no changes)" if dry_run else "Demo reset - APPLY")
        print(f"  Marker in titles/questions: {SEED_MARKER!r}")
        print(f"  Marker in audit JSON: source={SEED_TAG!r} or text contains {SEED_MARKER!r}")
        print()
        print(f"  Improvement tasks to delete: {len(task_rows)}")
        for r in task_rows:
            print(f"    - id={r['id']} feedback_id={r['feedback_id']} title={str(r['title'])[:120]!r}")

        print(f"  Query feedback rows (marker match): {len(fb_deletable) + len(fb_blocked)}")
        print(f"    deletable (no non-seed task references): {len(fb_deletable)}")
        for r in fb_deletable:
            print(f"    - id={r['id']} question={str(r['question_text'])[:100]!r}")

        if fb_blocked:
            print(f"  Skipped / unsafe feedback (still referenced by non-seed tasks): {len(fb_blocked)}")
            for b in fb_blocked:
                print(f"    - feedback_id={b['feedback_id']}: blocked by task(s) {b['blocked_by_tasks']}")
        else:
            print("  Skipped / unsafe feedback: 0")

        print(f"  Audit logs to delete: {len(audit_rows)}")
        for r in audit_rows[:50]:
            print(f"    - id={r['id']} action={r['action']!r} entity={r['entity_type']!r} entity_id={r['entity_id']}")
        if len(audit_rows) > 50:
            print(f"    ... and {len(audit_rows) - 50} more")

        if dry_run:
            db.rollback()
            print()
            print("  (Dry-run: no deletes performed.)")
            return

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        print()
        print("  Done: committed deletes.")


if __name__ == "__main__":
    main()
