import uuid
from datetime import datetime

from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    logo: str | None = None
    brand_color: str | None = None
    account_type: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    logo: str | None = None
    brand_color: str | None = None
    account_type: str | None = None


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    logo: str | None = None
    brand_color: str | None = None
    account_type: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    size: int
