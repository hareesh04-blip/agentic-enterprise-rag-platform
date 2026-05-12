from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_super_admin
from app.api.v1.admin_demo_logging import log_demo_endpoint_failure
from app.api.v1.endpoints import health as health_endpoints
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

CheckStatus = Literal["pass", "warn", "fail"]
OverallStatus = Literal["ready", "warning", "blocked"]


def _repo_root() -> Path:
    # app/api/v1/endpoints/this_file.py -> parents[4] = backend package root
    return Path(__file__).resolve().parents[4]


def _smoke_script_path() -> Path:
    return _repo_root() / "scripts" / "retrieval_smoke_test.py"


def _provider_check() -> tuple[CheckStatus, str]:
    llm = (settings.LLM_PROVIDER or "ollama").strip().lower()
    emb = (settings.EMBEDDING_PROVIDER or "ollama").strip().lower()
    needs_openai = llm == "openai" or emb == "openai"
    key = (settings.OPENAI_API_KEY or "").strip()
    if needs_openai and not key:
        return "fail", "OpenAI is selected for LLM and/or embeddings but OPENAI_API_KEY is not set."
    parts = [f"LLM={llm}", f"embeddings={emb}"]
    if needs_openai:
        parts.append("OpenAI API key is present.")
    else:
        parts.append("Ollama providers configured; ensure Ollama is reachable for the demo.")
    return "pass", "; ".join(parts)


def build_demo_readiness_payload(db: Session) -> dict[str, Any]:
    """Shared readiness snapshot for `/admin/demo-readiness` and `/admin/demo-script`."""
    platform = health_endpoints._build_platform_status()

    active_kb = int(db.execute(text("SELECT COUNT(*) FROM knowledge_bases WHERE is_active = true")).scalar_one())
    documents_count = int(db.execute(text("SELECT COUNT(*) FROM api_documents")).scalar_one())
    feedback_count = int(db.execute(text("SELECT COUNT(*) FROM query_feedback")).scalar_one())
    open_tasks = int(
        db.execute(
            text("SELECT COUNT(*) FROM improvement_tasks WHERE status IN ('open', 'in_progress')"),
        ).scalar_one()
    )
    high_open = int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM improvement_tasks "
                "WHERE status IN ('open', 'in_progress') AND priority = 'high'",
            ),
        ).scalar_one()
    )
    recent_audit = int(
        db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= NOW() - INTERVAL '7 days'"),
        ).scalar_one()
    )

    checks: list[dict[str, str]] = []

    checks.append(
        {
            "name": "Backend health",
            "status": "pass",
            "message": f"API process responding ({settings.APP_NAME}, {settings.ENVIRONMENT}).",
        }
    )

    db_status: CheckStatus = "pass" if platform["database"]["status"] == "ok" else "fail"
    db_msg = platform["database"].get("message") or "PostgreSQL connection OK."
    if db_status == "fail":
        db_msg = str(platform["database"].get("message") or "Database unreachable.")
    checks.append({"name": "Database reachable", "status": db_status, "message": db_msg})

    q = platform["qdrant"]
    q_status: CheckStatus
    q_msg: str
    if q["status"] != "ok":
        q_status = "fail"
        q_msg = str(q.get("message") or "Qdrant unreachable or error.")
    elif q.get("embedding_dimension_matches") is False:
        q_status = "warn"
        q_msg = "Qdrant is reachable but vector dimension does not match embedding configuration."
    else:
        q_status = "pass"
        q_msg = f"Qdrant OK (collection={q.get('collection_name')!r}, points≈{q.get('point_count', 0)})."
    checks.append({"name": "Qdrant reachable", "status": q_status, "message": q_msg})

    kb_status: CheckStatus = "pass" if active_kb >= 1 else "fail"
    checks.append(
        {
            "name": "At least one active knowledge base",
            "status": kb_status,
            "message": f"{active_kb} active knowledge base(s)." if active_kb else "No active knowledge bases.",
        }
    )

    doc_status: CheckStatus = "pass" if documents_count >= 1 else "fail"
    checks.append(
        {
            "name": "At least one ingested document",
            "status": doc_status,
            "message": f"{documents_count} document row(s) in api_documents."
            if documents_count
            else "No documents ingested; RAG demo will be empty.",
        }
    )

    prov_status, prov_msg = _provider_check()
    checks.append({"name": "Provider configuration present", "status": prov_status, "message": prov_msg})

    if high_open == 0:
        task_status: CheckStatus = "pass"
        task_msg = "No high-priority open or in-progress improvement tasks."
    else:
        task_status = "warn"
        task_msg = f"{high_open} high-priority task(s) still open or in progress."
    checks.append({"name": "No high-priority open improvement tasks", "status": task_status, "message": task_msg})

    smoke_path = _smoke_script_path()
    if smoke_path.is_file():
        smoke_status: CheckStatus = "pass"
        smoke_msg = f"Retrieval smoke test script present at scripts/{smoke_path.name}."
    else:
        smoke_status = "warn"
        smoke_msg = "retrieval_smoke_test.py not found at expected path; CLI smoke checks may be unavailable."
    checks.append({"name": "Recent smoke test script availability", "status": smoke_status, "message": smoke_msg})

    recommendations: list[str] = []
    if db_status != "ok":
        recommendations.append("Restore PostgreSQL connectivity before demo.")
    if q["status"] != "ok":
        recommendations.append("Start or repair Qdrant and verify QDRANT_URL and collection settings.")
    elif q.get("embedding_dimension_matches") is False:
        recommendations.append("Align EMBEDDING_DIM / provider settings with the Qdrant collection vector size.")
    if active_kb < 1:
        recommendations.append("Create and activate at least one knowledge base.")
    if documents_count < 1:
        recommendations.append("Upload and ingest at least one document into an active knowledge base.")
    if prov_status == "fail":
        recommendations.append("Set OPENAI_API_KEY in the environment or switch LLM/embedding providers to Ollama.")
    if high_open > 0:
        recommendations.append("Resolve or downgrade high-priority improvement tasks before a polished demo.")
    if smoke_status == "warn":
        recommendations.append("Restore scripts/retrieval_smoke_test.py in the deployment bundle for ops validation.")
    if feedback_count == 0:
        recommendations.append("Optional: collect a few query feedback samples to show quality loops in the admin UI.")
    if recent_audit == 0:
        recommendations.append("Optional: perform a few audited admin actions so the audit trail is non-empty for demos.")

    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    if has_fail:
        overall: OverallStatus = "blocked"
    elif has_warn:
        overall = "warning"
    else:
        overall = "ready"

    return {
        "overall_status": overall,
        "checks": checks,
        "summary": {
            "active_knowledge_bases": active_kb,
            "documents_count": documents_count,
            "feedback_count": feedback_count,
            "open_improvement_tasks": open_tasks,
            "recent_audit_logs": recent_audit,
        },
        "recommendations": recommendations,
    }


@router.get("/demo-readiness")
def get_demo_readiness(
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    try:
        return build_demo_readiness_payload(db)
    except Exception:
        log_demo_endpoint_failure(logger, "GET /admin/demo-readiness")
        raise
