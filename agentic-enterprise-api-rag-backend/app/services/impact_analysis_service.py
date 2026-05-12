from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_str(value: Any) -> str:
    try:
        return str(value).strip()
    except Exception:
        return ""


def _safe_lower(value: Any) -> str:
    return _safe_str(value).lower()


class ImpactAnalysisService:
    """
    Deterministic, retrieval-assisted impact analysis MVP.

    Important constraints:
    - No external calls
    - Never raise (fail closed with an empty/safe result)
    - No graph DB / Neo4j
    - Only uses already-ingested metadata from retrieved chunks
    """

    # Matches how ingestion formats API reference ids inside `authentication_chunk` chunk_text.
    # Example line: "API-REST-DSE-12345: auth=..., swagger=..."
    AUTH_LINE_RE = re.compile(
        r"(?P<api_ref>API-REST-[A-Z0-9]+-\d+)\s*:\s*auth\s*=\s*(?P<auth>.*?)(?:,\s*swagger\s*=|\s*$)",
        re.IGNORECASE,
    )

    # Matches how api reference ids appear in header-ish text.
    API_REF_RE = re.compile(r"API-REST-[A-Z0-9]+-\d+", re.IGNORECASE)

    # Chunk types (must match ingestion/chunking_service.py exactly)
    AUTH_CHUNK_TYPE = "authentication_chunk"
    OVERVIEW_CHUNK_TYPES = {"api_overview_chunk", "api_metadata_chunk"}
    REQUEST_CHUNK_TYPES = {
        "api_request_parameters_chunk",
        "api_header_parameters_chunk",
        "api_query_parameters_chunk",
    }
    RESPONSE_CHUNK_TYPES = {
        "api_response_parameters_chunk",
        "api_sample_success_response_chunk",
        "endpoint_response_chunk",
    }
    ERROR_CHUNK_TYPES = {
        "api_sample_failed_response_chunk",
        "api_sample_failed_request_chunk",
        "api_error_codes_chunk",
    }
    PRODUCT_CHUNK_TYPE = "product_section_chunk"

    def analyze_impact(
        self,
        *,
        user_question: str | None = None,
        retrieved_chunks: list[dict[str, Any]] | None = None,
        chunk_metadata: dict[str, Any] | None = None,
        api_reference_id: str | None = None,
        service_name: str | None = None,
        service_group: str | None = None,
        service_method: str | None = None,
        chunk_type: str | None = None,
        detected_intents: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            if not getattr(settings, "ENABLE_IMPACT_ANALYSIS", True):
                return {
                    "primary_entities": [],
                    "related_entities": [],
                    "potential_impacts": [],
                    "relationship_summary": [],
                    "impact_confidence": "low",
                }

            chunks: list[dict[str, Any]] = list(retrieved_chunks or [])
            meta: dict[str, Any] = dict(chunk_metadata or {})

            # Anchor fields prefer explicit inputs, then derived from retrieved chunks.
            intents = [str(x).strip().lower() for x in (detected_intents or []) if str(x).strip()]
            anchor = self._build_anchor(
                chunks=chunks,
                meta=meta,
                api_reference_id=api_reference_id,
                service_name=service_name,
                service_group=service_group,
                service_method=service_method,
                chunk_type=chunk_type,
            )

            api_entities = self.extract_api_entities(chunks=chunks, intents=intents)
            relationships = self.extract_relationships(
                chunks=chunks,
                anchor=anchor,
                intents=intents,
                api_entities=api_entities,
            )

            impact = self.build_impact_summary(
                anchor=anchor,
                relationships=relationships,
                intents=intents,
                chunks=chunks,
            )

            return {
                "primary_entities": impact["primary_entities"],
                "related_entities": impact["related_entities"],
                "potential_impacts": impact["potential_impacts"],
                "relationship_summary": impact["relationship_summary"],
                "impact_confidence": impact["impact_confidence"],
            }
        except Exception:
            # Never raise: fail closed with a deterministic low-confidence payload.
            return {
                "primary_entities": [],
                "related_entities": [],
                "potential_impacts": [],
                "relationship_summary": [],
                "impact_confidence": "low",
            }

    def _build_anchor(
        self,
        *,
        chunks: list[dict[str, Any]],
        meta: dict[str, Any],
        api_reference_id: str | None,
        service_name: str | None,
        service_group: str | None,
        service_method: str | None,
        chunk_type: str | None,
    ) -> dict[str, Any]:
        # Use most-common among retrieved chunks as a deterministic fallback.
        api_ref = _safe_str(api_reference_id or meta.get("api_reference_id"))
        svc_name = _safe_str(service_name or meta.get("service_name"))
        svc_group = _safe_str(service_group or meta.get("service_group"))
        svc_method = _safe_str(service_method or meta.get("service_method"))
        ctype = _safe_lower(chunk_type or meta.get("chunk_type"))

        if chunks:
            if not api_ref:
                api_ref = self._mode([_safe_str(c.get("api_reference_id")) for c in chunks])
            if not svc_name:
                svc_name = self._mode([_safe_str(c.get("service_name")) for c in chunks])
            if not svc_group:
                svc_group = self._mode([_safe_str(c.get("service_group")) for c in chunks])
            if not svc_method:
                svc_method = self._mode([_safe_str(c.get("service_method")) for c in chunks])
            if not ctype:
                ctype = _safe_lower(self._mode([_safe_str(c.get("chunk_type")) for c in chunks]))

        # Optional richer anchors from metadata-like keys.
        product_name = _safe_str(meta.get("product_name"))
        section_title = _safe_str(meta.get("section_title"))
        if chunks:
            if not product_name:
                product_name = self._mode([_safe_str(c.get("product_name")) for c in chunks])
            if not section_title:
                section_title = self._mode([_safe_str(c.get("section_title")) for c in chunks])

        return {
            "api_reference_id": api_ref or None,
            "service_name": svc_name or None,
            "service_group": svc_group or None,
            "service_method": svc_method or None,
            "chunk_type": ctype or None,
            "product_name": product_name or None,
            "section_title": section_title or None,
        }

    def _mode(self, values: list[str]) -> str:
        # Deterministic “most frequent, then lexicographically stable” selection.
        freq: dict[str, int] = {}
        for v in values:
            vv = _safe_str(v)
            if not vv:
                continue
            freq[vv] = freq.get(vv, 0) + 1
        if not freq:
            return ""
        return sorted(freq.items(), key=lambda kv: (-kv[1], kv[0].lower()))[0][0]

    def extract_api_entities(self, *, chunks: list[dict[str, Any]], intents: list[str]) -> dict[str, Any]:
        """
        Extract deterministic entity sets (APIs/services/sections/auth/error/product refs)
        from retrieved chunks.
        """
        api_refs: set[str] = set()
        service_names: set[str] = set()
        service_groups: set[str] = set()
        service_methods: set[str] = set()
        product_names: set[str] = set()
        section_titles: set[str] = set()

        auth_api_refs: set[str] = set()
        auth_flows: list[dict[str, Any]] = []
        request_api_refs: set[str] = set()
        response_api_refs: set[str] = set()
        error_api_refs: set[str] = set()

        for c in chunks or []:
            ctype = _safe_lower(c.get("chunk_type"))
            api_ref = _safe_str(c.get("api_reference_id"))
            svc_name = _safe_str(c.get("service_name"))
            svc_group = _safe_str(c.get("service_group"))
            svc_method = _safe_str(c.get("service_method"))
            prod_name = _safe_str(c.get("product_name"))
            sec_title = _safe_str(c.get("section_title"))

            if api_ref:
                api_refs.add(api_ref)
            if svc_name:
                service_names.add(svc_name)
            if svc_group:
                service_groups.add(svc_group)
            if svc_method:
                service_methods.add(svc_method)
            if prod_name:
                product_names.add(prod_name)
            if sec_title:
                section_titles.add(sec_title)

            if ctype == self.AUTH_CHUNK_TYPE:
                # Prefer structured metadata if present; otherwise parse from chunk_text.
                if api_ref:
                    auth_api_refs.add(api_ref)
                chunk_text = _safe_str(c.get("chunk_text"))
                for line in (chunk_text or "").splitlines():
                    m = self.AUTH_LINE_RE.search(line.strip())
                    if not m:
                        continue
                    matched_api_ref = _safe_str(m.group("api_ref"))
                    if matched_api_ref:
                        auth_api_refs.add(matched_api_ref)
                        auth_flows.append(
                            {
                                "api_reference_id": matched_api_ref,
                                "auth_hint": _safe_str(m.group("auth")),
                            }
                        )

            if ctype in self.OVERVIEW_CHUNK_TYPES:
                if api_ref:
                    # API overview/metadata counts as “request/response context anchor” for relationships.
                    api_refs.add(api_ref)

            if ctype in self.REQUEST_CHUNK_TYPES:
                if api_ref:
                    request_api_refs.add(api_ref)

            if ctype in self.RESPONSE_CHUNK_TYPES:
                if api_ref:
                    response_api_refs.add(api_ref)

            if ctype in self.ERROR_CHUNK_TYPES:
                if api_ref:
                    error_api_refs.add(api_ref)

        intents_set = set(intents or [])
        wants_auth_related = "authentication_intent" in intents_set
        wants_error_related = "error_intent" in intents_set
        wants_async_related = "async_intent" in intents_set

        return {
            "api_reference_ids": sorted(api_refs, key=lambda s: s.lower()),
            "service_names": sorted(service_names, key=lambda s: s.lower()),
            "service_groups": sorted(service_groups, key=lambda s: s.lower()),
            "service_methods": sorted(service_methods, key=lambda s: s.lower()),
            "product_names": sorted(product_names, key=lambda s: s.lower()),
            "section_titles": sorted(section_titles, key=lambda s: s.lower()),
            "auth_api_reference_ids": sorted(auth_api_refs, key=lambda s: s.lower()),
            "auth_flows": auth_flows,
            "request_api_reference_ids": sorted(request_api_refs, key=lambda s: s.lower()),
            "response_api_reference_ids": sorted(response_api_refs, key=lambda s: s.lower()),
            "error_api_reference_ids": sorted(error_api_refs, key=lambda s: s.lower()),
            "intent_wants": {
                "authentication_intent": wants_auth_related,
                "error_intent": wants_error_related,
                "async_intent": wants_async_related,
            },
        }

    def extract_relationships(
        self,
        *,
        chunks: list[dict[str, Any]],
        anchor: dict[str, Any],
        intents: list[str],
        api_entities: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Deterministically build relationships between “anchor” entities
        and other entities found in retrieved chunks.
        """
        relationships: list[dict[str, Any]] = []

        anchor_api = _safe_str(anchor.get("api_reference_id"))
        anchor_service = _safe_str(anchor.get("service_name"))
        anchor_group = _safe_str(anchor.get("service_group"))
        anchor_method = _safe_str(anchor.get("service_method"))
        anchor_product = _safe_str(anchor.get("product_name"))
        anchor_section = _safe_str(anchor.get("section_title"))
        anchor_intents = set(intents or [])

        def add_relationship(
            *,
            rule: str,
            from_entity: dict[str, Any],
            to_entity: dict[str, Any],
            strength: str,
            evidence: list[dict[str, Any]],
        ) -> None:
            if not from_entity or not to_entity:
                return
            # Ensure deterministic ordering/uniqueness (same rule + ids).
            key = (rule, from_entity.get("id"), to_entity.get("id"))
            if any((r.get("rule"), r.get("from", {}).get("id"), r.get("to", {}).get("id")) == key for r in relationships):
                return
            relationships.append(
                {
                    "rule": rule,
                    "from": from_entity,
                    "to": to_entity,
                    "strength": strength,
                    "evidence": evidence,
                }
            )

        # Build “primary from” entities; always include at least an API anchor if possible.
        from_api = {"type": "api", "id": anchor_api} if anchor_api else None
        from_service = {"type": "service", "id": anchor_service} if anchor_service else None
        from_group = {"type": "service_group", "id": anchor_group} if anchor_group else None
        from_product = {"type": "product", "id": anchor_product} if anchor_product else None
        from_section = {"type": "section", "id": anchor_section} if anchor_section else None

        # Pre-index chunk metadata for deterministic evidence.
        chunks_by_api: dict[str, list[dict[str, Any]]] = {}
        chunks_by_service: dict[str, list[dict[str, Any]]] = {}
        chunks_by_group: dict[str, list[dict[str, Any]]] = {}
        chunks_by_product: dict[str, list[dict[str, Any]]] = {}
        for c in chunks or []:
            api_ref = _safe_str(c.get("api_reference_id"))
            svc = _safe_str(c.get("service_name"))
            grp = _safe_str(c.get("service_group"))
            prod = _safe_str(c.get("product_name"))
            if api_ref:
                chunks_by_api.setdefault(api_ref, []).append(c)
            if svc:
                chunks_by_service.setdefault(svc, []).append(c)
            if grp:
                chunks_by_group.setdefault(grp, []).append(c)
            if prod:
                chunks_by_product.setdefault(prod, []).append(c)

        # 1) Same service_name across chunks → related (APIs sharing the same service_name)
        if anchor_service:
            anchor_service_l = _safe_lower(anchor_service)
            from_entity_for_service = from_api or from_service
            if from_entity_for_service:
                matching_api_refs: set[str] = set()
                for svc_name, svc_chunks in (chunks_by_service or {}).items():
                    if _safe_lower(svc_name) != anchor_service_l:
                        continue
                    for c in svc_chunks or []:
                        api_ref_val = _safe_str(c.get("api_reference_id"))
                        if api_ref_val:
                            matching_api_refs.add(api_ref_val)

                for other_api in sorted(matching_api_refs, key=lambda s: s.lower()):
                    if anchor_api and other_api.lower() == anchor_api.lower():
                        continue
                    add_relationship(
                        rule="same_service_name_across_chunks",
                        from_entity=from_entity_for_service,
                        to_entity={"type": "api", "id": other_api},
                        strength="medium",
                        evidence=[
                            {"matching_key": "service_name", "service_name": anchor_service},
                            {"note": "other API reference id shares the same service_name"},
                        ],
                    )

        # 2) Same api_reference_id → strongly related (contract sections for that API)
        if from_api and anchor_api:
            api_chunks = chunks_by_api.get(anchor_api, []) if anchor_api else []
            chunk_types = {_safe_lower(c.get("chunk_type")) for c in api_chunks if c.get("chunk_type")}
            has_auth = self.AUTH_CHUNK_TYPE in chunk_types
            has_request = bool(chunk_types & self.REQUEST_CHUNK_TYPES)
            has_response = bool(chunk_types & self.RESPONSE_CHUNK_TYPES)
            has_error = bool(chunk_types & self.ERROR_CHUNK_TYPES)
            has_overview_or_meta = bool(chunk_types & self.OVERVIEW_CHUNK_TYPES)

            if has_auth:
                add_relationship(
                    rule="same_api_reference_id_auth_flow",
                    from_entity=from_api,
                    to_entity={"type": "authentication_flow", "id": f"auth:{anchor_api}"},
                    strength="high",
                    evidence=[{"matching_key": "api_reference_id", "api_reference_id": anchor_api}],
                )
            if has_request:
                add_relationship(
                    rule="same_api_reference_id_request_sections",
                    from_entity=from_api,
                    to_entity={"type": "request_section", "id": f"request:{anchor_api}"},
                    strength="high",
                    evidence=[{"matching_key": "api_reference_id", "api_reference_id": anchor_api}],
                )
            if has_response:
                add_relationship(
                    rule="same_api_reference_id_response_sections",
                    from_entity=from_api,
                    to_entity={"type": "response_section", "id": f"response:{anchor_api}"},
                    strength="high",
                    evidence=[{"matching_key": "api_reference_id", "api_reference_id": anchor_api}],
                )
            if has_error:
                add_relationship(
                    rule="same_api_reference_id_error_flow",
                    from_entity=from_api,
                    to_entity={"type": "error_flow", "id": f"error:{anchor_api}"},
                    strength="high",
                    evidence=[{"matching_key": "api_reference_id", "api_reference_id": anchor_api}],
                )
            if has_overview_or_meta:
                add_relationship(
                    rule="same_api_reference_id_overview_metadata",
                    from_entity=from_api,
                    to_entity={"type": "api_overview_section", "id": f"overview:{anchor_api}"},
                    strength="medium",
                    evidence=[{"matching_key": "api_reference_id", "api_reference_id": anchor_api}],
                )

            # Additionally reflect “what depends on what” inside the API without building a graph.
            self._add_internal_api_relationships(
                relationships=relationships,
                anchor_api=anchor_api,
                api_chunks=api_chunks,
                add_relationship_fn=add_relationship,
            )

        # 3) Same service_group → medium relation (APIs sharing the same service_group)
        if anchor_group:
            anchor_group_l = _safe_lower(anchor_group)
            from_entity_for_group = from_api or from_group
            if from_entity_for_group:
                matching_api_refs: set[str] = set()
                for grp_name, grp_chunks in (chunks_by_group or {}).items():
                    if _safe_lower(grp_name) != anchor_group_l:
                        continue
                    for c in grp_chunks or []:
                        api_ref_val = _safe_str(c.get("api_reference_id"))
                        if api_ref_val:
                            matching_api_refs.add(api_ref_val)

                for other_api in sorted(matching_api_refs, key=lambda s: s.lower()):
                    if anchor_api and other_api.lower() == anchor_api.lower():
                        continue
                    add_relationship(
                        rule="same_service_group_across_chunks",
                        from_entity=from_entity_for_group,
                        to_entity={"type": "api", "id": other_api},
                        strength="medium",
                        evidence=[
                            {"matching_key": "service_group", "service_group": anchor_group},
                            {"note": "other API reference id shares the same service_group"},
                        ],
                    )

        # 4) Authentication chunks tied to API overview/request chunks (same api_reference_id)
        if from_api and anchor_api:
            api_chunks = chunks_by_api.get(anchor_api, []) or []
            has_auth = any(_safe_lower(c.get("chunk_type")) == self.AUTH_CHUNK_TYPE for c in api_chunks)
            has_overview_or_request = any(
                _safe_lower(c.get("chunk_type")) in (self.OVERVIEW_CHUNK_TYPES | self.REQUEST_CHUNK_TYPES)
                for c in api_chunks
            )
            if has_auth and has_overview_or_request:
                add_relationship(
                    rule="authentication_link_to_api_context",
                    from_entity={"type": "authentication_flow", "id": f"auth:{anchor_api}"},
                    to_entity={"type": "api", "id": anchor_api},
                    strength="high",
                    evidence=[
                        {"matching_key": "api_reference_id", "api_reference_id": anchor_api},
                        {"chunk_types_present": sorted({_safe_lower(c.get("chunk_type")) for c in api_chunks if c.get("chunk_type")})},
                    ],
                )

        # 5) Error response chunks tied to request/response chunks (same api_reference_id)
        if from_api and anchor_api:
            api_chunks = chunks_by_api.get(anchor_api, []) or []
            has_error = any(_safe_lower(c.get("chunk_type")) in self.ERROR_CHUNK_TYPES for c in api_chunks)
            has_req_or_resp = any(
                _safe_lower(c.get("chunk_type")) in (self.REQUEST_CHUNK_TYPES | self.RESPONSE_CHUNK_TYPES)
                for c in api_chunks
            )
            if has_error and has_req_or_resp:
                add_relationship(
                    rule="error_flow_link_to_request_response",
                    from_entity={"type": "error_flow", "id": f"error:{anchor_api}"},
                    to_entity={"type": "api", "id": anchor_api},
                    strength="high",
                    evidence=[
                        {"matching_key": "api_reference_id", "api_reference_id": anchor_api},
                        {"chunk_types_present": sorted({_safe_lower(c.get("chunk_type")) for c in api_chunks if c.get("chunk_type")})},
                    ],
                )

        # 6) Async APIs related to callback/status APIs (service_pattern heuristic)
        # Deterministic MVP: if async_intent is detected and any anchor chunk’s service_pattern mentions callback/asynch,
        # relate the API to a “sync/async integration” bucket.
        if anchor_api:
            api_chunks = chunks_by_api.get(anchor_api, []) or []
            patterns = [(_safe_str(c.get("service_pattern"))).lower() for c in api_chunks]
            joined_patterns = " ".join(patterns)
            mentions_async = any(token in joined_patterns for token in ["asynch", "asynchronous", "async", "callback"])
            if ("async_intent" in anchor_intents or mentions_async) and mentions_async:
                add_relationship(
                    rule="async_integration_link",
                    from_entity={"type": "api", "id": anchor_api},
                    to_entity={"type": "async_integration", "id": f"async:{anchor_api}"},
                    strength="medium" if "async_intent" in anchor_intents else "low",
                    evidence=[
                        {"matching_key": "service_pattern", "service_pattern_tokens": [p for p in patterns if p]},
                    ],
                )

        # 7) Product workflow sections tied by section/product metadata
        if anchor_product or anchor_section:
            # Only consider explicit product_section_chunk to keep deterministic signal purity.
            section_counts_by_product: dict[str, dict[str, int]] = {}
            original_titles_by_key: dict[tuple[str, str], str] = {}

            for c in chunks or []:
                if _safe_lower(c.get("chunk_type")) != self.PRODUCT_CHUNK_TYPE:
                    continue
                prod = _safe_str(c.get("product_name"))
                sec = _safe_str(c.get("section_title"))
                if not prod or not sec:
                    continue

                prod_l = _safe_lower(prod)
                sec_l = _safe_lower(sec)
                section_counts_by_product.setdefault(prod_l, {})
                section_counts_by_product[prod_l][sec_l] = section_counts_by_product[prod_l].get(sec_l, 0) + 1
                original_titles_by_key[(prod_l, sec_l)] = sec

            if anchor_product:
                anchor_prod_l = _safe_lower(anchor_product)
                sec_map = section_counts_by_product.get(anchor_prod_l, {}) or {}
                for sec_l, count in sorted(sec_map.items(), key=lambda kv: (-kv[1], kv[0])):
                    sec_original = original_titles_by_key.get((anchor_prod_l, sec_l)) or sec_l
                    is_anchor_section = bool(anchor_section) and sec_l == _safe_lower(anchor_section)
                    strength = "high" if is_anchor_section and count >= 2 else "medium"
                    add_relationship(
                        rule="product_workflow_section_link",
                        from_entity={"type": "product", "id": anchor_product},
                        to_entity={"type": "product_section", "id": sec_original},
                        strength=strength,
                        evidence=[
                            {
                                "matching_key": "product_name+section_title",
                                "product_name": anchor_product,
                                "section_title": sec_original,
                                "chunk_count": count,
                            }
                        ],
                    )
            elif anchor_section:
                # Anchor by section title only: connect it to all products that contain it.
                anchor_sec_l = _safe_lower(anchor_section)
                for prod_l, sec_map in section_counts_by_product.items():
                    if anchor_sec_l not in sec_map:
                        continue
                    count = sec_map.get(anchor_sec_l) or 0
                    sec_original = original_titles_by_key.get((prod_l, anchor_sec_l)) or anchor_section
                    # Best-effort product name recovery from the chunks.
                    prod_original = ""
                    for c in chunks or []:
                        if _safe_lower(c.get("product_name")) == prod_l and _safe_lower(c.get("section_title")) == anchor_sec_l:
                            prod_original = _safe_str(c.get("product_name"))
                            break
                    prod_original = prod_original or prod_l
                    add_relationship(
                        rule="product_workflow_section_link",
                        from_entity={"type": "section", "id": anchor_section},
                        to_entity={"type": "product", "id": prod_original},
                        strength="medium" if count > 0 else "low",
                        evidence=[
                            {
                                "matching_key": "product_name+section_title",
                                "section_title": sec_original,
                                "product_name": prod_original,
                            }
                        ],
                    )

        # 8) General “metadata references” links for request/response/auth/error within same API.
        # This keeps primary_entity -> related_entities populated even when the anchor is broad.
        if from_api and anchor_api:
            api_chunks = chunks_by_api.get(anchor_api, []) or []
            chunk_types = sorted({_safe_lower(c.get("chunk_type")) for c in api_chunks if c.get("chunk_type")})
            add_relationship(
                rule="api_internal_section_inventory",
                from_entity={"type": "api", "id": anchor_api},
                to_entity={"type": "metadata_inventory", "id": f"inventory:{anchor_api}"},
                strength="medium" if chunk_types else "low",
                evidence=[{"chunk_types_present": chunk_types}],
            )

        # Final deterministic ordering: highest strength first, then rule name.
        strength_order = {"high": 0, "medium": 1, "low": 2}
        relationships.sort(key=lambda r: (strength_order.get(r.get("strength"), 3), str(r.get("rule") or "")))
        return relationships

    def _add_internal_api_relationships(
        self,
        *,
        relationships: list[dict[str, Any]],
        anchor_api: str,
        api_chunks: list[dict[str, Any]],
        add_relationship_fn,
    ) -> None:
        if not anchor_api:
            return

        chunk_types = {_safe_lower(c.get("chunk_type")) for c in api_chunks if c.get("chunk_type")}
        has_overview = bool(chunk_types & self.OVERVIEW_CHUNK_TYPES)
        has_auth = bool(chunk_types & {self.AUTH_CHUNK_TYPE})
        has_request = bool(chunk_types & self.REQUEST_CHUNK_TYPES)
        has_response = bool(chunk_types & self.RESPONSE_CHUNK_TYPES)
        has_error = bool(chunk_types & self.ERROR_CHUNK_TYPES)

        if has_overview and has_request:
            add_relationship_fn(
                rule="overview_to_request",
                from_entity={"type": "api_section", "id": f"overview:{anchor_api}"},
                to_entity={"type": "api_section", "id": f"request:{anchor_api}"},
                strength="medium",
                evidence=[{"matching_key": "chunk_type", "chunk_types_present": sorted(chunk_types)}],
            )
        if has_request and has_response:
            add_relationship_fn(
                rule="request_to_response",
                from_entity={"type": "api_section", "id": f"request:{anchor_api}"},
                to_entity={"type": "api_section", "id": f"response:{anchor_api}"},
                strength="high",
                evidence=[{"matching_key": "chunk_type", "chunk_types_present": sorted(chunk_types)}],
            )
        if has_auth and (has_overview or has_request):
            add_relationship_fn(
                rule="authentication_supports_api_flow",
                from_entity={"type": "authentication_flow", "id": f"auth:{anchor_api}"},
                to_entity={"type": "api_flow", "id": f"api_flow:{anchor_api}"},
                strength="high",
                evidence=[{"matching_key": "chunk_type", "chunk_types_present": sorted(chunk_types)}],
            )
        if has_error and (has_request or has_response):
            add_relationship_fn(
                rule="error_supports_api_contract",
                from_entity={"type": "error_flow", "id": f"error:{anchor_api}"},
                to_entity={"type": "api_contract", "id": f"contract:{anchor_api}"},
                strength="high",
                evidence=[{"matching_key": "chunk_type", "chunk_types_present": sorted(chunk_types)}],
            )

    def build_impact_summary(
        self,
        *,
        anchor: dict[str, Any],
        relationships: list[dict[str, Any]],
        intents: list[str],
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        # Primary entities come from anchor.
        primary_entities: list[dict[str, Any]] = []
        related_entities: list[dict[str, Any]] = []
        potential_impacts: list[str] = []
        relationship_summary: list[dict[str, Any]] = []

        anchor_api = _safe_str(anchor.get("api_reference_id"))
        anchor_service = _safe_str(anchor.get("service_name"))
        anchor_group = _safe_str(anchor.get("service_group"))
        anchor_product = _safe_str(anchor.get("product_name"))
        anchor_section = _safe_str(anchor.get("section_title"))

        if anchor_api:
            primary_entities.append({"type": "api", "id": anchor_api})
        if anchor_service:
            primary_entities.append({"type": "service", "id": anchor_service})
        if anchor_group:
            primary_entities.append({"type": "service_group", "id": anchor_group})
        if anchor_product:
            primary_entities.append({"type": "product", "id": anchor_product})
        if anchor_section:
            primary_entities.append({"type": "section", "id": anchor_section})

        # Translate relationship rules into impact statements deterministically.
        strength_order = {"high": 3, "medium": 2, "low": 1}
        best_strength = "low"
        for rel in relationships or []:
            strength = str(rel.get("strength") or "low").lower()
            if strength_order.get(strength, 0) > strength_order.get(best_strength, 0):
                best_strength = strength

            relationship_summary.append(
                {
                    "rule": rel.get("rule"),
                    "from": rel.get("from"),
                    "to": rel.get("to"),
                    "strength": strength,
                }
            )

            to_ent = rel.get("to") or {}
            to_ent_id = _safe_str(to_ent.get("id"))
            to_ent_type = _safe_str(to_ent.get("type"))
            if to_ent_type and to_ent_id:
                related_entities.append({"type": to_ent_type, "id": to_ent_id})

        # Deterministic potential impacts based on presence of relationship rules.
        rule_names = {str(r.get("rule") or "").strip().lower() for r in relationship_summary or []}
        intents_set = set(intents or [])

        if any(("authentication" in rn) or ("auth_flow" in rn) for rn in rule_names):
            if anchor_api:
                potential_impacts.append(f"Authentication requirements for API {anchor_api} may be impacted.")
            else:
                potential_impacts.append("Authentication requirements for the related APIs may be impacted.")

        if any("error" in rn for rn in rule_names):
            if anchor_api:
                potential_impacts.append(f"Error handling and failure response contract for API {anchor_api} may be impacted.")
            else:
                potential_impacts.append("Error handling and failure response contracts may be impacted.")

        if any("request" in rn or "response" in rn for rn in rule_names):
            if anchor_api:
                potential_impacts.append(f"Request/response parameter expectations for API {anchor_api} may be impacted.")

        if any("async" in rn for rn in rule_names) or "async_intent" in intents_set:
            potential_impacts.append("Asynchronous/callback integration patterns may be impacted.")

        if any("product_workflow_section_link" in rn for rn in rule_names):
            if anchor_product:
                potential_impacts.append(f"Product workflow guidance for {anchor_product} may need review.")

        if not potential_impacts:
            # Fall back to a metadata relationship inventory statement.
            if anchor_api:
                potential_impacts.append(f"Related contract sections for API {anchor_api} may be impacted.")
            else:
                potential_impacts.append("Related documentation sections may be impacted.")

        # Deduplicate related_entities/potential_impacts deterministically.
        primary_seen = {(e.get("type"), _safe_str(e.get("id"))) for e in primary_entities if e}
        rel_seen: set[tuple[str, str]] = set()
        rel_out: list[dict[str, Any]] = []
        for e in related_entities:
            key = (e.get("type"), _safe_str(e.get("id")))
            if not key[0] or not key[1]:
                continue
            if key in primary_seen or key in rel_seen:
                continue
            rel_seen.add(key)
            rel_out.append(e)

        impact_confidence = best_strength if best_strength in {"high", "medium", "low"} else "low"

        return {
            "primary_entities": primary_entities,
            "related_entities": rel_out,
            "potential_impacts": self._dedupe_text(potential_impacts),
            "relationship_summary": relationship_summary,
            "impact_confidence": impact_confidence,
        }

    def _dedupe_text(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in items or []:
            text = _safe_str(raw)
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out


impact_analysis_service = ImpactAnalysisService()

