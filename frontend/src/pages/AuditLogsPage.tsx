import { useCallback, useEffect, useMemo, useState } from "react";
import { AxiosError } from "axios";
import { auditApi } from "../api/auditApi";
import type { AuditLogItem } from "../api/auditApi";
import { useAuth } from "../auth/AuthContext";

const COMMON_ACTIONS = [
  "",
  "improvement_task.created",
  "improvement_task.updated",
  "improvement_task.analyzed",
  "improvement_task.resolved",
  "query_feedback.submitted",
  "document.uploaded",
];

const COMMON_ENTITY_TYPES = ["", "improvement_task", "query_feedback", "document"];

export function AuditLogsPage() {
  const { accessibleKbs } = useAuth();
  const kbOptions = useMemo(() => accessibleKbs, [accessibleKbs]);
  const [actionFilter, setActionFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [kbFilter, setKbFilter] = useState("");
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await auditApi.listLogs({
        action: actionFilter || undefined,
        entity_type: entityTypeFilter || undefined,
        knowledge_base_id: kbFilter ? Number(kbFilter) : undefined,
      });
      setItems(res.items || []);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data as { detail?: string } | undefined;
        setError(
          typeof detail?.detail === "string"
            ? detail.detail
            : err.response?.status === 403
              ? "You do not have permission to view audit logs."
              : err.message || "Request failed.",
        );
      } else {
        setError("Unexpected error loading audit logs.");
      }
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [actionFilter, entityTypeFilter, kbFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Audit logs</h2>
          <p className="text-sm text-slate-600">
            Recent admin and governance-relevant actions. Restricted to admin and super admin roles.
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
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">Action</span>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="mt-1 min-w-[12rem] rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          >
            {COMMON_ACTIONS.map((a) => (
              <option key={a || "any"} value={a}>
                {a || "Any"}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">Entity type</span>
          <select
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
            className="mt-1 min-w-[10rem] rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          >
            {COMMON_ENTITY_TYPES.map((t) => (
              <option key={t || "any"} value={t}>
                {t || "Any"}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">Knowledge base</span>
          <select
            value={kbFilter}
            onChange={(e) => setKbFilter(e.target.value)}
            className="mt-1 min-w-[12rem] rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          >
            <option value="">Any</option>
            {kbOptions.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load audit logs</p>
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
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Time</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Actor</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Action</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Entity</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Entity ID</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">KB</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-700">Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!loading && items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-slate-600">
                  No audit entries match the filters.
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr key={row.id} className="align-top">
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-slate-700">{row.created_at ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-slate-800">
                    <span className="font-medium">{row.actor_summary}</span>
                    {row.actor_email ? (
                      <span className="mt-0.5 block text-[11px] text-slate-500">{row.actor_email}</span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-slate-900">{row.action}</td>
                  <td className="px-3 py-2 text-xs text-slate-800">{row.entity_type}</td>
                  <td className="px-3 py-2 tabular-nums text-xs text-slate-800">{row.entity_id ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-slate-800">{row.knowledge_base_name ?? row.knowledge_base_id ?? "—"}</td>
                  <td className="px-3 py-2 max-w-md">
                    <p className="break-words font-mono text-[11px] leading-snug text-slate-700">
                      {row.metadata_preview ?? "—"}
                    </p>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
