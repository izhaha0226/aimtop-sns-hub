"""Add llm routing and benchmark intelligence tables

Revision ID: 006
Revises: 005
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_provider_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("supports_json", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("supports_reasoning", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_llm_provider_configs_provider_name", "llm_provider_configs", ["provider_name"])

    op.create_table(
        "llm_task_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("routing_mode", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("primary_provider", sa.String(length=50), nullable=False, server_default="claude"),
        sa.Column("primary_model", sa.String(length=120), nullable=False, server_default="claude-sonnet-4-6"),
        sa.Column("fallback_provider", sa.String(length=50), nullable=True),
        sa.Column("fallback_model", sa.String(length=120), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("benchmark_window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("views_weight", sa.Float(), nullable=False, server_default="0.45"),
        sa.Column("engagement_weight", sa.Float(), nullable=False, server_default="0.30"),
        sa.Column("recency_weight", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("action_language_weight", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("strict_json_mode", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fallback_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("task_type", name="uq_llm_task_policies_task_type"),
    )
    op.create_index("ix_llm_task_policies_task_type", "llm_task_policies", ["task_type"])

    op.create_table(
        "benchmark_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("purpose", sa.String(length=50), nullable=False, server_default="all"),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("auto_discovered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_benchmark_accounts_client_id", "benchmark_accounts", ["client_id"])
    op.create_index("ix_benchmark_accounts_platform", "benchmark_accounts", ["platform"])

    op.create_table(
        "benchmark_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("benchmark_account_id", UUID(as_uuid=True), sa.ForeignKey("benchmark_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
        sa.Column("post_url", sa.String(length=2000), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("hook_text", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.Text(), nullable=True),
        sa.Column("hashtags_json", JSON, nullable=True),
        sa.Column("format_type", sa.String(length=50), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("save_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("benchmark_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("raw_payload", JSON, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_benchmark_posts_benchmark_account_id", "benchmark_posts", ["benchmark_account_id"])
    op.create_index("ix_benchmark_posts_client_platform_score", "benchmark_posts", ["client_id", "platform", "benchmark_score"])
    op.create_index("ix_benchmark_posts_external_post_id", "benchmark_posts", ["external_post_id"])
    op.create_index("ix_benchmark_posts_format_type", "benchmark_posts", ["format_type"])
    op.create_index("ix_benchmark_posts_published_at", "benchmark_posts", ["published_at"])

    op.create_table(
        "action_language_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("source_scope", sa.String(length=50), nullable=False, server_default="manual_benchmark"),
        sa.Column("top_hooks_json", JSON, nullable=True),
        sa.Column("top_ctas_json", JSON, nullable=True),
        sa.Column("tone_patterns_json", JSON, nullable=True),
        sa.Column("format_patterns_json", JSON, nullable=True),
        sa.Column("recommended_prompt_rules", sa.Text(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_action_language_profiles_client_id", "action_language_profiles", ["client_id"])
    op.create_index("ix_action_language_profiles_platform", "action_language_profiles", ["platform"])


def downgrade() -> None:
    op.drop_table("action_language_profiles")
    op.drop_table("benchmark_posts")
    op.drop_table("benchmark_accounts")
    op.drop_table("llm_task_policies")
    op.drop_table("llm_provider_configs")
