"""Step 51 — provider completion retry (empty then success)."""

import asyncio

from app.services.rag_service import (
    INSUFFICIENT_CONTEXT_ANSWER,
    MIN_PROMPT_CONTEXT_CHARS_SUBSTANTIVE,
    PROVIDER_GENERATION_FAILURE_ANSWER,
    RagService,
)


def test_generate_with_provider_retry_second_attempt_succeeds() -> None:
    svc = RagService()
    calls: list[int] = []

    async def fake_single(_prompt: str, _provider: str) -> str:
        calls.append(1)
        return "" if len(calls) == 1 else "x" * MIN_PROMPT_CONTEXT_CHARS_SUBSTANTIVE

    svc._single_llm_generate = fake_single  # type: ignore[method-assign]

    async def run() -> None:
        text, diag = await svc._generate_with_provider_retry("prompt", "openai")
        assert text is not None and len(text.strip()) >= 12
        assert diag.get("provider_retry_attempted") is True
        assert diag.get("provider_retry_reason") == "empty_or_weak_response"

    asyncio.run(run())


def test_resolve_failure_substantive_context_is_provider_not_insufficient() -> None:
    svc = RagService()
    results = [{"chunk_text": "a"}]
    diag = {"final_prompt_context_chars": MIN_PROMPT_CONTEXT_CHARS_SUBSTANTIVE + 10}
    ans, status = svc._resolve_llm_failure_answer(results=results, prompt_context_diag=diag)
    assert status == "fallback_provider_generation_failure"
    assert ans == PROVIDER_GENERATION_FAILURE_ANSWER
    assert ans != INSUFFICIENT_CONTEXT_ANSWER


def test_resolve_failure_sparse_context_is_insufficient() -> None:
    svc = RagService()
    results = [{"chunk_text": "a"}]
    diag = {"final_prompt_context_chars": 10, "selected_prompt_chunk_count": 0}
    ans, status = svc._resolve_llm_failure_answer(results=results, prompt_context_diag=diag)
    assert status == "fallback_insufficient_context"
    assert ans == INSUFFICIENT_CONTEXT_ANSWER
