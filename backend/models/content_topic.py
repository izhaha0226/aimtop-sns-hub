import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ContentTopic(Base):
    __tablename__ = "content_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    brief: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str | None] = mapped_column(String(100))
    target_audience: Mapped[str | None] = mapped_column(Text)
    core_message: Mapped[str | None] = mapped_column(Text)
    card_storyline: Mapped[list | None] = mapped_column(JSON)
    reference_assets: Mapped[list | None] = mapped_column(JSON)
    visual_options: Mapped[list | None] = mapped_column(JSON)
    selected_visual_option: Mapped[str | None] = mapped_column(String(50))
    shared_visual_prompt: Mapped[str | None] = mapped_column(Text)
    shared_media_urls: Mapped[list | None] = mapped_column(JSON)
    benchmark_context: Mapped[dict | None] = mapped_column(JSON)
    source_metadata: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
