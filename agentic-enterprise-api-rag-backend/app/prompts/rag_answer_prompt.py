from __future__ import annotations

from collections import Counter
from typing import Any


def build_rag_prompt(
    question: str,
    contexts: list[dict[str, Any]],
    *,
    prompt_mode: str = "api",
) -> str:
    if prompt_mode == "product":
        return _build_product_prompt(question=question, contexts=contexts)
    if prompt_mode == "hr":
        return _build_generic_prompt(question=question, contexts=contexts)
    return _build_api_prompt(question=question, contexts=contexts)


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


def _build_api_prompt(question: str, contexts: list[dict[str, Any]]) -> str:
    context_blocks: list[str] = []
    for idx, item in enumerate(contexts, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[Context {idx}]",
                    f"API Reference ID: {item.get('api_reference_id') or 'N/A'}",
                    f"Service Name: {item.get('service_name') or 'N/A'}",
                    f"Service Method: {item.get('service_method') or 'N/A'}",
                    f"Service Pattern: {item.get('service_pattern') or 'N/A'}",
                    f"File Name: {item.get('file_name') or 'N/A'}",
                    f"Chunk Type: {item.get('chunk_type') or 'N/A'}",
                    f"Chunk Text: {item.get('chunk_text') or 'N/A'}",
                ]
            )
        )

    context_text = "\n\n".join(context_blocks) if context_blocks else "No context provided."
    return (
        "You are an assistant for enterprise API documentation.\n"
        "Answer only using the provided API documentation context.\n"
        "Do not invent APIs, fields, URLs, or response codes.\n"
        'If context is insufficient, respond exactly with: "I could not find enough information in the uploaded API documentation."\n'
        "Include API reference ID and service name when available.\n"
        "Keep the answer concise and clear.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:"
    )


def _build_product_prompt(question: str, contexts: list[dict[str, Any]]) -> str:
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
    return (
        "You are an assistant for enterprise product documentation and user guides.\n"
        "Answer only using the provided product documentation context.\n"
        "Prefer practical, user-friendly guidance with clear workflow steps.\n"
        "Explain configuration and feature usage in plain language when context supports it.\n"
        "If the question asks for technical details and those details exist in context, include them clearly.\n"
        'If context is insufficient, respond exactly with: "I could not find enough information in the uploaded API documentation."\n'
        "Keep the answer concise and actionable.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:"
    )


def _build_generic_prompt(question: str, contexts: list[dict[str, Any]]) -> str:
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
    return (
        "You are an assistant for enterprise documentation.\n"
        "Answer only from the provided context.\n"
        'If context is insufficient, respond exactly with: "I could not find enough information in the uploaded API documentation."\n'
        "Keep the answer concise and clear.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:"
    )
