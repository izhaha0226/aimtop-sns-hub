import uuid
from datetime import datetime
from pydantic import BaseModel


class CommentBase(BaseModel):
    content_id: uuid.UUID
    channel_connection_id: uuid.UUID | None = None
    platform_comment_id: str | None = None
    author_name: str | None = None
    author_avatar_url: str | None = None
    text: str | None = None
    sentiment: str | None = None


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    text: str | None = None
    sentiment: str | None = None
    is_hidden: bool | None = None


class CommentResponse(CommentBase):
    id: uuid.UUID
    is_hidden: bool
    replied_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
