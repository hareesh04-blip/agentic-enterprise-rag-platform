import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ProviderBadge } from "./ProviderBadge";
import { accessLevelLabel, domainLabel, primaryRoleLabel } from "../utils/workspace";

export function TopNav() {
  const { user, selectedKb, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
      <div className="space-y-1">
        <p className="text-sm font-semibold text-slate-800">Enterprise Multi-Domain AI Knowledge Platform</p>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-700">
            KB: {selectedKb?.name ?? "Not selected"}
          </span>
          {selectedKb ? (
            <>
              <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-blue-700">
                {domainLabel(selectedKb.domain_type)}
              </span>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-emerald-700">
                {accessLevelLabel(selectedKb.access_level)}
              </span>
            </>
          ) : null}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <ProviderBadge />
        <span className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700">
          Role: {primaryRoleLabel(user)}
        </span>
        <div className="hidden text-right md:block">
          <p className="text-xs font-medium text-slate-700">{user?.full_name ?? "User"}</p>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="rounded-md bg-slate-800 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
