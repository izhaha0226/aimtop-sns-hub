"""
AI Schemas - Pydantic v2 request/response models for AI endpoints.
"""
import uuid

from pydantic import BaseModel, Field


class EngineOverride(BaseModel):
    provider: str | None = None
    model: str | None = None
    fallback_enabled: bool | None = None


class BenchmarkOverride(BaseModel):
    client_id: uuid.UUID | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)
    window_days: int | None = Field(default=None, ge=1, le=365)
    platform: str | None = None


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
    engine: EngineOverride | None = None
    benchmark: BenchmarkOverride | None = None


class GenerateCopyResponse(BaseModel):
    title: str = ""
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""


# ── Generate Image ─────────────────────────────────────────

class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., description="Image generation prompt")
    size: str = Field("1024x1024", description="Image size: 1024x1024, 1024x768, etc.")
    model: str = Field("gpt-image-2.0", description="Model alias. Default: gpt-image-2.0 via Fal")
    quality: str | None = Field(default=None, description="GPT Image quality: low, medium, high")


class GenerateImageResponse(BaseModel):
    image_url: str = ""
    seed: int = 0
    model_used: str = ""


# ── Suggest Hashtags ───────────────────────────────────────

class SuggestHashtagsRequest(BaseModel):
    topic: str = Field(..., description="Topic for hashtag suggestions")
    platform: str = Field("instagram", description="Target platform")
    count: int = Field(15, ge=1, le=50, description="Number of hashtags")
    engine: EngineOverride | None = None


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
    engine: EngineOverride | None = None


class GenerateConceptSetsResponse(BaseModel):
    concept_sets: list[ConceptSetSchema] = Field(default_factory=list)


# ── Chat Edit ──────────────────────────────────────────────

class ChatEditRequest(BaseModel):
    original_text: str = Field(..., description="Original text to edit")
    instruction: str = Field(..., description="Edit instruction")
    engine: EngineOverride | None = None


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
    engine: EngineOverride | None = None


class GenerateStrategyResponse(BaseModel):
    period: str = ""
    summary: str = ""
    goals: list[str] = Field(default_factory=list)
    themes: list[ThemeSchema] = Field(default_factory=list)
    kpi: KPISchema = Field(default_factory=KPISchema)
    notes: str = ""


# ── Generate Operation Plan ─────────────────────────────────

class GenerateOperationPlanRequest(BaseModel):
    client_id: uuid.UUID | None = Field(default=None, description="Selected client for benchmark collection/context")
    brand_name: str = Field(..., description="Brand name to operate")
    product_summary: str = Field(..., description="Product/service and offer summary")
    target_audience: str = Field("", description="Target audience to analyze")
    goals: list[str] = Field(default_factory=list, description="Operation goals")
    channels: list[str] = Field(default_factory=lambda: ["instagram", "threads"], description="Target SNS channels")
    benchmark_brands: list[str] = Field(default_factory=list, description="Benchmark brands/accounts")
    month: str | None = Field(default=None, description="Target month, e.g. 2026-06")
    season_context: str = Field("", description="Seasonal context or events")
    budget_level: str = Field("standard", description="lean, standard, aggressive")
    notes: str = Field("", description="Additional instructions")
    engine: EngineOverride | None = None


class ChannelOperationPlanSchema(BaseModel):
    channel: str = ""
    monthly_count: int = 0
    recommended_formats: list[str] = Field(default_factory=list)
    role: str = ""
    cadence: str = ""


class WeeklyChannelPlanSchema(BaseModel):
    channel: str = ""
    count: int = 0
    formats: list[str] = Field(default_factory=list)


class WeeklyOperationPlanSchema(BaseModel):
    week: int = 0
    theme: str = ""
    objective: str = ""
    channels: list[WeeklyChannelPlanSchema] = Field(default_factory=list)


class BenchmarkOperationInsightSchema(BaseModel):
    brand: str = ""
    channel: str = ""
    source_status: str = "manual_or_pending"
    support_level: str = "manual"
    evidence_count: int = 0
    hook_patterns: list[str] = Field(default_factory=list)
    format_patterns: list[str] = Field(default_factory=list)
    cta_patterns: list[str] = Field(default_factory=list)
    apply_points: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GenerateOperationPlanResponse(BaseModel):
    brand_name: str = ""
    month: str = ""
    strategy_summary: str = ""
    target_insights: list[str] = Field(default_factory=list)
    brand_study: list[str] = Field(default_factory=list)
    primary_offer: str = ""
    product_angles: list[str] = Field(default_factory=list)
    supermarketing_strategy: list[str] = Field(default_factory=list)
    seasonal_context: str = ""
    benchmark_source_status: str = "manual_or_pending"
    benchmark_notes: list[str] = Field(default_factory=list)
    benchmark_insights: list[BenchmarkOperationInsightSchema] = Field(default_factory=list)
    monthly_volume: dict[str, int] = Field(default_factory=dict)
    total_monthly_count: int = 0
    weekly_plan: list[WeeklyOperationPlanSchema] = Field(default_factory=list)
    channel_plan: list[ChannelOperationPlanSchema] = Field(default_factory=list)
    approval_checklist: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
