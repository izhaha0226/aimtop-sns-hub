import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class BenchmarkPost(Base):
    __tablename__ = "benchmark_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmark_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_post_id: Mapped[str | None] = mapped_column(String(255), index=True)
    post_url: Mapped[str | None] = mapped_column(String(2000))
    content_text: Mapped[str | None] = mapped_column(Text)
    hook_text: Mapped[str | None] = mapped_column(Text)
    cta_text: Mapped[str | None] = mapped_column(Text)
    hashtags_json: Mapped[list | None] = mapped_column(JSON)
    format_type: Mapped[str | None] = mapped_column(String(50), index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    benchmark_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
