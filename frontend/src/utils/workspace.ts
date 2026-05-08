import type { CurrentUser } from "../types/auth";
import type { KnowledgeBase, KbAccessLevel } from "../types/kb";

export type WorkspaceDomain = "api" | "product" | "hr" | "recruitment" | "general";

const DOMAIN_LABELS: Record<WorkspaceDomain, string> = {
  api: "API",
  product: "Product",
  hr: "HR",
  recruitment: "Recruitment",
  general: "General",
};

const ACCESS_LABELS: Record<KbAccessLevel, string> = {
  read: "Read",
  write: "Write",
  admin: "Admin",
};

export function normalizeDomainType(domain: string | null | undefined): WorkspaceDomain {
  if (!domain) return "general";
  const value = domain.toLowerCase();
  if (value.includes("api")) return "api";
  if (value.includes("product")) return "product";
  if (value.includes("hr")) return "hr";
  if (value.includes("recruit")) return "recruitment";
  return "general";
}

export function domainLabel(domain: string | null | undefined): string {
  return DOMAIN_LABELS[normalizeDomainType(domain)];
}

export function workspaceLabelFromKb(kb: KnowledgeBase | null): string {
  if (!kb) return "Workspace";
  return `${domainLabel(kb.domain_type)} Workspace`;
}

export function assistantLabelFromKb(kb: KnowledgeBase | null): string {
  if (!kb) return "Assistant";
  return `${domainLabel(kb.domain_type)} Assistant`;
}

export function documentsLabelFromKb(kb: KnowledgeBase | null): string {
  if (!kb) return "Documents";
  return `${domainLabel(kb.domain_type)} Documents`;
}

export function accessLevelLabel(accessLevel: KbAccessLevel | null | undefined): string {
  if (!accessLevel) return "Unknown";
  return ACCESS_LABELS[accessLevel];
}

export function primaryRoleLabel(user: CurrentUser | null): string {
  if (!user?.roles?.length) return "User";
  return user.roles[0]
    .split("_")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function isRecruitmentRole(user: CurrentUser | null): boolean {
  return Boolean(user?.roles?.some((role) => role.toLowerCase().includes("recruit")));
}
