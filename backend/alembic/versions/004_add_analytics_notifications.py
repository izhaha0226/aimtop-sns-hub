"""Analytics and notifications tables

Revision ID: 004
Revises: 003
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _create_analytics_table()
    _create_notifications_table()


def _create_analytics_table() -> None:
    op.create_table(
        "analytics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_connection_id", UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("followers", sa.Integer, server_default="0", nullable=False),
        sa.Column("following", sa.Integer, server_default="0", nullable=False),
        sa.Column("posts_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("impressions", sa.Integer, server_default="0", nullable=False),
        sa.Column("reach", sa.Integer, server_default="0", nullable=False),
        sa.Column("engagement", sa.Integer, server_default="0", nullable=False),
        sa.Column("clicks", sa.Integer, server_default="0", nullable=False),
        sa.Column("saves", sa.Integer, server_default="0", nullable=False),
        sa.Column("shares", sa.Integer, server_default="0", nullable=False),
        sa.Column("platform_data", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analytics_channel_connection_id", "analytics", ["channel_connection_id"])


def _create_notifications_table() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, server_default="false", nullable=False),
        sa.Column("link_url", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_client_id", "notifications", ["client_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("analytics")
