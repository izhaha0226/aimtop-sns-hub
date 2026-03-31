import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ChannelConnectionCreate(BaseModel):
    channel_type: str
    account_name: str | None = None
    account_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    extra_data: dict[str, Any] | None = None


class ChannelConnectionResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    channel_type: str
    account_name: str | None
    account_id: str | None
    is_connected: bool
    connected_at: datetime | None
    token_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
