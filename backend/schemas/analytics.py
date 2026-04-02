import uuid
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel


class AnalyticsBase(BaseModel):
    channel_connection_id: uuid.UUID
    date: date
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    impressions: int = 0
    reach: int = 0
    engagement: int = 0
    clicks: int = 0
    saves: int = 0
    shares: int = 0
    platform_data: dict[str, Any] | None = None


class AnalyticsCreate(AnalyticsBase):
    pass


class AnalyticsResponse(AnalyticsBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsListResponse(BaseModel):
    items: list[AnalyticsResponse]
    total: int


class AnalyticsSummary(BaseModel):
    total_followers: int = 0
    total_impressions: int = 0
    total_reach: int = 0
    total_engagement: int = 0
    total_clicks: int = 0
    period_start: date | None = None
    period_end: date | None = None
