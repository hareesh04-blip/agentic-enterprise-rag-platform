# Project name
Agentic Enterprise API RAG Backend

## Current architecture
- FastAPI backend on Windows
- PostgreSQL for metadata/RBAC/chat history
- Qdrant for vector DB
- Config-driven LLM/embedding provider abstraction
- Provider switching is config-only (OpenAI + Ollama)
- Provider-aware Qdrant collections implemented
- Provider-aware vector dimensions implemented
- Redis planned
- Neo4j disabled for Phase 1
- Mac Ollama via Caddy:
  http://172.16.111.209:8080
- OpenAI support added for POC/demo stability
- Backend runs on:
  http://127.0.0.1:8010
- Run backend WITHOUT --reload
- Frontend stack:
  - React
  - TypeScript
  - Vite
  - Tailwind CSS
  - React Router
  - Axios
- Frontend characteristics:
  - role-aware routing
  - KB-aware UI visibility
  - RBAC-aligned navigation
  - provider-aware UX
  - diagnostics-aware UI
  - workspace-driven architecture

## Current completed status
- Step 15: Chat session persistence
- Step 16: JWT Auth + RBAC + User Management
- Step 16.9: Swagger/OpenAPI Bearer Auth polish
- Step 17.1: Knowledge Base CRUD
- Step 17.2: Documents linked to Knowledge Bases
- Step 17.3: Knowledge Base aware query/retrieval
- Step 17.4: Knowledge Base aware chat sessions
- Step 17.5: Knowledge Base Access Management Polish
- Step 18.1: Product Document Classification + Metadata Enrichment
- Step 18.2: Product-oriented Chunking Strategy
- Step 18.3: Product-aware Prompting
- Step 18.4: Product Document Metadata Enrichment Polish
- Step 18.5: Product Documentation Retrieval Validation
- Step 19.1: Ollama Connectivity Stabilization
- Step 19.2: Embedding persistence and vector retrieval validation
- Step 20.1: Provider abstraction (OpenAI + Ollama)
- Step 20.2: Retrieval quality and response quality improvements (**mostly completed: Phase A + Phase B + Phase C implemented**)
- Step 20.3: Evaluation hardening and demo-readiness validation
- Step 22.1: Frontend foundation setup
- Step 22.2: Backend-supported accessible KB endpoint + frontend KB visibility cleanup
- Step 22.3: Full KB-aware chat UI
- Step 22.4: Chat session UX
- Step 22.5: Document Upload and Document Explorer UI
- Step 22.6: Demo polish and role-based workspace refinement
- Step 23: Final Demo Packaging and Signoff
- Step 24: Hybrid retrieval + metadata-aware reranking
- Step 25: Suggested Follow-up Questions
- Step 26: Confidence Scoring
- Step 27: Enhanced Sources Panel UX
- Step 28: Impact Analysis MVP
- Step 29.1: Production readiness — System health dashboard (admin-only status endpoint + UI)
- Step 29.2: Admin retrieval diagnostics console (admin-only retrieval test endpoint + UI)
- Step 29.3: Retrieval smoke test utility (`scripts/retrieval_smoke_test.py`)
- Step 30: Streaming chat responses (`POST /query/ask-stream`, SSE, optional UI toggle; non-streaming `/query/ask` unchanged)
- Step 31: Conversation memory summarization (session summary columns + rolling LLM summary + prompt injection)
- Step 32: Agent orchestration layer (config-gated deterministic steps before `RagService`)
- Step 33: Agent trace viewer (diagnostics UI for orchestration steps)
- Step 34: Query quality feedback (user thumbs up/down + optional comment; admin feedback review UI)
- Step 35: Feedback analytics dashboard (admin aggregates + trends on `query_feedback`)
- Step 36: Feedback-driven improvement task queue (admin tasks from negative feedback)
- Step 37: Improvement task action assistant (admin analyze endpoint + UI panel)
- Step 38: Improvement resolution notes (resolved_at / resolved_by / resolution_notes on tasks)
- Step 39: Admin audit trail (`audit_logs` table, service hooks, `GET /audit/logs`, admin UI)
- Step 40: Demo readiness dashboard (`GET /admin/demo-readiness`, admin UI)
- Step 41: Guided demo script (`GET /admin/demo-script`, admin UI, local progress)
- Step 42: Demo data seeder (`scripts/seed_demo_data.py` — idempotent feedback, tasks, audit)
- Step 43: Demo reset utility (`scripts/reset_demo_data.py` — marker-based cleanup only)
- Step 44: Demo command center (`/admin/demo-data/*` APIs + `/admin/demo-command-center` UI)
- Step 45: Demo environment smoke runner (`scripts/demo_smoke_runner.py`)
- Step 45.1: Smoke runner route alignment fix (`scripts/list_routes.py` + backend restart)
- Step 46: Demo evidence pack export (`GET /admin/demo-evidence-pack` + admin UI)
- Step 47: Evidence pack PDF export (`GET /admin/demo-evidence-pack/pdf`)
- Step 48: Admin demo runbook (`GET /admin/demo-runbook` + `/admin/demo-runbook` UI)
- Step 49: Final demo polish — grouped admin sidebar (Core / Diagnostics / Quality / Demo) + page intro consistency
- Step 50: Final demo hardening sprint (startup diagnostics, smoke runner gate on readiness blocked, admin error logging, evidence PDF UX, docs)
- Step 50.1: Safe KB-scoped test data cleanup (`POST /admin/test-data/cleanup` + `scripts/cleanup_test_data.py`)
- Step 50.2: Chat session `summary_message_count` default fix (NOT NULL + server default + explicit INSERT)

## Current important behavior
- JWT auth works
- Swagger BearerAuth works
- RBAC permission guards work
- User management APIs exist
- Knowledge Base CRUD exists
- KB user access management APIs exist
- KB users can be granted/updated/removed/listed via APIs
- KB access levels supported: read, write, admin
- KB access management APIs are protected by knowledge_bases.manage
- Documents are linked to knowledge_base_id
- api_documents now supports document_type, source_domain, product_name
- document_type supports: api, product, hr
- Upload accepts document_type, source_domain, product_name, version
- Upload validates KB access
- Query requires knowledge_base_id
- Retrieval is filtered by knowledge_base_id
- Retrieval source metadata includes document_type and product_name
- API document chunking remains unchanged
- Product documents now use product_section_chunk
- Product chunking uses logical sections from DOCX
- Product chunks preserve section title/context
- HR documents currently use generic_section_chunk
- Parser now returns logical_sections
- Product chunk metadata includes document_type, section_title, product_name
- rag_service/retrieval_service support section_title metadata
- Added document-type-aware prompt mode selection
- API prompts remain API-oriented and stable
- Product prompts are workflow/user-guide oriented
- HR currently uses generic prompt mode
- Product context formatting includes product_name and section_title when available
- Prompt selection was verified with API and Product metadata
- Added GET /api/v1/ingestion/documents
- Added optional document filters:
  - document_type
  - product_name
  - knowledge_base_id
- POST /api/v1/query/ask now supports optional debug=false/true
- When debug=true, response includes diagnostics:
  - retrieval_mode
  - retrieved_chunk_count
  - dominant_document_type
  - dominant_product_name
  - section_coverage_count
  - kb_match_verified
- debug=false or omitted preserves normal response shape
- Added lightweight structured retrieval logs
- Document detail/endpoints response now includes:
  - document_type
  - product_name
  - source_domain
  - document_version
  - knowledge_base_id
  - knowledge_base_name
  - created_at
- Chat sessions store knowledge_base_id
- Cross-KB session continuation is blocked
- Cross-KB user access is denied
- Retrieval currently uses db_keyword_fallback because vectors are not fully populated
- db_keyword_fallback remains active
- Query sources now include:
  - source_domain
  - document_version
  - document_type
  - product_name
  - section_title where available
- section_title may not always appear in query sources while fallback dominates
- Product DOCX upload was verified successfully
- API DOCX upload was verified successfully
- Product KB query returns source metadata correctly
- API KB query still works
- Runtime API/Product queries return 200
- Product/API queries still work
- Product KB debug query verified
- dominant_document_type reports product correctly
- dominant_product_name reports Claims Portal correctly
- kb_match_verified=true confirms KB isolation
- Retrieval remains db_keyword_fallback
- Swagger shows the new document filters
- Swagger/OpenAPI shows debug field
- Step 19.1 (Ollama connectivity stabilization): see **Step 19** below for retries, timeouts, diagnostics, fallback behavior, and known intermittency
- Step 19.2 completed: vector persistence and vector retrieval validation are implemented (see **Step 19** below)
- Product KB vector retrieval path is validated
- API KB vector retrieval may still return vector_kb_filtered_empty depending on source coverage
- Mac Ollama intermittency is treated as operational/network behavior, not backend architecture failure
- `LLM_PROVIDER` supports: `ollama`, `openai`
- `EMBEDDING_PROVIDER` supports: `ollama`, `openai`
- OpenAI generation path implemented
- OpenAI embedding path implemented
- Ollama generation path preserved
- Ollama embedding path preserved
- Provider-aware Qdrant collection routing implemented
- Provider-aware vector dimension resolver implemented
- Current collections:
  - `enterprise_api_docs` (Ollama / 768)
  - `enterprise_api_docs_openai` (OpenAI / 1536)
- OpenAI vector ingestion validated
- OpenAI vector retrieval validated
- OpenAI `vector_success` validated
- Product KB OpenAI retrieval validated
- Diagnostics include:
  - `llm_provider`
  - `embedding_provider`
  - `llm_model`
  - `embedding_model`
  - `vector_collection_name`
  - `configured_collection_embedding_dim`
  - `embedding_dimension_matches_collection`
- Safe fallback behavior preserved
- Ollama fallback behavior preserved during Mac connectivity intermittency
- Backend health verified on 127.0.0.1:8010
- LLM style differences may not show consistently while Ollama generation is intermittent
- Neo4j remains disabled for Phase 1
- No migration added for Step 17.5
- Existing query/chat/upload behavior unchanged
- Ingestion blocker fix applied: api_parameters.mandatory_optional expanded to TEXT
- Ingestion blocker fix applied: api_parameters.param_type expanded to TEXT
- Step 20.2 Phase A implemented:
  - candidate pool expansion
  - local reranking
  - metadata-aware ranking boosts
- Step 20.2 Phase B implemented:
  - hybrid rescue for weak vector retrieval
  - low-confidence vector recovery path
- Step 20.2 Phase C implemented:
  - prompt-context selection from ranked retrieval outputs
  - context deduplication
  - diversity balancing
  - prompt context budget control
- Step 20.2 diagnostics added:
  - `candidate_pool_size`
  - `reranked_result_count`
  - `hybrid_fusion_used`
  - `metadata_boost_applied`
  - `top_combined_score`
  - `rerank_strategy`
  - `vector_confidence_bucket`
  - `fusion_candidate_count`
  - `selected_prompt_chunk_count`
  - `dedup_chunks_removed`
  - `diversity_caps_applied`
  - `final_prompt_context_chars`
- API contracts unchanged
- Provider abstraction unchanged
- RBAC/KB/session isolation unchanged
- Fallback safety preserved
- Remaining weak cases appear mostly related to corpus coverage/content quality, not architecture
- Demo validation harness added
- Stable 12-query demo set created
- OpenAI provider demo path validated successfully
- Ollama degraded/local path validated for safe fallback
- Deterministic insufficient-context fallback implemented
- Insufficient-context message:
  - "I could not find enough information in the selected knowledge base to answer this confidently."
- `llm_status` now supports/uses `fallback_insufficient_context`
- Demo checklist added
- API contracts unchanged
- Provider abstraction unchanged
- RBAC/KB/session isolation unchanged
- Fallback safety preserved
- Mac-hosted Ollama connectivity remains intermittent operationally, but backend handles it safely without hangs/crashes
- Frontend users only see KBs returned by:
  - `GET /api/v1/knowledge-bases/me`
- Frontend never shows unrelated KBs
- Frontend action visibility depends on:
  - role
  - access_level
  - can_query
  - can_upload
  - can_manage
  - can_view_documents
- Backend remains source of truth for access control
- Frontend reflects backend access only
- `DocumentsPage` implemented
- KB-scoped document listing added
- Access-aware document upload added
- Upload form visible only when `selectedKb.can_upload=true`
- Document list visible only when `selectedKb.can_view_documents=true`
- Frontend document filters added:
  - `document_type`
  - `product_name`
  - `knowledge_base_id`
- Upload metadata supported:
  - `knowledge_base_id`
  - `document_type`
  - `source_domain`
  - `product_name`
  - `version`
- Upload result displays ingestion/vector fields when returned
- Document list refreshes after successful upload
- Frontend never allows arbitrary KB ID entry for upload
- Frontend always scopes document listing to selected KB
- Backend hardening: `GET /api/v1/ingestion/documents` now enforces KB access
- Platform admin/superadmin can list documents across KBs
- Regular users can list only explicitly accessible KB documents
- Unauthorized `knowledge_base_id` returns `403`
- Omitting `knowledge_base_id` returns only accessible KB documents
- No-access users see empty list or are blocked from specific KBs
- Critical cross-KB document visibility gap closed
- Step 22.6 completed: frontend demo polish and role-based workspace refinement implemented
- Role-aware workspace refinement implemented
- Sidebar grouped into Workspace and Administration sections
- Top navigation now shows selected KB, provider badge, role badge, and user info
- KB selector now shows domain/access/capability hints
- Chat UX polished with answer cards, copy button, loading state, auto-scroll, and clearer insufficient-context banner
- Diagnostics panel polished and remains restricted to admin/QA visibility
- DocumentsPage polished with metadata/status badges and clearer upload permission messaging
- Dashboard demo cards added
- Future-phase placeholders added for:
  - Recruitment Workspace
  - Analytics
  - Advanced Diagnostics
- Frontend README updated with startup, demo, provider, and troubleshooting instructions
- Validation summary for Step 22.6:
  - Admin walkthrough passed
  - Limited/read-only walkthrough passed
  - Writer/admin KB user walkthrough passed
  - Product/API/insufficient-context chat validation passed
  - Document listing/upload permission validation passed
  - `npm run build` passed
  - QA/tester walkthrough pending (seeded QA/tester users unavailable)
  - HR/basic walkthrough pending (seeded HR/basic users unavailable)
  - Manual screenshots pending for final demo packaging
- Bug fixes discovered and applied during Step 22.6 validation:
  - `GET /api/v1/ingestion/documents` listing permission adjusted so read/query users can view documents when KB access allows
  - Frontend `canViewDocuments` updated to align with backend `can_view_documents` behavior
  - KB access hierarchy fixed:
    - `read` is satisfied by `read`/`write`/`admin`
    - `write` is satisfied by `write`/`admin`
    - `admin` is satisfied by `admin`
- Step 23 completed: demo packaging and operational signoff artifacts prepared
- Seeded demo users:
  - `qa@local` (role: `qa`, KB: Product Documentation, diagnostics visible)
  - `hr@local` (role: `hr_basic`, KB: HR Resume Screening, diagnostics/admin hidden)
