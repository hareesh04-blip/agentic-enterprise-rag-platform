import { useEffect, useState } from "react";
import { healthApi } from "../api/healthApi";
import { useAuth } from "../auth/AuthContext";
import { canViewSystemHealth } from "../auth/roleAccess";
import type { RuntimeMetadata } from "../types/health";

function formatBuild(rt: RuntimeMetadata | undefined): string {
  if (!rt?.build_version) return "—";
  return String(rt.build_version);
}

export function RuntimeStatusBanner() {
  const { user } = useAuth();
  const showExtended = canViewSystemHealth(user);
  const [line, setLine] = useState<string>("Loading runtime…");

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const health = await healthApi.getLivenessHealth();
        const rt = health.runtime;
        const build = formatBuild(rt);
        const pid = rt?.process_pid != null ? String(rt.process_pid) : "—";
        const llm = (rt?.llm_provider || "—").toString().toUpperCase();

        let qdrantPart = "";
        if (showExtended) {
          try {
            const plat = await healthApi.getPlatformStatus();
            const qs = plat.qdrant?.status === "ok" ? "QDRANT OK" : `QDRANT ${String(plat.qdrant?.status || "?").toUpperCase()}`;
            qdrantPart = ` · ${qs}`;
          } catch {
            qdrantPart = " · QDRANT ?";
          }
        }

        if (!cancelled) {
          setLine(`BUILD ${build} · PID ${pid} · ${llm}${qdrantPart}`);
        }
      } catch {
        if (!cancelled) setLine("Runtime unavailable (backend unreachable?)");
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [showExtended]);

  return (
    <div
      className="rounded-md border border-slate-200 bg-slate-900 px-3 py-2 font-mono text-[11px] text-slate-100 shadow-inner"
      title="Snapshot from GET /health (QDRANT from GET /status when permitted)"
    >
      {line}
    </div>
  );
}
