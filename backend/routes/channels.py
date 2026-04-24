import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.channel import ChannelConnection
from models.user import User
from schemas.channel import ChannelConnectionCreate, ChannelConnectionResponse
from middleware.auth import get_current_user
from services.sns_oauth import encrypt_token

router = APIRouter(prefix="/api/v1/clients/{client_id}/channels", tags=["channels"])


@router.get("", response_model=list[ChannelConnectionResponse])
async def list_channels(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelConnection)
        .where(ChannelConnection.client_id == client_id)
        .order_by(ChannelConnection.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ChannelConnectionResponse, status_code=201)
async def connect_channel(
    client_id: uuid.UUID,
    body: ChannelConnectionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    access_token = body.access_token.strip() if body.access_token else ""
    refresh_token = body.refresh_token.strip() if body.refresh_token else ""
    is_connected = bool(access_token)

    payload = body.model_dump()
    payload["access_token"] = encrypt_token(access_token) if access_token else None
    payload["refresh_token"] = encrypt_token(refresh_token) if refresh_token else None

    channel = ChannelConnection(
        **payload,
        client_id=client_id,
        is_connected=is_connected,
        connected_at=datetime.now(timezone.utc) if is_connected else None,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
async def disconnect_channel(
    client_id: uuid.UUID,
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.id == channel_id,
            ChannelConnection.client_id == client_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="채널 연결을 찾을 수 없습니다")
    channel.is_connected = False
    await db.commit()


@router.get("/{channel_id}/status", response_model=ChannelConnectionResponse)
async def channel_status(
    client_id: uuid.UUID,
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.id == channel_id,
            ChannelConnection.client_id == client_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="채널 연결을 찾을 수 없습니다")
    return channel
