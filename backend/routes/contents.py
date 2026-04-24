import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.content import Content
from models.approval import Approval
from models.schedule import Schedule
from models.channel import ChannelConnection
from models.user import User
from schemas.content import ContentCreate, ContentUpdate, ContentResponse, ContentListResponse
from schemas.approval import ApprovalCreate
from schemas.schedule import ScheduleCreate, ScheduleResponse
from middleware.auth import get_current_user
from services.sns_publisher import SNSPublisher

router = APIRouter(prefix="/api/v1/contents", tags=["contents"])


def _reset_publish_evidence(content: Content) -> None:
    content.platform_post_id = None
    content.published_url = None
    content.published_at = None


def _mark_publish_failed(
    content: Content,
    *,
    channel_connection_id: uuid.UUID | None,
    error_message: str,
) -> None:
    content.channel_connection_id = channel_connection_id
    content.status = "failed"
    _reset_publish_evidence(content)
    content.publish_error = error_message[:500]


async def _get_content_or_404(content_id: uuid.UUID, db: AsyncSession) -> Content:
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.status != "trashed")
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
    return content


async def _ensure_channel_token_valid(channel_connection_id: uuid.UUID | None, db: AsyncSession):
    if not channel_connection_id:
        return
    result = await db.execute(select(ChannelConnection).where(ChannelConnection.id == channel_connection_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="채널 연결을 찾을 수 없습니다")
    if channel.token_expires_at and channel.token_expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail=f"{channel.channel_type} 채널 토큰이 만료되어 재인증이 필요합니다")


@router.get("", response_model=ContentListResponse)
async def list_contents(
    client_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    post_type: str | None = Query(None),
    author_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Content).where(Content.status != "trashed")
    if client_id:
        query = query.where(Content.client_id == client_id)
    if status:
        query = query.where(Content.status == status)
    if post_type:
        query = query.where(Content.post_type == post_type)
    if author_id:
        query = query.where(Content.author_id == author_id)
    query = query.order_by(Content.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": len(items)}


@router.post("", response_model=ContentResponse, status_code=201)
async def create_content(
    body: ContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = Content(**body.model_dump(), author_id=current_user.id)
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _get_content_or_404(content_id, db)


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: uuid.UUID,
    body: ContentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await _get_content_or_404(content_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(content, field, value)
    await db.commit()
    await db.refresh(content)
    return content


@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await _get_content_or_404(content_id, db)
    content.status = "trashed"
    await db.commit()


@router.post("/{content_id}/restore", response_model=ContentResponse)
async def restore_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.status == "trashed")
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="휴지통에서 콘텐츠를 찾을 수 없습니다")
    content.status = "draft"
    await db.commit()
    await db.refresh(content)
    return content


@router.post("/{content_id}/request-approval", response_model=ContentResponse)
async def request_approval(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await _get_content_or_404(content_id, db)
    if content.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="승인 요청이 불가한 상태입니다")
    content.status = "pending_approval"
    approval = Approval(content_id=content_id, action="pending")
    db.add(approval)
    await db.commit()
    await db.refresh(content)
    return content


@router.post("/{content_id}/approve", response_model=ContentResponse)
async def approve_content(
    content_id: uuid.UUID,
    body: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="승인 권한이 없습니다")
    content = await _get_content_or_404(content_id, db)
    if content.status != "pending_approval":
        raise HTTPException(status_code=400, detail="승인 대기 상태가 아닙니다")
    content.status = "approved"
    approval = Approval(content_id=content_id, approver_id=current_user.id, action="approved", memo=body.memo)
    db.add(approval)
    await db.commit()
    await db.refresh(content)
    return content


@router.post("/{content_id}/reject", response_model=ContentResponse)
async def reject_content(
    content_id: uuid.UUID,
    body: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="승인 권한이 없습니다")
    content = await _get_content_or_404(content_id, db)
    if content.status != "pending_approval":
        raise HTTPException(status_code=400, detail="승인 대기 상태가 아닙니다")
    content.status = "rejected"
    approval = Approval(content_id=content_id, approver_id=current_user.id, action="rejected", memo=body.memo)
    db.add(approval)
    await db.commit()
    await db.refresh(content)
    return content


@router.post("/{content_id}/schedule", response_model=ScheduleResponse)
async def schedule_content(
    content_id: uuid.UUID,
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await _get_content_or_404(content_id, db)
    if content.status != "approved":
        raise HTTPException(status_code=400, detail="승인된 콘텐츠만 예약 가능합니다")
    await _ensure_channel_token_valid(body.channel_connection_id, db)
    content.channel_connection_id = body.channel_connection_id
    content.status = "scheduled"
    content.scheduled_at = body.scheduled_at
    schedule = Schedule(content_id=content_id, channel_connection_id=body.channel_connection_id, scheduled_at=body.scheduled_at)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.post("/{content_id}/publish-now", response_model=ContentResponse)
async def publish_now(
    content_id: uuid.UUID,
    channel_connection_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await _get_content_or_404(content_id, db)
    if content.status not in ("approved", "scheduled"):
        raise HTTPException(status_code=400, detail="승인된 콘텐츠만 발행 가능합니다")

    target_channel_id = channel_connection_id or content.channel_connection_id
    if not target_channel_id:
        raise HTTPException(status_code=400, detail="발행할 채널을 선택해 주세요")

    channel_result = await db.execute(select(ChannelConnection).where(ChannelConnection.id == target_channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel or not channel.is_connected:
        _mark_publish_failed(
            content,
            channel_connection_id=target_channel_id,
            error_message="연결된 채널을 찾을 수 없습니다",
        )
        await db.commit()
        raise HTTPException(status_code=404, detail=content.publish_error)
    if channel.token_expires_at and channel.token_expires_at <= datetime.now(timezone.utc):
        _mark_publish_failed(
            content,
            channel_connection_id=target_channel_id,
            error_message=f"{channel.channel_type} 채널 토큰이 만료되어 재인증이 필요합니다",
        )
        await db.commit()
        raise HTTPException(status_code=400, detail=content.publish_error)
    if not SNSPublisher.is_supported_platform(channel.channel_type):
        _mark_publish_failed(
            content,
            channel_connection_id=target_channel_id,
            error_message=f"{channel.channel_type} 채널은 아직 실제 발행 자동화를 지원하지 않습니다",
        )
        await db.commit()
        raise HTTPException(status_code=400, detail=content.publish_error)

    publisher = SNSPublisher()
    try:
        result = await publisher.publish(channel, content)
        content.channel_connection_id = target_channel_id
        content.status = "published"
        content.platform_post_id = result.get("platform_post_id")
        content.published_url = result.get("url")
        content.published_at = datetime.now(timezone.utc)
        content.publish_error = None

        if not content.platform_post_id and not content.published_url:
            _mark_publish_failed(
                content,
                channel_connection_id=target_channel_id,
                error_message="발행 응답에 platform_post_id/published_url 증거가 없어 published 처리하지 않았습니다",
            )
            await db.commit()
            raise HTTPException(status_code=502, detail=content.publish_error)

        await db.commit()
        await db.refresh(content)
        return content
    except HTTPException:
        raise
    except Exception as e:
        _mark_publish_failed(
            content,
            channel_connection_id=target_channel_id,
            error_message=str(e),
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=f"발행 실패: {str(e)}")
