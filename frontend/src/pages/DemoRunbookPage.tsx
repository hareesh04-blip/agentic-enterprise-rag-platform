import { useCallback, useEffect, useState } from "react";
import { AxiosError } from "axios";
import { demoRunbookApi } from "../api/demoRunbookApi";
import type { DemoRunbookResponse } from "../api/demoRunbookApi";

async function copyText(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

export function DemoRunbookPage() {
  const [data, setData] = useState<DemoRunbookResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await demoRunbookApi.getRunbook();
      setData(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        setError(
          typeof detail === "string"
            ? detail
            : err.response?.status === 403
              ? "You do not have permission to view the demo runbook."
              : err.message || "Request failed.",
        );
      } else {
        setError("Unexpected error loading runbook.");
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
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Demo runbook</h2>
          <p className="text-sm text-slate-600">
            Exact commands and checks before a demo. Admin and super admin only. Nothing here runs automatically.
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
          <p className="font-semibold">Unable to load runbook</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">Loading…</div>
      ) : null}

      {data ? (
        <div className="space-y-6">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-medium text-slate-800">{data.title}</p>
            <p className="mt-1 text-sm text-slate-600">{data.description}</p>
          </div>

          {data.sections.map((section) => (
            <section key={section.id} className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <h3 className="text-base font-semibold text-slate-900">{section.title}</h3>
                {section.notes.length > 0 ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                    {section.notes.map((n) => (
                      <li key={n}>{n}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
              <div className="divide-y divide-slate-100 p-4 space-y-3">
                {section.commands.length === 0 ? (
                  <p className="text-sm text-slate-500">No shell commands for this section; see notes above.</p>
                ) : (
                  section.commands.map((cmd, idx) => {
                    const cardId = `${section.id}-${idx}`;
                    return (
                      <div key={cardId} className="rounded-md border border-slate-200 bg-slate-900/95 p-3">
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Command</span>
                          <button
                            type="button"
                            onClick={async () => {
                              try {
                                await copyText(cmd);
                                setCopiedId(cardId);
                                window.setTimeout(() => setCopiedId(null), 2000);
                              } catch {
                                setCopiedId(null);
                              }
                            }}
                            className="rounded border border-slate-600 bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
                          >
                            {copiedId === cardId ? "Copied" : "Copy"}
                          </button>
                        </div>
                        <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-slate-100">
                          {cmd}
                        </pre>
                      </div>
                    );
                  })
                )}
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
