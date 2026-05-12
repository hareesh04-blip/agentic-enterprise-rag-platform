import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AxiosError } from "axios";
import { demoScriptApi } from "../api/demoScriptApi";
import type { DemoScriptResponse, DemoScriptSection } from "../api/demoScriptApi";

const PROGRESS_KEY = "aerag_demo_script_progress_v1";

function loadProgress(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Record<string, boolean>;
  } catch {
    return {};
  }
}

function saveProgress(next: Record<string, boolean>) {
  localStorage.setItem(PROGRESS_KEY, JSON.stringify(next));
}

function overallClass(overall: string): string {
  const o = overall.toLowerCase();
  if (o === "ready") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (o === "warning") return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-rose-200 bg-rose-50 text-rose-900";
}

export function DemoScriptPage() {
  const [data, setData] = useState<DemoScriptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState<Record<string, boolean>>(() => loadProgress());
  const [showReadiness, setShowReadiness] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await demoScriptApi.getDemoScript();
      setData(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const raw = err.response?.data as { detail?: string } | undefined;
        setError(
          typeof raw?.detail === "string"
            ? raw.detail
            : err.response?.status === 403
              ? "You do not have permission to view the demo script."
              : err.message || "Request failed.",
        );
      } else {
        setError("Unexpected error loading demo script.");
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const completedCount = useMemo(() => {
    if (!data?.sections.length) return 0;
    return data.sections.filter((s) => progress[s.id]).length;
  }, [data, progress]);

  const toggleSection = (id: string, done: boolean) => {
    setProgress((prev) => {
      const next = { ...prev, [id]: done };
      saveProgress(next);
      return next;
    });
  };

  const resetProgress = () => {
    saveProgress({});
    setProgress({});
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Guided demo script</h2>
          <p className="text-sm text-slate-600">
            End-to-end scenario for presenting the platform. Progress is stored only in this browser ({PROGRESS_KEY}).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh script"}
          </button>
          <button
            type="button"
            onClick={resetProgress}
            className="rounded-md border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-medium text-rose-800 hover:bg-rose-100"
          >
            Reset demo progress
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load demo script</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">Loading…</div>
      ) : null}

      {data ? (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-base font-semibold text-slate-900">{data.title}</h3>
              <span className="text-sm text-slate-600">
                {completedCount} / {data.sections.length} sections checked
              </span>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50">
            <button
              type="button"
              onClick={() => setShowReadiness((v) => !v)}
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-slate-800 hover:bg-slate-100"
            >
              <span>Current demo readiness (live)</span>
              <span className="text-slate-500">{showReadiness ? "Hide" : "Show"}</span>
            </button>
            {showReadiness ? (
              <div className="border-t border-slate-200 px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-600">Overall:</span>
                  <span
                    className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${overallClass(data.demo_readiness.overall_status)}`}
                  >
                    {data.demo_readiness.overall_status}
                  </span>
                  <span className="text-slate-600">
                    {data.demo_readiness.summary.active_knowledge_bases} active KBs ·{" "}
                    {data.demo_readiness.summary.documents_count} documents ·{" "}
                    {data.demo_readiness.summary.feedback_count} feedback ·{" "}
                    {data.demo_readiness.summary.open_improvement_tasks} open tasks ·{" "}
                    {data.demo_readiness.summary.recent_audit_logs} audit rows (7d)
                  </span>
                </div>
                {data.demo_readiness.recommendations.length > 0 ? (
                  <ul className="mt-2 list-disc space-y-0.5 pl-5 text-slate-700">
                    {data.demo_readiness.recommendations.slice(0, 5).map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                    {data.demo_readiness.recommendations.length > 5 ? (
                      <li className="text-slate-500">…and more on the Demo Readiness page.</li>
                    ) : null}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>

          <ol className="space-y-4">
            {data.sections.map((section: DemoScriptSection, index: number) => (
              <li key={section.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start gap-3">
                  <label className="flex shrink-0 cursor-pointer items-center gap-2 pt-0.5 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={Boolean(progress[section.id])}
                      onChange={(e) => toggleSection(section.id, e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-slate-900"
                      aria-label={`Mark step ${index + 1} ${section.name} as presented`}
                    />
                    Done
                  </label>
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Step {index + 1}
                      </span>
                      <h4 className="text-base font-semibold text-slate-900">{section.name}</h4>
                    </div>
                    <p className="text-sm text-slate-700">
                      <span className="font-medium text-slate-800">Objective: </span>
                      {section.objective}
                    </p>
                    <p>
                      <Link
                        to={section.route}
                        className="text-sm font-medium text-blue-700 underline decoration-blue-300 underline-offset-2 hover:text-blue-900"
                      >
                        Go to {section.route}
                      </Link>
                    </p>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Talking points</p>
                      <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                        {section.talking_points.map((tp) => (
                          <li key={tp}>{tp}</li>
                        ))}
                      </ul>
                    </div>
                    <p className="text-sm text-slate-700">
                      <span className="font-medium text-slate-800">Expected outcome: </span>
                      {section.expected_outcome}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </>
      ) : null}
    </div>
  );
}
