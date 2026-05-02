"""Add operation plans table

Revision ID: 007
Revises: 006
Create Date: 2026-05-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operation_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approver_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("brand_name", sa.String(length=200), nullable=False),
        sa.Column("month", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("strategy_summary", sa.Text(), nullable=True),
        sa.Column("request_payload", JSON, nullable=True),
        sa.Column("plan_payload", JSON, nullable=True),
        sa.Column("approval_memo", sa.Text(), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_operation_plans_client_id", "operation_plans", ["client_id"])
    op.create_index("ix_operation_plans_author_id", "operation_plans", ["author_id"])
    op.create_index("ix_operation_plans_brand_name", "operation_plans", ["brand_name"])
    op.create_index("ix_operation_plans_month", "operation_plans", ["month"])
    op.create_index("ix_operation_plans_status", "operation_plans", ["status"])


def downgrade() -> None:
    op.drop_table("operation_plans")