- Demo packaging docs created:
  - `docs/demo_runbook.md`
  - `docs/demo_script.md`
  - `docs/startup_checklist.md`
  - `docs/troubleshooting_checklist.md`
  - `docs/known_limitations.md`
  - `docs/demo_queries.md`
  - `docs/environment_freeze.md`
  - `docs/screenshots/*` placeholders
- Step 23 validation completed:
  - backend startup verification passed (`/api/v1/health`)
  - frontend startup verification passed (`http://localhost:5173`)
  - OpenAI provider demo query passed (`llm_provider=openai`)
  - insufficient-context query passed (`llm_status=fallback_insufficient_context`)
  - document upload flow passed
  - QA walkthrough passed
  - HR/basic walkthrough passed
  - `npm run build` passed
- Recommended demo provider mode for stable presentation:
  - `LLM_PROVIDER=openai`
  - `EMBEDDING_PROVIDER=openai`
- Step 24 completed: Hybrid retrieval + metadata-aware reranking
- Summary:
  - Implemented a safe, additive retrieval-quality upgrade for the Agentic Enterprise API RAG Platform.
  - Existing RAG behavior, endpoints, RBAC, KB isolation, provider abstraction, frontend contract, database schema, and Qdrant provider-aware collection naming were preserved.
- What was implemented:
  - Added config-controlled hybrid retrieval kill switches:
    - `ENABLE_HYBRID_RETRIEVAL`
    - `ENABLE_METADATA_RERANKING`
    - `HYBRID_VECTOR_TOP_K`
    - `HYBRID_KEYWORD_TOP_K`
    - `FINAL_CONTEXT_TOP_K`
  - Added deterministic query intent detection for:
    - authentication questions
    - error / failed-response questions
    - async / callback questions
    - API lookup questions
    - parameter lookup questions
    - overview / purpose questions
  - Added hybrid retrieval using:
    - existing vector retrieval
    - keyword candidate retrieval
    - metadata-aware reranking
    - chunk-type boosting
    - intent-specific boosting
  - Added metadata-aware reranking to improve retrieval for:
    - authentication chunks
    - failed response chunks
    - async service pattern metadata
    - API metadata chunks
    - request / response parameter chunks
    - document overview chunks
  - Added async aggregation support for questions like:
    - "Which APIs are asynchronous?"
  - Added error lookup support for questions like:
    - "What happens if TimeSlotCategory is invalid?"
  - Added retrieval diagnostics:
    - `retrieval_mode`
    - `detected_intents`
    - `vector_candidate_count`
    - `keyword_candidate_count`
    - `final_context_count`
    - `top_chunk_types`
    - `applied_boosts`
  - Added retrieval logging summary:
    - question
    - kb_id
    - retrieval_mode
    - detected_intents
    - candidate count
    - final context count
    - top chunk types
    - top API references / service names when available
  - Added safe fallback:
    - if hybrid retrieval or reranking fails, system falls back to existing vector-only retrieval.
- Files changed:
  - `app/core/config.py`
  - `app/services/query_intent_service.py`
  - `app/services/retrieval_service.py`
  - `app/services/rag_service.py`
  - `tests/test_hybrid_intent_rerank.py`
- Validation completed:
  - Backend health verified:
    - `GET http://127.0.0.1:8010/api/v1/health` returned `200`
  - BB DOCX ingestion remained successful:
    - `chunk_count: 164`
    - `api_count: 18`
    - vector collection: `enterprise_api_docs_openai`
    - embedding dimension: `1536`
  - Passed query validation:
    - "What authentication method is used by the APIs?"
    - "What happens if TimeSlotCategory is invalid?"
    - "Which APIs are asynchronous?"
    - "Which API is used to check order status?"
    - "Which API is used to revise an order?"
    - "What is the purpose of the BB Order Service document?"
    - "What is the purpose of the getAppointment API?"
- Current retrieval status:
  - API lookup retrieval: working
  - API purpose retrieval: working
  - document overview retrieval: working
  - authentication retrieval: working
  - failed-response/error retrieval: working
  - async aggregation retrieval: working
  - existing vector-only fallback preserved
- Operational notes:
  - OpenAI demo path remains stable.
  - Ollama support remains preserved for local/final architecture.
  - `pytest` is not installed in the current environment, but tests were added and can be run after installing pytest:
    - `pip install pytest`
    - `pytest tests/test_hybrid_intent_rerank.py -v`
    - `pytest tests/test_docx_ingestion_quality.py -v`

- Step 25 completed: Suggested Follow-up Questions
- Summary:
  - Added deterministic suggested follow-up questions after successful RAG answers.
  - Suggestions are grounded in retrieved context metadata/chunk types.
  - Frontend displays suggestions as clickable chips.
- Backend files changed:
  - `app/core/config.py`
  - `app/services/suggested_question_service.py`
  - `app/api/v1/endpoints/query.py`
  - `app/services/rag_service.py`
- Frontend files changed:
  - `frontend/src/types/query.ts`
  - `frontend/src/pages/ChatPage.tsx`
- Config flags added:
  - `ENABLE_SUGGESTED_QUESTIONS=True`
  - `SUGGESTED_QUESTION_COUNT=4`
- Backend response addition:
  - `suggested_questions: list[str] = []`
- Diagnostics added when `debug=true`:
  - `suggested_question_count`
  - `suggested_question_generation_mode`
  - `suggested_question_status`
- Behavior:
  - Suggestions generated only for successful grounded answers.
  - Suggestions skipped for insufficient-context fallback.
  - Suggestions skipped when no retrieved context exists.
  - Suggestion generation is deterministic and non-blocking.
  - Suggestion service never breaks the main answer flow.
- Frontend behavior:
  - Assistant answers show "Suggested follow-ups" chips.
  - Clicking a chip submits it as the next user question.
  - Current KB and `session_id` are preserved.
  - Chips hidden during loading and fallback answers.
- Validation results:
  - Backend compile successful.
  - Frontend `npm run build` successful.
  - Login with `qa@local` succeeded.
  - Query tested: "What authentication method is used by the APIs?"
  - API-oriented suggestions returned.
  - Chip click flow validated with same `session_id`.
  - Fallback query returned `suggested_questions=[]`.
  - No request failures observed.
- Known limitation:
  - Some API suggestions may show "Service: Unknown Service" when retrieved metadata does not include `service_name`.
  - Current generation is deterministic/rule-based only; LLM-based suggestions are intentionally not enabled yet.

- Step 26 completed: Confidence Scoring
- Summary:
  - Added deterministic retrieval-grounded confidence scoring for RAG answers.
  - Confidence is derived from retrieval quality signals already produced by the system.
  - Frontend displays confidence as a compact assistant-answer badge.
- Backend files changed:
  - `app/core/config.py`
  - `app/services/confidence_service.py`
  - `app/api/v1/endpoints/query.py`
  - `app/services/rag_service.py`
- Frontend files changed:
  - `frontend/src/types/query.ts`
  - `frontend/src/pages/ChatPage.tsx`
- Config flags:
  - `ENABLE_CONFIDENCE_SCORING=True`
  - `CONFIDENCE_HIGH_THRESHOLD=0.75`
  - `CONFIDENCE_MEDIUM_THRESHOLD=0.45`
- Backend response addition:
  - `confidence: dict | None`
  - shape: `score`, `label`, `reasons`
- Debug diagnostics:
  - `confidence_score`
  - `confidence_label`
  - `confidence_reasons`
  - `confidence_status`
- Behavior:
  - deterministic retrieval-grounded scoring only
  - no LLM confidence scoring
  - fallback answers return `score=0.0` and `label=low`
  - scoring is non-blocking and safe
- Frontend behavior:
  - confidence badge shown on assistant answers
  - badge displays High/Medium/Low confidence and percentage
  - tooltip/title exposes reasons
- Validation:
  - backend compile passed
  - frontend `npm run build` passed
  - QA login passed
  - successful query returned medium confidence `0.73`
  - fallback query returned low confidence `0.0`
  - suggested follow-up chips still work
- Known limitation:
  - current confidence is retrieval-quality confidence, not factual truth guarantee
  - score tuning may be refined after more evaluation queries

- Step 27 completed: Enhanced Sources Panel UX
- Summary:
  - Enhanced Sources panel with enterprise-grade grounding/traceability UX.
  - Frontend-first additive implementation.
  - No backend endpoint/schema changes.
- Frontend files changed:
  - `frontend/src/pages/ChatPage.tsx`
- Behavior added:
  - Sources grouped by document/source.
  - Source cards collapsed by default and expandable.
  - Chunk-type badges displayed.
  - API/service metadata badges displayed where available.
  - Frontend-derived relevance badges displayed.
  - Deterministic "why this source matched" helper text shown.
  - Fallback answers suppress misleading source cards even if backend returns sources.
- Validation:
  - `npm run build` passed.
  - Successful query still shows answer, confidence badge, suggested chips, and grouped sources.
  - Fallback query shows fallback answer and low confidence, but no suggested chips and no misleading sources.
  - No backend changes required.
  - No endpoint contracts changed.
- Known limitations:
  - Some sources may still lack `service_name` metadata, limiting badge richness.
  - Source preview is currently derived from available metadata because raw chunk text is not always included in the source payload.

- Step 28 completed: Impact Analysis MVP
- Summary:
  - Added deterministic Impact Analysis MVP.
  - Backend extracts lightweight API/service/product relationships from retrieved metadata.
  - Frontend displays an Impact Analysis panel for successful grounded answers.
  - No Neo4j/graph database enabled.
  - No architecture redesign.
- Backend files changed:
  - `app/core/config.py`
  - `app/services/impact_analysis_service.py`
  - `app/api/v1/endpoints/query.py`
  - `app/services/rag_service.py`
- Frontend files changed:
  - `frontend/src/types/query.ts`
  - `frontend/src/pages/ChatPage.tsx`
- Config flag:
  - `ENABLE_IMPACT_ANALYSIS=True`
- Backend response addition:
  - `impact_analysis: dict | None`
  - Shape:
    - `primary_entities`
    - `related_entities`
    - `potential_impacts`
    - `relationship_summary`
    - `impact_confidence`
- Debug diagnostics:
  - `impact_analysis_status`
  - `impact_primary_entity_count`
  - `impact_related_entity_count`
  - `impact_relationship_count`
  - `impact_confidence`
- Behavior:
  - Impact analysis generated only for successful grounded answers.
  - Fallback answers return `impact_analysis=null`.
  - Deterministic metadata-based relationship extraction only.
  - No LLM-generated dependency graph.
  - No Neo4j or graph database usage.
  - Safe non-blocking behavior.
- Frontend behavior:
  - Impact Analysis panel shown under assistant answers when `impact_analysis` exists.
  - Shows impact confidence, primary entities, related entities, potential impacts, and relationship details.
  - Hidden for fallback answers.
- Validation:
  - backend compile passed.
  - frontend `npm run build` passed.
  - QA login passed.
  - Query tested: Which API is used to get appointment slots?
  - `impact_analysis` returned medium confidence with primary/related entities and relationship summary.
  - confidence badge, suggested chips, and enhanced sources panel still work.
  - fallback query returned `impact_analysis=null` and preserved low confidence/no chips/source suppression.
  - Frontend Vite used localhost:5176 due busy lower ports; this is operational only.
- Known limitations:
  - MVP is retrieval-assisted metadata relationship analysis, not full dependency graph.
  - Impact confidence is based on relationship evidence, not guaranteed real-world dependency.
  - Richness depends on extracted metadata quality such as `service_name`, `api_reference_id`, `service_group`, and `chunk_type`.

- Step 29.1 completed: System health dashboard (Windows production-readiness)
- Summary:
  - Added admin/super-admin-only platform status API for operations visibility (PostgreSQL, Qdrant, providers, vector collection, retrieval feature flags).
  - Added frontend **System Health** page under Administration for `super_admin` and `admin` roles only.
  - No architecture redesign; additive RBAC and routing only.
  - CORS extended for common local Vite ports (5175–5176) alongside existing 5173–5174.
- Backend files changed:
  - `app/api/deps.py` — `require_admin_or_super_admin` dependency (roles `super_admin`, `admin`).
  - `app/api/v1/endpoints/health.py` — `GET /api/v1/status` aggregated platform status (JWT required).
  - `app/main.py` — CORS origins for localhost `5175`/`5176`; root payload notes `/api/v1/status`.
- Frontend files changed:
  - `frontend/src/api/healthApi.ts`
  - `frontend/src/types/health.ts`
  - `frontend/src/auth/roleAccess.ts` — `canViewSystemHealth`
  - `frontend/src/pages/HealthStatusPage.tsx`
  - `frontend/src/App.tsx` — route `/admin/health`
  - `frontend/src/components/Sidebar.tsx` — link **System Health**
- Endpoint:
  - `GET /api/v1/status` — Bearer auth; **403** if user is not `super_admin` or `admin`.
- Response shape (summary):
  - `overall_status`: `healthy` | `degraded` | `unhealthy`
  - `backend`, `database`, `qdrant`, `providers`, `feature_flags` (`ENABLE_HYBRID_RETRIEVAL`, `ENABLE_METADATA_RERANKING`, etc.), `issues`
- Frontend behavior:
  - **System Health** nav item only for `super_admin` / `admin`.
  - Page shows backend, PostgreSQL, Qdrant, LLM/embedding providers, active vector collection, hybrid retrieval and metadata reranking on/off, and related flags.
  - Clear error state if the status API fails or returns 403.
- Validation:
  - `python -m compileall app` expected to pass; `npm run build` expected to pass.
  - Super admin can open **System Health**; non-admin users (e.g. QA) receive 403 on `/api/v1/status` and are gated to not-authorized on the page.
- Known limitations:
  - Status is point-in-time; does not replace full APM or external monitoring.
  - Qdrant/DB errors are surfaced as messages; degraded if vector dimension mismatch is detected.

- Step 29.2 completed: Admin retrieval diagnostics console (retrieval quality testing per KB)
- Objective:
  - Provide an **admin/super-admin-only** console to run **retrieval-only** tests per knowledge base (no LLM answer), reusing `retrieval_service.retrieve`, preserving hybrid retrieval and metadata reranking behavior via existing service flags.
  - Enforce **KB access** for non-platform admins (aligned with `/knowledge-bases/me` patterns).
- Backend files changed:
  - `app/api/v1/endpoints/diagnostics.py` — `POST /diagnostics/retrieval-test`; aggregates dominant types/products/sections; builds ranked chunk previews; merges vector diagnostics with retrieval mode notice.
  - `app/api/v1/router.py` — registers diagnostics router under `/api/v1`.
- Frontend files changed:
  - `frontend/src/types/diagnostics.ts`
  - `frontend/src/api/diagnosticsApi.ts`
  - `frontend/src/pages/RetrievalDiagnosticsPage.tsx`
  - `frontend/src/App.tsx` — route `/admin/retrieval-diagnostics` gated like System Health (`canViewSystemHealth`)
  - `frontend/src/components/Sidebar.tsx` — link **Retrieval Diagnostics**
- Endpoint added:
  - `POST /api/v1/diagnostics/retrieval-test` — Bearer auth; body `{ knowledge_base_id, question, top_k }`; **403** if user is not `super_admin` or `admin`; **403** if KB read access denied; **400** if KB has no documents (cannot resolve project); returns retrieval summary, ranked chunks, and diagnostics object (no generated answer field).
