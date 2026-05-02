import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReferenceAsset(BaseModel):
    url: str
    asset_type: str = "reference"
    usage_mode: str = "reference_only"
    target_cards: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    memo: str | None = None


class CardStorylineItem(BaseModel):
    card_no: int
    headline: str
    body: str
    visual_brief: str
    cta_or_transition: str | None = None


class VisualOption(BaseModel):
    option_id: str
    label: str
    style_type: str
    prompt: str
    image_url: str | None = None


class ContentTopicCreate(BaseModel):
    client_id: uuid.UUID
    title: str
    brief: str | None = None
    objective: str | None = "awareness"
    target_audience: str | None = None
    core_message: str | None = None
    channels: list[str] = Field(default_factory=lambda: ["instagram", "facebook", "threads"])
    reference_assets: list[ReferenceAsset] | None = None
    benchmark_context: dict[str, Any] | None = None
    source_metadata: dict[str, Any] | None = None


class ContentTopicUpdate(BaseModel):
    title: str | None = None
    brief: str | None = None
    objective: str | None = None
    target_audience: str | None = None
    core_message: str | None = None
    card_storyline: list[CardStorylineItem] | None = None
    reference_assets: list[ReferenceAsset] | None = None
    visual_options: list[VisualOption] | None = None
    selected_visual_option: str | None = None
    shared_media_urls: list[str] | None = None
    status: str | None = None
    source_metadata: dict[str, Any] | None = None


class ReferenceAssetsRequest(BaseModel):
    assets: list[ReferenceAsset]


class GenerateStorylineRequest(BaseModel):
    force_regenerate: bool = False
    engine: dict[str, Any] | None = None


class GenerateVisualOptionsRequest(BaseModel):
    force_regenerate: bool = False
    engine: dict[str, Any] | None = None


class SelectVisualOptionRequest(BaseModel):
    option_id: str


class GenerateCardImagesRequest(BaseModel):
    force_regenerate: bool = False
    size: str = "1024x1024"
    model: str = "fast"
    quality: str | None = "medium"


class GenerateChannelVariantsRequest(BaseModel):
    channels: list[str] = Field(default_factory=lambda: ["instagram", "facebook", "threads"])
    engine: dict[str, Any] | None = None
    create_contents: bool = True


class ContentTopicResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    author_id: uuid.UUID | None
    title: str
    brief: str | None
    objective: str | None
    target_audience: str | None
    core_message: str | None
    card_storyline: list[Any] | None
    reference_assets: list[Any] | None
    visual_options: list[Any] | None
    selected_visual_option: str | None
    shared_visual_prompt: str | None
    shared_media_urls: list[Any] | None
    benchmark_context: dict[str, Any] | None
    source_metadata: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentTopicListResponse(BaseModel):
    items: list[ContentTopicResponse]
    total: int


class ChannelVariantResponse(BaseModel):
    platform: str
    title: str
    text: str
    hashtags: list[str]
    content_id: uuid.UUID | None = None
