import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ActionLanguageProfile(Base):
    __tablename__ = "action_language_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_scope: Mapped[str] = mapped_column(String(50), default="manual_benchmark")
    top_hooks_json: Mapped[list | None] = mapped_column(JSON)
    top_ctas_json: Mapped[list | None] = mapped_column(JSON)
    tone_patterns_json: Mapped[dict | None] = mapped_column(JSON)
    format_patterns_json: Mapped[dict | None] = mapped_column(JSON)
    recommended_prompt_rules: Mapped[str | None] = mapped_column(Text)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