- Validation results:
  - `python -m compileall app` passed.
  - `npm run build` passed.
  - Frontend page and API restricted to **super_admin** / **admin** (same gate as Step 29.1 health dashboard); QA/user roles should see **403** / not-authorized on navigation.
  - Known-good KB questions should return ranked chunks when vectors match; empty retrieval returns zero chunks and UI empty copy: “No matching chunks found for this question.”
- Known limitations:
  - Diagnostics console does not substitute production observability or automated retrieval evaluation suites.

- Step 29.3 completed: Retrieval smoke test suite (CLI diagnostics against predefined questions)
- Objective:
  - Provide an **additive** backend utility that validates retrieval via existing **`POST /api/v1/diagnostics/retrieval-test`** without changing API contracts, retrieval behavior, or adding LLM calls.
- Backend files changed:
  - `scripts/retrieval_smoke_test.py` — login or `SMOKE_JWT`; lists KBs from `/knowledge-bases/me`; runs domain-specific question banks (`api` / `product` / `hr`); prints PASS/WARN/FAIL per question and per KB; exit **1** on auth/list errors, HTTP failures, or **no chunk hits for any question** on a KB.
  - `README.md` — how to run the script.
- Env vars:
  - `API_BASE_URL` (default `http://127.0.0.1:8010/api/v1`), `SMOKE_EMAIL`, `SMOKE_PASSWORD`, optional `SMOKE_JWT`, `SMOKE_TOP_K` (default `6`).
- Pass criteria:
  - Response **200** for each call; **at least one question per KB** with `retrieved_chunk_count > 0`; zero chunks on an individual question is **WARN** only.
- How to run:
  - `python scripts/retrieval_smoke_test.py`
- Validation results:
  - `python -m compileall app scripts` expected to pass.
  - Script is standalone (uses `httpx`); does not alter application runtime behavior.

- Step 30 completed: Streaming chat responses (additive SSE + UI)
- Objective:
  - Optional **token-by-token** assistant output via **Server-Sent Events** while preserving **`POST /query/ask`** behavior, RBAC/KB isolation, retrieval, suggested questions, confidence, impact analysis, insufficient-context fallback, and chat persistence.
- Backend files changed:
  - `app/api/v1/endpoints/query.py` — **`POST /query/ask-stream`** (`text/event-stream`), same `AskRequest` as `/query/ask`; validates KB access then streams SSE events: `start`, `token`, `sources`, `diagnostics` (when `debug`), `done`, `error`.
  - `app/services/rag_service.py` — `answer_question_stream` mirrors `answer_question` branches; **`_persist_user_message`** before generation, **`_persist_assistant_message`** after completion; **`_persist_messages`** unchanged for `/query/ask` (delegates to user+assistant inserts). OpenAI/Ollama **native streaming** when available; otherwise **simulated** chunked streaming from the same final answer as non-stream path.
  - `app/services/openai_client.py` — `generate_stream` (chat completions `stream: true`).
  - `app/services/ollama_client.py` — `generate_stream` (`/api/generate` with `stream: true`).
- Frontend files changed:
  - `frontend/src/api/client.ts` — exports **`apiBaseUrl`** for fetch/SSE.
  - `frontend/src/api/queryApi.ts` — **`askQuestionStream`** parses SSE and returns the **`done`** payload (`QueryResponse`).
  - `frontend/src/pages/ChatPage.tsx` — **“Streaming response”** checkbox (default **on**, persisted in `localStorage`); incremental assistant text; **`sources`** / diagnostics / follow-ups after **`done`**; on stream failure, notice + fallback to **`askQuestion`**.
- Endpoint added:
  - **`POST /api/v1/query/ask-stream`** — same auth and body as **`POST /api/v1/query/ask`**.
- Validation results:
  - `python -m compileall app` passed.
  - `npm run build` passed.
  - Non-streaming **`/query/ask`** unchanged in contract and behavior for clients that do not use streaming.
- Known limitations:
  - SSE requires browser **`fetch` ReadableStream** support; cross-origin setups must allow CORS for streamed responses.

- Step 31 completed: Conversation memory summarization (session-level rolling summary)
- Objective:
  - Add **optional** rolling conversation summaries stored on **`chat_sessions`** so long chats stay coherent without sending full transcript each turn; inject summary **only as secondary context** alongside KB retrieval (does not replace retrieved chunks).
- Backend files changed:
  - `alembic/versions/b8f3a1c9e2d0_add_chat_session_summary_columns.py` — nullable **`summary_text`**, **`summary_updated_at`**, **`summary_message_count`** (default 0).
  - `app/models/chat.py` — ORM fields aligned with migration.
  - `app/core/config.py` — **`ENABLE_CONVERSATION_SUMMARY`**, **`SUMMARY_TRIGGER_MESSAGE_COUNT`** (default 8), **`SUMMARY_MAX_MESSAGES`** (default 20).
  - `app/services/conversation_summary_service.py` — after every **N** assistant messages in a session, merges prior summary + recent transcript (capped) via configured LLM; failures are logged only (chat continues).
  - `app/prompts/rag_answer_prompt.py` — optional **`session_summary`** prefix on API/product/hr prompts.
  - `app/services/rag_service.py` — loads session summary when **`knowledge_base_id`** matches session row; **`conversation_summary_*`** diagnostics when **`debug=true`**; **`maybe_refresh_summary`** after each persist (`/query/ask` and `/query/ask-stream`).
  - `.env.example` — documented summary toggles.
- Frontend files changed:
  - `frontend/src/pages/ChatPage.tsx` — compact **Session memory** panel under Diagnostics (QA/admin diagnostics visibility unchanged).
- Diagnostics (`debug=true`):
  - **`conversation_summary_used`**, **`conversation_summary_message_count`**, **`conversation_summary_updated_at`**.
- Validation results:
  - `python -m compileall app` expected to pass; apply migration with **`alembic upgrade head`** on target DB.
  - **`POST /query/ask`** and **`POST /query/ask-stream`** contracts unchanged; insufficient-context and RBAC/KB isolation preserved.

- Step 32 completed: Agent orchestration layer (optional `/query/ask` pipeline)
- Objective:
  - Add a **config-gated**, **deterministic** orchestration path (no LangGraph, no extra LLM agents) that records explicit steps while reusing **`retrieval_service`** and **`RagService.answer_question`**.
- Backend files changed:
  - `app/core/config.py` — **`ENABLE_AGENT_ORCHESTRATION`** (default **`False`**).
  - `app/agents/orchestrator.py` — **`AgentOrchestrator.run_query_ask`**: steps **`classify_intent`** → **`plan_retrieval`** (intent → effective **`top_k`** hints only) → **`retrieve_context`** → **`validate_context`** (chunk count, dominant document type, **`insufficient_recommended`**) → **`generate_answer`** / **`package_response`** (delegates to **`rag_service.answer_question`** with **`prefetched_retrieval`** to avoid double retrieval).
  - `app/agents/__init__.py` — package marker.
  - `app/services/rag_service.py` — optional **`prefetched_retrieval`** on **`answer_question`**; when unset, behavior matches pre–Step 32.
  - `app/api/v1/endpoints/query.py` — when orchestration enabled, **`POST /query/ask`** uses orchestrator; **`POST /query/ask-stream`** unchanged (still **`answer_question_stream`**).
  - `.env.example` — **`ENABLE_AGENT_ORCHESTRATION`**.
- Deterministic intents (diagnostics / planning only): **`api_lookup`**, **`authentication`**, **`error_handling`**, **`product_feature`**, **`product_workflow`**, **`hr_screening`**, **`general`**.
- Diagnostics (`debug=true` when orchestration on): **`agent_orchestration_enabled`**, **`agent_steps`** (array of `{ step, status, details }`).
- Validation results:
  - `python -m compileall app` expected to pass.
  - With flag **`False`**, **`/query/ask`** matches legacy flow; with **`True`**, same **`QueryResponse`** shape and streaming unaffected.

- Step 33 completed: Agent trace viewer (frontend diagnostics UI)
- Objective:
  - Surface **`agent_orchestration_enabled`** / **`agent_steps`** from **`debug`** diagnostics in the chat sidebar without changing **`QueryResponse`** or streaming contracts.
- Backend:
  - Confirmed **`agent_orchestration_enabled`** and **`agent_steps`** are attached **only when `debug=true`** on the orchestrator path (`app/agents/orchestrator.py` comment clarified).
- Frontend files changed:
  - `frontend/src/pages/ChatPage.tsx` — **Agent trace** panel next to session memory under **Diagnostics** (same **`canViewDiagnostics`** gate); summary row (**detected intent**, **effective top K**, **chunk count**, **insufficient recommendation**) plus per-step readable labels and collapsible **Raw details** JSON; empty copy when trace data is absent.
- Validation results:
  - **`npm run build`** passed.

- Step 34 completed: Query quality feedback (answer ratings + admin review)
- Objective:
  - Capture **per-answer** thumbs up/down (optional comment on thumbs down) tied to **KB**, **session**, and optional **`chat_messages.id`**; **admin/super_admin** can list feedback for quality review without changing **`QueryResponse`** or **`/query/ask`** / **`/query/ask-stream`** contracts.
- Backend files changed:
  - `alembic/versions/d4e7b2a91f01_add_query_feedback_table.py` — table **`query_feedback`** (`user_id`, nullable **`session_id`** / **`message_id`**, **`knowledge_base_id`**, **`question_text`**, **`answer_text`**, **`rating`** `thumbs_up`/`thumbs_down`, nullable **`comment`**, **`created_at`**).
  - `app/models/query_feedback.py` — **`QueryFeedback`** ORM model.
  - `app/db/base.py` — model import for Alembic metadata.
  - `app/api/v1/endpoints/feedback.py` — **`POST /feedback/query`** (`query.ask`); validates KB access via **`check_knowledge_base_access`**; when **`session_id`** / **`message_id`** present, verifies ownership via **`chat_sessions.user_id`** and message/session KB alignment. **`GET /feedback/query`** (**`require_admin_or_super_admin`**); optional filters **`knowledge_base_id`**, **`rating`**, **`from_date`**, **`to_date`**; returns **`items`** with submitter and KB names.
  - `app/api/v1/router.py` — mounts feedback router under **`/feedback`**.
  - `app/api/v1/endpoints/query.py` — **`GET /query/sessions/{id}/messages`** includes **`id`** on each message (additive) so the UI can send **`message_id`** when reloading persisted chats.
- Frontend files changed:
  - `frontend/src/api/feedbackApi.ts` — submit + list clients.
  - `frontend/src/types/query.ts` — optional **`id`** on **`ChatMessage`** (session messages).
  - `frontend/src/pages/ChatPage.tsx` — thumbs **Helpful** / **Not helpful**, optional comment block after thumbs down, **`Feedback submitted.`** confirmation strip.
  - `frontend/src/pages/QueryFeedbackPage.tsx` — admin table + KB/rating filters (**`canViewSystemHealth`** gate, same as System Health).
  - `frontend/src/App.tsx` — **`/admin/query-feedback`** route.
  - `frontend/src/components/Sidebar.tsx` — **Query Feedback** link for admins.
- Validation results:
  - **`alembic upgrade head`** passes (PostgreSQL).
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 35 completed: Feedback analytics dashboard (admin-only aggregates)
- Objective:
  - Let **admin/super_admin** view **totals**, **thumbs mix**, **per-KB breakdown**, and **recent negative** rows over **`query_feedback`**, with optional **KB** and **date range** filters; additive only — **`GET /feedback/query`** unchanged, **no `QueryResponse`** changes.
- Backend files changed:
  - `app/api/v1/endpoints/feedback.py` — **`GET /feedback/analytics`** (**`require_admin_or_super_admin`**); optional **`knowledge_base_id`**, **`from_date`**, **`to_date`**; returns **`total_feedback`**, **`thumbs_up_count`**, **`thumbs_down_count`**, **`thumbs_up_rate`**, **`by_knowledge_base`**, **`recent_negative_feedback`** (latest 25 thumbs-down in range).
- Frontend files changed:
  - `frontend/src/api/feedbackApi.ts` — **`getFeedbackAnalytics`**.
  - `frontend/src/pages/FeedbackAnalyticsPage.tsx` — **`/admin/feedback-analytics`** summary cards + tables (**`canViewSystemHealth`** gate).
  - `frontend/src/App.tsx` — route registration.
  - `frontend/src/components/Sidebar.tsx` — **Feedback Analytics** link.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 36 completed: Feedback-driven improvement task queue
- Objective:
  - Let **admin/super_admin** turn **thumbs-down** **`query_feedback`** rows into tracked **improvement tasks** (optional link via **`feedback_id`**), list/filter/update **status** and **priority**, without changing existing **feedback** APIs or **`QueryResponse`**.
- Backend files changed:
  - `alembic/versions/a5c9e2f0b8d1_add_improvement_tasks_table.py` — **`improvement_tasks`** (`feedback_id` nullable FK → **`query_feedback`**, **`knowledge_base_id`**, **`title`**, **`description`**, **`status`**, **`priority`**, **`assigned_to`** nullable → **`users`**, **`created_by`**, **`created_at`**, **`updated_at`**).
  - `app/models/improvement_task.py` — **`ImprovementTask`** ORM model.
  - `app/db/base.py` — model import for Alembic metadata.
  - `app/api/v1/endpoints/improvements.py` — **`POST /improvements/tasks`**, **`GET /improvements/tasks`** (optional **`status`**, **`priority`** query params), **`PATCH /improvements/tasks/{task_id}`**; all **`require_admin_or_super_admin`**. **`POST`** with **`feedback_id`** loads thumbs-down feedback and **prefills** title/description; **`assigned_to`** validated against active users.
  - `app/api/v1/router.py` — mount **`/improvements`** router.
  - `app/api/v1/endpoints/feedback.py` — **`recent_negative_feedback`** entries now include **`knowledge_base_id`** (additive) for client context.
- Frontend files changed:
  - `frontend/src/api/improvementsApi.ts` — create / list / patch client.
  - `frontend/src/pages/ImprovementTasksPage.tsx` — **`/admin/improvement-tasks`**: filters, inline **status** / **priority** updates, **linked feedback** details, **`?feedback_id=`** banner to create from analytics, optional manual create form.
  - `frontend/src/pages/FeedbackAnalyticsPage.tsx` — **Create task** on each recent negative row (navigates with **`feedback_id`**).
  - `frontend/src/api/feedbackApi.ts` — **`RecentNegativeFeedbackItem.knowledge_base_id`**.
  - `frontend/src/App.tsx` — route + gate (**`canViewSystemHealth`**).
  - `frontend/src/components/Sidebar.tsx` — **Improvement Tasks** link.
- Validation results:
  - **`alembic upgrade head`** passes (PostgreSQL).
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 37 completed: Improvement task action assistant (deterministic triage + optional retrieval test)
- Objective:
  - Help **admin/super_admin** interpret an **improvement task** (especially with linked thumbs-down feedback) with a **recommended_action**, **reasoning_summary**, **suggested_kb_update**, **suggested_test_questions**, and optional **retrieval_test** payload mirroring diagnostics retrieval (no RAG answer generation); additive only — existing **improvements** CRUD and **feedback** APIs unchanged; **`QueryResponse`** unchanged.
