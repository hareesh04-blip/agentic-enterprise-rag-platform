# Step 20.3 Demo Readiness Checklist

## Core startup and auth
- [ ] Backend starts on `127.0.0.1:8010` without `--reload`
- [ ] `GET /api/v1/health` returns `200`
- [ ] `POST /api/v1/auth/login` returns bearer token

## Isolation and contracts
- [ ] KB isolation preserved (`knowledge_base_id`-scoped retrieval)
- [ ] RBAC/session behavior unchanged
- [ ] API contracts and response shapes unchanged

## OpenAI provider demo path
- [ ] `llm_provider=openai` and `embedding_provider=openai` in diagnostics
- [ ] API KB query returns `200` with sources and diagnostics
- [ ] Product KB query returns `200` with sources and diagnostics
- [ ] `llm_status=generated` for demo query set
- [ ] Retrieval mode remains vector-oriented (`vector` and/or hybrid-assisted vector)

## Ollama/local fallback path
- [ ] Provider routes to Ollama collection/provider diagnostics
- [ ] Requests return without hang/crash during Mac Ollama intermittency
- [ ] Safe fallback path is visible in diagnostics (`fallback_triggered=true`, `fallback_reason`)
- [ ] Backend remains responsive after timeout scenarios

## Retrieval, diagnostics, and grounding
- [ ] Sources are returned for successful answers
- [ ] Debug diagnostics populated (`debug=true`)
- [ ] Insufficient-context safety behavior is preserved
- [ ] Known weak cases are documented (coverage/content quality)

## Known limitations (current)
- Mac-hosted Ollama can be intermittent from Windows; fallback may dominate during outages.
- Some insufficient-context answers are corpus coverage/content quality issues, not architecture failures.
