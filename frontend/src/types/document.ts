export type DocumentType = "api" | "product" | "hr";

export interface DocumentItem {
  id: number;
  file_name?: string | null;
  name?: string | null;
  document_type?: DocumentType | string | null;
  product_name?: string | null;
  source_domain?: string | null;
  document_version?: string | null;
  knowledge_base_id: number;
  knowledge_base_name?: string | null;
  created_at?: string | null;
  /** ISO upload time (document.uploaded_at) */
  upload_timestamp?: string | null;
  uploaded_by?: number | null;
  ingestion_run_id?: number | null;
  embedding_provider?: string | null;
  vector_collection_name?: string | null;
  ingestion_status?: string | null;
  is_active_document?: boolean | null;
  superseded_by_document_id?: number | null;
  chunk_count?: number | null;
  vector_chunk_count?: number | null;
  embedding_status?: string | null;
  vector_store_status?: string | null;
}

export interface ListDocumentsFilters {
  document_type?: DocumentType;
  product_name?: string;
  knowledge_base_id: number;
  active_only?: boolean;
  failed_ingestion_only?: boolean;
}

export interface ListDocumentsResponse {
  filters: {
    document_type?: DocumentType | null;
    product_name?: string | null;
    knowledge_base_id?: number | null;
  };
  documents: DocumentItem[];
}

export interface UploadDocumentResponse {
  ingestion_job_id?: number;
  ingestion_run_id?: number | null;
  project_id?: number;
  document_id?: number;
  document_type?: DocumentType | string;
  source_domain?: string | null;
  product_name?: string | null;
  version?: string | null;
  api_count?: number;
  chunk_count?: number;
  qdrant_points_created?: number;
  embedding_status?: string;
  embedding_error?: string | null;
  vector_store_status?: string;
  vector_collection_name?: string;
  vector_embedding_dimension?: number | null;
  vector_sample_verified?: boolean | null;
}
