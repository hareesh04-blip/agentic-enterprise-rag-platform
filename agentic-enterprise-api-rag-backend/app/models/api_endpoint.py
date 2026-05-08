from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("api_documents.id"), nullable=False, index=True)
    api_reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    service_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_timeout: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_gateway: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authentication_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    swagger_urls_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    service_urls_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    environment_urls_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped["ApiDocument"] = relationship(back_populates="endpoints")
    parameters: Mapped[list["ApiParameter"]] = relationship(back_populates="endpoint")
    samples: Mapped[list["ApiSample"]] = relationship(back_populates="endpoint")
    error_codes: Mapped[list["ApiErrorCode"]] = relationship(back_populates="endpoint")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="endpoint")
