"""
Growth Hub Routes - AI 기반 성장 전략 API.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.growth_service import GrowthService
from middleware.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/api/v1/growth", tags=["growth"])


class ContentIdeasRequest(BaseModel):
    client_id: uuid.UUID
    count: int = 10


class CompetitorAnalysisRequest(BaseModel):
    competitor_handles: list[str]


@router.get("/trending-hashtags")
async def get_trending_hashtags(
    platform: str = Query(..., description="플랫폼 (instagram, youtube, x, naver)"),
    category: str | None = Query(None, description="카테고리"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """트렌딩 해시태그 조회."""
    svc = GrowthService(db)
    try:
        hashtags = await svc.get_trending_hashtags(platform, category)
        return {"ok": True, "data": hashtags, "platform": platform}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/content-ideas")
async def get_content_ideas(
    body: ContentIdeasRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """콘텐츠 아이디어 AI 생성."""
    svc = GrowthService(db)
    try:
        ideas = await svc.get_content_ideas(body.client_id, body.count)
        return {"ok": True, "data": ideas, "total": len(ideas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitor-analysis")
async def get_competitor_analysis(
    body: CompetitorAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """경쟁사 분석."""
    if not body.competitor_handles:
        raise HTTPException(status_code=400, detail="경쟁사 핸들을 입력해주세요")
    if len(body.competitor_handles) > 10:
        raise HTTPException(status_code=400, detail="최대 10개 계정까지 분석 가능합니다")

    svc = GrowthService(db)
    try:
        analysis = await svc.get_competitor_analysis(body.competitor_handles)
        return {"ok": True, "data": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimal-schedule/{account_id}")
async def get_optimal_schedule(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """최적 포스팅 스케줄 AI 추천."""
    svc = GrowthService(db)
    try:
        schedule = await svc.get_optimal_schedule(account_id)
        return {"ok": True, "data": schedule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
