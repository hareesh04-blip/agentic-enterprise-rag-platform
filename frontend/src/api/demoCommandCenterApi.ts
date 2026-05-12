import { apiClient } from "./client";

export interface DemoDataStatusResponse {
  seeded_feedback_count: number;
  seeded_task_count: number;
  seeded_audit_count: number;
}

export interface DemoDataOperationRequest {
  dry_run: boolean;
  email?: string;
  knowledge_base_name?: string;
}

export interface DemoDataOperationResponse {
  operation: "seed" | "reset";
  dry_run: boolean;
  status: DemoDataStatusResponse;
  [key: string]: unknown;
}

export const demoCommandCenterApi = {
  async getStatus(): Promise<DemoDataStatusResponse> {
    const { data } = await apiClient.get<DemoDataStatusResponse>("/admin/demo-data/status");
    return data;
  },
  async seed(body: DemoDataOperationRequest): Promise<DemoDataOperationResponse> {
    const { data } = await apiClient.post<DemoDataOperationResponse>("/admin/demo-data/seed", body);
    return data;
  },
  async reset(body: DemoDataOperationRequest): Promise<DemoDataOperationResponse> {
    const { data } = await apiClient.post<DemoDataOperationResponse>("/admin/demo-data/reset", body);
    return data;
  },
};

