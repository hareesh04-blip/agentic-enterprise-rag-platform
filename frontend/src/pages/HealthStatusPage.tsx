import { useCallback, useEffect, useState } from "react";
import { AxiosError } from "axios";
import { healthApi } from "../api/healthApi";
import type { PlatformStatusResponse } from "../types/health";

function statusPillClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "ok" || s === "healthy") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (s === "degraded") return "border-amber-200 bg-amber-50 text-amber-800";
  if (s === "error" || s === "unhealthy") return "border-rose-200 bg-rose-50 text-rose-800";
  return "border-slate-200 bg-slate-50 text-slate-800";
}

export function HealthStatusPage() {
  const [data, setData] = useState<PlatformStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await healthApi.getPlatformStatus();
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
                ? "You do not have permission to view platform status."
                : err.message || "Request failed.";
        setError(msg);
      } else {
        setError("Unexpected error loading platform status.");
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">System health</h2>
          <p className="text-sm text-slate-600">
            Operational snapshot for administrators. Restricted to admin and super admin roles.
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
          <p className="font-semibold">Unable to load status</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading platform status…</div>
      ) : null}

      {data ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overall</span>
            <span
              className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${statusPillClass(data.overall_status)}`}
            >
              {data.overall_status}
            </span>
            {data.issues?.length ? (
              <span className="text-xs text-amber-700">Issues: {data.issues.join(", ")}</span>
            ) : null}
          </div>

          {data.runtime ? (
            <section className="rounded-lg border border-slate-200 bg-slate-50 p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Runtime / build (process)</h3>
              <p className="mt-1 text-xs text-slate-600">
                Confirms which backend instance is running; PID and start time change after restart.
              </p>
              <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-800 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium text-slate-500">BUILD_VERSION</dt>
                  <dd className="font-mono text-xs">{data.runtime.build_version}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Process PID</dt>
                  <dd className="font-mono text-xs">{data.runtime.process_pid}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium text-slate-500">Process start (UTC)</dt>
                  <dd className="font-mono text-xs">{data.runtime.process_start_time}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Uptime (seconds)</dt>
                  <dd>{data.runtime.backend_uptime_seconds}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">App env</dt>
                  <dd>{data.runtime.app_env}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">LLM provider</dt>
                  <dd>{data.runtime.llm_provider}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Embedding provider</dt>
                  <dd>{data.runtime.embedding_provider}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium text-slate-500">Active vector collection</dt>
                  <dd className="font-mono text-xs">{data.runtime.active_vector_collection ?? "—"}</dd>
                </div>
              </dl>
              {data.runtime.stale_process_hint ? (
                <p className="mt-3 text-xs text-slate-600">{data.runtime.stale_process_hint}</p>
              ) : null}
            </section>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Backend</h3>
              <p className="mt-2 text-xs text-slate-500">Application process</p>
              <div className="mt-2 flex flex-wrap gap-2 text-sm">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusPillClass(data.backend.status)}`}>
                  {data.backend.status}
                </span>
                <span className="text-slate-700">{data.backend.app_name}</span>
                <span className="text-slate-500">({data.backend.environment})</span>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">PostgreSQL</h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusPillClass(data.database.status)}`}>
                  {data.database.status}
                </span>
              </div>
              {data.database.message ? (
                <p className="mt-2 text-xs text-rose-700">{data.database.message}</p>
              ) : (
                <p className="mt-2 text-xs text-slate-600">Connection check passed.</p>
              )}
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:col-span-2">
              <h3 className="text-sm font-semibold text-slate-900">Qdrant</h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusPillClass(data.qdrant.status)}`}>
                  {data.qdrant.status}
                </span>
                <span className="text-xs text-slate-600">{data.qdrant.url}</span>
              </div>
              <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium text-slate-500">Active collection</dt>
                  <dd>{data.qdrant.collection_name ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Collection exists</dt>
                  <dd>{data.qdrant.collection_exists ? "Yes" : "No"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Point count</dt>
                  <dd>{data.qdrant.point_count}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Embedding dim (configured)</dt>
                  <dd>{data.qdrant.embedding_dimension_configured ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Dim matches provider</dt>
                  <dd>
                    {data.qdrant.embedding_dimension_matches === null
                      ? "N/A"
                      : data.qdrant.embedding_dimension_matches
                        ? "Yes"
                        : "No"}
                  </dd>
                </div>
              </dl>
              {data.qdrant.message ? <p className="mt-2 text-xs text-rose-700">{data.qdrant.message}</p> : null}
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:col-span-2">
              <h3 className="text-sm font-semibold text-slate-900">Providers & collection</h3>
              <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium text-slate-500">LLM provider</dt>
                  <dd>{data.providers.llm_provider}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Embedding provider</dt>
                  <dd>{data.providers.embedding_provider}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">LLM model</dt>
                  <dd>{data.providers.llm_model}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Embedding model</dt>
                  <dd>{data.providers.embedding_model}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium text-slate-500">Vector collection (active)</dt>
                  <dd>{data.providers.vector_collection ?? "—"}</dd>
                </div>
              </dl>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:col-span-2">
              <h3 className="text-sm font-semibold text-slate-900">Retrieval & feature flags</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-800">
                <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                  <span>Hybrid retrieval</span>
                  <span className="font-medium">{data.feature_flags.ENABLE_HYBRID_RETRIEVAL ? "Enabled" : "Disabled"}</span>
                </li>
                <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                  <span>Metadata reranking</span>
                  <span className="font-medium">{data.feature_flags.ENABLE_METADATA_RERANKING ? "Enabled" : "Disabled"}</span>
                </li>
                <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                  <span>Suggested questions</span>
                  <span className="font-medium">{data.feature_flags.ENABLE_SUGGESTED_QUESTIONS ? "Enabled" : "Disabled"}</span>
                </li>
                <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                  <span>Confidence scoring</span>
                  <span className="font-medium">{data.feature_flags.ENABLE_CONFIDENCE_SCORING ? "Enabled" : "Disabled"}</span>
                </li>
                <li className="flex justify-between gap-2">
                  <span>Impact analysis</span>
                  <span className="font-medium">{data.feature_flags.ENABLE_IMPACT_ANALYSIS ? "Enabled" : "Disabled"}</span>
                </li>
              </ul>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
