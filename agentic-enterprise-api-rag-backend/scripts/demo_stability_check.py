#!/usr/bin/env python3
"""
Step 54 — Demo Stability Pack: single command to validate demo readiness.

Env (same auth contract as demo_smoke_runner.py):
  DEMO_SMOKE_API_BASE_URL   default http://127.0.0.1:8010/api/v1
  DEMO_SMOKE_EMAIL          default superadmin@local
  DEMO_SMOKE_PASSWORD       required unless DEMO_SMOKE_JWT set
  DEMO_SMOKE_JWT            optional bearer token
  DEMO_SMOKE_TIMEOUT_SECONDS default 20 (HTTP client for health/status/kb; use DEMO_STABILITY_* below for LLM)

  DEMO_STABILITY_PROJECT_ID optional override for POST /query/ask project_id
  DEMO_STABILITY_TIMEOUT_SECONDS  default 120 (POST /query/ask and retrieval-test)
  DEMO_STABILITY_SKIP_FRONTEND    set to 1 to skip frontend checks
  DEMO_STABILITY_RUN_NPM_BUILD    set to 1 to run npm run build (slow)

Exit codes:
  0 — all checks PASS (optional frontend SKIP ok)
  1 — no critical failure, but at least one WARN or non-critical FAIL
  2 — critical failure (backend down, auth, DB, QR gate, etc.)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# Backend repo root (for optional DB project resolution + settings import)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = BACKEND_ROOT.parent / "frontend"

QR_QUESTION_AUTH = "What authentication is required for the QR generation API?"
QR_QUESTION_PARAMS = "What are the request parameters for the QR generation API?"
QR_QUESTION_FIELDS = "What are the success response fields for the QR generation API?"


@dataclass
class LineResult:
    label: str
    status: str  # PASS | FAIL | WARN | SKIP
    detail: str = ""
    critical: bool = False


@dataclass
class RunState:
    lines: list[LineResult] = field(default_factory=list)

    def add(
        self,
        label: str,
        status: str,
        *,
        detail: str = "",
        critical: bool = False,
    ) -> None:
        self.lines.append(LineResult(label=label, status=status, detail=detail, critical=critical))


def _base_url() -> str:
    return os.getenv("DEMO_SMOKE_API_BASE_URL", "http://127.0.0.1:8010/api/v1").strip().rstrip("/")


def _http_timeout() -> float:
    raw = os.getenv("DEMO_SMOKE_TIMEOUT_SECONDS", "20").strip()
    try:
        v = float(raw)
        return min(max(v, 1.0), 120.0)
    except ValueError:
        return 20.0


def _llm_timeout() -> float:
    raw = os.getenv("DEMO_STABILITY_TIMEOUT_SECONDS", "120").strip()
    try:
        v = float(raw)
        return min(max(v, 30.0), 600.0)
    except ValueError:
        return 120.0


def _auth_headers(base_url: str, timeout_s: float) -> tuple[dict[str, str], str | None]:
    jwt = (os.getenv("DEMO_SMOKE_JWT") or "").strip()
    if jwt:
        return {"Authorization": f"Bearer {jwt}"}, None

    email = (os.getenv("DEMO_SMOKE_EMAIL") or "superadmin@local").strip()
    password = (os.getenv("DEMO_SMOKE_PASSWORD") or "").strip()
    if not password:
        return {}, (
            "Set DEMO_SMOKE_JWT or DEMO_SMOKE_PASSWORD (and DEMO_SMOKE_EMAIL if needed), "
            "same as demo_smoke_runner.py."
        )

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(f"{base_url}/auth/login", json={"email": email, "password": password})
    except httpx.TimeoutException:
        return {}, "Login timed out."
    except httpx.HTTPError as exc:
        return {}, f"Login HTTP error: {exc}"

    if resp.status_code != 200:
        return {}, f"Login HTTP {resp.status_code}: {resp.text[:200]}"

    token = (resp.json() or {}).get("access_token")
    if not token:
        return {}, "Login response missing access_token."
    return {"Authorization": f"Bearer {token}"}, None


def _ok(code: int | None) -> bool:
    return code is not None and 200 <= code < 300


def _ensure_backend_import_path() -> None:
    root = str(BACKEND_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _resolve_project_id(kb_id: int) -> tuple[int | None, str | None]:
    override = (os.getenv("DEMO_STABILITY_PROJECT_ID") or "").strip()
    if override.isdigit():
        return int(override), None
    old_cwd = os.getcwd()
    try:
        _ensure_backend_import_path()
        os.chdir(BACKEND_ROOT)
        from sqlalchemy import text

        from app.db.database import SessionLocal

        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT DISTINCT d.project_id
                    FROM api_documents d
                    WHERE d.knowledge_base_id = :kb
                    LIMIT 1
                    """
                ),
                {"kb": kb_id},
            ).mappings().first()
        if row is None or row.get("project_id") is None:
            return None, "No documents for this KB (cannot resolve project_id)."
        return int(row["project_id"]), None
    except Exception as exc:
        return None, f"DB resolve failed ({exc}); set DEMO_STABILITY_PROJECT_ID or run from backend with working DATABASE_URL."
    finally:
        os.chdir(old_cwd)


