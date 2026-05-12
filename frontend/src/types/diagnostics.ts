export interface RetrievalTestChunk {
  rank: number;
  document_id: number | null;
  document_name: string;
  chunk_id: string | null;
  chunk_type: string | null;
  document_type: string | null;
  product_name: string | null;
  section_title: string | null;
  score: number;
  content_preview: string;
}

export interface RetrievalTestResponse {
  knowledge_base_id: number;
  question: string;
  retrieval_mode: string;
  retrieved_chunk_count: number;
  dominant_document_type: string;
  dominant_product_name: string | null;
  section_coverage_count: number;
  chunks: RetrievalTestChunk[];
  diagnostics: Record<string, unknown>;
}
