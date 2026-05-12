"""
Embedding-time text hygiene: redact oversized secrets / JWT-like payloads and split long texts
so OpenAI embedding requests stay within safe input limits.

Used only on the path to embeddings — DB chunk_text in ingestion remains full fidelity unless
callers choose otherwise.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI text-embedding-3-small: 8192 tokens; conservative char budget (~3.5 chars/token EN prose).
_DEFAULT_MAX_CHARS = 24000
_OVERLAP_CHARS = 512

# JWT-like JWS compact forms (three base64url-ish segments).
_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
)

# Bearer / Authorization header long tokens
_BEARER_PATTERN = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-\.]{24,})")

# Key/value style token assignments (DOCX tables often paste full JWTs here)
_KV_ACCESS = re.compile(r'(?i)(\baccess_token\b\s*[:=]\s*)(["\']?)([^\s"\'`,\]\}]{36,})')
_KV_REFRESH = re.compile(r'(?i)(\brefresh_token\b\s*[:=]\s*)(["\']?)([^\s"\'`,\]\}]{36,})')
_KV_ID = re.compile(r'(?i)(\bid_token\b\s*[:=]\s*)(["\']?)([^\s"\'`,\]\}]{36,})')
_JSON_ACCESS = re.compile(r'(?i)("access_token"\s*:\s*")([^"]{36,})(")')
_JSON_REFRESH = re.compile(r'(?i)("refresh_token"\s*:\s*")([^"]{36,})(")')

# Very long bare alphanumeric / base64-ish runs (sample secrets pasted verbatim)
_LONG_SECRET_RUN = re.compile(r"[A-Za-z0-9+/=_\-]{200,}")


def redact_embedding_sensitive_content(text: str, *, chunk_type: str | None = None) -> str:
    """Replace JWT-like and oversized secret strings with placeholders; preserve structure."""
    if not text:
        return text

    out = text
    out = _JWT_PATTERN.sub("<JWT_TOKEN_REDACTED>", out)
    out = _BEARER_PATTERN.sub(r"\1<Bearer_TOKEN_REDACTED>", out)

    out = _KV_ACCESS.sub(r"\1\2<ACCESS_TOKEN_REDACTED>", out)
    out = _KV_REFRESH.sub(r"\1\2<REFRESH_TOKEN_REDACTED>", out)
    out = _KV_ID.sub(r"\1\2<ID_TOKEN_REDACTED>", out)
    out = _JSON_ACCESS.sub(r'\1<ACCESS_TOKEN_REDACTED>\3', out)
    out = _JSON_REFRESH.sub(r'\1<REFRESH_TOKEN_REDACTED>\3', out)

    out = _LONG_SECRET_RUN.sub("<LONG_TOKEN_REDACTED>", out)

    # Authentication chunks: extra pass for table-style "Authentication=Bearer ..."
    if chunk_type and "authentication" in chunk_type.lower():
        out = re.sub(
            r"(?i)(Authentication\s*[=:]\s*Bearer\s+)([^\s\n\r]{24,})",
            r"\1<Bearer_TOKEN_REDACTED>",
            out,
        )

    return out


def split_text_for_embedding(text: str, max_chars: int, overlap: int) -> list[str]:
    """Greedy segment split at paragraph/newline boundaries when possible."""
    if max_chars <= 0:
        return [text]
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    start = 0
    n = len(text)
    guard = 0
    while start < n and guard < n + 16:
        guard += 1
        chunk_end = min(start + max_chars, n)
        if chunk_end < n:
            window = text[start:chunk_end]
            break_idx = -1
            for sep in ("\n\n", "\n"):
                j = window.rfind(sep)
                if j > max_chars // 6:
                    break_idx = max(break_idx, j + len(sep))
            if break_idx < 0:
                j = window.rfind(" ")
                if j > max_chars // 6:
                    break_idx = j + 1
            if break_idx > 0:
                chunk_end = start + break_idx
        segment = text[start:chunk_end].strip()
        if segment:
            parts.append(segment)
        elif chunk_end >= n:
            break
        else:
            start = chunk_end
            continue
        if chunk_end >= n:
            break
        nxt = chunk_end - overlap
        start = max(nxt, start + 1)

    return parts if parts else [text[:max_chars]]


def prepare_embedding_text_segments(chunk: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """
    Returns text segments to embed (after redaction + optional splitting) and debug info.
    """
    raw = chunk.get("chunk_text") or ""
    chunk_type = chunk.get("chunk_type")
    metadata = chunk.get("metadata") or {}
    api_ref = metadata.get("api_reference_id") or "N/A"

    redacted = redact_embedding_sensitive_content(raw, chunk_type=str(chunk_type) if chunk_type else None)
    max_chars = int(getattr(settings, "EMBEDDING_INPUT_MAX_CHARS", _DEFAULT_MAX_CHARS) or _DEFAULT_MAX_CHARS)
    overlap = int(getattr(settings, "EMBEDDING_SPLIT_OVERLAP_CHARS", _OVERLAP_CHARS) or _OVERLAP_CHARS)

    parts = split_text_for_embedding(redacted, max_chars=max_chars, overlap=overlap)
    if not parts:
        parts = [" "]

    final_chars = sum(len(p) for p in parts)
    meta = {
        "chunk_type": chunk_type,
        "api_reference_id": api_ref,
        "original_chars": len(raw),
        "redacted_chars": len(redacted),
        "final_chars": final_chars,
        "segment_count": len(parts),
        "max_chars": max_chars,
    }
    if len(parts) > 1 or len(raw) != len(redacted) or len(raw) != final_chars:
        logger.info(
            "embedding_prep chunk_type=%s api_reference_id=%s original_chars=%s redacted_chars=%s "
            "final_chars=%s segments=%s",
            chunk_type,
            api_ref,
            len(raw),
            len(redacted),
            final_chars,
            len(parts),
        )
    return parts, meta


def average_normalized_vectors(vectors: list[list[float]]) -> list[float]:
    """Mean of embedding vectors with L2 normalization."""
    if not vectors:
        return []
    dim = len(vectors[0])
    acc = [0.0] * dim
    for v in vectors:
        if len(v) != dim:
            raise ValueError("embedding dimension mismatch for averaging")
        for i, x in enumerate(v):
            acc[i] += x
    n = float(len(vectors))
    mean = [x / n for x in acc]
    norm = math.sqrt(sum(x * x for x in mean))
    if norm <= 0:
        return mean
    return [x / norm for x in mean]