- Backend files changed:
  - `app/core/config.py` — **`ENABLE_IMPROVEMENT_LLM_ANALYSIS`** (default **`False`**); when **`True`** and **`OPENAI_API_KEY`** set, appends a short **OpenAI** refinement to **`reasoning_summary`** (failures fall back to heuristic text only).
  - `app/services/improvement_task_analysis.py` — loads task + linked **`query_feedback`** (question, answer, comment, rating, KB id); deterministic rules for **`update_kb_content`**, **`improve_prompt`**, **`improve_retrieval`**, **`mark_as_unclear`**; reuses **`diagnostics`** retrieval helpers + **`retrieval_service.retrieve`** for internal test (same path as **`POST /diagnostics/retrieval-test`** without LLM answer).
  - `app/api/v1/endpoints/improvements.py` — **`POST /improvements/tasks/{task_id}/analyze`** body **`{ "include_retrieval_test": true }`**; **`require_admin_or_super_admin`**.
  - `.env.example` — **`ENABLE_IMPROVEMENT_LLM_ANALYSIS`** documented.
- Frontend files changed:
  - `frontend/src/api/improvementsApi.ts` — **`analyzeTask`**.
  - `frontend/src/pages/ImprovementTasksPage.tsx` — per-row **Analyze**, checkbox for retrieval test, read-only analysis panel (does not PATCH the task).
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 38 completed: Improvement resolution notes (audit trail on resolve)
- Objective:
  - Let **admin/super_admin** store **`resolution_notes`** on **`improvement_tasks`**, and when **status** becomes **`resolved`**, stamp **`resolved_at`** (preserved if already set via **`COALESCE`**) and **`resolved_by`** as the current user; when leaving **`resolved`**, clear **`resolved_at`** / **`resolved_by`**; **`GET /improvements/tasks`** returns notes and resolver summary.
- Backend files changed:
  - `alembic/versions/b3d8f1a92c42_add_improvement_task_resolution_columns.py` — nullable **`resolution_notes`**, **`resolved_at`**, **`resolved_by`** (**`users`** FK).
  - `app/models/improvement_task.py` — ORM fields aligned.
  - `app/api/v1/endpoints/improvements.py` — **`PATCH`** accepts **`resolution_notes`**; list/detail **`SELECT`** joins resolver user; resolution fields on **`_row_to_item`**.
- Frontend files changed:
  - `frontend/src/api/improvementsApi.ts` — task item + **`patchTask`** **`resolution_notes`**.
  - `frontend/src/pages/ImprovementTasksPage.tsx` — per-task **Resolution** column (textarea, **Save notes**, **Resolved** meta).
- Validation results:
  - **`alembic upgrade head`** passes (PostgreSQL).
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 39 completed: Admin audit trail (governance log + admin list API + UI)
- Objective:
  - Persist important **admin** actions in **`audit_logs`** for governance and demos; **additive** only — no **`QueryResponse`**, RBAC, or KB isolation changes; **`record_audit_log`** helper used from existing flows.
- Backend files changed:
  - `alembic/versions/c2e8a1b304d9_add_audit_logs_table.py` — **`audit_logs`** (`actor_user_id`, `action`, `entity_type`, optional **`entity_id`**, **`knowledge_base_id`**, **`metadata_json`**, **`created_at`**); index on **`created_at`**.
  - `app/models/audit_log.py` — ORM model.
  - `app/db/base.py` — import **`AuditLog`** for metadata.
  - `app/services/audit_log_service.py` — **`record_audit_log(db, actor_user_id, action, entity_type, ...)`** (insert in own session; **`metadata_json`** JSON-serialized).
  - `app/api/v1/endpoints/audit.py` — **`GET /audit/logs`** (**`require_admin_or_super_admin`**); filters **`action`**, **`entity_type`**, **`knowledge_base_id`**, **`actor_user_id`**, **`from_date`**, **`to_date`**; returns **`items`** with **`actor_summary`**, **`actor_email`**, **`knowledge_base_name`**, **`metadata_preview`**.
  - `app/api/v1/router.py` — mount **`/audit`** router.
  - `app/api/v1/endpoints/improvements.py` — audit on task **create**, **update** / **resolved** (from **`PATCH`**), **analyze**.
  - `app/api/v1/endpoints/feedback.py` — audit on **`query_feedback.submitted`** after successful insert.
  - `app/api/v1/endpoints/ingestion.py` — audit **`document.uploaded`** when ingest returns **`document_id`** (no document delete audit; no delete API in scope).
- Frontend files changed:
  - `frontend/src/api/auditApi.ts` — **`listLogs`**.
  - `frontend/src/pages/AuditLogsPage.tsx` — **`/admin/audit-logs`**: table + filters (**action**, **entity type**, **KB**).
  - `frontend/src/App.tsx` — route + **`canViewSystemHealth`** gate (aligned with **`require_admin_or_super_admin`**).
  - `frontend/src/components/Sidebar.tsx` — **Audit Logs** link.
- Endpoint:
  - **`GET /api/v1/audit/logs`** — Bearer auth; **403** unless **`super_admin`** or **`admin`**.
- Validation results:
  - **`alembic upgrade head`** passes (PostgreSQL).
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 40 completed: Demo readiness dashboard (single admin snapshot for demo go/no-go)
- Objective:
  - Expose **`GET /api/v1/admin/demo-readiness`** (**`require_admin_or_super_admin`**) returning **`overall_status`** (**`ready` \| `warning` \| `blocked`**), **`checks`** (pass/warn/fail + message), **`summary`** counts, and **`recommendations`**; additive only — no **`QueryResponse`**, RBAC, or KB isolation changes.
- Backend files changed:
  - `app/api/v1/endpoints/admin_demo_readiness.py` — reuses **`health._build_platform_status()`** for DB/Qdrant signals; SQL counts for active KBs, **`api_documents`**, **`query_feedback`**, open improvement tasks, high-priority open tasks, **`audit_logs`** (last 7 days); provider key check when OpenAI selected; filesystem check for **`scripts/retrieval_smoke_test.py`**.
  - `app/api/v1/router.py` — mount admin router prefix **`/admin`**.
- Frontend files changed:
  - `frontend/src/api/demoReadinessApi.ts` — **`getDemoReadiness`**.
  - `frontend/src/pages/DemoReadinessPage.tsx` — **`/admin/demo-readiness`**: overall pill, summary cards, checks list, recommendations.
  - `frontend/src/App.tsx` — route + **`canViewSystemHealth`** gate.
  - `frontend/src/components/Sidebar.tsx` — **Demo Readiness** link.
- Endpoint:
  - **`GET /api/v1/admin/demo-readiness`** — Bearer auth; **403** unless **`super_admin`** or **`admin`**.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 41 completed: Demo script and guided scenario mode (admin presenter flow)
- Objective:
  - Provide **`GET /api/v1/admin/demo-script`** (**`require_admin_or_super_admin`**) returning a static ordered **`sections`** narrative (routes, objectives, talking points, outcomes) plus embedded live **`demo_readiness`** from **`build_demo_readiness_payload`**. Frontend **`/admin/demo-script`** stores per-section completion in **`localStorage`** only; additive only — no **`QueryResponse`**, RBAC, or KB isolation changes.
- Backend files changed:
  - `app/api/v1/endpoints/admin_demo_readiness.py` — extract **`build_demo_readiness_payload(db)`** for reuse by **`/admin/demo-readiness`** and **`/admin/demo-script`**.
  - `app/api/v1/endpoints/admin_demo_script.py` — **`GET /demo-script`**; sections include Demo Readiness, System Health, KB selection, documents, chat/sources, streaming, memory, retrieval diagnostics, agent trace, feedback submit/analytics, improvement tasks, audit logs; each section has stable **`id`** for client progress keys.
  - `app/api/v1/router.py` — second **`/admin`** router mount for demo script.
- Frontend files changed:
  - `frontend/src/api/demoScriptApi.ts` — **`getDemoScript`**.
  - `frontend/src/pages/DemoScriptPage.tsx` — ordered cards, internal **`Link`**, checkboxes + **Reset demo progress** (`aerag_demo_script_progress_v1`), collapsible live readiness summary.
  - `frontend/src/App.tsx` — route + **`canViewSystemHealth`** gate.
  - `frontend/src/components/Sidebar.tsx` — **Demo Script** link.
- Endpoint:
  - **`GET /api/v1/admin/demo-script`** — Bearer auth; **403** unless **`super_admin`** or **`admin`**.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.

- Step 42 completed: Demo data seeder (idempotent presentation data)
- Objective:
  - Add **`scripts/seed_demo_data.py`** using ORM models and **`record_audit_log`** to insert one thumbs-up, two thumbs-down **`query_feedback`** rows, one open **high**-priority **`improvement_tasks`** row (linked to first negative feedback), one **resolved** task with **resolution** fields (linked to second negative feedback), and matching **audit** rows — **never deletes**; idempotent via fixed **`[DEMO_SEED_42]`** question/title keys per user+KB.
- Backend / script files:
  - `scripts/seed_demo_data.py` — env **`DEMO_SEED_EMAIL`** (default **`superadmin@local`**), optional **`DEMO_SEED_KB_NAME`**, **`DEMO_SEED_DRY_RUN`** or **`--dry-run`**; prints user, KB, created/skipped (or would-create in dry-run), audit insert count.
- Validation results:
  - **`python -m compileall app scripts`** passes.
  - **`python scripts/seed_demo_data.py --dry-run`** runs without writes.
  - Re-run apply mode skips existing seed rows; **Demo Readiness** / **Feedback Analytics** reflect seeded counts.

- Step 43 completed: Demo reset / cleanup utility (safe marker-only deletion)
- Objective:
  - Add **`scripts/reset_demo_data.py`** to remove only Step 42 seeded rows using explicit markers: **`[DEMO_SEED_42]`** in **`query_feedback.question_text`** and **`improvement_tasks.title`**, plus audit rows where **`metadata_json.source == "DEMO_SEED_42"`** (or metadata text contains the marker). No non-marker data is deleted.
- Backend / script files:
  - `scripts/reset_demo_data.py` — supports **`--dry-run`** and **`DEMO_RESET_DRY_RUN=true`**; prints candidate counts/lists, plus **skipped/unsafe** feedback rows if referenced by non-seed tasks; deletion order is **improvement_tasks → query_feedback → audit_logs** in one transaction.
- Validation results:
  - **`python -m compileall app scripts`** passes.
  - **`python scripts/reset_demo_data.py --dry-run`** works and shows only marker-matched rows.
  - Seed then reset removes only seeded rows; second reset run is no-op and safe.

- Step 44 completed: Demo command center (admin seed/reset/status controls)
- Objective:
  - Add admin-only API controls to seed/reset demo data from UI while preserving Step 42/43 safety: **`POST /api/v1/admin/demo-data/seed`**, **`POST /api/v1/admin/demo-data/reset`**, **`GET /api/v1/admin/demo-data/status`**.
- Backend files changed:
  - `app/services/demo_data_service.py` — shared logic for seed, reset, and marker-based status counts (reused by APIs and scripts).
  - `app/api/v1/endpoints/admin_demo_data.py` — admin/super_admin endpoints with **`dry_run`** support; commits only on apply.
  - `app/api/v1/router.py` — mount demo-data admin router.
  - `scripts/seed_demo_data.py` and `scripts/reset_demo_data.py` — now delegate to the shared service.
- Frontend files changed:
  - `frontend/src/api/demoCommandCenterApi.ts` — status/seed/reset clients.
  - `frontend/src/pages/DemoCommandCenterPage.tsx` — counts, operation buttons (dry-run/apply), and latest JSON output panel with reset warning.
  - `frontend/src/App.tsx` — route **`/admin/demo-command-center`** with admin gate.
  - `frontend/src/components/Sidebar.tsx` — **Demo Command Center** link.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.
  - **`python scripts/seed_demo_data.py --dry-run`** and **`python scripts/reset_demo_data.py --dry-run`** pass with shared logic.

- Step 45 completed: Demo environment smoke runner (read-only pre-demo validation)
- Objective:
  - Add **`scripts/demo_smoke_runner.py`** to validate demo environment endpoints with JWT/login auth, timeout handling, clear PASS/WARN/FAIL table output, and non-zero exit when any critical check fails.
- Backend / script files:
  - `scripts/demo_smoke_runner.py` — auth via **`DEMO_SMOKE_JWT`** or **`DEMO_SMOKE_EMAIL`** + **`DEMO_SMOKE_PASSWORD`**; default base URL **`http://127.0.0.1:8010/api/v1`**; checks **`/health`**, **`/admin/demo-readiness`**, **`/status`**, **`/admin/demo-script`**, **`/admin/demo-data/status`**, **`/knowledge-bases/me`**, **`/feedback/analytics`**, **`/audit/logs`**, **`/improvements/tasks`**, plus optional **`/diagnostics/retrieval-test`** if KB exists.
- Validation results:
  - **`python -m compileall app scripts`** passes.
  - Running without credentials exits with clear auth guidance.
  - Running with credentials executes endpoint checks and reports failures/warnings in a table without mutating data.

- Step 45.1 completed: Smoke runner route alignment fix
- Objective:
  - Diagnose 404s from the smoke runner by verifying router includes and actual registered paths, then align runtime by restarting stale backend process on port **8010**.
- Backend / script files:
  - `scripts/list_routes.py` — prints all FastAPI API routes with **METHODS + PATH** from `app.main`.
  - `scripts/demo_smoke_runner.py` — retained endpoint paths; adjusted optional enrichment rows to emit only when corresponding endpoint call is 2xx.
- Findings:
  - `app/api/v1/router.py` already included **admin_demo_readiness**, **admin_demo_script**, **admin_demo_data**, **audit**, **improvements**, **feedback**, and **diagnostics** routers.
  - `python scripts/list_routes.py` confirmed expected paths exist: `/api/v1/admin/demo-readiness`, `/api/v1/admin/demo-script`, `/api/v1/admin/demo-data/status`, `/api/v1/status`, `/api/v1/feedback/analytics`, `/api/v1/audit/logs`, `/api/v1/improvements/tasks`, `/api/v1/diagnostics/retrieval-test`.
  - Root cause was stale server process (code/routes ahead of running backend), not path mismatch.
- Runtime action:
  - Stopped old listener on **8010** and restarted with:
    - `uvicorn app.main:app --host 127.0.0.1 --port 8010`
- Validation results:
  - **`python -m compileall app scripts`** passes.
  - `python scripts/list_routes.py` shows Step 40–45 routes.
  - `python scripts/demo_smoke_runner.py` passes route checks after restart.

- Step 46 completed: Demo evidence pack export (admin read-only bundle)
- Objective:
  - Provide **`GET /api/v1/admin/demo-evidence-pack`** for admin/super_admin to export a single JSON bundle containing readiness, platform health, demo script context, feedback analytics, open improvement tasks, and recent audit summary — no data mutation.
- Backend files changed:
  - `app/api/v1/endpoints/admin_demo_evidence_pack.py` — composes existing helper logic from readiness, health, demo script, feedback analytics, improvements list, and audit logs; adds `generated_at` and `generated_by`.
  - `app/api/v1/router.py` — mounts evidence-pack admin router under `/admin`.
