import uuid
from datetime import datetime
from pydantic import BaseModel


class AppSecretResponse(BaseModel):
    id: uuid.UUID | None = None
    secret_key: str
    label: str
    category: str
    description: str | None = None
    configured: bool = False
    source: str = "empty"
    masked_value: str = ""
    is_active: bool = True
    updated_at: datetime | None = None


class AppSecretUpdateRequest(BaseModel):
    value: str | None = None
    is_active: bool = True


class AppSecretCatalogItem(BaseModel):
    secret_key: str
    label: str
    category: str
    description: str | None = None
