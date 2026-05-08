from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

INSUFFICIENT_CONTEXT_TEXT = "I could not find enough information in the selected knowledge base to answer this confidently."

DEMO_QUERY_SET: list[dict[str, Any]] = [
    {"id": "api_lookup_01", "kb": 1, "type": "api_lookup", "question": "API-REST-NOK-01 endpoint details"},
    {"id": "api_lookup_02", "kb": 1, "type": "api_lookup", "question": "API-REST-SAC-01 method and pattern"},
    {"id": "api_workflow_01", "kb": 1, "type": "api_workflow", "question": "Explain the integration flow for order service."},
    {"id": "api_workflow_02", "kb": 1, "type": "api_workflow", "question": "How can I submit order creation request?"},
    {"id": "product_workflow_01", "kb": 2, "type": "product_workflow", "question": "How do users start a new claim in Claims Portal?"},
    {"id": "product_workflow_02", "kb": 2, "type": "product_workflow", "question": "How do I configure notifications in Claims Portal workflow?"},
    {"id": "product_howto_01", "kb": 2, "type": "product_howto", "question": "Where is Claims Portal test doc section guidance?"},
    {"id": "product_howto_02", "kb": 2, "type": "product_howto", "question": "Workflow to validate order before submission"},
    {"id": "mixed_semantic_01", "kb": 1, "type": "mixed_semantic", "question": "Which API is used for claims portal order update flow?"},
    {"id": "mixed_semantic_02", "kb": 2, "type": "mixed_semantic", "question": "Claims Portal API integration prerequisites"},
    {"id": "mixed_semantic_03", "kb": 2, "type": "mixed_semantic", "question": "Section title for notifications in product docs"},
    {
        "id": "insufficient_context_01",
        "kb": 2,
        "type": "insufficient_context",
        "question": "What is the Kubernetes HPA YAML and Helm chart for Claims Portal deployment?",
        "expect_insufficient": True,
    },
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step 20.3 demo readiness validation")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="Backend base URL")
    parser.add_argument("--email", default="superadmin@local", help="Login email")
    parser.add_argument("--password", default="SuperAdmin@123", help="Login password")
    parser.add_argument("--project-id", type=int, default=1, help="Project ID for query/ask")
    parser.add_argument(
        "--expected-provider",
        choices=["openai", "ollama", "any"],
        default="any",
        help="Optional provider expectation for diagnostics checks",
    )
    parser.add_argument(
        "--output-json",
        default="scripts/step20_3_demo_validation_report.json",
        help="Path to write JSON report",
    )
    parser.add_argument("--max-queries", type=int, default=0, help="Optional limit for number of queries to run (0 = all)")
    parser.add_argument("--query-timeout", type=float, default=180.0, help="Query ask timeout seconds")
    return parser.parse_args()


def _health_check(client: httpx.Client, base_api: str) -> dict[str, Any]:
    response = client.get(f"{base_api}/health", timeout=20)
    return {"status_code": response.status_code, "body": response.json() if response.status_code == 200 else response.text}


def _login(client: httpx.Client, base_api: str, email: str, password: str) -> dict[str, Any]:
    response = client.post(
        f"{base_api}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if response.status_code != 200:
        return {"status_code": response.status_code, "error": response.text}
    payload = response.json()
    return {"status_code": response.status_code, "access_token": payload.get("access_token"), "user": payload.get("user")}


def _run_query(
    client: httpx.Client,
    base_api: str,
    token: str,
    project_id: int,
    query: dict[str, Any],
    query_timeout: float,
) -> dict[str, Any]:
    try:
        response = client.post(
            f"{base_api}/query/ask",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": project_id,
                "knowledge_base_id": query["kb"],
                "question": query["question"],
                "top_k": 5,
                "debug": True,
            },
            timeout=query_timeout,
        )
    except Exception as exc:
        return {
            "id": query["id"],
            "type": query["type"],
            "knowledge_base_id": query["kb"],
            "question": query["question"],
            "http_status": None,
            "passed": False,
            "error": f"{exc.__class__.__name__}: {exc}",
        }
    if response.status_code != 200:
        return {
            "id": query["id"],
            "type": query["type"],
            "knowledge_base_id": query["kb"],
            "question": query["question"],
            "http_status": response.status_code,
            "passed": False,
            "error": response.text,
        }

    body = response.json()
    diagnostics = body.get("diagnostics") or {}
    answer = body.get("answer") or ""
    sources = body.get("sources") or []
    expect_insufficient = bool(query.get("expect_insufficient"))
    insufficient_match = answer.strip() == INSUFFICIENT_CONTEXT_TEXT

    query_passed = (
        isinstance(sources, list)
        and "retrieval_mode" in body
        and "llm_status" in body
        and isinstance(diagnostics, dict)
        and (insufficient_match if expect_insufficient else True)
    )

    return {
        "id": query["id"],
        "type": query["type"],
        "knowledge_base_id": query["kb"],
        "question": query["question"],
        "http_status": 200,
        "passed": query_passed,
        "retrieval_mode": body.get("retrieval_mode"),
        "llm_status": body.get("llm_status"),
        "source_count": len(sources),
        "answer_chars": len(answer.strip()),
        "insufficient_expected": expect_insufficient,
        "insufficient_matched": insufficient_match,
        "diagnostics": {
            "llm_provider": diagnostics.get("llm_provider"),
            "embedding_provider": diagnostics.get("embedding_provider"),
            "vector_collection_name": diagnostics.get("vector_collection_name"),
            "vector_results_count": diagnostics.get("vector_results_count"),
            "fallback_triggered": diagnostics.get("fallback_triggered"),
            "fallback_reason": diagnostics.get("fallback_reason"),
            "hybrid_fusion_used": diagnostics.get("hybrid_fusion_used"),
            "retrieved_chunk_count": diagnostics.get("retrieved_chunk_count"),
            "selected_prompt_chunk_count": diagnostics.get("selected_prompt_chunk_count"),
            "dedup_chunks_removed": diagnostics.get("dedup_chunks_removed"),
            "diversity_caps_applied": diagnostics.get("diversity_caps_applied"),
        },
    }


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    base_api = f"{args.base_url.rstrip('/')}/api/v1"
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_queries = DEMO_QUERY_SET[: args.max_queries] if args.max_queries and args.max_queries > 0 else DEMO_QUERY_SET

    with httpx.Client() as client:
        health = _health_check(client, base_api)
        login = _login(client, base_api, args.email, args.password)

        query_results: list[dict[str, Any]] = []
        if login.get("access_token"):
            token = str(login["access_token"])
            for query in selected_queries:
                query_results.append(_run_query(client, base_api, token, args.project_id, query, args.query_timeout))

    retrieval_counter = Counter(x.get("retrieval_mode") for x in query_results if x.get("retrieval_mode"))
    llm_status_counter = Counter(x.get("llm_status") for x in query_results if x.get("llm_status"))
    fallback_count = sum(1 for x in query_results if x.get("diagnostics", {}).get("fallback_triggered"))
    hybrid_count = sum(1 for x in query_results if x.get("diagnostics", {}).get("hybrid_fusion_used"))
    query_pass_count = sum(1 for x in query_results if x.get("passed"))

    observed_llm_provider = next(
        (x.get("diagnostics", {}).get("llm_provider") for x in query_results if x.get("diagnostics", {}).get("llm_provider")),
        None,
    )
    observed_embedding_provider = next(
        (
            x.get("diagnostics", {}).get("embedding_provider")
            for x in query_results
            if x.get("diagnostics", {}).get("embedding_provider")
        ),
        None,
    )
    provider_expected_ok = (
        args.expected_provider == "any"
        or (
            observed_llm_provider == args.expected_provider
            and observed_embedding_provider == args.expected_provider
        )
    )

    checks = {
        "backend_health_ok": health.get("status_code") == 200,
        "login_ok": login.get("status_code") == 200 and bool(login.get("access_token")),
        "api_kb_query_ok": any(x.get("knowledge_base_id") == 1 and x.get("passed") for x in query_results),
        "product_kb_query_ok": any(x.get("knowledge_base_id") == 2 and x.get("passed") for x in query_results),
        "diagnostics_populated": all(isinstance(x.get("diagnostics"), dict) for x in query_results) if query_results else False,
        "sources_returned": all((x.get("source_count") or 0) >= 0 for x in query_results),
        "insufficient_context_safety_ok": all(
            (not x.get("insufficient_expected")) or x.get("insufficient_matched")
            for x in query_results
        )
        if query_results
        else False,
        "provider_expectation_ok": provider_expected_ok,
    }
    overall_pass = all(checks.values()) and (query_pass_count == len(query_results)) and bool(query_results)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "expected_provider": args.expected_provider,
        "observed_provider": {
            "llm_provider": observed_llm_provider,
            "embedding_provider": observed_embedding_provider,
        },
        "health": health,
        "login": {
            "status_code": login.get("status_code"),
            "user": login.get("user"),
            "token_obtained": bool(login.get("access_token")),
        },
        "query_set": [{"id": q["id"], "type": q["type"], "knowledge_base_id": q["kb"], "question": q["question"]} for q in selected_queries],
        "summary": {
            "query_total": len(query_results),
            "query_passed": query_pass_count,
            "retrieval_mode_counts": dict(retrieval_counter),
            "llm_status_counts": dict(llm_status_counter),
            "fallback_count": fallback_count,
            "hybrid_fusion_count": hybrid_count,
            "overall_pass": overall_pass,
        },
        "checks": checks,
        "results": query_results,
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    args = _parse_args()
    report = run_validation(args)
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["checks"], indent=2))


if __name__ == "__main__":
    main()
