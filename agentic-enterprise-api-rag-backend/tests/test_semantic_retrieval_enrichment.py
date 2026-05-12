"""Step 55 — semantic retrieval enrichment tests (chunking + reranking intents)."""

from app.services.chunking_service import ApiChunkingService
from app.services.query_intent_service import detect_query_intents
from app.services.retrieval_service import RetrievalService


def test_chunking_emits_semantic_and_flattened_chunk_types() -> None:
    svc = ApiChunkingService()
    parsed_doc = {
        "document_title": "QR Util",
        "purpose_scope": "",
        "logical_sections": [],
        "authentication_preamble": (
            "OAuth 2.0 client credentials. Non-prod access tokens expire in 540 seconds; prod tokens expire in 60 seconds."
        ),
        "apis_full": [
            {
                "api_reference_id": "API-REST-QRU-01",
                "service_name": "QR Checkout URL Endpoint",
                "service_group": "/v1/provisioning/generate-qr",
                "service_description": "Generate QR",
                "service_method": "POST",
                "service_type": "REST",
                "service_pattern": "/v1/provisioning/generate-qr",
                "api_authentication": "Token / Bearer token",
                "header_parameters": [
                    {
                        "param_name": "Authorization",
                        "param_type": "String",
                        "mandatory_optional": "M",
                        "description": "bearer + token from IDP",
                    },
                    {
                        "param_name": "TransactionId",
                        "param_type": "String",
                        "mandatory_optional": "M",
                        "description": "unique correlation id",
                    },
                ],
                "query_parameters": [],
                "api_request_parameters": [
                    {
                        "param_name": "source",
                        "param_type": "String",
                        "mandatory_optional": "M",
                        "description": "client application",
                    },
                    {
                        "param_name": "targetUrl",
                        "param_type": "String",
                        "mandatory_optional": "M",
                        "description": "destination url",
                    },
                    {
                        "param_name": "request_type",
                        "param_type": "String",
                        "mandatory_optional": "M",
                        "description": "operation type",
                    },
                    {
                        "param_name": "parameters",
                        "param_type": "Array",
                        "mandatory_optional": "M",
                        "description": "key/value pairs",
                    },
                    {
                        "param_name": "parameters.key",
                        "param_type": "String",
                        "mandatory_optional": "O",
                        "description": "nested key",
                    },
                    {
                        "param_name": "parameters.value",
                        "param_type": "String",
                        "mandatory_optional": "O",
                        "description": "nested value",
                    },
                ],
                "input_parameters": [],
                "api_response_parameters": [
                    {"param_name": "status", "param_type": "String", "mandatory_optional": "M", "description": "status"},
                    {"param_name": "responseInfo.qrText", "param_type": "String", "mandatory_optional": "O", "description": "qr payload"},
                ],
                "output_response_success": [],
                "error_code_parameters": [{"param_name": "E001", "param_type": "String", "mandatory_optional": "M", "description": "error"}],
                "sample_request": "{}",
                "sample_success_response": "{}",
                "sample_failed_request": None,
                "sample_failed_response": None,
                "raw_text": "",
            }
        ],
    }
    chunks = svc.create_chunks(parsed_doc)
    types = [c["chunk_type"] for c in chunks]
    assert "auth_semantic_summary_chunk" in types
    assert "api_semantic_summary_chunk" in types
    assert types.count("api_table_flattened_chunk") >= 3

    summary = next(c for c in chunks if c["chunk_type"] == "api_semantic_summary_chunk")
    assert "Authorization" in summary["chunk_text"]
    assert "TransactionId" in summary["chunk_text"]
    assert "source" in summary["chunk_text"].lower()
    assert "targeturl" in summary["chunk_text"].lower()

    auth_chunk = next(c for c in chunks if c["chunk_type"] == "auth_semantic_summary_chunk")
    assert "540" in auth_chunk["chunk_text"]
    assert "60" in auth_chunk["chunk_text"]

    flat_header = next(
        c for c in chunks if c["chunk_type"] == "api_table_flattened_chunk" and "Authorization" in c["chunk_text"]
    )
    assert "Required header Authorization" in flat_header["chunk_text"]


def test_natural_language_flatten_preserves_meaning() -> None:
    svc = ApiChunkingService()
    row = {
        "param_name": "Authorization",
        "param_type": "String",
        "mandatory_optional": "M",
        "description": "bearer token",
    }
    line = svc._param_to_natural_language(row, slot="header")
    assert "authorization" in line.lower()
    assert "mandatory" in line.lower()


def test_intent_detection_step55_questions() -> None:
    q1 = "What headers are required while calling the QR generation API?"
    assert "header_parameter_intent" in detect_query_intents(q1)

    q2 = "What is the expiry time for access tokens in PROD vs non-PROD?"
    assert "token_expiry_intent" in detect_query_intents(q2)

    q3 = "Explain the request structure for QR generation."
    assert "request_structure_intent" in detect_query_intents(q3)


def test_rerank_prefers_semantic_summary_for_header_question() -> None:
    svc = RetrievalService()
    candidates = [
        {
            "chunk_type": "api_overview_chunk",
            "chunk_text": "API Reference ID: API-REST-QRU-01 Service Name: QR",
            "vector_score_raw": 0.92,
            "fallback_score_raw": 0.0,
            "score": 0.92,
        },
        {
            "chunk_type": "api_semantic_summary_chunk",
            "chunk_text": (
                "Required Headers:\n- Authorization\n- TransactionId\n"
                "headers required Authorization header TransactionId header"
            ),
            "vector_score_raw": 0.38,
            "fallback_score_raw": 0.0,
            "score": 0.38,
        },
    ]
    ranked = svc._rerank_candidates(
        candidates=candidates,
        question="What headers are required while calling the QR generation API?",
        intents=["header_parameter_intent"],
    )
    assert ranked[0]["chunk_type"] == "api_semantic_summary_chunk"


def test_rerank_prefers_auth_semantic_for_token_expiry_question() -> None:
    svc = RetrievalService()
    candidates = [
        {
            "chunk_type": "authentication_chunk",
            "chunk_text": "General Authentication:\nOAuth",
            "vector_score_raw": 0.85,
            "fallback_score_raw": 0.0,
            "score": 0.85,
        },
        {
            "chunk_type": "auth_semantic_summary_chunk",
            "chunk_text": "Non-prod: 540 seconds\nProd: 60 seconds\naccess token expiry expires_in",
            "vector_score_raw": 0.40,
            "fallback_score_raw": 0.0,
            "score": 0.40,
        },
    ]
    ranked = svc._rerank_candidates(
        candidates=candidates,
        question="What is the expiry time for access tokens in PROD vs non-PROD?",
        intents=["token_expiry_intent"],
    )
    assert ranked[0]["chunk_type"] == "auth_semantic_summary_chunk"
