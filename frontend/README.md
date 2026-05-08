# Agentic Enterprise API RAG Frontend

Enterprise demo UI for role-aware, KB-scoped assistant and document workflows.

## Prerequisites

- Node.js 18+
- Backend running at `http://127.0.0.1:8010` (without `--reload`)
- Seeded users and KB access from backend setup

## Setup and startup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Default frontend URL: `http://127.0.0.1:5173`

Required env:

- `VITE_API_BASE_URL=http://127.0.0.1:8010/api/v1`

## Demo login flow

- Open the frontend login page.
- Sign in with an admin account to verify full workspace visibility (chat, documents, admin).
- Sign in with a limited role account (for example HR/read-only) to verify restricted workspace visibility.
- Confirm only accessible KBs are visible in KB selector and workspace navigation.

## Provider switching note

- LLM/embedding provider switching remains backend-config-driven (`OpenAI` or `Ollama`).
- Frontend provider badge reflects latest provider diagnostics returned by chat responses.
- If fallback status is reported (`fallback_*`), provider badge can display degraded state.

## Troubleshooting

- If login fails, verify backend is running and JWT auth is configured.
- If no KB appears, user likely has no KB access assignment (`GET /knowledge-bases/me` returns empty).
- If chat/documents show authorization errors, verify selected KB access level and role permissions.
- If provider badge does not update, submit one chat query first so diagnostics are captured.

## Validation checklist

- `npm run build` succeeds.
- Admin login shows full workspace/admin navigation.
- Limited login shows only allowed workspace sections.
- Chat remains KB-scoped and operational.
- Documents listing/upload remain permission-aware.
