"""
External Approval Service - 외부 리뷰어 승인 워크플로우.
토큰 기반 승인/거절 (로그인 불필요).
"""
import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.content import Content
from models.external_approval import ExternalApproval
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _build_review_link(token: str) -> str:
        base = settings.APP_BASE_URL.rstrip("/")
        return f"{base}/external-approval/{token}"

    @staticmethod
    def _build_email_body(
        reviewer_name: str,
        content_title: str | None,
        content_text: str | None,
        review_link: str,
        expires_at: datetime,
    ) -> str:
        preview = (content_text or "")[:300]
        preview_html = preview.replace("\n", "<br>") if preview else "본문 미리보기가 없습니다."
        title = content_title or "제목 없는 콘텐츠"
        expires_label = expires_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"<h2>SNS Hub 외부 승인 요청</h2>"
            f"<p>{reviewer_name}님, 아래 콘텐츠 검토를 요청드립니다.</p>"
            f"<p><strong>제목:</strong> {title}</p>"
            f"<div style='padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#f9fafb;'>"
            f"{preview_html}"
            f"</div>"
            f"<p style='margin-top:16px'><a href='{review_link}'>승인 페이지 열기</a></p>"
            f"<p style='color:#6b7280'>만료 시각: {expires_label}</p>"
        )

    async def create_approval(
        self,
        content_id: uuid.UUID,
        reviewer_name: str,
        reviewer_email: str,
        expires_hours: int = 72,
    ) -> dict:
        """고유 토큰 생성, 만료시간 설정, 승인 레코드 생성 + 이메일 발송."""
        content_result = await self.db.execute(
            select(Content).where(Content.id == content_id)
        )
        content = content_result.scalar_one_or_none()
        if not content:
            raise ValueError("콘텐츠를 찾을 수 없습니다")

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

        review_link = self._build_review_link(token)
        email_sent = await NotificationService(self.db).send_email(
            to_email=reviewer_email,
            subject=f"[SNS Hub] 외부 승인 요청 · {content.title or '콘텐츠'}",
            body=self._build_email_body(
                reviewer_name=reviewer_name,
                content_title=content.title,
                content_text=content.text,
                review_link=review_link,
                expires_at=expires_at,
            ),
        )
        logger.info(
            "Approval created for content=%s reviewer=%s link=%s email_sent=%s",
            content_id,
            reviewer_email,
            review_link,
            email_sent,
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
            "email_sent": email_sent,
            "content_title": content.title,
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

        content_result = await self.db.execute(
            select(Content).where(Content.id == approval.content_id)
        )
        content = content_result.scalar_one_or_none()

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
            "content": {
                "title": content.title if content else None,
                "text": content.text if content else None,
                "post_type": content.post_type if content else None,
                "media_urls": content.media_urls if content and content.media_urls else [],
            },
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
                "review_link": self._build_review_link(a.token),
                "expired": bool(a.expires_at and a.expires_at < now),
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                "responded_at": a.responded_at.isoformat() if a.responded_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in approvals
        ]
