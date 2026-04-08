"""
SNS OAuth 라우트
- OAuth 인증 URL 생성
- OAuth 콜백 처리
- 연동 해제
"""

import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.channel import ChannelConnection
from models.user import User
from middleware.auth import get_current_user
from services.sns_oauth import SNSOAuth

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])

oauth_service = SNSOAuth()

SUPPORTED_PLATFORMS = ("instagram", "youtube", "x", "blog")


@router.get("/{platform}/auth-url")
async def get_auth_url(
    platform: str,
    redirect_uri: str = Query(..., description="OAuth 콜백 URI"),
    _: User = Depends(get_current_user),
):
    """플랫폼별 OAuth 인증 URL 반환"""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼: {platform}")

    try:
        url = oauth_service.get_auth_url(platform, redirect_uri)
        return {"auth_url": url, "platform": platform}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(None),
    redirect_uri: str = Query(..., description="원래 redirect_uri"),
    client_id: uuid.UUID = Query(..., description="연결할 클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 콜백 처리
    - code를 access_token으로 교환
    - ChannelConnection 생성/업데이트
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼: {platform}")

    try:
        tokens = await oauth_service.exchange_code(platform, code, redirect_uri, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"토큰 교환 실패: {str(e)}")

    # 기존 연결 확인
    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.client_id == client_id,
            ChannelConnection.channel_type == platform,
            ChannelConnection.is_connected == True,
        )
    )
    existing = result.scalar_one_or_none()

    expires_in = tokens.get("expires_in")
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    if existing:
        # 기존 연결 업데이트
        existing.access_token = tokens["access_token"]
        existing.refresh_token = tokens.get("refresh_token", existing.refresh_token)
        existing.token_expires_at = token_expires_at
        existing.connected_at = datetime.now(timezone.utc)
        existing.is_connected = True
        await db.commit()
        await db.refresh(existing)
        return {
            "status": "updated",
            "channel_connection_id": str(existing.id),
            "platform": platform,
        }
    else:
        # 새 연결 생성
        connection = ChannelConnection(
            client_id=client_id,
            channel_type=platform,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            token_expires_at=token_expires_at,
            is_connected=True,
            connected_at=datetime.now(timezone.utc),
        )
        db.add(connection)
        await db.commit()
        await db.refresh(connection)
        return {
            "status": "connected",
            "channel_connection_id": str(connection.id),
            "platform": platform,
        }


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
