from __future__ import annotations

from collections import Counter
from typing import Any


def build_rag_prompt(
    question: str,
    contexts: list[dict[str, Any]],
    *,
    prompt_mode: str = "api",
    session_summary: str | None = None,
    response_field_instruction: str | None = None,
) -> str:
    if prompt_mode == "product":
        return _build_product_prompt(question=question, contexts=contexts, session_summary=session_summary)
    if prompt_mode == "hr":
        return _build_generic_prompt(question=question, contexts=contexts, session_summary=session_summary)
    return _build_api_prompt(
        question=question,
        contexts=contexts,
        session_summary=session_summary,
        response_field_instruction=response_field_instruction,
    )


def _session_memory_prefix(session_summary: str | None) -> str:
    if not session_summary or not str(session_summary).strip():
        return ""
    return (
        "Prior turns in this chat session (session memory only — supports follow-ups and continuity; "
        "does not replace or override facts from the knowledge base context below):\n"
        f"{str(session_summary).strip()}\n\n"
    )


def detect_prompt_mode(contexts: list[dict[str, Any]]) -> str:
    if not contexts:
        return "api"
    first_type = (contexts[0].get("document_type") or "").strip().lower()
    if first_type in {"api", "product", "hr"}:
        return first_type
    counts = Counter((item.get("document_type") or "").strip().lower() for item in contexts)
    for mode in ("product", "api", "hr"):
        if counts.get(mode):
            return mode
    return "api"


def _build_api_prompt(
    question: str,
    contexts: list[dict[str, Any]],
    *,
    session_summary: str | None = None,
    response_field_instruction: str | None = None,
) -> str:
    context_blocks: list[str] = []
    for idx, item in enumerate(contexts, start=1):
        ct_display = item.get("chunk_type") or "N/A"
        if str(ct_display).lower() == "generic_section_chunk" and "recovered response parameters" in str(item.get("chunk_text") or "").lower():
            ct_display = "generic_section_chunk (Recovered Response Parameters)"
        context_blocks.append(
            "\n".join(
                [
                    f"[Context {idx}]",
                    f"API Reference ID: {item.get('api_reference_id') or 'N/A'}",
                    f"Service Name: {item.get('service_name') or 'N/A'}",
                    f"Service Method: {item.get('service_method') or 'N/A'}",
                    f"Service Pattern: {item.get('service_pattern') or 'N/A'}",
                    f"File Name: {item.get('file_name') or 'N/A'}",
                    f"Chunk Type: {ct_display}",
                    f"Chunk Text: {item.get('chunk_text') or 'N/A'}",
                ]
            )
        )

    context_text = "\n\n".join(context_blocks) if context_blocks else "No context provided."
    mem = _session_memory_prefix(session_summary)
    rf_extra = ""
    if response_field_instruction and str(response_field_instruction).strip():
        rf_extra = f"{str(response_field_instruction).strip()}\n\n"
    return (
        "You are an assistant for enterprise API documentation.\n"
        "Answer only using the provided API documentation context.\n"
        "Do not invent APIs, fields, URLs, or response codes.\n"
        'If context is insufficient, respond exactly with: "I could not find enough information in the uploaded API documentation."\n'
        "Include API reference ID and service name when available.\n"
        "Keep the answer concise and clear.\n\n"
        f"{mem}"
        f"{rf_extra}"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:"
    )


def _build_product_prompt(question: str, contexts: list[dict[str, Any]], *, session_summary: str | None = None) -> str:
    context_blocks: list[str] = []
    for idx, item in enumerate(contexts, start=1):
        product_name = item.get("product_name") or "N/A"
        section_title = item.get("section_title") or "General"
        context_blocks.append(
            "\n".join(
                [
                    f"[Context {idx}]",
                    f"[Product: {product_name}]",
                    f"[Section: {section_title}]",
                    f"File Name: {item.get('file_name') or 'N/A'}",
                    f"Chunk Type: {item.get('chunk_type') or 'N/A'}",
                    f"Chunk Text: {item.get('chunk_text') or 'N/A'}",
                ]
            )
        )

    context_text = "\n\n".join(context_blocks) if context_blocks else "No context provided."
    mem = _session_memory_prefix(session_summary)
    return (
        "You are an assistant for enterprise product documentation and user guides.\n"
        "Answer only using the provided product documentation context.\n"
        "Prefer practical, user-friendly guidance with clear workflow steps.\n"
        "Explain configuration and feature usage in plain language when context supports it.\n"
        "If the question asks for technical details and those details exist in context, include them clearly.\n"
        'If context is insufficient, respond exactly with: "I could not find enough information in the uploaded API documentation."\n'
        "Keep the answer concise and actionable.\n\n"
        f"{mem}"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:"
    )


def _build_generic_prompt(question: str, contexts: list[dict[str, Any]], *, session_summary: str | None = None) -> str:
    context_blocks: list[str] = []
    for idx, item in enumerate(contexts, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[Context {idx}]",
                    f"Document Type: {item.get('document_type') or 'N/A'}",
                    f"File Name: {item.get('file_name') or 'N/A'}",
                    f"Chunk Type: {item.get('chunk_type') or 'N/A'}",
                    f"Chunk Text: {item.get('chunk_text') or 'N/A'}",
                ]
            )
        )
    context_text = "\n\n".join(context_blocks) if context_blocks else "No context provided."
    mem = _session_memory_prefix(session_summary)
    return (
        "You are an assistant for enterprise documentation.\n"
        "Answer only from the provided context.\n"
        'If context is insufficient, respond exactly with: "I could not find enough information in the uploaded API documentation."\n'
        "Keep the answer concise and clear.\n\n"
        f"{mem}"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:"
    )
