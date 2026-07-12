from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CapabilityItem(BaseModel):
    platform: str
    label: str
    oauth: bool
    publish: bool
    publish_media: list[str] = []
    comment_fetch: bool
    comment_reply: bool
    material_variant: bool
    automation_ready: bool
    notes: str = ""
    blockers: list[str] = []


class PolicyUpsert(BaseModel):
    enabled: bool = False
    require_approval: bool = True
    daily_limit: int = Field(default=3, ge=0, le=50)
    auto_reply_enabled: bool = False
    quiet_hours_json: dict[str, Any] | None = None
    config_json: dict[str, Any] | None = None


class PolicyResponse(BaseModel):
    id: uuid.UUID | None = None
    client_id: uuid.UUID
    platform: str
    enabled: bool = False
    require_approval: bool = True
    daily_limit: int = 3
    auto_reply_enabled: bool = False
    quiet_hours_json: dict[str, Any] | None = None
    config_json: dict[str, Any] | None = None
    capability: CapabilityItem | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class MaterialGenerateRequest(BaseModel):
    client_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    brief: str | None = None
    objective: str | None = None
    target_audience: str | None = None
    core_message: str | None = None
    channels: list[str] = Field(default_factory=lambda: ["instagram", "facebook", "threads"])
    require_approval: bool = True
    generate_images: bool = False
    use_fallback_storyline: bool = False


class ActionLogResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID | None = None
    client_id: uuid.UUID
    platform: str | None = None
    action: str
    target_id: str | None = None
    ok: bool
    evidence_json: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    kind: str
    status: str
    summary_json: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class MaterialGenerateResponse(BaseModel):
    ok: bool
    run: RunResponse
    topic_id: uuid.UUID | None = None
    contents: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []


class CommentSyncRequest(BaseModel):
    client_id: uuid.UUID
    platform: str | None = None
    apply_auto_reply: bool = True
