from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ApiAuthProfile(Base):
    __tablename__ = "api_auth_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("api_documents.id"), nullable=False, index=True)
    auth_type: Mapped[str] = mapped_column(String(100), nullable=False)
    token_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    grant_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    header_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped["ApiDocument"] = relationship(back_populates="auth_profiles")
