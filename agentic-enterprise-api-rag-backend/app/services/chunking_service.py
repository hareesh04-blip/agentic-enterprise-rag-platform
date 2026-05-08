from __future__ import annotations

from typing import Any


class ApiChunkingService:
    def create_chunks(self, parsed_doc: dict[str, Any]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        document_title = parsed_doc.get("document_title")
        purpose_scope = parsed_doc.get("purpose_scope")
        logical_sections = parsed_doc.get("logical_sections") or []
        apis = parsed_doc.get("apis_full", [])

        overview_lines = []
        if document_title:
            overview_lines.append(f"Document Title: {document_title}")
        if purpose_scope:
            overview_lines.append(f"Purpose of Document: {purpose_scope}")
        intro_section = next(
            (
                section
                for section in logical_sections
                if "introduction" in (section.get("section_title") or "").lower()
                and (section.get("content") or "").strip()
            ),
            None,
        )
        if intro_section:
            overview_lines.append(f"Introduction: {intro_section.get('content')}")
        if overview_lines:
            overview_text = (
                "\n".join(overview_lines).strip()
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="document_overview_chunk",
                    chunk_text=overview_text,
                    metadata={},
                )
            )

        auth_entries = [
            api
            for api in apis
            if api.get("api_authentication") or api.get("service_swagger")
        ]
        if auth_entries:
            auth_lines = []
            for entry in auth_entries:
                auth_lines.append(
                    f"{entry.get('api_reference_id')}: auth={entry.get('api_authentication') or 'N/A'}, "
                    f"swagger={entry.get('service_swagger') or 'N/A'}"
                )
            chunks.append(
                self._build_chunk(
                    chunk_type="authentication_chunk",
                    chunk_text="\n".join(auth_lines),
                    metadata={},
                )
            )

        for api in apis:
            metadata = self._metadata_for_api(api)
            api_reference_id = api.get("api_reference_id") or "N/A"
            service_name = api.get("service_name") or "Unknown Service"
            header = self._api_chunk_header(api_reference_id, service_name, "API Overview")

            overview_text = (
                f"{header}\n"
                f"Service Group: {api.get('service_group') or 'N/A'}\n"
                f"Service Description: {api.get('service_description') or 'N/A'}\n"
                f"Source: {api.get('source') or 'N/A'}\n"
                f"Service Type: {api.get('service_type') or 'N/A'}\n"
                f"Service Pattern: {api.get('service_pattern') or 'N/A'}\n"
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_overview_chunk",
                    chunk_text=overview_text,
                    metadata=metadata,
                )
            )

            metadata_text = (
                f"{self._api_chunk_header(api_reference_id, service_name, 'API Metadata')}\n"
                f"Service Group: {api.get('service_group') or 'N/A'}\n"
                f"Service Description: {api.get('service_description') or 'N/A'}\n"
                f"Service Method: {api.get('service_method') or 'N/A'}\n"
                f"Service Type: {api.get('service_type') or 'N/A'}\n"
                f"Service Pattern: {api.get('service_pattern') or 'N/A'}\n"
                f"Service Max Timeout: {api.get('service_max_timeout') or 'N/A'}\n"
                f"API Authentication: {api.get('api_authentication') or 'N/A'}\n"
                f"API Gateway: {api.get('api_gateway') or 'N/A'}\n"
                f"Service URL: {api.get('service_url') or 'N/A'}\n"
                f"Swagger URL: {api.get('service_swagger') or 'N/A'}\n"
                f"Source: {api.get('source') or 'N/A'}\n"
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_metadata_chunk",
                    chunk_text=metadata_text,
                    metadata=metadata,
                )
            )

            request_params = api.get("api_request_parameters") or api.get("input_parameters", [])
            response_params = api.get("api_response_parameters") or api.get("output_response_success", [])
            request_text = (
                f"{self._api_chunk_header(api_reference_id, service_name, 'API Request Parameters')}\n"
                f"Method: {api.get('service_method') or 'N/A'}\n"
                f"Service Pattern: {api.get('service_pattern') or 'N/A'}\n"
                f"Header Parameters: {self._render_params(api.get('header_parameters', []))}\n"
                f"Request Parameters: {self._render_params(request_params)}\n"
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_request_parameters_chunk",
                    chunk_text=request_text,
                    metadata=metadata,
                )
            )

            response_text = (
                f"{self._api_chunk_header(api_reference_id, service_name, 'API Response Parameters')}\n"
                f"Response Parameters: {self._render_params(response_params)}"
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_response_parameters_chunk",
                    chunk_text=response_text,
                    metadata=metadata,
                )
            )

            chunks.append(
                self._build_chunk(
                    chunk_type="api_sample_request_chunk",
                    chunk_text=(
                        f"{self._api_chunk_header(api_reference_id, service_name, 'API Sample Request')}\n"
                        f"Sample Request: {api.get('sample_request') or api.get('sample_initial') or 'N/A'}"
                    ),
                    metadata=metadata,
                )
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_sample_success_response_chunk",
                    chunk_text=(
                        f"{self._api_chunk_header(api_reference_id, service_name, 'API Sample Success Response')}\n"
                        f"Sample Success Response: {api.get('sample_success_response') or api.get('sample_token_exist') or 'N/A'}"
                    ),
                    metadata=metadata,
                )
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_sample_failed_request_chunk",
                    chunk_text=(
                        f"{self._api_chunk_header(api_reference_id, service_name, 'API Sample Failed Request')}\n"
                        f"Sample Failed Request: {api.get('sample_failed_request') or 'N/A'}"
                    ),
                    metadata=metadata,
                )
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_sample_failed_response_chunk",
                    chunk_text=(
                        f"{self._api_chunk_header(api_reference_id, service_name, 'API Sample Failed Response')}\n"
                        f"Sample Failed Response: {api.get('sample_failed_response') or 'N/A'}"
                    ),
                    metadata=metadata,
                )
            )

            if api.get("raw_text"):
                chunks.append(
                    self._build_chunk(
                        chunk_type="generic_section_chunk",
                        chunk_text=f"{self._api_chunk_header(api_reference_id, service_name, 'Generic Section')}\n{api['raw_text']}",
                        metadata=metadata,
                    )
                )
        return chunks

    def _metadata_for_api(self, api: dict[str, Any]) -> dict[str, Any]:
        return {
            "api_reference_id": api.get("api_reference_id"),
            "service_name": api.get("service_name"),
            "service_group": api.get("service_group"),
            "service_description": api.get("service_description"),
            "service_method": api.get("service_method"),
            "service_type": api.get("service_type"),
            "service_pattern": api.get("service_pattern"),
            "service_max_timeout": api.get("service_max_timeout"),
            "api_authentication": api.get("api_authentication"),
            "api_gateway": api.get("api_gateway"),
            "source": api.get("source"),
            "source_type": "docx",
        }

    def _api_chunk_header(self, api_reference_id: str, service_name: str, section_name: str) -> str:
        return (
            f"API Reference ID: {api_reference_id}\n"
            f"Service Name: {service_name}\n"
            f"Section: {section_name}"
        )

    def _render_params(self, params: list[dict[str, Any]]) -> str:
        if not params:
            return "N/A"
        lines = []
        for param in params:
            lines.append(
                f"{param.get('param_name') or 'unknown'}"
                f" ({param.get('param_type') or 'unknown'}, {param.get('mandatory_optional') or 'N/A'})"
                f": {param.get('description') or 'N/A'}"
            )
        return "; ".join(lines)

    def _build_chunk(self, chunk_type: str, chunk_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "chunk_type": chunk_type,
            "chunk_text": chunk_text.strip(),
            "metadata": metadata,
        }


