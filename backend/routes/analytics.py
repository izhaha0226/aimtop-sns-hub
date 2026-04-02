"""
Analytics Routes - 성과 분석 API.
"""
import uuid
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from middleware.auth import get_current_user
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/{account_id}/summary")
async def get_summary(
    account_id: uuid.UUID,
    start_date: date = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    end_date: date = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """채널 성과 요약."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db)
    return await service.get_summary(account_id, start_date, end_date)


@router.get("/{account_id}/daily")
async def get_daily_stats(
    account_id: uuid.UUID,
    start_date: date = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    end_date: date = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """일별 시계열 데이터."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db)
    return await service.get_daily_stats(account_id, start_date, end_date)


@router.get("/content-performance")
async def get_content_performance(
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    limit: int = Query(default=20, ge=1, le=100, description="조회 수"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """콘텐츠별 성과 랜킹."""
    service = AnalyticsService(db)
    return await service.get_content_performance(client_id, limit)


@router.post("/{account_id}/sync")
async def sync_analytics(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """SNS API에서 성과 데이터 동기화."""
    service = AnalyticsService(db)
    try:
        return await service.sync_analytics(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{account_id}/insights")
async def get_insights(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """AI 성과 분석 인사이트."""
    service = AnalyticsService(db)
    return await service.generate_ai_insights(account_id)
