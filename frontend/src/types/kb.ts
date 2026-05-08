export type KbAccessLevel = "read" | "write" | "admin";

export interface KnowledgeBase {
  id: number;
  name: string;
  description: string | null;
  domain_type: string | null;
  is_active: boolean;
  created_by: number | null;
  created_at: string | null;
  access_level: KbAccessLevel;
  can_query: boolean;
  can_upload: boolean;
  can_manage: boolean;
  can_view_documents: boolean;
  document_count: number;
}

export interface ChatSessionSummary {
  id: number;
  title: string;
  knowledge_base_id: number;
  knowledge_base_name: string | null;
  created_at: string | null;
}
