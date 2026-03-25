import uuid
from datetime import datetime
from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    logo: str | None = None
    brand_color: str | None = None
    account_type: str = "brand"


class ClientUpdate(BaseModel):
    name: str | None = None
    logo: str | None = None
    brand_color: str | None = None
    account_type: str | None = None


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    logo: str | None
    brand_color: str | None
    account_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
