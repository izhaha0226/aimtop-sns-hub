"""
콘텐츠 발행 라우트
- 즉시 발행
- 발행 프리뷰
- 발행 상태 확인
"""

import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.content import Content
from models.channel import ChannelConnection
from models.user import User
from middleware.auth import get_current_user
from services.sns_publisher import SNSPublisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/publish", tags=["publish"])

publisher = SNSPublisher()


def _reset_publish_evidence(content: Content) -> None:
    content.platform_post_id = None
    content.published_url = None
    content.published_at = None


async def _get_content_or_404(content_id: uuid.UUID, db: AsyncSession) -> Content:
    result = await db.execute(
        select(Content).where(Content.id == content_id, Content.status != "trashed")
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
    return content


async def _get_channel_or_404(channel_id: uuid.UUID, db: AsyncSession) -> ChannelConnection:
    result = await db.execute(
        select(ChannelConnection).where(
            ChannelConnection.id == channel_id,
            ChannelConnection.is_connected == True,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="연결된 채널을 찾을 수 없습니다")
    return channel


@router.post("/{content_id}")
async def publish_content(
    content_id: uuid.UUID,
    channel_connection_id: uuid.UUID = Query(..., description="발행할 채널 연결 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    콘텐츠 즉시 발행
    - approved 또는 scheduled 상태의 콘텐츠만 발행 가능
    - 해당 채널에 실제 API 호출
    """
    content = await _get_content_or_404(content_id, db)

    if content.status not in ("approved", "scheduled"):
        raise HTTPException(
            status_code=400,
            detail=f"승인된 콘텐츠만 발행 가능합니다 (현재 상태: {content.status})",
        )

    channel = await _get_channel_or_404(channel_connection_id, db)
    if not SNSPublisher.is_supported_platform(channel.channel_type):
        raise HTTPException(
            status_code=400,
            detail=f"{channel.channel_type} 채널은 아직 실제 발행 자동화를 지원하지 않습니다",
        )

    try:
        result = await publisher.publish(channel, content)
        platform_post_id = result.get("platform_post_id")
        published_url = result.get("url")

        if not platform_post_id and not published_url:
            content.status = "failed"
            content.channel_connection_id = channel.id
            _reset_publish_evidence(content)
            content.publish_error = "발행 응답에 platform_post_id/published_url 증거가 없어 published 처리하지 않았습니다"
            await db.commit()
            raise HTTPException(status_code=502, detail=content.publish_error)

        # 발행 성공: 콘텐츠 상태 업데이트
        content.status = "published"
        content.platform_post_id = platform_post_id
        content.published_url = published_url
        content.published_at = datetime.now(timezone.utc)
        content.channel_connection_id = channel.id
        content.publish_error = None

        await db.commit()
        await db.refresh(content)

        logger.info(
            f"Content {content_id} published to {channel.channel_type}: "
            f"post_id={platform_post_id}"
        )

        return {
            "status": "published",
            "content_id": str(content_id),
            "platform": channel.channel_type,
            "platform_post_id": platform_post_id,
            "published_url": published_url,
            "published_at": content.published_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        # 발행 실패: 에러 기록
        content.status = "failed"
        content.channel_connection_id = channel.id
        _reset_publish_evidence(content)
        content.publish_error = str(e)
        await db.commit()

        logger.error(
            f"Content {content_id} publish failed to {channel.channel_type}: {e}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail=f"발행 실패: {str(e)}",
        )


@router.post("/{content_id}/preview")
async def preview_publish(
    content_id: uuid.UUID,
    channel_connection_id: uuid.UUID = Query(..., description="프리뷰할 채널 연결 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    발행 프리뷰
    - 실제 발행하지 않고 미리보기 데이터 반환
    """
    content = await _get_content_or_404(content_id, db)
    channel = await _get_channel_or_404(channel_connection_id, db)

    caption = SNSPublisher._build_caption(content)

    preview = {
        "platform": channel.channel_type,
        "account_name": channel.account_name,
        "title": content.title,
        "caption": caption,
        "media_urls": content.media_urls or [],
        "hashtags": content.hashtags or [],
        "post_type": content.post_type,
        "estimated_reach": None,
    }

    # 플랫폼별 제한 사항 체크
    warnings = []
    if channel.channel_type == "x" and len(caption) > 280:
        warnings.append(f"트윗은 280자 제한입니다 (현재: {len(caption)}자)")
    if channel.channel_type == "instagram" and not content.media_urls:
        warnings.append("Instagram은 이미지가 필요합니다")
    if channel.channel_type == "threads" and content.media_urls:
        warnings.append("Threads 이미지는 공개 접근 가능한 HTTPS URL이어야 합니다")
    if channel.channel_type == "youtube" and not content.title:
        warnings.append("YouTube는 제목이 필요합니다")

    preview["warnings"] = warnings

    return preview


@router.get("/{content_id}/status")
async def get_publish_status(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """발행 상태 확인"""
    content = await _get_content_or_404(content_id, db)

    return {
        "content_id": str(content_id),
        "status": content.status,
        "platform_post_id": content.platform_post_id,
        "published_url": content.published_url,
        "published_at": content.published_at.isoformat() if content.published_at else None,
        "channel_connection_id": str(content.channel_connection_id) if content.channel_connection_id else None,
        "publish_error": content.publish_error,
    }
