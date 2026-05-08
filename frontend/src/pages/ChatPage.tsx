import { useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { queryApi } from "../api/queryApi";
import { useAuth } from "../auth/AuthContext";
import { canViewDiagnostics } from "../auth/roleAccess";
import { ChatSessionSidebar } from "../components/ChatSessionSidebar";
import type { ChatMessage, ChatSession, QueryResponse, QuerySourceItem } from "../types/query";
import { useEffect } from "react";

interface ChatMessageView {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: QuerySourceItem[] | null;
  suggestedQuestions?: string[];
  confidence?: QueryResponse["confidence"];
  impactAnalysis?: QueryResponse["impact_analysis"];
  createdAt: string;
  kbName: string | null;
  llmStatus?: string;
  retrievalMode?: string;
  diagnostics?: Record<string, unknown>;
}

const INSUFFICIENT_CONTEXT_STATUS = "fallback_insufficient_context";
const INSUFFICIENT_CONTEXT_ANSWER =
  "I could not find enough information in the selected knowledge base to answer this confidently.";
const PROVIDER_SNAPSHOT_KEY = "demo_provider_snapshot";

function sourceTitle(source: QuerySourceItem): string {
  return source.file_name || source.api_reference_id || source.service_name || "Untitled Source";
}

function chunkPreview(source: QuerySourceItem): string | null {
  const raw = source.chunk_type || source.section_title || source.service_pattern || null;
  return raw ? String(raw) : null;
}

function chunkTypeLabel(chunkType?: string | null): string {
  const normalized = String(chunkType || "").toLowerCase();
  if (normalized.includes("authentication")) return "Authentication";
  if (normalized.includes("request_parameters")) return "Request Parameters";
  if (normalized.includes("response_parameters")) return "Response Parameters";
  if (normalized.includes("failed_response") || normalized.includes("error")) return "Error Response";
  if (normalized.includes("api_overview")) return "API Overview";
  if (normalized.includes("product_section")) return "Product Section";
  if (normalized.includes("generic_section")) return "Generic Section";
  if (normalized.includes("api_metadata")) return "API Metadata";
  return "Source Chunk";
}

function whyMatchedText(source: QuerySourceItem): string {
  const chunkType = String(source.chunk_type || "").toLowerCase();
  if (chunkType.includes("authentication")) return "Matched authentication-related content";
  if (chunkType.includes("request_parameters")) return "Matched API request parameters";
  if (chunkType.includes("response_parameters")) return "Matched API response parameters";
  if (chunkType.includes("failed_response") || chunkType.includes("error")) return "Matched error response details";
  if (chunkType.includes("product_section")) return "Matched product workflow information";
  if (source.api_reference_id || source.service_name) return "Matched API/service metadata";
  if (source.section_title) return "Matched section-level document context";
  return "Matched relevant knowledge base context";
}

function sourceMetadataRichness(source: QuerySourceItem): number {
  const fields = [
    source.chunk_type,
    source.section_title,
    source.api_reference_id,
    source.service_name,
    source.service_method,
    source.service_pattern,
    source.product_name,
    source.document_type,
    source.source_domain,
  ];
  return fields.filter((value) => value !== null && value !== undefined && String(value).trim()).length;
}

function sourceRelevanceLabel(source: QuerySourceItem, index: number, total: number): "High" | "Medium" | "Low" {
  const richness = sourceMetadataRichness(source);
  const positionBoost = total <= 0 ? 0 : (total - index) / total;
  const relevanceScore = richness * 0.12 + positionBoost;
  if (relevanceScore >= 1.1 || index <= 1) return "High";
  if (relevanceScore >= 0.7 || index <= 3) return "Medium";
  return "Low";
}

function sourceRelevanceClasses(level: "High" | "Medium" | "Low"): string {
  if (level === "High") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (level === "Medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-300 bg-slate-100 text-slate-700";
}

function groupSourceTitle(source: QuerySourceItem): string {
  return source.file_name || source.product_name || source.source_domain || source.document_type || "Unknown Source";
}

function confidenceBadgeClasses(label?: string | null): string {
  const normalized = String(label || "").toLowerCase();
  if (normalized === "high") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (normalized === "medium") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function impactBadgeClasses(label?: string | null): string {
  const normalized = String(label || "").toLowerCase();
  if (normalized === "high") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (normalized === "medium") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-slate-300 bg-slate-100 text-slate-700";
}

function renderEntityLabel(entity: Record<string, any>, fallback: string): string {
  const type = String(entity?.type ?? "").trim();
  const id = String(entity?.id ?? "").trim();
  if (type && id) return `${type}: ${id}`;
  if (id) return id;
  if (type) return type;
  return fallback;
}

export function ChatPage() {
  const { user, selectedKb, accessibleKbs, setSelectedKbById, logout } = useAuth();
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isLoadingSessionMessages, setIsLoadingSessionMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [activeSessionKbId, setActiveSessionKbId] = useState<number | null>(null);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [expandedSourceCards, setExpandedSourceCards] = useState<Record<string, boolean>>({});
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const canQuerySelectedKb = Boolean(selectedKb?.can_query);
  const canSeeDiagnostics = canViewDiagnostics(user);
  const latestAssistant = [...messages].reverse().find((m) => m.role === "assistant") ?? null;
  const latestAssistantIsFallback = Boolean(
    latestAssistant &&
      (latestAssistant.llmStatus === INSUFFICIENT_CONTEXT_STATUS ||
        latestAssistant.content.trim() === INSUFFICIENT_CONTEXT_ANSWER ||
        String(latestAssistant.diagnostics?.llm_status ?? "").toLowerCase() === INSUFFICIENT_CONTEXT_STATUS),
  );
  const latestDiagnostics = latestAssistant?.diagnostics ?? {};
  const sourceCount = latestAssistantIsFallback ? 0 : latestAssistant?.sources?.length ?? 0;
  const disableSubmit = isSubmitting || !question.trim() || !selectedKb || !canQuerySelectedKb;
  const accessibleKbIds = useMemo(() => new Set(accessibleKbs.map((kb) => kb.id)), [accessibleKbs]);

  const diagnosticsRows = useMemo(
    () =>
      [
        "llm_provider",
        "embedding_provider",
        "llm_model",
        "embedding_model",
        "retrieval_mode",
        "vector_retrieval_outcome",
        "vector_results_count",
        "hybrid_fusion_used",
        "rerank_strategy",
        "vector_confidence_bucket",
        "selected_prompt_chunk_count",
        "dedup_chunks_removed",
        "fallback_triggered",
        "fallback_reason",
        "llm_status",
      ].map((key) => ({ key, value: latestDiagnostics?.[key] ?? latestAssistant?.llmStatus ?? "N/A" })),
    [latestDiagnostics, latestAssistant],
  );

  const groupedSources = useMemo(() => {
    const groups = new Map<string, { title: string; items: Array<{ source: QuerySourceItem; index: number; key: string }> }>();
    const sources = latestAssistant?.sources ?? [];
    sources.forEach((source, index) => {
      const title = groupSourceTitle(source);
      const groupKey = title.toLowerCase();
      const key = `${groupKey}-${index}-${source.api_reference_id ?? "no-api"}-${source.service_name ?? "no-service"}`;
      if (!groups.has(groupKey)) {
        groups.set(groupKey, { title, items: [] });
      }
      groups.get(groupKey)?.items.push({ source, index, key });
    });
    return Array.from(groups.entries()).map(([groupKey, value]) => ({
      groupKey,
      title: value.title,
      items: value.items,
    }));
  }, [latestAssistant]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSubmitting]);

  const loadSessions = async () => {
    setIsLoadingSessions(true);
    try {
      const all = await queryApi.listSessions();
      setSessions(all.filter((session) => accessibleKbIds.has(session.knowledge_base_id)));
    } catch {
      // keep non-blocking for chat UX
    } finally {
      setIsLoadingSessions(false);
    }
  };

  useEffect(() => {
    void loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessibleKbs.length]);

  useEffect(() => {
    if (activeSessionId && selectedKb && activeSessionKbId && selectedKb.id !== activeSessionKbId) {
      setActiveSessionId(null);
      setActiveSessionKbId(null);
      setNotice("KB changed. Active session was cleared to preserve KB isolation. Start a new chat.");
      setMessages([]);
    }
  }, [selectedKb, activeSessionId, activeSessionKbId]);

  const handleError = (err: unknown, fallback = "Unexpected error occurred. Please retry.") => {
    if (err instanceof AxiosError) {
      if (err.response?.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      if (err.response?.status === 403) {
        setError("Not authorized for this knowledge base, session, or activity.");
        return;
      }
      if (!err.response) {
        setError("Network error. Please retry.");
        return;
      }
      setError(typeof err.response.data?.detail === "string" ? err.response.data.detail : fallback);
      return;
    }
    setError(fallback);
  };

  const startNewChat = () => {
    setActiveSessionId(null);
    setActiveSessionKbId(null);
    setMessages([]);
    setError(null);
    setNotice("Started a new chat in the currently selected KB.");
  };

  const loadSession = async (session: ChatSession) => {
    setError(null);
    setNotice(null);
    if (!accessibleKbIds.has(session.knowledge_base_id)) {
      setError("You are not authorized for this session's knowledge base.");
      return;
    }
    const kb = accessibleKbs.find((x) => x.id === session.knowledge_base_id);
    if (!kb) {
      setError("Session KB is not currently available.");
      return;
    }
    setSelectedKbById(kb.id);
    setIsLoadingSessionMessages(true);
    try {
      const payload = await queryApi.getSessionMessages(session.id);
      if (!accessibleKbIds.has(payload.knowledge_base_id)) {
        setError("You are not authorized for this session's messages.");
        return;
      }
      const mapped: ChatMessageView[] = payload.messages.map((msg: ChatMessage, idx) => ({
        id: `${payload.session_id}-${idx}-${msg.role}`,
        role: msg.role,
        content: msg.content,
        sources: msg.sources_json,
        createdAt: msg.created_at || new Date().toISOString(),
        kbName: payload.knowledge_base_name,
      }));
      setMessages(mapped);
      setActiveSessionId(payload.session_id);
      setActiveSessionKbId(payload.knowledge_base_id);
      setNotice(`Loaded session #${payload.session_id}.`);
    } catch (err) {
      handleError(err, "Failed to load session messages.");
    } finally {
      setIsLoadingSessionMessages(false);
    }
  };

  const submitQuestion = async (overrideQuestion?: string) => {
    const prompt = (overrideQuestion ?? question).trim();
    if (isSubmitting || !prompt || !selectedKb || !canQuerySelectedKb) return;
    if (activeSessionId && activeSessionKbId && activeSessionKbId !== selectedKb.id) {
      setError("Active session belongs to a different KB. Start a new chat first.");
      return;
    }
    setError(null);
    setNotice(null);
    setIsSubmitting(true);
    try {
      const response: QueryResponse = await queryApi.askQuestion({
        project_id: 1,
        knowledge_base_id: selectedKb.id,
        question: prompt,
        top_k: 5,
        session_id: activeSessionId ?? undefined,
        debug: true,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `u-${Date.now()}`,
          role: "user",
          content: prompt,
          sources: null,
          createdAt: new Date().toISOString(),
          kbName: selectedKb.name,
        },
        {
          id: `a-${Date.now() + 1}`,
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          suggestedQuestions: response.suggested_questions,
          confidence: response.confidence,
          impactAnalysis: response.impact_analysis,
          createdAt: new Date().toISOString(),
          kbName: selectedKb.name,
          llmStatus: response.llm_status,
          retrievalMode: response.retrieval_mode,
          diagnostics: response.diagnostics,
        },
      ]);
      const providerSnapshot = {
        llm_provider: String(response.diagnostics?.llm_provider ?? "backend-configured"),
        llm_status: response.llm_status,
      };
      window.localStorage.setItem(PROVIDER_SNAPSHOT_KEY, JSON.stringify(providerSnapshot));
      setActiveSessionId(response.session_id);
      setActiveSessionKbId(response.knowledge_base_id);
      setQuestion("");
      await loadSessions();
    } catch (err) {
      handleError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await submitQuestion();
  };

  const onQuestionKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submitQuestion();
    }
  };

  const handleSuggestedQuestionClick = async (suggestedQuestion: string) => {
    if (isSubmitting || !selectedKb || !canQuerySelectedKb) return;
    await submitQuestion(suggestedQuestion);
  };

  const toggleSourceCard = (cardKey: string) => {
    setExpandedSourceCards((prev) => ({ ...prev, [cardKey]: !prev[cardKey] }));
  };

  if (!selectedKb) {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        Select a Knowledge Base to start asking questions. This workspace only uses KBs your account can access.
      </div>
    );
  }

  if (!canQuerySelectedKb) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        You are not authorized to query the selected Knowledge Base.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
      <section className="space-y-4">
        {notice ? <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">{notice}</div> : null}
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">KB-aware chat</p>
          <p className="mt-1 text-sm text-slate-700">
            Active KB: <span className="font-medium">{selectedKb.name}</span>
          </p>
          <p className="mt-1 text-xs text-slate-600">
            Active session: <span className="font-semibold">{activeSessionId ?? "New chat"}</span>
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <label className="block text-sm font-medium text-slate-700" htmlFor="chat-question">
            Ask a question
          </label>
          <textarea
            id="chat-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={onQuestionKeyDown}
            rows={4}
            placeholder="Enter your question. Press Enter to send, Shift+Enter for newline."
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={disableSubmit}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? "Asking..." : "Ask"}
            </button>
            <p className="text-xs text-slate-500">Query payload includes selected `knowledge_base_id` and `debug=true`.</p>
          </div>
          {error ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
              <button
                type="button"
                onClick={() => void submitQuestion()}
                className="ml-3 rounded border border-red-300 bg-white px-2 py-0.5 text-xs font-medium text-red-700"
              >
                Retry
              </button>
            </div>
          ) : null}
        </form>

        <div className="space-y-3">
          {messages.length === 0 && !isSubmitting ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
              Ask your first question in this workspace. Responses are scoped to the selected knowledge base.
            </div>
          ) : null}
          {messages.map((message) => {
            const isAssistant = message.role === "assistant";
            const isInsufficient = message.llmStatus === INSUFFICIENT_CONTEXT_STATUS;
            const hasConfidence = isAssistant && !isSubmitting && !!message.confidence;
            const confidenceLabel = String(message.confidence?.label || "low").toLowerCase();
            const confidenceScore = Math.round(Math.max(0, Math.min(1, Number(message.confidence?.score ?? 0))) * 100);
            const confidenceReasons = Array.isArray(message.confidence?.reasons) ? message.confidence?.reasons : [];
            const showSuggestedQuestions =
              Boolean(selectedKb) &&
              isAssistant &&
              !isInsufficient &&
              !isSubmitting &&
              Array.isArray(message.suggestedQuestions) &&
              message.suggestedQuestions.length > 0;
            const showImpactAnalysis =
              isAssistant &&
              !isInsufficient &&
              !!message.impactAnalysis &&
              Array.isArray(message.impactAnalysis.primary_entities) &&
              Array.isArray(message.impactAnalysis.related_entities) &&
              Array.isArray(message.impactAnalysis.potential_impacts) &&
              Array.isArray(message.impactAnalysis.relationship_summary);
            return (
              <article
                key={message.id}
                className={`space-y-3 rounded-lg border p-4 ${
                  isAssistant ? "border-blue-100 bg-blue-50/30" : "border-slate-200 bg-white"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {isAssistant ? "Assistant answer" : "User question"}
                    </p>
                    {hasConfidence ? (
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${confidenceBadgeClasses(confidenceLabel)}`}
                        title={confidenceReasons.length ? confidenceReasons.join(" | ") : "Confidence derived from retrieval signals"}
                      >
                        {`${confidenceLabel.charAt(0).toUpperCase()}${confidenceLabel.slice(1)} confidence (${confidenceScore}%)`}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-900">{message.content}</p>
                </div>
                {isAssistant ? (
                  <div>
                    <button
                      type="button"
                      onClick={() => void navigator.clipboard.writeText(message.content)}
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Copy answer
                    </button>
                  </div>
                ) : null}

                {showSuggestedQuestions ? (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suggested follow-ups</p>
                    <div className="flex flex-wrap gap-2">
                      {message.suggestedQuestions?.map((suggestedQuestion, index) => (
                        <button
                          key={`${message.id}-suggested-${index}`}
                          type="button"
                          onClick={() => void handleSuggestedQuestionClick(suggestedQuestion)}
                          disabled={isSubmitting}
                          className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {suggestedQuestion}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                {showImpactAnalysis ? (
                  <section className="rounded-md border border-slate-200 bg-white p-3 shadow-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Impact Analysis</p>
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${impactBadgeClasses(
                          String(message.impactAnalysis?.impact_confidence || "low"),
                        )}`}
                      >
                        {`${String(message.impactAnalysis?.impact_confidence || "low").charAt(0).toUpperCase()}${String(
                          message.impactAnalysis?.impact_confidence || "low",
                        ).slice(1)} confidence`}
                      </span>
                    </div>

                    <div className="mt-2 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div className="rounded border border-slate-200 bg-slate-50 p-2">
                        <p className="text-xs font-semibold text-slate-700">
                          Primary entities ({message.impactAnalysis?.primary_entities?.length ?? 0})
                        </p>
                        {message.impactAnalysis?.primary_entities?.length ? (
                          <ul className="mt-1 space-y-1 text-xs text-slate-700">
                            {message.impactAnalysis.primary_entities.slice(0, 5).map((entity, idx) => (
                              <li key={`${message.id}-impact-primary-${idx}`} className="truncate">
                                - {renderEntityLabel(entity, "Entity")}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-1 text-xs text-slate-500">No primary entities detected.</p>
                        )}
                      </div>

                      <div className="rounded border border-slate-200 bg-slate-50 p-2">
                        <p className="text-xs font-semibold text-slate-700">
                          Related entities ({message.impactAnalysis?.related_entities?.length ?? 0})
                        </p>
                        {message.impactAnalysis?.related_entities?.length ? (
                          <ul className="mt-1 space-y-1 text-xs text-slate-700">
                            {message.impactAnalysis.related_entities.slice(0, 5).map((entity, idx) => (
                              <li key={`${message.id}-impact-related-${idx}`} className="truncate">
                                - {renderEntityLabel(entity, "Related entity")}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-1 text-xs text-slate-500">No related entities detected.</p>
                        )}
                      </div>
                    </div>

                    <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-2">
                      <p className="text-xs font-semibold text-slate-700">Potential impacts</p>
                      {message.impactAnalysis?.potential_impacts?.length ? (
                        <ul className="mt-1 space-y-1 text-xs text-slate-700">
                          {message.impactAnalysis.potential_impacts.map((impact, idx) => (
                            <li key={`${message.id}-impact-text-${idx}`}>- {impact}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-1 text-xs text-slate-500">No explicit impact statements generated.</p>
                      )}
                    </div>

                    <details className="mt-3 rounded border border-slate-200 bg-slate-50 p-2">
                      <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                        Relationship details ({message.impactAnalysis?.relationship_summary?.length ?? 0})
                      </summary>
                      {message.impactAnalysis?.relationship_summary?.length ? (
                        <div className="mt-2 space-y-2">
                          {message.impactAnalysis.relationship_summary.map((relationship, idx) => {
                            const fromLabel = renderEntityLabel((relationship?.from as Record<string, any>) ?? {}, "from");
                            const toLabel = renderEntityLabel((relationship?.to as Record<string, any>) ?? {}, "to");
                            const rule = String(relationship?.rule ?? "rule");
                            const strength = String(relationship?.strength ?? "unknown");
                            return (
                              <div
                                key={`${message.id}-impact-rel-${idx}`}
                                className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                              >
                                <p className="font-medium text-slate-800">{rule}</p>
                                <p>
                                  {fromLabel} {"->"} {toLabel}
                                </p>
                                <p className="text-slate-500">strength: {strength}</p>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="mt-2 text-xs text-slate-500">No relationship details available.</p>
                      )}
                    </details>
                  </section>
                ) : null}

                {isInsufficient ? (
                  <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    The system did not find enough trusted context in this KB.
                  </div>
                ) : null}

                {isAssistant ? (
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 md:grid-cols-5">
                    <p>
                      <span className="font-semibold">KB:</span> {message.kbName ?? "N/A"}
                    </p>
                    <p>
                      <span className="font-semibold">llm_status:</span> {message.llmStatus ?? "N/A"}
                    </p>
                    <p>
                      <span className="font-semibold">retrieval_mode:</span> {message.retrievalMode ?? "N/A"}
                    </p>
                    <p>
                      <span className="font-semibold">source_count:</span> {message.sources?.length ?? 0}
                    </p>
                    <p>
                      <span className="font-semibold">time:</span> {new Date(message.createdAt).toLocaleTimeString()}
                    </p>
                  </div>
                ) : null}
              </article>
            );
          })}
          {isSubmitting ? (
            <article className="animate-pulse space-y-3 rounded-lg border border-slate-200 bg-white p-4">
              <div className="h-3 w-32 rounded bg-slate-200" />
              <div className="h-3 w-full rounded bg-slate-200" />
              <div className="h-3 w-11/12 rounded bg-slate-200" />
            </article>
          ) : null}
          <div ref={bottomRef} />
        </div>
      </section>

      <aside className="space-y-4">
        <ChatSessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          isLoading={isLoadingSessions || isLoadingSessionMessages}
          onNewChat={startNewChat}
          onSelectSession={loadSession}
        />
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-900">Sources ({sourceCount})</h3>
          {latestAssistant?.sources?.length && !latestAssistantIsFallback ? (
            <div className="mt-3 space-y-3">
              {groupedSources.map((group) => (
                <div key={group.groupKey} className="space-y-2 rounded-md border border-slate-200 bg-slate-50/60 p-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-slate-800">{group.title}</p>
                    <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] text-slate-700">
                      {group.items.length} source{group.items.length > 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {group.items.map(({ source, index, key }) => {
                      const expanded = Boolean(expandedSourceCards[key]);
                      const chunkLabel = chunkTypeLabel(source.chunk_type);
                      const relevanceLabel = sourceRelevanceLabel(source, index, latestAssistant.sources?.length ?? 0);
                      const asyncIndicator =
                        String(source.service_pattern || "").toLowerCase().includes("asynch") ||
                        String(source.service_pattern || "").toLowerCase().includes("callback")
                          ? "Async"
                          : source.service_pattern
                            ? "Sync"
                            : null;
                      return (
                        <article key={key} className="rounded-md border border-slate-200 bg-white p-2 text-xs shadow-sm">
                          <button
                            type="button"
                            onClick={() => toggleSourceCard(key)}
                            className="w-full text-left"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="truncate font-semibold text-slate-800">
                                  #{index + 1} {sourceTitle(source)}
                                </p>
                                <p className="mt-1 text-[11px] text-slate-600">{whyMatchedText(source)}</p>
                              </div>
                              <span className="text-[11px] text-slate-500">{expanded ? "Hide" : "Show"}</span>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-1">
                              <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] text-blue-700">
                                {chunkLabel}
                              </span>
                              <span className={`rounded-full border px-2 py-0.5 text-[11px] ${sourceRelevanceClasses(relevanceLabel)}`}>
                                {relevanceLabel} relevance
                              </span>
                              {source.service_name ? (
                                <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] text-indigo-700">
                                  service: {source.service_name}
                                </span>
                              ) : null}
                              {source.api_reference_id ? (
                                <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] text-violet-700">
                                  api: {source.api_reference_id}
                                </span>
                              ) : null}
                              {source.service_method ? (
                                <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] text-slate-700">
                                  {source.service_method}
                                </span>
                              ) : null}
                              {asyncIndicator ? (
                                <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                                  {asyncIndicator}
                                </span>
                              ) : null}
                            </div>
                          </button>
                          <div
                            className={`overflow-hidden transition-all duration-200 ease-in-out ${
                              expanded ? "mt-2 max-h-64 opacity-100" : "max-h-0 opacity-0"
                            }`}
                          >
                            <div className="space-y-1 border-t border-slate-200 pt-2 text-slate-600">
                              <p>document_type: {source.document_type ?? "N/A"}</p>
                              <p>product_name: {source.product_name ?? "N/A"}</p>
                              <p>section_title: {source.section_title ?? "N/A"}</p>
                              <p>source_domain: {source.source_domain ?? "N/A"}</p>
                              <p>document_version: {source.document_version ?? "N/A"}</p>
                              <p>preview: {chunkPreview(source) ?? "N/A"}</p>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">No sources for the current result.</p>
          )}
        </section>

        {canSeeDiagnostics ? (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <button
              type="button"
              onClick={() => setShowDiagnostics((prev) => !prev)}
              className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-900"
            >
              Diagnostics
              <span className="text-xs text-slate-500">{showDiagnostics ? "Hide" : "Show"}</span>
            </button>
            {showDiagnostics ? (
              <div className="mt-3 space-y-3 text-xs text-slate-700">
                <div>
                  <p className="mb-1 font-semibold text-slate-800">Providers</p>
                  {diagnosticsRows
                    .filter((row) => row.key.includes("provider") || row.key.includes("model"))
                    .map((row) => (
                      <p key={row.key}>
                        <span className="font-semibold">{row.key}:</span> {String(row.value ?? "N/A")}
                      </p>
                    ))}
                </div>
                <div>
                  <p className="mb-1 font-semibold text-slate-800">Retrieval</p>
                  {diagnosticsRows
                    .filter((row) => row.key.includes("retrieval") || row.key.includes("vector") || row.key.includes("rerank"))
                    .map((row) => (
                      <p key={row.key}>
                        <span className="font-semibold">{row.key}:</span> {String(row.value ?? "N/A")}
                      </p>
                    ))}
                </div>
                <div>
                  <p className="mb-1 font-semibold text-slate-800">Fallback / Status</p>
                  {diagnosticsRows
                    .filter((row) => row.key.includes("fallback") || row.key.includes("llm_status") || row.key.includes("dedup"))
                    .map((row) => (
                      <p key={row.key}>
                        <span className="font-semibold">{row.key}:</span> {String(row.value ?? "N/A")}
                      </p>
                    ))}
                </div>
              </div>
            ) : null}
          </section>
        ) : null}
      </aside>
    </div>
  );
}
