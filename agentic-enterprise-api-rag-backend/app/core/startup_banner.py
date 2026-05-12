"""One-shot startup diagnostics (console / uvicorn log)."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.runtime_metadata import get_runtime_metadata

logger = logging.getLogger("app.startup")


def log_startup_banner() -> None:
    """Log provider mode, vector target, build/pid, and key feature toggles once at process start."""
    collection = "unknown"
    try:
        from app.services.qdrant_client import qdrant_service

        collection = qdrant_service._active_collection_name()
    except Exception as exc:  # noqa: BLE001 — banner must never abort startup
        collection = f"(unresolved: {exc})"

    llm_p = (settings.LLM_PROVIDER or "ollama").strip().lower()
    emb_p = (settings.EMBEDDING_PROVIDER or "ollama").strip().lower()
    rt = get_runtime_metadata()

    lines = [
        f"=== {settings.APP_NAME} ({settings.ENVIRONMENT}) startup ===",
        f"BUILD_VERSION={settings.BUILD_VERSION}",
        f"process_pid={rt.get('process_pid')} process_start_time={rt.get('process_start_time')}",
        f"provider_llm={llm_p} provider_embeddings={emb_p}",
        f"vector_collection_target={collection}",
        f"ENABLE_AGENT_ORCHESTRATION={bool(settings.ENABLE_AGENT_ORCHESTRATION)}",
        f"ENABLE_CONVERSATION_SUMMARY={bool(settings.ENABLE_CONVERSATION_SUMMARY)}",
        "streaming_route=POST /api/v1/query/ask-stream (SSE; mounted when query router is active)",
        f"QDRANT_URL={settings.QDRANT_URL}",
        "runtime_metadata=GET /api/v1/health (field: runtime)",
    ]
    for line in lines:
        logger.info(line)
