"""add operation plan content draft metadata

Revision ID: 008
Revises: 007
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contents", sa.Column("operation_plan_id", UUID(as_uuid=True), sa.ForeignKey("operation_plans.id", ondelete="SET NULL"), nullable=True))
    op.add_column("contents", sa.Column("source_metadata", JSON(), nullable=True))
    op.create_index("ix_contents_operation_plan_id", "contents", ["operation_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_contents_operation_plan_id", table_name="contents")
    op.drop_column("contents", "source_metadata")
    op.drop_column("contents", "operation_plan_id")
