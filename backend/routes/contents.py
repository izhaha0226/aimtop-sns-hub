import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.content import Content
from models.approval import Approval
from models.schedule import Schedule
from models.user import User
from schemas.content import ContentCreate, ContentUpdate, ContentResponse, ContentListResponse
from schemas.approval import ApprovalCreate, ApprovalResponse
from schemas.schedule import ScheduleCreate, ScheduleResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/contents", tags=["contents"])


async def _get_content_or_404(content_id: uuid.UUID, db: AsyncSession) -> Content:
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.status != "trashed")
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
    return content


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


@router.post("/{content_id}/approve", response_model=ApprovalResponse)
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
    await db.refresh(approval)
    return approval


@router.post("/{content_id}/reject", response_model=ApprovalResponse)
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
    await db.refresh(approval)
    return approval


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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    content = await _get_content_or_404(content_id, db)
    if content.status not in ("approved", "scheduled"):
        raise HTTPException(status_code=400, detail="승인된 콘텐츠만 발행 가능합니다")
    content.status = "published"
    content.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(content)
    return content
