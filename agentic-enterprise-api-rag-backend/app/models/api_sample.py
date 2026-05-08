from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ApiSample(Base):
    __tablename__ = "api_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("api_endpoints.id"), nullable=False, index=True)
    sample_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sample_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    endpoint: Mapped["ApiEndpoint"] = relationship(back_populates="samples")