- Frontend files changed:
  - `frontend/src/api/demoEvidencePackApi.ts` — client for `/admin/demo-evidence-pack`.
  - `frontend/src/pages/DemoEvidencePackPage.tsx` — loads evidence pack, shows generated metadata + key sections, and supports **Download JSON**.
  - `frontend/src/App.tsx` — route `/admin/demo-evidence-pack` with admin gate.
  - `frontend/src/components/Sidebar.tsx` — **Evidence Pack** link.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.
  - Admin endpoint returns expected keys after backend restart.
  - Smoke runner still passes.

- Step 47 completed: Evidence pack PDF export (admin read-only document)
- Objective:
  - Allow admin/super_admin users to download a human-readable PDF version of the demo evidence pack while preserving existing JSON export and read-only behavior.
- Backend files changed:
  - `app/api/v1/endpoints/admin_demo_evidence_pack.py` — extracted shared `build_demo_evidence_pack_payload(...)`, added **`GET /api/v1/admin/demo-evidence-pack/pdf`** returning `application/pdf`, and rendered a simple summary document (title, generated metadata, readiness/platform summaries, feedback summary, open tasks, recent audits, recommendations).
  - `requirements.txt` — added **`reportlab`**.
- Frontend files changed:
  - `frontend/src/api/demoEvidencePackApi.ts` — added PDF blob download method for `/admin/demo-evidence-pack/pdf`.
  - `frontend/src/pages/DemoEvidencePackPage.tsx` — added **Download PDF** button alongside JSON export.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.
  - Admin can fetch JSON and PDF evidence pack endpoints.
  - Smoke runner still passes.

- Step 48 completed: Admin demo runbook (read-only commands and checks)
- Objective:
  - Provide **`GET /api/v1/admin/demo-runbook`** for admin/super_admin with eight JSON sections (start backend/frontend, migrations, seed, smoke runner including `list_routes.py`, evidence export notes, troubleshooting stale process, demo URLs). No mutation, no `QueryResponse` changes.
  - Add **`/admin/demo-runbook`** UI with copy-friendly command cards and sidebar **Demo Runbook**.
- Backend files changed:
  - `app/api/v1/endpoints/admin_demo_runbook.py` — static runbook payload; `require_admin_or_super_admin`.
  - `app/api/v1/router.py` — mounts runbook router under `/admin`.
- Frontend files changed:
  - `frontend/src/api/demoRunbookApi.ts` — client for `/admin/demo-runbook`.
  - `frontend/src/pages/DemoRunbookPage.tsx` — fetches runbook, renders sections with copy-friendly command cards (Copy per command).
  - `frontend/src/App.tsx` — route `/admin/demo-runbook` with same admin gate as other demo admin pages.
  - `frontend/src/components/Sidebar.tsx` — **Demo Runbook** link.
- Validation results:
  - **`python -m compileall app`** passes.
  - **`npm run build`** passes.
  - Admin can open runbook; non-admin receives 403 from API and is redirected by gate.

- Step 49 completed: Final demo polish and admin navigation cleanup
- Objective:
  - Group **Administration** sidebar links into **Core**, **Diagnostics**, **Quality**, and **Demo** for clearer presenter flow; keep **Workspace** nav unchanged for regular users.
  - Confirm major admin/demo pages retain short top-of-page descriptions; avoid duplicate routes, gates, imports, or nav links.
- Frontend files changed:
  - `frontend/src/components/Sidebar.tsx` — sectioned admin nav: Core (Admin Workspace); Diagnostics (System Health, Retrieval Diagnostics, Audit Logs, optional Advanced Diagnostics future link); Quality (Query Feedback, Feedback Analytics, Improvement Tasks); Demo (Readiness, Script, Command Center, Evidence Pack, Runbook).
- Validation results:
  - **`npm run build`** passes.
  - Admin sidebar shows grouped labels; non-admin sidebar unchanged aside from hidden admin blocks.

- Step 50 completed: Final demo hardening sprint (stability, smoke validation, presentation readiness)
- Objective:
  - Harden **demo-day** operations: clear **startup logs** (providers, vector collection target, orchestration, conversation summary, streaming route), **`[admin.demo]`** logging on unexpected failures in heavy admin GETs, **smoke runner** coverage for evidence pack JSON/PDF and demo runbook, and **critical FAIL** when **Demo Readiness** `overall_status` is **blocked** (ready/warning only pass the gate).
  - Frontend: separate **PDF download** error from pack load error; **feedback analytics** empty state when `total_feedback === 0`; admin tables already use horizontal scroll wrappers where wide.
- Backend files changed:
  - `app/main.py` — FastAPI **lifespan** calls startup banner.
  - `app/core/startup_banner.py` — logs provider mode, `vector_collection_target`, `ENABLE_AGENT_ORCHESTRATION`, `ENABLE_CONVERSATION_SUMMARY`, streaming route hint, `QDRANT_URL`.
  - `app/api/v1/admin_demo_logging.py` — shared `log_demo_endpoint_failure` with `[admin.demo]` prefix.
  - `app/api/v1/endpoints/admin_demo_readiness.py`, `admin_demo_script.py`, `admin_demo_evidence_pack.py`, `admin_demo_data.py` — try/except + log on unexpected errors.
  - `scripts/demo_smoke_runner.py` — `/admin/demo-evidence-pack` schema check, streamed **PDF** header check, `/admin/demo-runbook`, readiness **blocked** = critical FAIL.
- Frontend files changed:
  - `frontend/src/pages/DemoEvidencePackPage.tsx` — `pdfError` banner vs load `error`.
  - `frontend/src/pages/FeedbackAnalyticsPage.tsx` — empty-range message when `total_feedback === 0`.
- Validation results:
  - **`python -m compileall app scripts`** passes.
  - **`npm run build`** passes.
  - **`python scripts/demo_smoke_runner.py`** expected **PASS** when API is up, admin auth works, and readiness is not **blocked** (otherwise FAIL by design).

- Step 50.1 completed: Safe test data cleanup for fresh E2E (KB-scoped)
- Objective:
  - Allow **admin/super_admin** to preview and run **KB-isolated** cleanup of ingestion/query test artifacts: **documents**, **chunks**, **Qdrant vectors** (by stored point IDs only), **ingestion jobs**, **chat sessions/messages**, optional **query feedback** / **improvement tasks** / **audit logs**, with **`dry_run`** first.
  - Preserve **users, roles, permissions, knowledge_bases**; preserve **demo seed** feedback/tasks/audit rows unless **`include_demo_seed: true`**.
- Backend files changed:
  - `app/services/test_data_cleanup_service.py` — planning + transactional deletes; Qdrant **PointIdsList** batch deletes only.
  - `app/api/v1/endpoints/admin_test_data_cleanup.py` — **`POST /api/v1/admin/test-data/cleanup`**.
  - `app/api/v1/router.py` — mount cleanup router under `/admin`.
  - `scripts/cleanup_test_data.py` — CLI using **`CLEANUP_KB_ID`**, **`CLEANUP_DRY_RUN`**, JWT/password envs.
- Validation results:
  - **`python -m compileall app scripts`** passes.
  - **`npm run build`** passes (no frontend change required for this step).

- Step 50.2 completed: Chat session summary default regression fix
- Root cause:
  - Migration **`b8f3a1c9e2d0`** added **`summary_message_count`** with **`server_default="0"`** then immediately called **`alter_column(..., server_default=None)`**, removing the DB default.
  - **`RagService._ensure_session`** used a raw **`INSERT INTO chat_sessions (user_id, knowledge_base_id, title)`** without **`summary_message_count`**, so PostgreSQL inserted **NULL** into a **NOT NULL** column → **`psycopg2.errors.NotNullViolation`** on **`POST /query/ask`** for new sessions.
- Backend files changed:
  - `app/models/chat.py` — **`summary_message_count`**: **`nullable=False`**, **`default=0`**, **`server_default=text("0")`**.
  - `app/services/rag_service.py` — new session **`INSERT`** explicitly sets **`summary_message_count = 0`**, **`summary_text = NULL`**, **`summary_updated_at = NULL`**.
  - `alembic/versions/a7c4e9d12f00_fix_chat_session_summary_message_count.py` — **`UPDATE`** NULLs to **0**; **`ALTER COLUMN`** restores **`DEFAULT 0`** and **`NOT NULL`** (no table drop).
- Validation results:
  - **`alembic upgrade head`** applies **`a7c4e9d12f00`** after **`c2e8a1b304d9`**.
  - **`python -m compileall app`** passes.
  - **Manual:** new chat from UI (e.g. *“What authentication flow is used in the QR Util Service?”*) should create a session without DB errors and return a normal answer.

## Current completed migrations
- a7c4e9d12f00_fix_chat_session_summary_message_count.py
- c2e8a1b304d9_add_audit_logs_table.py
- b3d8f1a92c42_add_improvement_task_resolution_columns.py
- a5c9e2f0b8d1_add_improvement_tasks_table.py
- d4e7b2a91f01_add_query_feedback_table.py
- b8f3a1c9e2d0_add_chat_session_summary_columns.py
- 7f1c2d9a4a10_add_auth_rbac_tables.py
- a3b9f2d11c77_add_kb_fields_and_document_kb_id.py
- f4d8a02b8a11_add_chat_session_knowledge_base_id.py
- 9b7c1e2d4f90_add_document_classification_metadata.py
- c2e4a9d71b33_expand_api_parameters_mandatory_optional.py
- e1a5c8d2f744_expand_api_parameters_param_type.py

## Current important files
- app/main.py
- app/core/startup_banner.py
- app/api/v1/admin_demo_logging.py
- app/api/v1/endpoints/admin_test_data_cleanup.py
- app/services/test_data_cleanup_service.py
- app/agents/orchestrator.py
- app/core/security.py
- app/api/deps.py
- app/api/v1/endpoints/auth.py
- app/api/v1/endpoints/users.py
- app/api/v1/endpoints/knowledge_bases.py
- app/api/v1/endpoints/query.py
- app/api/v1/endpoints/feedback.py
- app/api/v1/endpoints/improvements.py
- app/api/v1/endpoints/health.py
- app/api/v1/endpoints/diagnostics.py
- app/api/v1/endpoints/ingestion.py
- app/api/v1/endpoints/audit.py
- app/api/v1/endpoints/admin_demo_readiness.py
- app/api/v1/endpoints/admin_demo_script.py
- app/api/v1/endpoints/admin_demo_data.py
- app/api/v1/endpoints/admin_demo_evidence_pack.py
- app/api/v1/endpoints/admin_demo_runbook.py
- app/services/audit_log_service.py
- app/services/demo_data_service.py
- app/services/seed_service.py
- app/services/retrieval_service.py
- app/services/rag_service.py
- app/services/conversation_summary_service.py
- scripts/demo_smoke_runner.py
- scripts/cleanup_test_data.py
- scripts/step20_2_eval.py
- scripts/step20_3_demo_validation.py
- scripts/step20_3_demo_readiness_checklist.md
- app/services/ingestion_service.py
- app/services/openai_client.py
- app/services/improvement_task_analysis.py
- app/services/vector_dimension_resolver.py
- app/models/user.py
- app/models/role.py
- app/models/permission.py
- app/models/user_profile.py
- app/models/knowledge_base.py
- app/models/api_document.py
- app/models/chat.py
- app/models/improvement_task.py
- app/models/audit_log.py

## Current important frontend files
- frontend/src/api/client.ts
- frontend/src/api/authApi.ts
- frontend/src/api/kbApi.ts
- frontend/src/api/queryApi.ts
- frontend/src/api/healthApi.ts
- frontend/src/api/diagnosticsApi.ts
- frontend/src/api/ingestionApi.ts
- frontend/src/api/feedbackApi.ts
- frontend/src/api/improvementsApi.ts
- frontend/src/api/auditApi.ts
- frontend/src/api/demoReadinessApi.ts
- frontend/src/api/demoScriptApi.ts
- frontend/src/api/demoCommandCenterApi.ts
- frontend/src/api/demoEvidencePackApi.ts
- frontend/src/api/demoRunbookApi.ts
- frontend/src/auth/AuthContext.tsx
- frontend/src/auth/ProtectedRoute.tsx
- frontend/src/auth/roleAccess.ts
- frontend/src/components/ChatSessionSidebar.tsx
- frontend/src/components/Sidebar.tsx
- frontend/src/components/TopNav.tsx
- frontend/src/components/ProviderBadge.tsx
- frontend/src/components/KBSelector.tsx
- frontend/src/pages/ChatPage.tsx
- frontend/src/pages/HealthStatusPage.tsx
- frontend/src/pages/RetrievalDiagnosticsPage.tsx
- frontend/src/pages/QueryFeedbackPage.tsx
- frontend/src/pages/FeedbackAnalyticsPage.tsx
- frontend/src/pages/ImprovementTasksPage.tsx
- frontend/src/pages/AuditLogsPage.tsx
- frontend/src/pages/DemoReadinessPage.tsx
- frontend/src/pages/DemoScriptPage.tsx
- frontend/src/pages/DemoCommandCenterPage.tsx
- frontend/src/pages/DemoEvidencePackPage.tsx
- frontend/src/pages/DemoRunbookPage.tsx
- frontend/src/pages/DocumentsPage.tsx
- frontend/src/pages/DashboardPage.tsx
- frontend/src/pages/NotAuthorizedPage.tsx
- frontend/src/types/document.ts
- frontend/src/utils/workspace.ts
- frontend/README.md
- scripts/step23_seed_demo_users.py
- scripts/seed_demo_data.py
- scripts/reset_demo_data.py
- scripts/demo_smoke_runner.py
- scripts/cleanup_test_data.py
- scripts/list_routes.py
- scripts/retrieval_smoke_test.py
- scripts/step23_validate_demo.py
- docs/demo_runbook.md
- docs/demo_script.md
- docs/startup_checklist.md
- docs/troubleshooting_checklist.md
- docs/known_limitations.md
- docs/demo_queries.md
- docs/environment_freeze.md
- docs/screenshots/README.md

## Step 19: Ollama embeddings and vector retrieval

### Step 19.1 completed — Ollama Connectivity Stabilization

- Added retry handling for embeddings and generation
- Default retry behavior is **3** attempts
- Explicit timeout handling added:
  - connect
  - read
  - write
  - pool
- Environment variables for timeouts and retries (optional overrides): `OLLAMA_TIMEOUT_CONNECT_SECONDS`, `OLLAMA_TIMEOUT_READ_SECONDS`, `OLLAMA_TIMEOUT_WRITE_SECONDS`, `OLLAMA_TIMEOUT_POOL_SECONDS`, `OLLAMA_RETRY_COUNT`, `OLLAMA_RETRY_DELAY_SECONDS`
- Added structured Ollama diagnostics logging (success/failure/retry/elapsed time as applicable)
- Added **generation_retry_failed** status when generation retries are exhausted
- Added **embedding_retry_failed** status when embedding retries are exhausted
- Backend falls back gracefully **without hanging**
- API/Product ingestion and query tested successfully
- Retrieval still commonly operates in **db_keyword_fallback** due to intermittent Ollama connectivity
- Windows → Mac Ollama connectivity remains **intermittent**
- passlib/bcrypt warning remains **non-blocking**

