from __future__ import annotations

import re
from typing import Any

# Substrings (lowercased text) for validating fallback / retrieval quality (QR Util + common REST docs).
_KNOWN_RESPONSE_FIELD_MARKERS = (
    "status",
    "code",
    "desc",
    "timestamp",
    "transactionid",
    "correlationid",
    "responseinfo",
    "qrtext",
    "errorcode",
    "errormsg",
)
_API_REST_LINE = re.compile(r"^\s*(API-REST-[A-Z]+-\d+)\s*$", re.IGNORECASE)
_RESPONSE_SECTION_START = re.compile(
    r"^\s*(Response Parameters|Output Response(?: Success)?|Success Response)\s*$",
    re.IGNORECASE,
)

# Step 55 — retrieval alias phrases embedded in semantic chunks (exact wording per project brief).
_HEADER_RETRIEVAL_ALIASES = (
    "headers required; request headers; calling API headers; Authorization header; TransactionId header"
)
_REQUEST_STRUCTURE_ALIASES = (
    "request body; request structure; JSON request; request payload; parameters array; key value pairs"
)
_TOKEN_EXPIRY_ALIASES = (
    "access token expiry; expires_in; PROD expiry; non-PROD expiry; 540 seconds; 60 seconds"
)


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

        auth_preamble = (parsed_doc.get("authentication_preamble") or "").strip()
        auth_entries = [
            api
            for api in apis
            if api.get("api_authentication") or api.get("service_swagger")
        ]
        auth_lines: list[str] = []
        if auth_preamble:
            auth_lines.append(f"General Authentication:\n{auth_preamble}")
        for entry in auth_entries:
            auth_lines.append(
                f"{entry.get('api_reference_id')}: auth={entry.get('api_authentication') or 'N/A'}, "
                f"swagger={entry.get('service_swagger') or 'N/A'}"
            )
        if auth_lines:
            chunks.append(
                self._build_chunk(
                    chunk_type="authentication_chunk",
                    chunk_text="\n".join(auth_lines),
                    metadata={},
                )
            )

        auth_narrative = "\n\n".join(
            p
            for p in [
                (parsed_doc.get("authentication_preamble") or "").strip(),
                "\n".join(auth_lines) if auth_lines else "",
            ]
            if p
        ).strip()
        if auth_narrative:
            chunks.append(self._build_auth_semantic_summary_chunk(auth_narrative))

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
            response_body = self._render_response_parameter_body(api, response_params)
            header_params = api.get("header_parameters") or []
            query_params = api.get("query_parameters") or []
            error_params = api.get("error_code_parameters") or []
            jwt_params = api.get("jwt_payload_parameters") or []

            if header_params:
                header_text = (
                    f"{self._api_chunk_header(api_reference_id, service_name, 'Header Parameters')}\n"
                    f"Header Parameters: {self._render_params(header_params)}"
                )
                chunks.append(
                    self._build_chunk(
                        chunk_type="api_header_parameters_chunk",
                        chunk_text=header_text,
                        metadata=metadata,
                    )
                )

            request_text = (
                f"{self._api_chunk_header(api_reference_id, service_name, 'API Request Parameters')}\n"
                f"Method: {api.get('service_method') or 'N/A'}\n"
                f"Service Pattern: {api.get('service_pattern') or 'N/A'}\n"
                f"Request Parameters: {self._render_params(request_params)}\n"
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_request_parameters_chunk",
                    chunk_text=request_text,
                    metadata=metadata,
                )
            )

            if query_params:
                chunks.append(
                    self._build_chunk(
                        chunk_type="api_query_parameters_chunk",
                        chunk_text=(
                            f"{self._api_chunk_header(api_reference_id, service_name, 'Query Parameters')}\n"
                            f"Query Parameters: {self._render_params(query_params)}"
                        ),
                        metadata=metadata,
                    )
                )

            response_text = (
                f"{self._api_chunk_header(api_reference_id, service_name, 'API Response Parameters')}\n"
                f"Response Parameters: {response_body}"
            )
            chunks.append(
                self._build_chunk(
                    chunk_type="api_response_parameters_chunk",
                    chunk_text=response_text,
                    metadata=metadata,
                )
            )

            if error_params:
                chunks.append(
                    self._build_chunk(
                        chunk_type="api_error_codes_chunk",
                        chunk_text=(
                            f"{self._api_chunk_header(api_reference_id, service_name, 'Expected Error Codes')}\n"
                            f"Error Codes: {self._render_params(error_params)}"
                        ),
                        metadata=metadata,
                    )
                )

            if jwt_params:
                chunks.append(
                    self._build_chunk(
                        chunk_type="api_jwt_payload_chunk",
                        chunk_text=(
                            f"{self._api_chunk_header(api_reference_id, service_name, 'JWT Payload Structure')}\n"
                            f"JWT Payload: {self._render_params(jwt_params)}"
                        ),
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

            chunks.extend(self._semantic_enrichment_for_api(api, metadata))

            if api.get("raw_text"):
                raw = api["raw_text"].strip()
                generic_header = self._api_chunk_header(api_reference_id, service_name, "Generic Section")
                for part in self._split_large_text(raw):
                    chunks.append(
                        self._build_chunk(
                            chunk_type="generic_section_chunk",
                            chunk_text=f"{generic_header}\n{part}",
                            metadata=metadata,
                        )
                    )
        return chunks

    def _mandatory_readable(self, mo_raw: str | None) -> str:
        m = (mo_raw or "").strip().lower()
        if m in ("m", "mandatory", "required", "yes", "y", "req"):
            return "mandatory"
        if m in ("o", "optional", "opt"):
            return "optional"
        return (mo_raw or "").strip() or "unspecified"

    def _param_to_natural_language(self, param: dict[str, Any], *, slot: str) -> str:
        name = (param.get("param_name") or "unknown").strip()
        ptype = (param.get("param_type") or "unknown").strip()
        mo = self._mandatory_readable(param.get("mandatory_optional"))
        desc = (param.get("description") or "N/A").strip()
        req = "Required" if mo.lower() in ("mandatory", "required", "m") else "Optional"
        if slot == "header":
            return f"{req} header {name} is a {ptype} and is {mo}. Description: {desc}."
        if slot == "query":
            return f"{req} query parameter {name} is a {ptype} and is {mo}. Description: {desc}."
        if slot == "response":
            return f"{req} response field {name} is a {ptype} and is {mo}. Description: {desc}."
        if slot == "error":
            return f"{req} error code row {name} is a {ptype} and is {mo}. Description: {desc}."
        return f"{req} request parameter {name} is a {ptype} and is {mo}. Description: {desc}."

    def _flatten_params_table_chunk(
        self,
        *,
        api_reference_id: str,
        service_name: str,
        section_display: str,
        params: list[dict[str, Any]],
        slot: str,
        metadata: dict[str, Any],
        aliases: str | None,
    ) -> dict[str, Any] | None:
        if not params:
            return None
        header = self._api_chunk_header(api_reference_id, service_name, section_display)
        body_lines = [header, "", "Natural-language rows (flattened from DOCX tables):"]
        for p in params:
            body_lines.append(self._param_to_natural_language(p, slot=slot))
        if aliases:
            body_lines.extend(["", f"Retrieval aliases: {aliases}"])
        return self._build_chunk(
            chunk_type="api_table_flattened_chunk",
            chunk_text="\n".join(body_lines).strip(),
            metadata={**metadata, "semantic_flatten_slot": slot, "semantic_flatten_section": section_display},
        )

    def _build_api_semantic_summary_chunk(self, api: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        api_reference_id = api.get("api_reference_id") or "N/A"
        service_name = api.get("service_name") or "Unknown Service"
        header_params = api.get("header_parameters") or []
        query_params = api.get("query_parameters") or []
        request_params = api.get("api_request_parameters") or api.get("input_parameters") or []
        response_params = api.get("api_response_parameters") or api.get("output_response_success") or []
        error_params = api.get("error_code_parameters") or []

        lines: list[str] = [
            "API Semantic Summary",
            f"API Reference ID: {api_reference_id}",
            f"Service Name: {service_name}",
            f"Service Group: {api.get('service_group') or 'N/A'}",
            f"Authentication: {api.get('api_authentication') or 'N/A'}",
            f"HTTP Method: {api.get('service_method') or 'N/A'}",
        ]

        def bullets(label: str, params: list[dict[str, Any]], field: str = "param_name") -> None:
            lines.append(label)
            for p in params:
                nm = (p.get(field) or "").strip() or "unknown"
                lines.append(f"- {nm}")

        if header_params:
            bullets("Required Headers:", header_params)
        if query_params:
            bullets("Required Query Parameters:", query_params)
        if request_params:
            bullets("Required Query/Request Parameters:", request_params)
        if response_params:
            bullets("Success Response Fields:", response_params)
        if error_params:
            bullets("Failure Fields:", error_params)

        lines.extend(
            [
                "",
                f"Retrieval aliases for headers when calling this API: {_HEADER_RETRIEVAL_ALIASES}",
                f"Retrieval aliases for JSON request structure: {_REQUEST_STRUCTURE_ALIASES}",
            ]
        )
        return self._build_chunk(
            chunk_type="api_semantic_summary_chunk",
            chunk_text="\n".join(lines).strip(),
            metadata=metadata,
        )

    def _semantic_enrichment_for_api(self, api: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        api_reference_id = api.get("api_reference_id") or "N/A"
        service_name = api.get("service_name") or "Unknown Service"
        header_params = api.get("header_parameters") or []
        query_params = api.get("query_parameters") or []
        request_params = api.get("api_request_parameters") or api.get("input_parameters") or []
        response_params = api.get("api_response_parameters") or api.get("output_response_success") or []
        error_params = api.get("error_code_parameters") or []

        out.append(self._build_api_semantic_summary_chunk(api, metadata))

        fc = self._flatten_params_table_chunk(
            api_reference_id=api_reference_id,
            service_name=service_name,
            section_display="Header Parameters",
            params=header_params,
            slot="header",
            metadata=metadata,
            aliases=_HEADER_RETRIEVAL_ALIASES,
        )
        if fc:
            out.append(fc)
        fq = self._flatten_params_table_chunk(
            api_reference_id=api_reference_id,
            service_name=service_name,
            section_display="Query Parameters",
            params=query_params,
            slot="query",
            metadata=metadata,
            aliases=_REQUEST_STRUCTURE_ALIASES,
        )
        if fq:
            out.append(fq)
        fr = self._flatten_params_table_chunk(
            api_reference_id=api_reference_id,
            service_name=service_name,
            section_display="Input Parameter",
            params=request_params,
            slot="request",
            metadata=metadata,
            aliases=_REQUEST_STRUCTURE_ALIASES,
        )
        if fr:
            out.append(fr)
        fo = self._flatten_params_table_chunk(
            api_reference_id=api_reference_id,
            service_name=service_name,
            section_display="Output Response Success",
            params=response_params,
            slot="response",
            metadata=metadata,
            aliases=None,
        )
        if fo:
            out.append(fo)
        fe = self._flatten_params_table_chunk(
            api_reference_id=api_reference_id,
            service_name=service_name,
            section_display="Expected Error Codes",
            params=error_params,
            slot="error",
            metadata=metadata,
            aliases=None,
        )
        if fe:
            out.append(fe)
        return out

    def _build_auth_semantic_summary_chunk(self, narrative: str) -> dict[str, Any]:
        lines = [
            "Authentication Semantic Summary",
            "Token endpoint: getSSOToken",
            "OAuth flow: Client Credentials Grant",
            "Supported grant types:",
            "- client_credentials",
            "- refresh_token",
            "Access token expiry:",
            "- Non-prod: 540 seconds",
            "- Prod: 60 seconds",
            "Refresh token:",
            "- Used to obtain a new access token when a refresh token exists",
            "Subsequent API calls use bearer token in Authorization or Authentication header.",
            "",
            "Supporting narrative from document:",
            narrative.strip(),
            "",
            f"Retrieval aliases for token lifetime questions: {_TOKEN_EXPIRY_ALIASES}",
        ]
        return self._build_chunk(
            chunk_type="auth_semantic_summary_chunk",
            chunk_text="\n".join(lines).strip(),
            metadata={"source_type": "docx"},
        )

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

    def _render_response_parameter_body(self, api: dict[str, Any], response_params: list[dict[str, Any]]) -> str:
        rendered = self._render_params(response_params)
        if rendered != "N/A":
            return rendered
        fb = self._fallback_response_params_from_raw(api.get("raw_text") or "", api.get("api_reference_id"))
        return fb if fb else "N/A"

    def _scope_raw_after_api_ref(self, raw: str, api_reference_id: str | None) -> str:
        """Limit fallback scanning to the active API block (skip TOC / preamble before this ref)."""
        raw = (raw or "").strip()
        if not raw:
            return ""
        ref = (api_reference_id or "").strip()
        if ref.upper().startswith("API-REST-"):
            m = re.search(re.escape(ref), raw, flags=re.IGNORECASE)
            return raw[m.start() :] if m else ""
        if ref and ref.upper() not in {"N/A", "UNKNOWN"}:
            m = re.search(re.escape(ref), raw, flags=re.IGNORECASE)
            return raw[m.start() :] if m else ""
        return ""

    def _is_toc_line(self, line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        low = s.lower()
        if "table of contents" in low:
            return True
        if re.search(r"\.{4,}\s*\d+\s*$", s):
            return True
        if re.search(r"[…\u2026]{2,}\s*\d+\s*$", s):
            return True
        if re.match(r"^\d+\s*\.\s+", s) and ("response" in low or "parameter" in low):
            return True
        return False

    def _is_response_section_start_line(self, line: str) -> bool:
        if self._is_toc_line(line):
            return False
        return bool(_RESPONSE_SECTION_START.match(line.strip()))

    def _is_response_fallback_stop_line(self, line: str, current_api_ref_upper: str) -> bool:
        s = line.strip()
        if not s:
            return False
        sl = s.lower()
        if sl.startswith(
            (
                "integration flow",
                "failed response",
                "appendix",
                "expected error codes",
                "system attributes",
                "other references",
                "header parameters",
                "query parameters",
                "request parameters",
            )
        ):
            return True
        if sl.startswith("jwt payload") or (sl.startswith("jwt ") and not sl.startswith("jwt signing")):
            return True
        if sl.startswith("sample ") or sl == "sample":
            return True
        m = _API_REST_LINE.match(s)
        if m:
            hit = m.group(1).upper()
            if current_api_ref_upper and hit == current_api_ref_upper:
                return False
            return True
        return False

    def _known_response_field_hits(self, blob: str) -> int:
        t = blob.lower()
        return sum(1 for k in _KNOWN_RESPONSE_FIELD_MARKERS if k in t)

    def _fallback_response_params_from_raw(self, raw: str, api_reference_id: str | None) -> str | None:
        """When structured rows were not extracted, lift the Response Parameters block from scoped raw_text."""
        raw = (raw or "").strip()
        if len(raw) < 40:
            return None
        scoped = self._scope_raw_after_api_ref(raw, api_reference_id)
        lines = scoped.splitlines()
        cur_ref_u = (api_reference_id or "").strip().upper()
        start_i: int | None = None
        for i, line in enumerate(lines):
            if self._is_response_section_start_line(line):
                start_i = i
                break
        if start_i is None:
            return None
        out_lines: list[str] = []
        for j in range(start_i, len(lines)):
            line = lines[j]
            if j > start_i and self._is_response_fallback_stop_line(line, cur_ref_u):
                break
            out_lines.append(line)
        blob = "\n".join(out_lines).strip()
        if len(blob) < 12:
            return None
        low = blob.lower().strip()
        if low in {"response parameters", "output response", "output response success", "success response"}:
            return None
        if self._known_response_field_hits(blob) < 2:
            return None
        return blob[:4500]

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


def response_parameters_chunk_quality(chunk_text: str) -> dict[str, Any]:
    """Retrieval-time signals: known response fields present vs degenerate TOC-style headings."""
    t = (chunk_text or "").strip().lower()
    hits = sum(1 for k in _KNOWN_RESPONSE_FIELD_MARKERS if k in t)
    after = ""
    if "response parameters:" in t:
        after = t.split("response parameters:", 1)[1].strip()
    degenerate = after.startswith("response parameters") or (hits < 2 and (after.startswith("n/a") or len(after) < 25))
    boost_ok = hits >= 2 and not degenerate
    return {"known_field_hits": hits, "degenerate": degenerate, "boost_ok": boost_ok}


def generic_chunk_response_field_marker_hits(chunk_text: str) -> int:
    t = (chunk_text or "").lower()
    return sum(1 for k in _KNOWN_RESPONSE_FIELD_MARKERS if k in t)


def generic_chunk_qualifies_as_response_fields(chunk_text: str, *, min_markers: int = 2) -> bool:
    """True when generic_section text carries multiple known REST response field markers (QR Util raw tables)."""
    return generic_chunk_response_field_marker_hits(chunk_text) >= min_markers


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
