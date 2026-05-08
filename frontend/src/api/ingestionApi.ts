import { apiClient } from "./client";
import type { ListDocumentsFilters, ListDocumentsResponse, UploadDocumentResponse } from "../types/document";

export const ingestionApi = {
  async listDocuments(filters: ListDocumentsFilters): Promise<ListDocumentsResponse> {
    const params = {
      knowledge_base_id: filters.knowledge_base_id,
      document_type: filters.document_type || undefined,
      product_name: filters.product_name?.trim() || undefined,
    };
    const { data } = await apiClient.get<ListDocumentsResponse>("/ingestion/documents", { params });
    return data;
  },

  async uploadDocument(formData: FormData): Promise<UploadDocumentResponse> {
    const { data } = await apiClient.post<UploadDocumentResponse>("/ingestion/ingest-docx", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};
