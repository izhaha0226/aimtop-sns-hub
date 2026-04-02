"""
External Approval Service - 외부 리뷰어 승인 워크플로우.
토큰 기반 승인/거절 (로그인 불필요).
"""
import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.external_approval import ExternalApproval

logger = logging.getLogger(__name__)


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_approval(
        self,
        content_id: uuid.UUID,
        reviewer_name: str,
        reviewer_email: str,
        expires_hours: int = 72,
    ) -> dict:
        """고유 토큰 생성, 만료시간 설정, 승인 레코드 생성."""
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

        approval = ExternalApproval(
            content_id=content_id,
            reviewer_name=reviewer_name,
            reviewer_email=reviewer_email,
            token=token,
            status="pending",
            expires_at=expires_at,
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)

        # TODO: 이메일 발송 (notification_service 연동)
        review_link = f"/api/v1/approvals/review/{token}"
        logger.info(
            "Approval created for content=%s reviewer=%s link=%s",
            content_id,
            reviewer_email,
            review_link,
        )

        return {
            "id": str(approval.id),
            "content_id": str(approval.content_id),
            "reviewer_name": approval.reviewer_name,
            "reviewer_email": approval.reviewer_email,
            "token": approval.token,
            "status": approval.status,
            "expires_at": approval.expires_at.isoformat(),
            "review_link": review_link,
            "created_at": approval.created_at.isoformat(),
        }

    async def get_approval_by_token(self, token: str) -> dict:
        """토큰으로 승인 조회 (만료 체크)."""
        result = await self.db.execute(
            select(ExternalApproval).where(ExternalApproval.token == token)
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise ValueError("유효하지 않은 토큰입니다")

        now = datetime.now(timezone.utc)
        expired = approval.expires_at and approval.expires_at < now

        return {
            "id": str(approval.id),
            "content_id": str(approval.content_id),
            "reviewer_name": approval.reviewer_name,
            "reviewer_email": approval.reviewer_email,
            "status": approval.status,
            "feedback": approval.feedback,
            "expired": expired,
            "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
            "responded_at": approval.responded_at.isoformat() if approval.responded_at else None,
            "created_at": approval.created_at.isoformat(),
        }

    async def respond(self, token: str, status: str, feedback: str = "") -> dict:
        """approved/rejected + 피드백 응답 처리."""
        if status not in ("approved", "rejected"):
            raise ValueError("status는 approved 또는 rejected만 가능합니다")

        result = await self.db.execute(
            select(ExternalApproval).where(ExternalApproval.token == token)
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise ValueError("유효하지 않은 토큰입니다")

        if approval.status != "pending":
            raise ValueError(f"이미 처리된 승인입니다 (현재: {approval.status})")

        now = datetime.now(timezone.utc)
        if approval.expires_at and approval.expires_at < now:
            raise ValueError("만료된 승인 요청입니다")

        approval.status = status
        approval.feedback = feedback
        approval.responded_at = now
        await self.db.commit()
        await self.db.refresh(approval)

        logger.info(
            "Approval %s responded: status=%s content=%s",
            approval.id,
            status,
            approval.content_id,
        )

        return {
            "id": str(approval.id),
            "content_id": str(approval.content_id),
            "status": approval.status,
            "feedback": approval.feedback,
            "responded_at": approval.responded_at.isoformat(),
        }

    async def get_approvals_for_content(self, content_id: uuid.UUID) -> list:
        """콘텐츠의 모든 외부 승인 목록."""
        result = await self.db.execute(
            select(ExternalApproval)
            .where(ExternalApproval.content_id == content_id)
            .order_by(ExternalApproval.created_at.desc())
        )
        approvals = result.scalars().all()
        now = datetime.now(timezone.utc)

        return [
            {
                "id": str(a.id),
                "content_id": str(a.content_id),
                "reviewer_name": a.reviewer_name,
                "reviewer_email": a.reviewer_email,
                "status": a.status,
                "feedback": a.feedback,
                "expired": bool(a.expires_at and a.expires_at < now),
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                "responded_at": a.responded_at.isoformat() if a.responded_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in approvals
        ]
