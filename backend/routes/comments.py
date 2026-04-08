"""
댓글 관리 라우트
- 댓글 목록 / 동기화 / 답글 / 숨기기
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.channel import ChannelConnection
from models.comment import Comment
from models.user import User
from middleware.auth import get_current_user
from services.comment_service import CommentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/comments", tags=["comments"])


class ReplyRequest(BaseModel):
    text: str


@router.get("/all")
async def list_comments_for_client(
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    limit: int = Query(50, ge=1, le=200),
    include_hidden: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """선택된 클라이언트의 전체 댓글 목록."""
    query = (
        select(Comment)
        .join(ChannelConnection, Comment.channel_connection_id == ChannelConnection.id)
        .where(ChannelConnection.client_id == client_id)
        .order_by(Comment.created_at.desc())
        .limit(limit)
    )
    if not include_hidden:
        query = query.where(Comment.is_hidden == False)

    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": len(items)}


@router.post("/sync/all")
async def sync_comments_for_client(
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """선택된 클라이언트의 연결 채널 전체 댓글 동기화."""
    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.client_id == client_id,
            ChannelConnection.is_connected == True,
        )
    )
    channels = result.scalars().all()

    service = CommentService(db)
    synced_channels = 0
    total_new_comments = 0
    errors: list[dict] = []

    for channel in channels:
        try:
            total_new_comments += await service.sync_comments(channel.id)
            synced_channels += 1
        except Exception as e:
            logger.warning("Failed to sync comments for channel %s: %s", channel.id, e)
            errors.append({"channel_id": str(channel.id), "error": str(e)})

    return {
        "status": "synced",
        "client_id": str(client_id),
        "synced_channels": synced_channels,
        "new_comments": total_new_comments,
        "errors": errors,
    }


@router.get("/{account_id}")
async def list_comments(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_hidden: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """댓글 목록 (페이지네이션)"""
    service = CommentService(db)
    result = await service.get_comments(
        account_id=account_id,
        page=page,
        page_size=page_size,
        include_hidden=include_hidden,
    )
    return result


@router.post("/{comment_id}/reply")
async def reply_to_comment(
    comment_id: uuid.UUID,
    body: ReplyRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """댓글에 답글 전송"""
    service = CommentService(db)
    try:
        result = await service.reply_comment(comment_id, body.text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{comment_id}/hide")
async def hide_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """댓글 숨기기"""
    service = CommentService(db)
    success = await service.hide_comment(comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")
    return {"status": "hidden", "comment_id": str(comment_id)}


@router.post("/sync/{account_id}")
async def sync_comments(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """SNS에서 댓글 동기화"""
    service = CommentService(db)
    try:
        count = await service.sync_comments(account_id)
        return {
            "status": "synced",
            "account_id": str(account_id),
            "new_comments": count,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
