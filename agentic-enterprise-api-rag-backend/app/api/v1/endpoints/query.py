import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Any

from app.agents.orchestrator import agent_orchestrator
from app.api.deps import check_knowledge_base_access, require_permission
from app.core.config import settings
from app.db.database import get_db
from app.services.rag_service import rag_service

router = APIRouter(prefix="/query")


class AskRequest(BaseModel):
    project_id: int
    knowledge_base_id: int
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: int | None = None
    debug: bool = False


class AskResponse(BaseModel):
    session_id: int
    project_id: int
    knowledge_base_id: int
    question: str
    answer: str
    retrieval_mode: str
    llm_status: str
    sources: list[dict[str, Any]]
    suggested_questions: list[str] = []
    confidence: dict[str, Any] | None = None
    impact_analysis: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    current_user: dict = Depends(require_permission("query.ask")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        kb = db.execute(
            text("SELECT id, is_active FROM knowledge_bases WHERE id = :kb_id"),
            {"kb_id": payload.knowledge_base_id},
        ).mappings().first()
        if kb is None or not kb["is_active"]:
            raise HTTPException(status_code=404, detail="Knowledge base not found or inactive")
        if not check_knowledge_base_access(
            db=db,
            user_id=current_user["id"],
            knowledge_base_id=payload.knowledge_base_id,
            access_level="read",
        ):
            raise HTTPException(status_code=403, detail="Knowledge base access denied")
        if getattr(settings, "ENABLE_AGENT_ORCHESTRATION", False):
            return await agent_orchestrator.run_query_ask(
                project_id=payload.project_id,
                knowledge_base_id=payload.knowledge_base_id,
                question=payload.question,
                top_k=payload.top_k,
                session_id=payload.session_id,
                user_id=current_user["id"],
                debug=payload.debug,
            )
        return await rag_service.answer_question(
            project_id=payload.project_id,
            knowledge_base_id=payload.knowledge_base_id,
            question=payload.question,
            top_k=payload.top_k,
            session_id=payload.session_id,
            user_id=current_user["id"],
            debug=payload.debug,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG answer failed: {exc}") from exc


def _format_sse(event_name: str, data: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ask-stream")
async def ask_question_stream(
    payload: AskRequest,
    current_user: dict = Depends(require_permission("query.ask")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Same behavior as POST /query/ask but streams Server-Sent Events (SSE).
    Event types: start, token, sources, diagnostics, done, error.
    """
    try:
        kb = db.execute(
            text("SELECT id, is_active FROM knowledge_bases WHERE id = :kb_id"),
            {"kb_id": payload.knowledge_base_id},
        ).mappings().first()
        if kb is None or not kb["is_active"]:
            raise HTTPException(status_code=404, detail="Knowledge base not found or inactive")
        if not check_knowledge_base_access(
            db=db,
            user_id=current_user["id"],
            knowledge_base_id=payload.knowledge_base_id,
            access_level="read",
        ):
            raise HTTPException(status_code=403, detail="Knowledge base access denied")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def event_generator():
        try:
            async for item in rag_service.answer_question_stream(
                project_id=payload.project_id,
                knowledge_base_id=payload.knowledge_base_id,
                question=payload.question,
                top_k=payload.top_k,
                session_id=payload.session_id,
                user_id=current_user["id"],
                debug=payload.debug,
            ):
                ev = str(item.get("event") or "message")
                data = item.get("data")
                if not isinstance(data, dict):
                    data = {}
                yield _format_sse(ev, data)
        except Exception as exc:
            yield _format_sse("error", {"detail": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("chat.read")),
) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                s.id,
                s.title,
                s.created_at,
                s.knowledge_base_id,
                kb.name AS knowledge_base_name
            FROM chat_sessions s
            LEFT JOIN knowledge_bases kb ON kb.id = s.knowledge_base_id
            JOIN user_knowledge_base_access uka ON uka.knowledge_base_id = s.knowledge_base_id
            WHERE uka.user_id = :user_id
            ORDER BY s.id DESC
            """
        ),
        {"user_id": current_user["id"]},
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "knowledge_base_id": row["knowledge_base_id"],
            "knowledge_base_name": row["knowledge_base_name"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("chat.read")),
) -> dict:
    session_exists = db.execute(
        text(
            """
            SELECT
                s.id,
                s.knowledge_base_id,
                kb.name AS knowledge_base_name
            FROM chat_sessions s
            LEFT JOIN knowledge_bases kb ON kb.id = s.knowledge_base_id
            JOIN user_knowledge_base_access uka ON uka.knowledge_base_id = s.knowledge_base_id
            WHERE s.id = :session_id
              AND uka.user_id = :user_id
            """
        ),
        {"session_id": session_id, "user_id": current_user["id"]},
    ).mappings().first()
    if session_exists is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    rows = db.execute(
        text(
            """
            SELECT id, role, content, sources_json, created_at
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY id ASC
            """
        ),
        {"session_id": session_id},
    ).mappings().all()

    return {
        "session_id": session_id,
        "knowledge_base_id": session_exists["knowledge_base_id"],
        "knowledge_base_name": session_exists["knowledge_base_name"],
        "messages": [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "sources_json": row["sources_json"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ],
    }
