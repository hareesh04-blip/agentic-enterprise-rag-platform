import { useCallback, useEffect, useMemo, useState } from "react";
import { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { feedbackApi } from "../api/feedbackApi";
import type { FeedbackAnalyticsResponse } from "../api/feedbackApi";
import { useAuth } from "../auth/AuthContext";

function pct(rate: number): string {
  if (!Number.isFinite(rate)) return "0%";
  return `${(rate * 100).toFixed(1)}%`;
}

export function FeedbackAnalyticsPage() {
  const navigate = useNavigate();
  const { accessibleKbs } = useAuth();
  const kbOptions = useMemo(() => accessibleKbs, [accessibleKbs]);
  const [kbFilter, setKbFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [data, setData] = useState<FeedbackAnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { knowledge_base_id?: number; from_date?: string; to_date?: string } = {};
      if (kbFilter) params.knowledge_base_id = Number(kbFilter);
      if (fromDate) params.from_date = `${fromDate}T00:00:00`;
      if (toDate) params.to_date = `${toDate}T23:59:59`;
      const res = await feedbackApi.getFeedbackAnalytics(params);
      setData(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(
          typeof detail?.detail === "string"
            ? detail.detail
            : err.response?.status === 403
              ? "You do not have permission to view feedback analytics."
              : err.message || "Request failed.",
        );
      } else {
        setError("Unexpected error loading analytics.");
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [kbFilter, fromDate, toDate]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Feedback analytics</h2>
          <p className="text-sm text-slate-600">
            Aggregated answer ratings across knowledge bases. Restricted to admin and super admin roles.
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

      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <label className="text-sm">
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">Knowledge base</span>
          <select
            value={kbFilter}
            onChange={(e) => setKbFilter(e.target.value)}
            className="mt-1 min-w-[12rem] rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
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
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">From date</span>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
          />
        </label>
        <label className="text-sm">
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">To date</span>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
          />
        </label>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load analytics</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">Loading…</div>
      ) : null}

      {data && data.total_feedback === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          No feedback in the selected range. Adjust dates or knowledge base, or submit a few chat ratings to populate
          analytics.
        </div>
      ) : null}

      {data && data.total_feedback > 0 ? (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total feedback</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">{data.total_feedback}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Thumbs up</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-emerald-800">{data.thumbs_up_count}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Thumbs down</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-rose-800">{data.thumbs_down_count}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Thumbs up rate</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">{pct(data.thumbs_up_rate)}</p>
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-800">By knowledge base</h3>
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">Knowledge base</th>
                    <th className="px-4 py-2 text-right font-semibold text-slate-700">Total</th>
                    <th className="px-4 py-2 text-right font-semibold text-slate-700">Up</th>
                    <th className="px-4 py-2 text-right font-semibold text-slate-700">Down</th>
                    <th className="px-4 py-2 text-right font-semibold text-slate-700">Up rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.by_knowledge_base.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-center text-slate-600">
                        No feedback in this range.
                      </td>
                    </tr>
                  ) : (
                    data.by_knowledge_base.map((row) => (
                      <tr key={row.knowledge_base_id}>
                        <td className="px-4 py-2 text-slate-900">{row.knowledge_base_name || `#${row.knowledge_base_id}`}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-slate-800">{row.total}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-emerald-800">{row.thumbs_up}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-rose-800">{row.thumbs_down}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-slate-800">{pct(row.thumbs_up_rate)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Recent negative feedback</h3>
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">KB</th>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">Question</th>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">Answer preview</th>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">Comment</th>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">Date</th>
                    <th className="px-4 py-2 text-left font-semibold text-slate-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.recent_negative_feedback.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-center text-slate-600">
                        No thumbs-down feedback in this range.
                      </td>
                    </tr>
                  ) : (
                    data.recent_negative_feedback.map((row) => (
                      <tr key={row.id}>
                        <td className="px-4 py-2 whitespace-nowrap text-slate-800">{row.knowledge_base_name}</td>
                        <td className="px-4 py-2 max-w-xs">
                          <p className="line-clamp-3 whitespace-pre-wrap text-slate-800">{row.question_text}</p>
                        </td>
                        <td className="px-4 py-2 max-w-xs">
                          <p className="line-clamp-3 whitespace-pre-wrap text-slate-700">{row.answer_preview}</p>
                        </td>
                        <td className="px-4 py-2 max-w-xs text-slate-700">{row.comment ?? "—"}</td>
                        <td className="px-4 py-2 whitespace-nowrap text-slate-600">{row.created_at ?? "—"}</td>
                        <td className="px-4 py-2 whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => navigate(`/admin/improvement-tasks?feedback_id=${row.id}`)}
                            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50"
                          >
                            Create task
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
