import { apiClient } from "./client";
import type { KnowledgeBase } from "../types/kb";

export const kbApi = {
  async listMyKnowledgeBases(): Promise<KnowledgeBase[]> {
    const { data } = await apiClient.get<KnowledgeBase[]>("/knowledge-bases/me");
    return data;
  },

  async listAccessibleKnowledgeBases(): Promise<KnowledgeBase[]> {
    return this.listMyKnowledgeBases();
  },
};
