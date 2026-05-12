import type { CurrentUser } from "../types/auth";
import type { KnowledgeBase } from "../types/kb";

const hasPermission = (user: CurrentUser | null, permission: string): boolean =>
  Boolean(user?.permissions?.includes(permission));

const hasRole = (user: CurrentUser | null, roleNames: string[]): boolean =>
  Boolean(user?.roles?.some((role) => roleNames.includes(role)));

export const canViewChat = (user: CurrentUser | null, kbs: KnowledgeBase[]): boolean =>
  hasPermission(user, "query.ask") && kbs.some((kb) => kb.can_query);

export const canViewDocuments = (user: CurrentUser | null, kbs: KnowledgeBase[]): boolean =>
  (hasPermission(user, "documents.upload") || hasPermission(user, "ingestion.run") || hasPermission(user, "query.ask")) &&
  kbs.some((kb) => kb.can_view_documents);

export const canUploadDocuments = (user: CurrentUser | null, selectedKb: KnowledgeBase | null): boolean => {
  if (!user || !selectedKb) return false;
  if (hasPermission(user, "knowledge_bases.manage")) return true;
  if (!hasPermission(user, "documents.upload") && !hasPermission(user, "ingestion.run")) return false;
  return selectedKb.can_upload;
};

export const canManageKb = (user: CurrentUser | null, selectedKb: KnowledgeBase | null): boolean => {
  if (!user || !selectedKb) return false;
  return hasPermission(user, "knowledge_bases.manage") || selectedKb.can_manage;
};

export const canViewAdmin = (user: CurrentUser | null): boolean =>
  hasRole(user, ["super_admin", "admin", "platform_admin"]) ||
  hasPermission(user, "users.manage") ||
  hasPermission(user, "knowledge_bases.manage");

/** System health / status dashboard: super_admin and admin roles only. */
export const canViewSystemHealth = (user: CurrentUser | null): boolean =>
  hasRole(user, ["super_admin", "admin"]);

export const canViewDiagnostics = (user: CurrentUser | null): boolean =>
  canViewAdmin(user) ||
  hasRole(user, ["qa", "tester"]) ||
  hasPermission(user, "admin.read");
