import { apiClient } from "./client";

export interface DemoRunbookSection {
  id: string;
  title: string;
  notes: string[];
  commands: string[];
}

export interface DemoRunbookResponse {
  title: string;
  description: string;
  sections: DemoRunbookSection[];
}

export const demoRunbookApi = {
  async getRunbook(): Promise<DemoRunbookResponse> {
    const { data } = await apiClient.get<DemoRunbookResponse>("/admin/demo-runbook");
    return data;
  },
};
