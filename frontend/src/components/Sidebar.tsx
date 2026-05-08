import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { canViewAdmin, canViewChat, canViewDiagnostics, canViewDocuments } from "../auth/roleAccess";
import {
  accessLevelLabel,
  assistantLabelFromKb,
  documentsLabelFromKb,
  isRecruitmentRole,
  workspaceLabelFromKb,
} from "../utils/workspace";

interface NavItem {
  to: string;
  label: string;
}

export function Sidebar() {
  const { user, accessibleKbs, selectedKb } = useAuth();
  const canChat = canViewChat(user, accessibleKbs);
  const canDocs = canViewDocuments(user, accessibleKbs);
  const canAdmin = canViewAdmin(user);
  const canDiagnostics = canViewDiagnostics(user);
  const showRecruitmentPlaceholder = isRecruitmentRole(user) || canAdmin;

  const workspaceItems: NavItem[] = [{ to: "/", label: "Workspace Home" }];
  if (canChat) workspaceItems.push({ to: "/chat", label: assistantLabelFromKb(selectedKb) });
  if (canDocs) workspaceItems.push({ to: "/documents", label: documentsLabelFromKb(selectedKb) });

  const adminItems: NavItem[] = [];
  if (canAdmin) adminItems.push({ to: "/admin", label: "Admin Workspace" });
  if (canDiagnostics) adminItems.push({ to: "/not-authorized", label: "Advanced Diagnostics (Future Phase)" });

  return (
    <aside className="w-64 border-r border-slate-200 bg-white p-4">
      <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{workspaceLabelFromKb(selectedKb)}</p>
        <p className="mt-1 text-sm font-medium text-slate-800">{selectedKb?.name ?? "No KB selected"}</p>
        {selectedKb ? (
          <p className="mt-1 text-xs text-slate-600">Access level: {accessLevelLabel(selectedKb.access_level)}</p>
        ) : (
          <p className="mt-1 text-xs text-amber-700">No KB access assigned yet.</p>
        )}
      </div>

      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Workspace</p>
      <nav className="space-y-1">
        {workspaceItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                "block rounded-md px-3 py-2 text-sm",
                isActive ? "bg-blue-600 text-white" : "text-slate-700 hover:bg-slate-100",
              ].join(" ")
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      {(adminItems.length > 0 || showRecruitmentPlaceholder) && (
        <>
          <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">Administration</p>
          <nav className="space-y-1">
            {adminItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  "block rounded-md px-3 py-2 text-sm",
                  isActive ? "bg-blue-600 text-white" : "text-slate-700 hover:bg-slate-100",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
            ))}
          </nav>
        </>
      )}

      {showRecruitmentPlaceholder ? (
        <div className="mt-5 rounded-md border border-dashed border-slate-300 bg-slate-50 p-3">
          <p className="text-xs font-semibold text-slate-700">Recruitment Workspace</p>
          <p className="mt-1 text-xs text-slate-500">Future Phase placeholder for recruiter workflows.</p>
        </div>
      ) : null}
    </aside>
  );
}
