"""
Step 29.3 — Retrieval smoke test for diagnostics (no LLM).

Requires admin/super_admin token (retrieval-test endpoint is admin-only).

Env:
  API_BASE_URL=http://127.0.0.1:8010/api/v1
  SMOKE_EMAIL=superadmin@local
  SMOKE_PASSWORD=<password>
  SMOKE_JWT=<optional; skips login when set>
  SMOKE_TOP_K=6

Run from repo backend root:
  python scripts/retrieval_smoke_test.py
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

QUESTIONS_API = [
    "Which API is used to get appointment slots?",
    "What authentication is required for the API?",
    "What are the request parameters?",
]

QUESTIONS_PRODUCT = [
    "What are the main product features?",
    "How do I configure the product?",
    "What workflow should a user follow?",
]

QUESTIONS_HR = [
    "What are the candidate screening criteria?",
    "What skills are mentioned?",
    "What experience is required?",
]

QUESTIONS_BY_DOMAIN: dict[str, list[str]] = {
    "api": QUESTIONS_API,
    "product": QUESTIONS_PRODUCT,
    "hr": QUESTIONS_HR,
}


def _base_url() -> str:
    raw = os.getenv("API_BASE_URL", "http://127.0.0.1:8010/api/v1").strip().rstrip("/")
    return raw


def _top_k() -> int:
    try:
        return max(1, min(20, int(os.getenv("SMOKE_TOP_K", "6"))))
    except ValueError:
        return 6


def _auth_headers() -> dict[str, str]:
    jwt = (os.getenv("SMOKE_JWT") or "").strip()
    if jwt:
        return {"Authorization": f"Bearer {jwt}"}

    email = (os.getenv("SMOKE_EMAIL") or "").strip()
    password = os.getenv("SMOKE_PASSWORD")
    if password is None:
        password = ""
    if not email:
        print("ERROR: Set SMOKE_JWT or both SMOKE_EMAIL and SMOKE_PASSWORD.", file=sys.stderr)
        sys.exit(1)

    base = _base_url()
    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{base}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print(f"ERROR: Login failed HTTP {r.status_code}: {r.text[:500]}", file=sys.stderr)
        sys.exit(1)
    token = r.json().get("access_token")
    if not token:
        print("ERROR: Login response missing access_token.", file=sys.stderr)
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}


def _domain_bank(kb: dict[str, Any]) -> tuple[list[str], str, bool]:
    raw = kb.get("domain_type")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return QUESTIONS_BY_DOMAIN["api"], "api", True
    dt = str(raw).strip().lower()
    if dt not in QUESTIONS_BY_DOMAIN:
        return QUESTIONS_BY_DOMAIN["api"], dt, True
    return QUESTIONS_BY_DOMAIN[dt], dt, False


def _run() -> int:
    base = _base_url()
    headers = _auth_headers()
    top_k = _top_k()

    print(f"API_BASE_URL={base}")
    print(f"SMOKE_TOP_K={top_k}")
    print()

    critical = False

    with httpx.Client(timeout=120.0) as client:
        kr = client.get(f"{base}/knowledge-bases/me", headers=headers)
        if kr.status_code != 200:
            print(f"FAIL: Could not list knowledge bases (HTTP {kr.status_code}).", file=sys.stderr)
            return 1
        kbs: list[dict[str, Any]] = kr.json()
        if not isinstance(kbs, list):
            print("FAIL: Unexpected /knowledge-bases/me response shape.", file=sys.stderr)
            return 1

        if not kbs:
            print("FAIL: No knowledge bases returned for this user.", file=sys.stderr)
            return 1

        kb_summaries: list[tuple[str, int, str]] = []
        tested_count = 0

        for kb in kbs:
            if not kb.get("is_active", True):
                continue
            tested_count += 1

            kb_id = int(kb["id"])
            kb_name = str(kb.get("name") or "(unnamed)")
            questions, domain_label, domain_warn = _domain_bank(kb)

            print("=" * 80)
            print(f"Knowledge base: {kb_name}")
            print(f"  id:           {kb_id}")
            warn_note = ""
            if domain_warn:
                warn_note = (
                    "  [using API question bank — missing or unknown domain_type]"
                    if not kb.get("domain_type")
                    else "  [using API question bank — unrecognized domain_type]"
                )
            print(f"  domain_type:  {domain_label}{warn_note}")
            print("=" * 80)

            kb_has_chunks = False
            kb_http_fail = False

            for question in questions:
                try:
                    resp = client.post(
                        f"{base}/diagnostics/retrieval-test",
                        headers=headers,
                        json={
                            "knowledge_base_id": kb_id,
                            "question": question,
                            "top_k": top_k,
                        },
                    )
                except httpx.HTTPError as exc:
                    print(f"  Q: {question}")
                    print(f"     ERROR: {exc}")
                    critical = True
                    kb_http_fail = True
                    continue

                status_line = ""
                n_chunks = 0
                top_doc = "—"
                top_ct = "—"

                if resp.status_code != 200:
                    detail = resp.text[:300]
                    status_line = f"FAIL (HTTP {resp.status_code})"
                    print(f"  Q: {question}")
                    print(f"     {status_line} {detail}")
                    critical = True
                    kb_http_fail = True
                    continue

                try:
                    data = resp.json()
                except Exception:
                    print(f"  Q: {question}")
                    print("     FAIL (invalid JSON response)")
                    critical = True
                    kb_http_fail = True
                    continue

                n_chunks = int(data.get("retrieved_chunk_count") or 0)
                chunks = data.get("chunks") or []
                if chunks and isinstance(chunks, list):
                    first = chunks[0]
                    if isinstance(first, dict):
                        top_doc = str(first.get("document_name") or "—")
                        top_ct = str(first.get("chunk_type") or "—")

                if n_chunks > 0:
                    status_line = "PASS"
                    kb_has_chunks = True
                else:
                    status_line = "WARN"

                print(f"  Q: {question}")
                print(f"     retrieved_chunk_count: {n_chunks}")
                print(f"     top document name:     {top_doc}")
                print(f"     top chunk type:        {top_ct}")
                print(f"     status:                {status_line}")
                print()

            if kb_http_fail:
                kb_summaries.append((kb_name, kb_id, "FAIL"))
                continue

            if not kb_has_chunks:
                print(f"  >>> KB FAIL: no question returned retrieved_chunk_count > 0")
                print()
                critical = True
                kb_summaries.append((kb_name, kb_id, "FAIL"))
            else:
                kb_summaries.append((kb_name, kb_id, "PASS"))

        if tested_count == 0:
            print("FAIL: No active knowledge bases to test.", file=sys.stderr)
            return 1

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        for name, kid, outcome in kb_summaries:
            print(f"  [{outcome}] {name} (id={kid})")

        overall = "PASS" if not critical else "FAIL"
        print()
        print(f"OVERALL: {overall}")
        return 0 if not critical else 1


def main() -> None:
    try:
        code = _run()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
