from __future__ import annotations

import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8010/api/v1"
FRONTEND = "http://localhost:5173"

results: list[dict[str, object]] = []


def rec(name: str, ok: bool, detail: str) -> None:
    results.append({"check": name, "ok": ok, "detail": detail})


def login(email: str, password: str):
    response = requests.post(
        f"{BASE}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if response.status_code != 200:
        return None, response
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{BASE}/auth/me", headers=headers, timeout=30)
    return {"headers": headers, "me": me.json()}, response


def ask(headers: dict[str, str], kb_id: int, question: str):
    return requests.post(
        f"{BASE}/query/ask",
        headers=headers,
        json={
            "project_id": 1,
            "knowledge_base_id": kb_id,
            "question": question,
            "top_k": 5,
            "debug": True,
        },
        timeout=60,
    )


def main() -> None:
    # Service health
    backend_health = requests.get("http://127.0.0.1:8010/api/v1/health", timeout=20)
    rec("backend_health", backend_health.status_code == 200, f"status={backend_health.status_code}")

    frontend_health = requests.get(FRONTEND, timeout=20)
    rec("frontend_health", frontend_health.status_code == 200, f"status={frontend_health.status_code}")

    admin, admin_login = login("superadmin@local", "SuperAdmin@123")
    rec("admin_login", admin is not None, f"status={admin_login.status_code}")
    if not admin:
        print(json.dumps(results, indent=2))
        return

    kbs_response = requests.get(f"{BASE}/knowledge-bases/me", headers=admin["headers"], timeout=30)
    kbs = kbs_response.json() if kbs_response.ok else []
    kb_by_name = {kb["name"]: kb for kb in kbs}
    rec("admin_kbs_loaded", kbs_response.status_code == 200 and len(kbs) >= 3, f"count={len(kbs)}")

    api_kb = kb_by_name.get("API Documentation")
    product_kb = kb_by_name.get("Product Documentation")
    hr_kb = kb_by_name.get("HR Resume Screening")
    rec("required_kbs_present", bool(api_kb and product_kb and hr_kb), f"api={bool(api_kb)} product={bool(product_kb)} hr={bool(hr_kb)}")

    # OpenAI provider demo query
    if product_kb:
        openai_query = ask(admin["headers"], int(product_kb["id"]), "What is Claims Portal?")
        ok = openai_query.status_code == 200
        data = openai_query.json() if ok else {}
        provider = str((data.get("diagnostics") or {}).get("llm_provider", "n/a"))
        rec("openai_provider_demo_query", ok and provider == "openai", f"status={openai_query.status_code} llm_provider={provider}")

    # Insufficient context query
    if api_kb:
        insuf = ask(admin["headers"], int(api_kb["id"]), "Explain our quantum wormhole banana protocol internals.")
        ok = insuf.status_code == 200
        llm_status = insuf.json().get("llm_status") if ok else "n/a"
        rec("insufficient_context_query", ok and llm_status == "fallback_insufficient_context", f"status={insuf.status_code} llm_status={llm_status}")

    # Upload flow verification (admin)
    upload_file = Path("claims_portal_test.docx")
    if upload_file.exists() and product_kb:
        with upload_file.open("rb") as fh:
            response = requests.post(
                f"{BASE}/ingestion/ingest-docx",
                headers=admin["headers"],
                data={
                    "project_id": "1",
                    "knowledge_base_id": str(product_kb["id"]),
                    "document_type": "product",
                    "product_name": "Claims Portal",
                    "source_domain": "demo.local",
                    "version": "step23-demo",
                },
                files={"file": (upload_file.name, fh, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                timeout=120,
            )
        rec("document_upload_flow", response.status_code == 200, f"status={response.status_code}")
    else:
        rec("document_upload_flow", False, "claims_portal_test.docx missing or Product KB unavailable")

    # QA walkthrough
    qa, qa_login = login("qa@local", "QaDemo@123")
    rec("qa_login", qa is not None, f"status={qa_login.status_code}")
    if qa:
        qa_roles = qa["me"].get("roles", [])
        qa_permissions = qa["me"].get("permissions", [])
        qa_has_diagnostics = ("admin.read" in qa_permissions) or any(r in ["qa", "tester", "admin", "super_admin"] for r in qa_roles)
        rec("qa_diagnostics_visibility", qa_has_diagnostics, f"roles={qa_roles} perms={qa_permissions}")
        qa_kbs_resp = requests.get(f"{BASE}/knowledge-bases/me", headers=qa["headers"], timeout=30)
        qa_kbs = [kb.get("name") for kb in qa_kbs_resp.json()] if qa_kbs_resp.ok else []
        rec("qa_kb_scope", qa_kbs_resp.status_code == 200 and "HR Resume Screening" not in qa_kbs, f"kbs={qa_kbs}")

    # HR walkthrough
    hr, hr_login = login("hr@local", "HrDemo@123")
    rec("hr_login", hr is not None, f"status={hr_login.status_code}")
    if hr:
        hr_roles = hr["me"].get("roles", [])
        hr_permissions = hr["me"].get("permissions", [])
        hr_has_diagnostics = ("admin.read" in hr_permissions) or any(r in ["qa", "tester", "admin", "super_admin"] for r in hr_roles)
        rec("hr_diagnostics_hidden", not hr_has_diagnostics, f"roles={hr_roles} perms={hr_permissions}")
        hr_has_admin = any(r in ["admin", "super_admin", "platform_admin"] for r in hr_roles)
        rec("hr_admin_hidden", not hr_has_admin, f"roles={hr_roles}")
        hr_kbs_resp = requests.get(f"{BASE}/knowledge-bases/me", headers=hr["headers"], timeout=30)
        hr_kbs = [kb.get("name") for kb in hr_kbs_resp.json()] if hr_kbs_resp.ok else []
        rec("hr_kb_only_hr", hr_kbs == ["HR Resume Screening"], f"kbs={hr_kbs}")

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
