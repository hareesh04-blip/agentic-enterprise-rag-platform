from io import BytesIO

from docx import Document

from app.services.chunking_service import create_document_chunks
from app.services.docx_parser_service import docx_parser_service


def _build_sample_docx_bytes() -> bytes:
    doc = Document()
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph(
        "This document details the information that is required to Process Broadband Order requests from ISOTON to DSE through Application."
    )
    doc.add_heading("API-REST-DSE-01", level=1)
    table = doc.add_table(rows=9, cols=2)
    rows = [
        ("Service Name", "getAppointment"),
        ("Service Group", "broadband"),
        ("Service Description", "To get the list of valid appointment slots when NLT appointment is required."),
        ("Service Method", "POST"),
        ("Service Pattern", "/appointments/get"),
        ("API Authentication", "Bearer"),
        ("API Gateway", "DSE"),
        ("Source", "BB Order Service"),
        ("Sample Request", '{"customerId":"123"}'),
    ]
    for idx, (k, v) in enumerate(rows):
        table.rows[idx].cells[0].text = k
        table.rows[idx].cells[1].text = v

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()


def test_docx_extraction_includes_table_metadata() -> None:
    parsed = docx_parser_service.parse_preview("sample.docx", _build_sample_docx_bytes())
    api = next((item for item in parsed["apis_full"] if item.get("api_reference_id") == "API-REST-DSE-01"), None)
    assert api is not None
    assert api.get("service_name") == "getAppointment"
    assert "appointment slots" in (api.get("service_description") or "").lower()


def test_purpose_of_document_chunk_created() -> None:
    parsed = docx_parser_service.parse_preview("sample.docx", _build_sample_docx_bytes())
    chunks = create_document_chunks(parsed, document_type="api")
    overview = next((chunk for chunk in chunks if chunk.get("chunk_type") == "document_overview_chunk"), None)
    assert overview is not None
    assert "This document details the information that is required to Process Broadband Order requests" in (
        overview.get("chunk_text") or ""
    )


def test_api_reference_chunk_contains_service_name() -> None:
    parsed = docx_parser_service.parse_preview("sample.docx", _build_sample_docx_bytes())
    chunks = create_document_chunks(parsed, document_type="api")
    metadata_chunk = next(
        (
            chunk
            for chunk in chunks
            if chunk.get("chunk_type") == "api_metadata_chunk"
            and "API Reference ID: API-REST-DSE-01" in (chunk.get("chunk_text") or "")
        ),
        None,
    )
    assert metadata_chunk is not None
    assert "Service Name: getAppointment" in (metadata_chunk.get("chunk_text") or "")
