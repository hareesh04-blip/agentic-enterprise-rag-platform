import { apiClient } from "./client";
import type { DemoReadinessResponse } from "./demoReadinessApi";

export interface DemoScriptSection {
  id: string;
  name: string;
  objective: string;
  route: string;
  talking_points: string[];
  expected_outcome: string;
}

export interface DemoScriptResponse {
  title: string;
  sections: DemoScriptSection[];
  demo_readiness: DemoReadinessResponse;
}

export const demoScriptApi = {
  async getDemoScript(): Promise<DemoScriptResponse> {
    const { data } = await apiClient.get<DemoScriptResponse>("/admin/demo-script");
    return data;
  },
};
