import { diagNumber, diagString } from "../../lib/diagnosticsHelpers";

interface RetrievalMetricsCardsProps {
  diagnostics: Record<string, unknown> | undefined;
  llmProvider?: string | null;
  answerCharCount?: number;
  className?: string;
}

export function RetrievalMetricsCards({
  diagnostics,
  llmProvider,
  answerCharCount,
  className = "",
}: RetrievalMetricsCardsProps) {
  const d = diagnostics ?? {};
  const retrieved = diagNumber(d, "retrieved_chunk_count") ?? diagNumber(d, "vector_results_count");
  const reranked = diagNumber(d, "reranked_result_count") ?? retrieved;
  const promptChunks = diagNumber(d, "selected_prompt_chunk_count");
  const provider = llmProvider ?? diagString(d, "llm_provider") ?? "—";

  const cards: Array<{ label: string; value: string }> = [
    { label: "Retrieved chunks", value: retrieved != null ? String(retrieved) : "—" },
    { label: "Reranked chunks", value: reranked != null ? String(reranked) : "—" },
    { label: "Prompt chunks", value: promptChunks != null ? String(promptChunks) : "—" },
    {
      label: "Answer chars",
      value: answerCharCount != null ? String(answerCharCount) : "—",
    },
    { label: "Runtime provider", value: String(provider).toUpperCase() },
  ];

  return (
    <div className={`grid grid-cols-2 gap-2 md:grid-cols-5 ${className}`}>
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-md border border-slate-200 bg-white px-2 py-2 text-center shadow-sm"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{c.label}</p>
          <p className="mt-1 truncate text-sm font-semibold text-slate-900" title={c.value}>
            {c.value}
          </p>
        </div>
      ))}
    </div>
  );
}
