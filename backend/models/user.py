import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Enum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    approver = "approver"
    editor = "editor"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    telegram_id: Mapped[str | None] = mapped_column(String(100))
    profile_image: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(
        Enum("admin", "approver", "editor", "viewer", name="user_role"),
        default="editor",
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="user_status"),
        default="active",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
