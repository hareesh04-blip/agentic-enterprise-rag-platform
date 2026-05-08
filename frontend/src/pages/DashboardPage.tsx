import { useAuth } from "../auth/AuthContext";
import { canViewAdmin, canViewChat, canViewDocuments } from "../auth/roleAccess";
import { domainLabel, workspaceLabelFromKb } from "../utils/workspace";

export function DashboardPage() {
  const { user, accessibleKbs, selectedKb } = useAuth();
  const showChat = canViewChat(user, accessibleKbs);
  const showDocuments = canViewDocuments(user, accessibleKbs);
  const showAdmin = canViewAdmin(user);

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h2 className="text-lg font-semibold text-slate-900">Welcome to your workspace</h2>
        <p className="mt-1 text-sm text-slate-600">
          Signed in as {user?.full_name ?? user?.email}. Your navigation is filtered by role and knowledge-base access.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-700">
            {workspaceLabelFromKb(selectedKb)}
          </span>
          <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-700">
            Accessible KBs: {accessibleKbs.length}
          </span>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {showChat ? (
          <article className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-900">Assistant Workspace</p>
            <p className="mt-1 text-sm text-slate-600">
              Ask KB-scoped questions in the {domainLabel(selectedKb?.domain_type)} domain assistant.
            </p>
          </article>
        ) : null}
        {showDocuments ? (
          <article className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-900">Document Workspace</p>
            <p className="mt-1 text-sm text-slate-600">Browse and upload documents based on your KB permissions.</p>
          </article>
        ) : null}
        {showAdmin ? (
          <article className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-900">Admin Workspace</p>
            <p className="mt-1 text-sm text-slate-600">Access admin capabilities and operational controls.</p>
          </article>
        ) : null}
        <article className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Recruitment Workspace</p>
          <p className="mt-1 text-xs text-slate-600">Future Phase</p>
        </article>
        <article className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Analytics</p>
          <p className="mt-1 text-xs text-slate-600">Future Phase</p>
        </article>
        <article className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Advanced Diagnostics</p>
          <p className="mt-1 text-xs text-slate-600">Future Phase</p>
        </article>
      </section>
    </div>
  );
}