api_chunking_service = ApiChunkingService()


class ProductChunkingService:
    def create_chunks(
        self,
        parsed_doc: dict[str, Any],
        *,
        document_type: str,
        product_name: str | None = None,
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        logical_sections = parsed_doc.get("logical_sections") or []
        if logical_sections:
            for section in logical_sections:
                section_title = (section.get("section_title") or "General").strip()[:255]
                section_body = (section.get("content") or "").strip()
                if not section_body:
                    continue
                for text in self._split_large_text(section_body):
                    chunk_text = f"Section Title: {section_title}\n\n{text}"
                    chunks.append(
                        self._build_chunk(
                            chunk_type="product_section_chunk" if document_type == "product" else "generic_section_chunk",
                            chunk_text=chunk_text,
                            metadata={
                                "document_type": document_type,
                                "section_title": section_title,
                                "product_name": product_name,
                                "source_type": "docx",
                            },
                        )
                    )
        if chunks:
            return chunks

        # Fallback for sparse documents.
        fallback = (
            f"Document Title: {parsed_doc.get('document_title') or 'N/A'}\n"
            f"Purpose/Scope: {parsed_doc.get('purpose_scope') or 'N/A'}"
        )
        chunks.append(
            self._build_chunk(
                chunk_type="product_section_chunk" if document_type == "product" else "generic_section_chunk",
                chunk_text=fallback,
                metadata={
                    "document_type": document_type,
                    "section_title": parsed_doc.get("document_title") or "General",
                    "product_name": product_name,
                    "source_type": "docx",
                },
            )
        )
        return chunks

    def _split_large_text(self, text: str, max_chars: int = 1400) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        parts: list[str] = []
        current = ""
        for paragraph in text.split("\n"):
            candidate = f"{current}\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                parts.append(current)
            current = paragraph
        if current:
            parts.append(current)
        return parts

    def _build_chunk(self, chunk_type: str, chunk_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "chunk_type": chunk_type,
            "chunk_text": chunk_text.strip(),
            "metadata": metadata,
        }


def create_document_chunks(
    parsed_doc: dict[str, Any],
    *,
    document_type: str,
    product_name: str | None = None,
) -> list[dict[str, Any]]:
    if document_type == "api":
        return api_chunking_service.create_chunks(parsed_doc)
    return product_chunking_service.create_chunks(
        parsed_doc,
        document_type=document_type,
        product_name=product_name,
    )


product_chunking_service = ProductChunkingService()
