import uuid
from datetime import datetime
from pydantic import BaseModel


class OnboardingStep1(BaseModel):
    account_type: str


class OnboardingStep2(BaseModel):
    tones: list[str]
    forbidden_words: list[str] = []
    emoji_policy: str = "minimal"
    hashtag_policy: str = "medium"
    extra_notes: str | None = None


class OnboardingStep3(BaseModel):
    selected_channels: list[str]


class BenchmarkChannel(BaseModel):
    platform: str
    handle: str
    url: str | None = None
    purpose: str = "all"
    memo: str | None = None


class OnboardingStep4(BaseModel):
    benchmark_channels: list[BenchmarkChannel]


class OnboardingResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    account_type: str | None
    tones: list | None
    forbidden_words: list | None
    emoji_policy: str
    hashtag_policy: str
    selected_channels: list | None
    benchmark_channels: list | None
    strategy_content: str | None
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
