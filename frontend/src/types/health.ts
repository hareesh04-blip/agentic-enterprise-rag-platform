export interface RuntimeMetadata {
  build_version: string;
  process_start_time: string;
  process_pid: number;
  backend_uptime_seconds: number;
  llm_provider: string;
  embedding_provider: string;
  active_vector_collection: string | null;
  app_env: string;
  app_name: string;
  stale_process_hint?: string;
}

export interface PlatformStatusResponse {
  overall_status: "healthy" | "degraded" | "unhealthy" | string;
  backend: {
    status: string;
    app_name: string;
    environment: string;
  };
  database: {
    status: string;
    message: string | null;
  };
  qdrant: {
    status: string;
    url: string;
    collection_name: string | null;
    collection_exists: boolean;
    point_count: number;
    embedding_dimension_configured: number | null;
    embedding_dimension_matches: boolean | null;
    message: string | null;
  };
  providers: {
    llm_provider: string;
    embedding_provider: string;
    llm_model: string;
    embedding_model: string;
    vector_collection: string | null;
  };
  feature_flags: {
    ENABLE_HYBRID_RETRIEVAL: boolean;
    ENABLE_METADATA_RERANKING: boolean;
    ENABLE_SUGGESTED_QUESTIONS: boolean;
    ENABLE_CONFIDENCE_SCORING: boolean;
    ENABLE_IMPACT_ANALYSIS: boolean;
  };
  issues: string[];
  runtime?: RuntimeMetadata;
}
