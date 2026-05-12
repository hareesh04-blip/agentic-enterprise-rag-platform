# Agentic Enterprise API RAG Backend

## Developer backend lifecycle (Step 53)

From the **backend repo root** (`agentic-enterprise-api-rag-backend`), typical flow on **Windows**:

```powershell
# Start (kills existing listener on 8010 if any)
python scripts/start_backend.py --force-kill

# Health / runtime one-liner (exit 1 if down)
python scripts/check_backend_runtime.py

# Restart and confirm new PID in logs
python scripts/restart_backend.py

# Stop and free 8010
python scripts/stop_backend.py
```

Optional: `scripts/dev_start.ps1` and `scripts/dev_restart.ps1` run the same from **PowerShell** (they `cd` to the backend root). Details and validation notes: **`PROJECT_CONTEXT.md`** (Step 53).

## Demo Stability Pack (Step 54)

End-to-end demo readiness (backend **+** optional frontend build). From the **backend repo root**, with API on **127.0.0.1:8010** and the same **`DEMO_SMOKE_*`** credentials as **`demo_smoke_runner.py`**:

```powershell
python scripts/demo_stability_check.py --skip-frontend
```

Optional: `scripts/demo_ready.ps1`; slow **`npm run build`**: `python scripts/demo_stability_check.py --npm-build`. Exit **0** = **DEMO READY**; see **`PROJECT_CONTEXT.md`** (Step 54) for checks and exit codes.

## Local test note (DOCX ingestion quality)

If `pytest` is not available in your environment, install it first:

```bash
pip install pytest
```

Run the DOCX ingestion quality tests:

```bash
set PYTHONPATH=. && python -m pytest tests/test_docx_ingestion_quality.py -q
```

## Retrieval diagnostics smoke test (Step 29.3)

Runs predefined questions against each accessible KB via `POST /diagnostics/retrieval-test` (admin JWT required). Set `SMOKE_EMAIL` / `SMOKE_PASSWORD` or `SMOKE_JWT`, then:

```bash
python scripts/retrieval_smoke_test.py
```

Optional: `API_BASE_URL`, `SMOKE_TOP_K`. Exit code `0` when each tested KB returns chunks for at least one question; non-zero on auth/list failures, HTTP errors, or no retrieval hits for a KB.
