#!/usr/bin/env python3
"""
Step 50.1 — KB-scoped test data cleanup via admin API.

Calls POST /api/v1/admin/test-data/cleanup (Bearer auth required).

Environment variables:
  CLEANUP_API_BASE_URL   default http://127.0.0.1:8010/api/v1
  CLEANUP_KB_ID          knowledge base id (required)
  CLEANUP_DRY_RUN        true/false (default true)
  CLEANUP_DELETE_DOCUMENTS   default true
  CLEANUP_DELETE_VECTORS     default true
  CLEANUP_DELETE_CHAT_SESSIONS default true
  CLEANUP_DELETE_FEEDBACK    default false
  CLEANUP_DELETE_IMPROVEMENT_TASKS default false
  CLEANUP_INCLUDE_DEMO_SEED    default false
  CLEANUP_DELETE_AUDIT_LOGS    default false
  CLEANUP_JWT            optional bearer token
  CLEANUP_EMAIL          with CLEANUP_PASSWORD if no JWT
  CLEANUP_PASSWORD
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx


def _truthy(raw: str | None, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _auth_headers(base: str, timeout: float) -> tuple[dict[str, str], str | None]:
    jwt = (os.getenv("CLEANUP_JWT") or "").strip()
    if jwt:
        return {"Authorization": f"Bearer {jwt}"}, None
    email = (os.getenv("CLEANUP_EMAIL") or "superadmin@local").strip()
    password = (os.getenv("CLEANUP_PASSWORD") or "").strip()
    if not password:
        return {}, "Set CLEANUP_JWT or CLEANUP_PASSWORD (and optionally CLEANUP_EMAIL)."
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{base.rstrip('/')}/auth/login", json={"email": email, "password": password})
    except httpx.HTTPError as exc:
        return {}, f"Login failed: {exc}"
    if r.status_code != 200:
        return {}, f"Login HTTP {r.status_code}: {r.text[:300]}"
    token = (r.json() or {}).get("access_token")
    if not token:
        return {}, "Login response missing access_token."
    return {"Authorization": f"Bearer {token}"}, None


def main() -> int:
    p = argparse.ArgumentParser(description="Admin test-data cleanup (dry-run by default).")
    p.add_argument("--kb-id", type=int, default=None, help="Knowledge base id (or CLEANUP_KB_ID).")
    p.add_argument("--apply", action="store_true", help="Perform deletes (default is dry-run).")
    args = p.parse_args()

    base = (os.getenv("CLEANUP_API_BASE_URL") or "http://127.0.0.1:8010/api/v1").strip().rstrip("/")
    kb_id = args.kb_id if args.kb_id is not None else int(os.getenv("CLEANUP_KB_ID") or "0")
    if kb_id <= 0:
        print("ERROR: Set CLEANUP_KB_ID or pass --kb-id", file=sys.stderr)
        return 1

    dry_run = not args.apply and _truthy(os.getenv("CLEANUP_DRY_RUN"), True)

    body: dict[str, Any] = {
        "knowledge_base_id": kb_id,
        "delete_documents": _truthy(os.getenv("CLEANUP_DELETE_DOCUMENTS"), True),
        "delete_vectors": _truthy(os.getenv("CLEANUP_DELETE_VECTORS"), True),
        "delete_chat_sessions": _truthy(os.getenv("CLEANUP_DELETE_CHAT_SESSIONS"), True),
        "delete_feedback": _truthy(os.getenv("CLEANUP_DELETE_FEEDBACK"), False),
        "delete_improvement_tasks": _truthy(os.getenv("CLEANUP_DELETE_IMPROVEMENT_TASKS"), False),
        "include_demo_seed": _truthy(os.getenv("CLEANUP_INCLUDE_DEMO_SEED"), False),
        "delete_audit_logs": _truthy(os.getenv("CLEANUP_DELETE_AUDIT_LOGS"), False),
        "dry_run": dry_run,
    }

    headers, err = _auth_headers(base, 30.0)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    url = f"{base}/admin/test-data/cleanup"
    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, headers={**headers, "Content-Type": "application/json"}, json=body)
    except httpx.HTTPError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text[:2000]}

    print(json.dumps(payload, indent=2))
    if r.status_code != 200:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
