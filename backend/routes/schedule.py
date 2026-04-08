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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.channel import ChannelConnection
from models.content import Content
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
    client_id: uuid.UUID | None = Query(default=None, description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """캘린더 뷰 데이터 — 기간 내 예약 목록"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="시작일은 종료일보다 이전이어야 합니다")

    service = SchedulerService(db)
    schedules = await service.get_schedules_in_range(start_date, end_date)
    content_ids = [schedule.content_id for schedule in schedules]
    channel_ids = [schedule.channel_connection_id for schedule in schedules]

    content_map = {}
    channel_map = {}
    if content_ids:
        content_result = await db.execute(select(Content).where(Content.id.in_(content_ids)))
        content_map = {content.id: content for content in content_result.scalars().all()}
    if channel_ids:
        channel_result = await db.execute(select(ChannelConnection).where(ChannelConnection.id.in_(channel_ids)))
        channel_map = {channel.id: channel for channel in channel_result.scalars().all()}

    items = []
    calendar_data = {}
    for schedule in schedules:
        content = content_map.get(schedule.content_id)
        channel = channel_map.get(schedule.channel_connection_id)
        if client_id and (not content or content.client_id != client_id):
            continue

        item = {
            "id": str(schedule.id),
            "content_id": str(schedule.content_id),
            "channel_connection_id": str(schedule.channel_connection_id),
            "scheduled_at": schedule.scheduled_at.isoformat(),
            "status": schedule.status,
            "title": content.title if content else None,
            "platform": channel.channel_type if channel else None,
        }
        items.append(item)

        date_key = schedule.scheduled_at.strftime("%Y-%m-%d")
        calendar_data.setdefault(date_key, []).append(item)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total": len(items),
        "items": items,
        "dates": calendar_data,
    }
