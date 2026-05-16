"""add threads automation tables

Revision ID: 009
Revises: 008
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=1000), nullable=True),
        sa.Column("badge_label", sa.String(length=100), nullable=False, server_default="인증됨"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_auth_identities_provider_user"),
    )
    op.create_index("ix_auth_identities_client_id", "auth_identities", ["client_id"])
    op.create_index("ix_auth_identities_provider", "auth_identities", ["provider"])
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])

    op.create_table(
        "threads_personas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tone_keywords_json", JSON, nullable=True),
        sa.Column("prohibited_topics_json", JSON, nullable=True),
        sa.Column("author_display_name", sa.String(length=120), nullable=True),
        sa.Column("author_transparency", sa.String(length=500), nullable=True),
        sa.Column("auth_identity_id", UUID(as_uuid=True), sa.ForeignKey("auth_identities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_badge_label", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_personas_auth_identity_id", "threads_personas", ["auth_identity_id"])
    op.create_index("ix_threads_personas_client_id", "threads_personas", ["client_id"])

    op.create_table(
        "threads_target_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("keywords_json", JSON, nullable=True),
        sa.Column("competitor_handles_json", JSON, nullable=True),
        sa.Column("hashtags_json", JSON, nullable=True),
        sa.Column("min_fit_score", sa.Float(), nullable=False, server_default="0.55"),
        sa.Column("daily_like_limit", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("daily_comment_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("auto_like_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requires_comment_approval", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_target_rules_client_id", "threads_target_rules", ["client_id"])

    op.create_table(
        "threads_safety_filters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("blocked_terms_json", JSON, nullable=True),
        sa.Column("sensitive_topics_json", JSON, nullable=True),
        sa.Column("min_safety_score", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_safety_filters_client_id", "threads_safety_filters", ["client_id"])

    op.create_table(
        "threads_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_id", UUID(as_uuid=True), sa.ForeignKey("threads_personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_rule_id", UUID(as_uuid=True), sa.ForeignKey("threads_target_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=30), nullable=False, server_default="comment"),
        sa.Column("target_post_url", sa.String(length=2000), nullable=True),
        sa.Column("target_author_handle", sa.String(length=255), nullable=True),
        sa.Column("target_post_text", sa.Text(), nullable=True),
        sa.Column("draft_text", sa.Text(), nullable=True),
        sa.Column("fit_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("safety_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("safety_labels_json", JSON, nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="approval_required"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provider_badge_label", sa.String(length=100), nullable=True),
        sa.Column("author_transparency", sa.String(length=500), nullable=True),
        sa.Column("simulation_status", sa.String(length=50), nullable=False, server_default="approval_required"),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_drafts_client_id", "threads_drafts", ["client_id"])
    op.create_index("ix_threads_drafts_persona_id", "threads_drafts", ["persona_id"])
    op.create_index("ix_threads_drafts_target_rule_id", "threads_drafts", ["target_rule_id"])

    op.create_table(
        "threads_approval_queue",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("threads_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("queue_reason", sa.String(length=500), nullable=True),
        sa.Column("requested_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_approval_queue_client_id", "threads_approval_queue", ["client_id"])
    op.create_index("ix_threads_approval_queue_draft_id", "threads_approval_queue", ["draft_id"])

    op.create_table(
        "threads_action_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("threads_drafts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("threads_approval_queue.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="simulated"),
        sa.Column("simulation_status", sa.String(length=50), nullable=False, server_default="simulated"),
        sa.Column("external_write_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_action_logs_approval_id", "threads_action_logs", ["approval_id"])
    op.create_index("ix_threads_action_logs_client_id", "threads_action_logs", ["client_id"])
    op.create_index("ix_threads_action_logs_draft_id", "threads_action_logs", ["draft_id"])

    op.create_table(
        "threads_learning_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_log_id", UUID(as_uuid=True), sa.ForeignKey("threads_action_logs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("signal_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("outcome", sa.String(length=100), nullable=True),
        sa.Column("metrics_json", JSON, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_learning_events_action_log_id", "threads_learning_events", ["action_log_id"])
    op.create_index("ix_threads_learning_events_client_id", "threads_learning_events", ["client_id"])


def downgrade() -> None:
    op.drop_table("threads_learning_events")
    op.drop_table("threads_action_logs")
    op.drop_table("threads_approval_queue")
    op.drop_table("threads_drafts")
    op.drop_table("threads_safety_filters")
    op.drop_table("threads_target_rules")
    op.drop_table("threads_personas")
    op.drop_table("auth_identities")
