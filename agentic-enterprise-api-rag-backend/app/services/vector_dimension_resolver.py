from __future__ import annotations

from app.core.config import settings


def get_active_vector_size() -> int:
    """
    Resolve expected vector size for the active embedding provider.

    - EMBEDDING_PROVIDER=openai -> size based on OPENAI_EMBEDDING_MODEL (text-embedding-3-small -> 1536)
    - EMBEDDING_PROVIDER=ollama -> settings.EMBEDDING_DIM (existing behavior, e.g. 768)
    """
    provider = (getattr(settings, "EMBEDDING_PROVIDER", "ollama") or "ollama").strip().lower()
    if provider == "openai":
        model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        # Known dimension for text-embedding-3-small; keep logic centralized here.
        if model == "text-embedding-3-small":
            return 1536
        # Fallback: if a different OpenAI embedding is configured, prefer its expected dim if known.
        # Until additional mappings are needed, default to 1536 for OpenAI embeddings.
        return 1536
    # Default / Ollama path stays with existing embedding dim
    return settings.EMBEDDING_DIM

