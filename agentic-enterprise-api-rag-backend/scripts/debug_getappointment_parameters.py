#!/usr/bin/env python3
"""
Step 59 — Diagnostic: mandatory / request-parameter questions vs BB Order Service chunks.

Env:
  DEMO_SMOKE_PASSWORD or DEMO_SMOKE_JWT (same contract as demo_smoke_runner.py)
  DATABASE_URL or load backend .env for DB inspection
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

BASE = (os.getenv("DEMO_SMOKE_API_BASE_URL") or "http://127.0.0.1:8010/api/v1").strip().rstrip("/")
DOCUMENT_ID = int(os.getenv("DEBUG_BB_ORDER_DOCUMENT_ID", "44"))
KB_ID = int(os.getenv("DEBUG_KB_ID", "1"))
PROJECT_ID = int(os.getenv("DEBUG_PROJECT_ID", "1"))


def _auth_headers(client: httpx.Client) -> dict[str, str]:
    jwt = (os.getenv("DEMO_SMOKE_JWT") or "").strip()
    if jwt:
        return {"Authorization": f"Bearer {jwt}"}
    email = (os.getenv("DEMO_SMOKE_EMAIL") or "superadmin@local").strip()
    password = (os.getenv("DEMO_SMOKE_PASSWORD") or "").strip()
    if not password:
        password = "SuperAdmin@123"
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("Login missing access_token")
    return {"Authorization": f"Bearer {token}"}


def _print_ask(client: httpx.Client, headers: dict[str, str], question: str) -> None:
    body = {
        "project_id": PROJECT_ID,
        "knowledge_base_id": KB_ID,
        "question": question,
        "top_k": 10,
        "debug": True,
    }
    r = client.post(f"{BASE}/query/ask", headers=headers, json=body, timeout=180.0)
    print("=" * 80)
    print("Q:", question)
    print("HTTP", r.status_code)
    if r.status_code != 200:
        print(r.text[:1200])
        return
    data = r.json()
    print("answer:", (data.get("answer") or "")[:1200])
    print("llm_status:", data.get("llm_status"))
    print("retrieval_mode:", data.get("retrieval_mode"))
    diag = data.get("diagnostics") or {}
    print("retrieved_chunk_count:", diag.get("retrieved_chunk_count"))
    obs = {k: diag.get(k) for k in ("detected_intents", "request_parameter_chunk_promoted", "top_chunk_types")}
    print("diagnostic_keys_sample:", json.dumps(obs, indent=2))
    prompt_diag = {
        k: diag.get(k)
        for k in (
            "parameter_prompt_prioritization",
            "max_per_document_cap",
            "max_per_api_ref_cap",
            "max_prompt_chunks_cap",
            "selected_prompt_chunk_count",
            "final_prompt_context_chars",
        )
        if k in diag
    }
    if prompt_diag:
        print("prompt_selection:", json.dumps(prompt_diag, indent=2))
    sources = data.get("sources") or []
    print("source_count:", len(sources))
    for i, s in enumerate(sources[:8], start=1):
        print(
            f"  [{i}] doc={s.get('document_id')} chunk_type={s.get('chunk_type')} "
            f"api_ref={s.get('api_reference_id')} service={s.get('service_name')}"
        )
        prev = (s.get("chunk_text") or "")[:220].replace("\n", " ")
        print(f"      preview: {prev}...")

    rd = diag.get("vector_retrieval_diagnostics") or {}
    if rd:
        print(
            "vector_diag:",
            "mode=",
            rd.get("retrieval_mode"),
            "promoted=",
            rd.get("request_parameter_chunk_promoted"),
            "hybrid=",
            rd.get("hybrid_fusion_used"),
        )


def _db_inspect() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("[db] DATABASE_URL not set; skipping SQL inspection")
        return
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT dc.id, dc.chunk_type,
                       LEFT(dc.chunk_text, 400) AS preview,
                       e.service_name, e.api_reference_id
                FROM document_chunks dc
                LEFT JOIN api_endpoints e ON e.id = dc.endpoint_id
                WHERE dc.document_id = :doc_id
                  AND (
                    LOWER(COALESCE(e.service_name, '')) LIKE '%getappointment%'
                    OR LOWER(COALESCE(e.api_reference_id, '')) LIKE '%api-rest-dse-01%'
                  )
                  AND (
                    LOWER(dc.chunk_type) LIKE '%request%'
                    OR LOWER(dc.chunk_type) LIKE '%parameter%'
                  )
                ORDER BY dc.id
                LIMIT 25
                """
            ),
            {"doc_id": DOCUMENT_ID},
        ).mappings().all()
        print("--- DB chunks (service/ref + request/parameter chunk_types) ---")
        for row in rows:
            print(dict(row))
        rows2 = conn.execute(
            text(
                """
                SELECT dc.chunk_type, COUNT(*)::int AS n
                FROM document_chunks dc
                WHERE dc.document_id = :doc_id
                GROUP BY dc.chunk_type
                ORDER BY n DESC
                """
            ),
            {"doc_id": DOCUMENT_ID},
        ).mappings().all()
        print("--- chunk_type histogram ---")
        for row in rows2:
            print(dict(row))


def main() -> int:
    questions = [
        "What are the mandatory inputs for getAppointment?",
        "What request parameters are required for API-REST-DSE-01?",
        "List getAppointment request parameters.",
    ]
    with httpx.Client(timeout=60.0) as client:
        headers = _auth_headers(client)
        for q in questions:
            _print_ask(client, headers, q)
    _db_inspect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
