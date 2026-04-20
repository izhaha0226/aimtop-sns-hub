from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import uuid

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.action_language_profile import ActionLanguageProfile
from models.benchmark_account import BenchmarkAccount
from models.benchmark_post import BenchmarkPost
from models.channel import ChannelConnection
from services.action_language_service import build_action_language_profile
from services.benchmark_scoring_service import calculate_benchmark_score
from services.sns_oauth import decrypt_token

HASHTAG_RE = re.compile(r"#\w+")
CTA_RE = re.compile(r"(저장|댓글|문의|신청|클릭|링크|팔로우|구독|DM)")


class BenchmarkCollectorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_accounts(self, client_id: uuid.UUID | None = None) -> list[BenchmarkAccount]:
        query = select(BenchmarkAccount).order_by(BenchmarkAccount.created_at.desc())
        if client_id:
            query = query.where(BenchmarkAccount.client_id == client_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_account(self, **kwargs) -> BenchmarkAccount:
        account = BenchmarkAccount(**kwargs)
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update_account(self, account: BenchmarkAccount, **kwargs) -> BenchmarkAccount:
        for field, value in kwargs.items():
            if value is not None:
                setattr(account, field, value)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_account(self, account_id: uuid.UUID) -> BenchmarkAccount | None:
        result = await self.db.execute(select(BenchmarkAccount).where(BenchmarkAccount.id == account_id))
        return result.scalar_one_or_none()

    async def refresh_account(self, account: BenchmarkAccount, top_k: int = 10, window_days: int = 30) -> dict:
        await self._clear_existing_posts(account.id)

        try:
            posts, status_payload = await self._collect_live_posts(account, top_k=top_k, window_days=window_days)
        except Exception as e:
            status_payload = {
                "status": "collector_error",
                "message": f"실수집 중 오류가 발생했습니다: {e}",
                "live_supported": False,
                "platform": account.platform,
            }
            posts = []

        if not posts:
            posts = self._build_placeholder_posts(account, top_k=top_k, window_days=window_days)
            status_payload = {
                **status_payload,
                "status": status_payload.get("status") or "manual_ingest_required",
                "message": status_payload.get("message") or "실채널 수집기를 아직 지원하지 않아 샘플 데이터로 대체했습니다.",
                "live_supported": False,
            }

        inserted = await self._insert_posts(account, posts, window_days=window_days)
        profile = await self.rebuild_action_language_profile(account.client_id, account.platform)
        return {
            **status_payload,
            "inserted": inserted,
            "profile_id": str(profile.id) if profile else None,
        }

    async def get_top_posts(self, client_id: uuid.UUID, platform: str, top_k: int = 10) -> list[BenchmarkPost]:
        result = await self.db.execute(
            select(BenchmarkPost)
            .where(BenchmarkPost.client_id == client_id, BenchmarkPost.platform == platform)
            .order_by(desc(BenchmarkPost.benchmark_score), desc(BenchmarkPost.view_count))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def rebuild_action_language_profile(self, client_id: uuid.UUID, platform: str) -> ActionLanguageProfile | None:
        posts = await self.get_top_posts(client_id, platform, top_k=20)
        if not posts:
            return None
        profile_data = build_action_language_profile(
            platform,
            [
                {
                    "content_text": p.content_text,
                    "hook_text": p.hook_text,
                    "cta_text": p.cta_text,
                }
                for p in posts
            ],
        )
        result = await self.db.execute(
            select(ActionLanguageProfile).where(
                ActionLanguageProfile.client_id == client_id,
                ActionLanguageProfile.platform == platform,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ActionLanguageProfile(
                client_id=client_id,
                platform=platform,
                source_scope="manual_benchmark",
            )
            self.db.add(row)
        row.top_hooks_json = profile_data["top_hooks"]
        row.top_ctas_json = profile_data["top_ctas"]
        row.tone_patterns_json = profile_data["tone_patterns"]
        row.format_patterns_json = profile_data["format_patterns"]
        row.recommended_prompt_rules = profile_data["recommended_prompt_rules"]
        row.profile_version = (row.profile_version or 0) + 1
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_action_language_profile(self, client_id: uuid.UUID, platform: str) -> ActionLanguageProfile | None:
        result = await self.db.execute(
            select(ActionLanguageProfile).where(
                ActionLanguageProfile.client_id == client_id,
                ActionLanguageProfile.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def _clear_existing_posts(self, benchmark_account_id: uuid.UUID) -> None:
        existing = await self.db.execute(select(BenchmarkPost).where(BenchmarkPost.benchmark_account_id == benchmark_account_id))
        for row in existing.scalars().all():
            await self.db.delete(row)
        await self.db.flush()

    async def _insert_posts(self, account: BenchmarkAccount, posts: list[dict], window_days: int) -> int:
        inserted = 0
        for item in posts:
            post = BenchmarkPost(
                benchmark_account_id=account.id,
                client_id=account.client_id,
                platform=account.platform,
                external_post_id=item.get("external_post_id"),
                post_url=item.get("post_url"),
                content_text=item.get("content_text"),
                hook_text=item.get("hook_text"),
                cta_text=item.get("cta_text"),
                hashtags_json=item.get("hashtags_json") or [],
                format_type=item.get("format_type"),
                view_count=int(item.get("view_count") or 0),
                like_count=int(item.get("like_count") or 0),
                comment_count=int(item.get("comment_count") or 0),
                share_count=int(item.get("share_count") or 0),
                save_count=int(item.get("save_count") or 0),
                engagement_rate=float(item.get("engagement_rate") or 0),
                raw_payload=item.get("raw_payload") or {},
                published_at=item.get("published_at"),
            )
            post.benchmark_score = calculate_benchmark_score(post, window_days=window_days)
            self.db.add(post)
            inserted += 1
        await self.db.commit()
        return inserted

    async def _collect_live_posts(self, account: BenchmarkAccount, top_k: int, window_days: int) -> tuple[list[dict], dict]:
        platform = account.platform.lower()
        source_channel = await self._get_source_channel(account.client_id, platform)
        if platform == "youtube":
            if not source_channel:
                return [], {
                    "status": "manual_ingest_required",
                    "message": "YouTube 실수집에는 이 클라이언트의 연결된 YouTube 채널 토큰이 필요합니다.",
                    "live_supported": False,
                    "platform": platform,
                }
            posts = await self._collect_youtube_posts(account, source_channel, top_k=top_k, window_days=window_days)
            return posts, {
                "status": "live_collected",
                "message": "YouTube 실데이터 수집 완료",
                "live_supported": True,
                "platform": platform,
            }
        if platform == "x":
            if not source_channel:
                return [], {
                    "status": "manual_ingest_required",
                    "message": "X 실수집에는 이 클라이언트의 연결된 X 채널 토큰이 필요합니다.",
                    "live_supported": False,
                    "platform": platform,
                }
            posts = await self._collect_x_posts(account, source_channel, top_k=top_k)
            return posts, {
                "status": "live_collected_proxy_views",
                "message": "X 공개 지표 기반 실수집 완료 (조회수는 공개 지표 프록시 추정)",
                "live_supported": True,
                "platform": platform,
            }
        return [], {
            "status": "manual_ingest_required",
            "message": f"{platform} 실수집기는 아직 미구현입니다.",
            "live_supported": False,
            "platform": platform,
        }

    async def _get_source_channel(self, client_id: uuid.UUID, platform: str) -> ChannelConnection | None:
        result = await self.db.execute(
            select(ChannelConnection)
            .where(
                ChannelConnection.client_id == client_id,
                ChannelConnection.channel_type == platform,
                ChannelConnection.is_connected.is_(True),
            )
            .order_by(ChannelConnection.updated_at.desc())
        )
        return result.scalars().first()

    async def _collect_youtube_posts(
        self,
        account: BenchmarkAccount,
        source_channel: ChannelConnection,
        top_k: int,
        window_days: int,
    ) -> list[dict]:
        access_token = decrypt_token(source_channel.access_token or "")
        if not access_token:
            raise RuntimeError("YouTube source token is missing")

        channel_id = await self._resolve_youtube_channel_id(account.handle, access_token, account.metadata_json or {})
        if not channel_id:
            raise RuntimeError("YouTube 채널 ID를 찾지 못했습니다")

        published_after = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat().replace("+00:00", "Z")
        max_results = max(5, min(top_k * 2, 25))
        async with httpx.AsyncClient(timeout=30) as client:
            search_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "order": "viewCount",
                    "type": "video",
                    "publishedAfter": published_after,
                    "maxResults": max_results,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            video_ids = [item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")]
            if not video_ids:
                return []

            videos_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "maxResults": len(video_ids),
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            videos_resp.raise_for_status()
            videos = videos_resp.json().get("items", [])

        rows: list[dict] = []
        for video in videos:
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            title = (snippet.get("title") or "").strip()
            description = (snippet.get("description") or "").strip()
            text = f"{title}\n{description}".strip()
            rows.append(
                {
                    "external_post_id": video.get("id"),
                    "post_url": f"https://www.youtube.com/watch?v={video.get('id')}",
                    "content_text": text,
                    "hook_text": title,
                    "cta_text": self._extract_cta_text(text),
                    "hashtags_json": self._extract_hashtags(text),
                    "format_type": self._detect_youtube_format(snippet),
                    "view_count": int(stats.get("viewCount", 0) or 0),
                    "like_count": int(stats.get("likeCount", 0) or 0),
                    "comment_count": int(stats.get("commentCount", 0) or 0),
                    "share_count": 0,
                    "save_count": 0,
                    "engagement_rate": self._calc_engagement_rate(
                        views=int(stats.get("viewCount", 0) or 0),
                        likes=int(stats.get("likeCount", 0) or 0),
                        comments=int(stats.get("commentCount", 0) or 0),
                    ),
                    "published_at": self._parse_dt(snippet.get("publishedAt")),
                    "raw_payload": {
                        "source": "youtube_api_live",
                        "channel_id": channel_id,
                        "statistics": stats,
                        "view_metric": "actual",
                    },
                }
            )

        rows.sort(key=lambda item: (item.get("view_count", 0), item.get("engagement_rate", 0)), reverse=True)
        return rows[:top_k]

    async def _resolve_youtube_channel_id(self, handle: str, access_token: str, metadata: dict) -> str | None:
        if metadata.get("channel_id"):
            return str(metadata["channel_id"])
        normalized = handle.strip().lstrip("@")
        async with httpx.AsyncClient(timeout=30) as client:
            direct_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "id", "forHandle": normalized, "maxResults": 1},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if direct_resp.status_code == 200:
                items = direct_resp.json().get("items", [])
                if items:
                    return items[0].get("id")

            search_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": normalized, "type": "channel", "maxResults": 1},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            if items:
                return items[0].get("snippet", {}).get("channelId") or items[0].get("id", {}).get("channelId")
        return None

    async def _collect_x_posts(self, account: BenchmarkAccount, source_channel: ChannelConnection, top_k: int) -> list[dict]:
        access_token = decrypt_token(source_channel.access_token or "")
        if not access_token:
            raise RuntimeError("X source token is missing")

        username = account.handle.strip().lstrip("@")
        async with httpx.AsyncClient(timeout=30) as client:
            user_resp = await client.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                params={"user.fields": "public_metrics,description,created_at,verified"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user = user_resp.json().get("data", {})
            user_id = user.get("id")
            if not user_id:
                return []

            tweets_resp = await client.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                params={
                    "exclude": "retweets,replies",
                    "max_results": max(5, min(top_k * 2, 20)),
                    "tweet.fields": "created_at,public_metrics,entities",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            tweets_resp.raise_for_status()
            tweets = tweets_resp.json().get("data", [])

        rows: list[dict] = []
        for tweet in tweets:
            text = (tweet.get("text") or "").strip()
            metrics = tweet.get("public_metrics", {})
            like_count = int(metrics.get("like_count", 0) or 0)
            comment_count = int(metrics.get("reply_count", 0) or 0)
            share_count = int(metrics.get("retweet_count", 0) or 0)
            quote_count = int(metrics.get("quote_count", 0) or 0)
            proxy_views = self._estimate_x_views(like_count, comment_count, share_count, quote_count)
            rows.append(
                {
                    "external_post_id": tweet.get("id"),
                    "post_url": f"https://x.com/{username}/status/{tweet.get('id')}",
                    "content_text": text,
                    "hook_text": self._first_line(text),
                    "cta_text": self._extract_cta_text(text),
                    "hashtags_json": [f"#{item.get('tag')}" for item in ((tweet.get("entities") or {}).get("hashtags") or []) if item.get("tag")],
                    "format_type": "text",
                    "view_count": proxy_views,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "share_count": share_count + quote_count,
                    "save_count": 0,
                    "engagement_rate": self._calc_engagement_rate(
                        views=proxy_views,
                        likes=like_count,
                        comments=comment_count,
                        shares=share_count + quote_count,
                    ),
                    "published_at": self._parse_dt(tweet.get("created_at")),
                    "raw_payload": {
                        "source": "x_api_live",
                        "user_id": user_id,
                        "public_metrics": metrics,
                        "view_metric": "proxy_from_public_metrics",
                    },
                }
            )

        rows.sort(key=lambda item: (item.get("view_count", 0), item.get("engagement_rate", 0)), reverse=True)
        return rows[:top_k]

    def _build_placeholder_posts(self, account: BenchmarkAccount, top_k: int, window_days: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        posts: list[dict] = []
        for idx in range(max(3, min(top_k, 10))):
            text = (
                f"{account.handle} benchmark sample {idx+1}\n"
                f"지금 확인해야 하는 핵심 포인트 {idx+1}가지\n"
                f"저장하고 댓글로 의견 남겨주세요 #{account.platform} #{idx+1}"
            )
            posts.append(
                {
                    "external_post_id": f"sample-{idx+1}",
                    "post_url": f"https://example.com/{account.platform}/{account.handle.strip('@')}/{idx+1}",
                    "content_text": text,
                    "hook_text": f"지금 확인해야 하는 핵심 포인트 {idx+1}가지",
                    "cta_text": "저장하고 댓글로 의견 남겨주세요",
                    "hashtags_json": [f"#{account.platform}", f"#{idx+1}"],
                    "format_type": "text",
                    "view_count": max(1000, 10000 - (idx * 700)),
                    "like_count": max(100, 1200 - (idx * 80)),
                    "comment_count": max(10, 150 - (idx * 12)),
                    "share_count": max(5, 80 - (idx * 6)),
                    "save_count": max(5, 60 - (idx * 4)),
                    "engagement_rate": max(0.5, 8.0 - (idx * 0.55)),
                    "published_at": now - timedelta(days=idx * 2),
                    "raw_payload": {"source": "placeholder_benchmark_pipeline", "live_supported": False, "window_days": window_days},
                }
            )
        return posts

    def _extract_hashtags(self, text: str) -> list[str]:
        return HASHTAG_RE.findall(text or "")[:20]

    def _first_line(self, text: str) -> str:
        return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""

    def _extract_cta_text(self, text: str) -> str:
        if not text:
            return ""
        for line in reversed([line.strip() for line in text.splitlines() if line.strip()]):
            if CTA_RE.search(line):
                return line
        match = CTA_RE.search(text)
        return match.group(0) if match else ""

    def _detect_youtube_format(self, snippet: dict) -> str:
        title = (snippet.get("title") or "").lower()
        if "#shorts" in title:
            return "shorts"
        return "video"

    def _estimate_x_views(self, likes: int, comments: int, shares: int, quotes: int) -> int:
        proxy = (likes * 28) + (comments * 45) + (shares * 35) + (quotes * 40)
        return max(proxy, likes + comments + shares + quotes)

    def _calc_engagement_rate(self, views: int, likes: int, comments: int, shares: int = 0, saves: int = 0) -> float:
        if views <= 0:
            return 0.0
        return round(((likes + comments + shares + saves) / views) * 100, 4)

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
