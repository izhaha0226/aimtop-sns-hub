"""
댓글 관리 서비스
- SNS API에서 댓글 동기화
- 답글 전송
- 숨기기
- 감성 분석 (Claude CLI)
"""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from models.channel import ChannelConnection
from models.content import Content
from services.sns_oauth import decrypt_token
from services.ai_service import call_claude

logger = logging.getLogger(__name__)


class CommentService:
    """댓글 관리 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_comments(self, account_id: uuid.UUID) -> int:
        """
        SNS API에서 댓글을 가져와서 DB에 저장
        account_id = channel_connection_id
        Returns: 새로 동기화된 댓글 수
        """
        # 채널 연결 정보 조회
        result = await self.db.execute(
            select(ChannelConnection).where(ChannelConnection.id == account_id)
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise ValueError("채널 연결을 찾을 수 없습니다")

        platform = channel.channel_type
        access_token = decrypt_token(channel.access_token or "")

        # 해당 채널의 발행된 콘텐츠 조회
        contents_result = await self.db.execute(
            select(Content).where(
                Content.channel_connection_id == account_id,
                Content.status == "published",
                Content.platform_post_id.isnot(None),
            )
        )
        contents = contents_result.scalars().all()

        new_count = 0
        for content in contents:
            try:
                comments = await self._fetch_comments_from_platform(
                    platform, access_token, content.platform_post_id, channel
                )
                for comment_data in comments:
                    # 이미 동기화된 댓글은 스킵
                    existing = await self.db.execute(
                        select(Comment).where(
                            Comment.platform_comment_id == comment_data["id"]
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    comment = Comment(
                        content_id=content.id,
                        channel_connection_id=account_id,
                        platform_comment_id=comment_data["id"],
                        author_name=comment_data.get("author_name"),
                        author_avatar_url=comment_data.get("author_avatar_url"),
                        text=comment_data.get("text"),
                    )
                    self.db.add(comment)
                    new_count += 1

            except Exception as e:
                logger.warning(
                    f"Failed to sync comments for content {content.id}: {e}"
                )
                continue

        if new_count > 0:
            await self.db.commit()

        logger.info(f"Synced {new_count} new comments for account {account_id}")
        return new_count

    async def _fetch_comments_from_platform(
        self, platform: str, access_token: str, post_id: str, channel
    ) -> list[dict]:
        """플랫폼별 댓글 API 호출"""
        if platform == "instagram":
            return await self._fetch_instagram_comments(access_token, post_id)
        elif platform == "youtube":
            return await self._fetch_youtube_comments(access_token, post_id)
        # blog, x 등은 추가 구현
        return []

    async def _fetch_instagram_comments(
        self, access_token: str, media_id: str
    ) -> list[dict]:
        """Instagram Graph API - 미디어 댓글 조회"""
        base_url = "https://graph.facebook.com/v19.0"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{base_url}/{media_id}/comments",
                params={
                    "fields": "id,text,username,timestamp",
                    "access_token": access_token,
                },
            )
            if resp.status_code != 200:
                logger.error(f"Instagram comments fetch failed: {resp.text}")
                return []

            data = resp.json().get("data", [])
            return [
                {
                    "id": item["id"],
                    "text": item.get("text", ""),
                    "author_name": item.get("username", ""),
                    "author_avatar_url": None,
                }
                for item in data
            ]

    async def _fetch_youtube_comments(
        self, access_token: str, video_id: str
    ) -> list[dict]:
        """YouTube Data API v3 - 댓글 스레드 조회"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": 100,
                    "order": "time",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                logger.error(f"YouTube comments fetch failed: {resp.text}")
                return []

            items = resp.json().get("items", [])
            result = []
            for item in items:
                snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                result.append({
                    "id": item["id"],
                    "text": snippet.get("textDisplay", ""),
                    "author_name": snippet.get("authorDisplayName", ""),
                    "author_avatar_url": snippet.get("authorProfileImageUrl"),
                })
            return result

    async def reply_comment(self, comment_id: uuid.UUID, text: str) -> dict:
        """SNS API로 답글 전송"""
        result = await self.db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise ValueError("댓글을 찾을 수 없습니다")

        if not comment.channel_connection_id:
            raise ValueError("채널 연결 정보가 없습니다")

        # 채널 정보 조회
        ch_result = await self.db.execute(
            select(ChannelConnection).where(
                ChannelConnection.id == comment.channel_connection_id
            )
        )
        channel = ch_result.scalar_one_or_none()
        if not channel:
            raise ValueError("채널 연결을 찾을 수 없습니다")

        access_token = decrypt_token(channel.access_token or "")
        platform = channel.channel_type

        # 플랫폼별 답글 전송
        reply_result = await self._send_reply(
            platform, access_token, comment.platform_comment_id, text
        )

        # DB 업데이트
        comment.replied_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "comment_id": str(comment_id),
            "reply_text": text,
            "replied_at": comment.replied_at.isoformat(),
            **reply_result,
        }

    async def _send_reply(
        self, platform: str, access_token: str, platform_comment_id: str, text: str
    ) -> dict:
        """플랫폼별 답글 API 호출"""
        if platform == "instagram":
            return await self._reply_instagram(access_token, platform_comment_id, text)
        elif platform == "youtube":
            return await self._reply_youtube(access_token, platform_comment_id, text)
        return {"status": "unsupported_platform"}

    async def _reply_instagram(
        self, access_token: str, comment_id: str, text: str
    ) -> dict:
        """Instagram 답글"""
        base_url = "https://graph.facebook.com/v19.0"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/{comment_id}/replies",
                data={"message": text, "access_token": access_token},
            )
            if resp.status_code != 200:
                raise ValueError(f"Instagram reply failed: {resp.text}")
            return {"platform_reply_id": resp.json().get("id")}

    async def _reply_youtube(
        self, access_token: str, parent_id: str, text: str
    ) -> dict:
        """YouTube 답글"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://www.googleapis.com/youtube/v3/comments",
                params={"part": "snippet"},
                json={
                    "snippet": {
                        "parentId": parent_id,
                        "textOriginal": text,
                    }
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code not in (200, 201):
                raise ValueError(f"YouTube reply failed: {resp.text}")
            return {"platform_reply_id": resp.json().get("id")}

    async def hide_comment(self, comment_id: uuid.UUID) -> bool:
        """댓글 숨기기"""
        result = await self.db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return False

        comment.is_hidden = True
        await self.db.commit()

        # 플랫폼에서도 숨기기 시도 (실패해도 DB는 유지)
        if comment.channel_connection_id and comment.platform_comment_id:
            try:
                ch_result = await self.db.execute(
                    select(ChannelConnection).where(
                        ChannelConnection.id == comment.channel_connection_id
                    )
                )
                channel = ch_result.scalar_one_or_none()
                if channel:
                    access_token = decrypt_token(channel.access_token or "")
                    await self._hide_on_platform(
                        channel.channel_type, access_token, comment.platform_comment_id
                    )
            except Exception as e:
                logger.warning(f"Failed to hide comment on platform: {e}")

        return True

    async def _hide_on_platform(
        self, platform: str, access_token: str, platform_comment_id: str
    ):
        """플랫폼에서 댓글 숨기기"""
        if platform == "instagram":
            base_url = "https://graph.facebook.com/v19.0"
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(
                    f"{base_url}/{platform_comment_id}",
                    data={"hide": "true", "access_token": access_token},
                )

    async def analyze_sentiment(self, text: str) -> str:
        """
        Claude CLI로 감성 분석
        Returns: positive / neutral / negative
        """
        prompt = (
            "다음 SNS 댓글의 감성을 분석해줘. "
            "반드시 positive, neutral, negative 중 하나의 단어만 출력해.\n\n"
            f"댓글: {text}"
        )
        try:
            result = await call_claude(prompt, timeout=30)
            sentiment = result.strip().lower()
            if sentiment in ("positive", "neutral", "negative"):
                return sentiment
            # 결과에서 키워드 추출
            for s in ("positive", "neutral", "negative"):
                if s in sentiment:
                    return s
            return "neutral"
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return "neutral"

    async def get_comments(
        self,
        account_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        include_hidden: bool = False,
    ) -> dict:
        """댓글 목록 (페이지네이션)"""
        query = select(Comment).where(
            Comment.channel_connection_id == account_id
        )
        if not include_hidden:
            query = query.where(Comment.is_hidden == False)

        # 전체 개수
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = query.order_by(Comment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
