from __future__ import annotations

from typing import Any

from app.core.config import settings

INSUFFICIENT_CONTEXT_ANSWER = "I could not find enough information in the selected knowledge base to answer this confidently."


class SuggestedQuestionService:
    def generate(
        self,
        *,
        user_question: str,
        answer: str,
        contexts: list[dict[str, Any]] | None,
        document_type: str | None = None,
        detected_intents: list[str] | None = None,
    ) -> list[str]:
        try:
            if not getattr(settings, "ENABLE_SUGGESTED_QUESTIONS", True):
                return []
            if (answer or "").strip() == INSUFFICIENT_CONTEXT_ANSWER:
                return []
            if not (contexts or []):
                return []

            max_count = max(1, int(getattr(settings, "SUGGESTED_QUESTION_COUNT", 4)))
            intents = {str(x).strip().lower() for x in (detected_intents or []) if str(x).strip()}

            dominant_doc_type = (document_type or self._dominant_document_type(contexts or []) or "api").strip().lower()
            chunk_types = {str(item.get("chunk_type") or "").strip().lower() for item in (contexts or []) if item}
            service_names = self._unique_non_empty(item.get("service_name") for item in (contexts or []))
            api_refs = self._unique_non_empty(item.get("api_reference_id") for item in (contexts or []))
            section_titles = self._unique_non_empty(item.get("section_title") for item in (contexts or []))
            product_names = self._unique_non_empty(item.get("product_name") for item in (contexts or []))
            service_patterns = self._unique_non_empty(item.get("service_pattern") for item in (contexts or []))
            service_methods = self._unique_non_empty(item.get("service_method") for item in (contexts or []))
            service_groups = self._unique_non_empty(item.get("service_group") for item in (contexts or []))

            suggestions: list[str] = []

            has_api_indicator = self._has_api_indicators(
                user_question=user_question,
                intents=intents,
                chunk_types=chunk_types,
                api_refs=api_refs,
                service_names=service_names,
                service_methods=service_methods,
                service_groups=service_groups,
            )
            has_hr_indicator = self._has_hr_indicators(user_question=user_question, chunk_types=chunk_types, section_titles=section_titles)
            has_product_indicator = self._has_product_indicators(
                user_question=user_question,
                chunk_types=chunk_types,
                product_names=product_names,
                section_titles=section_titles,
            )

            if has_api_indicator or dominant_doc_type == "api":
                suggestions.extend(
                    self._api_questions(
                        chunk_types,
                        intents,
                        service_names,
                        api_refs,
                        service_patterns,
                        contexts=contexts or [],
                    )
                )
            elif has_hr_indicator or dominant_doc_type == "hr":
                suggestions.extend(self._hr_questions(chunk_types, section_titles))
            elif has_product_indicator or dominant_doc_type == "product":
                suggestions.extend(self._product_questions(chunk_types, section_titles, product_names))
            else:
                suggestions.extend(self._generic_grounded_questions(chunk_types, section_titles))

            suggestions = self._dedupe_and_filter(suggestions, user_question=user_question)
            return suggestions[:max_count]
        except Exception:
            return []

    def _primary_api_scope(self, contexts: list[dict[str, Any]]) -> tuple[str | None, str | None]:
        """Prefer metadata/response chunks so suggested questions match the current retrieval, not arbitrary order."""
        priority = (
            "api_response_parameters_chunk",
            "api_sample_success_response_chunk",
            "api_metadata_chunk",
            "api_overview_chunk",
            "api_request_parameters_chunk",
            "api_header_parameters_chunk",
            "api_query_parameters_chunk",
            "api_error_codes_chunk",
            "api_jwt_payload_chunk",
        )
        rank = {t: i for i, t in enumerate(priority)}
        best: tuple[int, int, str | None, str | None] | None = None
        for idx, item in enumerate(contexts or []):
            ct = (item.get("chunk_type") or "").strip().lower()
            if ct not in rank:
                continue
            s_raw, r_raw = item.get("service_name"), item.get("api_reference_id")
            s = str(s_raw).strip() if s_raw else None
            r = str(r_raw).strip() if r_raw else None
            if not s and not r:
                continue
            cand = (rank[ct], idx, s, r)
            if best is None or cand[:2] < best[:2]:
                best = cand
        if best:
            return best[2], best[3]
        for item in contexts or []:
            s_raw, r_raw = item.get("service_name"), item.get("api_reference_id")
            s = str(s_raw).strip() if s_raw else None
            r = str(r_raw).strip() if r_raw else None
            if s or r:
                return s, r
        return None, None

    def _api_questions(
        self,
        chunk_types: set[str],
        intents: set[str],
        service_names: list[str],
        api_refs: list[str],
        service_patterns: list[str],
        contexts: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        out: list[str] = []
        primary_service, primary_ref = self._primary_api_scope(contexts or [])
        if not primary_service and service_names:
            primary_service = service_names[0]
        if not primary_ref and api_refs:
            primary_ref = api_refs[0]

        if "authentication_intent" in intents:
            out.extend(
                [
                    self._api_scoped("What authentication method is required by this API?", primary_service, primary_ref),
                    self._api_scoped("What request parameters are required?", primary_service, primary_ref),
                    self._api_scoped("What are the success and failure response fields?", primary_service, primary_ref),
                    self._api_scoped("What error scenarios are documented?", primary_service, primary_ref),
                ]
            )

        if (
            "api_request_parameters_chunk" in chunk_types
            or "api_header_parameters_chunk" in chunk_types
            or "api_query_parameters_chunk" in chunk_types
            or "parameter_intent" in intents
        ):
            out.append(self._api_scoped("What are the request parameters for this API?", primary_service, primary_ref))
        if (
            "api_response_parameters_chunk" in chunk_types
            or "api_sample_success_response_chunk" in chunk_types
            or "response_field_intent" in intents
        ):
            out.append(self._api_scoped("What are the success response fields for this API?", primary_service, primary_ref))
        if (
            "api_sample_failed_response_chunk" in chunk_types
            or "api_error_codes_chunk" in chunk_types
            or "error_intent" in intents
        ):
            out.append(self._api_scoped("What are the failure response fields or error codes for this API?", primary_service, primary_ref))
            out.append(self._api_scoped("What error scenarios are documented for this API?", primary_service, primary_ref))
        if "authentication_chunk" in chunk_types or "authentication_intent" in intents:
            out.append(self._api_scoped("What authentication method is required by this API?", primary_service, primary_ref))
        if "async_intent" in intents or any(("asynch" in p.lower() or "callback" in p.lower()) for p in service_patterns):
            out.append("Is this API synchronous or asynchronous?")
        if any("status" in name.lower() for name in service_names) or any("status" in ref.lower() for ref in api_refs):
            out.append("Which API is used to check order status?")
        if any("revise" in name.lower() for name in service_names) or any("revise" in ref.lower() for ref in api_refs):
            out.append("Which API is used to revise an order?")
        if not out:
            out.extend(
                [
                    "What are the request parameters for this API?",
                    "What are the success and failure response fields?",
                    "Which authentication method is required?",
                    "Is this API synchronous or asynchronous?",
                ]
            )
        return out

    def _product_questions(self, chunk_types: set[str], section_titles: list[str], product_names: list[str]) -> list[str]:
        out: list[str] = []
        product_scope = f" for {product_names[0]}" if product_names else ""
        if "product_section_chunk" in chunk_types or section_titles:
            out.append(f"What are the main configuration steps{product_scope}?")
            out.append(f"What are the prerequisites{product_scope}?")
            out.append(f"What workflow should the user follow{product_scope}?")
            out.append(f"What limitations are mentioned{product_scope}?")
        return out or [
            "What are the main configuration steps?",
            "What are the prerequisites?",
            "What workflow should the user follow?",
            "What limitations are mentioned?",
        ]

    def _hr_questions(self, chunk_types: set[str], section_titles: list[str]) -> list[str]:
        if "generic_section_chunk" in chunk_types or section_titles:
            return [
                "What policy applies in this case?",
                "What are the eligibility criteria?",
                "What documents or approvals are required?",
            ]
        return [
            "What policy applies in this case?",
            "What are the eligibility criteria?",
            "What documents or approvals are required?",
        ]

    def _generic_grounded_questions(self, chunk_types: set[str], section_titles: list[str]) -> list[str]:
        out: list[str] = []
        if section_titles:
            out.append(f"Can you explain the section '{section_titles[0]}' in more detail?")
        if chunk_types:
            out.append("What related details are available in the current knowledge base context?")
        return out

    def _api_scoped(self, question: str, service_name: str | None, api_ref: str | None) -> str:
        if service_name:
            return f"{question} (Service: {service_name})"
        if api_ref:
            return f"{question} (API: {api_ref})"
        return question

    def _dedupe_and_filter(self, items: list[str], *, user_question: str) -> list[str]:
        user_norm = self._normalize(user_question)
        seen: set[str] = set()
        out: list[str] = []
        for raw in items:
            text = (raw or "").strip()
            if not text:
                continue
            norm = self._normalize(text)
            if not norm or norm == user_norm or norm in seen:
                continue
            seen.add(norm)
            out.append(text)
        return out

    def _dominant_document_type(self, contexts: list[dict[str, Any]]) -> str | None:
        counts: dict[str, int] = {}
        for item in contexts:
            dt = str(item.get("document_type") or "").strip().lower()
            if not dt:
                continue
            counts[dt] = counts.get(dt, 0) + 1
        if not counts:
            return None
        return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[0][0]

    def _unique_non_empty(self, values: Any) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for v in values:
            text = str(v or "").strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out

    def _normalize(self, value: str) -> str:
        return " ".join((value or "").lower().split())

    def _has_api_indicators(
        self,
        *,
        user_question: str,
        intents: set[str],
        chunk_types: set[str],
        api_refs: list[str],
        service_names: list[str],
        service_methods: list[str],
        service_groups: list[str],
    ) -> bool:
        api_chunk_tokens = (
            "api",
            "endpoint",
            "request",
            "response",
            "authentication",
            "auth",
            "error",
            "sample",
            "parameter",
        )
        if any(any(token in chunk for token in api_chunk_tokens) for chunk in chunk_types):
            return True
        if api_refs or service_names or service_methods or service_groups:
            return True
        if {"authentication_intent", "error_intent", "api_lookup_intent", "parameter_intent", "async_intent", "response_field_intent"}.intersection(intents):
            return True

        q = (user_question or "").lower()
        question_terms = (
            "api",
            "apis",
            "authentication",
            "request",
            "response",
            "parameter",
            "error",
            "async",
            "asynchronous",
            "status",
            "order",
            "revise",
            "appointment",
        )
        return any(term in q for term in question_terms)

    def _has_product_indicators(
        self,
        *,
        user_question: str,
        chunk_types: set[str],
        product_names: list[str],
        section_titles: list[str],
    ) -> bool:
        if "product_section_chunk" in chunk_types or product_names:
            return True
        text = " ".join(section_titles).lower()
        if any(token in text for token in ("workflow", "configuration", "prerequisite", "limitations", "setup", "portal")):
            return True
        q = (user_question or "").lower()
        return any(term in q for term in ("configuration", "configure", "workflow", "prerequisite", "limitations", "product"))

    def _has_hr_indicators(self, *, user_question: str, chunk_types: set[str], section_titles: list[str]) -> bool:
        text = (" ".join(section_titles) + " " + (user_question or "")).lower()
        if any(token in text for token in ("hr", "policy", "eligibility", "approval", "leave", "benefit", "documents required")):
            return True
        return any("hr" in chunk for chunk in chunk_types)


suggested_question_service = SuggestedQuestionService()
