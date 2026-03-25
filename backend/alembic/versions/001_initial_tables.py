"""Initial tables

Revision ID: 001
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _create_user_role_enum()
    _create_user_status_enum()
    _create_users_table()
    _create_clients_table()
    _create_client_users_table()
    _create_user_activity_logs_table()
    _create_user_permission_logs_table()


def _create_user_role_enum() -> None:
    op.execute(
        "CREATE TYPE user_role AS ENUM "
        "('super_admin', 'admin', 'manager', 'viewer')"
    )


def _create_user_status_enum() -> None:
    op.execute(
        "CREATE TYPE user_status AS ENUM "
        "('active', 'inactive', 'invited')"
    )


def _create_users_table() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("telegram_id", sa.String(100), nullable=True),
        sa.Column("profile_image", sa.String(500), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "super_admin", "admin", "manager", "viewer",
                name="user_role",
                create_type=False,
            ),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active", "inactive", "invited",
                name="user_status",
                create_type=False,
            ),
            nullable=False,
            server_default="invited",
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def _create_clients_table() -> None:
    op.create_table(
        "clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("logo", sa.String(500), nullable=True),
        sa.Column("brand_color", sa.String(7), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean,
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def _create_client_users_table() -> None:
    op.create_table(
        "client_users",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def _create_user_activity_logs_table() -> None:
    op.create_table(
        "user_activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=True),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("meta", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def _create_user_permission_logs_table() -> None:
    op.create_table(
        "user_permission_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "target_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "changed_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "prev_role",
            sa.Enum(
                "super_admin", "admin", "manager", "viewer",
                name="user_role",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "new_role",
            sa.Enum(
                "super_admin", "admin", "manager", "viewer",
                name="user_role",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_permission_logs")
    op.drop_table("user_activity_logs")
    op.drop_table("client_users")
    op.drop_table("clients")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS user_role")
