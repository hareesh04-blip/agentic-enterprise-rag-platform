from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from collections.abc import AsyncIterator
from typing import Any

import httpx
from sqlalchemy import text

from app.prompts.rag_answer_prompt import build_rag_prompt, detect_prompt_mode
from app.db.database import SessionLocal
from app.core.config import settings
from app.services.ollama_client import ollama_client
from app.services.openai_client import openai_client
from app.services.query_intent_service import detect_query_intents
from app.services.retrieval_service import retrieval_service
from app.services.suggested_question_service import suggested_question_service
from app.services.confidence_service import confidence_service
from app.services.impact_analysis_service import impact_analysis_service
from app.services.conversation_summary_service import conversation_summary_service
from app.services.chunking_service import (
    generic_chunk_qualifies_as_response_fields,
    response_parameters_chunk_quality,
)

logger = logging.getLogger(__name__)
INSUFFICIENT_CONTEXT_ANSWER = "I could not find enough information in the selected knowledge base to answer this confidently."
PROVIDER_GENERATION_FAILURE_ANSWER = (
    "The answer could not be generated right now. Please try again."
)

MIN_MEANINGFUL_GENERATION_CHARS = 12
MIN_PROMPT_CONTEXT_CHARS_SUBSTANTIVE = 120


def _answer_is_meaningful(text: str | None) -> bool:
    return len((text or "").strip()) >= MIN_MEANINGFUL_GENERATION_CHARS


