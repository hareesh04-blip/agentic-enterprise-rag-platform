import type { ReactNode } from "react";
import { diagBool, diagNumber, diagString, diagStringArray } from "../../lib/diagnosticsHelpers";

export type RetrievalJourneyMode = "full" | "retrieval_only";

interface RetrievalJourneyPanelProps {
  question: string;
  diagnostics: Record<string, unknown> | undefined;
  llmStatus?: string | null;
  mode?: RetrievalJourneyMode;
  /** Length of generated answer (assistant messages only). */
  answerCharCount?: number;
  className?: string;
}

function Step({
  title,
  detail,
  accent,
}: {
  title: string;
  detail: ReactNode;
  accent?: "neutral" | "ok" | "warn";
}) {
  const bar =
    accent === "ok"
      ? "border-emerald-200 bg-emerald-50"
      : accent === "warn"
        ? "border-amber-200 bg-amber-50"
        : "border-slate-200 bg-white";
  return (
    <div className={`rounded-md border px-3 py-2 text-xs shadow-sm ${bar}`}>
      <p className="font-semibold text-slate-900">{title}</p>
      <div className="mt-1 text-slate-700">{detail}</div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="flex justify-center py-0.5 text-slate-400" aria-hidden>
      ↓
    </div>
  );
}

export function RetrievalJourneyPanel({
  question,
  diagnostics,
  llmStatus,
  mode = "full",
  answerCharCount,
  className = "",
}: RetrievalJourneyPanelProps) {
  const d = diagnostics ?? {};
  const intents = diagStringArray(d, "detected_intents");
  const intentsDisplay = intents.length ? intents.join(", ") : "—";

  const vectorCount =
    diagNumber(d, "vector_results_count") ??
    diagNumber(d, "vector_candidate_count") ??
    diagNumber(d, "retrieved_chunk_count");

  const retrievedChunkCount = diagNumber(d, "retrieved_chunk_count") ?? vectorCount;
  const hybrid = diagBool(d, "hybrid_fusion_used");
  const rerank = diagString(d, "rerank_strategy") ?? "metadata rerank (when enabled)";
  const selectedPrompt = diagNumber(d, "selected_prompt_chunk_count");
  const promptChars = diagNumber(d, "final_prompt_context_chars");
  const keywordCount = diagNumber(d, "keyword_candidate_count");
  const fusionCount = diagNumber(d, "fusion_candidate_count");

  const llm = llmStatus ?? diagString(d, "llm_status") ?? "—";

  const questionPreview =
    question.length > 140 ? `${question.slice(0, 137)}…` : question || "—";

  return (
    <div className={`space-y-0 ${className}`}>
      <Step
        title="Question"
        detail={<span className="whitespace-pre-wrap">{questionPreview}</span>}
      />
      <Arrow />
      <Step
        title="Intent detection"
        detail={
          <span>
            <span className="font-medium text-slate-800">Detected intents:</span> {intentsDisplay}
          </span>
        }
        accent={intents.length ? "ok" : "neutral"}
      />
      <Arrow />
      <Step
        title="Vector retrieval"
        detail={
          <ul className="list-inside list-disc space-y-0.5 text-[11px]">
            <li>
              Candidates / results:{" "}
              <span className="font-mono">{vectorCount ?? "—"}</span>
            </li>
            {keywordCount != null ? (
              <li>
                Keyword candidates (hybrid path): <span className="font-mono">{keywordCount}</span>
              </li>
            ) : null}
          </ul>
        }
      />
      <Arrow />
      <Step
        title="Hybrid merge"
        detail={
          <span>
            Fusion{" "}
            <span className="font-semibold">{hybrid === true ? "used" : hybrid === false ? "not used" : "—"}</span>
            {fusionCount != null ? (
              <>
                {" "}
                · merged candidates <span className="font-mono">{fusionCount}</span>
              </>
            ) : null}
          </span>
        }
        accent={hybrid === true ? "ok" : "neutral"}
      />
      <Arrow />
      <Step
        title="Metadata rerank"
        detail={
          <span>
            Strategy: <span className="font-mono text-[11px]">{rerank}</span>
            {retrievedChunkCount != null ? (
              <>
                {" "}
                · ranked chunks <span className="font-mono">{retrievedChunkCount}</span>
              </>
            ) : null}
          </span>
        }
      />
      <Arrow />
      <Step
        title="Prompt context"
        detail={
          mode === "retrieval_only" ? (
            <span className="text-slate-600">
              Retrieval-only run — showing top-ranked chunks below (no LLM prompt assembly). Retrieved count:{" "}
              <span className="font-mono">{retrievedChunkCount ?? "—"}</span>
            </span>
          ) : (
            <ul className="list-inside list-disc space-y-0.5 text-[11px]">
              <li>
                Selected prompt chunks: <span className="font-mono">{selectedPrompt ?? "—"}</span>
              </li>
              <li>
                Final prompt context size: <span className="font-mono">{promptChars ?? "—"}</span> chars
              </li>
            </ul>
          )
        }
        accent={mode === "full" && (selectedPrompt ?? 0) > 0 ? "ok" : "neutral"}
      />
      {mode === "full" ? (
        <>
          <Arrow />
          <Step
            title="LLM response"
            detail={
              <ul className="list-inside list-disc space-y-0.5 text-[11px]">
                <li>
                  llm_status: <span className="font-mono">{llm}</span>
                </li>
                {answerCharCount != null ? (
                  <li>
                    Answer length: <span className="font-mono">{answerCharCount}</span> chars
                  </li>
                ) : null}
              </ul>
            }
            accent={String(llm).toLowerCase().includes("ok") || String(llm).toLowerCase() === "success" ? "ok" : "neutral"}
          />
        </>
      ) : null}
    </div>
  );
}
