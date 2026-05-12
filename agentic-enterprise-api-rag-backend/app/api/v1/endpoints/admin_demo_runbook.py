from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_or_super_admin

router = APIRouter()


@router.get("/demo-runbook")
def get_demo_runbook(_: dict[str, Any] = Depends(require_admin_or_super_admin)) -> dict[str, Any]:
    """
    Read-only admin runbook: exact commands and checks before a demo (no server-side execution).
    """
    return {
        "title": "Demo runbook",
        "description": "Commands and checks to run before presenting the platform. Paths assume backend repo root.",
        "sections": [
            {
                "id": "start-backend",
                "title": "Start backend",
                "notes": [
                    "Run from agentic-enterprise-api-rag-backend (or your backend root).",
                    "Do not use --reload in production-style demos unless your runbook explicitly allows it.",
                ],
                "commands": [
                    "cd agentic-enterprise-api-rag-backend",
                    "uvicorn app.main:app --host 127.0.0.1 --port 8010",
                ],
            },
            {
                "id": "start-frontend",
                "title": "Start frontend",
                "notes": ["Run from the frontend workspace root."],
                "commands": [
                    "cd frontend",
                    "npm install",
                    "npm run dev",
                ],
            },
            {
                "id": "run-migrations",
                "title": "Run migrations",
                "notes": [
                    "Requires DATABASE_URL and PostgreSQL reachable.",
                    "Run once after pulling schema changes.",
                ],
                "commands": [
                    "cd agentic-enterprise-api-rag-backend",
                    "alembic upgrade head",
                ],
            },
            {
                "id": "seed-demo-data",
                "title": "Seed demo data",
                "notes": [
                    "Idempotent; safe to re-run. Uses DEMO_SEED_EMAIL (default superadmin@local) and optional DEMO_SEED_KB_NAME.",
                    "Use --dry-run to preview without writes.",
                ],
                "commands": [
                    "cd agentic-enterprise-api-rag-backend",
                    "python scripts/seed_demo_data.py --dry-run",
                    "python scripts/seed_demo_data.py",
                ],
            },
            {
                "id": "smoke-runner",
                "title": "Run smoke runner",
                "notes": [
                    "Set DEMO_SMOKE_JWT or DEMO_SMOKE_EMAIL + DEMO_SMOKE_PASSWORD.",
                    "Default API base: http://127.0.0.1:8010/api/v1",
                    "If smoke or curl returns 404 for routes that exist in code, run list_routes.py to confirm the running app’s registered paths.",
                ],
                "commands": [
                    "cd agentic-enterprise-api-rag-backend",
                    "python scripts/demo_smoke_runner.py",
                    "python scripts/list_routes.py",
                ],
            },
            {
                "id": "export-evidence-pack",
                "title": "Export evidence pack",
                "notes": [
                    "JSON: GET /api/v1/admin/demo-evidence-pack (Bearer token).",
                    "PDF: GET /api/v1/admin/demo-evidence-pack/pdf (Bearer token).",
                    "Or use the Admin UI: Evidence Pack page (Download JSON / Download PDF).",
                ],
                "commands": [],
            },
            {
                "id": "troubleshoot-stale-backend",
                "title": "Troubleshooting stale backend process",
                "notes": [
                    "If smoke checks return 404 for routes that exist in code, an old uvicorn may still be bound to port 8010.",
                    "Windows (PowerShell): find listener on 8010 and stop the owning process, then start uvicorn again.",
                ],
                "commands": [
                    "Get-NetTCPConnection -LocalPort 8010 -State Listen",
                    "# Note OwningProcess, then:",
                    "Stop-Process -Id <PID> -Force",
                    "cd agentic-enterprise-api-rag-backend",
                    "uvicorn app.main:app --host 127.0.0.1 --port 8010",
                ],
            },
            {
                "id": "common-demo-urls",
                "title": "Common demo URLs",
                "notes": ["Adjust host/port if your local setup differs."],
                "commands": [
                    "Backend health: http://127.0.0.1:8010/api/v1/health",
                    "API docs: http://127.0.0.1:8010/docs",
                    "Frontend (Vite default): http://127.0.0.1:5173",
                ],
            },
        ],
    }
