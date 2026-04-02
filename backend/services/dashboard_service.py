"""
Dashboard Service - 통합 대시보드 데이터 및 AI 최적 발행 시간 추천.
"""
import uuid
import json
import logging
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.channel import ChannelConnection
from models.content import Content
from models.analytics import Analytics
from models.schedule import Schedule

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self, client_id: uuid.UUID) -> dict:
        """전체 계정 통합 대시보드."""
        # 총 연결 계정 수
        accounts_result = await self.db.execute(
            select(func.count()).select_from(ChannelConnection).where(
                and_(
                    ChannelConnection.client_id == client_id,
                    ChannelConnection.is_connected.is_(True),
                )
            )
        )
        total_accounts = accounts_result.scalar() or 0

        # 총 팔로워 수 (각 계정의 최신 analytics에서)
        # 서브쿼리: 각 channel_connection_id별 최신 date
        latest_dates = (
            select(
                Analytics.channel_connection_id,
                func.max(Analytics.date).label("max_date"),
            )
            .join(
                ChannelConnection,
                Analytics.channel_connection_id == ChannelConnection.id,
            )
            .where(ChannelConnection.client_id == client_id)
            .group_by(Analytics.channel_connection_id)
            .subquery()
        )

        followers_result = await self.db.execute(
            select(func.coalesce(func.sum(Analytics.followers), 0)).join(
                latest_dates,
                and_(
                    Analytics.channel_connection_id == latest_dates.c.channel_connection_id,
                    Analytics.date == latest_dates.c.max_date,
                ),
            )
        )
        total_followers = followers_result.scalar() or 0

        # 총 콘텐츠 수
        contents_result = await self.db.execute(
            select(func.count()).select_from(Content).where(
                and_(
                    Content.client_id == client_id,
                    Content.status != "trashed",
                )
            )
        )
        total_contents = contents_result.scalar() or 0

        # 예약된 콘텐츠 수
        scheduled_result = await self.db.execute(
            select(func.count()).select_from(Content).where(
                and_(
                    Content.client_id == client_id,
                    Content.status == "scheduled",
                )
            )
        )
        scheduled_count = scheduled_result.scalar() or 0

        # 최근 활동 (최근 발행 콘텐츠 5개)
        recent_result = await self.db.execute(
            select(Content)
            .where(
                and_(
                    Content.client_id == client_id,
                    Content.status != "trashed",
                )
            )
            .order_by(Content.updated_at.desc())
            .limit(5)
        )
        recent_contents = recent_result.scalars().all()

        recent_activities = [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status,
                "post_type": c.post_type,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in recent_contents
        ]

        # 플랫폼별 계정 분포
        platform_result = await self.db.execute(
            select(
                ChannelConnection.channel_type,
                func.count().label("count"),
            )
            .where(
                and_(
                    ChannelConnection.client_id == client_id,
                    ChannelConnection.is_connected.is_(True),
                )
            )
            .group_by(ChannelConnection.channel_type)
        )
        platforms = {row.channel_type: row.count for row in platform_result}

        return {
            "total_accounts": total_accounts,
            "total_followers": total_followers,
            "total_contents": total_contents,
            "scheduled_count": scheduled_count,
            "recent_activities": recent_activities,
            "platforms": platforms,
        }

    async def get_best_times(self, account_id: uuid.UUID) -> dict:
        """AI 기반 최적 발행 시간 추천."""
        from services.ai_service import call_claude, _parse_json_response

        # 채널 정보 조회
        ch_result = await self.db.execute(
            select(ChannelConnection).where(ChannelConnection.id == account_id)
        )
        channel = ch_result.scalar_one_or_none()
        if not channel:
            raise ValueError("채널 연결을 찾을 수 없습니다")

        # 최근 30일 일별 데이터 조회
        end = date.today()
        start = end - timedelta(days=30)
        analytics_result = await self.db.execute(
            select(Analytics)
            .where(
                and_(
                    Analytics.channel_connection_id == account_id,
                    Analytics.date >= start,
                    Analytics.date <= end,
                )
            )
            .order_by(Analytics.date.asc())
        )
        records = analytics_result.scalars().all()

        daily_summary = [
            {
                "date": r.date.isoformat(),
                "impressions": r.impressions,
                "engagement": r.engagement,
                "reach": r.reach,
            }
            for r in records
        ]

        # 최근 발행된 콘텐츠의 발행 시간 분석
        published_result = await self.db.execute(
            select(Content.published_at)
            .where(
                and_(
                    Content.channel_connection_id == account_id,
                    Content.status == "published",
                    Content.published_at.isnot(None),
                )
            )
            .order_by(Content.published_at.desc())
            .limit(20)
        )
        publish_times = [
            row[0].strftime("%A %H:%M") for row in published_result if row[0]
        ]

        prompt = (
            f"다음 SNS 채널의 최적 발행 시간을 추천해줘.\n\n"
            f"플랫폼: {channel.channel_type}\n"
            f"계정: {channel.account_name}\n"
            f"최근 30일 성과: {json.dumps(daily_summary[-7:], ensure_ascii=False)}\n"
            f"최근 발행 시간들: {json.dumps(publish_times, ensure_ascii=False)}\n\n"
            f"JSON 형식으로 응답해:\n"
            f'{{"best_times": [{{"day": "Monday", "times": ["09:00", "18:00"], "reason": "이유"}}], '
            f'"general_recommendation": "종합 추천", '
            f'"avoid_times": ["피해야할 시간대"]}}'
        )

        try:
            raw = await call_claude(prompt, timeout=120)
            result = _parse_json_response(raw)
            if isinstance(result, dict):
                result["account_id"] = str(account_id)
                result["platform"] = channel.channel_type
                return result
            return {
                "account_id": str(account_id),
                "platform": channel.channel_type,
                "best_times": [],
                "general_recommendation": raw,
                "avoid_times": [],
            }
        except Exception as e:
            logger.error("Best times AI generation failed: %s", e)
            return {
                "account_id": str(account_id),
                "platform": channel.channel_type,
                "best_times": [
                    {"day": "Weekdays", "times": ["09:00", "12:00", "18:00"], "reason": "일반적 권장 시간"},
                ],
                "general_recommendation": "AI 분석 실패 - 일반적 권장 시간을 표시합니다",
                "avoid_times": ["02:00-06:00"],
                "error": str(e),
            }
