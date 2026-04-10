"""
SNS OAuth 라우트
- OAuth 인증 URL 생성
- OAuth 콜백 처리
- 연동 해제
"""

import base64
import json
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.channel import ChannelConnection
from models.user import User
from middleware.auth import get_current_user
from services.sns_oauth import SNSOAuth, decrypt_token

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])

oauth_service = SNSOAuth()

SUPPORTED_PLATFORMS = ("instagram", "facebook", "threads", "youtube", "x", "blog", "kakao", "tiktok", "linkedin")


def _encode_state(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def _decode_state(value: str | None) -> dict:
    if not value:
        return {}
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        return json.loads(raw)
    except Exception:
        return {}


@router.get("/{platform}/auth-url")
async def get_auth_url(
    platform: str,
    client_id: uuid.UUID = Query(..., description="연결할 클라이언트 ID"),
    redirect_uri: str = Query(..., description="OAuth 콜백 URI"),
    frontend_redirect: str | None = Query(default=None, description="연동 후 이동할 프론트 URL"),
    _: User = Depends(get_current_user),
):
    """플랫폼별 OAuth 인증 URL 반환"""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼: {platform}")

    try:
        state = _encode_state(
            {
                "client_id": str(client_id),
                "frontend_redirect": frontend_redirect,
                "redirect_uri": redirect_uri,
            }
        )
        url = oauth_service.get_auth_url(platform, redirect_uri, state=state)
        return {"auth_url": url, "platform": platform}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{platform}/callback")
async def oauth_callback(
    request: Request,
    platform: str,
    code: str = Query(..., description="Authorization code"),
    state: str | None = Query(default=None),
    client_id: uuid.UUID | None = Query(default=None, description="연결할 클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 콜백 처리
    - code를 access_token으로 교환
    - ChannelConnection 생성/업데이트
    - 처리 후 프론트로 리다이렉트
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼: {platform}")

    state_payload = _decode_state(state)
    resolved_client_id = client_id or (uuid.UUID(state_payload["client_id"]) if state_payload.get("client_id") else None)
    if not resolved_client_id:
        raise HTTPException(status_code=400, detail="client_id가 누락되었습니다")

    redirect_uri = state_payload.get("redirect_uri") or str(request.url).split("?")[0]
    frontend_redirect = state_payload.get("frontend_redirect") or f"/clients/{resolved_client_id}"

    try:
        tokens = await oauth_service.exchange_code(platform, code, redirect_uri, state=state)
    except ValueError as e:
        error_url = f"{frontend_redirect}?oauth=error&platform={platform}&message={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)

    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.client_id == resolved_client_id,
            ChannelConnection.channel_type == platform,
            ChannelConnection.is_connected == True,
        )
    )
    existing = result.scalar_one_or_none()

    access_token = decrypt_token(tokens["access_token"])
    profile = await oauth_service.fetch_account_profile(platform, access_token)

    expires_in = tokens.get("expires_in")
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    if existing:
        existing.access_token = tokens["access_token"]
        existing.refresh_token = tokens.get("refresh_token", existing.refresh_token)
        existing.token_expires_at = token_expires_at
        existing.connected_at = datetime.now(timezone.utc)
        existing.is_connected = True
        existing.account_name = profile.get("account_name") or existing.account_name
        existing.account_id = profile.get("account_id") or existing.account_id
        existing.extra_data = {**(existing.extra_data or {}), **profile.get("extra_data", {})}
        await db.commit()
    else:
        connection = ChannelConnection(
            client_id=resolved_client_id,
            channel_type=platform,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            token_expires_at=token_expires_at,
            is_connected=True,
            connected_at=datetime.now(timezone.utc),
            account_name=profile.get("account_name"),
            account_id=profile.get("account_id"),
            extra_data=profile.get("extra_data", {}),
        )
        db.add(connection)
        await db.commit()

    success_url = f"{frontend_redirect}?oauth=success&platform={platform}"
    return RedirectResponse(url=success_url, status_code=302)


@router.post("/{platform}/disconnect")
async def disconnect_platform(
    platform: str,
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """SNS 연동 해제"""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼: {platform}")

    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.client_id == client_id,
            ChannelConnection.channel_type == platform,
            ChannelConnection.is_connected == True,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="연결된 채널을 찾을 수 없습니다")

    connection.is_connected = False
    connection.access_token = None
    connection.refresh_token = None
    await db.commit()

    return {"status": "disconnected", "platform": platform}
