from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Agentic Enterprise API RAG Platform"
    ENVIRONMENT: str = "local"
    # Operational build label (set per deploy / CI; bump when validating stale-process confusion).
    BUILD_VERSION: str = "52.0.0-local"

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise_rag"

    JWT_SECRET_KEY: str = "change-me-local-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    LLM_PROVIDER: str = "ollama"
    EMBEDDING_PROVIDER: str = "ollama"

    OPENAI_API_KEY: str | None = None
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    OLLAMA_BASE_URL: str = "http://172.16.111.209:8080"
    OLLAMA_LLM_MODEL: str = "llama3:8b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    OLLAMA_TIMEOUT_CONNECT_SECONDS: float = 5.0
    OLLAMA_TIMEOUT_READ_SECONDS: float = 120.0
    OLLAMA_TIMEOUT_WRITE_SECONDS: float = 30.0
    OLLAMA_TIMEOUT_POOL_SECONDS: float = 5.0
    OLLAMA_RETRY_COUNT: int = 2
    OLLAMA_RETRY_DELAY_SECONDS: float = 1.0

    EMBEDDING_DIM: int = 768
    # Prepared embedding inputs only (OpenAI ~8k tokens — conservative char ceiling).
    EMBEDDING_INPUT_MAX_CHARS: int = 24000
    EMBEDDING_SPLIT_OVERLAP_CHARS: int = 512

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "enterprise_api_docs"
    QDRANT_COLLECTION_OPENAI: str = "enterprise_api_docs_openai"

    ENABLE_HYBRID_RETRIEVAL: bool = True
    ENABLE_METADATA_RERANKING: bool = True
    HYBRID_VECTOR_TOP_K: int = 12
    HYBRID_KEYWORD_TOP_K: int = 12
    FINAL_CONTEXT_TOP_K: int = 6
    ENABLE_SUGGESTED_QUESTIONS: bool = True
    SUGGESTED_QUESTION_COUNT: int = 4
    ENABLE_CONFIDENCE_SCORING: bool = True
    CONFIDENCE_HIGH_THRESHOLD: float = 0.75
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.45
    ENABLE_IMPACT_ANALYSIS: bool = True

    ENABLE_CONVERSATION_SUMMARY: bool = True
    SUMMARY_TRIGGER_MESSAGE_COUNT: int = 8
    SUMMARY_MAX_MESSAGES: int = 20

    ENABLE_AGENT_ORCHESTRATION: bool = False

    ENABLE_IMPROVEMENT_LLM_ANALYSIS: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
