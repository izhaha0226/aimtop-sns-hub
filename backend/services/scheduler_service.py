"""
예약 발행 스케줄러 서비스
Celery 없이 asyncio + DB 폴링 방식으로 구현 (초기 버전)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from models.schedule import Schedule
from models.content import Content
from models.channel import ChannelConnection
from services.sns_publisher import SNSPublisher

logger = logging.getLogger(__name__)

publisher = SNSPublisher()


class SchedulerService:
    """예약 발행 관리 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def schedule_publish(
        self,
        content_id: uuid.UUID,
        scheduled_at: datetime,
        channel_connection_id: uuid.UUID | None = None,
    ) -> dict:
        """예약 발행 등록"""
        # 콘텐츠 존재 확인
        result = await self.db.execute(
            select(Content).where(Content.id == content_id)
        )
        content = result.scalar_one_or_none()
        if not content:
            raise ValueError("콘텐츠를 찾을 수 없습니다")

        if content.status not in ("approved", "scheduled"):
            raise ValueError(f"승인된 콘텐츠만 예약 가능합니다 (현재: {content.status})")

        if scheduled_at <= datetime.now(timezone.utc):
            raise ValueError("예약 시간은 현재 시간 이후여야 합니다")

        # 기존 pending 예약이 있으면 취소
        existing = await self.db.execute(
            select(Schedule).where(
                Schedule.content_id == content_id,
                Schedule.status == "pending",
            )
        )
        for old_schedule in existing.scalars().all():
            old_schedule.status = "cancelled"

        # 새 예약 생성
        conn_id = channel_connection_id or content.channel_connection_id
        if not conn_id:
            raise ValueError("채널 연결 ID가 필요합니다")

        schedule = Schedule(
            content_id=content_id,
            channel_connection_id=conn_id,
            scheduled_at=scheduled_at,
            status="pending",
        )
        self.db.add(schedule)

        # 콘텐츠 상태를 scheduled로 변경
        content.status = "scheduled"
        content.scheduled_at = scheduled_at

        await self.db.commit()
        await self.db.refresh(schedule)

        logger.info(f"Schedule created: content={content_id}, at={scheduled_at}")
        return {
            "id": str(schedule.id),
            "content_id": str(content_id),
            "scheduled_at": scheduled_at.isoformat(),
            "status": schedule.status,
        }

    async def cancel_schedule(self, content_id: uuid.UUID) -> bool:
        """예약 취소"""
        result = await self.db.execute(
            select(Schedule).where(
                Schedule.content_id == content_id,
                Schedule.status == "pending",
            )
        )
        schedules = result.scalars().all()
        if not schedules:
            return False

        for schedule in schedules:
            schedule.status = "cancelled"

        # 콘텐츠 상태 복원
        content_result = await self.db.execute(
            select(Content).where(Content.id == content_id)
        )
        content = content_result.scalar_one_or_none()
        if content and content.status == "scheduled":
            content.status = "approved"
            content.scheduled_at = None

        await self.db.commit()
        logger.info(f"Schedule cancelled: content={content_id}")
        return True

    async def get_pending_schedules(self) -> list:
        """대기 중인 예약 목록"""
        result = await self.db.execute(
            select(Schedule)
            .where(Schedule.status == "pending")
            .order_by(Schedule.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_schedules_in_range(
        self, start_date: datetime, end_date: datetime
    ) -> list:
        """기간 내 예약 목록 (캘린더 뷰)"""
        result = await self.db.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.scheduled_at >= start_date,
                    Schedule.scheduled_at <= end_date,
                )
            )
            .order_by(Schedule.scheduled_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def process_due_schedules():
        """
        매분 실행 — due 된 예약을 찾아서 발행 처리
        독립적 DB 세션 사용 (백그라운드 태스크)
        """
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Schedule).where(
                    Schedule.status == "pending",
                    Schedule.scheduled_at <= now,
                )
            )
            due_schedules = result.scalars().all()

            if not due_schedules:
                return

            logger.info(f"Processing {len(due_schedules)} due schedules")

            for schedule in due_schedules:
                try:
                    # 콘텐츠와 채널 조회
                    content_result = await db.execute(
                        select(Content).where(Content.id == schedule.content_id)
                    )
                    content = content_result.scalar_one_or_none()

                    channel_result = await db.execute(
                        select(ChannelConnection).where(
                            ChannelConnection.id == schedule.channel_connection_id
                        )
                    )
                    channel = channel_result.scalar_one_or_none()

                    if not content or not channel:
                        schedule.status = "failed"
                        schedule.error_message = "콘텐츠 또는 채널을 찾을 수 없습니다"
                        await db.commit()
                        continue

                    # 발행 실행
                    pub_result = await publisher.publish(channel, content)

                    # 성공 처리
                    schedule.status = "published"
                    schedule.platform_post_id = pub_result.get("platform_post_id")
                    schedule.published_at = datetime.now(timezone.utc)

                    content.status = "published"
                    content.platform_post_id = pub_result.get("platform_post_id")
                    content.published_url = pub_result.get("url")
                    content.published_at = datetime.now(timezone.utc)

                    await db.commit()
                    logger.info(
                        f"Schedule published: content={schedule.content_id}, "
                        f"post_id={pub_result.get('platform_post_id')}"
                    )

                except Exception as e:
                    schedule.status = "failed"
                    schedule.error_message = str(e)[:500]
                    schedule.retry_count = (schedule.retry_count or 0) + 1

                    # 3회 미만 실패 시 다시 pending으로 (재시도)
                    if schedule.retry_count < 3:
                        schedule.status = "pending"
                        logger.warning(
                            f"Schedule retry ({schedule.retry_count}/3): "
                            f"content={schedule.content_id}, error={e}"
                        )
                    else:
                        logger.error(
                            f"Schedule failed permanently: "
                            f"content={schedule.content_id}, error={e}"
                        )

                    await db.commit()


async def scheduler_loop():
    """백그라운드에서 매분 실행되는 스케줄러 루프"""
    logger.info("Scheduler loop started")
    while True:
        try:
            await SchedulerService.process_due_schedules()
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}", exc_info=True)
        await asyncio.sleep(60)  # 1분마다 체크
