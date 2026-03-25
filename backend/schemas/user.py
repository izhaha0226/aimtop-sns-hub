import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    telegram_id: str | None = None
    profile_image: str | None = None
    role: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str | None = None
    telegram_id: str | None = None
    profile_image: str | None = None
    role: str
    status: str
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