def _verify_providers(runtime: dict[str, Any]) -> tuple[str, str, bool]:
    """
    Returns (status, message, critical_if_fail).
    Uses local app settings + live runtime providers (must match server when same .env).
    """
    llm = str(runtime.get("llm_provider") or "").strip().lower()
    emb = str(runtime.get("embedding_provider") or "").strip().lower()
    crit = True
    old_cwd = os.getcwd()
    try:
        _ensure_backend_import_path()
        os.chdir(BACKEND_ROOT)
        from app.core.config import settings

        if "openai" in (llm, emb):
            key = (settings.OPENAI_API_KEY or "").strip()
            if not key:
                return "FAIL", "OPENAI_API_KEY not set (required when LLM or embedding uses OpenAI).", crit

        if llm == "ollama":
            base = (settings.OLLAMA_BASE_URL or "").rstrip("/")
            try:
                with httpx.Client(timeout=15.0, trust_env=False) as client:
                    r = client.get(f"{base}/api/tags")
                if r.status_code != 200:
                    return "FAIL", f"Ollama unreachable at {base}/api/tags (HTTP {r.status_code}).", crit
            except httpx.HTTPError as exc:
                return "FAIL", f"Ollama unreachable: {exc}", crit

        return "PASS", "Provider configuration OK.", False
    except Exception as exc:
        return "WARN", f"Could not verify providers via local settings: {exc}", False
    finally:
        os.chdir(old_cwd)


def _vector_collection_line(
    *,
    runtime: dict[str, Any],
    status_payload: dict[str, Any],
) -> tuple[str, str, bool]:
    emb = str(runtime.get("embedding_provider") or "").strip().lower()
    active = runtime.get("active_vector_collection")
    qdrant = status_payload.get("qdrant") or {}
    exists = bool(qdrant.get("collection_exists"))
    name_ok = str(active or "")
    if emb == "openai":
        if name_ok != "enterprise_api_docs_openai":
            return (
                "FAIL",
                f"Expected active collection enterprise_api_docs_openai, got {active!r}.",
                True,
            )
        if not exists:
            return "FAIL", "OpenAI embedding active but Qdrant collection missing.", True
        return "PASS", f"Collection {active} exists.", False
    if emb == "ollama":
        if not name_ok:
            return "FAIL", "Active vector collection unknown.", True
        if not exists:
            return "FAIL", f"Collection {active} not found in Qdrant.", True
        return "PASS", f"Collection {name_ok} exists.", False
    return "WARN", f"Unknown embedding_provider={emb!r}; check manually.", False


