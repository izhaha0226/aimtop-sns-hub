import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class ClientOnboarding(Base):
    __tablename__ = "client_onboardings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), unique=True
    )
    # Step 1: 계정 유형
    account_type: Mapped[str | None] = mapped_column(String(50))
    # Step 2: 톤앤매너
    tones: Mapped[list | None] = mapped_column(JSON)
    forbidden_words: Mapped[list | None] = mapped_column(JSON)
    emoji_policy: Mapped[str] = mapped_column(String(20), default="minimal")
    hashtag_policy: Mapped[str] = mapped_column(String(20), default="medium")
    extra_notes: Mapped[str | None] = mapped_column(Text)
    # Step 3: 채널 선택
    selected_channels: Mapped[list | None] = mapped_column(JSON)
    # Step 4: 벤치마킹
    benchmark_channels: Mapped[list | None] = mapped_column(JSON)
    # Step 5: 운영 전략서
    strategy_content: Mapped[str | None] = mapped_column(Text)
    # 완료 여부
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
