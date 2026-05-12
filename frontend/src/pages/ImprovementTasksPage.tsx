import { useCallback, useEffect, useMemo, useState } from "react";
import { AxiosError } from "axios";
import { useSearchParams } from "react-router-dom";
import { improvementsApi } from "../api/improvementsApi";
import type {
  ImprovementTaskAnalyzeResponse,
  ImprovementTaskItem,
  ImprovementTaskPriority,
  ImprovementTaskStatus,
} from "../api/improvementsApi";
import { useAuth } from "../auth/AuthContext";

const STATUS_OPTIONS: ImprovementTaskStatus[] = ["open", "in_progress", "resolved", "dismissed"];
const PRIORITY_OPTIONS: ImprovementTaskPriority[] = ["low", "medium", "high"];

function formatStatus(s: string): string {
  return s.replace(/_/g, " ");
}

export function ImprovementTasksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { accessibleKbs } = useAuth();
  const pendingFeedbackId = searchParams.get("feedback_id");

  const [items, setItems] = useState<ImprovementTaskItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<ImprovementTaskStatus | "">("");
  const [priorityFilter, setPriorityFilter] = useState<ImprovementTaskPriority | "">("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creatingFromFeedback, setCreatingFromFeedback] = useState(false);

  const [newKbId, setNewKbId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creatingManual, setCreatingManual] = useState(false);
  const [includeRetrievalTest, setIncludeRetrievalTest] = useState(true);
  const [analysis, setAnalysis] = useState<ImprovementTaskAnalyzeResponse | null>(null);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [notesDraft, setNotesDraft] = useState<Record<number, string>>({});
  const [savingNotesId, setSavingNotesId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await improvementsApi.listTasks({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      });
      setItems(res.items || []);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(
          typeof detail?.detail === "string"
            ? detail.detail
            : err.response?.status === 403
              ? "You do not have permission to view improvement tasks."
              : err.message || "Request failed.",
        );
      } else {
        setError("Unexpected error loading tasks.");
      }
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setNotesDraft(Object.fromEntries(items.map((i) => [i.id, i.resolution_notes ?? ""])));
  }, [items]);

  const clearFeedbackQuery = useCallback(() => {
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const createFromFeedback = async () => {
    if (!pendingFeedbackId) return;
    setCreatingFromFeedback(true);
    setError(null);
    try {
      await improvementsApi.createTask({ feedback_id: Number(pendingFeedbackId) });
      setNotice("Task created from feedback.");
      clearFeedbackQuery();
      await load();
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(typeof detail?.detail === "string" ? detail.detail : "Failed to create task.");
      } else {
        setError("Failed to create task.");
      }
    } finally {
      setCreatingFromFeedback(false);
    }
  };

  const createManual = async () => {
    const kb = Number(newKbId);
    if (!kb || !newTitle.trim() || !newDescription.trim()) {
      setError("Select a knowledge base and enter title and description.");
      return;
    }
    setCreatingManual(true);
    setError(null);
    try {
      await improvementsApi.createTask({
        knowledge_base_id: kb,
        title: newTitle.trim(),
        description: newDescription.trim(),
      });
      setNotice("Task created.");
      setNewTitle("");
      setNewDescription("");
      await load();
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(typeof detail?.detail === "string" ? detail.detail : "Failed to create task.");
      } else {
        setError("Failed to create task.");
      }
    } finally {
      setCreatingManual(false);
    }
  };

  const runAnalyze = async (taskId: number) => {
    setAnalyzingId(taskId);
    setError(null);
    try {
      const res = await improvementsApi.analyzeTask(taskId, includeRetrievalTest);
      setAnalysis(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(typeof detail?.detail === "string" ? detail.detail : "Analysis failed.");
      } else {
        setError("Analysis failed.");
      }
      setAnalysis(null);
    } finally {
      setAnalyzingId(null);
    }
  };

  const patchRow = async (id: number, patch: Parameters<typeof improvementsApi.patchTask>[1]) => {
    setError(null);
    try {
      const updated = await improvementsApi.patchTask(id, patch);
      setItems((prev) => prev.map((row) => (row.id === id ? updated : row)));
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(typeof detail?.detail === "string" ? detail.detail : "Update failed.");
      } else {
        setError("Update failed.");
      }
      void load();
    }
  };

  const saveResolutionNotes = async (id: number) => {
    const raw = (notesDraft[id] ?? "").trim();
    setSavingNotesId(id);
    setError(null);
    try {
      const updated = await improvementsApi.patchTask(id, { resolution_notes: raw ? raw : null });
      setItems((prev) => prev.map((row) => (row.id === id ? updated : row)));
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(typeof detail?.detail === "string" ? detail.detail : "Failed to save resolution notes.");
      } else {
        setError("Failed to save resolution notes.");
      }
      void load();
    } finally {
      setSavingNotesId(null);
    }
  };

  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(t);
  }, [notice]);

  const defaultKb = useMemo(() => String(accessibleKbs[0]?.id ?? ""), [accessibleKbs]);
  useEffect(() => {
    if (!newKbId && defaultKb) setNewKbId(defaultKb);
  }, [defaultKb, newKbId]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Improvement tasks</h2>
          <p className="text-sm text-slate-600">
            Track follow-ups from negative query feedback. Restricted to admin and super admin roles.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {notice ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>
      ) : null}

      {pendingFeedbackId ? (
        <div className="rounded-lg border border-slate-300 bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-800">Create task from feedback</p>
          <p className="mt-1 text-xs text-slate-600">
            Feedback ID <span className="font-mono font-semibold">{pendingFeedbackId}</span> — title and description will be
            filled from the feedback record.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={creatingFromFeedback}
              onClick={() => void createFromFeedback()}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {creatingFromFeedback ? "Creating…" : "Create task"}
            </button>
            <button
              type="button"
              onClick={clearFeedbackQuery}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4">
        <label className="text-sm">
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">Status</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter((e.target.value || "") as ImprovementTaskStatus | "")}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {formatStatus(s)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">Priority</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter((e.target.value || "") as ImprovementTaskPriority | "")}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={includeRetrievalTest}
            onChange={(e) => setIncludeRetrievalTest(e.target.checked)}
            className="rounded border-slate-300"
          />
          <span>
            Include retrieval test <span className="text-xs text-slate-500">(diagnostics retrieval only, no answer)</span>
          </span>
        </label>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm font-semibold text-slate-800">New task (manual)</p>
        <p className="mt-1 text-xs text-slate-600">Optional — create without linking to feedback.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="block text-sm">
            <span className="text-xs font-medium text-slate-600">Knowledge base</span>
            <select
              value={newKbId}
              onChange={(e) => setNewKbId(e.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            >
              <option value="">Select…</option>
              {accessibleKbs.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm md:col-span-2">
            <span className="text-xs font-medium text-slate-600">Title</span>
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              placeholder="Short summary"
            />
          </label>
          <label className="block text-sm md:col-span-2">
            <span className="text-xs font-medium text-slate-600">Description</span>
            <textarea
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              placeholder="What should change in the KB or retrieval pipeline?"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={creatingManual}
          onClick={() => void createManual()}
          className="mt-3 rounded-md border border-slate-300 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-800 hover:bg-slate-100 disabled:opacity-50"
        >
          {creatingManual ? "Creating…" : "Create manual task"}
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Error</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !items.length ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">Loading…</div>
      ) : null}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Title</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">KB</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Status</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Priority</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Assignee</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700 min-w-[14rem]">Resolution</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Linked feedback</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Updated</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!loading && items.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-slate-600">
                  No tasks match the current filters.
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr key={row.id} className="align-top">
                  <td className="px-3 py-2 max-w-xs">
                    <p className="font-medium text-slate-900">{row.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-slate-600">{row.description}</p>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-slate-800">{row.knowledge_base_name}</td>
                  <td className="px-3 py-2">
                    <select
                      value={row.status}
                      onChange={(e) =>
                        void patchRow(row.id, { status: e.target.value as ImprovementTaskStatus })
                      }
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {formatStatus(s)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={row.priority}
                      onChange={(e) =>
                        void patchRow(row.id, { priority: e.target.value as ImprovementTaskPriority })
                      }
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
                    >
                      {PRIORITY_OPTIONS.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-700">{row.assigned_to_label ?? "—"}</td>
                  <td className="px-3 py-2 min-w-[12rem] max-w-xs align-top text-xs">
                    <label className="block text-[10px] font-medium uppercase tracking-wide text-slate-500">
                      Resolution notes
                    </label>
                    <textarea
                      rows={3}
                      value={notesDraft[row.id] ?? ""}
                      onChange={(e) => setNotesDraft((prev) => ({ ...prev, [row.id]: e.target.value }))}
                      placeholder={
                        row.status === "resolved"
                          ? "How was this resolved?"
                          : "Document outcome when closing the task…"
                      }
                      className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs text-slate-800"
                    />
                    <button
                      type="button"
                      disabled={savingNotesId === row.id}
                      onClick={() => void saveResolutionNotes(row.id)}
                      className="mt-1 rounded border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      {savingNotesId === row.id ? "Saving…" : "Save notes"}
                    </button>
                    {row.resolved_at ? (
                      <div className="mt-2 rounded border border-emerald-100 bg-emerald-50/80 p-2 text-[11px] text-emerald-900">
                        <p>
                          <span className="font-semibold">Resolved:</span> {row.resolved_at}
                        </p>
                        {row.resolved_by_label ? (
                          <p className="mt-0.5">
                            <span className="font-semibold">By:</span> {row.resolved_by_label}
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 max-w-xs text-xs">
                    {row.linked_feedback ? (
                      <details className="rounded border border-slate-200 bg-slate-50 p-2">
                        <summary className="cursor-pointer font-medium text-slate-800">
                          Feedback #{row.linked_feedback.id}
                        </summary>
                        <p className="mt-2 text-slate-600">
                          <span className="font-semibold text-slate-700">Rating:</span> {row.linked_feedback.rating}
                        </p>
                        <p className="mt-1 whitespace-pre-wrap text-slate-800">{row.linked_feedback.question_text}</p>
                        <p className="mt-2 text-slate-600">
                          <span className="font-semibold">Answer preview:</span>
                        </p>
                        <p className="whitespace-pre-wrap text-slate-700">{row.linked_feedback.answer_preview}</p>
                        {row.linked_feedback.comment ? (
                          <p className="mt-2 text-slate-600">
                            <span className="font-semibold">Comment:</span> {row.linked_feedback.comment}
                          </p>
                        ) : null}
                        <p className="mt-2 text-[11px] text-slate-500">{row.linked_feedback.created_at ?? ""}</p>
                      </details>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-slate-600">{row.updated_at ?? "—"}</td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <button
                      type="button"
                      disabled={analyzingId === row.id}
                      onClick={() => void runAnalyze(row.id)}
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
                    >
                      {analyzingId === row.id ? "Analyzing…" : "Analyze"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {analysis ? (
        <section className="rounded-lg border border-slate-300 bg-slate-50 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">Analysis — task #{analysis.task_id}</h3>
            <button
              type="button"
              onClick={() => setAnalysis(null)}
              className="text-xs font-medium text-slate-600 hover:text-slate-900"
            >
              Close
            </button>
          </div>
          <p className="mt-1 text-xs text-slate-600">
            Suggestions only; the task is not updated automatically.
          </p>
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recommended action</dt>
              <dd className="mt-1 font-mono text-sm font-medium text-slate-900">{analysis.recommended_action}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Reasoning summary</dt>
              <dd className="mt-1 whitespace-pre-wrap text-slate-800">{analysis.reasoning_summary}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suggested KB update</dt>
              <dd className="mt-1 whitespace-pre-wrap text-slate-800">{analysis.suggested_kb_update}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suggested test questions</dt>
              <dd className="mt-1">
                <ul className="list-inside list-disc space-y-1 text-slate-800">
                  {analysis.suggested_test_questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </dd>
            </div>
            {analysis.retrieval_test ? (
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Retrieval test summary</dt>
                <dd className="mt-2 space-y-1 rounded border border-slate-200 bg-white p-3 text-xs text-slate-800">
                  {"error" in analysis.retrieval_test && analysis.retrieval_test.error ? (
                    <p className="text-rose-700">Error: {String(analysis.retrieval_test.error)}</p>
                  ) : null}
                  <p>
                    <span className="font-semibold">Chunks:</span>{" "}
                    {String(analysis.retrieval_test.retrieved_chunk_count ?? "—")}
                  </p>
                  <p>
                    <span className="font-semibold">Mode:</span> {String(analysis.retrieval_test.retrieval_mode ?? "—")}
                  </p>
                  <p>
                    <span className="font-semibold">Dominant doc type:</span>{" "}
                    {String(analysis.retrieval_test.dominant_document_type ?? "—")}
                  </p>
                  <details className="mt-2">
                    <summary className="cursor-pointer font-medium text-slate-700">Raw retrieval payload</summary>
                    <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-100 p-2 text-[11px] leading-snug">
                      {JSON.stringify(analysis.retrieval_test, null, 2)}
                    </pre>
                  </details>
                </dd>
              </div>
            ) : (
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Retrieval test</dt>
                <dd className="mt-1 text-xs text-slate-600">Not requested (include retrieval test unchecked).</dd>
              </div>
            )}
          </dl>
        </section>
      ) : null}
    </div>
  );
}
