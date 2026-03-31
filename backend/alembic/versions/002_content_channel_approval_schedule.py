"""Content, channel, approval, schedule tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _create_contents_table()
    _create_content_versions_table()
    _create_channel_connections_table()
    _create_approvals_table()
    _create_schedules_table()


def _create_contents_table() -> None:
    op.create_table(
        "contents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("post_type", sa.String(50), nullable=False, server_default="text"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("media_urls", JSON, nullable=True),
        sa.Column("hashtags", JSON, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contents_client_id", "contents", ["client_id"])
    op.create_index("ix_contents_author_id", "contents", ["author_id"])
    op.create_index("ix_contents_status", "contents", ["status"])


def _create_content_versions_table() -> None:
    op.create_table(
        "content_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("snapshot", JSON, nullable=True),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_content_versions_content_id", "content_versions", ["content_id"])


def _create_channel_connections_table() -> None:
    op.create_table(
        "channel_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("account_name", sa.String(200), nullable=True),
        sa.Column("account_id", sa.String(200), nullable=True),
        sa.Column("access_token", sa.String(2000), nullable=True),
        sa.Column("refresh_token", sa.String(2000), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_connected", sa.Boolean, server_default="true", nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_channel_connections_client_id", "channel_connections", ["client_id"])


def _create_approvals_table() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approver_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_approvals_content_id", "approvals", ["content_id"])


def _create_schedules_table() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_connection_id", UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("platform_post_id", sa.String(200), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_schedules_content_id", "schedules", ["content_id"])
    op.create_index("ix_schedules_status", "schedules", ["status"])


def downgrade() -> None:
    op.drop_table("schedules")
    op.drop_table("approvals")
    op.drop_table("channel_connections")
    op.drop_table("content_versions")
    op.drop_table("contents")
