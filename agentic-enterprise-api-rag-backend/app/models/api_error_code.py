from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ApiErrorCode(Base):
    __tablename__ = "api_error_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("api_documents.id"), nullable=True, index=True)
    endpoint_id: Mapped[int | None] = mapped_column(ForeignKey("api_endpoints.id"), nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped["ApiDocument | None"] = relationship(back_populates="error_codes")
    endpoint: Mapped["ApiEndpoint | None"] = relationship(back_populates="error_codes")
