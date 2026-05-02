import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from schemas.content import ContentResponse


class OperationPlanCreate(BaseModel):
    client_id: uuid.UUID | None = None
    brand_name: str
    month: str
    strategy_summary: str | None = None
    request_payload: dict[str, Any] | None = None
    plan_payload: dict[str, Any]


class OperationPlanUpdate(BaseModel):
    brand_name: str | None = None
    month: str | None = None
    strategy_summary: str | None = None
    request_payload: dict[str, Any] | None = None
    plan_payload: dict[str, Any] | None = None


class OperationPlanAction(BaseModel):
    memo: str | None = None


class OperationPlanResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID | None
    author_id: uuid.UUID | None
    approver_id: uuid.UUID | None
    brand_name: str
    month: str
    status: str
    strategy_summary: str | None
    request_payload: dict[str, Any] | None
    plan_payload: dict[str, Any] | None
    approval_memo: str | None
    rejected_reason: str | None
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OperationPlanListResponse(BaseModel):
    items: list[OperationPlanResponse]
    total: int


class OperationPlanDraftsResponse(BaseModel):
    operation_plan_id: uuid.UUID
    items: list[ContentResponse]
    total: int
    manual_required_count: int
    token_check_required_count: int
