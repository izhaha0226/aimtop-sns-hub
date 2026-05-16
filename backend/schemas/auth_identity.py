import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuthIdentityCreateRequest(BaseModel):
    client_id: uuid.UUID | None = None
    provider: str = Field(min_length=1, max_length=50)
    provider_user_id: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=1000)
    badge_label: str = Field(default="인증됨", max_length=100)
    is_verified: bool = True
    metadata_json: dict | None = None


class AuthIdentityUpdateRequest(BaseModel):
    client_id: uuid.UUID | None = None
    display_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=1000)
    badge_label: str | None = Field(default=None, max_length=100)
    is_verified: bool | None = None
    metadata_json: dict | None = None


class AuthIdentityResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    provider: str
    provider_user_id: str | None = None
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    badge_label: str
    is_verified: bool
    last_seen_at: datetime | None = None
    metadata_json: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
