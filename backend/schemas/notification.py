import uuid
from datetime import datetime
from pydantic import BaseModel


class NotificationBase(BaseModel):
    client_id: uuid.UUID
    user_id: uuid.UUID
    type: str  # comment/mention/milestone/schedule/approval
    title: str
    message: str | None = None
    link_url: str | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    id: uuid.UUID
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int = 0
