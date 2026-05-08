from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("api_documents.id"), nullable=False, index=True)
    endpoint_id: Mapped[int | None] = mapped_column(ForeignKey("api_endpoints.id"), nullable=True, index=True)
    chunk_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped["ApiDocument"] = relationship(back_populates="chunks")
    endpoint: Mapped["ApiEndpoint | None"] = relationship(back_populates="chunks")
