import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BenchmarkAccountCreateRequest(BaseModel):
    client_id: uuid.UUID
    platform: str
    handle: str
    purpose: str = "all"
    source_type: str = "manual"
    memo: str | None = None
    metadata_json: dict | None = None


class BenchmarkAccountUpdateRequest(BaseModel):
    purpose: str | None = None
    source_type: str | None = None
    memo: str | None = None
    metadata_json: dict | None = None
    is_active: bool | None = None


class BenchmarkAccountResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    platform: str
    handle: str
    source_type: str = "manual"
    purpose: str = "all"
    memo: str | None = None
    auto_discovered: bool = False
    is_active: bool = True
    metadata_json: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BenchmarkPostResponse(BaseModel):
    id: uuid.UUID
    benchmark_account_id: uuid.UUID
    platform: str
    external_post_id: str | None = None
    post_url: str | None = None
    content_text: str | None = None
    hook_text: str | None = None
    cta_text: str | None = None
    format_type: str | None = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    save_count: int = 0
    engagement_rate: float = 0.0
    benchmark_score: float = 0.0
    published_at: datetime | None = None


class ActionLanguageProfileResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    platform: str
    source_scope: str
    top_hooks_json: list | None = None
    top_ctas_json: list | None = None
    tone_patterns_json: dict | None = None
    format_patterns_json: dict | None = None
    recommended_prompt_rules: str | None = None
    profile_version: int = 1
    updated_at: datetime | None = None


class TopPostsQuery(BaseModel):
    client_id: uuid.UUID
    platform: str
    top_k: int = Field(default=10, ge=1, le=50)
