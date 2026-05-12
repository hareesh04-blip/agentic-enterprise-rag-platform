import { apiClient } from "./client";

export const documentGovernanceApi = {
  deactivate(documentId: number) {
    return apiClient.post<{ document_id: number; is_active_document: boolean }>(
      `/ingestion/documents/${documentId}/deactivate`,
    );
  },
  reactivate(documentId: number) {
    return apiClient.post<{ document_id: number; is_active_document: boolean }>(
      `/ingestion/documents/${documentId}/reactivate`,
    );
  },
  reindex(documentId: number) {
    return apiClient.post<{
      document_id: number;
      chunks_reindexed: number;
      vectors_upserted: number;
      embedding_provider: string;
      vector_collection_name: string;
    }>(`/ingestion/documents/${documentId}/reindex`);
  },
  removeVectors(documentId: number) {
    return apiClient.delete<{ document_id: number; vectors_removed: number }>(
      `/ingestion/documents/${documentId}/vectors`,
    );
  },
};