### Step 19.2 completed — Embedding persistence and vector retrieval validation

- Qdrant collection existence validated
- Vector persistence validated
- Vector dimensions validated (**768**)
- Qdrant collection point counts verified
- Added vector/fallback diagnostics under `debug=true`
- Added vector retrieval observability fields:
  - `vector_search_attempted`
  - `vector_results_count`
  - `vector_retrieval_outcome`
  - `fallback_triggered`
  - `fallback_reason`
  - `source_metadata_coverage`
- Product KB vector retrieval successfully validated
- `vector_retrieval_outcome=vector_success` confirmed for Product KB
- KB-isolated vector retrieval verified
- Product vector metadata verified:
  - `document_type`
  - `product_name`
  - `section_title`
- Added Qdrant compatibility wrapper for `qdrant-client 1.17.1`
- Compatibility fix supports:
  - `search(...)`
  - `query_points(...)`
- Temporary Windows Ollama validation was used only for diagnostics
- Official architecture restored back to Mac-hosted Ollama
- Current runtime still commonly falls back due to intermittent Mac Ollama connectivity
- Fallback behavior remains safe and stable

## Step 20.1: Provider abstraction (OpenAI + Ollama)

### Completed
- Config-driven provider abstraction
- OpenAI client integration
- OpenAI embedding support
- OpenAI generation support
- Ollama compatibility preserved
- Provider-aware Qdrant collection routing
- Provider-aware vector dimensions
- Provider-aware diagnostics
- OpenAI end-to-end `vector_success` validation
- Ollama regression validation

### Provider-aware vector collections
- `enterprise_api_docs`
  - provider: ollama
  - vector dimension: 768
- `enterprise_api_docs_openai`
  - provider: openai
  - vector dimension: 1536

### Current provider config
- `OPENAI_API_KEY`
- `LLM_PROVIDER`
- `EMBEDDING_PROVIDER`
- `OPENAI_LLM_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_LLM_MODEL`
- `OLLAMA_EMBEDDING_MODEL`

### Current operational behavior
- OpenAI path is stable and validated for POC/demo usage
- Ollama remains the official/final architecture
- Mac-hosted Ollama intermittency still exists operationally
- Fallback behavior remains safe and non-blocking

## Step 22.1: Frontend foundation setup

### Completed
- Frontend foundation scaffolded under `frontend/`
- Auth context added
- Protected routes added
- JWT handling with `localStorage` (POC)
- Role-aware sidebar added
- KB selector added
- Axios API client setup added

### Current frontend routes
- `/login`
- `/`
- `/chat`
- `/admin`
- `/documents`
- `/not-authorized`

## Step 22.2: Accessible KB endpoint + frontend KB visibility cleanup

### Completed
- Added backend endpoint: `GET /api/v1/knowledge-bases/me`
- Frontend now uses backend-supported accessible KB visibility
- Removed frontend session-derived KB visibility workaround

### Accessible KB response fields in use
- `access_level`
- `can_query`
- `can_upload`
- `can_manage`
- `can_view_documents`

## Step 22.3: Full KB-aware chat UI

### Completed
- KB-aware query flow implemented
- Full `ChatPage` implemented for ask/answer loop
- Sources panel implemented
- Diagnostics panel implemented (role-restricted)
- Deterministic insufficient-context UX implemented
- Loading and error handling implemented
- In-memory chat history implemented

### Diagnostics fields shown in UI
- `llm_provider`
- `embedding_provider`
- `llm_model`
- `embedding_model`
- `retrieval_mode`
- `vector_retrieval_outcome`
- `vector_results_count`
- `hybrid_fusion_used`
- `rerank_strategy`
- `vector_confidence_bucket`
- `selected_prompt_chunk_count`
- `dedup_chunks_removed`
- `fallback_triggered`
- `fallback_reason`
- `llm_status`

## Step 22.4: Chat session UX

### Completed
- Chat session sidebar added
- New chat flow added
- Persisted session continuation added
- Previous session loading added
- Cross-KB session safety added
- Session filtering by accessible KBs added

### Session architecture notes
- Reused existing backend session APIs
- No backend session redesign required
- Frontend prevents cross-KB continuation

## Frontend workspace notes
- API Workspace
- Product Workspace
- HR Workspace
- Recruitment Workspace (future)
- Admin Workspace
- Current implementation uses a shared chat UI with RBAC-aware behavior and KB-aware isolation.

## Demo Day Startup Checklist

1. **PostgreSQL** — `DATABASE_URL` valid; run **`alembic upgrade head`** from `agentic-enterprise-api-rag-backend`.
2. **Qdrant** — `QDRANT_URL` reachable; collection matches **embedding provider** (see startup log `vector_collection_target=`).
3. **Providers** — `.env`: `LLM_PROVIDER` / `EMBEDDING_PROVIDER`; if OpenAI, `OPENAI_API_KEY` set.
4. **Backend** — `uvicorn app.main:app --host 127.0.0.1 --port 8010` (no `--reload` per project constraints); confirm **uvicorn stdout** shows the **startup banner** lines.
5. **Seed (optional but typical)** — `python scripts/seed_demo_data.py` from backend root (see Demo Runbook for flags).
6. **Optional: reset uploaded test docs for one KB** — `python scripts/cleanup_test_data.py --kb-id <id>` (dry-run by default); use **`--apply`** only after reviewing JSON output; or **`POST /api/v1/admin/test-data/cleanup`** with **`"dry_run": true`** first.
7. **Smoke** — `python scripts/demo_smoke_runner.py` with `DEMO_SMOKE_JWT` or `DEMO_SMOKE_EMAIL` + `DEMO_SMOKE_PASSWORD`; expect **OVERALL: PASS** and readiness **not blocked**.
8. **Frontend** — `npm run dev` from `frontend`; log in as admin; walk **Demo** sidebar: Readiness → Script → Command Center → Evidence Pack (JSON + PDF) → Runbook.
9. **Presenter loop** — Chat (streaming), feedback thumbs, improvement task from analytics link, audit logs, retrieval diagnostics on a seeded KB.

## Recommended demo flow

Open **Demo Readiness** first and narrate **ready** vs **warning** vs **blocked**. Follow **Demo Script** section order; use **Demo Command Center** only if you need to re-seed or confirm counts. Pull **Evidence Pack** (JSON and/or PDF) for stakeholders who want a single artifact. Keep **Demo Runbook** open on the presenter machine for exact commands. Use **System Health** if anything misbehaves mid-demo; use **Retrieval Diagnostics** to prove hybrid search without burning LLM tokens.

## Step 50.3: API DOCX parser — QR Util and generic `API-REST-*` references

### Problem
Some API specification DOCX files (for example **QR Util Service**) ingested with **`api_count=0`** and a single fallback chunk because:
- The parser only recognized **`API-REST-(DSE|NOK|SAC)-\d+`**, so identifiers such as **`API-REST-QRU-01`** were ignored.
- Tables and narrative **before the first recognized API id** were skipped when no `current_ref` was set, so structured tables never attached to an API section.

### Changes
- **`app/services/docx_parser_service.py`**
  - API reference regex extended to **`API-REST-[A-Z]+-\d+`** (still matches legacy DSE/NOK/SAC).
  - Document walk keeps a **preamble buffer** until the first API section; preamble is merged into the first parsed API block.
  - **`getSSOToken`** heading starts a synthetic section with id **`getSSOToken`** (OpenID-style metadata).
  - **QR Checkout / `generate-qr`** headings enrich the active REST section (name, path).
  - Tables classify **header / query / response / error / JWT** parameter rows using the preceding heading/paragraph context.
  - **`authentication_preamble`** is built from logical sections titled **General Authentication** / OAuth2 client credentials narrative for the **`authentication_chunk`**.
  - Light **defaults** fill typical QR Util template fields when rows are missing (without overwriting explicit table values).
- **`app/services/chunking_service.py`**
  - **`authentication_chunk`** includes **`authentication_preamble`** plus per-API auth lines.
  - Additional chunk types: **`api_header_parameters_chunk`**, **`api_query_parameters_chunk`**, **`api_error_codes_chunk`**, **`api_jwt_payload_chunk`**; large **`generic_section_chunk`** bodies are split (~1400 chars).
- **`app/services/ingestion_service.py`** — persist **`query`**, **`error`**, and **`jwt_payload`** parameter rows.
- **`app/services/retrieval_service.py`**, **`rag_service.py`**, **`impact_analysis_service.py`**, **`suggested_question_service.py`** — intent / impact logic recognizes the new chunk types where relevant; **`authentication_chunk`** rerank boost under **`authentication_intent`** increased so auth-oriented chunks are not drowned out by higher raw vector scores alone.
- **`tests/test_docx_ingestion_quality.py`** — **`test_qr_util_style_docx_parsing_and_chunking`** fixture covering **`API-REST-QRU-01`**, **`getSSOToken`**, and parameter blocks.

### Validation
- Re-upload the QR Util DOCX to the API knowledge base; expect **`api_count >= 1`**, **`chunk_count` well above 1**, and retrieval diagnostics hitting **`authentication_chunk`**, metadata, and parameter chunks for questions about OAuth2, **`API-REST-QRU-01`**, and mandatory QR parameters.
- **`python -m pytest tests/test_docx_ingestion_quality.py`**

## Step 50.4: Response parameter retrieval — QR generation / success response fields

### Problem
After Step 50.3, QR Util docs chunked well, but questions such as **"What are the success response fields for the QR generation API?"** often missed **`api_response_parameters_chunk`** because:
- **`parameter_intent`** did not match the word **"fields"** (only **`field`**).
- **`api_error_codes_chunk`** was boosted under generic **parameter** intent alongside response chunks.
- Prompt context selection used **high token overlap** between chunks sharing the same API header lines, so **`api_response_parameters_chunk`** could be dropped in favor of metadata/overview.
- Suggested follow-up questions used **`service_names[0]`**, which could be an unrelated generic chunk (for example **deactivationService**) instead of the QR service from the best retrieval row.

### Changes
- **`app/services/query_intent_service.py`** — New **`response_field_intent`** regexes (success response fields, response parameters, output response, what fields are returned, etc.); **`parameter_intent`** adds **`fields`**.
- **`app/services/docx_parser_service.py`** — Table rows keep **empty leading cells** for column alignment; **Response Parameters** (and request-side) tables support **nested rows** under a parent object row (for example **`responseInfo.merchantName`**).
- **`app/services/retrieval_service.py`** — **`response_field_intent`**: strong boost for **`api_response_parameters_chunk`**, **`api_sample_success_response_chunk`**, and reserved **`endpoint_response_chunk`**; slight penalty for **`generic_section_chunk`**; **`api_error_codes_chunk`** is **not** boosted under **`parameter_intent`** when **`response_field_intent`** is present (error questions still use **`error_intent`**).
- **`app/services/rag_service.py`** — **`_select_prompt_contexts`**: when **`response_field_intent`** is set, **sort** candidates so response chunks are considered first, **skip token-overlap dedupe** for response/success-response chunk types, relax **per-document** and **per-api_ref** caps, and optionally allow an extra response chunk when the **per-section** cap would block it; **`_has_intent_supporting_context`** extended for response-field questions.
- **`app/services/suggested_question_service.py`** — **`_primary_api_scope`** picks **`service_name` / `api_reference_id`** from the highest-priority retrieved chunk types (response/metadata before generic).
- **`app/services/confidence_service.py`**, **`app/services/impact_analysis_service.py`** — Treat **`api_sample_success_response_chunk`** (and **`endpoint_response_chunk`**) as response-oriented where relevant.
- **`tests/test_docx_ingestion_quality.py`** — Expanded QR fixture **Response Parameters** table; tests for intent detection, parsed field names, chunk text, reranking, prompt selection, and suggested-question scoping.

### Validation
- Ask **"What are the success response fields for the QR generation API?"** against a re-ingested QR Util KB; diagnostics should include **`api_response_parameters_chunk`** in top contexts / prompt selection when applicable.
- **`python -m pytest tests/test_docx_ingestion_quality.py tests/test_hybrid_intent_rerank.py`**

## Step 50.5: QR Response Parameters table extraction into structured chunks

### Problem
Hybrid retrieval ranked **`api_response_parameters_chunk`** correctly, but chunk text showed **`Response Parameters: N/A`** and **`api_sample_success_response_chunk`** showed **`Sample Success Response: N/A`** while **`generic_section_chunk`** still contained the real table (transactionId, correlationId, responseInfo, …). Root causes:
- **Context loss**: the paragraph immediately before a table was not always a reliable cue (`recent_context` alone); captions such as **Output Response Success** did not map to the response bucket.
- **Strict header detection**: some templates use **Field** / **Element** column titles instead of **Name**.
- **Nested rows**: object parents (**responseInfo**) and following scalar rows (**qrText**, **errorcode**) needed stable **`responseInfo.*`** names.

### Changes
- **`app/services/docx_parser_service.py`**
  - **`pending_table_hint`** from caption paragraphs matching **Response Parameters**, **Output Response**, **Output Response Success**, **Success Response**, plus request/header/query/error/jwt captions.
  - **Title row**: first table row with a single cell matching those captions strips the row and applies the hint.
  - Broader **parameter table** detection (**field**, **element**, **attribute**).
  - **`section_hint`** + context routing into **`api_response_parameters`** / **`output_response_success`**.
  - **Nested response naming**: object row sets **`nested_response_prefix`**; subsequent rows become **`responseInfo.qrText`**, **`responseInfo.errorcode`**, etc.; blank first-cell rows nest under the same prefix.
- **`app/services/chunking_service.py`** — **`_render_response_parameter_body`**: if structured lists are empty, **fallback** extracts the Response Parameters region from **`raw_text`** so **`api_response_parameters_chunk`** does not emit **`N/A`** when the prose still contains the table.
- **`app/services/retrieval_service.py`** — For **`response_field_intent`**: extra boost when response chunk is **not** `N/A`; **penalty** when **`api_sample_success_response_chunk`** body is **`N/A`**.
- **`app/services/rag_service.py`** — Prompt ordering: **`api_sample_success_response_chunk`** with empty/N/A sample sorts **after** structured response chunks.

### Validation
- **`python -m pytest tests/test_docx_ingestion_quality.py`** (includes **`test_step_50_5_qr_response_table_extracted_not_na_chunk`**).

## Step 50.6: Response Parameters fallback capture boundary (TOC / preamble safe)

### Problem
After Step 50.5, **`api_response_parameters_chunk`** could rank first but embed wrong fallback text: matching **“Response Parameters”** from a **Table of Contents** or early prose, then pulling **General Authentication** / unrelated narrative instead of the real parameter table for **`API-REST-QRU-01`**.

