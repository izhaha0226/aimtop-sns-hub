"""
External Approvals Routes - 외부 리뷰어 승인 관리 API.
토큰 기반으로 로그인 없이 승인/거절 가능.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.approval_service import ApprovalService
from middleware.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ExternalApprovalCreate(BaseModel):
    reviewer_name: str
    reviewer_email: str
    expires_hours: int = 72


class ApprovalRespondRequest(BaseModel):
    status: str  # approved / rejected
    feedback: str = ""


@router.post("/{content_id}")
async def create_approval(
    content_id: uuid.UUID,
    body: ExternalApprovalCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """외부 승인 요청 생성 (인증 필요)."""
    svc = ApprovalService(db)
    try:
        result = await svc.create_approval(
            content_id=content_id,
            reviewer_name=body.reviewer_name,
            reviewer_email=body.reviewer_email,
            expires_hours=body.expires_hours,
        )
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/review/{token}")
async def get_review_page(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """토큰으로 승인 페이지 조회 (로그인 불필요)."""
    svc = ApprovalService(db)
    try:
        result = await svc.get_approval_by_token(token)
        return {"ok": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/review/{token}/respond")
async def respond_to_approval(
    token: str,
    body: ApprovalRespondRequest,
    db: AsyncSession = Depends(get_db),
):
    """승인/거절 응답 (로그인 불필요)."""
    svc = ApprovalService(db)
    try:
        result = await svc.respond(
            token=token,
            status=body.status,
            feedback=body.feedback,
        )
        return {"ok": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/content/{content_id}")
async def list_approvals_for_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """콘텐츠의 외부 승인 목록 (인증 필요)."""
    svc = ApprovalService(db)
    approvals = await svc.get_approvals_for_content(content_id)
    return {"ok": True, "data": approvals, "total": len(approvals)}
