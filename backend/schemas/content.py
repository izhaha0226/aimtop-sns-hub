import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ContentCreate(BaseModel):
    client_id: uuid.UUID
    post_type: str = "text"
    title: str | None = None
    text: str | None = None
    media_urls: list[str] | None = None
    hashtags: list[str] | None = None
    operation_plan_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    target_platform: str | None = None
    variant_role: str | None = None
    source_metadata: dict[str, Any] | None = None


class ContentUpdate(BaseModel):
    post_type: str | None = None
    title: str | None = None
    text: str | None = None
    media_urls: list[str] | None = None
    hashtags: list[str] | None = None
    topic_id: uuid.UUID | None = None
    target_platform: str | None = None
    variant_role: str | None = None


class ContentResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    author_id: uuid.UUID | None
    post_type: str
    title: str | None
    text: str | None
    media_urls: list[Any] | None
    hashtags: list[Any] | None
    status: str
    channel_connection_id: uuid.UUID | None = None
    operation_plan_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    target_platform: str | None = None
    variant_role: str | None = None
    source_metadata: dict[str, Any] | None = None
    platform_post_id: str | None = None
    published_url: str | None = None
    publish_error: str | None = None
    scheduled_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentListResponse(BaseModel):
    items: list[ContentResponse]
    total: int
