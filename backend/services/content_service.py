import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.content import Content
from models.approval import Approval
from models.schedule import Schedule
from models.user import User
from schemas.content import ContentCreate, ContentUpdate


class ContentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_404(self, content_id: uuid.UUID) -> Content:
        result = await self.db.execute(
            select(Content).where(Content.id == content_id, Content.status != "trashed")
        )
        content = result.scalar_one_or_none()
        if not content:
            raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
        return content

    async def list_contents(
        self,
        client_id: uuid.UUID | None = None,
        status: str | None = None,
        post_type: str | None = None,
        author_id: uuid.UUID | None = None,
    ) -> list[Content]:
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
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_content(self, body: ContentCreate, author_id: uuid.UUID) -> Content:
        content = Content(**body.model_dump(), author_id=author_id)
        self.db.add(content)
        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def update_content(self, content_id: uuid.UUID, body: ContentUpdate) -> Content:
        content = await self.get_or_404(content_id)
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(content, field, value)
        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def soft_delete(self, content_id: uuid.UUID) -> None:
        content = await self.get_or_404(content_id)
        content.status = "trashed"
        await self.db.commit()

    async def restore(self, content_id: uuid.UUID) -> Content:
        result = await self.db.execute(
            select(Content).where(Content.id == content_id, Content.status == "trashed")
        )
        content = result.scalar_one_or_none()
        if not content:
            raise HTTPException(status_code=404, detail="휴지통에서 콘텐츠를 찾을 수 없습니다")
        content.status = "draft"
        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def request_approval(self, content_id: uuid.UUID) -> Content:
        content = await self.get_or_404(content_id)
        if content.status not in ("draft", "rejected"):
            raise HTTPException(status_code=400, detail="승인 요청이 불가한 상태입니다")
        content.status = "pending_approval"
        approval = Approval(content_id=content_id, action="pending")
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def approve(self, content_id: uuid.UUID, approver: User, memo: str | None = None) -> Approval:
        if approver.role not in ("admin", "approver"):
            raise HTTPException(status_code=403, detail="승인 권한이 없습니다")
        content = await self.get_or_404(content_id)
        if content.status != "pending_approval":
            raise HTTPException(status_code=400, detail="승인 대기 상태가 아닙니다")
        content.status = "approved"
        approval = Approval(content_id=content_id, approver_id=approver.id, action="approved", memo=memo)
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def reject(self, content_id: uuid.UUID, approver: User, memo: str | None = None) -> Approval:
        if approver.role not in ("admin", "approver"):
            raise HTTPException(status_code=403, detail="승인 권한이 없습니다")
        content = await self.get_or_404(content_id)
        if content.status != "pending_approval":
            raise HTTPException(status_code=400, detail="승인 대기 상태가 아닙니다")
        content.status = "rejected"
        approval = Approval(content_id=content_id, approver_id=approver.id, action="rejected", memo=memo)
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def schedule(self, content_id: uuid.UUID, channel_connection_id: uuid.UUID, scheduled_at: datetime) -> Schedule:
        content = await self.get_or_404(content_id)
        if content.status != "approved":
            raise HTTPException(status_code=400, detail="승인된 콘텐츠만 예약 가능합니다")
        content.status = "scheduled"
        content.scheduled_at = scheduled_at
        schedule = Schedule(content_id=content_id, channel_connection_id=channel_connection_id, scheduled_at=scheduled_at)
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def publish_now(self, content_id: uuid.UUID) -> Content:
        content = await self.get_or_404(content_id)
        if content.status not in ("approved", "scheduled"):
            raise HTTPException(status_code=400, detail="승인된 콘텐츠만 발행 가능합니다")
        raise HTTPException(status_code=400, detail="즉시 발행은 채널 선택과 실제 발행 검증이 필요한 /api/v1/contents/{content_id}/publish-now 경로만 사용해 주세요")
