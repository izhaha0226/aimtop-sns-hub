"""
AI Schemas - Pydantic v2 request/response models for AI endpoints.
"""
from pydantic import BaseModel, Field


# ── Generate Copy ──────────────────────────────────────────

class GenerateCopyRequest(BaseModel):
    platform: str = Field(..., description="Target platform: instagram, blog, youtube, x, threads")
    tone: str = Field("친근한", description="Tone of voice")
    topic: str = Field(..., description="Main topic or subject")
    context: str = Field("", description="Additional context or instructions")
    language: str = Field("ko", description="Output language: ko, en, ja")
    brand_name: str = Field("", description="Brand name for context")
    target_audience: str = Field("", description="Target audience description")
    strategy_keywords: list[str] = Field(default_factory=list, description="Strategy keywords to include")


class GenerateCopyResponse(BaseModel):
    title: str = ""
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""


# ── Generate Image ─────────────────────────────────────────

class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., description="Image generation prompt")
    size: str = Field("1024x1024", description="Image size: 1024x1024, 1024x768, etc.")
    model: str = Field("fast", description="Model: fast (nano2) or quality (nano_pro)")


class GenerateImageResponse(BaseModel):
    image_url: str = ""
    seed: int = 0
    model_used: str = ""


# ── Suggest Hashtags ───────────────────────────────────────

class SuggestHashtagsRequest(BaseModel):
    topic: str = Field(..., description="Topic for hashtag suggestions")
    platform: str = Field("instagram", description="Target platform")
    count: int = Field(15, ge=1, le=50, description="Number of hashtags")


class SuggestHashtagsResponse(BaseModel):
    hashtags: list[str] = Field(default_factory=list)


# ── Generate Concept Sets ─────────────────────────────────

class SlideSchema(BaseModel):
    title: str = ""
    body: str = ""
    visual_direction: str = ""


class ConceptSetSchema(BaseModel):
    concept_name: str = ""
    slides: list[SlideSchema] = Field(default_factory=list)


class GenerateConceptSetsRequest(BaseModel):
    topic: str = Field(..., description="Card-news topic")
    brand_info: str = Field("", description="Brand information for context")
    count: int = Field(3, ge=1, le=5, description="Number of concept sets")


class GenerateConceptSetsResponse(BaseModel):
    concept_sets: list[ConceptSetSchema] = Field(default_factory=list)


# ── Chat Edit ──────────────────────────────────────────────

class ChatEditRequest(BaseModel):
    original_text: str = Field(..., description="Original text to edit")
    instruction: str = Field(..., description="Edit instruction")


class ChatEditResponse(BaseModel):
    edited_text: str = ""


# ── Generate Strategy ──────────────────────────────────────

class ThemeSchema(BaseModel):
    week: int = 0
    theme: str = ""
    keywords: list[str] = Field(default_factory=list)
    content_ideas: list[str] = Field(default_factory=list)


class KPISchema(BaseModel):
    followers_target: int = 0
    engagement_rate: float = 0.0


class GenerateStrategyRequest(BaseModel):
    client_info: str = Field(..., description="Client information text")
    period: str = Field("monthly", description="Strategy period: weekly, monthly, quarterly")
    brand_name: str = Field("", description="Brand name")
    tone: str = Field("", description="Brand tone")
    target_audience: str = Field("", description="Target audience")
    goals: list[str] = Field(default_factory=list, description="Campaign goals")


class GenerateStrategyResponse(BaseModel):
    period: str = ""
    summary: str = ""
    goals: list[str] = Field(default_factory=list)
    themes: list[ThemeSchema] = Field(default_factory=list)
    kpi: KPISchema = Field(default_factory=KPISchema)
    notes: str = ""
