"""
SNS OAuth2 플로우 관리
플랫폼별 OAuth URL 생성, 코드 교환, 토큰 갱신
"""

import secrets
import logging
import hashlib
import base64
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

from core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet | None:
    """토큰 암호화/복호화용 Fernet 인스턴스"""
    if settings.TOKEN_ENCRYPT_KEY:
        return Fernet(settings.TOKEN_ENCRYPT_KEY.encode())
    return None


def encrypt_token(token: str) -> str:
    """토큰 암호화 (TOKEN_ENCRYPT_KEY 미설정 시 평문 반환)"""
    f = _get_fernet()
    if f and token:
        return f.encrypt(token.encode()).decode()
    return token


def decrypt_token(token: str) -> str:
    """토큰 복호화 (TOKEN_ENCRYPT_KEY 미설정 시 평문 반환)"""
    f = _get_fernet()
    if f and token:
        try:
            return f.decrypt(token.encode()).decode()
        except Exception:
            return token
    return token


def _build_code_verifier() -> str:
    """PKCE code_verifier 생성."""
    return secrets.token_urlsafe(64)


def _build_code_challenge(code_verifier: str) -> str:
    """code_verifier -> S256 challenge (base64url without padding)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# ---------- 플랫폼별 OAuth 설정 ----------

PLATFORM_CONFIGS = {
    "instagram": {
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "scopes": "instagram_basic,instagram_content_publish,pages_read_engagement,pages_show_list",
    },
    "facebook": {
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "scopes": "pages_show_list,pages_read_engagement,pages_manage_posts,pages_manage_metadata",
    },
    "threads": {
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "scopes": "instagram_basic,threads_basic,threads_content_publish,pages_show_list",
    },
    "youtube": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
    },
    "x": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": "tweet.read tweet.write users.read offline.access",
    },
    "blog": {
        "auth_url": "https://nid.naver.com/oauth2.0/authorize",
        "token_url": "https://nid.naver.com/oauth2.0/token",
        "scopes": "blog",
    },
    "kakao": {
        "auth_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "scopes": "profile_nickname,talk_message",
    },
    "tiktok": {
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": "user.info.basic,video.publish",
    },
    "linkedin": {
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": "openid profile w_member_social email",
    },
}


def _get_client_credentials(platform: str) -> tuple[str, str]:
    """플랫폼별 client_id / client_secret 반환"""
    meta_id = settings.META_APP_ID or settings.INSTAGRAM_APP_ID
    meta_secret = settings.META_APP_SECRET or settings.INSTAGRAM_APP_SECRET
    mapping = {
        "instagram": (meta_id, meta_secret),
        "facebook": (meta_id, meta_secret),
        "threads": (meta_id, meta_secret),
        "youtube": (settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET),
        "x": (settings.X_CLIENT_ID, settings.X_CLIENT_SECRET),
        "blog": (settings.NAVER_CLIENT_ID, settings.NAVER_CLIENT_SECRET),
        "kakao": (settings.KAKAO_CLIENT_ID, settings.KAKAO_CLIENT_SECRET),
        "tiktok": (settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET),
        "linkedin": (settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET),
    }
    creds = mapping.get(platform)
    if not creds:
        raise ValueError(f"Unsupported platform: {platform}")
    return creds


class SNSOAuth:
    """SNS OAuth2 플로우 관리 클래스"""

    _x_verifier_by_state: dict[str, str] = {}

    def get_auth_url(self, platform: str, redirect_uri: str, state: str | None = None) -> str:
        """플랫폼별 OAuth 인증 URL 생성"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        client_id, _ = _get_client_credentials(platform)
        oauth_state = state or secrets.token_urlsafe(32)

        if platform in ("instagram", "facebook", "threads"):
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": config["scopes"],
                "response_type": "code",
                "state": oauth_state,
            }
        elif platform == "youtube":
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": config["scopes"],
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
                "state": oauth_state,
            }
        elif platform == "x":
            code_verifier = _build_code_verifier()
            code_challenge = _build_code_challenge(code_verifier)
            self._x_verifier_by_state[oauth_state] = code_verifier

            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": config["scopes"],
                "response_type": "code",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": oauth_state,
            }
        elif platform == "blog":
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "state": oauth_state,
            }
        elif platform == "kakao":
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": config["scopes"],
                "state": oauth_state,
            }
        elif platform == "tiktok":
            params = {
                "client_key": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": config["scopes"],
                "state": oauth_state,
            }
        elif platform == "linkedin":
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": config["scopes"],
                "state": oauth_state,
            }
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        return f"{config['auth_url']}?{urlencode(params)}"

    async def exchange_code(
        self,
        platform: str,
        code: str,
        redirect_uri: str,
        state: str | None = None,
        code_verifier: str | None = None,
    ) -> dict:
        """Authorization code -> access_token + refresh_token 교환"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        client_id, client_secret = _get_client_credentials(platform)

        if platform == "x" and not code_verifier:
            code_verifier = self._x_verifier_by_state.pop(state, None) if state else None

        async with httpx.AsyncClient(timeout=30) as client:
            if platform in ("instagram", "facebook", "threads"):
                resp = await client.post(
                    config["token_url"],
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
            elif platform == "youtube":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
            elif platform == "x":
                if not code_verifier:
                    raise ValueError("PKCE verifier가 누락되었습니다")
                resp = await client.post(
                    config["token_url"],
                    data={
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": code,
                        "client_id": client_id,
                        "code_verifier": code_verifier,
                    },
                    auth=(client_id, client_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            elif platform == "blog":
                resp = await client.get(
                    config["token_url"],
                    params={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "authorization_code",
                        "code": code,
                        "state": "completed",
                    },
                )
            elif platform == "kakao":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "grant_type": "authorization_code",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
            elif platform == "tiktok":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "client_key": client_id,
                        "client_secret": client_secret,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            elif platform == "linkedin":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "grant_type": "authorization_code",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            else:
                raise ValueError(f"Unsupported platform: {platform}")

            if resp.status_code != 200:
                logger.error(
                    f"OAuth token exchange failed for {platform}: "
                    f"status={resp.status_code}, body={resp.text}"
                )
                raise ValueError(f"Token exchange failed: {resp.text}")

            data = resp.json()
            logger.info(f"OAuth token exchange successful for {platform}")

            return {
                "access_token": encrypt_token(data.get("access_token", "")),
                "refresh_token": encrypt_token(data.get("refresh_token", "")),
                "expires_in": data.get("expires_in"),
                "token_type": data.get("token_type", "bearer"),
                "raw": data,
            }

    async def fetch_account_profile(self, platform: str, access_token: str) -> dict:
        """연동 직후 계정 식별자/이름 조회."""
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                if platform in ("instagram", "threads"):
                    resp = await client.get(
                        "https://graph.facebook.com/v19.0/me",
                        params={"fields": "id,name,username", "access_token": access_token},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "account_id": data.get("id"),
                            "account_name": data.get("username") or data.get("name"),
                            "extra_data": data,
                        }
                elif platform == "facebook":
                    resp = await client.get(
                        "https://graph.facebook.com/v19.0/me/accounts",
                        params={"access_token": access_token},
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("data", [])
                        page = items[0] if items else {}
                        return {
                            "account_id": page.get("id"),
                            "account_name": page.get("name"),
                            "extra_data": {"pages": items},
                        }
                elif platform == "youtube":
                    resp = await client.get(
                        "https://www.googleapis.com/youtube/v3/channels",
                        params={"part": "snippet", "mine": "true"},
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        channel = items[0] if items else {}
                        snippet = channel.get("snippet", {})
                        return {
                            "account_id": channel.get("id"),
                            "account_name": snippet.get("title"),
                            "extra_data": channel,
                        }
                elif platform == "x":
                    resp = await client.get(
                        "https://api.twitter.com/2/users/me",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        return {
                            "account_id": data.get("id"),
                            "account_name": data.get("username") or data.get("name"),
                            "extra_data": data,
                        }
                elif platform == "blog":
                    return {"account_id": None, "account_name": "네이버 블로그", "extra_data": {}}
                elif platform == "kakao":
                    resp = await client.get(
                        "https://kapi.kakao.com/v2/user/me",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        props = data.get("properties", {})
                        return {
                            "account_id": str(data.get("id")) if data.get("id") else None,
                            "account_name": props.get("nickname") or "카카오 사용자",
                            "extra_data": data,
                        }
                elif platform == "tiktok":
                    resp = await client.get(
                        "https://open.tiktokapis.com/v2/user/info/",
                        params={"fields": "open_id,display_name,avatar_url"},
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("data", {}).get("user", {})
                        return {
                            "account_id": data.get("open_id"),
                            "account_name": data.get("display_name"),
                            "extra_data": data,
                        }
                elif platform == "linkedin":
                    resp = await client.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "account_id": data.get("sub"),
                            "account_name": data.get("name") or data.get("localizedFirstName"),
                            "extra_data": data,
                        }
        except Exception as e:
            logger.warning("Account profile fetch failed for %s: %s", platform, e)
        return {"account_id": None, "account_name": None, "extra_data": {}}

    async def refresh_token(
        self,
        platform: str,
        current_refresh_token: str | None = None,
        current_access_token: str | None = None,
    ) -> dict:
        """토큰 갱신"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        client_id, client_secret = _get_client_credentials(platform)
        decrypted_rt = decrypt_token(current_refresh_token) if current_refresh_token else None
        decrypted_at = decrypt_token(current_access_token) if current_access_token else None

        async with httpx.AsyncClient(timeout=30) as client:
            if platform in ("instagram", "facebook", "threads"):
                if not decrypted_at:
                    raise ValueError("Meta token refresh requires current access token")
                resp = await client.get(
                    "https://graph.facebook.com/v19.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "fb_exchange_token": decrypted_at,
                    },
                )
            elif platform == "youtube":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": decrypted_rt,
                    },
                )
            elif platform == "x":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": decrypted_rt,
                        "client_id": client_id,
                    },
                    auth=(client_id, client_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            elif platform == "blog":
                resp = await client.get(
                    config["token_url"],
                    params={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": decrypted_rt,
                    },
                )
            elif platform == "kakao":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": decrypted_rt,
                    },
                )
            elif platform == "tiktok":
                resp = await client.post(
                    config["token_url"],
                    data={
                        "client_key": client_id,
                        "client_secret": client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": decrypted_rt,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            elif platform == "linkedin":
                raise ValueError("LinkedIn은 refresh token을 지원하지 않아 수동 재인증이 필요합니다")
            else:
                raise ValueError(f"Unsupported platform: {platform}")

            if resp.status_code != 200:
                logger.error(
                    f"Token refresh failed for {platform}: "
                    f"status={resp.status_code}, body={resp.text}"
                )
                raise ValueError(f"Token refresh failed: {resp.text}")

            data = resp.json()
            logger.info(f"Token refresh successful for {platform}")

            return {
                "access_token": encrypt_token(data.get("access_token", "")),
                "refresh_token": encrypt_token(
                    data.get("refresh_token", current_refresh_token)
                ),
                "expires_in": data.get("expires_in"),
            }
