import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "editor"
    phone: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    telegram_id: str | None = None


class UserRoleUpdate(BaseModel):
    role: str
    reason: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    phone: str | None
    telegram_id: str | None
    profile_image: str | None
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
