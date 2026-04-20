from __future__ import annotations

from datetime import datetime, timezone
import math


def _safe_log_norm(value: int | float, scale: float = 10000.0) -> float:
    if value <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(scale))


def normalize_views(view_count: int) -> float:
    return _safe_log_norm(view_count, scale=100000.0)


def normalize_engagement(engagement_rate: float) -> float:
    if engagement_rate <= 0:
        return 0.0
    return min(1.0, engagement_rate / 15.0)


def normalize_recency(published_at: datetime | None, window_days: int = 30) -> float:
    if not published_at:
        return 0.0
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - published_at).total_seconds() / 86400)
    if days >= window_days:
        return 0.0
    return round(1 - (days / window_days), 4)


def calculate_benchmark_score(post, weights: dict | None = None, window_days: int = 30) -> float:
    weights = weights or {
        "views_weight": 0.45,
        "engagement_weight": 0.30,
        "recency_weight": 0.15,
        "action_language_weight": 0.10,
    }
    action_score = getattr(post, "action_language_score", None)
    if action_score is None and isinstance(post, dict):
        action_score = post.get("action_language_score", 0)
    if action_score is None:
        action_score = 0

    view_count = post.get("view_count", 0) if isinstance(post, dict) else getattr(post, "view_count", 0)
    engagement_rate = post.get("engagement_rate", 0) if isinstance(post, dict) else getattr(post, "engagement_rate", 0)
    published_at = post.get("published_at") if isinstance(post, dict) else getattr(post, "published_at", None)

    score = (
        weights.get("views_weight", 0.45) * normalize_views(int(view_count or 0))
        + weights.get("engagement_weight", 0.30) * normalize_engagement(float(engagement_rate or 0))
        + weights.get("recency_weight", 0.15) * normalize_recency(published_at, window_days=window_days)
        + weights.get("action_language_weight", 0.10) * float(action_score or 0)
    )
    return round(score, 6)
