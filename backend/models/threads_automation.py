import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ThreadsPersona(Base):
    __tablename__ = "threads_personas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_keywords_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    prohibited_topics_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    author_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    author_transparency: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_identities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider_badge_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ThreadsTargetRule(Base):
    __tablename__ = "threads_target_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    keywords_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    competitor_handles_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    hashtags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    min_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.55)
    daily_like_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    daily_comment_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    auto_like_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_comment_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ThreadsSafetyFilter(Base):
    __tablename__ = "threads_safety_filters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    blocked_terms_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sensitive_topics_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    min_safety_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ThreadsDraft(Base):
    __tablename__ = "threads_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads_personas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads_target_rules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False, default="comment")
    target_post_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    target_author_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_post_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    safety_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    safety_labels_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="approval_required")
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    provider_badge_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author_transparency: Mapped[str | None] = mapped_column(String(500), nullable=True)
    simulation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="approval_required")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ThreadsApprovalQueue(Base):
    __tablename__ = "threads_approval_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    queue_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ThreadsActionLog(Base):
    __tablename__ = "threads_action_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads_drafts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads_approval_queue.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="simulated")
    simulation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="simulated")
    external_write_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ThreadsLearningEvent(Base):
    __tablename__ = "threads_learning_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads_action_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