def _frontend_check(run_build: bool, skip: bool) -> tuple[str, str]:
    if skip:
        return "SKIP", "skipped"
    if not FRONTEND_ROOT.is_dir():
        return "WARN", f"frontend dir not found at {FRONTEND_ROOT}"
    nm = FRONTEND_ROOT / "node_modules"
    if not nm.is_dir():
        return "WARN", "node_modules missing (run npm install)"
    if not run_build:
        return "PASS", "present (build not requested)"
    try:
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(FRONTEND_ROOT),
            shell=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode == 0:
            return "PASS", "npm run build succeeded"
        tail = (proc.stderr or proc.stdout or "")[-800:]
        return "FAIL", f"npm run build exit {proc.returncode}: {tail}"
    except subprocess.TimeoutExpired:
        return "FAIL", "npm run build timed out"
    except FileNotFoundError:
        return "WARN", "npm not found in PATH"


def _exit_code(state: RunState) -> int:
    crit_fail = any(x.critical and x.status == "FAIL" for x in state.lines)
    if crit_fail:
        return 2
    bad = any(x.status in ("FAIL", "WARN") for x in state.lines)
    if bad:
        return 1
    return 0


def _print_banner(title: str) -> None:
    print(title)


def _print_runtime_summary(rt: dict[str, Any]) -> None:
    print()
    print("Runtime snapshot (from GET /health):")
    print(f"  BUILD_VERSION:            {rt.get('build_version')!s}")
    print(f"  PID:                      {rt.get('process_pid')!s}")
    print(f"  uptime_s:                 {rt.get('backend_uptime_seconds')!s}")
    print(f"  process_start_time:       {rt.get('process_start_time')!s}")
    print(f"  llm_provider:             {rt.get('llm_provider')!s}")
    print(f"  embedding_provider:       {rt.get('embedding_provider')!s}")
    print(f"  active_vector_collection: {rt.get('active_vector_collection')!s}")
    print()


def _overall_label(code: int) -> str:
    if code == 0:
        return "DEMO READY"
    if code == 1:
        return "DEMO DEGRADED (warnings or non-critical failures)"
    return "NOT READY (critical failures)"


