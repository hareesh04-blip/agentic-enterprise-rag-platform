from fastapi import APIRouter

from app.api.v1.endpoints.admin_demo_data import router as admin_demo_data_router
from app.api.v1.endpoints.admin_demo_evidence_pack import router as admin_demo_evidence_pack_router
from app.api.v1.endpoints.admin_demo_runbook import router as admin_demo_runbook_router
from app.api.v1.endpoints.admin_test_data_cleanup import router as admin_test_data_cleanup_router
from app.api.v1.endpoints.admin_demo_readiness import router as admin_demo_readiness_router
from app.api.v1.endpoints.admin_demo_script import router as admin_demo_script_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.chunking import router as chunking_router
from app.api.v1.endpoints.diagnostics import router as diagnostics_router
from app.api.v1.endpoints.db import router as db_router
from app.api.v1.endpoints.embedding import router as embedding_router
from app.api.v1.endpoints.feedback import router as feedback_router
from app.api.v1.endpoints.improvements import router as improvements_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.ingestion import router as ingestion_router
from app.api.v1.endpoints.knowledge_bases import router as knowledge_bases_router
from app.api.v1.endpoints.ollama import router as ollama_router
from app.api.v1.endpoints.parser import router as parser_router
from app.api.v1.endpoints.query import router as query_router
from app.api.v1.endpoints.qdrant import router as qdrant_router
from app.api.v1.endpoints.retrieval import router as retrieval_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(diagnostics_router, tags=["Diagnostics"])
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(db_router, tags=["Database"])
api_router.include_router(embedding_router, tags=["Embedding"])
api_router.include_router(ollama_router, tags=["Ollama"])
api_router.include_router(parser_router, tags=["Parser"])
api_router.include_router(chunking_router, tags=["Chunking"])
api_router.include_router(qdrant_router, tags=["Qdrant"])
api_router.include_router(ingestion_router, tags=["Ingestion"])
api_router.include_router(knowledge_bases_router, tags=["KnowledgeBases"])
api_router.include_router(retrieval_router, tags=["Retrieval"])
api_router.include_router(query_router, tags=["Query"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(improvements_router, prefix="/improvements", tags=["Improvements"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit"])
api_router.include_router(admin_demo_readiness_router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_demo_script_router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_demo_data_router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_demo_evidence_pack_router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_demo_runbook_router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_test_data_cleanup_router, prefix="/admin", tags=["Admin"])
api_router.include_router(users_router, tags=["Users"])
