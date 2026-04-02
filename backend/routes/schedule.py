"""
예약 발행 관리 라우트
- 예약 등록 / 취소
- 대기 중 예약 목록
- 캘린더 뷰 데이터
"""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from middleware.auth import get_current_user
from services.scheduler_service import SchedulerService
from schemas.schedule import ScheduleResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


class ScheduleRequest(BaseModel):
    scheduled_at: datetime
    channel_connection_id: uuid.UUID | None = None


@router.post("/{content_id}")
async def create_schedule(
    content_id: uuid.UUID,
    body: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """예약 발행 등록"""
    service = SchedulerService(db)
    try:
        result = await service.schedule_publish(
            content_id=content_id,
            scheduled_at=body.scheduled_at,
            channel_connection_id=body.channel_connection_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{content_id}")
async def cancel_schedule(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """예약 취소"""
    service = SchedulerService(db)
    success = await service.cancel_schedule(content_id)
    if not success:
        raise HTTPException(status_code=404, detail="대기 중인 예약을 찾을 수 없습니다")
    return {"status": "cancelled", "content_id": str(content_id)}


@router.get("/pending", response_model=list[ScheduleResponse])
async def get_pending_schedules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """대기 중인 예약 목록"""
    service = SchedulerService(db)
    schedules = await service.get_pending_schedules()
    return schedules


@router.get("/calendar")
async def get_calendar_schedules(
    start_date: datetime = Query(..., description="조회 시작일"),
    end_date: datetime = Query(..., description="조회 종료일"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """캘린더 뷰 데이터 — 기간 내 예약 목록"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="시작일은 종료일보다 이전이어야 합니다")

    service = SchedulerService(db)
    schedules = await service.get_schedules_in_range(start_date, end_date)

    # 캘린더 뷰를 위한 날짜별 그룹핑
    calendar_data = {}
    for s in schedules:
        date_key = s.scheduled_at.strftime("%Y-%m-%d")
        if date_key not in calendar_data:
            calendar_data[date_key] = []
        calendar_data[date_key].append({
            "id": str(s.id),
            "content_id": str(s.content_id),
            "channel_connection_id": str(s.channel_connection_id),
            "scheduled_at": s.scheduled_at.isoformat(),
            "status": s.status,
        })

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total": len(schedules),
        "dates": calendar_data,
    }