def run_checks(*, skip_frontend: bool, run_npm_build: bool) -> int:
    base_url = _base_url()
    http_to = _http_timeout()
    llm_to = _llm_timeout()
    state = RunState()

    # --- Backend / health (no auth)
    try:
        with httpx.Client(timeout=http_to) as client:
            hr = client.get(f"{base_url}/health")
    except Exception as exc:
        state.add("Backend", "FAIL", detail=str(exc), critical=True)
        state.add("Health endpoint", "FAIL", critical=True)
        state.add("Runtime metadata", "FAIL", critical=True)
        _print_banner("================================================\nDEMO STABILITY CHECK\n================================================")
        for x in state.lines:
            d = f" ({x.detail})" if x.detail else ""
            print(f"{x.label}: {x.status}{d}")
        print("================================================")
        print(f"OVERALL STATUS: {_overall_label(2)}")
        print("================================================")
        return 2

    if not _ok(hr.status_code):
        state.add("Backend", "FAIL", detail=f"HTTP {hr.status_code}", critical=True)
        state.add("Health endpoint", "FAIL", detail=f"HTTP {hr.status_code}", critical=True)
    else:
        state.add("Backend", "PASS")
        state.add("Health endpoint", "PASS")

    health_data: dict[str, Any] = {}
    try:
        health_data = hr.json() if hr.content else {}
    except Exception:
        health_data = {}

    rt = health_data.get("runtime") or {}
    if not rt.get("build_version") or rt.get("process_pid") is None:
        state.add("Runtime metadata", "FAIL", detail="missing build_version or process_pid in health.runtime", critical=True)
    else:
        state.add("Runtime metadata", "PASS")

    _print_banner("================================================\nDEMO STABILITY CHECK\n================================================")
    _print_runtime_summary(rt)

    headers, auth_err = _auth_headers(base_url, http_to)
    if auth_err:
        state.add("Authentication", "FAIL", detail=auth_err, critical=True)
    else:
        state.add("Authentication", "PASS")

    status_payload: dict[str, Any] = {}
    if not headers:
        state.add("GET /knowledge-bases/me", "FAIL", detail="not authenticated", critical=True)
        state.add("GET /status", "FAIL", detail="no token", critical=True)
    else:
        try:
            with httpx.Client(timeout=http_to) as client:
                sr = client.get(f"{base_url}/status", headers=headers)
            if _ok(sr.status_code):
                status_payload = sr.json() if sr.content else {}
                state.add("GET /status", "PASS")
            else:
                state.add("GET /status", "FAIL", detail=f"HTTP {sr.status_code}", critical=True)
        except httpx.HTTPError as exc:
            state.add("GET /status", "FAIL", detail=str(exc), critical=True)

    # PostgreSQL / Qdrant from platform status (uses existing service wiring)
    db = status_payload.get("database") or {}
    qd = status_payload.get("qdrant") or {}
    if db.get("status") == "ok":
        state.add("PostgreSQL", "PASS")
    else:
        state.add(
            "PostgreSQL",
            "FAIL",
            detail=str(db.get("message") or "database status not ok"),
            critical=True,
        )

    if qd.get("status") == "ok":
        state.add("Qdrant", "PASS")
    else:
        state.add(
            "Qdrant",
            "FAIL",
            detail=str(qd.get("message") or "qdrant status not ok"),
            critical=True,
        )

    vc_status, vc_detail, _ = _vector_collection_line(runtime=rt, status_payload=status_payload)
    state.add("Vector collection", vc_status, detail=vc_detail, critical=(vc_status == "FAIL"))

    pv, pmsg, _ = _verify_providers(rt)
    state.add("Provider configuration", pv, detail=pmsg, critical=(pv == "FAIL"))

    kb_id: int | None = None
    project_id: int | None = None

    if headers:
        try:
            with httpx.Client(timeout=http_to) as client:
                kr = client.get(f"{base_url}/knowledge-bases/me", headers=headers)
            if _ok(kr.status_code):
                klist = kr.json()
                if isinstance(klist, list) and klist:
                    # Prefer first KB with documents (QR demo content)
                    chosen = None
                    for item in klist:
                        if int(item.get("document_count") or 0) > 0:
                            chosen = item
                            break
                    chosen = chosen or klist[0]
                    kb_id = int(chosen["id"])
                    state.add("GET /knowledge-bases/me", "PASS", detail=f"using KB id={kb_id}")
                else:
                    state.add("GET /knowledge-bases/me", "FAIL", detail="no knowledge bases", critical=True)
            else:
                state.add("GET /knowledge-bases/me", "FAIL", detail=f"HTTP {kr.status_code}", critical=True)
        except httpx.HTTPError as exc:
            state.add("GET /knowledge-bases/me", "FAIL", detail=str(exc), critical=True)

    if kb_id is not None:
        project_id, pres = _resolve_project_id(kb_id)
        if project_id is None:
            state.add("Resolve project_id", "FAIL", detail=pres or "unknown", critical=True)
        else:
            state.add("Resolve project_id", "PASS", detail=str(project_id))

    # retrieval-test + query/ask (need auth + kb + project)
    if headers and kb_id is not None and project_id is not None:
        ask_body_base = {
            "project_id": project_id,
            "knowledge_base_id": kb_id,
            "top_k": 6,
            "debug": True,
        }
        try:
            with httpx.Client(timeout=llm_to) as client:
                rr = client.post(
                    f"{base_url}/diagnostics/retrieval-test",
                    headers=headers,
                    json={
                        "knowledge_base_id": kb_id,
                        "question": "QR generation API overview",
                        "top_k": 6,
                    },
                )
            if _ok(rr.status_code):
                chunks = (rr.json() or {}).get("retrieved_chunk_count")
                state.add("POST /diagnostics/retrieval-test", "PASS", detail=f"chunks={chunks}")
            else:
                state.add(
                    "POST /diagnostics/retrieval-test",
                    "FAIL",
                    detail=f"HTTP {rr.status_code}",
                    critical=True,
                )
        except httpx.HTTPError as exc:
            state.add("POST /diagnostics/retrieval-test", "FAIL", detail=str(exc), critical=True)

        def run_qr_line(label: str, question: str, *, require_recovery: bool) -> None:
            try:
                with httpx.Client(timeout=llm_to) as client:
                    ar = client.post(
                        f"{base_url}/query/ask",
                        headers=headers,
                        json={**ask_body_base, "question": question},
                    )
            except httpx.HTTPError as exc:
                state.add(label, "FAIL", detail=str(exc), critical=True)
                return
            if not _ok(ar.status_code):
                state.add(label, "FAIL", detail=f"HTTP {ar.status_code} {ar.text[:120]!s}", critical=True)
                return
            body = ar.json() or {}
            ls = body.get("llm_status")
            diag = body.get("diagnostics") if isinstance(body.get("diagnostics"), dict) else {}
            recovered = diag.get("response_fields_recovered_from_generic")
            if ls != "generated":
                state.add(label, "FAIL", detail=f"llm_status={ls!r} (want generated)", critical=True)
                return
            if require_recovery and recovered is not True:
                # Step 55+: semantic/structured chunks may satisfy response-field intent without generic_section recovery.
                tops = [str(t).lower() for t in (diag.get("top_chunk_types") or []) if t]
                semantic_ok = any(
                    x in tops
                    for x in (
                        "api_semantic_summary_chunk",
                        "api_response_parameters_chunk",
                        "api_sample_success_response_chunk",
                    )
                )
                if semantic_ok:
                    state.add(label, "PASS", detail="recovery=n/a (semantic/structured context)")
                    return
                state.add(
                    label,
                    "FAIL",
                    detail=f"response_fields_recovered_from_generic={recovered!r} (want true)",
                    critical=True,
                )
                return
            extra = "recovery=true" if require_recovery and recovered is True else ""
            state.add(label, "PASS", detail=extra)

        run_qr_line("QR Util authentication question", QR_QUESTION_AUTH, require_recovery=False)
        run_qr_line("QR Util request-parameters question", QR_QUESTION_PARAMS, require_recovery=False)
        run_qr_line("QR Util response-fields question", QR_QUESTION_FIELDS, require_recovery=True)
    else:
        state.add("POST /diagnostics/retrieval-test", "FAIL", detail="skipped (no KB/project)", critical=True)
        state.add("QR Util authentication question", "FAIL", detail="skipped", critical=True)
        state.add("QR Util request-parameters question", "FAIL", detail="skipped", critical=True)
        state.add("QR Util response-fields question", "FAIL", detail="skipped", critical=True)

    fe_st, fe_msg = _frontend_check(run_npm_build, skip_frontend)
    crit_fe = fe_st == "FAIL" and run_npm_build
    state.add(
        "Frontend build",
        fe_st,
        detail=fe_msg,
        critical=crit_fe,
    )

    print("================================================")
    for x in state.lines:
        d = f" ({x.detail})" if x.detail else ""
        print(f"{x.label}: {x.status}{d}")
    code = _exit_code(state)
    print("================================================")
    print(f"OVERALL STATUS: {_overall_label(code)}")
    print("================================================")
    return code


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Stability Pack (Step 54)")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend presence/build checks.")
    parser.add_argument(
        "--npm-build",
        action="store_true",
        help="Run npm run build in ../frontend (slow).",
    )
    args = parser.parse_args()

    skip_fe = args.skip_frontend or os.getenv("DEMO_STABILITY_SKIP_FRONTEND", "").strip() in ("1", "true", "yes")
    run_build = args.npm_build or os.getenv("DEMO_STABILITY_RUN_NPM_BUILD", "").strip() in ("1", "true", "yes")

    try:
        code = run_checks(skip_frontend=skip_fe, run_npm_build=run_build)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