### Changes
- **`app/services/chunking_service.py`**
  - **`_scope_raw_after_api_ref`**: fallback scans only **`raw_text` at or after the active `api_reference_id`** (REST IDs must appear in `raw_text` or fallback is skipped — no full-document scan from offset 0).
  - **TOC heuristics**: skip dot-leader / page-number lines and common TOC patterns before accepting a **section start** line.
  - **Start lines** (whole-line): **Response Parameters**, **Output Response**, **Output Response Success**, **Success Response** (must not be TOC lines).
  - **Stop lines**: **Integration Flow**, **Sample**, **Failed Response**, **Appendix**, **Expected Error Codes**, **System Attributes**, **JWT** payload headings, **Other References**, **Header/Query/Request Parameters**, next **`API-REST-*`** id (other than current).
  - **Validation**: fallback accepted only if at least **two** known markers appear among **status, code, desc, timestamp, transactionId, correlationId, responseInfo, qrText, errorcode, errormsg** (substring match on normalized text).
  - **`response_parameters_chunk_quality`**: shared helper for retrieval — detects degenerate **`Response Parameters: response parameters`** style bodies and insufficient known fields.
- **`app/services/retrieval_service.py`** — Under **`response_field_intent`**, **`api_response_parameters_chunk`** gets the extra boost only when **`boost_ok`** (≥2 known fields, non-degenerate); otherwise applies **weak_response_chunk_penalty**.

### Validation
- **`python -m pytest tests/test_docx_ingestion_quality.py`** — includes **`test_step_50_6_*`** (TOC fixture, fallback unit tests, quality helper).

## Step 50.7: Response field fallback from generic_section_chunk

### Problem
For some QR Util DOCX parses, **`api_response_parameters_chunk`** / **`api_sample_*`** still surface **`N/A`** while **`generic_section_chunk`** already holds the real response table (`transactionId`, `correlationId`, `responseInfo`, `qrText`, …). Retrieval diagnostics showed structured chunks first even when useless, and prompt selection could drop the generic chunk or trigger insufficient-context heuristics despite usable text.

### Changes
- **`app/services/chunking_service.py`** — **`generic_chunk_qualifies_as_response_fields`** / marker helpers (≥2 known markers among status, code, desc, timestamp, transactionId, correlationId, responseInfo, qrText, errorcode, errormsg).
- **`app/services/retrieval_service.py`** — Under **`response_field_intent`**: strong penalties when structured response/sample chunks are degenerate **`N/A`**; boost **`generic_section_chunk`** when it qualifies as response-field text.
- **`app/services/rag_service.py`**
  - Sort prompt-context candidates so qualifying **`generic_section_chunk`** ranks above empty structured chunks; overlap / section caps bypass when a chunk actually supports response-field answers (including qualifying generic).
  - **`_is_context_insufficient`**: for **`response_field_intent`**, return **False** when context includes qualifying generic or usable structured response text.
  - **`_annotate_recovered_response_chunks`**: prepend **`Recovered Response Parameters`** for qualifying generic chunks when the question has **`response_field_intent`**; set **`response_fields_recovered_from_generic`** in **`prompt_context_diagnostics`** when structured chunks did not carry usable fields but generic did.
  - **`_response_field_prompt_instruction`**: instruct the LLM to list only the named standard fields **if present** in context.
- **`app/prompts/rag_answer_prompt.py`** — Display **`generic_section_chunk (Recovered Response Parameters)`** when chunk text is labeled; optional **`response_field_instruction`** passed into **`build_rag_prompt`**.
- **`tests/test_response_field_generic_fallback.py`** — Selection, insufficient-context, recovery flag, rerank ordering.

### Validation
- **`python -m pytest tests/test_docx_ingestion_quality.py tests/test_hybrid_intent_rerank.py tests/test_response_field_generic_fallback.py`**

## Step 50.8 — 8010 Restart and Step 50.7 Closure

### Summary
- Port **8010** was running a **stale** backend process (pre–Step 50.7 code).
- **Restarted** **`uvicorn`** from the current backend workspace on **`127.0.0.1:8010`**.
- Step **50.7** response-field generic recovery is **validated** on **8010** with live QR Util KB data.

### Validation
- **`diagnostics.response_fields_recovered_from_generic`**: **true**
- **`detected_intents`**: **`['parameter_intent', 'response_field_intent']`**
- **`generic_section_chunk`** is **favored** over **N/A** structured response chunks (rerank / top sources)
- **`selected_prompt_chunk_count`**: **3**
- **`final_prompt_context_chars`**: **5608**
- **Regression passed** for:
  - authentication questions
  - error-code questions
  - request-parameter questions

### Closure
- Step **50.7** **product / retrieval** logic is **closed**.
- Remaining **intermittent fallback** on the success-response-fields question is due to **occasional empty LLM / provider response**, not retrieval failure.
- Treat future recurrence as **LLM reliability monitoring** unless **retrieval diagnostics** fail.

## Step 51 — LLM Reliability Hardening

### Summary
- Added **provider retry** handling in **`rag_service.py`**.
- Added classification between **true retrieval insufficiency** and **provider generation failure**.
- Added **`llm_status`**: **`fallback_provider_generation_failure`**.
- Added diagnostics:
  - **`provider_retry_attempted`**
  - **`provider_retry_reason`**
  - **`provider_response_empty`**
  - **`provider_exception_type`**
  - **`generation_char_count`**
- Updated **`confidence_service.py`** to treat **`fallback_provider_generation_failure`** as **low confidence**.
- Added **`tests/test_generation_retry.py`**.

### Validation
- **`demo_smoke_runner.py`** passed.
- **`pytest`** passed:
  - **`tests/test_generation_retry.py`**
  - **`tests/test_response_field_generic_fallback.py`**
  - **`tests/test_hybrid_intent_rerank.py`**

## Step 51.2 — Restart 8010 and Live Validation

### Summary
- **8010** was **stale** before restart.
- **Restarted** backend from current **Step 51** workspace.
- **Step 51** diagnostics **confirmed live** on **8010**.

### Live validation
- QR success-response question ran **5** times.
- **5/5** returned **`llm_status`**: **`generated`**.
- **`response_fields_recovered_from_generic`**: **`true`**.
- **`provider_retry_attempted`**: **`false`**.
- **`provider_response_empty`**: **`false`**.
- **`generation_char_count`**: **2391**.
- **`selected_prompt_chunk_count`**: **3**.
- **`final_prompt_context_chars`**: **5608**.

### Regression
- **Authentication** question: **`generated`**.
- **Error-code** question: **`generated`**.
- **Request-parameter** question: **`generated`**.

### Closure
- Step **50.7** retrieval recovery **remains stable**.
- Step **51** provider reliability diagnostics are **live**.
- Step **51** is **closed**.
- Prior **missing diagnostics** were caused by a **stale 8010 process**, not source-code failure.

## Step 52 — Runtime Process Guard and Build Visibility

### Summary
- Added **`BUILD_VERSION`** to config (default **`52.0.0-local`**).
- Added **runtime metadata** helper (**`app/core/runtime_metadata.py`**).
- Added **startup banner** logging (build, PID, start time, providers, vector target).
- Added **`runtime`** block to **`GET /api/v1/health`** and **`GET /api/v1/status`** (backward-compatible append).
- Added **frontend** runtime display to **System Health** and **Demo Command Center**.
- Added **`tests/test_runtime_metadata.py`**.

### Runtime fields (`runtime` object)
- **`build_version`**
- **`process_start_time`**
- **`process_pid`**
- **`backend_uptime_seconds`**
- **`llm_provider`**
- **`embedding_provider`**
- **`active_vector_collection`**
- **`app_env`**
- **`app_name`**
- **`stale_process_hint`**

## Step 52.1 — Restart and Live Validation

### Validation
- **8010** was **stale** and was **restarted**.
- New process **PID**: **24700**.
- **`/health`** returned **`runtime`** metadata.
- **`/status`** returned **`runtime`** metadata.
- **`build_version`**: **`52.0.0-local`**.
- **`llm_provider`**: **openai**.
- **`embedding_provider`**: **openai**.
- **`active_vector_collection`**: **`enterprise_api_docs_openai`**.
- **Frontend** **`npm run build`** passed.
- **`demo_smoke_runner.py`** passed.
- **QR regression** passed:
  - **`llm_status`**: **`generated`**
  - **`response_fields_recovered_from_generic`**: **`true`**
  - **`generation_char_count`**: **2391**

### Closure
- Step **52** is **live-validated** and **closed**.
- **Stale backend process** confusion can be diagnosed using **`/health`** or **`/status`** (**`build_version`**, **PID**, **start time**).
- Existing **passlib/bcrypt** warning is **unrelated** and can be handled separately later.

## Step 53 — Backend lifecycle utility scripts

Lightweight developer helpers under `scripts/` (no Docker/Kubernetes/process managers; does not change retrieval, providers, or frontend).

### Scripts
| Script | Purpose |
|--------|---------|
| `scripts/start_backend.py` | If port **8010** is in use, print PID; optional **`--force-kill`** / **`-f`** stops stale listener; starts **`uvicorn app.main:app --host 127.0.0.1 --port 8010`** (detached); polls **`GET /api/v1/health`** and prints runtime summary (**`BUILD_VERSION`**, **`process_pid`**, **`process_start_time`**, **`llm_provider`**, **`embedding_provider`**, **`active_vector_collection`**). |
| `scripts/stop_backend.py` | Finds PID listening on **8010**, terminates, confirms port free. |
| `scripts/restart_backend.py` | Runs stop then start (with **`--force-kill`**); compares **`runtime.process_pid`** before vs after when health was reachable. |
| `scripts/check_backend_runtime.py` | **`GET /api/v1/health`** → concise runtime summary; exit **`1`** if unreachable, **`2`** if runtime block missing. Optional **`--json`**. |
| `scripts/dev_start.ps1` | PowerShell: **`cd`** to backend root, **`python scripts/start_backend.py @args`**. |
| `scripts/dev_restart.ps1` | PowerShell: **`python scripts/restart_backend.py @args`**. |
| `scripts/backend_lifecycle_lib.py` | Shared port/health helpers (stdlib **`urllib`**). |

### Validation (2026-05-12)
- **`start_backend.py --force-kill`**: backend up; health showed **`build_version`**: **`52.0.0-local`**, **`process_pid`**: **20784**, providers and **`active_vector_collection`** as expected.
- **`check_backend_runtime.py`**: printed healthy runtime summary (same PID while server stayed up).
- **`restart_backend.py`**: **`process_pid`** **20784** → **12284**; message **"Verified: process_pid changed after restart."**
- **`stop_backend.py`**: port **8010** released after stop.
- **`python scripts/demo_smoke_runner.py`**: **OVERALL: PASS** (with API on **127.0.0.1:8010** and env credentials as documented).

## Step 54 — Demo Stability Pack

### Summary
- Added **`scripts/demo_stability_check.py`**.
- Validates full demo readiness from one command.
- Supports **`--skip-frontend`**.
- Uses the same auth/env style as **`demo_smoke_runner.py`** (**`DEMO_SMOKE_*`**).
- Checks backend reachability, **`GET /api/v1/health`**, **`GET /api/v1/status`**, runtime metadata (**`build_version`**, **`process_pid`**, etc.), **PostgreSQL** / **Qdrant** via **`/status`** platform payload, vector collection, provider gate, authentication, **`POST /diagnostics/retrieval-test`**, and the QR Util key **`POST /query/ask`** questions (authentication, request parameters, response fields).

### Sample validation
- Command: **`python scripts/demo_stability_check.py --skip-frontend`**
- Result: **`OVERALL STATUS: DEMO READY`**
- Exit code: **`0`**
- Runtime **`BUILD_VERSION`**: **`52.0.0-local`**
- Runtime **PID**: **`28616`**
- **QR Util response-fields question**: **PASS** with **`recovery=true`**
- **Frontend build**: **SKIP** when **`--skip-frontend`** is used

### Exit code behavior
- **`0`** = demo ready
- **`1`** = warning / non-critical issue
- **`2`** = critical failure

### Regression
- **`python scripts/demo_smoke_runner.py`** passed unchanged.

### Closure
- Step **54** is **closed**.
- The project now has a **one-command** demo readiness check.

## Step 55 — Semantic Retrieval Enrichment for API Specs

### Summary
- **`app/services/chunking_service.py`**: Added **`api_semantic_summary_chunk`** (per-endpoint consolidated headers, query/request parameters, success response fields, failure fields; embedded retrieval alias lines for **headers** / **request JSON structure**), **`auth_semantic_summary_chunk`** (structured OAuth/expiry lines **540** / **60** seconds plus document narrative and token-expiry aliases), and **`api_table_flattened_chunk`** (natural-language rows for **Header Parameters**, **Query Parameters**, **Input Parameter**, **Output Response Success**, **Expected Error Codes**). Existing chunk types and ordering of legacy chunks are preserved; new chunks are additive.
- **`app/services/docx_parser_service.py`**: **`Input Parameter`** table captions recognized; authentication preamble extraction extended for access-token / refresh-token / **getSSOToken**-related sections.
- **`app/services/query_intent_service.py`**: New intents **`header_parameter_intent`**, **`token_expiry_intent`**, **`request_structure_intent`** (aligned with QR Util phrasing such as “headers required”, “expiry time … PROD vs non-PROD”, “request structure”).
- **`app/services/retrieval_service.py`**: Intent-aware reranking boosts for semantic chunks; **`authentication_chunk`** deprioritized when **`token_expiry_intent`** is active so **`auth_semantic_summary_chunk`** can win; **`api_semantic_summary_chunk`** receives extra boost under **`response_field_intent`** when success-field markers appear.
- **`app/services/confidence_service.py`**: Intent alignment recognizes **`api_semantic_summary_chunk`** / **`api_table_flattened_chunk`** / **`generic_section_chunk`** where appropriate.
- **Tests**: **`tests/test_semantic_retrieval_enrichment.py`**; **`pytest`** full backend suite **33 passed** (includes Step **50.7** response-field recovery and Step **51** provider retry tests).

### New chunk types
| Type | Role |
|------|------|
| **`api_semantic_summary_chunk`** | Single searchable summary per API endpoint (IDs, method, auth line, bullet lists, alias footer). |
| **`auth_semantic_summary_chunk`** | Searchable auth/expiry summary + preamble narrative + alias footer. |
| **`api_table_flattened_chunk`** | Flattened natural-language lines per parameter table (metadata `semantic_flatten_slot`). |

### Before / after retrieval diagnostics (conceptual)
- **Before**: Valid QR questions (headers, PROD vs non-PROD expiry, request structure) could return **`fallback_insufficient_context`** or weak mixes because tables lived mainly in structured/param chunks or raw generic sections.
- **After**: Matching intents trigger boosts such as **`header_semantic_boost`**, **`token_expiry_semantic_boost`**, **`request_structure_boost`**; top **`top_chunk_types`** should include the new semantic types after re-ingestion.

### Re-ingestion (required for full effect)
- New chunks are produced **during ingestion**. Re-upload / re-run ingestion for the QR Util DOCX (or use existing cleanup/reset tooling) so vectors include the new chunk texts.

### Validation targets (after re-ingestion)
| Question | Expected signal |
|----------|-------------------|
| What headers are required while calling the QR generation API? | **Authorization**, **TransactionId** surfaced from semantic / flattened header chunks. |
| What is the expiry time for access tokens in PROD vs non-PROD? | **Non-prod 540 seconds**, **Prod 60 seconds** from **`auth_semantic_summary_chunk`** / narrative. |
| Explain the request structure for QR generation. | **source**, **targetUrl**, **request_type**, **parameters** key/value language. |
| Regression: auth / error codes / success response fields questions | Still answered from existing chunk paths + **`response_field`** recovery unchanged (tests green). |

