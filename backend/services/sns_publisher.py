"""
SNS 플랫폼별 발행 엔진
Instagram Graph API, YouTube Data API v3, Naver Blog API, X API v2
"""

import logging
from datetime import datetime, timezone

import httpx

from services.sns_oauth import decrypt_token

logger = logging.getLogger(__name__)


class SNSPublisher:
    """SNS 플랫폼별 콘텐츠 발행"""

    async def publish(self, account, content) -> dict:
        """
        계정 플랫폼에 맞게 콘텐츠 발행
        account: ChannelConnection 모델 인스턴스
        content: Content 모델 인스턴스
        Returns: {platform_post_id, url, published_at}
        """
        platform = account.channel_type
        if platform == "instagram":
            return await self._publish_instagram(account, content)
        elif platform == "youtube":
            return await self._publish_youtube(account, content)
        elif platform == "blog":
            return await self._publish_blog(account, content)
        elif platform == "x":
            return await self._publish_x(account, content)
        raise ValueError(f"Unsupported platform: {platform}")

    async def _publish_instagram(self, account, content) -> dict:
        """
        Instagram Graph API를 통한 미디어 발행
        1단계: 컨테이너 생성 (이미지 URL + 캡션)
        2단계: 미디어 발행
        """
        access_token = decrypt_token(account.access_token)
        ig_user_id = (account.extra_data or {}).get("instagram_user_id", account.account_id)
        base_url = "https://graph.facebook.com/v19.0"

        caption = self._build_caption(content)
        media_url = (content.media_urls or [None])[0]

        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: Create media container
            container_params = {
                "access_token": access_token,
                "caption": caption,
            }
            if media_url:
                container_params["image_url"] = media_url

            resp = await client.post(
                f"{base_url}/{ig_user_id}/media",
                data=container_params,
            )
            if resp.status_code != 200:
                logger.error(f"Instagram container creation failed: {resp.text}")
                raise ValueError(f"Instagram container failed: {resp.text}")

            container_id = resp.json()["id"]
            logger.info(f"Instagram container created: {container_id}")

            # Step 2: Publish the container
            resp = await client.post(
                f"{base_url}/{ig_user_id}/media_publish",
                data={
                    "access_token": access_token,
                    "creation_id": container_id,
                },
            )
            if resp.status_code != 200:
                logger.error(f"Instagram publish failed: {resp.text}")
                raise ValueError(f"Instagram publish failed: {resp.text}")

            post_id = resp.json()["id"]

            # Get permalink
            resp = await client.get(
                f"{base_url}/{post_id}",
                params={"fields": "permalink", "access_token": access_token},
            )
            permalink = resp.json().get("permalink", f"https://www.instagram.com/p/{post_id}/")

            logger.info(f"Instagram published: {post_id}")
            return {
                "platform_post_id": post_id,
                "url": permalink,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _publish_youtube(self, account, content) -> dict:
        """
        YouTube Data API v3 - Community Post (텍스트)
        영상 업로드의 경우 resumable upload 필요 (별도 확장)
        """
        access_token = decrypt_token(account.access_token)
        caption = self._build_caption(content)

        async with httpx.AsyncClient(timeout=60) as client:
            # YouTube Community Post via activities API (제한적)
            # 실제로는 YouTube Studio / resumable upload 사용
            # 여기서는 텍스트 기반 community post 시뮬레이션

            # Video upload (snippet + status)
            video_metadata = {
                "snippet": {
                    "title": content.title or "Untitled",
                    "description": caption,
                    "tags": content.hashtags or [],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            resp = await client.post(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet,status"},
                json=video_metadata,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code not in (200, 201):
                logger.error(f"YouTube publish failed: {resp.text}")
                raise ValueError(f"YouTube publish failed: {resp.text}")

            data = resp.json()
            video_id = data.get("id", "")
            url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(f"YouTube published: {video_id}")
            return {
                "platform_post_id": video_id,
                "url": url,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _publish_blog(self, account, content) -> dict:
        """
        Naver Blog Write API
        POST https://openapi.naver.com/blog/writePost.json
        """
        access_token = decrypt_token(account.access_token)
        title = content.title or "Untitled"
        body_text = content.text or ""

        # 해시태그를 본문 하단에 추가
        if content.hashtags:
            tags_str = " ".join(f"#{tag}" for tag in content.hashtags)
            body_text += f"\n\n{tags_str}"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://openapi.naver.com/blog/writePost.json",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                data={
                    "title": title,
                    "contents": body_text,
                },
            )
            if resp.status_code != 200:
                logger.error(f"Naver Blog publish failed: {resp.text}")
                raise ValueError(f"Naver Blog publish failed: {resp.text}")

            data = resp.json()
            blog_url = data.get("message", {}).get("result", {}).get("url", "")
            post_id = data.get("message", {}).get("result", {}).get("logNo", "")

            logger.info(f"Naver Blog published: {post_id}")
            return {
                "platform_post_id": str(post_id),
                "url": blog_url,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _publish_x(self, account, content) -> dict:
        """
        X API v2 - 트윗 작성
        POST https://api.twitter.com/2/tweets
        """
        access_token = decrypt_token(account.access_token)
        tweet_text = self._build_caption(content, max_length=280)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.twitter.com/2/tweets",
                json={"text": tweet_text},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 201):
                logger.error(f"X publish failed: {resp.text}")
                raise ValueError(f"X publish failed: {resp.text}")

            data = resp.json()
            tweet_id = data.get("data", {}).get("id", "")
            url = f"https://x.com/i/status/{tweet_id}"

            logger.info(f"X published: {tweet_id}")
            return {
                "platform_post_id": tweet_id,
                "url": url,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def _build_caption(content, max_length: int | None = None) -> str:
        """콘텐츠에서 캡션 텍스트 생성"""
        parts = []
        if content.title:
            parts.append(content.title)
        if content.text:
            parts.append(content.text)
        if content.hashtags:
            tags_str = " ".join(f"#{tag}" for tag in content.hashtags)
            parts.append(tags_str)
        caption = "\n\n".join(parts)
        if max_length and len(caption) > max_length:
            caption = caption[: max_length - 3] + "..."
        return caption
