# Troubleshooting Checklist

## Frontend not loading
- Verify `npm run dev` is active in `frontend/`.
- Confirm URL `http://localhost:5173`.
- Check `VITE_API_BASE_URL` points to backend API.

## Backend unavailable
- Verify uvicorn process is running on `127.0.0.1:8010`.
- Check backend logs for startup exceptions.
- Confirm PostgreSQL connectivity.

## Auth failures
- Validate demo credentials.
- Confirm JWT settings and system clock are reasonable.
- Re-login to refresh token.

## No KBs visible
- Call `GET /api/v1/knowledge-bases/me` for current user.
- Verify user KB access mappings in `user_knowledge_base_access`.

## Upload failure
- Confirm user has `write/admin` KB access and upload permissions.
- Verify file is valid `.docx`.
- Check backend ingestion logs for parser/vector errors.

## OpenAI key issue
- Verify `OPENAI_API_KEY` is configured and active.
- Ensure provider mode is set to OpenAI before restart.

## Ollama timeout
- Confirm Mac Ollama endpoint is reachable (`OLLAMA_BASE_URL`).
- Retry with configured timeout/retry settings.
- Switch to OpenAI mode for stable demo continuity.

## `embedding_failed`
- Check embedding provider endpoint and model settings.
- Validate Qdrant connection and collection dimension compatibility.

## `generation_retry_failed`
- Check generation provider connectivity.
- Retry query after confirming provider health.
- Use OpenAI mode if Ollama is degraded.

## `fallback_insufficient_context`
- Expected for out-of-domain/insufficient KB content.
- Confirm behavior is consistent and safety banner is shown.

## Empty retrieval
- Verify query KB selection and document coverage.
- Check whether current path is keyword fallback vs vector retrieval.

## Provider mismatch
- Confirm backend env values (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`).
- Restart backend after any provider change.
- Validate via diagnostics/provider badge after one query.
