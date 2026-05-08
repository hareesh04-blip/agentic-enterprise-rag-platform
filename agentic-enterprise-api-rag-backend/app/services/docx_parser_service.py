from __future__ import annotations

import re
from collections.abc import Iterator
from io import BytesIO
from typing import Any

from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

API_REF_PATTERN = re.compile(r"API-REST-(?:DSE|NOK|SAC)-\d+", re.IGNORECASE)


class DocxParserService:
    def parse_preview(self, file_name: str, file_bytes: bytes) -> dict[str, Any]:
        document = Document(BytesIO(file_bytes))
        sections = self._parse_document(document)
        apis = list(sections.values())
        logical_sections = self._extract_logical_sections(document)
        return {
            "file_name": file_name,
            "document_title": self._extract_document_title(document),
            "purpose_scope": self._extract_purpose_scope(document),
            "api_count": len(apis),
            "logical_sections": logical_sections,
            "apis": [
                {
                    "api_reference_id": api["api_reference_id"],
                    "service_name": api.get("service_name"),
                    "service_group": api.get("service_group"),
                    "service_method": api.get("service_method"),
                    "service_pattern": api.get("service_pattern"),
                }
                for api in apis
            ],
            "apis_full": apis,
        }

    def _extract_logical_sections(self, document: DocumentType) -> list[dict[str, str]]:
        collected: list[dict[str, str]] = []
        current_title = "General"
        current_lines: list[str] = []
        for block in self._iter_block_items(document):
            if isinstance(block, Paragraph):
                text = self._normalize_text(block.text)
                if not text:
                    continue
                if self._is_heading_like(block, text):
                    if current_lines:
                        collected.append(
                            {
                                "section_title": current_title,
                                "content": "\n".join(current_lines).strip(),
                            }
                        )
                        current_lines = []
                    current_title = text
                    continue
                current_lines.append(text)
            elif isinstance(block, Table):
                table_rows = self._extract_table_rows(block)
                if not table_rows:
                    continue
                table_lines = self._table_rows_to_readable_lines(table_rows)
                current_lines.extend(table_lines)

        if current_lines:
            collected.append(
                {
                    "section_title": current_title,
                    "content": "\n".join(current_lines).strip(),
                }
            )
        return [item for item in collected if item.get("content")]

    def _is_heading_like(self, paragraph: Paragraph, text: str) -> bool:
        style_name = (paragraph.style.name if paragraph.style else "") or ""
        style_lower = style_name.lower()
        if "heading" in style_lower or style_lower in {"title", "subtitle"}:
            return True
        if re.match(r"^\d+(\.\d+)*[\)\.]?\s+[A-Za-z].*", text):
            return True
        if len(text) <= 80 and not text.endswith(".") and text[0].isupper():
            alpha = [c for c in text if c.isalpha()]
            if alpha and (sum(1 for c in alpha if c.isupper()) / len(alpha)) > 0.55:
                return True
        return False

    def _parse_document(self, document: DocumentType) -> dict[str, dict[str, Any]]:
        sections: dict[str, dict[str, Any]] = {}
        current_ref: str | None = None
        recent_context = ""
        pending_key: str | None = None

        for block in self._iter_block_items(document):
            if isinstance(block, Paragraph):
                text = self._normalize_text(block.text)
                if not text:
                    continue
                recent_context = text
                refs = self._extract_api_refs(text)
                if refs:
                    current_ref = refs[0]
                    if current_ref not in sections:
                        sections[current_ref] = self._new_section(current_ref)
                if current_ref:
                    if pending_key and self._looks_like_value_line(text):
                        self._map_key_value(sections[current_ref], pending_key, text)
                        pending_key = None
                    elif self._looks_like_metadata_key_line(text):
                        pending_key = text
                    else:
                        pending_key = None
                    self._append_raw_text(sections[current_ref], text)
                    self._extract_inline_metadata(sections[current_ref], text)
            elif isinstance(block, Table):
                table_rows = self._extract_table_rows(block)
                if not table_rows:
                    continue
                table_text = "\n".join(self._table_rows_to_readable_lines(table_rows))
                refs = self._extract_api_refs(table_text)
                if refs:
                    current_ref = refs[0]
                    if current_ref not in sections:
                        sections[current_ref] = self._new_section(current_ref)
                if not current_ref:
                    continue
                section = sections[current_ref]
                self._append_raw_text(section, table_text)
                self._parse_table_into_section(section, table_rows, recent_context)
        return sections

    def _new_section(self, api_reference_id: str) -> dict[str, Any]:
        return {
            "api_reference_id": api_reference_id,
            "service_name": None,
            "service_group": None,
            "service_description": None,
            "service_swagger": None,
            "service_url": None,
            "api_authentication": None,
            "api_gateway": None,
            "source": None,
            "service_method": None,
            "service_type": None,
            "service_pattern": None,
            "service_max_timeout": None,
            "header_parameters": [],
            "input_parameters": [],
            "output_response_success": [],
            "api_request_parameters": [],
            "api_response_parameters": [],
            "sample_initial": None,
            "sample_token_exist": None,
            "sample_request": None,
            "sample_success_response": None,
            "sample_failed_request": None,
            "sample_failed_response": None,
            "raw_text": "",
        }

    def _extract_document_title(self, document: DocumentType) -> str | None:
        for paragraph in document.paragraphs:
            text = self._normalize_text(paragraph.text)
            if text and len(text) > 5 and not API_REF_PATTERN.search(text):
                return text
        return None

    def _extract_purpose_scope(self, document: DocumentType) -> str | None:
        sections = self._extract_logical_sections(document)
        for section in sections:
            title = (section.get("section_title") or "").lower()
            content = self._normalize_text(section.get("content") or "")
            if not content:
                continue
            if "introduction" in title or "purpose" in title or "scope" in title:
                return content
        for paragraph in document.paragraphs:
            text = self._normalize_text(paragraph.text)
            if not text:
                continue
            lowered = text.lower()
            if "this document details the information that is required to process broadband order requests" in lowered:
                return text
            if "purpose" in lowered or "scope" in lowered:
                return text
        return None

    def _extract_table_rows(self, table: Table) -> list[list[str]]:
        rows: list[list[str]] = []
        for row in table.rows:
            cells = [self._normalize_text(cell.text) for cell in row.cells]
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(cells)
        return rows

    def _parse_table_into_section(self, section: dict[str, Any], table_rows: list[list[str]], context: str) -> None:
        for key, value in self._table_rows_to_key_values(table_rows):
            self._map_key_value(section, key, value)

        max_cols = max((len(row) for row in table_rows), default=0)
        if max_cols <= 2:
            return

        header_row = [self._normalize_key(col) for col in table_rows[0]]
        is_param_table = any("param" in col for col in header_row)
        for row in table_rows[1:]:
            if len(row) < 2:
                continue
            entry = {
                "param_name": row[0] if len(row) > 0 else None,
                "param_type": row[1] if len(row) > 1 else None,
                "mandatory_optional": row[2] if len(row) > 2 else None,
                "description": row[3] if len(row) > 3 else None,
            }
            if not is_param_table:
                # Fallback for non-standard tables; keep as input parameter rows.
                section["input_parameters"].append(entry)
                continue
            context_lower = context.lower()
            if "header" in context_lower:
                section["header_parameters"].append(entry)
            elif "output" in context_lower or "response" in context_lower:
                section["output_response_success"].append(entry)
                section["api_response_parameters"].append(entry)
            else:
                section["input_parameters"].append(entry)
                section["api_request_parameters"].append(entry)

    def _extract_inline_metadata(self, section: dict[str, Any], text: str) -> None:
        if ":" not in text:
            return
        key, value = text.split(":", 1)
        self._map_key_value(section, key, value)

    def _map_key_value(self, section: dict[str, Any], key: str, value: str) -> None:
        key_norm = self._normalize_key(key)
        value_norm = self._normalize_text(value)
        if not value_norm:
            return
        if value_norm.lower() == key_norm:
            return
        mapping = {
            "service name": "service_name",
            "service group": "service_group",
            "service description": "service_description",
            "service swagger": "service_swagger",
            "service swagger url": "service_swagger",
            "service url": "service_url",
            "api authentication": "api_authentication",
            "authentication": "api_authentication",
            "api gateway": "api_gateway",
            "source": "source",
            "service method": "service_method",
            "service type": "service_type",
            "service pattern": "service_pattern",
            "service max timeout": "service_max_timeout",
            "max timeout": "service_max_timeout",
            "sample initial": "sample_initial",
            "sample token exist": "sample_token_exist",
            "sample request": "sample_request",
            "sample success response": "sample_success_response",
            "sample failed request": "sample_failed_request",
            "sample failed response": "sample_failed_response",
        }
        target = mapping.get(key_norm)
        if target and value_norm.lower() not in mapping:
            section[target] = value_norm

    def _extract_api_refs(self, text: str) -> list[str]:
        return [match.upper() for match in API_REF_PATTERN.findall(text or "")]

    def _table_rows_to_key_values(self, table_rows: list[list[str]]) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        recognized_keys = {
            "service name",
            "service group",
            "service description",
            "service method",
            "service type",
            "service pattern",
            "service max timeout",
            "api authentication",
            "api gateway",
            "source",
            "sample request",
            "sample success response",
            "sample failed request",
            "sample failed response",
        }
        consumed_rows: set[int] = set()
        for idx, row in enumerate(table_rows):
            if idx in consumed_rows:
                continue
            if len(row) >= 2:
                key = row[0]
                key_norm = self._normalize_key(key)
                value_candidate = next(
                    (
                        cell
                        for cell in row[1:]
                        if self._normalize_key(cell)
                        and self._normalize_key(cell) != key_norm
                        and self._normalize_key(cell) not in recognized_keys
                    ),
                    None,
                )
                value = value_candidate or row[1]
                value_norm = self._normalize_key(value)
                if key_norm in recognized_keys and (not value_norm or value_norm in recognized_keys or value_norm == key_norm):
                    if idx + 1 < len(table_rows):
                        next_row = table_rows[idx + 1]
                        next_value = self._normalize_text(" | ".join(next_row))
                        next_value_norm = self._normalize_key(next_value)
                        if next_value and next_value_norm not in recognized_keys:
                            pairs.append((key, next_value))
                            consumed_rows.add(idx + 1)
                    continue
                pairs.append((key, value))

        linear_cells = [row[0] for index, row in enumerate(table_rows) if len(row) == 1 and index not in consumed_rows]
        pending_key: str | None = None
        for cell in linear_cells:
            cell_norm = self._normalize_key(cell)
            if pending_key is None and cell_norm in recognized_keys:
                pending_key = cell
                continue
            if pending_key and cell_norm not in recognized_keys:
                pairs.append((pending_key, cell))
                pending_key = None
        return pairs

    def _table_rows_to_readable_lines(self, table_rows: list[list[str]]) -> list[str]:
        lines: list[str] = []
        for row in table_rows:
            if len(row) >= 2:
                lines.append(f"{row[0]}: {' | '.join(row[1:])}")
            elif len(row) == 1:
                lines.append(row[0])
        return lines

    def _looks_like_metadata_key_line(self, text: str) -> bool:
        key = self._normalize_key(text)
        return key in {
            "service name",
            "service group",
            "service description",
            "service method",
            "service type",
            "service pattern",
            "service max timeout",
            "api authentication",
            "api gateway",
            "source",
            "sample request",
            "sample success response",
            "sample failed request",
            "sample failed response",
        }

    def _looks_like_value_line(self, text: str) -> bool:
        return bool(text and ":" not in text and len(text) > 2)

    def _append_raw_text(self, section: dict[str, Any], text: str) -> None:
        if not text:
            return
        if section["raw_text"]:
            section["raw_text"] += "\n"
        section["raw_text"] += text

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _normalize_key(self, key: str) -> str:
        return self._normalize_text(key).lower()

    def _iter_block_items(self, document: DocumentType) -> Iterator[Paragraph | Table]:
        parent_elm = document.element.body
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, document)
            elif isinstance(child, CT_Tbl):
                yield Table(child, document)


docx_parser_service = DocxParserService()
