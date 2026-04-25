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
    handle: str | None = None
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

    model_config = {"from_attributes": True}


class BenchmarkPostResponse(BaseModel):
    id: uuid.UUID
    benchmark_account_id: uuid.UUID
    client_id: uuid.UUID
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
    raw_payload: dict | None = None
    source_scope: str = "client_direct"
    source_scope_label: str = "직접 클라이언트"
    is_direct_client_post: bool = True

    model_config = {"from_attributes": True}


class RefreshAccountResponse(BaseModel):
    status: str
    status_label: str | None = None
    message: str
    inserted: int = 0
    profile_id: uuid.UUID | None = None
    profile_generated: bool = False
    live_supported: bool = False
    platform: str | None = None
    used_placeholder: bool = False
    data_source: str | None = None
    data_source_label: str | None = None
    view_metric_type: str | None = None
    view_metric_label: str | None = None
    source_channel_connected: bool = False
    source_channel_platform: str | None = None
    source_channel_account_name: str | None = None
    source_channel_missing_reason: str | None = None
    source_channel_has_token: bool = False
    source_channel_connection_count: int = 0
    source_channel_duplicate_count: int = 0
    source_channel_duplicate_warning: bool = False
    refreshed_at: datetime | None = None


class BenchmarkAccountDiagnosticResponse(BaseModel):
    account_id: uuid.UUID
    client_id: uuid.UUID
    platform: str
    handle: str
    is_active: bool = True
    support_level: str
    support_label: str
    status: str
    status_label: str | None = None
    message: str
    live_supported: bool = False
    source_channel_connected: bool = False
    source_channel_platform: str | None = None
    source_channel_account_name: str | None = None
    source_channel_missing_reason: str | None = None
    source_channel_has_token: bool = False
    source_channel_connection_count: int = 0
    source_channel_duplicate_count: int = 0
    source_channel_duplicate_warning: bool = False
    live_post_count: int = 0
    placeholder_post_count: int = 0
    actual_metric_count: int = 0
    proxy_metric_count: int = 0
    total_post_count: int = 0
    data_source: str | None = None
    data_source_label: str | None = None
    view_metric_type: str | None = None
    view_metric_label: str | None = None
    used_placeholder: bool = False
    last_refresh_status: str | None = None
    last_refresh_status_label: str | None = None
    last_refresh_message: str | None = None
    last_refresh_inserted: int = 0
    last_refresh_profile_id: uuid.UUID | None = None
    last_refresh_profile_generated: bool = False
    last_refresh_used_placeholder: bool = False
    last_refresh_data_source: str | None = None
    last_refresh_data_source_label: str | None = None
    last_refresh_view_metric_type: str | None = None
    last_refresh_view_metric_label: str | None = None
    last_refresh_at: datetime | None = None


class ActionLanguageProfileResponse(BaseModel):
    id: uuid.UUID | None = None
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
    source_client_id: uuid.UUID | None = None
    industry_category: str | None = None
    sample_count: int = 0

    model_config = {"from_attributes": True}


class TopPostsQuery(BaseModel):
    client_id: uuid.UUID
    platform: str
    top_k: int = Field(default=10, ge=1, le=50)
