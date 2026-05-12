"""Tests for embedding-time redaction and splitting (Step 58)."""

from __future__ import annotations

import asyncio

import pytest

from app.core.config import settings
from app.services.chunking_service import create_document_chunks
from app.services.docx_parser_service import docx_parser_service
from app.services.embedding_text_prepare import (
    prepare_embedding_text_segments,
    redact_embedding_sensitive_content,
    split_text_for_embedding,
)
from tests.test_docx_ingestion_quality import _build_qr_util_style_docx_bytes


def test_redacts_compact_jwt_and_bearer() -> None:
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "dozjgNryP4J3jVmNHl0w5N_XJSrIe0UcP87DQrUkBZs"
    )
    text = f'Authorization: Bearer {jwt}\n"access_token":"{jwt}"'
    out = redact_embedding_sensitive_content(text)
    assert jwt not in out
    assert "<JWT_TOKEN_REDACTED>" in out


def test_authentication_chunk_preserves_oauth_semantics_redacts_secrets() -> None:
    long_secret = "x" * 250
    raw = (
        "OAuth2 Client Credentials flow. grant_type=client_credentials "
        "client_id=my-client client_secret=my-secret-keep-short "
        f"access_token={long_secret} refresh_token={long_secret} "
        "Non-prod access token expiry 540s; prod 60s. "
        "Use Authorization: Bearer <token> on subsequent requests.\n"
        f"Authentication=Bearer {long_secret}"
    )
    out = redact_embedding_sensitive_content(raw, chunk_type="authentication_chunk")
    assert "OAuth2" in out and "client_credentials" in out and "540" in out and "60" in out
    assert long_secret not in out
    assert "Bearer" in out


def test_long_chunk_split_under_max_chars() -> None:
    raw = "Intro paragraph.\n\n" + ("word " * 25000)
    max_chars = min(settings.EMBEDDING_INPUT_MAX_CHARS, 4000)
    parts = split_text_for_embedding(raw, max_chars=max_chars, overlap=64)
    assert len(parts) >= 2
    assert all(len(p) <= max_chars + 50 for p in parts)


def test_authentication_chunk_embedding_prep_is_safe() -> None:
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzIjoieCJ9."
        "sig"
    ) + "A" * 5000
    raw = (
        "General Authentication: OAuth2 Client Credentials. "
        f"Sample access_token: {jwt} refresh_token: {jwt}\n"
        "Bearer header on API calls."
    )
    chunk = {
        "chunk_text": raw,
        "chunk_type": "authentication_chunk",
        "metadata": {"api_reference_id": "AUTH"},
    }
    segs, meta = prepare_embedding_text_segments(chunk)
    max_chars = settings.EMBEDDING_INPUT_MAX_CHARS
    assert all(len(s) <= max_chars for s in segs)
    assert jwt not in "".join(segs)
    assert meta["final_chars"] <= meta["original_chars"]


def test_qr_util_style_docx_chunks_embedding_prep_safe() -> None:
    parsed = docx_parser_service.parse_preview("qr_util.docx", _build_qr_util_style_docx_bytes())
    chunks = create_document_chunks(parsed, document_type="api")
    max_chars = settings.EMBEDDING_INPUT_MAX_CHARS
    for chunk in chunks:
        segs, meta = prepare_embedding_text_segments(chunk)
        assert all(len(s) <= max_chars for s in segs)
        assert meta["segment_count"] >= 1


def test_embed_chunks_one_failure_does_not_block_others(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.embedding_service import EmbeddingService

    svc = EmbeddingService()

    async def fake_embed(text: str) -> list[float]:
        if "EMBED_FAIL" in text:
            raise RuntimeError("400 Bad Request")
        return [0.02] * settings.EMBEDDING_DIM

    monkeypatch.setattr(svc, "embed_text", fake_embed)

    out = asyncio.run(
        svc.embed_chunks(
            [
                {"chunk_text": "alpha content", "chunk_type": "t1", "metadata": {}},
                {"chunk_text": "EMBED_FAIL marker", "chunk_type": "t2", "metadata": {}},
                {"chunk_text": "beta content", "chunk_type": "t3", "metadata": {}},
            ]
        )
    )
    assert out[0]["embedding"] is not None
    assert out[1].get("embedding") is None
    assert out[2]["embedding"] is not None
