from app.services.query_intent_service import detect_query_intents
from app.services.retrieval_service import RetrievalService


def test_intent_detection_authentication() -> None:
    intents = detect_query_intents("What authentication method and token flow are used?")
    assert "authentication_intent" in intents


def test_intent_detection_error() -> None:
    intents = detect_query_intents("What happens if TimeSlotCategory is invalid return code?")
    assert "error_intent" in intents


def test_intent_detection_async() -> None:
    intents = detect_query_intents("Which APIs are asynchronous?")
    assert "async_intent" in intents


def test_reranking_prefers_auth_chunk() -> None:
    service = RetrievalService()
    candidates = [
        {
            "chunk_type": "authentication_chunk",
            "chunk_text": "Token authentication with OAuth2 Client Credentials Grant and getSSOToken.",
            "vector_score_raw": 0.2,
            "fallback_score_raw": 0.1,
            "score": 0.2,
        },
        {
            "chunk_type": "generic_section_chunk",
            "chunk_text": "General API notes.",
            "vector_score_raw": 0.3,
            "fallback_score_raw": 0.0,
            "score": 0.3,
        },
    ]
    ranked = service._rerank_candidates(
        candidates=candidates,
        question="What authentication method is used?",
        intents=["authentication_intent"],
    )
    assert ranked[0]["chunk_type"] == "authentication_chunk"


def test_reranking_prefers_failed_response_chunk() -> None:
    service = RetrievalService()
    candidates = [
        {
            "chunk_type": "api_sample_failed_response_chunk",
            "chunk_text": "ReturnCode EUC-120074 ReturnMsg The value of TimeSlotCategory is incorrect.",
            "vector_score_raw": 0.15,
            "fallback_score_raw": 0.1,
            "score": 0.15,
        },
        {
            "chunk_type": "api_metadata_chunk",
            "chunk_text": "Service metadata only.",
            "vector_score_raw": 0.2,
            "fallback_score_raw": 0.0,
            "score": 0.2,
        },
    ]
    ranked = service._rerank_candidates(
        candidates=candidates,
        question="What happens if TimeSlotCategory is invalid?",
        intents=["error_intent"],
    )
    assert ranked[0]["chunk_type"] == "api_sample_failed_response_chunk"


def test_promote_moves_matching_request_parameter_chunk_first() -> None:
    svc = RetrievalService()
    candidates = [
        {
            "chunk_type": "api_metadata_chunk",
            "chunk_text": "metadata only",
            "vector_score_raw": 0.9,
            "fallback_score_raw": 0.0,
            "score": 0.9,
        },
        {
            "chunk_type": "api_request_parameters_chunk",
            "chunk_text": "Request Parameters: Name customerId Mandatory Yes",
            "service_name": "getAppointment",
            "api_reference_id": "API-REST-DSE-01",
            "vector_score_raw": 0.12,
            "fallback_score_raw": 0.2,
            "score": 0.12,
        },
    ]
    out = svc._promote_matching_request_parameter_chunks(
        candidates,
        "What are the mandatory inputs for getAppointment?",
        ["parameter_intent"],
    )
    assert out[0]["chunk_type"] == "api_request_parameters_chunk"
    assert svc._last_parameter_promotion_applied is True


def test_reranking_prefers_async_metadata_chunks() -> None:
    service = RetrievalService()
    candidates = [
        {
            "chunk_type": "api_metadata_chunk",
            "chunk_text": "API Reference ID: API-REST-DSE-09 Service Pattern: Asynch callback required.",
            "service_pattern": "Asynch",
            "vector_score_raw": 0.1,
            "fallback_score_raw": 0.1,
            "score": 0.1,
        },
        {
            "chunk_type": "generic_section_chunk",
            "chunk_text": "General notes.",
            "vector_score_raw": 0.3,
            "fallback_score_raw": 0.0,
            "score": 0.3,
        },
    ]
    ranked = service._rerank_candidates(
        candidates=candidates,
        question="Which APIs are asynchronous?",
        intents=["async_intent"],
    )
    assert ranked[0]["chunk_type"] == "api_metadata_chunk"
