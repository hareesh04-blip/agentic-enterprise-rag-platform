import { useCallback, useEffect, useState } from "react";
import { AxiosError } from "axios";
import { DemoScenarioCards } from "../components/DemoScenarioCards";
import { ChunkTypeBadge } from "../components/retrieval/ChunkTypeBadge";
import { RetrievalJourneyPanel } from "../components/retrieval/RetrievalJourneyPanel";
import { RetrievalMetricsCards } from "../components/retrieval/RetrievalMetricsCards";
import { diagnosticsApi } from "../api/diagnosticsApi";
import { kbApi } from "../api/kbApi";
import { semanticCategoryLabel, semanticChunkCategory } from "../lib/chunkTypeMeta";
import type { RetrievalTestResponse } from "../types/diagnostics";
import type { KnowledgeBase } from "../types/kb";

const TOP_K_OPTIONS = [3, 6, 10, 15, 20];

export function RetrievalDiagnosticsPage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [kbId, setKbId] = useState<number | "">("");
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(6);
  const [loadingKbs, setLoadingKbs] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RetrievalTestResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await kbApi.listMyKnowledgeBases();
        if (!cancelled) {
          setKbs(list);
          if (list.length && kbId === "") {
            setKbId(list[0].id);
          }
        }
      } catch {
        if (!cancelled) setError("Could not load knowledge bases.");
      } finally {
        if (!cancelled) setLoadingKbs(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runTest = useCallback(
    async (presetQuestion?: string) => {
      const q = (presetQuestion ?? question).trim();
      if (kbId === "" || !q) return;
      if (presetQuestion !== undefined) setQuestion(presetQuestion);
      setRunning(true);
      setError(null);
      setResult(null);
      try {
        const data = await diagnosticsApi.runRetrievalTest({
          knowledge_base_id: Number(kbId),
          question: q,
          top_k: topK,
        });
        setResult(data);
      } catch (err) {
        if (err instanceof AxiosError) {
          const detail = err.response?.data?.detail;
          const msg =
            typeof detail === "string"
              ? detail
              : err.response?.status === 403
                ? "Access denied."
                : err.message || "Request failed.";
          setError(msg);
        } else {
          setError("Unexpected error.");
        }
      } finally {
        setRunning(false);
      }
    },
    [kbId, question, topK],
  );

  const chunkCount = result?.retrieved_chunk_count ?? 0;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Retrieval diagnostics</h2>
        <p className="text-sm text-slate-600">
          Run hybrid retrieval against a knowledge base without generating an LLM answer. Admin / super admin only.
        </p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            Knowledge base
            <select
              value={kbId === "" ? "" : String(kbId)}
              onChange={(e) => setKbId(e.target.value ? Number(e.target.value) : "")}
              disabled={loadingKbs || !kbs.length}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {loadingKbs ? (
                <option value="">Loading…</option>
              ) : kbs.length === 0 ? (
                <option value="">No accessible KBs</option>
              ) : (
                kbs.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))
              )}
            </select>
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Top K
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {TOP_K_OPTIONS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Question
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="Enter a question to test retrieval…"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <div className="mt-3">
          <DemoScenarioCards disabled={running || kbId === ""} onSelect={(preset) => void runTest(preset)} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void runTest()}
            disabled={running || kbId === "" || !question.trim()}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running ? "Running…" : "Run test"}
          </button>
        </div>
      </section>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>
      ) : null}

      {result ? (
        <div className="space-y-3">
          <section className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Query journey (retrieval-only)</h3>
            <p className="mt-1 text-[11px] text-slate-600">
              Hybrid merge and rerank stages reflect runtime flags; prompt assembly runs only in chat queries.
            </p>
            <div className="mt-3 space-y-3">
              <RetrievalMetricsCards diagnostics={result.diagnostics} />
              <RetrievalJourneyPanel
                question={result.question}
                diagnostics={result.diagnostics}
                mode="retrieval_only"
              />
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Summary</h3>
            <dl className="mt-2 grid grid-cols-1 gap-2 text-sm text-slate-800 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-medium text-slate-500">Retrieval mode</dt>
                <dd>{result.retrieval_mode}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500">Retrieved chunk count</dt>
                <dd>{result.retrieved_chunk_count}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500">Dominant document type</dt>
                <dd>{result.dominant_document_type}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500">Dominant product name</dt>
                <dd>{result.dominant_product_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500">Section coverage count</dt>
                <dd>{result.section_coverage_count}</dd>
              </div>
            </dl>
          </section>

          {chunkCount === 0 ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              No matching chunks found for this question.
            </div>
          ) : (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Ranked chunks</h3>
              <p className="mt-1 text-[11px] text-slate-500">
                Retrieved and reranked candidates (merge score shown). Expand a row for full preview text.
              </p>
              <div className="mt-3 space-y-3">
                {result.chunks.map((ch) => {
                  const cat = semanticChunkCategory(ch.chunk_type);
                  const catLabel = semanticCategoryLabel(cat);
                  return (
                    <details
                      key={`${ch.rank}-${ch.document_id}-${ch.chunk_id ?? "x"}`}
                      className="group rounded-md border border-slate-100 bg-slate-50/80 text-sm open:bg-white"
                    >
                      <summary className="cursor-pointer list-none p-3 [&::-webkit-details-marker]:hidden">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-semibold text-slate-800">#{ch.rank} · Rerank score {ch.score.toFixed(4)}</span>
                          <span className="text-[11px] text-slate-500 group-open:hidden">Expand</span>
                          <span className="hidden text-[11px] text-slate-500 group-open:inline">Collapse</span>
                        </div>
                        <p className="mt-1 font-medium text-slate-800">{ch.document_name || "Untitled document"}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600">
                            Retrieved
                          </span>
                          <ChunkTypeBadge chunkType={ch.chunk_type} showRaw />
                          <span className="text-[11px] text-slate-600">{catLabel}</span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs">
                          <span className="rounded border border-slate-200 bg-white px-2 py-0.5">doc type: {ch.document_type ?? "—"}</span>
                          {ch.section_title ? (
                            <span className="rounded border border-blue-200 bg-blue-50 px-2 py-0.5 text-blue-800">
                              section: {ch.section_title}
                            </span>
                          ) : null}
                          {ch.chunk_id ? (
                            <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-slate-600">id: {ch.chunk_id}</span>
                          ) : null}
                        </div>
                      </summary>
                      <div className="border-t border-slate-100 px-3 pb-3">
                        <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-700">{ch.content_preview || "—"}</p>
                      </div>
                    </details>
                  );
                })}
              </div>
            </section>
          )}

          <details className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <summary className="cursor-pointer font-semibold text-slate-800">Raw diagnostics</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded bg-white p-2 text-xs text-slate-700">
              {JSON.stringify(result.diagnostics, null, 2)}
            </pre>
          </details>
        </div>
      ) : null}
    </div>
  );
}
