# Startup Checklist

- [ ] PostgreSQL is running and `ragdb` is reachable.
- [ ] Qdrant is running and health endpoint responds.
- [ ] Backend started on `http://127.0.0.1:8010` (without `--reload`).
- [ ] Frontend started on `http://localhost:5173`.
- [ ] Provider mode confirmed (`LLM_PROVIDER` and `EMBEDDING_PROVIDER`).
- [ ] Demo users verified (`superadmin@local`, `qa@local`, `hr@local`).
- [ ] KBs verified (API, Product, HR visible to expected users only).
- [ ] Sample documents verified in API/Product/HR KBs.
- [ ] Test query verification completed (API + Product).
- [ ] Fallback verification completed (`fallback_insufficient_context` path).
- [ ] Diagnostics visibility checked for admin/QA only.
- [ ] Upload permission behavior checked (write/admin allowed, read-only denied).
