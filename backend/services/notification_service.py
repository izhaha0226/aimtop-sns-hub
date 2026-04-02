"""
Notification Service - 알림 생성, 조회, 읽음 처리, 텔레그램/이메일 발송.
"""
import uuid
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_

from models.notification import Notification
from core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        type: str,
        title: str,
        message: str | None = None,
        link_url: str | None = None,
    ) -> dict:
        """알림 생성."""
        notification = Notification(
            client_id=client_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link_url=link_url,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        return {
            "id": str(notification.id),
            "client_id": str(notification.client_id),
            "user_id": str(notification.user_id),
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "is_read": notification.is_read,
            "link_url": notification.link_url,
            "created_at": notification.created_at.isoformat(),
        }

    async def get_list(
        self, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> list:
        """알림 목록 조회."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        notifications = result.scalars().all()

        return [
            {
                "id": str(n.id),
                "client_id": str(n.client_id),
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "link_url": n.link_url,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]

    async def get_unread(self, user_id: uuid.UUID) -> list:
        """미읽음 알림 목록."""
        return await self.get_list(user_id, unread_only=True)

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """미읽음 알림 수."""
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
        )
        return result.scalar() or 0

    async def mark_read(self, notification_id: uuid.UUID) -> bool:
        """알림 읽음 처리."""
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False

        notification.is_read = True
        await self.db.commit()
        return True

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """전체 알림 읽음 처리. 업데이트된 수 반환."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount

    async def send_telegram(self, user_id: uuid.UUID, message: str) -> bool:
        """python-telegram-bot으로 텔레그램 알림 발송."""
        try:
            from telegram import Bot

            bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
            if not bot_token:
                logger.warning("TELEGRAM_BOT_TOKEN not configured")
                return False

            # user_id로부터 텔레그램 chat_id 조회 (users 테이블에 저장된다고 가정)
            from models.user import User
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                logger.warning("User not found for telegram notification: %s", user_id)
                return False

            # extra_data 또는 별도 필드에서 telegram_chat_id 가져오기
            chat_id = getattr(user, "telegram_chat_id", None)
            if not chat_id:
                logger.info("No telegram_chat_id for user %s", user_id)
                return False

            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=message)
            logger.info("Telegram notification sent to user %s", user_id)
            return True

        except ImportError:
            logger.warning("python-telegram-bot not installed")
            return False
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)
            return False

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """SMTP 이메일 알림 발송."""
        try:
            smtp_host = getattr(settings, "SMTP_HOST", None)
            smtp_port = getattr(settings, "SMTP_PORT", 587)
            smtp_user = getattr(settings, "SMTP_USER", None)
            smtp_password = getattr(settings, "SMTP_PASSWORD", None)
            from_email = getattr(settings, "SMTP_FROM_EMAIL", smtp_user)

            if not all([smtp_host, smtp_user, smtp_password]):
                logger.warning("SMTP settings not configured")
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            msg.attach(MIMEText(body, "html", "utf-8"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())

            logger.info("Email sent to %s: %s", to_email, subject)
            return True

        except Exception as e:
            logger.error("Email notification failed: %s", e)
            return False
