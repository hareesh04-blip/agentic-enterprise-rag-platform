import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { canViewAdmin, canViewChat, canViewDiagnostics, canViewDocuments, canViewSystemHealth } from "../auth/roleAccess";
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

function AdminSubnav({ title, items, isFirstSection }: { title: string; items: NavItem[]; isFirstSection: boolean }) {
  if (items.length === 0) return null;
  return (
    <>
      <p
        className={[
          "mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500",
          isFirstSection ? "" : "mt-4",
        ].join(" ")}
      >
        {title}
      </p>
      <nav className="space-y-1">
        {items.map((item) => (
          <NavLink
            key={`${item.to}::${item.label}`}
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
  );
}

export function Sidebar() {
  const { user, accessibleKbs, selectedKb } = useAuth();
  const canChat = canViewChat(user, accessibleKbs);
  const canDocs = canViewDocuments(user, accessibleKbs);
  const canAdmin = canViewAdmin(user);
  const canHealth = canViewSystemHealth(user);
  const canDiagnostics = canViewDiagnostics(user);
  const showRecruitmentPlaceholder = isRecruitmentRole(user) || canAdmin;

  const workspaceItems: NavItem[] = [{ to: "/", label: "Workspace Home" }];
  if (canChat) workspaceItems.push({ to: "/chat", label: assistantLabelFromKb(selectedKb) });
  if (canDocs) workspaceItems.push({ to: "/documents", label: documentsLabelFromKb(selectedKb) });

  const coreItems: NavItem[] = [];
  if (canAdmin) coreItems.push({ to: "/admin", label: "Admin Workspace" });

  const diagnosticsItems: NavItem[] = [];
  if (canHealth) {
    diagnosticsItems.push({ to: "/admin/health", label: "System Health" });
    diagnosticsItems.push({ to: "/admin/retrieval-diagnostics", label: "Retrieval Diagnostics" });
    diagnosticsItems.push({ to: "/admin/audit-logs", label: "Audit Logs" });
  }
  if (canDiagnostics) {
    diagnosticsItems.push({ to: "/not-authorized", label: "Advanced Diagnostics (Future Phase)" });
  }

  const qualityItems: NavItem[] = [];
  if (canHealth) {
    qualityItems.push({ to: "/admin/query-feedback", label: "Query Feedback" });
    qualityItems.push({ to: "/admin/feedback-analytics", label: "Feedback Analytics" });
    qualityItems.push({ to: "/admin/improvement-tasks", label: "Improvement Tasks" });
  }

  const demoItems: NavItem[] = [];
  if (canHealth) {
    demoItems.push({ to: "/admin/demo-readiness", label: "Demo Readiness" });
    demoItems.push({ to: "/admin/demo-script", label: "Demo Script" });
    demoItems.push({ to: "/admin/demo-command-center", label: "Demo Command Center" });
    demoItems.push({ to: "/admin/demo-evidence-pack", label: "Evidence Pack" });
    demoItems.push({ to: "/admin/demo-runbook", label: "Demo Runbook" });
  }

  const adminSectionGroups: { title: string; items: NavItem[] }[] = [
    { title: "Core", items: coreItems },
    { title: "Diagnostics", items: diagnosticsItems },
    { title: "Quality", items: qualityItems },
    { title: "Demo", items: demoItems },
  ];

  const hasAdminNav = adminSectionGroups.some((g) => g.items.length > 0);
  const firstNonEmptyAdminIdx = adminSectionGroups.findIndex((g) => g.items.length > 0);

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

      {(hasAdminNav || showRecruitmentPlaceholder) && (
        <>
          <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">Administration</p>
          {adminSectionGroups.map((group, idx) =>
            group.items.length === 0 ? null : (
              <AdminSubnav
                key={group.title}
                title={group.title}
                items={group.items}
                isFirstSection={idx === firstNonEmptyAdminIdx}
              />
            ),
          )}
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
