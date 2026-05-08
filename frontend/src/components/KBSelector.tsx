import { useAuth } from "../auth/AuthContext";
import { accessLevelLabel, domainLabel } from "../utils/workspace";

export function KBSelector() {
  const { accessibleKbs, selectedKb, setSelectedKbById } = useAuth();

  if (accessibleKbs.length === 0) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm font-semibold text-amber-800">No knowledge base access</p>
        <p className="mt-1 text-xs text-amber-700">
          Your account does not currently have KB visibility. Contact your platform admin to request read/write/admin access.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <label className="text-xs font-semibold text-slate-600" htmlFor="kb-selector">
        Active Knowledge Base
      </label>
      <select
        id="kb-selector"
        className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
        value={selectedKb?.id ?? ""}
        onChange={(event) => setSelectedKbById(Number(event.target.value))}
      >
        {accessibleKbs.map((kb) => (
          <option key={kb.id} value={kb.id}>
            {kb.name} | {domainLabel(kb.domain_type)} | {accessLevelLabel(kb.access_level)}
          </option>
        ))}
      </select>
      {selectedKb ? (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-blue-700">
            Domain: {domainLabel(selectedKb.domain_type)}
          </span>
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-emerald-700">
            Access: {accessLevelLabel(selectedKb.access_level)}
          </span>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-600">
            Query: {selectedKb.can_query ? "Yes" : "No"}
          </span>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-600">
            Upload: {selectedKb.can_upload ? "Yes" : "No"}
          </span>
        </div>
      ) : null}
    </div>
  );
}
