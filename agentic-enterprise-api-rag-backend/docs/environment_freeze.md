# Environment Freeze Notes

- Recommended demo provider mode:
  - `LLM_PROVIDER=openai`
  - `EMBEDDING_PROVIDER=openai`
- Recommended KBs:
  - API Documentation
  - Product Documentation
  - HR Resume Screening
- Recommended demo accounts:
  - `superadmin@local` (full)
  - `qa@local` (diagnostics-visible)
  - `hr@local` (HR-only)
- Recommended browser:
  - Latest Chrome/Edge (desktop)
- Ports:
  - Frontend: `5173`
  - Backend: `8010`
  - Qdrant: `6333`
  - PostgreSQL: `5432`
- Startup order:
  1. PostgreSQL
  2. Qdrant
  3. Backend
  4. Frontend
- Freeze rule:
  - No architecture changes before demo signoff.
  - Only critical bug fixes and documentation updates are allowed.
