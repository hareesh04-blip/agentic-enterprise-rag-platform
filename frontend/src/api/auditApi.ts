import { apiClient } from "./client";

export interface AuditLogItem {
  id: number;
  actor_user_id: number;
  actor_summary: string;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  knowledge_base_id: number | null;
  knowledge_base_name: string | null;
  metadata_preview: string | null;
  metadata_json: unknown;
  created_at: string | null;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
}

export const auditApi = {
  async listLogs(params: {
    action?: string;
    entity_type?: string;
    knowledge_base_id?: number;
    actor_user_id?: number;
    from_date?: string;
    to_date?: string;
  }): Promise<AuditLogListResponse> {
    const { data } = await apiClient.get<AuditLogListResponse>("/audit/logs", { params });
    return data;
  },
};
