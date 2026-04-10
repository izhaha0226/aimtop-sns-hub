"""
Analytics Service - SNS performance data collection and analysis.
"""
import json
import logging
import uuid
from datetime import date, timedelta

import httpx
from sqlalchemy import and_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytics import Analytics
from models.channel import ChannelConnection
from models.content import Content
from services.sns_oauth import decrypt_token

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

        # 플랫폼별 데이터 수집 (더미 제거 / 실패 시 보수 보완)
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

    async def _fetch_recent_snapshot(self, channel_connection_id: uuid.UUID) -> dict | None:
        """최근 7일치 데이터에서 보수 보완용 기준점을 구한다."""
        today = date.today()
        cutoff = today - timedelta(days=7)
        result = await self.db.execute(
            select(Analytics)
            .where(
                and_(
                    Analytics.channel_connection_id == channel_connection_id,
                    Analytics.date >= cutoff,
                    Analytics.date <= today,
                )
            )
            .order_by(desc(Analytics.date))
            .limit(1)
        )
        prev = result.scalar_one_or_none()

        if not prev:
            return None

        return {
            "followers": prev.followers,
            "following": prev.following,
            "posts_count": prev.posts_count,
            "impressions": prev.impressions,
            "reach": prev.reach,
            "engagement": prev.engagement,
            "clicks": prev.clicks,
            "saves": prev.saves,
            "shares": prev.shares,
            "platform_data": prev.platform_data or {},
        }

    def _normalize_metrics(self, metrics: dict, fallback: dict | None, status: str) -> dict:
        """플랫폼 수집 성공/실패 시 필드 보정 및 보수 보완."""
        if fallback:
            base = {
                "followers": fallback["followers"],
                "following": fallback["following"],
                "posts_count": fallback["posts_count"],
                "impressions": fallback["impressions"],
                "reach": fallback["reach"],
                "engagement": fallback["engagement"],
                "clicks": fallback["clicks"],
                "saves": fallback["saves"],
                "shares": fallback["shares"],
            }
        else:
            base = {"followers": 0, "following": 0, "posts_count": 0, "impressions": 0,
                    "reach": 0, "engagement": 0, "clicks": 0, "saves": 0, "shares": 0}

        if not metrics:
            metrics = {}

        for key in base:
            if key not in metrics:
                continue
            try:
                base[key] = int(metrics[key] or 0)
            except (TypeError, ValueError):
                pass

        base["raw"] = {
            "platform": "unknown",
            "status": status,
        }
        return base

    async def _fallback(self, channel: ChannelConnection, reason: str) -> dict:
        """연동 불가 시 최근 7일치 기준으로 보수 보완."""
        fallback = await self._fetch_recent_snapshot(channel.id)
        metrics = self._normalize_metrics({}, fallback, status="fallback_7days")
        metrics["raw"] = {
            "platform": channel.channel_type,
            "status": "fallback_7days",
            "reason": reason,
            "snapshot": bool(fallback),
            "fallback_source": "last_7_days",
            "fallback_to": None if not fallback else {
                "date": None,
                "note": "기존 데이터 기준 보존",
            },
        }
        if fallback and fallback.get("platform_data"):
            metrics["raw"]["snapshot_raw"] = fallback.get("platform_data")
        return metrics

    async def _fetch_platform_data(self, channel: ChannelConnection) -> dict:
        """플랫폼별 API에서 데이터 수집."""
        platform = channel.channel_type
        logger.info("Fetching analytics for %s channel: %s", platform, channel.account_name)

        access_token = decrypt_token(channel.access_token or "")
        if not access_token:
            return await self._fallback(channel, "No access token available")

        try:
            if platform == "instagram":
                return await self._fetch_instagram_data(channel, access_token)
            if platform == "youtube":
                return await self._fetch_youtube_data(channel, access_token)
            if platform == "x":
                return await self._fetch_x_data(channel, access_token)
            if platform == "blog":
                return await self._fallback(
                    channel, "Naver Blog API is not implemented in this scope"
                )

            return await self._fallback(channel, f"Unsupported platform: {platform}")
        except Exception as e:
            logger.warning("Analytics fetch failed for %s: %s", platform, e)
            return await self._fallback(channel, str(e))

    async def _fetch_instagram_data(self, channel: ChannelConnection, access_token: str) -> dict:
        base_url = "https://graph.facebook.com/v19.0"
        base = {}
        raw = {
            "platform": "instagram",
            "status": "fetched",
            "api_calls": [],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            # me endpoint
            me_resp = await client.get(
                f"{base_url}/me",
                params={
                    "fields": "id,username,followers_count,follows_count,media_count",
                    "access_token": access_token,
                },
            )
            if me_resp.status_code == 200:
                data = me_resp.json()
                base["followers"] = data.get("followers_count") or 0
                base["following"] = data.get("follows_count") or 0
                base["posts_count"] = data.get("media_count") or 0
                raw["api_calls"].append("me")
                raw["instagram_user_id"] = data.get("id")
                raw["instagram_username"] = data.get("username")
            else:
                return await self._fallback(channel, f"Instagram profile API failed: {me_resp.text}")

            # insights (optional)
            if data.get("id"):
                try:
                    insight_resp = await client.get(
                        f"{base_url}/{data['id']}/insights",
                        params={
                            "metric": "impressions,reach,engagement",
                            "period": "day",
                            "metric_type": "lifetime",
                            "access_token": access_token,
                        },
                    )
                    if insight_resp.status_code == 200:
                        for item in insight_resp.json().get("data", []):
                            if item.get("name") == "impressions":
                                vals = item.get("values", [])
                                if vals:
                                    base["impressions"] = int(vals[-1].get("value", 0))
                            elif item.get("name") == "reach":
                                vals = item.get("values", [])
                                if vals:
                                    base["reach"] = int(vals[-1].get("value", 0))
                            elif item.get("name") == "engagement":
                                vals = item.get("values", [])
                                if vals:
                                    base["engagement"] = int(vals[-1].get("value", 0))
                        raw["api_calls"].append("insights")
                except Exception as e:
                    logger.warning("Instagram insights fetch skipped: %s", e)

        fallback = await self._fetch_recent_snapshot(channel.id)
        result = self._normalize_metrics(base, fallback, status="fetched")
        result["raw"] = raw
        result["raw"]["note"] = "Instagram live fetch attempted; fallback from 최근 7일 used if not provided"
        return result

    async def _fetch_youtube_data(self, channel: ChannelConnection, access_token: str) -> dict:
        raw = {
            "platform": "youtube",
            "status": "fetched",
            "api_calls": ["channels.list"],
        }
        base = {}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "statistics", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                return await self._fallback(channel, f"YouTube API failed: {response.text}")

            items = response.json().get("items", [])
            if not items:
                return await self._fallback(channel, "YouTube API returned no channel items")

            stats = items[0].get("statistics", {})
            base["followers"] = int(stats.get("subscriberCount", 0) or 0)
            base["following"] = 0
            base["posts_count"] = int(stats.get("videoCount", 0) or 0)
            base["impressions"] = int(stats.get("viewCount", 0) or 0)
            base["reach"] = int(stats.get("viewCount", 0) or 0)
            base["engagement"] = int(
                (stats.get("viewCount", 0) or 0)
                if stats.get("viewCount") is not None
                else 0
            )

        fallback = await self._fetch_recent_snapshot(channel.id)
        result = self._normalize_metrics(base, fallback, status="fetched")
        result["raw"] = raw
        result["raw"]["statistics"] = {k: str(v) for k, v in stats.items()} if "stats" in locals() else {}
        result["raw"]["note"] = "YouTube live fetch attempted"
        return result

    async def _fetch_x_data(self, channel: ChannelConnection, access_token: str) -> dict:
        raw = {"platform": "x", "status": "fetched", "api_calls": ["users/me"]}
        base = {}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://api.twitter.com/2/users/me",
                params={
                    "user.fields": "public_metrics,created_at,description,username,name"
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                return await self._fallback(channel, f"X API failed: {response.text}")

            user = response.json().get("data", {})
            if not user:
                return await self._fallback(channel, "X API returned empty user")

            metrics = user.get("public_metrics", {})
            base["followers"] = int(metrics.get("followers_count", 0) or 0)
            base["following"] = int(metrics.get("following_count", 0) or 0)
            base["posts_count"] = int(metrics.get("tweet_count", 0) or 0)
            raw["user"] = {
                "id": user.get("id"),
                "username": user.get("username"),
            }

        fallback = await self._fetch_recent_snapshot(channel.id)
        result = self._normalize_metrics(base, fallback, status="fetched")
        result["raw"] = raw
        result["raw"]["note"] = "X live fetch attempted"
        return result

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
            "다음 SNS 계정의 최근 30일 성과 데이터를 분석해서 인사이트를 제공해줘.\n\n"
            f"채널: {channel_info}\n"
            f"요약: {json.dumps(summary, ensure_ascii=False)}\n"
            f"일별 데이터 (최근 7일): {json.dumps(daily[-7:], ensure_ascii=False)}\n\n"
            'JSON 형식으로 응답해:\n'
            '{"summary": "전체 요약", "strengths": ["강점1", "강점2"], "improvements": ["개선점1", "개선점2"], "recommendations": ["추천 액션1", "추천 액션2"], "predicted_trend": "향후 트렌드 예측"}'
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