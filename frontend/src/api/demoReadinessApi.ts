import { apiClient } from "./client";

export type DemoCheckStatus = "pass" | "warn" | "fail";
export type DemoOverallStatus = "ready" | "warning" | "blocked";

export interface DemoReadinessCheck {
  name: string;
  status: DemoCheckStatus;
  message: string;
}

export interface DemoReadinessSummary {
  active_knowledge_bases: number;
  documents_count: number;
  feedback_count: number;
  open_improvement_tasks: number;
  recent_audit_logs: number;
}

export interface DemoReadinessResponse {
  overall_status: DemoOverallStatus;
  checks: DemoReadinessCheck[];
  summary: DemoReadinessSummary;
  recommendations: string[];
}

export const demoReadinessApi = {
  async getDemoReadiness(): Promise<DemoReadinessResponse> {
    const { data } = await apiClient.get<DemoReadinessResponse>("/admin/demo-readiness");
    return data;
  },
};
