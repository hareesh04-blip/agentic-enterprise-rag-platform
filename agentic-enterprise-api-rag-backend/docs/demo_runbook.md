# Demo Runbook

## Purpose
Operational runbook for Phase-1 enterprise demo execution.

## Required Services
- PostgreSQL (`localhost:5432`)
- Qdrant (`http://localhost:6333`)
- Backend API (`http://127.0.0.1:8010`)
- Frontend (`http://localhost:5173`)
- Optional Ollama endpoint (`http://172.16.111.209:8080`)

## Startup Steps
1. Start PostgreSQL and verify database `ragdb` is reachable.
2. Start Qdrant and verify service responds on port `6333`.
3. Start backend:
   - `cd agentic-enterprise-api-rag-backend`
   - set provider env (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`)
   - `python -m uvicorn app.main:app --host 127.0.0.1 --port 8010`
4. Start frontend:
   - `cd frontend`
   - `npm install` (if needed)
   - `npm run dev`

## Health Checks
- Backend OpenAPI: `http://127.0.0.1:8010/docs`
- Backend health: `http://127.0.0.1:8010/health`
- Frontend: `http://localhost:5173`
- Qdrant health: `http://localhost:6333/healthz`

## Demo Login Credentials
- `superadmin@local` / `SuperAdmin@123` (full platform view)
- `qa@local` / `QaDemo@123` (diagnostics-focused QA role)
- `hr@local` / `HrDemo@123` (HR/basic scoped role)
- `s225_readonly@local` / existing seeded password (read-only behavior validation if needed)

## Provider Switching Steps
1. Stop backend process.
2. Set `.env` or shell values:
   - OpenAI stable demo: `LLM_PROVIDER=openai`, `EMBEDDING_PROVIDER=openai`
   - Ollama local path: `LLM_PROVIDER=ollama`, `EMBEDDING_PROVIDER=ollama`
3. Restart backend.
4. Run one chat query and confirm diagnostics/provider badge values.

## Troubleshooting
- Login fails: verify backend up and JWT settings unchanged.
- No KB visible: verify user KB access mapping via `/knowledge-bases/me`.
- Docs page returns denied: verify role permissions and KB access-level mapping.
- Provider mismatch: check backend env and restart backend.

## Fallback / Recovery
- If Ollama times out, switch to OpenAI provider mode and restart backend.
- If upload demo fails, continue with existing ingested documents and run query/sources demo.
- If diagnostics panel appears empty, run one fresh `debug=true` chat query.
- If frontend session gets stale, logout/login and reselect KB.

## Known Operational Caveats
- Mac-hosted Ollama connectivity can be intermittent.
- OpenAI path is currently the most stable demo route.
- Recruitment/Analytics/Advanced Diagnostics are marked Future Phase placeholders.
