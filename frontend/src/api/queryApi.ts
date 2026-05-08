import { apiClient } from "./client";
import type { ChatMessage, ChatSession, QueryRequest, QueryResponse, SessionMessagesResponse } from "../types/query";

export const queryApi = {
  async askQuestion(payload: QueryRequest): Promise<QueryResponse> {
    const { data } = await apiClient.post<QueryResponse>("/query/ask", payload);
    return data;
  },

  async listSessions(): Promise<ChatSession[]> {
    const { data } = await apiClient.get<ChatSession[]>("/query/sessions");
    return data;
  },

  async getSessionMessages(sessionId: number): Promise<SessionMessagesResponse> {
    const { data } = await apiClient.get<SessionMessagesResponse>(`/query/sessions/${sessionId}/messages`);
    return {
      ...data,
      messages: (data.messages || []).map((msg) => ({
        ...msg,
        sources_json: parseSourcesJson(msg.sources_json),
      })),
    };
  },

  // Backward-compatible alias
  ask(payload: QueryRequest): Promise<QueryResponse> {
    return this.askQuestion(payload);
  },
};

function parseSourcesJson(value: unknown): ChatMessage["sources_json"] {
  if (Array.isArray(value)) return value as ChatMessage["sources_json"];
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? (parsed as ChatMessage["sources_json"]) : null;
    } catch {
      return null;
    }
  }
  return null;
}
