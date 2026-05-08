import type { PropsWithChildren } from "react";
import { KBSelector } from "./KBSelector";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-slate-100">
      <TopNav />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 space-y-4 p-6">
          <KBSelector />
          <section className="rounded-lg border border-slate-200 bg-white p-4">{children}</section>
        </main>
      </div>
    </div>
  );
}
