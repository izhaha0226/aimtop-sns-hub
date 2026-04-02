"""
Notifications Routes - 알림 API.
"""
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from middleware.auth import get_current_user
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(
    unread_only: bool = Query(default=False, description="미읽음만 조회"),
    limit: int = Query(default=50, ge=1, le=200, description="조회 수"),
    offset: int = Query(default=0, ge=0, description="오프셋"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """알림 목록 조회."""
    service = NotificationService(db)
    return await service.get_list(current_user.id, unread_only=unread_only, limit=limit, offset=offset)


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """미읽음 알림 수."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """알림 읽음 처리."""
    service = NotificationService(db)
    success = await service.mark_read(notification_id)
    return {"success": success}


@router.put("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """전체 알림 읽음 처리."""
    service = NotificationService(db)
    count = await service.mark_all_read(current_user.id)
    return {"updated_count": count}
