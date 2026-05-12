"""Process/runtime snapshot for health endpoints and stale-build verification."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

_PROCESS_BOOT_MONOTONIC = time.monotonic()
_PROCESS_START_WALL_UTC = datetime.now(timezone.utc)
_PROCESS_PID = os.getpid()


def get_runtime_metadata() -> dict[str, Any]:
    """
    Lightweight JSON-safe snapshot of this running process.
    Use BUILD_VERSION + process_pid + process_start_time to confirm which binary is live after restart.
    """
    uptime_s = round(time.monotonic() - _PROCESS_BOOT_MONOTONIC, 3)
    active_collection: str | None = None
    try:
        from app.services.qdrant_client import qdrant_service

        active_collection = qdrant_service._active_collection_name()
    except Exception:
        active_collection = None

    llm_p = (settings.LLM_PROVIDER or "ollama").strip().lower()
    emb_p = (settings.EMBEDDING_PROVIDER or "ollama").strip().lower()

    return {
        "build_version": settings.BUILD_VERSION,
        "process_start_time": _PROCESS_START_WALL_UTC.isoformat(),
        "process_pid": _PROCESS_PID,
        "backend_uptime_seconds": uptime_s,
        "llm_provider": llm_p,
        "embedding_provider": emb_p,
        "active_vector_collection": active_collection,
        "app_env": settings.ENVIRONMENT,
        "app_name": settings.APP_NAME,
        "stale_process_hint": (
            "After deploy, confirm build_version matches the release tag and that process_start_time/pid "
            "changed when you restarted uvicorn."
        ),
    }
