"""
SNS 플랫폼별 발행 엔진
Instagram Graph API, Threads API, YouTube Data API v3, Naver Blog API, X API v2
"""

import logging
from datetime import datetime, timezone

import httpx

from services.sns_oauth import decrypt_token

logger = logging.getLogger(__name__)


class SNSPublisher:
    """SNS 플랫폼별 콘텐츠 발행"""

    SUPPORTED_PLATFORMS = {"instagram", "threads", "youtube", "blog", "x", "facebook", "linkedin"}

    @classmethod
    def is_supported_platform(cls, platform: str) -> bool:
        return platform in cls.SUPPORTED_PLATFORMS

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
        elif platform == "threads":
            return await self._publish_threads(account, content)
        elif platform == "youtube":
            return await self._publish_youtube(account, content)
        elif platform == "blog":
            return await self._publish_blog(account, content)
        elif platform == "x":
            return await self._publish_x(account, content)
        elif platform == "facebook":
            return await self._publish_facebook(account, content)
        elif platform == "linkedin":
            return await self._publish_linkedin(account, content)
        raise ValueError(f"Unsupported platform: {platform}")

    async def _publish_instagram(self, account, content) -> dict:
        """
        Instagram Graph API를 통한 미디어 발행
        1단계: 컨테이너 생성 (이미지 URL + 캡션)
        2단계: 미디어 발행
        """
        access_token = decrypt_token(account.access_token)
        if not access_token:
            raise ValueError("Instagram access token이 없어 재연동이 필요합니다")

        extra_data = account.extra_data if isinstance(account.extra_data, dict) else {}
        ig_user_id = extra_data.get("instagram_user_id") or account.account_id
        if not ig_user_id:
            raise ValueError(
                "Instagram 발행 계정 ID가 없어 자동 발행할 수 없습니다. "
                "현재 연결은 Meta 최소 권한 연결 상태이므로 Instagram Graph API 발행용 "
                "instagram_business_account ID와 instagram_content_publish 권한을 준비한 뒤 재연동해야 합니다."
            )

        base_url = "https://graph.facebook.com/v19.0"

        caption = self._build_caption(content)
        media_url = (content.media_urls or [None])[0]
        if not media_url:
            raise ValueError("Instagram 자동 발행에는 공개 접근 가능한 이미지 URL이 필요합니다")

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

    async def _publish_threads(self, account, content) -> dict:
        """
        Threads API를 통한 텍스트/단일 이미지 발행
        1단계: 컨테이너 생성
        2단계: 컨테이너 발행
        """
        access_token = decrypt_token(account.access_token)
        if not access_token:
            raise ValueError("Threads access token is missing")

        threads_user_id = self._resolve_threads_user_id(account)
        if not threads_user_id:
            raise ValueError("Threads user id를 찾을 수 없습니다")

        text = self._build_caption(content)
        media_url = (content.media_urls or [None])[0]
        base_url = "https://graph.threads.net/v1.0"
        create_params = {
            "access_token": access_token,
            "text": text,
            "media_type": "IMAGE" if media_url else "TEXT",
        }
        if media_url:
            create_params["image_url"] = media_url

        async with httpx.AsyncClient(timeout=60) as client:
            create_resp = await client.post(
                f"{base_url}/{threads_user_id}/threads",
                data=create_params,
            )
            if create_resp.status_code not in (200, 201):
                logger.error("Threads container creation failed: %s", create_resp.text)
                raise ValueError(f"Threads container failed: {create_resp.text}")

            creation_id = (create_resp.json() or {}).get("id")
            if not creation_id:
                raise ValueError(f"Threads creation id missing: {create_resp.text}")

            publish_resp = await client.post(
                f"{base_url}/{threads_user_id}/threads_publish",
                data={
                    "access_token": access_token,
                    "creation_id": creation_id,
                },
            )
            if publish_resp.status_code not in (200, 201):
                logger.error("Threads publish failed: %s", publish_resp.text)
                raise ValueError(f"Threads publish failed: {publish_resp.text}")

            post_id = (publish_resp.json() or {}).get("id")
            if not post_id:
                raise ValueError(f"Threads post id missing: {publish_resp.text}")

            permalink = None
            permalink_resp = await client.get(
                f"{base_url}/{post_id}",
                params={
                    "fields": "permalink",
                    "access_token": access_token,
                },
            )
            if permalink_resp.status_code == 200:
                permalink = (permalink_resp.json() or {}).get("permalink")

            if not permalink:
                username = self._resolve_threads_username(account)
                if username:
                    permalink = f"https://www.threads.net/@{username}/post/{post_id}"

            logger.info("Threads published: %s", post_id)
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

    async def _publish_facebook(self, account, content) -> dict:
        """
        Facebook Page Graph API 발행.
        - 이미지가 있으면 /{page-id}/photos
        - 텍스트만 있으면 /{page-id}/feed
        """
        access_token = decrypt_token(account.access_token)
        if not access_token:
            raise ValueError("Facebook access token이 없어 재연동이 필요합니다")

        page_id = self._resolve_facebook_page_id(account)
        if not page_id:
            raise ValueError("Facebook 페이지 ID가 없어 자동 발행할 수 없습니다. 페이지 권한을 준비한 뒤 재연동해야 합니다")

        page_token = self._resolve_facebook_page_token(account) or access_token
        caption = self._build_caption(content)
        media_url = (content.media_urls or [None])[0]
        base_url = "https://graph.facebook.com/v19.0"

        async with httpx.AsyncClient(timeout=60) as client:
            if media_url:
                resp = await client.post(
                    f"{base_url}/{page_id}/photos",
                    data={
                        "access_token": page_token,
                        "url": media_url,
                        "caption": caption,
                        "published": "true",
                    },
                )
            else:
                resp = await client.post(
                    f"{base_url}/{page_id}/feed",
                    data={
                        "access_token": page_token,
                        "message": caption,
                    },
                )

            if resp.status_code not in (200, 201):
                logger.error("Facebook publish failed: %s", resp.text)
                raise ValueError(f"Facebook publish failed: {resp.text}")

            data = resp.json() or {}
            post_id = data.get("post_id") or data.get("id")
            if not post_id:
                raise ValueError(f"Facebook post id missing: {resp.text}")

            logger.info("Facebook published: %s", post_id)
            return {
                "platform_post_id": post_id,
                "url": f"https://www.facebook.com/{post_id}",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _publish_linkedin(self, account, content) -> dict:
        """LinkedIn Posts API를 통한 개인/조직 텍스트 발행."""
        access_token = decrypt_token(account.access_token)
        if not access_token:
            raise ValueError("LinkedIn access token이 없어 재연동이 필요합니다")

        author_urn = self._resolve_linkedin_author_urn(account)
        if not author_urn:
            raise ValueError("LinkedIn 작성자 ID가 없어 자동 발행할 수 없습니다. LinkedIn 계정 정보를 재연동해야 합니다")

        commentary = self._build_caption(content)
        media_urls = [url for url in (content.media_urls or []) if url]
        if media_urls:
            commentary = f"{commentary}\n\n" + "\n".join(media_urls)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.linkedin.com/rest/posts",
                json={
                    "author": author_urn,
                    "commentary": commentary,
                    "visibility": "PUBLIC",
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "lifecycleState": "PUBLISHED",
                    "isReshareDisabledByAuthor": False,
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Linkedin-Version": "202405",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            if resp.status_code not in (200, 201):
                logger.error("LinkedIn publish failed: %s", resp.text)
                raise ValueError(f"LinkedIn publish failed: {resp.text}")

            data = resp.json() or {}
            post_id = data.get("id") or getattr(resp, "headers", {}).get("x-restli-id")
            if not post_id:
                raise ValueError(f"LinkedIn post id missing: {resp.text}")

            logger.info("LinkedIn published: %s", post_id)
            return {
                "platform_post_id": post_id,
                "url": f"https://www.linkedin.com/feed/update/{post_id}",
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

    @staticmethod
    def _resolve_threads_user_id(account) -> str | None:
        extra = account.extra_data or {}
        return extra.get("id") or extra.get("threads_user_id") or account.account_id

    @staticmethod
    def _resolve_threads_username(account) -> str | None:
        extra = account.extra_data or {}
        username = extra.get("username") or account.account_name
        if not username:
            return None
        return str(username).lstrip("@")

    @staticmethod
    def _resolve_facebook_page_id(account) -> str | None:
        extra = account.extra_data if isinstance(account.extra_data, dict) else {}
        page_id = extra.get("page_id") or account.account_id
        if page_id:
            return str(page_id)
        pages = extra.get("pages") if isinstance(extra.get("pages"), list) else []
        page = pages[0] if pages else {}
        return str(page.get("id")) if page.get("id") else None

    @staticmethod
    def _resolve_facebook_page_token(account) -> str | None:
        extra = account.extra_data if isinstance(account.extra_data, dict) else {}
        direct = extra.get("page_access_token")
        if direct:
            return str(direct)
        page_id = SNSPublisher._resolve_facebook_page_id(account)
        pages = extra.get("pages") if isinstance(extra.get("pages"), list) else []
        for page in pages:
            if not isinstance(page, dict):
                continue
            if page_id and str(page.get("id")) != page_id:
                continue
            token = page.get("access_token")
            if token:
                return str(token)
        return None

    @staticmethod
    def _resolve_linkedin_author_urn(account) -> str | None:
        extra = account.extra_data if isinstance(account.extra_data, dict) else {}
        explicit = extra.get("author_urn") or extra.get("linkedin_author_urn")
        if explicit:
            return str(explicit)
        organization_id = extra.get("organization_id") or extra.get("linkedin_organization_id")
        if organization_id:
            return f"urn:li:organization:{organization_id}"
        person_id = extra.get("person_id") or extra.get("sub") or account.account_id
        if person_id:
            person_id = str(person_id)
            if person_id.startswith("urn:li:"):
                return person_id
            return f"urn:li:person:{person_id}"
        return None
