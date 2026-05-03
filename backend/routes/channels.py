import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.channel import ChannelConnection
from models.user import User
from schemas.channel import ChannelConnectionCreate, ChannelConnectionResponse, ChannelAccountSelection
from middleware.auth import get_current_user
from services.sns_oauth import encrypt_token

router = APIRouter(prefix="/api/v1/clients/{client_id}/channels", tags=["channels"])


def _find_channel_choice(channel: ChannelConnection, selected_id: str) -> dict | None:
    choices = (channel.extra_data or {}).get("channel_choices")
    if not isinstance(choices, list):
        return None
    for choice in choices:
        if isinstance(choice, dict) and str(choice.get("id")) == selected_id:
            return choice
    return None


def _page_for_choice(channel: ChannelConnection, choice: dict) -> dict | None:
    pages = (channel.extra_data or {}).get("pages")
    if not isinstance(pages, list):
        return None
    page_id = str(choice.get("page_id") or choice.get("id") or "")
    for page in pages:
        if isinstance(page, dict) and str(page.get("id")) == page_id:
            return page
    return None


def _apply_channel_selection(channel: ChannelConnection, choice: dict) -> None:
    extra = dict(channel.extra_data or {})
    safe_choice = {
        key: value
        for key, value in choice.items()
        if key not in {"access_token", "page_access_token", "token", "secret"}
    }
    channel.account_id = str(choice["id"])
    channel.account_name = str(choice.get("label") or choice.get("name") or choice["id"])
    extra["selected_channel"] = safe_choice
    extra["selection_required"] = False

    if channel.channel_type == "facebook":
        page = _page_for_choice(channel, choice)
        if isinstance(page, dict):
            # Keep token in server-only extra_data for publishing, but never expose
            # extra_data in response schemas.
            extra["page_id"] = str(page.get("id")) if page.get("id") else channel.account_id
            extra["page_name"] = str(page.get("name")) if page.get("name") else channel.account_name
            if page.get("access_token"):
                extra["page_access_token"] = page.get("access_token")
    elif channel.channel_type == "instagram":
        extra["instagram_user_id"] = channel.account_id
        if choice.get("username"):
            extra["instagram_username"] = choice.get("username")
        if choice.get("page_id"):
            extra["page_id"] = choice.get("page_id")

    channel.extra_data = extra


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


@router.post("/{channel_id}/select-account", response_model=ChannelConnectionResponse)
async def select_channel_account(
    client_id: uuid.UUID,
    channel_id: uuid.UUID,
    body: ChannelAccountSelection,
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
    if channel.channel_type not in {"facebook", "instagram"}:
        raise HTTPException(status_code=400, detail="이 채널은 계정 선택이 필요하지 않습니다")

    choice = _find_channel_choice(channel, body.selected_id.strip())
    if not choice:
        raise HTTPException(status_code=400, detail="선택 가능한 페이지/채널 ID가 아닙니다. 다시 연동해 주세요.")

    _apply_channel_selection(channel, choice)
    await db.commit()
    await db.refresh(channel)
    return channel
