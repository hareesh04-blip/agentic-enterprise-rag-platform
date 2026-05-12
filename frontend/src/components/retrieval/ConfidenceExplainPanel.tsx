import type { QueryResponse } from "../../types/query";
import { diagBool, diagString, diagStringArray } from "../../lib/diagnosticsHelpers";

interface ConfidenceExplainPanelProps {
  confidence: QueryResponse["confidence"];
  diagnostics: Record<string, unknown> | undefined;
  llmStatus?: string | null;
  className?: string;
}

function qualityLabel(bucket: string | undefined): string {
  const b = String(bucket || "").toLowerCase();
  if (b.includes("high") || b === "strong") return "Strong";
  if (b.includes("medium") || b.includes("mid")) return "Moderate";
  if (b.includes("low") || b.includes("weak")) return "Limited";
  if (b) return bucket ?? "—";
  return "—";
}

function semanticMatchFromTypes(types: string[]): string {
  if (!types.length) return "—";
  const t = types.join(" ").toLowerCase();
  if (t.includes("semantic_summary")) return "High (semantic chunks)";
  if (t.includes("table_flattened") || t.includes("flattened")) return "High (structured table)";
  if (t.includes("generic")) return "Moderate (generic sections)";
  return "Moderate";
}

function coverageLabel(
  fallbackTriggered: boolean | undefined,
  promptChars: number | undefined,
  selectedChunks: number | undefined,
): string {
  if (fallbackTriggered) return "Insufficient — fallback triggered";
  const chars = promptChars ?? 0;
  const sel = selectedChunks ?? 0;
  if (sel <= 0 && chars <= 0) return "None visible";
  if (chars >= 4000 && sel >= 2) return "Complete";
  if (chars >= 1500 || sel >= 1) return "Partial";
  return "Thin";
}

function providerLine(llmStatus: string | undefined | null): { label: string; ok: boolean } {
  const s = String(llmStatus || "").toLowerCase();
  if (!s || s === "n/a") return { label: "Unknown", ok: false };
  if (s === "generated" || (s.includes("generated") && !s.includes("failure"))) {
    return { label: "Successful", ok: true };
  }
  if (s.includes("insufficient") || s.includes("failure") || s.includes("error")) {
    return { label: "Failure or insufficient context", ok: false };
  }
  return { label: "Successful", ok: true };
}

export function ConfidenceExplainPanel({
  confidence,
  diagnostics,
  llmStatus,
  className = "",
}: ConfidenceExplainPanelProps) {
  const d = diagnostics ?? {};
  const bucket = diagString(d, "vector_confidence_bucket");
  const topTypes = diagStringArray(d, "top_chunk_types");
  const fallbackTriggered = diagBool(d, "fallback_triggered");
  const promptChars =
    typeof d.final_prompt_context_chars === "number" ? d.final_prompt_context_chars : undefined;
  const selectedChunks =
    typeof d.selected_prompt_chunk_count === "number" ? d.selected_prompt_chunk_count : undefined;

  const retrievalQuality = qualityLabel(bucket);
  const semanticMatch = semanticMatchFromTypes(topTypes);
  const contextCoverage = coverageLabel(fallbackTriggered, promptChars, selectedChunks);
  const provider = providerLine(llmStatus ?? diagString(d, "llm_status"));

  const summaryFallback =
    fallbackTriggered === true
      ? "Retrieval context insufficient or gated by policy."
      : !provider.ok
        ? "Provider generation did not complete normally."
        : null;

  const diagScore =
    typeof d.confidence_score === "number" && !Number.isNaN(d.confidence_score)
      ? d.confidence_score
      : undefined;
  const diagLabel = typeof d.confidence_label === "string" ? d.confidence_label : undefined;

  const scorePct = Math.round(
    Math.max(0, Math.min(1, Number(confidence?.score ?? diagScore ?? 0))) * 100,
  );
  const label = String(confidence?.label || diagLabel || "low");

  return (
    <div className={`rounded-md border border-slate-200 bg-slate-50/80 p-3 text-xs text-slate-800 ${className}`}>
      <p className="font-semibold text-slate-900">
        Confidence overview · {label} ({scorePct}%)
      </p>
      <ul className="mt-2 space-y-1.5">
        <li>
          <span className="font-medium text-slate-700">Retrieval quality:</span> {retrievalQuality}
        </li>
        <li>
          <span className="font-medium text-slate-700">Semantic match:</span> {semanticMatch}
        </li>
        <li>
          <span className="font-medium text-slate-700">Context coverage:</span> {contextCoverage}
        </li>
        <li>
          <span className="font-medium text-slate-700">Provider generation:</span>{" "}
          <span className={provider.ok ? "text-emerald-800" : "text-rose-800"}>{provider.label}</span>
        </li>
      </ul>
      {summaryFallback ? (
        <p className="mt-2 border-t border-slate-200 pt-2 text-amber-900">{summaryFallback}</p>
      ) : null}
      {(() => {
        const fromApi = Array.isArray(confidence?.reasons) ? confidence.reasons : [];
        const fromDiag = Array.isArray(d.confidence_reasons)
          ? (d.confidence_reasons as unknown[]).map((x) => String(x))
          : [];
        const merged = fromApi.length ? fromApi : fromDiag;
        return merged.length ? (
          <p className="mt-2 text-[11px] text-slate-600">Signals: {merged.join(" · ")}</p>
        ) : null;
      })()}
    </div>
  );
}
