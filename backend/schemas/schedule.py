import uuid
from datetime import datetime
from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    channel_connection_id: uuid.UUID
    scheduled_at: datetime


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    channel_connection_id: uuid.UUID
    scheduled_at: datetime
    status: str
    platform_post_id: str | None
    published_at: datetime | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
