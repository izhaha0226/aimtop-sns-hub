"""전 채널 자동화 정책 / 실행 / 액션 로그 모델"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ChannelAutomationPolicy(Base):
    __tablename__ = "channel_automation_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=3)
    auto_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_json: Mapped[dict | None] = mapped_column(JSON)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # material|publish|comment_sync
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running", index=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AutomationActionLog(Base):
    __tablename__ = "automation_action_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automation_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str | None] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(200))
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_json: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
