from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_super_admin
from app.api.v1.admin_demo_logging import log_demo_endpoint_failure
from app.api.v1.endpoints.admin_demo_readiness import build_demo_readiness_payload

router = APIRouter()
logger = logging.getLogger(__name__)


def _demo_sections() -> list[dict[str, Any]]:
    return [
        {
            "id": "demo-readiness",
            "name": "Demo Readiness",
            "objective": "Confirm the environment is safe to present before walking stakeholders through features.",
            "route": "/admin/demo-readiness",
            "talking_points": [
                "Open the readiness dashboard to show pass/warn/fail checks at a glance.",
                "Call out overall status: ready, warning, or blocked, and tie it to recommendations.",
                "Mention summary counts (KBs, documents, feedback, tasks, recent audit) as evidence of platform use.",
            ],
            "expected_outcome": "Audience understands go/no-go signals and what would block a live demo.",
        },
        {
            "id": "system-health",
            "name": "System Health",
            "objective": "Show operational depth: database, Qdrant, providers, and feature flags.",
            "route": "/admin/health",
            "talking_points": [
                "Explain that this is the same stack the RAG pipeline depends on.",
                "Highlight healthy vs degraded states and any listed issues.",
            ],
            "expected_outcome": "Stakeholders trust that infra is visible and monitored, not a black box.",
        },
        {
            "id": "knowledge-base-selection",
            "name": "Knowledge Base Selection",
            "objective": "Demonstrate tenant-style isolation: the assistant and documents follow the selected KB.",
            "route": "/",
            "talking_points": [
                "From Workspace Home, use the KB selector in the shell to switch context.",
                "Explain RBAC: users only see KBs they are allowed to use; isolation carries into chat and documents.",
            ],
            "expected_outcome": "Audience sees how multi-KB enterprise rollouts are modeled in the UI.",
        },
        {
            "id": "document-upload",
            "name": "Document Upload / Ingestion",
            "objective": "Show how curated content enters the retrieval index.",
            "route": "/documents",
            "talking_points": [
                "Upload or reference an existing ingested DOCX/API artifact for the active KB.",
                "Mention validation, chunking, and vector upsert as background steps the platform performs.",
            ],
            "expected_outcome": "Audience connects documents in the library to answers in chat.",
        },
        {
            "id": "chat-with-sources",
            "name": "Chat with Sources",
            "objective": "Deliver the core RAG story: grounded answers with cited chunks.",
            "route": "/chat",
            "talking_points": [
                "Ask a domain question that should hit ingested content.",
                "Expand sources, show chunk metadata, and tie answers back to the KB.",
            ],
            "expected_outcome": "Clear before/after: question → retrieval-backed answer with traceable sources.",
        },
        {
            "id": "streaming-response",
            "name": "Streaming Response",
            "objective": "Optionally contrast streaming vs non-streaming UX if enabled in your build.",
            "route": "/chat",
            "talking_points": [
                "Toggle streaming in chat if available; narrate token-by-token perceived latency wins.",
                "Note that the underlying `/query/ask` contract remains for integrations.",
            ],
            "expected_outcome": "Audience sees a modern assistant experience without API breakage.",
        },
        {
            "id": "conversation-memory",
            "name": "Conversation Memory",
            "objective": "Show multi-turn behavior and session-scoped memory.",
            "route": "/chat",
            "talking_points": [
                "Stay in one chat session; ask a follow-up that depends on prior context.",
                "Mention rolling summaries and session boundaries when relevant to your audience.",
            ],
            "expected_outcome": "Stakeholders experience continuity, not a stateless FAQ bot.",
        },
        {
            "id": "retrieval-diagnostics",
            "name": "Retrieval Diagnostics",
            "objective": "Peel back the answer: ranked chunks without generating an LLM reply.",
            "route": "/admin/retrieval-diagnostics",
            "talking_points": [
                "Run a retrieval test for the same KB and question used in chat.",
                "Walk through chunk scores, types, and empty-retrieval as a tuning signal.",
            ],
            "expected_outcome": "Technical buyers see transparency and a path to improve recall.",
        },
        {
            "id": "agent-trace",
            "name": "Agent Trace",
            "objective": "When orchestration is enabled, show deterministic pre-RAG steps in the assistant UI.",
            "route": "/chat",
            "talking_points": [
                "After a response, open the Agent trace panel if orchestration ran.",
                "Explain intent detection, retrieval parameters, and guardrails as an audit-friendly layer.",
            ],
            "expected_outcome": "Audience understands controlled agent steps vs opaque prompt-only behavior.",
        },
        {
            "id": "feedback-submission",
            "name": "Feedback Submission",
            "objective": "Close the loop: capture thumbs and optional comments on answers.",
            "route": "/chat",
            "talking_points": [
                "Rate an answer thumbs up or down and optionally add a short comment.",
                "Tie feedback to KB and session for downstream analytics and tasks.",
            ],
            "expected_outcome": "Quality signals are captured in-product, not lost in email.",
        },
        {
            "id": "feedback-analytics",
            "name": "Feedback Analytics",
            "objective": "Aggregate signal for admins: trends and recent negative feedback.",
            "route": "/admin/feedback-analytics",
            "talking_points": [
                "Show thumbs-up rate and per-KB breakdown.",
                "Pick a recent negative example to justify an improvement task.",
            ],
            "expected_outcome": "Leaders see measurable quality and a path from signal to action.",
        },
        {
            "id": "improvement-tasks",
            "name": "Improvement Tasks",
            "objective": "Operationalize remediation: tasks linked to feedback and KB.",
            "route": "/admin/improvement-tasks",
            "talking_points": [
                "Create or review a task; show analyze panel and resolution notes if applicable.",
                "Explain priority and status for governance.",
            ],
            "expected_outcome": "Audience sees a lightweight ITSM-style queue for RAG quality.",
        },
        {
            "id": "audit-logs",
            "name": "Audit Logs",
            "objective": "Demonstrate governance: who did what, on which KB and entity.",
            "route": "/admin/audit-logs",
            "talking_points": [
                "Filter by action or entity type after performing a few admin actions earlier.",
                "Relate rows to improvement tasks, feedback, or uploads shown in the demo.",
            ],
            "expected_outcome": "Compliance-minded stakeholders see an append-only style trail for key actions.",
        },
    ]


@router.get("/demo-script")
def get_demo_script(
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_admin_or_super_admin),
) -> dict[str, Any]:
    try:
        return {
            "title": "Agentic Enterprise API RAG Platform Demo",
            "sections": _demo_sections(),
            "demo_readiness": build_demo_readiness_payload(db),
        }
    except Exception:
        log_demo_endpoint_failure(logger, "GET /admin/demo-script")
        raise
