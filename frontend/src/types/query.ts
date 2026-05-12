export interface QueryRequest {
  project_id: number;
  knowledge_base_id: number;
  question: string;
  top_k?: number;
  session_id?: number;
  debug?: boolean;
}

export interface QuerySourceItem {
  score?: number;
  chunk_type?: string | null;
  section_title?: string | null;
  api_reference_id?: string | null;
  service_name?: string | null;
  service_method?: string | null;
  service_pattern?: string | null;
  file_name?: string | null;
  document_type?: string | null;
  source_domain?: string | null;
  product_name?: string | null;
  document_version?: string | null;
  knowledge_base_id?: number | null;
  knowledge_base_name?: string | null;
  document_id?: number | null;
  /** ISO timestamp from document.uploaded_at when available */
  upload_timestamp?: string | null;
  ingestion_run_id?: number | null;
  /** False when source chunk belongs to a governance-deactivated document */
  is_active_document?: boolean | null;
}

export interface QueryResponse {
  session_id: number;
  project_id: number;
  knowledge_base_id: number;
  question: string;
  answer: string;
  retrieval_mode: string;
  llm_status: string;
  sources: QuerySourceItem[];
  suggested_questions?: string[];
  confidence?: {
    score: number;
    label: "high" | "medium" | "low" | string;
    reasons: string[];
  } | null;
  impact_analysis?: {
    primary_entities: Array<Record<string, any>>;
    related_entities: Array<Record<string, any>>;
    potential_impacts: string[];
    relationship_summary: Array<Record<string, any>>;
    impact_confidence: "high" | "medium" | "low" | string;
  } | null;
  diagnostics?: Record<string, unknown>;
}

export interface ChatSession {
  id: number;
  title: string;
  knowledge_base_id: number;
  knowledge_base_name: string | null;
  created_at: string | null;
}

export interface ChatMessage {
  id?: number | null;
  role: "user" | "assistant";
  content: string;
  sources_json: QuerySourceItem[] | null;
  created_at: string | null;
}

export interface SessionMessagesResponse {
  session_id: number;
  knowledge_base_id: number;
  knowledge_base_name: string | null;
  messages: ChatMessage[];
}

// Backward-compatible aliases for existing code paths
export type AskQueryRequest = QueryRequest;
export type AskQueryResponse = QueryResponse;
