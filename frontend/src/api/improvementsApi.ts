import { apiClient } from "./client";

export type ImprovementTaskStatus = "open" | "in_progress" | "resolved" | "dismissed";
export type ImprovementTaskPriority = "low" | "medium" | "high";

export interface LinkedFeedbackSummary {
  id: number;
  rating: string;
  question_text: string;
  answer_preview: string;
  comment: string | null;
  created_at: string | null;
}

export interface ImprovementTaskItem {
  id: number;
  feedback_id: number | null;
  knowledge_base_id: number;
  knowledge_base_name: string;
  title: string;
  description: string;
  status: ImprovementTaskStatus;
  priority: ImprovementTaskPriority;
  assigned_to: number | null;
  assigned_to_label: string | null;
  created_by: number;
  created_by_label: string;
  created_at: string | null;
  updated_at: string | null;
  resolution_notes: string | null;
  resolved_at: string | null;
  resolved_by: number | null;
  resolved_by_label: string | null;
  linked_feedback: LinkedFeedbackSummary | null;
}

export interface ImprovementTaskListResponse {
  items: ImprovementTaskItem[];
}

export type ImprovementRecommendedAction =
  | "update_kb_content"
  | "improve_prompt"
  | "improve_retrieval"
  | "mark_as_unclear";

export interface ImprovementTaskAnalyzeResponse {
  task_id: number;
  recommended_action: ImprovementRecommendedAction;
  reasoning_summary: string;
  suggested_kb_update: string;
  suggested_test_questions: string[];
  retrieval_test: Record<string, unknown> | null;
}

export const improvementsApi = {
  async createTask(payload: {
    feedback_id?: number | null;
    knowledge_base_id?: number | null;
    title?: string | null;
    description?: string | null;
    status?: ImprovementTaskStatus;
    priority?: ImprovementTaskPriority;
    assigned_to?: number | null;
  }): Promise<ImprovementTaskItem> {
    const body: Record<string, unknown> = {};
    if (payload.feedback_id != null) body.feedback_id = payload.feedback_id;
    if (payload.knowledge_base_id != null) body.knowledge_base_id = payload.knowledge_base_id;
    if (payload.title != null && payload.title !== "") body.title = payload.title;
    if (payload.description != null && payload.description !== "") body.description = payload.description;
    if (payload.status) body.status = payload.status;
    if (payload.priority) body.priority = payload.priority;
    if (payload.assigned_to != null) body.assigned_to = payload.assigned_to;

    const { data } = await apiClient.post<ImprovementTaskItem>("/improvements/tasks", body);
    return data;
  },

  async listTasks(params: { status?: ImprovementTaskStatus; priority?: ImprovementTaskPriority }): Promise<ImprovementTaskListResponse> {
    const { data } = await apiClient.get<ImprovementTaskListResponse>("/improvements/tasks", { params });
    return data;
  },

  async patchTask(
    taskId: number,
    patch: Partial<{
      title: string;
      description: string;
      status: ImprovementTaskStatus;
      priority: ImprovementTaskPriority;
      assigned_to: number | null;
      resolution_notes: string | null;
    }>,
  ): Promise<ImprovementTaskItem> {
    const { data } = await apiClient.patch<ImprovementTaskItem>(`/improvements/tasks/${taskId}`, patch);
    return data;
  },

  async analyzeTask(taskId: number, includeRetrievalTest: boolean): Promise<ImprovementTaskAnalyzeResponse> {
    const { data } = await apiClient.post<ImprovementTaskAnalyzeResponse>(`/improvements/tasks/${taskId}/analyze`, {
      include_retrieval_test: includeRetrievalTest,
    });
    return data;
  },
};
