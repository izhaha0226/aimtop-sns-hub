"""
Analytics Service - SNS performance data collection and analysis.
"""
import uuid
import json
import logging
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.analytics import Analytics
from models.channel import ChannelConnection
from models.content import Content

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_analytics(self, account_id: uuid.UUID) -> dict:
        """SNS API에서 성과 데이터 가져와서 analytics 테이블에 저장."""
        # 채널 연결 정보 조회
        result = await self.db.execute(
            select(ChannelConnection).where(ChannelConnection.id == account_id)
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise ValueError("채널 연결을 찾을 수 없습니다")

        today = date.today()

        # 이미 오늘 데이터가 있는지 확인
        existing = await self.db.execute(
            select(Analytics).where(
                and_(
                    Analytics.channel_connection_id == account_id,
                    Analytics.date == today,
                )
            )
        )
        record = existing.scalar_one_or_none()

        # 플랫폼별 데이터 수집 (실제 API 연동 전 placeholder)
        platform_data = await self._fetch_platform_data(channel)

        if record:
            # 기존 레코드 업데이트
            record.followers = platform_data.get("followers", 0)
            record.following = platform_data.get("following", 0)
            record.posts_count = platform_data.get("posts_count", 0)
            record.impressions = platform_data.get("impressions", 0)
            record.reach = platform_data.get("reach", 0)
            record.engagement = platform_data.get("engagement", 0)
            record.clicks = platform_data.get("clicks", 0)
            record.saves = platform_data.get("saves", 0)
            record.shares = platform_data.get("shares", 0)
            record.platform_data = platform_data.get("raw", {})
        else:
            record = Analytics(
                channel_connection_id=account_id,
                date=today,
                followers=platform_data.get("followers", 0),
                following=platform_data.get("following", 0),
                posts_count=platform_data.get("posts_count", 0),
                impressions=platform_data.get("impressions", 0),
                reach=platform_data.get("reach", 0),
                engagement=platform_data.get("engagement", 0),
                clicks=platform_data.get("clicks", 0),
                saves=platform_data.get("saves", 0),
                shares=platform_data.get("shares", 0),
                platform_data=platform_data.get("raw", {}),
            )
            self.db.add(record)

        await self.db.commit()
        await self.db.refresh(record)

        return {
            "id": str(record.id),
            "channel_connection_id": str(record.channel_connection_id),
            "date": record.date.isoformat(),
            "followers": record.followers,
            "impressions": record.impressions,
            "engagement": record.engagement,
            "synced": True,
        }

    async def _fetch_platform_data(self, channel: ChannelConnection) -> dict:
        """플랫폼별 API에서 데이터 수집 (추후 각 플랫폼 API 연동)."""
        platform = channel.channel_type
        logger.info("Fetching analytics for %s channel: %s", platform, channel.account_name)

        # TODO: 각 플랫폼 API 실제 연동
        # instagram: Graph API /me/insights
        # youtube: YouTube Analytics API
        # twitter: Twitter API v2 /tweets/counts
        # naver_blog: Naver Blog API

        return {
            "followers": 0,
            "following": 0,
            "posts_count": 0,
            "impressions": 0,
            "reach": 0,
            "engagement": 0,
            "clicks": 0,
            "saves": 0,
            "shares": 0,
            "raw": {"platform": platform, "note": "API 연동 전 placeholder"},
        }

    async def get_summary(
        self, account_id: uuid.UUID, start_date: date, end_date: date
    ) -> dict:
        """기간별 요약 (followers_growth, total_impressions, avg_engagement_rate 등)."""
        result = await self.db.execute(
            select(Analytics)
            .where(
                and_(
                    Analytics.channel_connection_id == account_id,
                    Analytics.date >= start_date,
                    Analytics.date <= end_date,
                )
            )
            .order_by(Analytics.date.asc())
        )
        records = result.scalars().all()

        if not records:
            return {
                "account_id": str(account_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": 0,
                "followers_start": 0,
                "followers_end": 0,
                "followers_growth": 0,
                "total_impressions": 0,
                "total_reach": 0,
                "total_engagement": 0,
                "avg_engagement_rate": 0.0,
                "total_clicks": 0,
                "total_saves": 0,
                "total_shares": 0,
            }

        first = records[0]
        last = records[-1]
        followers_growth = last.followers - first.followers
        total_impressions = sum(r.impressions for r in records)
        total_engagement = sum(r.engagement for r in records)
        avg_engagement_rate = (
            round(total_engagement / total_impressions * 100, 2)
            if total_impressions > 0
            else 0.0
        )

        return {
            "account_id": str(account_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": len(records),
            "followers_start": first.followers,
            "followers_end": last.followers,
            "followers_growth": followers_growth,
            "total_impressions": total_impressions,
            "total_reach": sum(r.reach for r in records),
            "total_engagement": total_engagement,
            "avg_engagement_rate": avg_engagement_rate,
            "total_clicks": sum(r.clicks for r in records),
            "total_saves": sum(r.saves for r in records),
            "total_shares": sum(r.shares for r in records),
        }

    async def get_daily_stats(
        self, account_id: uuid.UUID, start_date: date, end_date: date
    ) -> list:
        """일별 시계열 데이터."""
        result = await self.db.execute(
            select(Analytics)
            .where(
                and_(
                    Analytics.channel_connection_id == account_id,
                    Analytics.date >= start_date,
                    Analytics.date <= end_date,
                )
            )
            .order_by(Analytics.date.asc())
        )
        records = result.scalars().all()

        return [
            {
                "date": r.date.isoformat(),
                "followers": r.followers,
                "following": r.following,
                "posts_count": r.posts_count,
                "impressions": r.impressions,
                "reach": r.reach,
                "engagement": r.engagement,
                "clicks": r.clicks,
                "saves": r.saves,
                "shares": r.shares,
            }
            for r in records
        ]

    async def get_content_performance(
        self, client_id: uuid.UUID, limit: int = 20
    ) -> list:
        """콘텐츠별 성과 랜킹 (발행된 콘텐츠 기준)."""
        result = await self.db.execute(
            select(Content)
            .where(
                and_(
                    Content.client_id == client_id,
                    Content.status == "published",
                    Content.published_at.isnot(None),
                )
            )
            .order_by(Content.published_at.desc())
            .limit(limit)
        )
        contents = result.scalars().all()

        return [
            {
                "id": str(c.id),
                "title": c.title,
                "post_type": c.post_type,
                "platform_post_id": c.platform_post_id,
                "published_url": c.published_url,
                "published_at": c.published_at.isoformat() if c.published_at else None,
                "channel_connection_id": str(c.channel_connection_id) if c.channel_connection_id else None,
            }
            for c in contents
        ]

    async def generate_ai_insights(self, account_id: uuid.UUID) -> dict:
        """Claude CLI로 성과 분석 AI 인사이트 생성."""
        from services.ai_service import call_claude, _parse_json_response

        # 최근 30일 데이터 조회
        end = date.today()
        start = end - timedelta(days=30)
        summary = await self.get_summary(account_id, start, end)
        daily = await self.get_daily_stats(account_id, start, end)

        # 채널 정보 조회
        ch_result = await self.db.execute(
            select(ChannelConnection).where(ChannelConnection.id == account_id)
        )
        channel = ch_result.scalar_one_or_none()
        channel_info = (
            f"{channel.channel_type} / {channel.account_name}"
            if channel
            else "unknown"
        )

        prompt = (
            f"다음 SNS 계정의 최근 30일 성과 데이터를 분석해서 인사이트를 제공해줘.\n\n"
            f"채널: {channel_info}\n"
            f"요약: {json.dumps(summary, ensure_ascii=False)}\n"
            f"일별 데이터 (최근 7일): {json.dumps(daily[-7:], ensure_ascii=False)}\n\n"
            f"JSON 형식으로 응답해:\n"
            f'{{"summary": "전체 요약", '
            f'"strengths": ["강점1", "강점2"], '
            f'"improvements": ["개선점1", "개선점2"], '
            f'"recommendations": ["추천 액션1", "추천 액션2"], '
            f'"predicted_trend": "향후 트렌드 예측"}}'
        )

        try:
            raw = await call_claude(prompt, timeout=120)
            insights = _parse_json_response(raw)
            if isinstance(insights, dict):
                return insights
            return {"summary": raw, "strengths": [], "improvements": [], "recommendations": [], "predicted_trend": ""}
        except Exception as e:
            logger.error("AI insights generation failed: %s", e)
            return {
                "summary": "AI 인사이트 생성에 실패했습니다",
                "strengths": [],
                "improvements": [],
                "recommendations": [],
                "predicted_trend": "",
                "error": str(e),
            }
