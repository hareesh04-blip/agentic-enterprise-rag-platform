import { apiClient } from "./client";
import type { RetrievalTestResponse } from "../types/diagnostics";

export interface RetrievalTestRequest {
  knowledge_base_id: number;
  question: string;
  top_k?: number;
}

export const diagnosticsApi = {
  async runRetrievalTest(payload: RetrievalTestRequest): Promise<RetrievalTestResponse> {
    const { data } = await apiClient.post<RetrievalTestResponse>("/diagnostics/retrieval-test", payload);
    return data;
  },
};