## Step 55.1 — Re-ingest and Live Validate Semantic Retrieval

### Summary
- Restarted backend from current repo.
- Runtime confirmed using lifecycle scripts.
- Cleaned **KB 1** using scoped cleanup.
- **KB 1** initially had **no documents**.
- Re-ingested QR Util-style DOCX using **`scripts/step551_live_validate.py`** because the production QR Util DOCX was **not present in repo**.
- Ingestion created **`document_id` 42**.
- **`chunk_count`**: **33**.
- **`qdrant_points_created`**: **33**.
- **`vector_store_status`**: **`persisted_ok`**.
- **`vector_sample_verified`**: **`true`**.
- **Collection**: **`enterprise_api_docs_openai`**.

### New chunk types confirmed
- **`api_semantic_summary_chunk`**
- **`auth_semantic_summary_chunk`**
- **`api_table_flattened_chunk`**

### Validation

**Q1:** What headers are required while calling the QR generation API?
- Answer included **Authorization** and **TransactionId**.
- **`detected_intents`** included **`parameter_intent`** and **`header_parameter_intent`**.
- Top chunk types included **`api_table_flattened_chunk`**, **`api_semantic_summary_chunk`**, **`api_header_parameters_chunk`**.

**Q2:** What is the expiry time for access tokens in PROD vs non-PROD?
- Answer included **Non-prod: 540 seconds** and **Prod: 60 seconds**.
- **`detected_intents`** included **`token_expiry_intent`**.
- Top chunk types included **`auth_semantic_summary_chunk`** and **`authentication_chunk`**.

**Q3:** Explain the request structure for QR generation.
- Answer covered **source**, **targetUrl**, **request_type**, **parameters** array, **key/value**.
- **`detected_intents`** included **`request_structure_intent`**.
- Top chunk types included **`api_semantic_summary_chunk`**, **`api_table_flattened_chunk`**, **`api_sample_request_chunk`**, **`api_request_parameters_chunk`**.

### Regression
- Authentication question: **`generated`**.
- Error-code question: **`generated`**.
- Success response fields question: **`generated`**.
- **`response_fields_recovered_from_generic`** was **`false`** because structured/semantic chunks now satisfied context directly.

### Demo Stability
- Updated **`scripts/demo_stability_check.py`** to support Step **55** behavior where semantic/structured chunks satisfy response-field questions even when generic recovery is **`false`**.
- **`python scripts/demo_stability_check.py --skip-frontend`** returned **`OVERALL STATUS: DEMO READY`**.
- Full **`pytest`** suite: **33 passed**.

### Closure
- Step **55** semantic enrichment is **closed**.
- Header, token expiry, and request structure retrieval gaps are **resolved**.
- Production QR Util DOCX should be re-ingested through the same cleanup/upload flow when available.
- No architecture, provider, frontend, or API contract redesign was done.

## Step 56 — Demo UX Polish + Retrieval Visualization

### Summary
- Added retrieval visualization and explainability UI without changing backend contracts.
- Added chunk type metadata and semantic category labels.
- Added retrieval journey visualization.
- Added confidence explainability panel.
- Added runtime status banner.
- Added QR demo scenario cards.
- Improved source cards with chunk type badges, prompt-context labels, scores, and provenance hints.

### Files added
- `frontend/src/lib/chunkTypeMeta.ts`
- `frontend/src/lib/diagnosticsHelpers.ts`
- `frontend/src/components/retrieval/ChunkTypeBadge.tsx`
- `frontend/src/components/retrieval/RetrievalJourneyPanel.tsx`
- `frontend/src/components/retrieval/ConfidenceExplainPanel.tsx`
- `frontend/src/components/retrieval/RetrievalMetricsCards.tsx`
- `frontend/src/components/RuntimeStatusBanner.tsx`
- `frontend/src/components/DemoScenarioCards.tsx`

### Files updated
- `frontend/src/components/AppShell.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/pages/RetrievalDiagnosticsPage.tsx`

### Implemented UI sections
- Chat page demo scenario cards.
- Chat page confidence breakdown.
- Chat page expandable “How this answer was generated”.
- Retrieval journey pipeline.
- Retrieval metric cards.
- Source cards with chunk badges and semantic categories.
- Retrieval diagnostics page demo presets.
- Runtime status banner on chat/admin routes.

### Validation
- `npm run build` passed.
- `scripts/demo_smoke_runner.py` passed.
- `scripts/demo_stability_check.py --skip-frontend` returned **OVERALL STATUS: DEMO READY**.

### Closure
- Step **56** is closed.
- Retrieval/provider/backend contracts were not changed.
- Demo UX now exposes retrieval explainability, runtime state, source provenance, and one-click QR scenarios.

## Step 57 — Knowledge Base Governance + Document Lineage

### Summary
- Added **`ingestion_runs`** table and document lineage columns on **`api_documents`** (nullable / default-safe migration).
- Extended **`document_chunks`** with optional **`ingestion_run_id`**.
- Ingestion now creates a run record, stamps **`uploaded_by`**, **`uploaded_at`**, **`embedding_provider`**, **`vector_collection_name`**, **`ingestion_status`**, and **`is_active_document`**; re-upload of the same **`file_name`** in a KB marks the prior active row inactive and sets **`superseded_by_document_id`** (soft governance; vectors not auto-deleted).
- Retrieval excludes inactive documents (vector + keyword paths); diagnostics include **`vector_hits_inactive_document_filtered`** when Qdrant returns inactive chunk rows.
- Query **`sources`** JSON gains **`document_id`**, **`upload_timestamp`**, **`ingestion_run_id`**, **`is_active_document`** (additive fields).
- Admin-safe governance endpoints: deactivate / reactivate / re-index / drop vectors only.
- Document explorer: lineage columns, filters (**active only**, **failed ingestion only**), governance actions when upload is allowed.
- **`pytest.ini`** restricts collection to **`tests/`** (avoids picking up **`app/services/test_data_cleanup_service.py`** as a test module).

### Schema / migration
- **`alembic/versions/f8a1c2d3e4b5_add_ingestion_runs_document_lineage.py`**
- **`ingestion_runs`**: id, knowledge_base_id, started_at, completed_at, uploaded_by, document_count, chunk_count, vector_count, status, embedding_provider, vector_collection.
- **`api_documents`**: ingestion_run_id, uploaded_by, uploaded_at, embedding_provider, vector_collection_name, ingestion_status, superseded_by_document_id, is_active_document (defaults preserve existing rows).

### Key files
- **Backend models**: `app/models/ingestion_run.py`, `app/models/api_document.py`, `app/models/document_chunk.py`, `app/models/knowledge_base.py`, `app/db/base.py`
- **Services**: `app/services/ingestion_service.py`, `app/services/document_governance_service.py`, `app/services/retrieval_service.py`, `app/services/rag_service.py`, `app/services/qdrant_client.py` (**delete_points**)
- **API**: `app/api/v1/endpoints/ingestion.py` (list filters + governance routes)
- **Frontend**: `frontend/src/types/document.ts`, `frontend/src/types/query.ts`, `frontend/src/api/ingestionApi.ts`, `frontend/src/api/documentGovernanceApi.ts`, `frontend/src/pages/DocumentsPage.tsx`, `frontend/src/pages/ChatPage.tsx`
- **Tests**: `pytest.ini`

### Governance endpoints (additive)
- `POST /api/v1/ingestion/documents/{id}/deactivate`
- `POST /api/v1/ingestion/documents/{id}/reactivate`
- `POST /api/v1/ingestion/documents/{id}/reindex`
- `DELETE /api/v1/ingestion/documents/{id}/vectors`

### Validation
- `alembic upgrade head` applied locally.
- **`pytest`**: **33 passed** (with **`pytest.ini`** **`testpaths = tests`**).
- **`npm run build`** (frontend): passed.

### Closure
- Step **57** implementation is complete; live validation is recorded under **Step 57.1**.
- Architecture, retrieval scoring logic, and provider abstraction were **not** redesigned; API responses remain backward-compatible with **additional optional fields**.

## Step 57.1 — Live Validate Document Lineage and Governance

### Automation run (2026-05-12)
- **`python scripts/restart_backend.py`**: OK (PID changed **26700 → 29632**).
- **`python scripts/check_backend_runtime.py`**: OK (**BUILD** **52.0.0-local**, collection **enterprise_api_docs_openai**).
- **`python -m alembic upgrade head`**: OK (already at head).
- **`python -m pytest`**: **33 passed**.
- **`npm run build`** (frontend): OK.
- **`python scripts/demo_smoke_runner.py`**: **OVERALL: PASS**.
- **`python scripts/demo_stability_check.py --skip-frontend`**: **OVERALL STATUS: DEMO READY**.

### API / retrieval / governance (KB **1**, document **42** legacy ingest)
- **Headers question**: Answer included **Authorization** and **TransactionId**; **5** sources; **`vector_hits_inactive_document_filtered`**: **0**.
- **Source provenance keys** present: **`document_id`**, **`upload_timestamp`**, **`is_active_document`**; **`ingestion_run_id`** **null** on pre–Step-57 ingest (expected until same file is re-uploaded under new pipeline).
- **Deactivate**: **`POST .../deactivate`** → retrieval returned **0** sources for the QR headers question.
- **Reactivate**: **`POST .../reactivate`** → sources restored (**5**).
- **Drop vectors + reindex**: **`DELETE .../vectors`** removed **33** points, **`ingestion_status`** became **`vectors_removed`**; **`POST .../reindex`** re-embedded **33** chunks, **`vector_collection_name`** **enterprise_api_docs_openai**.

### Not run in this session
- **Double upload** of the same **QR DOCX** (no **`.docx`** in repo here): operator should repeat upload twice and confirm **version bump**, **`superseded_by_document_id`**, non-null **`ingestion_run_id`** / **`uploaded_by`** on new rows.

### Frontend
- **Documents** / **Chat** UI checks: confirm in browser (lineage columns, filters, governance buttons, expanded source fields).

## Step 58 — Embedding-safe chunk preparation (DOCX / JWT-heavy auth chunks)

### Implemented (code)
- **`app/services/embedding_text_prepare.py`**: JWT / Bearer / KV `access_token` / JSON token fields / long base64-ish runs redacted; paragraph-aware split; prep logging (`original_chars`, `redacted_chars`, `final_chars`, `segments`).
- **`app/core/config.py`**: **`EMBEDDING_INPUT_MAX_CHARS`** default **24000**, **`EMBEDDING_SPLIT_OVERLAP_CHARS`** default **512**.
- **`app/services/embedding_service.py`**: segment embed + average; per-part failure isolation; **`embedding`** **`None`** when all parts fail.
- **`app/services/qdrant_client.py`**: **`upsert_chunks`** returns **`list[str | None]`** aligned with chunks — skips **`None`/empty** embeddings; sample verify ignores **`None`** IDs.
- **`app/services/ingestion_service.py`**: partial **`partial_persisted_with_warnings`**, **`embedding_status`** **`partial_embedding_failed`** when some vectors persist; DB **`qdrant_point_id`** only when point exists.
- **`app/services/document_governance_service.py`**: reindex aligns **`None`** skips; returns **`chunks_embedding_failed`**.
- **Tests**: **`tests/test_embedding_text_prepare.py`** (+ full suite **39 passed**).

### Operator validation (not run in agent session)
- Re-upload **BB Order Service** DOCX; expect **`qdrant_points_created > 0`**, **`vector_embedding_dimension`** **1536** (OpenAI), status **`persisted_ok`** or **`partial_persisted_with_warnings`**; run RAG spot-checks from the Step 58 checklist.

## Step 59 — Request-parameter RAG coverage (mandatory inputs / getAppointment)

### Root cause
- **`_select_prompt_contexts`** used **`max_per_document = 2`** for typical API questions. Large multi-API DOCXs filled the prompt with two early chunks from the same document (overview/metadata), so **`api_request_parameters_chunk`** often never reached the LLM even when retrieval ranked it in top‑K sources.

### Fix (minimal layers)
- **`app/services/rag_service.py`**: For **`parameter_intent`**, sort candidates so **`api_request_parameters_chunk`** (matched **`service_name`** / **`api_reference_id`** in the question) is considered first; relax **`max_per_document`** / **`max_per_api_ref`** / **`max_prompt_chunks`**; skip token-overlap dedupe for **`api_request_parameters_chunk`**; pass **`question`** into selection; extend **`_is_context_insufficient`** / **`_has_intent_supporting_context`** for request-parameter chunks; diagnostics include **`parameter_prompt_prioritization`** and caps.
- **`app/services/query_intent_service.py`**: Broader **`parameter_intent`** phrases (mandatory/required inputs, request parameters, payload, body fields, etc.).
- **`app/services/retrieval_service.py`**: Stronger rerank boosts for **`api_request_parameters_chunk`** when service/API ref match; keyword **`_fallback_score`** bonus; optional **`_promote_matching_request_parameter_chunks`** (rank‑1 pin when intent + match); diagnostic **`request_parameter_chunk_promoted`**.
- **`scripts/debug_getappointment_parameters.py`**: Auth + **`/query/ask`** with **`debug=true`** + SQL chunk inspection for **`document_id` 44**.

### Validation (2026-05-12, agent session)
- **`python scripts/debug_getappointment_parameters.py`**: mandatory-input question → grounded answer; **`parameter_prompt_prioritization: true`**; **`selected_prompt_chunk_count`** **3–4**; smoke/stability **PASS** / **DEMO READY**; regression questions (purpose, slots, token expiry, eucNewOrder) unchanged.

## Next planned step
Further ops / quality follow-ups as needed.

Prior reference — Step 24 — Post-Demo Hardening and Handoff (historical)

Planned focus (historical):
- capture and finalize real demo screenshots from placeholders
- execute dry-run with presenter notes and timing
- package signoff bundle (runbook + script + checklists + freeze notes)
- optional post-demo cleanup and handoff notes

## Known current limitations
- Recruitment workspace is placeholder only
- Admin management UI still placeholder
- Advanced diagnostics export/filtering not implemented
- Document preview not implemented
- Manual UI screenshot capture still pending (placeholders prepared)
- Mac Ollama intermittency remains operational caveat; OpenAI demo path remains stable
- **`demo_smoke_runner.py`** requires a **running API** and valid **admin credentials**; it returns **FAIL** if **Demo Readiness** is **blocked** (by design for demo-day gating)
- Smoke **PDF** check streams only the first chunk; it validates **Content-Type** and **%PDF** header, not full document layout
- **`POST /admin/test-data/cleanup`** is destructive when **`dry_run`** is **false**; defaults preserve demo-seeded feedback/tasks unless **`include_demo_seed`** is **true**; always scoped to a single **`knowledge_base_id`**

## Constraints
- Do not install Ollama on Windows
- Do not use cloud services
- Do not touch Neo4j in Phase 1
- Do not use --reload
- Use existing services/models/routes as source of truth
- Preserve existing parser/chunking/ingestion/retrieval architecture
- Do not redesign architecture
- Do not redesign provider abstraction
- Do not merge OpenAI and Ollama vector collections
- Preserve provider-aware vector dimension handling
