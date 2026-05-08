from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ApiDocument(Base):
    __tablename__ = "api_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("api_projects.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_bases.id"), nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="api")
    source_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped["ApiProject"] = relationship(back_populates="documents")
    knowledge_base: Mapped["KnowledgeBase | None"] = relationship(back_populates="documents")
    auth_profiles: Mapped[list["ApiAuthProfile"]] = relationship(back_populates="document")
    endpoints: Mapped[list["ApiEndpoint"]] = relationship(back_populates="document")
    error_codes: Mapped[list["ApiErrorCode"]] = relationship(back_populates="document")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="document")