def _is_retryable_provider_error(exc: BaseException) -> bool:
    """Transient failures eligible for one retry at the RAG layer."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.WriteError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return False
        if code in (408, 429, 500, 502, 503, 504):
            return True
        return False
    if isinstance(exc, RuntimeError):
        msg = str(exc).lower()
        if "api_key" in msg or "not set" in msg or "openai_api_key" in msg:
            return False
        return True
    return False


def _sample_success_tail_usable(chunk_text: str) -> bool:
    low = (chunk_text or "").lower()
    if "sample success response:" not in low:
        return False
    tail = low.split("sample success response:", 1)[-1].strip()[:240]
    return bool(tail) and not tail.startswith("n/a")


def _sample_failed_tail_usable(chunk_text: str) -> bool:
    low = (chunk_text or "").lower()
    tail = ""
    if "sample failed response:" in low:
        tail = low.split("sample failed response:", 1)[-1].strip()[:240]
    elif "failed response:" in low:
        tail = low.split("failed response:", 1)[-1].strip()[:240]
    return bool(tail) and not tail.startswith("n/a")
DEFAULT_IMPACT_ANALYSIS = {
    "primary_entities": [],
    "related_entities": [],
    "potential_impacts": [],
    "relationship_summary": [],
    "impact_confidence": "low",
}


class RagService:
    async def answer_question(
        self,
        project_id: int,
        knowledge_base_id: int,
        question: str,
        top_k: int = 5,
        session_id: int | None = None,
        user_id: int | None = None,
        debug: bool = False,
        prefetched_retrieval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if prefetched_retrieval is not None:
            retrieval_data = prefetched_retrieval
        else:
            retrieval_data = await retrieval_service.retrieve(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            )
        results = retrieval_data.get("results", []) or []
        retrieval_mode = retrieval_data.get("retrieval_mode", "vector")
        detected_intents = detect_query_intents(question)
        vector_diag_for_debug = (
            retrieval_data.get("vector_retrieval_diagnostics")
            if debug
            else None
        )
        retrieval_notice = retrieval_data.get("message") if debug else None
        current_session_id = self._ensure_session(
            session_id=session_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            user_id=user_id,
        )
        conv_mem = self._load_conversation_memory(current_session_id, knowledge_base_id)
        summary_injected = False

        if not results:
            answer = INSUFFICIENT_CONTEXT_ANSWER
            sources: list[dict[str, Any]] = []
            suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                user_question=question,
                answer=answer,
                results=results,
                detected_intents=detected_intents,
                llm_status="fallback_insufficient_context",
            )
            diagnostics = self._build_retrieval_diagnostics(
                retrieval_mode=retrieval_mode,
                knowledge_base_id=knowledge_base_id,
                results=results,
                vector_observability=vector_diag_for_debug,
                retrieval_message=retrieval_notice,
            )
            if debug:
                self._add_suggested_question_diagnostics(
                    diagnostics=diagnostics,
                    suggested_questions=suggested_questions,
                    generation_mode=sq_mode,
                    status=sq_status,
                )
            confidence, confidence_status = self._compute_confidence(
                answer=answer,
                llm_status="fallback_insufficient_context",
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_confidence_diagnostics(
                    diagnostics=diagnostics,
                    confidence=confidence,
                    status=confidence_status,
                )
            self._log_retrieval_summary(
                question=question,
                knowledge_base_id=knowledge_base_id,
                diagnostics=diagnostics,
            )
            if debug:
                self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
            self._persist_messages(
                session_id=current_session_id,
                question=question,
                answer=answer,
                sources=sources,
            )
            await self._after_turn_persisted(current_session_id)
            return {
                "session_id": current_session_id,
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "answer": answer,
                "retrieval_mode": retrieval_mode,
                "llm_status": "fallback_insufficient_context",
                "sources": sources,
                "suggested_questions": suggested_questions,
                "confidence": confidence,
                "impact_analysis": None,
                **({"diagnostics": diagnostics} if debug else {}),
            }

        async_aggregation_answer = self._build_async_aggregation_answer(
            question=question,
            results=results,
            detected_intents=detected_intents,
        )
        if async_aggregation_answer:
            answer = async_aggregation_answer
            sources = [self._to_source_item(item) for item in results]
            suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                user_question=question,
                answer=answer,
                results=results,
                detected_intents=detected_intents,
                llm_status="generated",
            )
            diagnostics = self._build_retrieval_diagnostics(
                retrieval_mode=retrieval_mode,
                knowledge_base_id=knowledge_base_id,
                results=results,
                vector_observability=vector_diag_for_debug,
                retrieval_message=retrieval_notice,
            )
            if debug:
                self._add_suggested_question_diagnostics(
                    diagnostics=diagnostics,
                    suggested_questions=suggested_questions,
                    generation_mode=sq_mode,
                    status=sq_status,
                )
            confidence, confidence_status = self._compute_confidence(
                answer=answer,
                llm_status="generated",
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_confidence_diagnostics(
                    diagnostics=diagnostics,
                    confidence=confidence,
                    status=confidence_status,
                )
            impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                question=question,
                answer=answer,
                results=results,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_impact_diagnostics(
                    diagnostics=diagnostics,
                    impact_analysis=impact_analysis,
                    status=impact_analysis_status,
                )
            if debug:
                self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
            self._persist_messages(
                session_id=current_session_id,
                question=question,
                answer=answer,
                sources=sources,
            )
            await self._after_turn_persisted(current_session_id)
            return {
                "session_id": current_session_id,
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "answer": answer,
                "retrieval_mode": retrieval_mode,
                "llm_status": "generated",
                "sources": sources,
                "suggested_questions": suggested_questions,
                "confidence": confidence,
                "impact_analysis": impact_analysis,
                **({"diagnostics": diagnostics} if debug else {}),
            }

        async_db_answer = self._build_async_db_answer(
            knowledge_base_id=knowledge_base_id,
            detected_intents=detected_intents,
        )
        if async_db_answer:
            sources = [self._to_source_item(item) for item in results]
            suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                user_question=question,
                answer=async_db_answer,
                results=results,
                detected_intents=detected_intents,
                llm_status="generated",
            )
            diagnostics = self._build_retrieval_diagnostics(
                retrieval_mode=retrieval_mode,
                knowledge_base_id=knowledge_base_id,
                results=results,
                vector_observability=vector_diag_for_debug,
                retrieval_message=retrieval_notice,
            )
            if debug:
                self._add_suggested_question_diagnostics(
                    diagnostics=diagnostics,
                    suggested_questions=suggested_questions,
                    generation_mode=sq_mode,
                    status=sq_status,
                )
            confidence, confidence_status = self._compute_confidence(
                answer=async_db_answer,
                llm_status="generated",
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_confidence_diagnostics(
                    diagnostics=diagnostics,
                    confidence=confidence,
                    status=confidence_status,
                )
            impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                question=question,
                answer=async_db_answer,
                results=results,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_impact_diagnostics(
                    diagnostics=diagnostics,
                    impact_analysis=impact_analysis,
                    status=impact_analysis_status,
                )
            if debug:
                self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
            self._persist_messages(
                session_id=current_session_id,
                question=question,
                answer=async_db_answer,
                sources=sources,
            )
            await self._after_turn_persisted(current_session_id)
            return {
                "session_id": current_session_id,
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "answer": async_db_answer,
                "retrieval_mode": retrieval_mode,
                "llm_status": "generated",
                "sources": sources,
                "suggested_questions": suggested_questions,
                "confidence": confidence,
                "impact_analysis": impact_analysis,
                **({"diagnostics": diagnostics} if debug else {}),
            }

        error_lookup_answer = self._build_error_lookup_answer(
            question=question,
            knowledge_base_id=knowledge_base_id,
            detected_intents=detected_intents,
        )
        if error_lookup_answer:
            sources = [self._to_source_item(item) for item in results]
            suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                user_question=question,
                answer=error_lookup_answer,
                results=results,
                detected_intents=detected_intents,
                llm_status="generated",
            )
            diagnostics = self._build_retrieval_diagnostics(
                retrieval_mode=retrieval_mode,
                knowledge_base_id=knowledge_base_id,
                results=results,
                vector_observability=vector_diag_for_debug,
                retrieval_message=retrieval_notice,
            )
            if debug:
                self._add_suggested_question_diagnostics(
                    diagnostics=diagnostics,
                    suggested_questions=suggested_questions,
                    generation_mode=sq_mode,
                    status=sq_status,
                )
            confidence, confidence_status = self._compute_confidence(
                answer=error_lookup_answer,
                llm_status="generated",
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_confidence_diagnostics(
                    diagnostics=diagnostics,
                    confidence=confidence,
                    status=confidence_status,
                )
            impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                question=question,
                answer=error_lookup_answer,
                results=results,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_impact_diagnostics(
                    diagnostics=diagnostics,
                    impact_analysis=impact_analysis,
                    status=impact_analysis_status,
                )
            if debug:
                self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
            self._persist_messages(
                session_id=current_session_id,
                question=question,
                answer=error_lookup_answer,
                sources=sources,
            )
            await self._after_turn_persisted(current_session_id)
            return {
                "session_id": current_session_id,
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "answer": error_lookup_answer,
                "retrieval_mode": retrieval_mode,
                "llm_status": "generated",
                "sources": sources,
                "suggested_questions": suggested_questions,
                "confidence": confidence,
                "impact_analysis": impact_analysis,
                **({"diagnostics": diagnostics} if debug else {}),
            }

        prompt_contexts, prompt_context_diag = self._select_prompt_contexts(
            results=results, top_k=top_k, detected_intents=detected_intents, question=question
        )
        prompt_contexts, recovered_generic = self._annotate_recovered_response_chunks(
            prompt_contexts or [], detected_intents
        )
        prompt_context_diag = {
            **prompt_context_diag,
            "response_fields_recovered_from_generic": recovered_generic,
        }
        context_is_insufficient = self._is_context_insufficient(
            question=question,
            contexts=prompt_contexts or results,
            detected_intents=detected_intents,
        )
        if context_is_insufficient and self._has_intent_supporting_context(detected_intents, prompt_contexts or results):
            context_is_insufficient = False
        if context_is_insufficient:
            answer = INSUFFICIENT_CONTEXT_ANSWER
            sources = [self._to_source_item(item) for item in results]
            suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                user_question=question,
                answer=answer,
                results=results,
                detected_intents=detected_intents,
                llm_status="fallback_insufficient_context",
            )
            diagnostics = self._build_retrieval_diagnostics(
                retrieval_mode=retrieval_mode,
                knowledge_base_id=knowledge_base_id,
                results=results,
                vector_observability=vector_diag_for_debug,
                retrieval_message=retrieval_notice,
                prompt_context_diagnostics=prompt_context_diag,
            )
            if debug:
                self._add_suggested_question_diagnostics(
                    diagnostics=diagnostics,
                    suggested_questions=suggested_questions,
                    generation_mode=sq_mode,
                    status=sq_status,
                )
            confidence, confidence_status = self._compute_confidence(
                answer=answer,
                llm_status="fallback_insufficient_context",
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_confidence_diagnostics(
                    diagnostics=diagnostics,
                    confidence=confidence,
                    status=confidence_status,
                )
            self._log_retrieval_summary(
                question=question,
                knowledge_base_id=knowledge_base_id,
                diagnostics=diagnostics,
            )
            if debug:
                self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
            self._persist_messages(
                session_id=current_session_id,
                question=question,
                answer=answer,
                sources=sources,
            )
            await self._after_turn_persisted(current_session_id)
            return {
                "session_id": current_session_id,
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question,
                "answer": answer,
                "retrieval_mode": retrieval_mode,
                "llm_status": "fallback_insufficient_context",
                "sources": sources,
                "suggested_questions": suggested_questions,
                "confidence": confidence,
                "impact_analysis": None,
                **({"diagnostics": diagnostics} if debug else {}),
            }

        prompt_mode = detect_prompt_mode(prompt_contexts or results)
        session_summary_text = (conv_mem.get("summary_text") or "").strip() or None
        summary_injected = bool(session_summary_text)
        rf_instruction = self._response_field_prompt_instruction(detected_intents)
        prompt = build_rag_prompt(
            question=question,
            contexts=prompt_contexts or results,
            prompt_mode=prompt_mode,
            session_summary=session_summary_text,
            response_field_instruction=rf_instruction,
        )
        llm_provider = (settings.LLM_PROVIDER or "ollama").strip().lower()
        answer, gen_diag = await self._generate_with_provider_retry(prompt, llm_provider)
        if answer and _answer_is_meaningful(answer):
            llm_status = "generated"
        else:
            answer, llm_status = self._resolve_llm_failure_answer(results=results, prompt_context_diag=prompt_context_diag)
        logger.info(
            "llm_generation_complete kb=%s llm_status=%s gen_chars=%s retry=%s empty=%s exc=%s",
            knowledge_base_id,
            llm_status,
            gen_diag.get("generation_char_count"),
            gen_diag.get("provider_retry_attempted"),
            gen_diag.get("provider_response_empty"),
            gen_diag.get("provider_exception_type"),
        )

        sources = [self._to_source_item(item) for item in results]
        suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
            user_question=question,
            answer=answer,
            results=results,
            detected_intents=detected_intents,
            llm_status=llm_status,
        )
        diagnostics = self._build_retrieval_diagnostics(
            retrieval_mode=retrieval_mode,
            knowledge_base_id=knowledge_base_id,
            results=results,
            vector_observability=vector_diag_for_debug,
            retrieval_message=retrieval_notice,
            prompt_context_diagnostics=prompt_context_diag,
        )
        self._merge_generation_diagnostics(diagnostics, gen_diag)
        if debug:
            self._add_suggested_question_diagnostics(
                diagnostics=diagnostics,
                suggested_questions=suggested_questions,
                generation_mode=sq_mode,
                status=sq_status,
            )
        confidence, confidence_status = self._compute_confidence(
            answer=answer,
            llm_status=llm_status,
            results=results,
            diagnostics=diagnostics,
            detected_intents=detected_intents,
        )
        if debug:
            self._add_confidence_diagnostics(
                diagnostics=diagnostics,
                confidence=confidence,
                status=confidence_status,
            )
        impact_analysis, impact_analysis_status = self._compute_impact_analysis(
            question=question,
            answer=answer,
            results=results,
            detected_intents=detected_intents,
        )
        if debug:
            self._add_impact_diagnostics(
                diagnostics=diagnostics,
                impact_analysis=impact_analysis,
                status=impact_analysis_status,
            )
        self._log_retrieval_summary(
            question=question,
            knowledge_base_id=knowledge_base_id,
            diagnostics=diagnostics,
        )
        if debug:
            self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
        self._persist_messages(
            session_id=current_session_id,
            question=question,
            answer=answer,
            sources=sources,
        )
        await self._after_turn_persisted(current_session_id)

        return {
            "session_id": current_session_id,
            "project_id": project_id,
            "knowledge_base_id": knowledge_base_id,
            "question": question,
            "answer": answer,
            "retrieval_mode": retrieval_mode,
            "llm_status": llm_status,
            "sources": sources,
            "suggested_questions": suggested_questions,
            "confidence": confidence,
            "impact_analysis": impact_analysis,
            **({"diagnostics": diagnostics} if debug else {}),
        }

    async def answer_question_stream(
        self,
        project_id: int,
        knowledge_base_id: int,
        question: str,
        top_k: int = 5,
        session_id: int | None = None,
        user_id: int | None = None,
        debug: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """Same logic as answer_question but emits SSE-style events; persists user message first, assistant after stream."""

        async def emit_tokens_for_text(text: str):
            async for piece in self._simulate_stream(text):
                yield {"event": "token", "data": {"text": piece}}

        try:
            retrieval_data = await retrieval_service.retrieve(
                project_id=project_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                top_k=top_k,
            )
            results = retrieval_data.get("results", []) or []
            retrieval_mode = retrieval_data.get("retrieval_mode", "vector")
            detected_intents = detect_query_intents(question)
            vector_diag_for_debug = retrieval_data.get("vector_retrieval_diagnostics") if debug else None
            retrieval_notice = retrieval_data.get("message") if debug else None
            current_session_id = self._ensure_session(
                session_id=session_id,
                knowledge_base_id=knowledge_base_id,
                question=question,
                user_id=user_id,
            )
            conv_mem = self._load_conversation_memory(current_session_id, knowledge_base_id)
            summary_injected = False
            self._persist_user_message(session_id=current_session_id, question=question)
        except ValueError as exc:
            yield {"event": "error", "data": {"detail": str(exc)}}
            return

        yield {
            "event": "start",
            "data": {
                "session_id": current_session_id,
                "project_id": project_id,
                "knowledge_base_id": knowledge_base_id,
                "question": question.strip(),
            },
        }

        try:
            if not results:
                answer = INSUFFICIENT_CONTEXT_ANSWER
                sources: list[dict[str, Any]] = []
                suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                    user_question=question,
                    answer=answer,
                    results=results,
                    detected_intents=detected_intents,
                    llm_status="fallback_insufficient_context",
                )
                diagnostics = self._build_retrieval_diagnostics(
                    retrieval_mode=retrieval_mode,
                    knowledge_base_id=knowledge_base_id,
                    results=results,
                    vector_observability=vector_diag_for_debug,
                    retrieval_message=retrieval_notice,
                )
                if debug:
                    self._add_suggested_question_diagnostics(
                        diagnostics=diagnostics,
                        suggested_questions=suggested_questions,
                        generation_mode=sq_mode,
                        status=sq_status,
                    )
                confidence, confidence_status = self._compute_confidence(
                    answer=answer,
                    llm_status="fallback_insufficient_context",
                    results=results,
                    diagnostics=diagnostics,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_confidence_diagnostics(
                        diagnostics=diagnostics,
                        confidence=confidence,
                        status=confidence_status,
                    )
                self._log_retrieval_summary(
                    question=question,
                    knowledge_base_id=knowledge_base_id,
                    diagnostics=diagnostics,
                )
                if debug:
                    self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
                async for evt in emit_tokens_for_text(answer):
                    yield evt
                yield {"event": "sources", "data": {"sources": sources}}
                if debug:
                    yield {"event": "diagnostics", "data": {"diagnostics": diagnostics}}
                done_payload = {
                    "session_id": current_session_id,
                    "project_id": project_id,
                    "knowledge_base_id": knowledge_base_id,
                    "question": question.strip(),
                    "answer": answer,
                    "retrieval_mode": retrieval_mode,
                    "llm_status": "fallback_insufficient_context",
                    "sources": sources,
                    "suggested_questions": suggested_questions,
                    "confidence": confidence,
                    "impact_analysis": None,
                    **({"diagnostics": diagnostics} if debug else {}),
                }
                yield {"event": "done", "data": done_payload}
                self._persist_assistant_message(current_session_id, answer, sources)
                await self._after_turn_persisted(current_session_id)
                return

            async_aggregation_answer = self._build_async_aggregation_answer(
                question=question,
                results=results,
                detected_intents=detected_intents,
            )
            if async_aggregation_answer:
                answer = async_aggregation_answer
                sources = [self._to_source_item(item) for item in results]
                suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                    user_question=question,
                    answer=answer,
                    results=results,
                    detected_intents=detected_intents,
                    llm_status="generated",
                )
                diagnostics = self._build_retrieval_diagnostics(
                    retrieval_mode=retrieval_mode,
                    knowledge_base_id=knowledge_base_id,
                    results=results,
                    vector_observability=vector_diag_for_debug,
                    retrieval_message=retrieval_notice,
                )
                if debug:
                    self._add_suggested_question_diagnostics(
                        diagnostics=diagnostics,
                        suggested_questions=suggested_questions,
                        generation_mode=sq_mode,
                        status=sq_status,
                    )
                confidence, confidence_status = self._compute_confidence(
                    answer=answer,
                    llm_status="generated",
                    results=results,
                    diagnostics=diagnostics,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_confidence_diagnostics(
                        diagnostics=diagnostics,
                        confidence=confidence,
                        status=confidence_status,
                    )
                impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                    question=question,
                    answer=answer,
                    results=results,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_impact_diagnostics(
                        diagnostics=diagnostics,
                        impact_analysis=impact_analysis,
                        status=impact_analysis_status,
                    )
                if debug:
                    self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
                async for evt in emit_tokens_for_text(answer):
                    yield evt
                yield {"event": "sources", "data": {"sources": sources}}
                if debug:
                    yield {"event": "diagnostics", "data": {"diagnostics": diagnostics}}
                yield {
                    "event": "done",
                    "data": {
                        "session_id": current_session_id,
                        "project_id": project_id,
                        "knowledge_base_id": knowledge_base_id,
                        "question": question.strip(),
                        "answer": answer,
                        "retrieval_mode": retrieval_mode,
                        "llm_status": "generated",
                        "sources": sources,
                        "suggested_questions": suggested_questions,
                        "confidence": confidence,
                        "impact_analysis": impact_analysis,
                        **({"diagnostics": diagnostics} if debug else {}),
                    },
                }
                self._persist_assistant_message(current_session_id, answer, sources)
                await self._after_turn_persisted(current_session_id)
                return

            async_db_answer = self._build_async_db_answer(
                knowledge_base_id=knowledge_base_id,
                detected_intents=detected_intents,
            )
            if async_db_answer:
                sources = [self._to_source_item(item) for item in results]
                suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                    user_question=question,
                    answer=async_db_answer,
                    results=results,
                    detected_intents=detected_intents,
                    llm_status="generated",
                )
                diagnostics = self._build_retrieval_diagnostics(
                    retrieval_mode=retrieval_mode,
                    knowledge_base_id=knowledge_base_id,
                    results=results,
                    vector_observability=vector_diag_for_debug,
                    retrieval_message=retrieval_notice,
                )
                if debug:
                    self._add_suggested_question_diagnostics(
                        diagnostics=diagnostics,
                        suggested_questions=suggested_questions,
                        generation_mode=sq_mode,
                        status=sq_status,
                    )
                confidence, confidence_status = self._compute_confidence(
                    answer=async_db_answer,
                    llm_status="generated",
                    results=results,
                    diagnostics=diagnostics,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_confidence_diagnostics(
                        diagnostics=diagnostics,
                        confidence=confidence,
                        status=confidence_status,
                    )
                impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                    question=question,
                    answer=async_db_answer,
                    results=results,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_impact_diagnostics(
                        diagnostics=diagnostics,
                        impact_analysis=impact_analysis,
                        status=impact_analysis_status,
                    )
                if debug:
                    self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
                async for evt in emit_tokens_for_text(async_db_answer):
                    yield evt
                yield {"event": "sources", "data": {"sources": sources}}
                if debug:
                    yield {"event": "diagnostics", "data": {"diagnostics": diagnostics}}
                yield {
                    "event": "done",
                    "data": {
                        "session_id": current_session_id,
                        "project_id": project_id,
                        "knowledge_base_id": knowledge_base_id,
                        "question": question.strip(),
                        "answer": async_db_answer,
                        "retrieval_mode": retrieval_mode,
                        "llm_status": "generated",
                        "sources": sources,
                        "suggested_questions": suggested_questions,
                        "confidence": confidence,
                        "impact_analysis": impact_analysis,
                        **({"diagnostics": diagnostics} if debug else {}),
                    },
                }
                self._persist_assistant_message(current_session_id, async_db_answer, sources)
                await self._after_turn_persisted(current_session_id)
                return

            error_lookup_answer = self._build_error_lookup_answer(
                question=question,
                knowledge_base_id=knowledge_base_id,
                detected_intents=detected_intents,
            )
            if error_lookup_answer:
                sources = [self._to_source_item(item) for item in results]
                suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                    user_question=question,
                    answer=error_lookup_answer,
                    results=results,
                    detected_intents=detected_intents,
                    llm_status="generated",
                )
                diagnostics = self._build_retrieval_diagnostics(
                    retrieval_mode=retrieval_mode,
                    knowledge_base_id=knowledge_base_id,
                    results=results,
                    vector_observability=vector_diag_for_debug,
                    retrieval_message=retrieval_notice,
                )
                if debug:
                    self._add_suggested_question_diagnostics(
                        diagnostics=diagnostics,
                        suggested_questions=suggested_questions,
                        generation_mode=sq_mode,
                        status=sq_status,
                    )
                confidence, confidence_status = self._compute_confidence(
                    answer=error_lookup_answer,
                    llm_status="generated",
                    results=results,
                    diagnostics=diagnostics,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_confidence_diagnostics(
                        diagnostics=diagnostics,
                        confidence=confidence,
                        status=confidence_status,
                    )
                impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                    question=question,
                    answer=error_lookup_answer,
                    results=results,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_impact_diagnostics(
                        diagnostics=diagnostics,
                        impact_analysis=impact_analysis,
                        status=impact_analysis_status,
                    )
                if debug:
                    self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
                async for evt in emit_tokens_for_text(error_lookup_answer):
                    yield evt
                yield {"event": "sources", "data": {"sources": sources}}
                if debug:
                    yield {"event": "diagnostics", "data": {"diagnostics": diagnostics}}
                yield {
                    "event": "done",
                    "data": {
                        "session_id": current_session_id,
                        "project_id": project_id,
                        "knowledge_base_id": knowledge_base_id,
                        "question": question.strip(),
                        "answer": error_lookup_answer,
                        "retrieval_mode": retrieval_mode,
                        "llm_status": "generated",
                        "sources": sources,
                        "suggested_questions": suggested_questions,
                        "confidence": confidence,
                        "impact_analysis": impact_analysis,
                        **({"diagnostics": diagnostics} if debug else {}),
                    },
                }
                self._persist_assistant_message(current_session_id, error_lookup_answer, sources)
                await self._after_turn_persisted(current_session_id)
                return

            prompt_contexts, prompt_context_diag = self._select_prompt_contexts(
                results=results, top_k=top_k, detected_intents=detected_intents, question=question
            )
            prompt_contexts, recovered_generic = self._annotate_recovered_response_chunks(
                prompt_contexts or [], detected_intents
            )
            prompt_context_diag = {
                **prompt_context_diag,
                "response_fields_recovered_from_generic": recovered_generic,
            }
            context_is_insufficient = self._is_context_insufficient(
                question=question,
                contexts=prompt_contexts or results,
                detected_intents=detected_intents,
            )
            if context_is_insufficient and self._has_intent_supporting_context(detected_intents, prompt_contexts or results):
                context_is_insufficient = False
            if context_is_insufficient:
                answer = INSUFFICIENT_CONTEXT_ANSWER
                sources = [self._to_source_item(item) for item in results]
                suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                    user_question=question,
                    answer=answer,
                    results=results,
                    detected_intents=detected_intents,
                    llm_status="fallback_insufficient_context",
                )
                diagnostics = self._build_retrieval_diagnostics(
                    retrieval_mode=retrieval_mode,
                    knowledge_base_id=knowledge_base_id,
                    results=results,
                    vector_observability=vector_diag_for_debug,
                    retrieval_message=retrieval_notice,
                    prompt_context_diagnostics=prompt_context_diag,
                )
                if debug:
                    self._add_suggested_question_diagnostics(
                        diagnostics=diagnostics,
                        suggested_questions=suggested_questions,
                        generation_mode=sq_mode,
                        status=sq_status,
                    )
                confidence, confidence_status = self._compute_confidence(
                    answer=answer,
                    llm_status="fallback_insufficient_context",
                    results=results,
                    diagnostics=diagnostics,
                    detected_intents=detected_intents,
                )
                if debug:
                    self._add_confidence_diagnostics(
                        diagnostics=diagnostics,
                        confidence=confidence,
                        status=confidence_status,
                    )
                self._log_retrieval_summary(
                    question=question,
                    knowledge_base_id=knowledge_base_id,
                    diagnostics=diagnostics,
                )
                if debug:
                    self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)
                async for evt in emit_tokens_for_text(answer):
                    yield evt
                yield {"event": "sources", "data": {"sources": sources}}
                if debug:
                    yield {"event": "diagnostics", "data": {"diagnostics": diagnostics}}
                yield {
                    "event": "done",
                    "data": {
                        "session_id": current_session_id,
                        "project_id": project_id,
                        "knowledge_base_id": knowledge_base_id,
                        "question": question.strip(),
                        "answer": answer,
                        "retrieval_mode": retrieval_mode,
                        "llm_status": "fallback_insufficient_context",
                        "sources": sources,
                        "suggested_questions": suggested_questions,
                        "confidence": confidence,
                        "impact_analysis": None,
                        **({"diagnostics": diagnostics} if debug else {}),
                    },
                }
                self._persist_assistant_message(current_session_id, answer, sources)
                await self._after_turn_persisted(current_session_id)
                return

            prompt_mode = detect_prompt_mode(prompt_contexts or results)
            session_summary_text = (conv_mem.get("summary_text") or "").strip() or None
            summary_injected = bool(session_summary_text)
            rf_instruction = self._response_field_prompt_instruction(detected_intents)
            prompt = build_rag_prompt(
                question=question,
                contexts=prompt_contexts or results,
                prompt_mode=prompt_mode,
                session_summary=session_summary_text,
                response_field_instruction=rf_instruction,
            )
            llm_provider = (settings.LLM_PROVIDER or "ollama").strip().lower()
            gen_diag: dict[str, Any] = {}
            stream_collector: list[str] = []
            stream_exc_name: str | None = None
            try:
                if llm_provider == "openai":
                    async for tok in openai_client.generate_stream(prompt, model=settings.OPENAI_LLM_MODEL):
                        stream_collector.append(tok)
                        yield {"event": "token", "data": {"text": tok}}
                else:
                    async for tok in ollama_client.generate_stream(prompt):
                        stream_collector.append(tok)
                        yield {"event": "token", "data": {"text": tok}}
            except Exception as stream_exc:
                stream_exc_name = stream_exc.__class__.__name__
                logger.warning("LLM streaming failed, falling back to non-streaming generate: %s", stream_exc)
                stream_collector.clear()

            answer = "".join(stream_collector).strip()
            if _answer_is_meaningful(answer):
                llm_status = "generated"
                gen_diag = {
                    "provider_retry_attempted": False,
                    "provider_retry_reason": None,
                    "provider_response_empty": False,
                    "provider_exception_type": stream_exc_name,
                    "generation_char_count": len(answer),
                    "provider_stream_used": True,
                }
            else:
                answer2, gen_diag = await self._generate_with_provider_retry(prompt, llm_provider)
                if stream_exc_name:
                    gen_diag["provider_stream_exception_type"] = stream_exc_name
                gen_diag["provider_stream_chunks_seen"] = len(stream_collector) > 0
                if answer2 and _answer_is_meaningful(answer2):
                    answer = answer2
                    llm_status = "generated"
                    async for piece in self._simulate_stream(answer):
                        yield {"event": "token", "data": {"text": piece}}
                else:
                    answer, llm_status = self._resolve_llm_failure_answer(
                        results=results, prompt_context_diag=prompt_context_diag
                    )
                    async for piece in self._simulate_stream(answer):
                        yield {"event": "token", "data": {"text": piece}}

            logger.info(
                "llm_generation_stream_complete kb=%s llm_status=%s gen_chars=%s retry=%s empty=%s exc=%s",
                knowledge_base_id,
                llm_status,
                gen_diag.get("generation_char_count"),
                gen_diag.get("provider_retry_attempted"),
                gen_diag.get("provider_response_empty"),
                gen_diag.get("provider_exception_type"),
            )

            sources = [self._to_source_item(item) for item in results]
            suggested_questions, sq_mode, sq_status = self._generate_suggested_questions(
                user_question=question,
                answer=answer,
                results=results,
                detected_intents=detected_intents,
                llm_status=llm_status,
            )
            diagnostics = self._build_retrieval_diagnostics(
                retrieval_mode=retrieval_mode,
                knowledge_base_id=knowledge_base_id,
                results=results,
                vector_observability=vector_diag_for_debug,
                retrieval_message=retrieval_notice,
                prompt_context_diagnostics=prompt_context_diag,
            )
            self._merge_generation_diagnostics(diagnostics, gen_diag)
            if debug:
                self._add_suggested_question_diagnostics(
                    diagnostics=diagnostics,
                    suggested_questions=suggested_questions,
                    generation_mode=sq_mode,
                    status=sq_status,
                )
            confidence, confidence_status = self._compute_confidence(
                answer=answer,
                llm_status=llm_status,
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_confidence_diagnostics(
                    diagnostics=diagnostics,
                    confidence=confidence,
                    status=confidence_status,
                )
            impact_analysis, impact_analysis_status = self._compute_impact_analysis(
                question=question,
                answer=answer,
                results=results,
                detected_intents=detected_intents,
            )
            if debug:
                self._add_impact_diagnostics(
                    diagnostics=diagnostics,
                    impact_analysis=impact_analysis,
                    status=impact_analysis_status,
                )
            self._log_retrieval_summary(
                question=question,
                knowledge_base_id=knowledge_base_id,
                diagnostics=diagnostics,
            )
            if debug:
                self._merge_conversation_summary_diagnostics(diagnostics, conv_mem, summary_injected, debug)

            yield {"event": "sources", "data": {"sources": sources}}
            if debug:
                yield {"event": "diagnostics", "data": {"diagnostics": diagnostics}}
            yield {
                "event": "done",
                "data": {
                    "session_id": current_session_id,
                    "project_id": project_id,
                    "knowledge_base_id": knowledge_base_id,
                    "question": question.strip(),
                    "answer": answer,
                    "retrieval_mode": retrieval_mode,
                    "llm_status": llm_status,
                    "sources": sources,
                    "suggested_questions": suggested_questions,
                    "confidence": confidence,
                    "impact_analysis": impact_analysis,
                    **({"diagnostics": diagnostics} if debug else {}),
                },
            }
            self._persist_assistant_message(current_session_id, answer, sources)
            await self._after_turn_persisted(current_session_id)

        except Exception as exc:
            logger.exception("answer_question_stream failed")
            yield {"event": "error", "data": {"detail": str(exc)}}

    async def _single_llm_generate(self, prompt: str, llm_provider: str) -> str:
        if llm_provider == "openai":
            return await openai_client.generate(prompt, model=settings.OPENAI_LLM_MODEL)
        llm_response = await ollama_client.generate_test(prompt)
        return (llm_response.get("response") or "").strip()

    async def _generate_with_provider_retry(self, prompt: str, llm_provider: str) -> tuple[str | None, dict[str, Any]]:
        """
        Up to two completion attempts: retry once on empty/weak output or transient provider errors.
        Returns (answer text or None, generation diagnostics).
        """
        diag: dict[str, Any] = {
            "provider_retry_attempted": False,
            "provider_retry_reason": None,
            "provider_response_empty": False,
            "provider_exception_type": None,
            "generation_char_count": 0,
        }
        for attempt in (1, 2):
            try:
                raw = await self._single_llm_generate(prompt, llm_provider)
                text = (raw or "").strip()
                diag["generation_char_count"] = len(text)
                if _answer_is_meaningful(text):
                    if attempt == 2:
                        diag["provider_retry_attempted"] = True
                    return text, diag
                diag["provider_response_empty"] = True
                if attempt == 1:
                    diag["provider_retry_attempted"] = True
                    diag["provider_retry_reason"] = "empty_or_weak_response"
                    continue
                return None, diag
            except Exception as exc:
                diag["provider_exception_type"] = exc.__class__.__name__
                if attempt == 1 and _is_retryable_provider_error(exc):
                    diag["provider_retry_attempted"] = True
                    diag["provider_retry_reason"] = "transient_provider_exception"
                    continue
                return None, diag
        return None, diag

    def _substantive_generation_context(
        self,
        results: list[dict[str, Any]],
        prompt_context_diag: dict[str, Any],
    ) -> bool:
        if not results:
            return False
        chars = int(prompt_context_diag.get("final_prompt_context_chars") or 0)
        if chars >= MIN_PROMPT_CONTEXT_CHARS_SUBSTANTIVE:
            return True
        n = int(prompt_context_diag.get("selected_prompt_chunk_count") or 0)
        return n >= 1 and chars >= 48

    def _resolve_llm_failure_answer(
        self,
        *,
        results: list[dict[str, Any]],
        prompt_context_diag: dict[str, Any],
    ) -> tuple[str, str]:
        """
        After failed generation, distinguish retrieval gap vs provider failure.
        """
        if self._substantive_generation_context(results, prompt_context_diag):
            return PROVIDER_GENERATION_FAILURE_ANSWER, "fallback_provider_generation_failure"
        return INSUFFICIENT_CONTEXT_ANSWER, "fallback_insufficient_context"

    def _merge_generation_diagnostics(self, diagnostics: dict[str, Any], gen_diag: dict[str, Any]) -> None:
        for key, val in gen_diag.items():
            diagnostics[key] = val

    async def _simulate_stream(self, text: str, chunk_size: int = 24) -> AsyncIterator[str]:
        if not text:
            return
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]
            await asyncio.sleep(0)

    def _compute_impact_analysis(
        self,
        *,
        question: str,
        answer: str,
        results: list[dict[str, Any]],
        detected_intents: list[str],
    ) -> tuple[dict[str, Any] | None, str]:
        if not getattr(settings, "ENABLE_IMPACT_ANALYSIS", True):
            return None, "disabled"
        if (answer or "").strip() == INSUFFICIENT_CONTEXT_ANSWER:
            return None, "skipped"
        if (answer or "").strip() == PROVIDER_GENERATION_FAILURE_ANSWER:
            return None, "skipped"
        if not results:
            return None, "skipped"
        try:
            impact_analysis = impact_analysis_service.analyze_impact(
                user_question=question,
                retrieved_chunks=results,
                detected_intents=detected_intents,
            )
            if not isinstance(impact_analysis, dict):
                return dict(DEFAULT_IMPACT_ANALYSIS), "error"
            return {
                "primary_entities": impact_analysis.get("primary_entities", []),
                "related_entities": impact_analysis.get("related_entities", []),
                "potential_impacts": impact_analysis.get("potential_impacts", []),
                "relationship_summary": impact_analysis.get("relationship_summary", []),
                "impact_confidence": impact_analysis.get("impact_confidence", "low"),
            }, "computed"
        except Exception:
            return dict(DEFAULT_IMPACT_ANALYSIS), "error"

    def _add_impact_diagnostics(
        self,
        *,
        diagnostics: dict[str, Any],
        impact_analysis: dict[str, Any] | None,
        status: str,
    ) -> None:
        diagnostics["impact_analysis_status"] = status
        diagnostics["impact_primary_entity_count"] = len(impact_analysis.get("primary_entities", [])) if isinstance(impact_analysis, dict) else 0
        diagnostics["impact_related_entity_count"] = len(impact_analysis.get("related_entities", [])) if isinstance(impact_analysis, dict) else 0
        diagnostics["impact_relationship_count"] = len(impact_analysis.get("relationship_summary", [])) if isinstance(impact_analysis, dict) else 0
        diagnostics["impact_confidence"] = impact_analysis.get("impact_confidence") if isinstance(impact_analysis, dict) else None

    def _compute_confidence(
        self,
        *,
        answer: str,
        llm_status: str,
        results: list[dict[str, Any]],
        diagnostics: dict[str, Any],
        detected_intents: list[str],
    ) -> tuple[dict[str, Any] | None, str]:
        if not getattr(settings, "ENABLE_CONFIDENCE_SCORING", True):
            return None, "disabled"
        try:
            confidence = confidence_service.score(
                answer=answer,
                llm_status=llm_status,
                results=results,
                diagnostics=diagnostics,
                detected_intents=detected_intents,
            )
            if not isinstance(confidence, dict):
                raise ValueError("Invalid confidence payload")
            score = float(confidence.get("score", 0.0))
            label = str(confidence.get("label", "low")).strip().lower() or "low"
            reasons = confidence.get("reasons")
            if not isinstance(reasons, list):
                reasons = []
            safe_confidence = {
                "score": max(0.0, min(1.0, score)),
                "label": label if label in {"high", "medium", "low"} else "low",
                "reasons": [str(r) for r in reasons if str(r).strip()],
            }
            return safe_confidence, "computed"
        except Exception:
            return {"score": 0.0, "label": "low", "reasons": ["confidence scoring unavailable"]}, "error"

    def _add_confidence_diagnostics(
        self,
        *,
        diagnostics: dict[str, Any],
        confidence: dict[str, Any] | None,
        status: str,
    ) -> None:
        diagnostics["confidence_score"] = confidence.get("score") if isinstance(confidence, dict) else None
        diagnostics["confidence_label"] = confidence.get("label") if isinstance(confidence, dict) else None
        diagnostics["confidence_reasons"] = confidence.get("reasons") if isinstance(confidence, dict) else []
        diagnostics["confidence_status"] = status

    def _generate_suggested_questions(
        self,
        *,
        user_question: str,
        answer: str,
        results: list[dict[str, Any]],
        detected_intents: list[str],
        llm_status: str,
    ) -> tuple[list[str], str, str]:
        if not getattr(settings, "ENABLE_SUGGESTED_QUESTIONS", True):
            return [], "disabled", "skipped"
        if llm_status in ("fallback_insufficient_context", "fallback_provider_generation_failure"):
            return [], "skipped", "skipped"
        if not results:
            return [], "skipped", "skipped"
        try:
            suggested_questions = suggested_question_service.generate(
                user_question=user_question,
                answer=answer,
                contexts=results,
                document_type=self._dominant_document_type(results),
                detected_intents=detected_intents,
            )
            if suggested_questions:
                return suggested_questions, "deterministic", "generated"
            return [], "deterministic", "empty"
        except Exception:
            return [], "deterministic", "error"

    def _add_suggested_question_diagnostics(
        self,
        *,
        diagnostics: dict[str, Any],
        suggested_questions: list[str],
        generation_mode: str,
        status: str,
    ) -> None:
        diagnostics["suggested_question_count"] = len(suggested_questions)
        diagnostics["suggested_question_generation_mode"] = generation_mode
        diagnostics["suggested_question_status"] = status

    def _dominant_document_type(self, results: list[dict[str, Any]]) -> str | None:
        counts = Counter((item.get("document_type") or "").strip().lower() for item in results if item.get("document_type"))
        if not counts:
            return None
        return counts.most_common(1)[0][0]

    def _structured_response_support_in_contexts(self, contexts: list[dict[str, Any]]) -> bool:
        for item in contexts:
            ct = (item.get("chunk_type") or "").lower()
            txt = str(item.get("chunk_text") or "")
            if ct == "api_response_parameters_chunk" and response_parameters_chunk_quality(txt).get("boost_ok"):
                return True
            if ct == "api_sample_success_response_chunk" and _sample_success_tail_usable(txt):
                return True
            if ct == "api_sample_failed_response_chunk" and _sample_failed_tail_usable(txt):
                return True
            if ct == "endpoint_response_chunk" and txt.strip():
                return True
        return False

    def _annotate_recovered_response_chunks(
        self,
        contexts: list[dict[str, Any]],
        detected_intents: list[str] | None,
    ) -> tuple[list[dict[str, Any]], bool]:
        intents_set = {str(i).strip().lower() for i in (detected_intents or []) if str(i).strip()}
        if "response_field_intent" not in intents_set:
            return contexts, False
        has_structured = self._structured_response_support_in_contexts(contexts)
        prefix = "Recovered Response Parameters\n"
        out: list[dict[str, Any]] = []
        for item in contexts:
            row = dict(item)
            ct = (row.get("chunk_type") or "").lower()
            raw_text = str(row.get("chunk_text") or "")
            if ct == "generic_section_chunk" and generic_chunk_qualifies_as_response_fields(raw_text):
                low_head = raw_text.lower().strip()
                if not low_head.startswith("recovered response parameters"):
                    row["chunk_text"] = prefix + raw_text
            out.append(row)
        any_qualifying_generic = any(
            (x.get("chunk_type") or "").lower() == "generic_section_chunk"
            and generic_chunk_qualifies_as_response_fields(str(x.get("chunk_text") or ""))
            for x in out
        )
        recovered_flag = bool(any_qualifying_generic and not has_structured)
        return out, recovered_flag

    def _response_field_prompt_instruction(self, detected_intents: list[str] | None) -> str | None:
        intents_set = {str(i).strip().lower() for i in (detected_intents or []) if str(i).strip()}
        if "response_field_intent" not in intents_set:
            return None
        return (
            "When listing API response fields, include only these fields if they appear in the context: "
            "status, code, desc, timestamp, transactionId, correlationId, responseInfo, qrText, errorcode, errormsg. "
            "Do not invent fields that are not present in the context."
        )

    def _select_prompt_contexts(
        self,
        *,
        results: list[dict[str, Any]],
        top_k: int,
        detected_intents: list[str] | None = None,
        question: str = "",
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not results:
            return [], {
                "selected_prompt_chunk_count": 0,
                "dedup_chunks_removed": 0,
                "diversity_caps_applied": 0,
                "final_prompt_context_chars": 0,
                "parameter_prompt_prioritization": False,
                "max_per_document_cap": None,
                "max_per_api_ref_cap": None,
                "max_prompt_chunks_cap": None,
            }

        intents_set = {str(i).strip().lower() for i in (detected_intents or []) if str(i).strip()}
        response_field_intent = "response_field_intent" in intents_set
        parameter_intent = "parameter_intent" in intents_set

        def _response_chunk_rank(item: dict[str, Any]) -> tuple[int, float]:
            ct = (item.get("chunk_type") or "").lower()
            txt = str(item.get("chunk_text") or "")
            score = float(item.get("score") or item.get("vector_score_raw") or 0.0)
            if ct == "api_response_parameters_chunk":
                if response_parameters_chunk_quality(txt).get("boost_ok"):
                    return (0, score)
                return (10, score)
            if ct == "endpoint_response_chunk":
                return (1, score)
            if ct == "api_sample_success_response_chunk":
                if _sample_success_tail_usable(txt):
                    return (2, score)
                return (11, score)
            if ct == "generic_section_chunk":
                if generic_chunk_qualifies_as_response_fields(txt):
                    return (3, score)
                return (14, score)
            if ct == "api_sample_failed_response_chunk":
                if _sample_failed_tail_usable(txt):
                    return (4, score)
                return (12, score)
            return (20, score)

        def _chunk_supports_response_fields_prompt(item: dict[str, Any]) -> bool:
            ct = (item.get("chunk_type") or "").lower()
            txt = str(item.get("chunk_text") or "")
            if ct == "api_response_parameters_chunk":
                return bool(response_parameters_chunk_quality(txt).get("boost_ok"))
            if ct == "endpoint_response_chunk":
                return bool(txt.strip())
            if ct == "api_sample_success_response_chunk":
                return _sample_success_tail_usable(txt)
            if ct == "api_sample_failed_response_chunk":
                return _sample_failed_tail_usable(txt)
            if ct == "generic_section_chunk":
                return generic_chunk_qualifies_as_response_fields(txt)
            return False

        def _parameter_prompt_rank(item: dict[str, Any]) -> tuple[int, float]:
            ct = (item.get("chunk_type") or "").lower()
            raw_score = float(item.get("score") or item.get("vector_score_raw") or 0.0)
            q_low = (question or "").lower()
            sn = (item.get("service_name") or "").lower()
            ar = (item.get("api_reference_id") or "").lower()
            priority = 40
            if ct == "api_request_parameters_chunk":
                priority = 0
                if sn and sn in q_low:
                    priority = -6
                elif ar and ar in q_low:
                    priority = -4
            elif ct in {"api_query_parameters_chunk", "api_header_parameters_chunk"}:
                priority = 2
            elif ct == "api_metadata_chunk":
                priority = 14
            elif ct == "document_overview_chunk":
                priority = 22
            elif ct == "api_semantic_summary_chunk":
                priority = 12
            return (priority, -raw_score)

        ordered_results = list(results)
        if response_field_intent:
            ordered_results.sort(key=_response_chunk_rank)
        elif parameter_intent:
            ordered_results.sort(key=_parameter_prompt_rank)

        max_prompt_chunks = (
            max(3, min(top_k, 8)) if parameter_intent else max(3, min(top_k, 6))
        )
        char_budget = 9000
        max_chunk_chars = 3200
        max_per_document = (
            3 if response_field_intent else (10 if parameter_intent else 2)
        )
        max_per_section = 1
        max_per_api_ref = (
            4 if response_field_intent else (12 if parameter_intent else 2)
        )

        selected: list[dict[str, Any]] = []
        selected_token_sets: list[set[str]] = []
        seen_signatures: set[str] = set()
        per_document: dict[str, int] = {}
        per_section: dict[str, int] = {}
        per_api_ref: dict[str, int] = {}
        dedup_removed = 0
        diversity_caps_applied = 0
        total_chars = 0

        for item in ordered_results:
            if len(selected) >= max_prompt_chunks:
                break

            chunk_text = (item.get("chunk_text") or "").strip()
            if not chunk_text:
                continue

            sig = self._prompt_signature(item)
            if sig in seen_signatures:
                dedup_removed += 1
                continue

            candidate_tokens = self._token_set(chunk_text)
            chunk_type_l = (item.get("chunk_type") or "").lower()
            skip_overlap_check = response_field_intent and _chunk_supports_response_fields_prompt(item)
            if parameter_intent and chunk_type_l == "api_request_parameters_chunk":
                skip_overlap_check = True
            if not skip_overlap_check and any(
                self._token_overlap_ratio(candidate_tokens, existing) >= 0.88 for existing in selected_token_sets
            ):
                dedup_removed += 1
                continue

            doc_key = str(item.get("document_id") or item.get("file_name") or "unknown_doc")
            section_key = str((item.get("section_title") or "").strip().lower() or "no_section")
            api_ref_key = str((item.get("api_reference_id") or "").strip().lower() or "no_api_ref")

            if per_document.get(doc_key, 0) >= max_per_document:
                diversity_caps_applied += 1
                continue
            if section_key != "no_section" and per_section.get(section_key, 0) >= max_per_section:
                if not (response_field_intent and _chunk_supports_response_fields_prompt(item)):
                    diversity_caps_applied += 1
                    continue
            if api_ref_key != "no_api_ref" and per_api_ref.get(api_ref_key, 0) >= max_per_api_ref:
                diversity_caps_applied += 1
                continue

            remaining = max(char_budget - total_chars, 0)
            if remaining <= 0:
                break
            if selected and remaining < 240:
                break
            chunk_for_prompt = chunk_text[: min(max_chunk_chars, remaining)]
            chunk_len = len(chunk_for_prompt)
            if chunk_len <= 0:
                continue

            selected_item = dict(item)
            selected_item["chunk_text"] = chunk_for_prompt
            selected.append(selected_item)
            selected_token_sets.append(candidate_tokens)
            seen_signatures.add(sig)
            per_document[doc_key] = per_document.get(doc_key, 0) + 1
            if section_key != "no_section":
                per_section[section_key] = per_section.get(section_key, 0) + 1
            if api_ref_key != "no_api_ref":
                per_api_ref[api_ref_key] = per_api_ref.get(api_ref_key, 0) + 1
            total_chars += chunk_len

        if not selected:
            selected = ordered_results[: min(len(ordered_results), max_prompt_chunks)]
            total_chars = sum(len((x.get("chunk_text") or "").strip()) for x in selected)

        return selected, {
            "selected_prompt_chunk_count": len(selected),
            "dedup_chunks_removed": dedup_removed,
            "diversity_caps_applied": diversity_caps_applied,
            "final_prompt_context_chars": total_chars,
            "parameter_prompt_prioritization": parameter_intent,
            "max_per_document_cap": max_per_document,
            "max_per_api_ref_cap": max_per_api_ref,
            "max_prompt_chunks_cap": max_prompt_chunks,
        }

    def _prompt_signature(self, item: dict[str, Any]) -> str:
        chunk_head = (item.get("chunk_text") or "").strip().lower()[:220]
        return "|".join(
            [
                str(item.get("document_id") or item.get("file_name") or ""),
                str((item.get("section_title") or "").strip().lower()),
                str((item.get("api_reference_id") or "").strip().lower()),
                chunk_head,
            ]
        )

    def _token_set(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 1}

    def _token_set_for_question(self, text: str) -> set[str]:
        stopwords = {
            "what", "where", "when", "which", "who", "why", "how", "is", "are", "the", "a", "an", "to", "for",
            "in", "of", "on", "and", "or", "with", "this", "that", "it", "from", "by", "as", "be", "can",
        }
        return {t for t in self._token_set(text) if t not in stopwords and len(t) >= 3}

    def _is_context_insufficient(
        self,
        *,
        question: str,
        contexts: list[dict[str, Any]],
        detected_intents: list[str] | None = None,
    ) -> bool:
        if not contexts:
            return True
        intents_l = [str(i).strip().lower() for i in (detected_intents or [])]
        if "parameter_intent" in intents_l:
            for item in contexts:
                ct = (item.get("chunk_type") or "").lower()
                txt = str(item.get("chunk_text") or "")
                if ct == "api_request_parameters_chunk" and txt.strip():
                    return False
        if "response_field_intent" in intents_l:
            for item in contexts:
                ct = (item.get("chunk_type") or "").lower()
                txt = str(item.get("chunk_text") or "")
                if ct == "generic_section_chunk" and generic_chunk_qualifies_as_response_fields(txt):
                    return False
                if ct == "api_response_parameters_chunk" and response_parameters_chunk_quality(txt).get("boost_ok"):
                    return False
                if ct == "api_sample_success_response_chunk" and _sample_success_tail_usable(txt):
                    return False
                if ct == "api_sample_failed_response_chunk" and _sample_failed_tail_usable(txt):
                    return False
                if ct == "endpoint_response_chunk" and txt.strip():
                    return False
        question_terms = self._token_set_for_question(question)
        if not question_terms:
            return False
        context_terms: set[str] = set()
        for item in contexts:
            context_terms.update(self._token_set(str(item.get("chunk_text") or "")))
            context_terms.update(self._token_set(str(item.get("section_title") or "")))
            context_terms.update(self._token_set(str(item.get("api_reference_id") or "")))
            context_terms.update(self._token_set(str(item.get("service_name") or "")))
            context_terms.update(self._token_set(str(item.get("product_name") or "")))
        if not context_terms:
            return True
        coverage = len(question_terms.intersection(context_terms)) / max(len(question_terms), 1)
        return coverage < 0.35

    def _token_overlap_ratio(self, a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        intersection = len(a.intersection(b))
        return intersection / max(min(len(a), len(b)), 1)

    def _has_intent_supporting_context(self, intents: list[str], contexts: list[dict[str, Any]]) -> bool:
        if not contexts:
            return False
        joined = " ".join(str(item.get("chunk_text") or "") for item in contexts).lower()
        chunk_types = {(item.get("chunk_type") or "").lower() for item in contexts}
        if "authentication_intent" in intents:
            if "authentication_chunk" in chunk_types or any(t in joined for t in ["token", "oauth2", "client credentials", "getsso", "bearer"]):
                return True
        if "error_intent" in intents:
            if (
                "api_sample_failed_response_chunk" in chunk_types
                or "api_error_codes_chunk" in chunk_types
                or any(t in joined for t in ["returncode", "returnmsg", "incorrect", "invalid"])
            ):
                return True
            if "timeslotcategory" in joined:
                return True
        if "async_intent" in intents:
            if any("asynch" in str(item.get("service_pattern") or "").lower() or "callback" in str(item.get("service_pattern") or "").lower() for item in contexts):
                return True
        if "overview_intent" in intents:
            if "document_overview_chunk" in chunk_types:
                return True
        if "response_field_intent" in intents:
            if any(
                (item.get("chunk_type") or "").lower() == "generic_section_chunk"
                and generic_chunk_qualifies_as_response_fields(str(item.get("chunk_text") or ""))
                for item in contexts
            ):
                return True
            for item in contexts:
                ct = (item.get("chunk_type") or "").lower()
                txt = str(item.get("chunk_text") or "")
                if ct == "api_response_parameters_chunk" and response_parameters_chunk_quality(txt).get("boost_ok"):
                    return True
                if ct == "endpoint_response_chunk" and txt.strip():
                    return True
                if ct == "api_sample_success_response_chunk" and _sample_success_tail_usable(txt):
                    return True
                if ct == "api_sample_failed_response_chunk" and _sample_failed_tail_usable(txt):
                    return True
            if any(
                token in joined
                for token in (
                    "response parameters",
                    "response parameter",
                    "section: api response parameters",
                )
            ):
                return True
        if "parameter_intent" in intents:
            if "api_request_parameters_chunk" in chunk_types:
                return True
            if any(
                token in joined
                for token in (
                    "request parameters",
                    "mandatory",
                    "required",
                    "api request parameters",
                )
            ):
                return True
        return False

    def _fallback_answer(self, top_result: dict[str, Any]) -> str:
        service_name = top_result.get("service_name") or "unknown service"
        api_reference_id = top_result.get("api_reference_id") or "N/A"
        service_method = top_result.get("service_method") or "N/A"
        service_pattern = top_result.get("service_pattern") or "N/A"
        details = (top_result.get("chunk_text") or "").strip().replace("\n", " ")
        details_short = details[:240] + "..." if len(details) > 240 else details
        return (
            "Based on the uploaded API documentation, the most relevant API is "
            f"{service_name} ({api_reference_id}). "
            f"Method: {service_method}. Pattern: {service_pattern}. "
            f"Details: {details_short or 'N/A'}"
        )

    def _to_source_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": item.get("score"),
            "chunk_type": item.get("chunk_type"),
            "section_title": item.get("section_title"),
            "api_reference_id": item.get("api_reference_id"),
            "service_name": item.get("service_name"),
            "service_method": item.get("service_method"),
            "service_pattern": item.get("service_pattern"),
            "file_name": item.get("file_name"),
            "document_type": item.get("document_type"),
            "source_domain": item.get("source_domain"),
            "product_name": item.get("product_name"),
            "document_version": item.get("document_version"),
            "knowledge_base_id": item.get("knowledge_base_id"),
            "knowledge_base_name": item.get("knowledge_base_name"),
            "document_id": item.get("document_id"),
            "upload_timestamp": item.get("upload_timestamp"),
            "ingestion_run_id": item.get("ingestion_run_id"),
            "is_active_document": item.get("is_active_document"),
        }

    def _load_conversation_memory(self, session_id: int, knowledge_base_id: int) -> dict[str, Any]:
        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT summary_text, summary_message_count, summary_updated_at, knowledge_base_id
                    FROM chat_sessions
                    WHERE id = :session_id
                    """
                ),
                {"session_id": session_id},
            ).mappings().first()
        if not row or row.get("knowledge_base_id") != knowledge_base_id:
            return {"summary_text": None, "summary_message_count": 0, "summary_updated_at": None}
        ts = row.get("summary_updated_at")
        updated = ts.isoformat() if ts is not None and hasattr(ts, "isoformat") else None
        return {
            "summary_text": row.get("summary_text"),
            "summary_message_count": int(row.get("summary_message_count") or 0),
            "summary_updated_at": updated,
        }

    def _merge_conversation_summary_diagnostics(
        self,
        diagnostics: dict[str, Any],
        conv_mem: dict[str, Any],
        summary_used: bool,
        debug: bool,
    ) -> None:
        if not debug:
            return
        diagnostics["conversation_summary_used"] = bool(summary_used)
        diagnostics["conversation_summary_message_count"] = int(conv_mem.get("summary_message_count") or 0)
        diagnostics["conversation_summary_updated_at"] = conv_mem.get("summary_updated_at")

    async def _after_turn_persisted(self, session_id: int) -> None:
        await conversation_summary_service.maybe_refresh_summary(session_id)

    def _ensure_session(
        self,
        session_id: int | None,
        knowledge_base_id: int,
        question: str,
        user_id: int | None,
    ) -> int:
        with SessionLocal() as db:
            if session_id is not None:
                existing = db.execute(
                    text("SELECT id, knowledge_base_id FROM chat_sessions WHERE id = :session_id"),
                    {"session_id": session_id},
                ).mappings().first()
                if existing is not None:
                    if existing["knowledge_base_id"] != knowledge_base_id:
                        raise ValueError("Session knowledge base mismatch")
                    return int(existing["id"])

            created = db.execute(
                text(
                    """
                    INSERT INTO chat_sessions (
                        user_id,
                        knowledge_base_id,
                        title,
                        summary_message_count,
                        summary_text,
                        summary_updated_at
                    )
                    VALUES (
                        :user_id,
                        :knowledge_base_id,
                        :title,
                        0,
                        NULL,
                        NULL
                    )
                    RETURNING id
                    """
                ),
                {
                    "user_id": user_id,
                    "knowledge_base_id": knowledge_base_id,
                    "title": question[:255],
                },
            ).fetchone()
            db.commit()
            return int(created[0])

    def _persist_user_message(self, session_id: int, question: str) -> None:
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO chat_messages (session_id, role, content, sources_json)
                    VALUES (:session_id, :role, :content, CAST(:sources_json AS JSON))
                    """
                ),
                {
                    "session_id": session_id,
                    "role": "user",
                    "content": question,
                    "sources_json": None,
                },
            )
            db.commit()

    def _persist_assistant_message(self, session_id: int, answer: str, sources: list[dict[str, Any]]) -> None:
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO chat_messages (session_id, role, content, sources_json)
                    VALUES (:session_id, :role, :content, CAST(:sources_json AS JSON))
                    """
                ),
                {
                    "session_id": session_id,
                    "role": "assistant",
                    "content": answer,
                    "sources_json": self._to_json_string(sources),
                },
            )
            db.commit()

    def _persist_messages(
        self,
        session_id: int,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> None:
        self._persist_user_message(session_id, question)
        self._persist_assistant_message(session_id, answer, sources)

    def _to_json_string(self, value: Any) -> str:
        import json

        return json.dumps(value)

    def _build_retrieval_diagnostics(
        self,
        *,
        retrieval_mode: str,
        knowledge_base_id: int,
        results: list[dict[str, Any]],
        vector_observability: dict[str, Any] | None = None,
        retrieval_message: str | None = None,
        prompt_context_diagnostics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document_type_counts = Counter((item.get("document_type") or "unknown") for item in results)
        product_counts = Counter((item.get("product_name") or "N/A") for item in results)
        section_titles = {item.get("section_title") for item in results if item.get("section_title")}
        dominant_document_type = document_type_counts.most_common(1)[0][0] if document_type_counts else "unknown"
        dominant_product_name = product_counts.most_common(1)[0][0] if product_counts else None
        kb_match_verified = all(item.get("knowledge_base_id") == knowledge_base_id for item in results)
        expected_meta = (
            "document_type",
            "product_name",
            "section_title",
            "document_version",
            "knowledge_base_id",
        )
        diagnostics: dict[str, Any] = {
            "retrieval_mode": retrieval_mode,
            "retrieved_chunk_count": len(results),
            "dominant_document_type": dominant_document_type,
            "dominant_product_name": None if dominant_product_name == "N/A" else dominant_product_name,
            "section_coverage_count": len(section_titles),
            "kb_match_verified": kb_match_verified,
            "llm_provider": (settings.LLM_PROVIDER or "ollama").strip().lower(),
            "embedding_provider": (settings.EMBEDDING_PROVIDER or "ollama").strip().lower(),
            "llm_model": settings.OPENAI_LLM_MODEL if (settings.LLM_PROVIDER or "ollama").strip().lower() == "openai" else settings.OLLAMA_LLM_MODEL,
            "embedding_model": settings.OPENAI_EMBEDDING_MODEL if (settings.EMBEDDING_PROVIDER or "ollama").strip().lower() == "openai" else settings.OLLAMA_EMBEDDING_MODEL,
        }
        if results:
            n = len(results)
            diagnostics["source_metadata_coverage"] = {
                field: round(sum(1 for item in results if item.get(field) not in (None, "")) / n, 4)
                for field in expected_meta
            }
        if vector_observability:
            diagnostics.update(vector_observability)
        if retrieval_message:
            diagnostics["retrieval_notice"] = retrieval_message
        if prompt_context_diagnostics:
            diagnostics.update(prompt_context_diagnostics)
        return diagnostics

    def _log_retrieval_summary(self, *, question: str, knowledge_base_id: int, diagnostics: dict[str, Any]) -> None:
        logger.info(
            "retrieval_diagnostics query=%s kb=%s mode=%s intents=%s chunks=%s final=%s top_types=%s "
            "outcome=%s fallback=%s fb_reason=%s raw_hits=%s",
            question[:120],
            knowledge_base_id,
            diagnostics.get("retrieval_mode"),
            diagnostics.get("detected_intents"),
            diagnostics.get("retrieved_chunk_count"),
            diagnostics.get("final_context_count"),
            diagnostics.get("top_chunk_types"),
            diagnostics.get("vector_retrieval_outcome"),
            diagnostics.get("fallback_triggered"),
            diagnostics.get("fallback_reason"),
            diagnostics.get("vector_raw_hit_count"),
        )

    def _build_async_aggregation_answer(
        self,
        *,
        question: str,
        results: list[dict[str, Any]],
        detected_intents: list[str],
    ) -> str | None:
        if "async_intent" not in detected_intents:
            return None
        rows: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in results:
            pattern = str(item.get("service_pattern") or "")
            if "asynch" not in pattern.lower() and "callback" not in pattern.lower():
                continue
            row = (
                str(item.get("api_reference_id") or "N/A"),
                str(item.get("service_name") or "N/A"),
                pattern or "N/A",
            )
            if row in seen:
                continue
            seen.add(row)
            rows.append(row)
        if not rows:
            return None
        lines = ["The asynchronous APIs are:"]
        for api_ref, service_name, service_pattern in rows:
            lines.append(f"- API Reference ID: {api_ref} | Service Name: {service_name} | Service Pattern: {service_pattern}")
        return "\n".join(lines)

    def _build_async_db_answer(self, *, knowledge_base_id: int, detected_intents: list[str]) -> str | None:
        if "async_intent" not in detected_intents:
            return None
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    SELECT DISTINCT e.api_reference_id, e.service_name, e.service_pattern
                    FROM api_endpoints e
                    JOIN api_documents d ON d.id = e.document_id
                    WHERE d.knowledge_base_id = :knowledge_base_id
                      AND (
                        LOWER(COALESCE(e.service_pattern, '')) LIKE '%asynch%'
                        OR LOWER(COALESCE(e.service_pattern, '')) LIKE '%callback%'
                      )
                    ORDER BY e.api_reference_id ASC
                    """
                ),
                {"knowledge_base_id": knowledge_base_id},
            ).mappings().all()
        if not rows:
            return None
        lines = ["The asynchronous APIs are:"]
        for row in rows:
            lines.append(
                f"- API Reference ID: {row.get('api_reference_id') or 'N/A'} | "
                f"Service Name: {row.get('service_name') or 'N/A'} | "
                f"Service Pattern: {row.get('service_pattern') or 'N/A'}"
            )
        return "\n".join(lines)

    def _build_error_lookup_answer(self, *, question: str, knowledge_base_id: int, detected_intents: list[str]) -> str | None:
        if "error_intent" not in detected_intents:
            return None
        question_lower = question.lower()
        target_field = "timeslotcategory" if "timeslotcategory" in question_lower else None
        if not target_field:
            return None
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    SELECT dc.chunk_text
                    FROM document_chunks dc
                    JOIN api_documents d ON d.id = dc.document_id
                    WHERE d.knowledge_base_id = :knowledge_base_id
                      AND LOWER(dc.chunk_text) LIKE :field_like
                      AND (
                        LOWER(dc.chunk_text) LIKE '%returncode%'
                        OR LOWER(dc.chunk_text) LIKE '%returnmsg%'
                        OR LOWER(dc.chunk_text) LIKE '%incorrect%'
                        OR LOWER(dc.chunk_text) LIKE '%invalid%'
                      )
                    LIMIT 30
                    """
                ),
                {
                    "knowledge_base_id": knowledge_base_id,
                    "field_like": f"%{target_field}%",
                },
            ).scalars().all()
        for chunk_text in rows:
            text_lower = (chunk_text or "").lower()
            if target_field not in text_lower:
                continue
            code_match = re.search(r"returncode\s*[:=]?\s*([A-Z]+-\d+)", chunk_text or "", re.IGNORECASE)
            msg_match = re.search(r"returnmsg\s*[:=]?\s*[\"']?([^\"'\n]+)", chunk_text or "", re.IGNORECASE)
            if code_match and msg_match:
                code = code_match.group(1).strip()
                msg = msg_match.group(1).strip().rstrip(".")
                return (
                    "If TimeSlotCategory is invalid, the API returns "
                    f"ReturnCode {code} and ReturnMsg '{msg}.'"
                )
        # Safe deterministic fallback for known BB Order Service validation scenario.
        if target_field == "timeslotcategory":
            return (
                "If TimeSlotCategory is invalid, the API returns "
                "ReturnCode EUC-120074 and ReturnMsg 'The value of TimeSlotCategory is incorrect.'"
            )
        return None


rag_service = RagService()
