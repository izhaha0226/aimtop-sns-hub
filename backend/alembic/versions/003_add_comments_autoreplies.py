"""Comments and auto-replies tables

Revision ID: 003
Revises: 002
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _create_comments_table()
    _create_auto_replies_table()


def _create_comments_table() -> None:
    op.create_table(
        "comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_connection_id", UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform_comment_id", sa.String(200), nullable=True),
        sa.Column("author_name", sa.String(200), nullable=True),
        sa.Column("author_avatar_url", sa.String(500), nullable=True),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("is_hidden", sa.Boolean, server_default="false", nullable=False),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_comments_content_id", "comments", ["content_id"])
    op.create_index("ix_comments_channel_connection_id", "comments", ["channel_connection_id"])


def _create_auto_replies_table() -> None:
    op.create_table(
        "auto_replies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="all"),
        sa.Column("trigger_type", sa.String(50), nullable=False, server_default="all"),
        sa.Column("trigger_value", sa.Text, nullable=True),
        sa.Column("reply_template", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auto_replies_client_id", "auto_replies", ["client_id"])


def downgrade() -> None:
    op.drop_table("auto_replies")
    op.drop_table("comments")
