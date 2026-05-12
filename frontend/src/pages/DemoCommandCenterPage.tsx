import { useCallback, useEffect, useState } from "react";
import { AxiosError } from "axios";
import { demoCommandCenterApi } from "../api/demoCommandCenterApi";
import type { DemoDataOperationResponse, DemoDataStatusResponse } from "../api/demoCommandCenterApi";
import { healthApi } from "../api/healthApi";
import type { LivenessHealthResponse } from "../api/healthApi";

const DEFAULT_EMAIL = "superadmin@local";

export function DemoCommandCenterPage() {
  const [status, setStatus] = useState<DemoDataStatusResponse | null>(null);
  const [healthSnap, setHealthSnap] = useState<LivenessHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [email, setEmail] = useState(DEFAULT_EMAIL);
  const [kbName, setKbName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [latestOutput, setLatestOutput] = useState<string>("");

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await demoCommandCenterApi.getStatus();
      setStatus(res);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        setError(typeof detail === "string" ? detail : err.message || "Failed to load demo data status.");
      } else {
        setError("Failed to load demo data status.");
      }
      setStatus(null);
    } finally {
      setLoading(false);
    }
    try {
      const live = await healthApi.getLivenessHealth();
      setHealthSnap(live);
    } catch {
      setHealthSnap(null);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const runOperation = useCallback(
    async (operation: "seed" | "reset", dry_run: boolean) => {
      setWorking(true);
      setError(null);
      try {
        const body = {
          dry_run,
          email: email.trim() || DEFAULT_EMAIL,
          knowledge_base_name: kbName.trim() || undefined,
        };
        const res: DemoDataOperationResponse =
          operation === "seed" ? await demoCommandCenterApi.seed(body) : await demoCommandCenterApi.reset(body);
        const output = JSON.stringify(res, null, 2);
        setLatestOutput(output);
        if (res.status) {
          setStatus(res.status);
        } else {
          await loadStatus();
        }
      } catch (err) {
        if (err instanceof AxiosError) {
          const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
          setError(typeof detail === "string" ? detail : err.message || "Operation failed.");
        } else {
          setError("Operation failed.");
        }
      } finally {
        setWorking(false);
      }
    },
    [email, kbName, loadStatus],
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Demo Command Center</h2>
        <p className="text-sm text-slate-600">
          Admin-only utility to seed, reset, and verify demo data. Reset only removes rows marked with
          <code className="mx-1 rounded bg-slate-100 px-1">[DEMO_SEED_42]</code>.
        </p>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">Operation error</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : null}

      {healthSnap?.runtime ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800">Backend runtime (read-only)</h3>
          <p className="mt-1 text-xs text-slate-600">
            From GET /health — use BUILD_VERSION and PID to verify you hit the intended process after restart.
          </p>
          <dl className="mt-3 grid gap-2 text-sm text-slate-800 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-slate-500">BUILD_VERSION</dt>
              <dd className="font-mono text-xs">{healthSnap.runtime.build_version}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">PID</dt>
              <dd className="font-mono text-xs">{healthSnap.runtime.process_pid}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium text-slate-500">Started (UTC)</dt>
              <dd className="font-mono text-xs">{healthSnap.runtime.process_start_time}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">Uptime s</dt>
              <dd>{healthSnap.runtime.backend_uptime_seconds}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">Vector collection</dt>
              <dd className="break-all font-mono text-xs">{healthSnap.runtime.active_vector_collection ?? "—"}</dd>
            </div>
          </dl>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Seeded feedback</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{loading || !status ? "…" : status.seeded_feedback_count}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Seeded tasks</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{loading || !status ? "…" : status.seeded_task_count}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Seeded audit logs</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{loading || !status ? "…" : status.seeded_audit_count}</p>
        </div>
      </div>

      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800">Seed settings</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">Actor email</span>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
              KB name (optional)
            </span>
            <input
              value={kbName}
              onChange={(e) => setKbName(e.target.value)}
              placeholder="Uses first active KB when blank"
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <button
          type="button"
          disabled={working}
          onClick={() => void runOperation("seed", true)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          Dry-run seed
        </button>
        <button
          type="button"
          disabled={working}
          onClick={() => void runOperation("seed", false)}
          className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
        >
          Apply seed
        </button>
        <button
          type="button"
          disabled={working}
          onClick={() => void runOperation("reset", true)}
          className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100 disabled:opacity-50"
        >
          Dry-run reset
        </button>
        <button
          type="button"
          disabled={working}
          onClick={() => void runOperation("reset", false)}
          className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-800 hover:bg-rose-100 disabled:opacity-50"
        >
          Apply reset
        </button>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-800">Latest operation output</h3>
          <button
            type="button"
            onClick={() => void loadStatus()}
            disabled={loading || working}
            className="rounded border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Refresh counts
          </button>
        </div>
        <pre className="max-h-96 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
          {latestOutput || "No operation has been run yet."}
        </pre>
      </div>
    </div>
  );
}

