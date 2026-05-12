"""Session-level conversation summarization (additive; no cross-session / cross-KB memory)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.database import SessionLocal
from app.services.ollama_client import ollama_client
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)


def _format_messages_for_prompt(rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for row in rows:
        role = str(row.get("role") or "").strip()
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _build_merge_summary_prompt(*, prior_summary: str | None, transcript: str) -> str:
    prior = (prior_summary or "").strip()
    prior_block = f"Existing summary (may be empty):\n{prior}\n\n" if prior else ""
    return (
        "You are summarizing a single chat session for a retrieval-assistant.\n"
        "Produce a concise summary (max ~400 words) of topics discussed, user goals, and decisions.\n"
        "Use only information present in the transcript and existing summary.\n"
        "Do not invent APIs, products, or policies.\n"
        "Output plain text only — no markdown headings required.\n\n"
        f"{prior_block}"
        f"Messages to incorporate:\n{transcript}\n\n"
        "Merged session summary:"
    )


class ConversationSummaryService:
    async def maybe_refresh_summary(self, session_id: int) -> None:
        if not getattr(settings, "ENABLE_CONVERSATION_SUMMARY", True):
            return
        trigger = max(1, int(getattr(settings, "SUMMARY_TRIGGER_MESSAGE_COUNT", 8)))
        max_lines = max(1, int(getattr(settings, "SUMMARY_MAX_MESSAGES", 20)))

        prompt: str | None = None
        with SessionLocal() as db:
            acount = db.execute(
                text(
                    """
                    SELECT COUNT(*) AS c
                    FROM chat_messages
                    WHERE session_id = :session_id AND role = 'assistant'
                    """
                ),
                {"session_id": session_id},
            ).scalar()
            assistant_count = int(acount or 0)
            if assistant_count < trigger or assistant_count % trigger != 0:
                return

            session_row = db.execute(
                text(
                    """
                    SELECT id, knowledge_base_id, summary_text
                    FROM chat_sessions
                    WHERE id = :session_id
                    """
                ),
                {"session_id": session_id},
            ).mappings().first()
            if session_row is None:
                return

            rows = db.execute(
                text(
                    """
                    SELECT role, content
                    FROM chat_messages
                    WHERE session_id = :session_id
                    ORDER BY id ASC
                    """
                ),
                {"session_id": session_id},
            ).mappings().all()
            msg_rows = [dict(r) for r in rows]
            if not msg_rows:
                return

            if len(msg_rows) > max_lines:
                msg_rows = msg_rows[-max_lines:]
            transcript = _format_messages_for_prompt(msg_rows)
            prior_summary = session_row.get("summary_text")
            prompt = _build_merge_summary_prompt(
                prior_summary=str(prior_summary) if prior_summary else None,
                transcript=transcript,
            )

        summary_text: str | None = None
        llm_provider = (settings.LLM_PROVIDER or "ollama").strip().lower()
        try:
            if llm_provider == "openai":
                summary_text = await openai_client.generate(prompt or "", model=settings.OPENAI_LLM_MODEL)
            else:
                llm_response = await ollama_client.generate_test(prompt or "")
                summary_text = (llm_response.get("response") or "").strip()
        except Exception as exc:
            logger.warning("conversation summary generation failed session_id=%s: %s", session_id, exc)
            return

        if not summary_text or not summary_text.strip():
            return
        summary_text = summary_text.strip()
        if len(summary_text) > 12000:
            summary_text = summary_text[:12000] + "…"

        with SessionLocal() as db:
            total_messages = int(
                db.execute(
                    text("SELECT COUNT(*) FROM chat_messages WHERE session_id = :session_id"),
                    {"session_id": session_id},
                ).scalar()
                or 0
            )
            db.execute(
                text(
                    """
                    UPDATE chat_sessions
                    SET summary_text = :summary_text,
                        summary_updated_at = NOW(),
                        summary_message_count = :summary_message_count
                    WHERE id = :session_id
                    """
                ),
                {
                    "session_id": session_id,
                    "summary_text": summary_text,
                    "summary_message_count": total_messages,
                },
            )
            db.commit()


conversation_summary_service = ConversationSummaryService()
