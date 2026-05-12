import { apiBaseUrl, apiClient, tokenStorage } from "./client";
import type { ChatMessage, ChatSession, QueryRequest, QueryResponse, SessionMessagesResponse } from "../types/query";

export interface AskStreamHandlers {
  onToken?: (text: string) => void;
  onStart?: (data: Record<string, unknown>) => void;
}

function consumeSseBlocks(buffer: string): { events: Array<{ event: string; data: unknown }>; rest: string } {
  const events: Array<{ event: string; data: unknown }> = [];
  let rest = buffer;
  const delim = /\r?\n\r?\n/;
  while (true) {
    const match = rest.match(delim);
    if (!match || match.index === undefined) break;
    const block = rest.slice(0, match.index);
    rest = rest.slice(match.index + match[0].length);
    let eventName = "message";
    let dataStr = "";
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      if (line.startsWith("data:")) dataStr = line.slice(5).trim();
    }
    if (dataStr) {
      try {
        events.push({ event: eventName, data: JSON.parse(dataStr) as unknown });
      } catch {
        events.push({ event: eventName, data: dataStr });
      }
    }
  }
  return { events, rest };
}

export const queryApi = {
  async askQuestion(payload: QueryRequest): Promise<QueryResponse> {
    const { data } = await apiClient.post<QueryResponse>("/query/ask", payload);
    return data;
  },

  /**
   * POST /query/ask-stream (SSE). Throws on HTTP errors or `error` events.
   * Resolves with the `done` payload (same shape as QueryResponse).
   */
  async askQuestionStream(payload: QueryRequest, handlers: AskStreamHandlers = {}): Promise<QueryResponse> {
    const token = tokenStorage.get();
    const res = await fetch(`${apiBaseUrl}/query/ask-stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errBody = (await res.json()) as { detail?: unknown };
        if (typeof errBody.detail === "string") detail = errBody.detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");
    const decoder = new TextDecoder();
    let carry = "";
    let final: QueryResponse | null = null;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      carry += decoder.decode(value, { stream: true });
      const { events, rest } = consumeSseBlocks(carry);
      carry = rest;
      for (const { event, data } of events) {
        if (event === "start" && handlers.onStart && data && typeof data === "object") {
          handlers.onStart(data as Record<string, unknown>);
        }
        if (event === "token" && handlers.onToken && data && typeof data === "object") {
          const text = (data as { text?: string }).text;
          if (text) handlers.onToken(text);
        }
        if (event === "done") {
          final = data as QueryResponse;
        }
        if (event === "error") {
          const detail =
            data && typeof data === "object" && "detail" in data ? String((data as { detail?: unknown }).detail) : "Stream error";
          throw new Error(detail);
        }
      }
    }
    if (!final) throw new Error("Stream ended without a done event");
    return final;
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
