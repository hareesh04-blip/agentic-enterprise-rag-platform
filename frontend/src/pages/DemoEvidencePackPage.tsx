import { useCallback, useEffect, useMemo, useState } from "react";
import { AxiosError } from "axios";
import { demoEvidencePackApi } from "../api/demoEvidencePackApi";
import type { DemoEvidencePackResponse } from "../api/demoEvidencePackApi";

function toPrettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function downloadJson(filename: string, payload: unknown): void {
  const blob = new Blob([toPrettyJson(payload)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function DemoEvidencePackPage() {
  const [data, setData] = useState<DemoEvidencePackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPdfError(null);
    try {
      const res = await demoEvidencePackApi.getEvidencePack();
      setData(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        setError(typeof detail === "string" ? detail : err.message || "Request failed.");
      } else {
        setError("Unexpected error while loading evidence pack.");
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => {
    if (!data) return null;
    return {
      generatedAt: data.generated_at,
      generatedBy: data.generated_by?.full_name || data.generated_by?.email || "unknown",
      openTaskCount: Array.isArray(data.open_improvement_tasks) ? data.open_improvement_tasks.length : 0,
      auditCount: Array.isArray(data.recent_audit_logs) ? data.recent_audit_logs.length : 0,
    };
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Evidence Pack</h2>
          <p className="mt-1 text-sm text-slate-600">
            Read-only export for stakeholders: readiness, health, script context, feedback, tasks, and audit summary.
            Restricted to admin and super admin roles.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button
            type="button"
            disabled={!data}
            onClick={() => {
              if (!data) return;
              const ts = (data.generated_at || new Date().toISOString()).replace(/[:.]/g, "-");
              downloadJson(`demo-evidence-pack-${ts}.json`, data);
            }}
            className="rounded-md border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-800 hover:bg-blue-100 disabled:opacity-50"
          >
            Download JSON
          </button>
          <button
            type="button"
            disabled={downloadingPdf}
            onClick={async () => {
              try {
                setDownloadingPdf(true);
                setPdfError(null);
                const blob = await demoEvidencePackApi.downloadEvidencePackPdf();
                const ts = (data?.generated_at || new Date().toISOString()).replace(/[:.]/g, "-");
                downloadBlob(`demo-evidence-pack-${ts}.pdf`, blob);
              } catch (err) {
                if (err instanceof AxiosError) {
                  const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
                  setPdfError(typeof detail === "string" ? detail : err.message || "PDF download failed.");
                } else {
                  setPdfError("PDF download failed.");
                }
              } finally {
                setDownloadingPdf(false);
              }
            }}
            className="rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-800 hover:bg-indigo-100 disabled:opacity-50"
          >
            {downloadingPdf ? "Downloading PDF…" : "Download PDF"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load evidence pack</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {pdfError ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">PDF download</p>
          <p className="mt-1">{pdfError}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading evidence pack…</div>
      ) : null}

      {summary ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Generated at</p>
            <p className="mt-1 text-sm text-slate-900 break-all">{summary.generatedAt}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Generated by</p>
            <p className="mt-1 text-sm text-slate-900">{summary.generatedBy}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Open improvement tasks</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{summary.openTaskCount}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Recent audit logs</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{summary.auditCount}</p>
          </div>
        </div>
      ) : null}

      {data ? (
        <div className="space-y-4">
          {[
            { title: "demo_readiness", payload: data.demo_readiness },
            { title: "platform_status", payload: data.platform_status },
            { title: "demo_script", payload: data.demo_script },
            { title: "feedback_analytics", payload: data.feedback_analytics },
            { title: "open_improvement_tasks", payload: data.open_improvement_tasks },
            { title: "recent_audit_logs", payload: data.recent_audit_logs },
          ].map(({ title, payload }) => (
            <section key={title} className="rounded-lg border border-slate-200 bg-white overflow-hidden">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-2">
                <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
              </div>
              <pre className="max-h-96 overflow-auto bg-slate-900 p-4 text-xs text-slate-100">{toPrettyJson(payload)}</pre>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}

