"""
Deterministic agent orchestration wrapper (no extra LLM agents).
Steps record intent, retrieval planning, retrieval, validation; generation stays in RagService.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.core.config import settings
from app.services.retrieval_service import retrieval_service
from app.services.rag_service import rag_service


AgentIntent = str


def classify_intent(question: str) -> AgentIntent:
    """Rule-based routing intent for diagnostics and retrieval hints only."""
    q = (question or "").lower()

    if any(
        x in q
        for x in (
            "authentication",
            "authenticate",
            "auth ",
            " bearer",
            "token",
            "jwt",
            "oauth",
            "client credential",
            "api key",
        )
    ):
        return "authentication"

    if any(
        x in q
        for x in (
            "error response",
            "error code",
            "failed response",
            "invalid ",
            "failure message",
            "return message",
            "error handling",
        )
    ):
        return "error_handling"

    if any(x in q for x in ("which api", "what api", "endpoint", "service pattern", "api reference")):
        return "api_lookup"

    if any(x in q for x in ("workflow", "step by step", "how do i", "process flow", "user journey")):
        return "product_workflow"

    if any(x in q for x in ("feature", "configure", "configuration", "setting", "product capability")):
        return "product_feature"

    if any(x in q for x in ("candidate", "resume", "screening", "skill", "hr ", "hiring", "interview")):
        return "hr_screening"

    return "general"


def plan_retrieval(intent: AgentIntent, requested_top_k: int) -> tuple[int, dict[str, Any]]:
    """Map intent to effective top_k only (metadata hints); retrieval API unchanged."""
    base = max(1, min(20, int(requested_top_k)))
    delta = 0
    notes = ""
    if intent == "api_lookup":
        delta = 2
        notes = "boost retrieval breadth for API identification questions"
    elif intent == "authentication":
        delta = 1
        notes = "slightly broader context for auth-related phrasing"
    elif intent == "error_handling":
        delta = 1
        notes = "slightly broader context for error / failure phrasing"
    elif intent in {"product_workflow", "product_feature"}:
        delta = 1
        notes = "slightly broader context for product questions"
    elif intent == "hr_screening":
        delta = 0
        notes = "default depth for HR-style questions"
    else:
        notes = "default planning for general or mixed intent"

    effective = max(1, min(20, base + delta))
    hints: dict[str, Any] = {
        "intent": intent,
        "requested_top_k": base,
        "effective_top_k": effective,
        "top_k_delta": delta,
        "notes": notes,
    }
    return effective, hints


def validate_context(retrieval_data: dict[str, Any]) -> dict[str, Any]:
    results = list(retrieval_data.get("results") or [])
    chunk_count = len(results)
    doc_types = Counter((item.get("document_type") or "unknown").strip().lower() or "unknown" for item in results)
    dominant = doc_types.most_common(1)[0][0] if doc_types else "unknown"
    insufficient_recommended = chunk_count == 0
    return {
        "chunk_count": chunk_count,
        "dominant_document_type": dominant,
        "insufficient_recommended": insufficient_recommended,
    }


class AgentOrchestrator:
    async def run_query_ask(
        self,
        *,
        project_id: int,
        knowledge_base_id: int,
        question: str,
        top_k: int,
        session_id: int | None,
        user_id: int,
        debug: bool,
    ) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []

        intent = classify_intent(question)
        steps.append({"step": "classify_intent", "status": "completed", "details": {"intent": intent}})

        effective_top_k, plan_hints = plan_retrieval(intent, top_k)
        steps.append(
            {
                "step": "plan_retrieval",
                "status": "completed",
                "details": plan_hints,
            }
        )

        retrieval_data = await retrieval_service.retrieve(
            project_id=project_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            top_k=effective_top_k,
        )
        results = retrieval_data.get("results") or []
        steps.append(
            {
                "step": "retrieve_context",
                "status": "completed",
                "details": {
                    "retrieval_mode": retrieval_data.get("retrieval_mode", "vector"),
                    "chunk_count": len(results),
                },
            }
        )

        validation = validate_context(retrieval_data)
        steps.append(
            {
                "step": "validate_context",
                "status": "completed",
                "details": validation,
            }
        )

        result = await rag_service.answer_question(
            project_id=project_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            top_k=top_k,
            session_id=session_id,
            user_id=user_id,
            debug=debug,
            prefetched_retrieval=retrieval_data,
        )

        steps.append(
            {
                "step": "generate_answer",
                "status": "completed",
                "details": {
                    "llm_status": result.get("llm_status"),
                    "retrieval_mode": result.get("retrieval_mode"),
                },
            }
        )
        steps.append(
            {
                "step": "package_response",
                "status": "completed",
                "details": {
                    "shape": "QueryResponse",
                    "keys": sorted(result.keys()),
                },
            }
        )

        # Orchestration trace fields are debug-only (same contract as other diagnostics).
        if debug:
            result.setdefault("diagnostics", {})
            result["diagnostics"]["agent_orchestration_enabled"] = True
            result["diagnostics"]["agent_steps"] = steps

        return result


agent_orchestrator = AgentOrchestrator()
