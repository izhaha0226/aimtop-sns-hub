import uuid
from datetime import datetime
from pydantic import BaseModel


class ApprovalCreate(BaseModel):
    memo: str | None = None


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    approver_id: uuid.UUID | None
    action: str
    memo: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
