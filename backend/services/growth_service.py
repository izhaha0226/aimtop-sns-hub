"""
Growth Service - AI 기반 성장 허브.
트렌딩 해시태그, 콘텐츠 아이디어, 경쟁사 분석, 최적 스케줄.
Claude CLI만 사용 (Anthropic API 직접 호출 금지).
"""
import json
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_service import call_claude, _parse_json_response

logger = logging.getLogger(__name__)


class GrowthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_trending_hashtags(
        self, platform: str, category: str | None = None
    ) -> list:
        """Claude CLI로 트렌딩 해시태그 분석."""
        category_text = f" ({category} 카테고리)" if category else ""
        prompt = (
            f"{platform} 플랫폼{category_text}에서 현재 트렌딩 중인 해시태그 20개를 추천해줘.\n"
            f"각 해시태그의 인기도(high/medium/low)와 추천 이유도 함께 제공해.\n\n"
            f"JSON 배열로만 응답:\n"
            f'[{{"hashtag": "#예시", "popularity": "high", "reason": "이유"}}]'
        )
        raw = await call_claude(prompt)
        try:
            result = _parse_json_response(raw)
            return result if isinstance(result, list) else [result]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Trending hashtag parse failed: %s", e)
            return [{"hashtag": tag.strip(), "popularity": "medium", "reason": ""}
                    for tag in raw.split(",") if tag.strip().startswith("#")]

    async def get_content_ideas(
        self, client_id: uuid.UUID, count: int = 10
    ) -> list:
        """콘텐츠 아이디어 AI 생성."""
        # 최근 콘텐츠 정보 조회
        from models.content import Content
        result = await self.db.execute(
            select(Content.title, Content.platform, Content.post_type)
            .where(Content.client_id == client_id)
            .order_by(Content.created_at.desc())
            .limit(20)
        )
        recent = result.all()
        recent_titles = [r[0] for r in recent if r[0]] or ["정보 없음"]
        platforms = list(set(r[1] for r in recent if r[1])) or ["instagram"]

        prompt = (
            f"다음 클라이언트의 최근 콘텐츠를 분석하고 새로운 콘텐츠 아이디어를 {count}개 제안해줘.\n\n"
            f"최근 콘텐츠 제목:\n"
            + "\n".join(f"- {t}" for t in recent_titles[:10])
            + f"\n\n활성 플랫폼: {', '.join(platforms)}\n\n"
            f"JSON 배열로만 응답:\n"
            f'[{{"title": "아이디어 제목", "platform": "플랫폼", "post_type": "유형", '
            f'"description": "설명", "expected_engagement": "high/medium/low"}}]'
        )
        raw = await call_claude(prompt, timeout=180)
        try:
            result = _parse_json_response(raw)
            ideas = result if isinstance(result, list) else [result]
            return ideas[:count]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Content ideas parse failed: %s", e)
            return [{"title": "아이디어 생성 실패", "description": raw, "expected_engagement": "low"}]

    async def get_competitor_analysis(
        self, competitor_handles: list[str]
    ) -> dict:
        """경쟁사 분석 AI."""
        handles_text = ", ".join(competitor_handles)
        prompt = (
            f"다음 SNS 계정들의 경쟁사 분석을 수행해줘: {handles_text}\n\n"
            f"각 계정에 대해 추정되는 전략, 강점, 약점, 콘텐츠 패턴을 분석해.\n\n"
            f"JSON 형식으로 응답:\n"
            f'{{"competitors": [{{"handle": "@계정", "estimated_strategy": "...", '
            f'"strengths": ["..."], "weaknesses": ["..."], "content_pattern": "...", '
            f'"posting_frequency": "..."}}], '
            f'"recommendations": ["우리가 할 수 있는 차별화 전략"], '
            f'"market_gaps": ["시장 기회"]}}'
        )
        raw = await call_claude(prompt, timeout=180)
        try:
            result = _parse_json_response(raw)
            return result if isinstance(result, dict) else {"raw": result}
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Competitor analysis parse failed: %s", e)
            return {"competitors": [], "recommendations": [raw], "market_gaps": []}

    async def get_optimal_schedule(self, account_id: uuid.UUID) -> dict:
        """최적 스케줄 AI 추천."""
        # 기존 스케줄/분석 데이터 조회
        from models.analytics import Analytics
        from models.channel import ChannelConnection

        channel_result = await self.db.execute(
            select(ChannelConnection.platform)
            .where(ChannelConnection.id == account_id)
        )
        channel = channel_result.scalar_one_or_none()
        platform = channel or "instagram"

        # 요일별 분석 데이터
        analytics_result = await self.db.execute(
            select(
                func.extract("dow", Analytics.date).label("dow"),
                func.avg(Analytics.likes).label("avg_likes"),
                func.avg(Analytics.reach).label("avg_reach"),
            )
            .where(Analytics.channel_id == account_id)
            .group_by("dow")
            .order_by("dow")
        )
        weekday_stats = [
            {"day_of_week": int(r[0]), "avg_likes": float(r[1] or 0), "avg_reach": float(r[2] or 0)}
            for r in analytics_result.all()
        ]

        stats_text = json.dumps(weekday_stats, ensure_ascii=False) if weekday_stats else "데이터 없음"

        prompt = (
            f"{platform} 플랫폼 계정의 최적 포스팅 스케줄을 추천해줘.\n\n"
            f"요일별 성과 데이터:\n{stats_text}\n\n"
            f"JSON 형식으로 응답:\n"
            f'{{"platform": "{platform}", '
            f'"recommended_times": [{{"day": "월요일", "times": ["09:00", "18:00"], "reason": "..."}}], '
            f'"posting_frequency": "주 N회 추천", '
            f'"best_days": ["화요일", "목요일"], '
            f'"avoid_times": ["..."], '
            f'"tips": ["..."]}}'
        )
        raw = await call_claude(prompt)
        try:
            result = _parse_json_response(raw)
            return result if isinstance(result, dict) else {"raw": result}
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Optimal schedule parse failed: %s", e)
            return {
                "platform": platform,
                "recommended_times": [],
                "posting_frequency": "분석 실패",
                "tips": [raw],
            }
