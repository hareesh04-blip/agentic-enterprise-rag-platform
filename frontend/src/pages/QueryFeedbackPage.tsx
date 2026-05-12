import { useCallback, useEffect, useMemo, useState } from "react";
import { AxiosError } from "axios";
import { feedbackApi } from "../api/feedbackApi";
import { useAuth } from "../auth/AuthContext";
import type { QueryFeedbackItem, QueryFeedbackRating } from "../api/feedbackApi";

function ratingLabel(r: QueryFeedbackRating): string {
  return r === "thumbs_up" ? "Thumbs up" : "Thumbs down";
}

export function QueryFeedbackPage() {
  const { accessibleKbs } = useAuth();
  const [items, setItems] = useState<QueryFeedbackItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [kbFilter, setKbFilter] = useState<string>("");
  const [ratingFilter, setRatingFilter] = useState<string>("");

  const kbOptions = useMemo(() => accessibleKbs, [accessibleKbs]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await feedbackApi.listQueryFeedback({
        knowledge_base_id: kbFilter ? Number(kbFilter) : undefined,
        rating: ratingFilter === "thumbs_up" || ratingFilter === "thumbs_down" ? ratingFilter : undefined,
      });
      setItems(res.items || []);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(
          typeof detail?.detail === "string"
            ? detail.detail
            : err.response?.status === 403
              ? "You do not have permission to view query feedback."
              : err.message || "Request failed.",
        );
      } else {
        setError("Unexpected error loading feedback.");
      }
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [kbFilter, ratingFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Query feedback</h2>
          <p className="text-sm text-slate-600">
            Ratings and comments from chat users. Restricted to admin and super admin roles.
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

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <label className="text-sm">
          <span className="block text-xs font-medium text-slate-600">Knowledge base</span>
          <select
            value={kbFilter}
            onChange={(e) => setKbFilter(e.target.value)}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">All</option>
            {kbOptions.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-xs font-medium text-slate-600">Rating</span>
          <select
            value={ratingFilter}
            onChange={(e) => setRatingFilter(e.target.value)}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">All</option>
            <option value="thumbs_up">Thumbs up</option>
            <option value="thumbs_down">Thumbs down</option>
          </select>
        </label>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load feedback</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !items.length ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading…</div>
      ) : null}

      {!loading && !items.length && !error ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">No feedback yet.</div>
      ) : null}

      {items.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">Rating</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">KB</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">Question</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">Answer preview</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">Comment</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">Submitted by</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-700">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((row) => (
                <tr key={row.id} className="align-top">
                  <td className="px-3 py-2 whitespace-nowrap">{ratingLabel(row.rating)}</td>
                  <td className="px-3 py-2">{row.knowledge_base_name ?? `#${row.knowledge_base_id}`}</td>
                  <td className="px-3 py-2 max-w-xs">
                    <p className="line-clamp-4 whitespace-pre-wrap text-slate-800">{row.question_text}</p>
                  </td>
                  <td className="px-3 py-2 max-w-xs">
                    <p className="line-clamp-4 whitespace-pre-wrap text-slate-700">{row.answer_preview}</p>
                  </td>
                  <td className="px-3 py-2 max-w-xs text-slate-700">{row.comment ?? "—"}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-slate-700">{row.submitted_by}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-slate-600">{row.created_at ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
