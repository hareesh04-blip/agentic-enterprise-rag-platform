import { useMemo } from "react";

interface ProviderSnapshot {
  llm_provider?: string;
  llm_status?: string;
}

const SNAPSHOT_KEY = "demo_provider_snapshot";

function readProviderSnapshot(): ProviderSnapshot | null {
  try {
    const raw = window.localStorage.getItem(SNAPSHOT_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ProviderSnapshot;
  } catch {
    return null;
  }
}

export function ProviderBadge() {
  const snapshot = useMemo(() => readProviderSnapshot(), []);
  const provider = (snapshot?.llm_provider || "backend-configured").toLowerCase();
  const isFallback = (snapshot?.llm_status || "").toLowerCase().includes("fallback");

  const tone = isFallback
    ? "border-amber-300 bg-amber-50 text-amber-700"
    : provider.includes("openai")
      ? "border-emerald-300 bg-emerald-50 text-emerald-700"
      : provider.includes("ollama")
        ? "border-violet-300 bg-violet-50 text-violet-700"
        : "border-slate-300 bg-white text-slate-600";

  const label = isFallback
    ? `Provider: ${provider} (degraded)`
    : provider === "backend-configured"
      ? "Provider: Backend configured"
      : `Provider: ${provider}`;

  return <span className={`rounded-full border px-3 py-1 text-xs font-medium ${tone}`}>{label}</span>;
}
