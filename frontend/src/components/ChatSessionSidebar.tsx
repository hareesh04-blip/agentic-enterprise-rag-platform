import type { ChatSession } from "../types/query";

interface ChatSessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: number | null;
  isLoading: boolean;
  onNewChat: () => void;
  onSelectSession: (session: ChatSession) => void;
}

export function ChatSessionSidebar({
  sessions,
  activeSessionId,
  isLoading,
  onNewChat,
  onSelectSession,
}: ChatSessionSidebarProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Sessions</h3>
        <button
          type="button"
          onClick={onNewChat}
          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
        >
          New Chat
        </button>
      </div>

      {isLoading ? <p className="text-xs text-slate-500">Loading sessions...</p> : null}

      {!isLoading && sessions.length === 0 ? (
        <p className="text-xs text-slate-500">No previous sessions for your accessible KBs.</p>
      ) : null}

      <div className="space-y-2">
        {sessions.map((session) => {
          const active = activeSessionId === session.id;
          return (
            <button
              key={session.id}
              type="button"
              onClick={() => onSelectSession(session)}
              className={[
                "w-full rounded-md border px-3 py-2 text-left text-xs",
                active ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-slate-50 hover:bg-slate-100",
              ].join(" ")}
            >
              <p className="font-semibold text-slate-800">{session.title || `Session ${session.id}`}</p>
              <p className="text-slate-600">KB: {session.knowledge_base_name || session.knowledge_base_id}</p>
              <p className="text-slate-500">{session.created_at ? new Date(session.created_at).toLocaleString() : "N/A"}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
