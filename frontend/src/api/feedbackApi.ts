import { apiClient } from "./client";

export type QueryFeedbackRating = "thumbs_up" | "thumbs_down";

export interface QueryFeedbackCreatePayload {
  knowledge_base_id: number;
  question_text: string;
  answer_text: string;
  rating: QueryFeedbackRating;
  comment?: string | null;
  session_id?: number | null;
  message_id?: number | null;
}

export interface QueryFeedbackItem {
  id: number;
  user_id: number;
  session_id: number | null;
  message_id: number | null;
  knowledge_base_id: number;
  knowledge_base_name: string | null;
  question_text: string;
  answer_text: string;
  answer_preview: string;
  rating: QueryFeedbackRating;
  comment: string | null;
  created_at: string | null;
  submitted_by: string;
  submitter_email: string;
}

export interface QueryFeedbackListResponse {
  items: QueryFeedbackItem[];
}

export interface FeedbackKbBreakdown {
  knowledge_base_id: number;
  knowledge_base_name: string;
  total: number;
  thumbs_up: number;
  thumbs_down: number;
  thumbs_up_rate: number;
}

export interface RecentNegativeFeedbackItem {
  id: number;
  knowledge_base_id: number;
  knowledge_base_name: string;
  question_text: string;
  answer_preview: string;
  comment: string | null;
  created_at: string | null;
}

export interface FeedbackAnalyticsResponse {
  total_feedback: number;
  thumbs_up_count: number;
  thumbs_down_count: number;
  thumbs_up_rate: number;
  by_knowledge_base: FeedbackKbBreakdown[];
  recent_negative_feedback: RecentNegativeFeedbackItem[];
}

export const feedbackApi = {
  async submitQueryFeedback(payload: QueryFeedbackCreatePayload): Promise<{ id: number; created_at: string | null }> {
    const body: Record<string, unknown> = {
      knowledge_base_id: payload.knowledge_base_id,
      question_text: payload.question_text,
      answer_text: payload.answer_text,
      rating: payload.rating,
    };
    if (payload.comment != null && payload.comment.trim()) body.comment = payload.comment.trim();
    if (payload.session_id != null) body.session_id = payload.session_id;
    if (payload.message_id != null) body.message_id = payload.message_id;

    const { data } = await apiClient.post<{ id: number; created_at: string | null }>("/feedback/query", body);
    return data;
  },

  async listQueryFeedback(params: {
    knowledge_base_id?: number;
    rating?: QueryFeedbackRating;
    from_date?: string;
    to_date?: string;
  }): Promise<QueryFeedbackListResponse> {
    const { data } = await apiClient.get<QueryFeedbackListResponse>("/feedback/query", { params });
    return data;
  },

  async getFeedbackAnalytics(params: {
    knowledge_base_id?: number;
    from_date?: string;
    to_date?: string;
  }): Promise<FeedbackAnalyticsResponse> {
    const { data } = await apiClient.get<FeedbackAnalyticsResponse>("/feedback/analytics", { params });
    return data;
  },
};
