"""
Step 45 — Demo environment smoke runner (read-only).

Checks core demo endpoints and prints a PASS/WARN/FAIL table.
No data mutation, no seed/reset actions.

Also checks: /admin/demo-evidence-pack (schema), /admin/demo-evidence-pack/pdf (PDF header),
/admin/demo-runbook; fails critical if demo readiness overall_status is blocked.

Env:
  DEMO_SMOKE_API_BASE_URL=http://127.0.0.1:8010/api/v1
  DEMO_SMOKE_EMAIL=superadmin@local
  DEMO_SMOKE_PASSWORD=<required when DEMO_SMOKE_JWT is not set>
  DEMO_SMOKE_JWT=<optional bearer token; skips login>
  DEMO_SMOKE_TIMEOUT_SECONDS=20
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class CheckResult:
    name: str
    endpoint: str
    status: str  # PASS | WARN | FAIL
    http_status: int | None
    message: str
    critical: bool


def _base_url() -> str:
    return os.getenv("DEMO_SMOKE_API_BASE_URL", "http://127.0.0.1:8010/api/v1").strip().rstrip("/")


def _timeout_seconds() -> float:
    raw = os.getenv("DEMO_SMOKE_TIMEOUT_SECONDS", "20").strip()
    try:
        val = float(raw)
        if val <= 0:
            return 20.0
        return min(val, 120.0)
    except ValueError:
        return 20.0


def _auth_headers(base_url: str, timeout_s: float) -> tuple[dict[str, str], str | None]:
    jwt = (os.getenv("DEMO_SMOKE_JWT") or "").strip()
    if jwt:
        return {"Authorization": f"Bearer {jwt}"}, None

    email = (os.getenv("DEMO_SMOKE_EMAIL") or "superadmin@local").strip()
    password = (os.getenv("DEMO_SMOKE_PASSWORD") or "").strip()
    if not password:
        return {}, (
            "Auth missing: set DEMO_SMOKE_JWT or DEMO_SMOKE_PASSWORD "
            "(with DEMO_SMOKE_EMAIL, default superadmin@local)."
        )

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(f"{base_url}/auth/login", json={"email": email, "password": password})
    except httpx.TimeoutException:
        return {}, "Auth login timed out."
    except httpx.HTTPError as exc:
        return {}, f"Auth login HTTP error: {exc}"

    if resp.status_code != 200:
        return {}, f"Auth login failed HTTP {resp.status_code}: {resp.text[:200]}"

    token = (resp.json() or {}).get("access_token")
    if not token:
        return {}, "Auth login response missing access_token."
    return {"Authorization": f"Bearer {token}"}, None


def _request_json(
    client: httpx.Client,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> tuple[int | None, Any, str | None]:
    try:
        r = client.request(method, url, headers=headers, json=json_body)
    except httpx.TimeoutException:
        return None, None, "timeout"
    except httpx.HTTPError as exc:
        return None, None, str(exc)

    data: Any = None
    try:
        data = r.json()
    except Exception:
        data = None
    return r.status_code, data, None


def _ok(status: int | None) -> bool:
    return status is not None and 200 <= status < 300


def _add_result(
    results: list[CheckResult],
    *,
    name: str,
    endpoint: str,
    critical: bool,
    status_code: int | None,
    ok_msg: str,
    fail_msg: str,
    warn: bool = False,
) -> None:
    if warn:
        state = "WARN"
        msg = fail_msg
    elif _ok(status_code):
        state = "PASS"
        msg = ok_msg
    else:
        state = "FAIL"
        msg = fail_msg
    results.append(
        CheckResult(
            name=name,
            endpoint=endpoint,
            status=state,
            http_status=status_code,
            message=msg,
            critical=critical,
        )
    )


def _print_results(results: list[CheckResult]) -> None:
    print()
    print("DEMO SMOKE RESULTS")
    print("-" * 120)
    print(f"{'RESULT':<8} {'HTTP':<6} {'CRIT':<5} {'ENDPOINT':<32} MESSAGE")
    print("-" * 120)
    for r in results:
        http_cell = str(r.http_status) if r.http_status is not None else "-"
        crit_cell = "yes" if r.critical else "no"
        print(f"{r.status:<8} {http_cell:<6} {crit_cell:<5} {r.endpoint:<32} {r.message}")
    print("-" * 120)


def _run() -> int:
    base_url = _base_url()
    timeout_s = _timeout_seconds()
    print(f"API_BASE_URL={base_url}")
    print(f"TIMEOUT_SECONDS={timeout_s}")

    headers, auth_error = _auth_headers(base_url, timeout_s)
    if auth_error:
        print(f"FAIL: {auth_error}", file=sys.stderr)
        return 1

    results: list[CheckResult] = []

    with httpx.Client(timeout=timeout_s) as client:
        # 1) Public health
        s, data, err = _request_json(client, "GET", f"{base_url}/health")
        msg = "liveness ok" if _ok(s) else f"{err or 'request failed'}"
        _add_result(
            results,
            name="health",
            endpoint="/health",
            critical=True,
            status_code=s,
            ok_msg=msg,
            fail_msg=f"health failed: {msg}",
        )

        # Admin endpoints
        def admin_get(path: str, critical: bool = True) -> tuple[int | None, Any]:
            status, body, req_err = _request_json(client, "GET", f"{base_url}{path}", headers=headers)
            if req_err:
                _add_result(
                    results,
                    name=path,
                    endpoint=path,
                    critical=critical,
                    status_code=status,
                    ok_msg="",
                    fail_msg=req_err,
                )
                return status, body
            _add_result(
                results,
                name=path,
                endpoint=path,
                critical=critical,
                status_code=status,
                ok_msg="ok",
                fail_msg=f"HTTP {status}",
            )
            return status, body

        readiness_status, readiness = admin_get("/admin/demo-readiness", True)
        admin_get("/status", True)
        admin_get("/admin/demo-script", True)
        demo_data_status_code, demo_data_status = admin_get("/admin/demo-data/status", True)
        kb_status, kb_data = admin_get("/knowledge-bases/me", True)
        admin_get("/feedback/analytics", True)
        admin_get("/audit/logs", True)
        admin_get("/improvements/tasks", True)

        ev_status, ev_body = admin_get("/admin/demo-evidence-pack", True)
        rb_status, rb_body = admin_get("/admin/demo-runbook", True)

        # Evidence pack PDF (stream first bytes; non-critical WARN on mismatch)
        pdf_path = "/admin/demo-evidence-pack/pdf"
        pdf_url = f"{base_url}{pdf_path}"
        try:
            with client.stream("GET", pdf_url, headers=headers, timeout=timeout_s) as pr:
                pdf_code = pr.status_code
                ct = (pr.headers.get("content-type") or "").lower()
                head = b""
                for chunk in pr.iter_bytes():
                    head += chunk
                    if len(head) >= 5:
                        break
                looks_pdf = "application/pdf" in ct and head.startswith(b"%PDF")
                if _ok(pdf_code) and looks_pdf:
                    _add_result(
                        results,
                        name=pdf_path,
                        endpoint=pdf_path,
                        critical=False,
                        status_code=pdf_code,
                        ok_msg="pdf stream ok (content-type + %PDF header)",
                        fail_msg="",
                    )
                elif _ok(pdf_code):
                    _add_result(
                        results,
                        name=pdf_path,
                        endpoint=pdf_path,
                        critical=False,
                        status_code=pdf_code,
                        ok_msg="",
                        fail_msg=f"unexpected pdf response ct={ct!r} head={head[:8]!r}",
                        warn=True,
                    )
                else:
                    _add_result(
                        results,
                        name=pdf_path,
                        endpoint=pdf_path,
                        critical=False,
                        status_code=pdf_code,
                        ok_msg="",
                        fail_msg=f"HTTP {pdf_code}",
                        warn=True,
                    )
        except httpx.TimeoutException:
            _add_result(
                results,
                name=pdf_path,
                endpoint=pdf_path,
                critical=False,
                status_code=None,
                ok_msg="",
                fail_msg="pdf request timed out",
                warn=True,
            )
        except httpx.HTTPError as exc:
            _add_result(
                results,
                name=pdf_path,
                endpoint=pdf_path,
                critical=False,
                status_code=None,
                ok_msg="",
                fail_msg=str(exc),
                warn=True,
            )

        if _ok(ev_status) and isinstance(ev_body, dict):
            required_keys = (
                "generated_at",
                "demo_readiness",
                "demo_script",
                "feedback_analytics",
                "open_improvement_tasks",
                "recent_audit_logs",
            )
            missing = [k for k in required_keys if k not in ev_body]
            if missing:
                results.append(
                    CheckResult(
                        name="evidence_pack_schema",
                        endpoint="/admin/demo-evidence-pack",
                        status="FAIL",
                        http_status=ev_status,
                        message=f"missing keys: {missing}",
                        critical=True,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="evidence_pack_schema",
                        endpoint="/admin/demo-evidence-pack",
                        status="PASS",
                        http_status=ev_status,
                        message="required top-level keys present",
                        critical=False,
                    )
                )

        if _ok(rb_status) and isinstance(rb_body, dict):
            secs = rb_body.get("sections")
            if isinstance(secs, list) and len(secs) >= 4:
                results.append(
                    CheckResult(
                        name="demo_runbook_sections",
                        endpoint="/admin/demo-runbook",
                        status="PASS",
                        http_status=rb_status,
                        message=f"sections count={len(secs)}",
                        critical=False,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="demo_runbook_sections",
                        endpoint="/admin/demo-runbook",
                        status="WARN",
                        http_status=rb_status,
                        message="sections missing or too short",
                        critical=False,
                    )
                )

        # optional diagnostics retrieval if at least one KB exists
        if _ok(kb_status) and isinstance(kb_data, list) and kb_data:
            kb_id = int(kb_data[0].get("id"))
            s, body, err = _request_json(
                client,
                "POST",
                f"{base_url}/diagnostics/retrieval-test",
                headers=headers,
                json_body={
                    "knowledge_base_id": kb_id,
                    "question": "What is this knowledge base about?",
                    "top_k": 3,
                },
            )
            if err:
                _add_result(
                    results,
                    name="retrieval_optional",
                    endpoint="/diagnostics/retrieval-test",
                    critical=False,
                    status_code=s,
                    ok_msg="",
                    fail_msg=f"optional retrieval check failed: {err}",
                    warn=True,
                )
            elif _ok(s):
                n = int((body or {}).get("retrieved_chunk_count") or 0)
                _add_result(
                    results,
                    name="retrieval_optional",
                    endpoint="/diagnostics/retrieval-test",
                    critical=False,
                    status_code=s,
                    ok_msg=f"optional retrieval ok (chunks={n})",
                    fail_msg=f"HTTP {s}",
                )
            else:
                _add_result(
                    results,
                    name="retrieval_optional",
                    endpoint="/diagnostics/retrieval-test",
                    critical=False,
                    status_code=s,
                    ok_msg="",
                    fail_msg=f"optional retrieval returned HTTP {s}",
                    warn=True,
                )
        else:
            _add_result(
                results,
                name="retrieval_optional",
                endpoint="/diagnostics/retrieval-test",
                critical=False,
                status_code=None,
                ok_msg="",
                fail_msg="skipped: no accessible KBs",
                warn=True,
            )

        # Readiness overall: blocked fails the sprint gate; ready/warning only passes
        if _ok(readiness_status) and isinstance(readiness, dict):
            overall = readiness.get("overall_status")
            if overall == "blocked":
                results.append(
                    CheckResult(
                        name="readiness_overall",
                        endpoint="/admin/demo-readiness",
                        status="FAIL",
                        http_status=readiness_status,
                        message="overall_status=blocked (not acceptable for demo day)",
                        critical=True,
                    )
                )
            elif overall in ("ready", "warning"):
                results.append(
                    CheckResult(
                        name="readiness_overall",
                        endpoint="/admin/demo-readiness",
                        status="PASS",
                        http_status=readiness_status,
                        message=f"overall_status={overall}",
                        critical=False,
                    )
                )
            elif overall:
                results.append(
                    CheckResult(
                        name="readiness_overall",
                        endpoint="/admin/demo-readiness",
                        status="WARN",
                        http_status=readiness_status,
                        message=f"unexpected overall_status={overall!r}",
                        critical=False,
                    )
                )
        if _ok(demo_data_status_code) and isinstance(demo_data_status, dict):
            f = demo_data_status.get("seeded_feedback_count", 0)
            t = demo_data_status.get("seeded_task_count", 0)
            a = demo_data_status.get("seeded_audit_count", 0)
            results.append(
                CheckResult(
                    name="demo_data_counts",
                    endpoint="/admin/demo-data/status",
                    status="PASS",
                    http_status=200,
                    message=f"seeded counts feedback={f}, tasks={t}, audit={a}",
                    critical=False,
                )
            )

    _print_results(results)
    critical_fail = any(r.critical and r.status == "FAIL" for r in results)
    print(f"OVERALL: {'FAIL' if critical_fail else 'PASS'}")
    return 1 if critical_fail else 0


def main() -> None:
    try:
        code = _run()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()

