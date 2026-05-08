from __future__ import annotations

from typing import Any

from app.core.config import settings

INSUFFICIENT_CONTEXT_ANSWER = "I could not find enough information in the selected knowledge base to answer this confidently."


class ConfidenceService:
    """
    Deterministic, retrieval-grounded confidence scoring.
    This service never raises and never makes external calls.
    """

    def score(
        self,
        *,
        answer: str,
        llm_status: str | None = None,
        results: list[dict[str, Any]] | None = None,
        diagnostics: dict[str, Any] | None = None,
        detected_intents: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            if not getattr(settings, "ENABLE_CONFIDENCE_SCORING", True):
                return {"score": 0.0, "label": "low", "reasons": ["confidence scoring disabled"]}

            if self._is_fallback(answer=answer, llm_status=llm_status):
                return {"score": 0.0, "label": "low", "reasons": ["insufficient-context fallback"]}

            docs = results or []
            diag = diagnostics or {}
            intents = {str(x).strip().lower() for x in (detected_intents or []) if str(x).strip()}

            score = 0.0
            reasons: list[str] = []

            # 1) Final context strength (positive / negative)
            final_context_count = self._as_int(diag.get("final_context_count"), default=len(docs))
            if final_context_count >= 5:
                score += 0.22
                reasons.append("multiple supporting chunks")
            elif final_context_count >= 3:
                score += 0.14
                reasons.append("adequate supporting chunks")
            elif final_context_count >= 1:
                score += 0.06
                reasons.append("limited supporting chunks")
            else:
                score -= 0.16
                reasons.append("very few chunks")

            # 2) Metadata coverage quality
            metadata_coverage = self._metadata_coverage(diag=diag, docs=docs)
            if metadata_coverage >= 0.75:
                score += 0.18
                reasons.append("strong metadata matches")
            elif metadata_coverage >= 0.45:
                score += 0.10
                reasons.append("moderate metadata matches")
            else:
                score -= 0.10
                reasons.append("weak metadata matches")

            # 3) Retrieval mode / hybrid agreement
            retrieval_mode = str(diag.get("retrieval_mode") or "").strip().lower()
            hybrid_used = bool(diag.get("hybrid_fusion_used"))
            if retrieval_mode == "hybrid" or hybrid_used:
                score += 0.12
                reasons.append("hybrid retrieval agreement")
            elif retrieval_mode:
                score += 0.04
                reasons.append(f"retrieval mode: {retrieval_mode}")

            # 4) Rescue/fallback penalties
            if bool(diag.get("fallback_triggered")):
                score -= 0.20
                reasons.append("retrieval fallback path used")
            vector_outcome = str(diag.get("vector_retrieval_outcome") or "").strip().lower()
            if "empty" in vector_outcome or "fallback" in vector_outcome:
                score -= 0.08
                reasons.append("vector retrieval rescue path")

            # 5) Rerank/top score quality
            top_combined_score = self._as_float(diag.get("top_combined_score"))
            if top_combined_score is not None:
                if top_combined_score >= 0.75:
                    score += 0.14
                    reasons.append("strong rerank agreement")
                elif top_combined_score >= 0.45:
                    score += 0.08
                    reasons.append("moderate rerank agreement")
                else:
                    score -= 0.05
                    reasons.append("weak rerank agreement")

            # 6) Chunk diversity and generic-only penalty
            diversity = self._chunk_diversity(diag=diag, docs=docs, final_context_count=final_context_count)
            if diversity >= 0.5:
                score += 0.12
                reasons.append("good chunk diversity")
            elif diversity >= 0.25:
                score += 0.06
                reasons.append("moderate chunk diversity")
            else:
                score -= 0.08
                reasons.append("low context diversity")

            chunk_types = self._chunk_types(diag=diag, docs=docs)
            if chunk_types and all("generic" in ctype for ctype in chunk_types):
                score -= 0.10
                reasons.append("generic chunks only")

            # 7) Intent-aligned evidence
            alignment = self._intent_alignment_score(intents=intents, docs=docs)
            if alignment >= 0.75:
                score += 0.12
                reasons.append("intent-aligned chunks")
            elif alignment >= 0.35:
                score += 0.06
                reasons.append("partial intent alignment")
            elif intents:
                score -= 0.05
                reasons.append("weak intent alignment")

            # 8) API/service match signal
            if self._has_api_service_match(docs):
                score += 0.08
                reasons.append("api/service metadata matches")

            final_score = self._clamp(score, 0.0, 1.0)
            label = self._label_for_score(final_score)
            return {"score": round(final_score, 4), "label": label, "reasons": self._dedupe(reasons)}
        except Exception:
            return {"score": 0.0, "label": "low", "reasons": ["confidence scoring error"]}

    def _is_fallback(self, *, answer: str, llm_status: str | None) -> bool:
        if str(llm_status or "").strip().lower() == "fallback_insufficient_context":
            return True
        return (answer or "").strip() == INSUFFICIENT_CONTEXT_ANSWER

    def _metadata_coverage(self, *, diag: dict[str, Any], docs: list[dict[str, Any]]) -> float:
        coverage = diag.get("source_metadata_coverage")
        if isinstance(coverage, dict) and coverage:
            vals = [self._as_float(v) for v in coverage.values()]
            vals = [v for v in vals if v is not None]
            if vals:
                return self._clamp(sum(vals) / len(vals), 0.0, 1.0)

        if not docs:
            return 0.0
        keys = ("document_type", "product_name", "section_title", "api_reference_id", "service_name")
        filled = 0
        for item in docs:
            filled += sum(1 for key in keys if item.get(key) not in (None, ""))
        total = len(docs) * len(keys)
        if total <= 0:
            return 0.0
        return self._clamp(filled / total, 0.0, 1.0)

    def _chunk_types(self, *, diag: dict[str, Any], docs: list[dict[str, Any]]) -> set[str]:
        top_chunk_types = diag.get("top_chunk_types")
        if isinstance(top_chunk_types, list) and top_chunk_types:
            return {str(x).strip().lower() for x in top_chunk_types if str(x).strip()}
        return {
            str(item.get("chunk_type") or "").strip().lower()
            for item in docs
            if str(item.get("chunk_type") or "").strip()
        }

    def _chunk_diversity(self, *, diag: dict[str, Any], docs: list[dict[str, Any]], final_context_count: int) -> float:
        unique_types = self._chunk_types(diag=diag, docs=docs)
        denom = max(final_context_count, len(docs), 1)
        return self._clamp(len(unique_types) / denom, 0.0, 1.0)

    def _intent_alignment_score(self, *, intents: set[str], docs: list[dict[str, Any]]) -> float:
        if not intents or not docs:
            return 0.0

        matches = 0
        for item in docs:
            chunk_type = str(item.get("chunk_type") or "").lower()
            text = " ".join(
                [
                    str(item.get("chunk_text") or ""),
                    str(item.get("section_title") or ""),
                    str(item.get("service_pattern") or ""),
                ]
            ).lower()
            aligned = False
            if "authentication_intent" in intents and ("authentication" in chunk_type or "token" in text or "bearer" in text):
                aligned = True
            if "error_intent" in intents and ("failed" in chunk_type or "error" in chunk_type or "returncode" in text):
                aligned = True
            if "parameter_intent" in intents and ("parameter" in chunk_type or "parameter" in text):
                aligned = True
            if "async_intent" in intents and ("asynch" in text or "callback" in text):
                aligned = True
            if "overview_intent" in intents and ("overview" in chunk_type or "purpose" in text):
                aligned = True
            if aligned:
                matches += 1

        return self._clamp(matches / max(len(docs), 1), 0.0, 1.0)

    def _has_api_service_match(self, docs: list[dict[str, Any]]) -> bool:
        return any(
            item.get("api_reference_id") not in (None, "")
            or item.get("service_name") not in (None, "")
            or item.get("service_method") not in (None, "")
            for item in docs
        )

    def _label_for_score(self, score: float) -> str:
        if score >= float(getattr(settings, "CONFIDENCE_HIGH_THRESHOLD", 0.75)):
            return "high"
        if score >= float(getattr(settings, "CONFIDENCE_MEDIUM_THRESHOLD", 0.45)):
            return "medium"
        return "low"

    def _as_int(self, value: Any, *, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except Exception:
            return default

    def _as_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out


confidence_service = ConfidenceService()
