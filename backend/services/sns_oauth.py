"""
SNS OAuth2 플로우 관리
플랫폼별 OAuth URL 생성, 코드 교환, 토큰 갱신
"""

import secrets
import logging
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


# ---------- 플랫폼별 OAuth 설정 ----------

PLATFORM_CONFIGS = {
    "instagram": {
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "scopes": "instagram_basic,instagram_content_publish,pages_read_engagement",
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
}


def _get_client_credentials(platform: str) -> tuple[str, str]:
    """플랫폼별 client_id / client_secret 반환"""
    mapping = {
        "instagram": (settings.INSTAGRAM_APP_ID, settings.INSTAGRAM_APP_SECRET),
        "youtube": (settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET),
        "x": (settings.X_CLIENT_ID, settings.X_CLIENT_SECRET),
        "blog": (settings.NAVER_CLIENT_ID, settings.NAVER_CLIENT_SECRET),
    }
    creds = mapping.get(platform)
    if not creds:
        raise ValueError(f"Unsupported platform: {platform}")
    return creds


class SNSOAuth:
    """SNS OAuth2 플로우 관리 클래스"""

    def get_auth_url(self, platform: str, redirect_uri: str, state: str | None = None) -> str:
        """플랫폼별 OAuth 인증 URL 생성"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        client_id, _ = _get_client_credentials(platform)
        oauth_state = state or secrets.token_urlsafe(32)

        if platform == "instagram":
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
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": config["scopes"],
                "response_type": "code",
                "code_challenge": secrets.token_urlsafe(43),
                "code_challenge_method": "plain",
                "state": oauth_state,
            }
        elif platform == "blog":
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "state": oauth_state,
            }
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        return f"{config['auth_url']}?{urlencode(params)}"

    async def exchange_code(
        self, platform: str, code: str, redirect_uri: str
    ) -> dict:
        """Authorization code -> access_token + refresh_token 교환"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        client_id, client_secret = _get_client_credentials(platform)

        async with httpx.AsyncClient(timeout=30) as client:
            if platform == "instagram":
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
                resp = await client.post(
                    config["token_url"],
                    data={
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": code,
                        "client_id": client_id,
                        "code_verifier": "placeholder",
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

    async def refresh_token(self, platform: str, current_refresh_token: str) -> dict:
        """토큰 갱신"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        client_id, client_secret = _get_client_credentials(platform)
        decrypted_rt = decrypt_token(current_refresh_token)

        async with httpx.AsyncClient(timeout=30) as client:
            if platform == "instagram":
                # Instagram long-lived token exchange
                resp = await client.get(
                    "https://graph.facebook.com/v19.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "fb_exchange_token": decrypted_rt,
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
