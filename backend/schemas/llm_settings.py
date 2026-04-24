import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LLMProviderConfigResponse(BaseModel):
    id: uuid.UUID | None = None
    provider_name: str
    model_name: str
    label: str
    is_active: bool = True
    is_default: bool = False
    supports_json: bool = True
    supports_reasoning: bool = True
    max_tokens: int = 4096
    timeout_seconds: int = 60
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LLMProviderConfigUpdateRequest(BaseModel):
    label: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    supports_json: bool | None = None
    supports_reasoning: bool | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)


class LLMTaskPolicyResponse(BaseModel):
    task_type: str
    routing_mode: str = "manual"
    primary_provider: str = "gpt"
    primary_model: str = "gpt-5.4"
    fallback_provider: str | None = None
    fallback_model: str | None = None
    top_k: int = 10
    benchmark_window_days: int = 30
    views_weight: float = 0.45
    engagement_weight: float = 0.30
    recency_weight: float = 0.15
    action_language_weight: float = 0.10
    strict_json_mode: bool = True
    fallback_enabled: bool = True
    notes: str | None = None
    is_active: bool = True
    updated_at: datetime | None = None


class LLMTaskPolicyUpdateRequest(BaseModel):
    routing_mode: str | None = None
    primary_provider: str | None = None
    primary_model: str | None = None
    fallback_provider: str | None = None
    fallback_model: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)
    benchmark_window_days: int | None = Field(default=None, ge=1, le=365)
    views_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    engagement_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    recency_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    action_language_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    strict_json_mode: bool | None = None
    fallback_enabled: bool | None = None
    notes: str | None = None
    is_active: bool | None = None
