from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ApiParameter(Base):
    __tablename__ = "api_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("api_endpoints.id"), nullable=False, index=True)
    parameter_location: Mapped[str] = mapped_column(String(50), nullable=False)
    param_name: Mapped[str] = mapped_column(String(255), nullable=False)
    param_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    mandatory_optional: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    endpoint: Mapped["ApiEndpoint"] = relationship(back_populates="parameters")
