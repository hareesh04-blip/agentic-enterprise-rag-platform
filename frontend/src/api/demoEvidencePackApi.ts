import { apiClient } from "./client";

export interface DemoEvidencePackResponse {
  generated_at: string;
  generated_by: {
    id: number;
    email: string;
    full_name: string;
  };
  demo_readiness: unknown;
  platform_status: unknown;
  demo_script: unknown;
  feedback_analytics: unknown;
  open_improvement_tasks: unknown[];
  recent_audit_logs: unknown[];
}

export const demoEvidencePackApi = {
  async getEvidencePack(): Promise<DemoEvidencePackResponse> {
    const { data } = await apiClient.get<DemoEvidencePackResponse>("/admin/demo-evidence-pack");
    return data;
  },
  async downloadEvidencePackPdf(): Promise<Blob> {
    const { data } = await apiClient.get("/admin/demo-evidence-pack/pdf", { responseType: "blob" });
    return data as Blob;
  },
};

