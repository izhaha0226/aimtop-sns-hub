import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class LLMTaskPolicy(Base):
    __tablename__ = "llm_task_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    routing_mode: Mapped[str] = mapped_column(String(30), default="manual")
    primary_provider: Mapped[str] = mapped_column(String(50), default="gpt")
    primary_model: Mapped[str] = mapped_column(String(120), default="gpt-5.4")
    fallback_provider: Mapped[str | None] = mapped_column(String(50))
    fallback_model: Mapped[str | None] = mapped_column(String(120))
    top_k: Mapped[int] = mapped_column(Integer, default=10)
    benchmark_window_days: Mapped[int] = mapped_column(Integer, default=30)
    views_weight: Mapped[float] = mapped_column(Float, default=0.45)
    engagement_weight: Mapped[float] = mapped_column(Float, default=0.30)
    recency_weight: Mapped[float] = mapped_column(Float, default=0.15)
    action_language_weight: Mapped[float] = mapped_column(Float, default=0.10)
    strict_json_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
