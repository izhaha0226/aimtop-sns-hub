import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PersonaCreateRequest(BaseModel):
    client_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    tone_keywords_json: list[str] | None = None
    prohibited_topics_json: list[str] | None = None
    author_display_name: str | None = Field(default=None, max_length=120)
    author_transparency: str | None = Field(default=None, max_length=500)
    auth_identity_id: uuid.UUID | None = None
    provider_badge_label: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class PersonaUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    tone_keywords_json: list[str] | None = None
    prohibited_topics_json: list[str] | None = None
    author_display_name: str | None = Field(default=None, max_length=120)
    author_transparency: str | None = Field(default=None, max_length=500)
    auth_identity_id: uuid.UUID | None = None
    provider_badge_label: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class PersonaResponse(PersonaCreateRequest):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TargetRuleCreateRequest(BaseModel):
    client_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    keywords_json: list[str] | None = None
    competitor_handles_json: list[str] | None = None
    hashtags_json: list[str] | None = None
    min_fit_score: float = Field(default=0.55, ge=0, le=1)
    daily_like_limit: int = Field(default=20, ge=0, le=500)
    daily_comment_limit: int = Field(default=5, ge=0, le=100)
    auto_like_enabled: bool = True
    requires_comment_approval: bool = True
    is_active: bool = True


class TargetRuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    keywords_json: list[str] | None = None
    competitor_handles_json: list[str] | None = None
    hashtags_json: list[str] | None = None
    min_fit_score: float | None = Field(default=None, ge=0, le=1)
    daily_like_limit: int | None = Field(default=None, ge=0, le=500)
    daily_comment_limit: int | None = Field(default=None, ge=0, le=100)
    auto_like_enabled: bool | None = None
    requires_comment_approval: bool | None = None
    is_active: bool | None = None


class TargetRuleResponse(TargetRuleCreateRequest):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SafetyFilterCreateRequest(BaseModel):
    client_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    blocked_terms_json: list[str] | None = None
    sensitive_topics_json: list[str] | None = None
    min_safety_score: float = Field(default=0.75, ge=0, le=1)
    is_active: bool = True


class SafetyFilterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    blocked_terms_json: list[str] | None = None
    sensitive_topics_json: list[str] | None = None
    min_safety_score: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None


class SafetyFilterResponse(SafetyFilterCreateRequest):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DraftCreateRequest(BaseModel):
    client_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    target_rule_id: uuid.UUID | None = None
    action_type: str = "comment"
    target_post_url: str | None = Field(default=None, max_length=2000)
    target_author_handle: str | None = Field(default=None, max_length=255)
    target_post_text: str | None = None
    draft_text: str | None = None
    metadata_json: dict | None = None

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        allowed = {"like", "comment", "repost"}
        if value not in allowed:
            raise ValueError(f"action_type must be one of {sorted(allowed)}")
        return value


class DraftUpdateRequest(BaseModel):
    draft_text: str | None = None
    status: str | None = None
    metadata_json: dict | None = None


class DraftResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    target_rule_id: uuid.UUID | None = None
    action_type: str
    target_post_url: str | None = None
    target_author_handle: str | None = None
    target_post_text: str | None = None
    draft_text: str | None = None
    fit_score: float
    safety_score: float
    safety_labels_json: list | None = None
    status: str
    approval_required: bool
    provider_badge_label: str | None = None
    author_transparency: str | None = None
    simulation_status: str
    metadata_json: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApprovalStatusRequest(BaseModel):
    status: str
    review_note: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"queued", "approved", "rejected"}
        if value not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return value


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    draft_id: uuid.UUID
    action_type: str
    status: str
    queue_reason: str | None = None
    requested_by_id: uuid.UUID | None = None
    reviewed_by_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    scheduled_for: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ActionCreateRequest(BaseModel):
    client_id: uuid.UUID
    draft_id: uuid.UUID | None = None
    approval_id: uuid.UUID | None = None
    action_type: str = "like"
    metadata_json: dict | None = None


class ActionLogResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    draft_id: uuid.UUID | None = None
    approval_id: uuid.UUID | None = None
    action_type: str
    status: str
    simulation_status: str
    external_write_enabled: bool
    message: str | None = None
    metadata_json: dict | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class LearningEventCreateRequest(BaseModel):
    client_id: uuid.UUID
    action_log_id: uuid.UUID | None = None
    event_type: str = Field(min_length=1, max_length=50)
    signal_score: float = Field(default=0, ge=0, le=1)
    outcome: str | None = Field(default=None, max_length=100)
    metrics_json: dict | None = None
    notes: str | None = None


class LearningEventResponse(LearningEventCreateRequest):
    id: uuid.UUID
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
