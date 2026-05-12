import { useCallback, useEffect, useState } from "react";
import { AxiosError } from "axios";
import { demoReadinessApi } from "../api/demoReadinessApi";
import type { DemoCheckStatus, DemoReadinessResponse } from "../api/demoReadinessApi";

function checkPillClass(s: DemoCheckStatus): string {
  if (s === "pass") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (s === "warn") return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-rose-200 bg-rose-50 text-rose-900";
}

function overallPillClass(overall: string): string {
  const o = overall.toLowerCase();
  if (o === "ready") return "border-emerald-300 bg-emerald-100 text-emerald-950";
  if (o === "warning") return "border-amber-300 bg-amber-100 text-amber-950";
  return "border-rose-300 bg-rose-100 text-rose-950";
}

export function DemoReadinessPage() {
  const [data, setData] = useState<DemoReadinessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await demoReadinessApi.getDemoReadiness();
      setData(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const raw = err.response?.data as { detail?: string | { msg?: string }[] } | undefined;
        const detail = raw?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]
              ? String((detail[0] as { msg: string }).msg)
              : err.response?.status === 403
                ? "You do not have permission to view demo readiness."
                : err.message || "Request failed.";
        setError(msg);
      } else {
        setError("Unexpected error loading demo readiness.");
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const s = data?.summary;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Demo readiness</h2>
          <p className="text-sm text-slate-600">
            One-page snapshot for whether the platform is ready to demo. Restricted to admin and super admin roles.
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

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load demo readiness</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">Loading…</div>
      ) : null}

      {data ? (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overall status</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <span
                className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold capitalize ${overallPillClass(data.overall_status)}`}
              >
                {data.overall_status}
              </span>
              <span className="text-sm text-slate-600">
                {data.overall_status === "ready"
                  ? "Infrastructure and content checks passed; review recommendations for polish."
                  : data.overall_status === "warning"
                    ? "Demo may proceed with caveats; address warnings before a high-stakes presentation."
                    : "Critical checks failed; fix blocking items before relying on this environment for a demo."}
              </span>
            </div>
          </div>

          {s ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {[
                { label: "Active KBs", value: s.active_knowledge_bases },
                { label: "Documents", value: s.documents_count },
                { label: "Query feedback", value: s.feedback_count },
                { label: "Open tasks", value: s.open_improvement_tasks },
                { label: "Audit logs (7d)", value: s.recent_audit_logs },
              ].map((card) => (
                <div key={card.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{card.label}</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{card.value}</p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-200 bg-slate-50 px-4 py-2">
              <h3 className="text-sm font-semibold text-slate-800">Checks</h3>
            </div>
            <ul className="divide-y divide-slate-100">
              {data.checks.map((c) => (
                <li key={c.name} className="flex flex-wrap items-start gap-3 px-4 py-3">
                  <span
                    className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold uppercase ${checkPillClass(c.status)}`}
                  >
                    {c.status}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-slate-900">{c.name}</p>
                    <p className="mt-0.5 text-sm text-slate-600">{c.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-800">Recommendations</h3>
            {data.recommendations.length === 0 ? (
              <p className="mt-2 text-sm text-slate-600">No specific recommendations; you are in good shape.</p>
            ) : (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {data.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
