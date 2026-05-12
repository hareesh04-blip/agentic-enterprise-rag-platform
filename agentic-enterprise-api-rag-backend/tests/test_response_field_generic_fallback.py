"""Step 50.7 — generic_section_chunk fallback when structured response chunks are N/A."""

from app.services.rag_service import RagService
from app.services.retrieval_service import RetrievalService


def test_parameter_prompt_prioritizes_request_parameters_chunk() -> None:
    svc = RagService()
    q = "What are the mandatory inputs for getAppointment?"
    filler = "y" * 200
    results = [
        {"chunk_type": "document_overview_chunk", "chunk_text": filler, "document_id": 44},
        {
            "chunk_type": "api_request_parameters_chunk",
            "chunk_text": "Request Parameters: Name customerId Mandatory Yes\nType string",
            "document_id": 44,
            "service_name": "getAppointment",
            "api_reference_id": "API-REST-DSE-01",
            "score": 0.35,
            "vector_score_raw": 0.35,
        },
    ]
    selected, diag = svc._select_prompt_contexts(
        results=results, top_k=8, detected_intents=["parameter_intent"], question=q
    )
    assert selected[0]["chunk_type"] == "api_request_parameters_chunk"
    assert diag.get("parameter_prompt_prioritization") is True


def test_prompt_selection_prefers_generic_when_structured_na() -> None:
    svc = RagService()
    results = [
        {
            "chunk_type": "api_response_parameters_chunk",
            "chunk_text": "Response Parameters: N/A",
            "score": 0.9,
            "vector_score_raw": 0.9,
        },
        {
            "chunk_type": "generic_section_chunk",
            "chunk_text": (
                "Section Title: Output Response Success\n\n"
                "transactionId correlationId responseInfo qrText errorcode errormsg"
            ),
            "score": 0.5,
            "vector_score_raw": 0.5,
        },
    ]
    selected, _diag = svc._select_prompt_contexts(
        results=results,
        top_k=5,
        detected_intents=["response_field_intent"],
        question="What fields are in the success response?",
    )
    assert selected[0]["chunk_type"] == "generic_section_chunk"


def test_insufficient_context_not_triggered_with_generic_markers() -> None:
    svc = RagService()
    contexts = [
        {
            "chunk_type": "generic_section_chunk",
            "chunk_text": "transactionId x correlationId y responseInfo z",
        }
    ]
    question = "What are the success response fields for the QR generation API?"
    assert not svc._is_context_insufficient(
        question=question,
        contexts=contexts,
        detected_intents=["response_field_intent"],
    )


def test_recovered_flag_when_only_generic_supports_fields() -> None:
    svc = RagService()
    contexts = [
        {"chunk_type": "api_response_parameters_chunk", "chunk_text": "Response Parameters: N/A"},
        {
            "chunk_type": "generic_section_chunk",
            "chunk_text": "transactionId a correlationId b responseInfo c",
        },
    ]
    out, recovered = svc._annotate_recovered_response_chunks(contexts, ["response_field_intent"])
    assert recovered is True
    generic_row = next(x for x in out if x.get("chunk_type") == "generic_section_chunk")
    assert "Recovered Response Parameters" in (generic_row.get("chunk_text") or "")


def test_reranking_prefers_generic_section_over_na_response_chunks() -> None:
    service = RetrievalService()
    candidates = [
        {
            "chunk_type": "api_response_parameters_chunk",
            "chunk_text": "Response Parameters: N/A",
            "vector_score_raw": 0.95,
            "fallback_score_raw": 0.0,
            "score": 0.95,
        },
        {
            "chunk_type": "generic_section_chunk",
            "chunk_text": (
                "transactionId correlationId responseInfo qrText errorcode errormsg status code desc timestamp"
            ),
            "vector_score_raw": 0.4,
            "fallback_score_raw": 0.0,
            "score": 0.4,
        },
    ]
    ranked = service._rerank_candidates(
        candidates=candidates,
        question="What are the success response fields?",
        intents=["response_field_intent"],
    )
    assert ranked[0]["chunk_type"] == "generic_section_chunk"
