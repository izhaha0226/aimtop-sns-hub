"""
채널 토큰 헬스 모니터링 및 재인증 알림 서비스.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.channel import ChannelConnection
from models.client import Client, ClientUser
from models.notification import Notification
from models.user import User
from services.notification_service import NotificationService
from services.sns_oauth import SNSOAuth

logger = logging.getLogger(__name__)
oauth_service = SNSOAuth()
AUTO_REFRESH_POLICIES = {
    "instagram": {"threshold": timedelta(days=5), "mode": "access_token"},
    "facebook": {"threshold": timedelta(days=5), "mode": "access_token"},
    "threads": {"threshold": timedelta(days=5), "mode": "access_token"},
    "youtube": {"threshold": timedelta(days=1), "mode": "refresh_token"},
    "x": {"threshold": timedelta(days=3), "mode": "refresh_token"},
    "blog": {"threshold": timedelta(days=3), "mode": "refresh_token"},
    "kakao": {"threshold": timedelta(days=3), "mode": "refresh_token"},
    "tiktok": {"threshold": timedelta(days=7), "mode": "refresh_token"},
}


def classify_token_health(token_expires_at: datetime | None, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    soon = now + timedelta(days=7)
    if not token_expires_at:
        return "unknown"
    if token_expires_at <= now:
        return "reauth_required"
    if token_expires_at <= soon:
        return "expiring"
    return "healthy"


class ChannelHealthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = NotificationService(db)

    async def monitor_and_notify(self) -> dict:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(ChannelConnection, Client)
            .join(Client, Client.id == ChannelConnection.client_id)
            .where(ChannelConnection.is_connected.is_(True))
        )
        rows = result.all()

        notified = 0
        scanned = 0
        refreshed = 0
        refresh_failed = 0
        for channel, client in rows:
            refresh_attempted, refresh_success = await self._maybe_refresh_channel(channel, now)
            if refresh_success:
                refreshed += 1
            elif refresh_attempted:
                refresh_failed += 1

            health = classify_token_health(channel.token_expires_at, now)
            if health not in {"expiring", "reauth_required"}:
                continue
            scanned += 1
            created = await self._notify_channel_issue(client, channel, health, now)
            notified += created

        if scanned or refreshed:
            logger.info("Channel health monitor scanned=%s notified=%s refreshed=%s refresh_failed=%s", scanned, notified, refreshed, refresh_failed)
        return {"scanned": scanned, "notified": notified, "refreshed": refreshed, "refresh_failed": refresh_failed}

    async def _maybe_refresh_channel(self, channel: ChannelConnection, now: datetime) -> tuple[bool, bool]:
        policy = self._get_refresh_policy(channel)
        if not policy:
            return False, False
        if channel.token_expires_at and channel.token_expires_at - now > policy["threshold"]:
            return False, False

        try:
            kwargs = {"platform": channel.channel_type}
            if policy["mode"] == "refresh_token":
                kwargs["current_refresh_token"] = channel.refresh_token
            else:
                kwargs["current_access_token"] = channel.access_token

            tokens = await oauth_service.refresh_token(**kwargs)
            expires_in = tokens.get("expires_in")
            token_expires_at = channel.token_expires_at
            if expires_in:
                token_expires_at = now + timedelta(seconds=int(expires_in))

            extra_data = dict(channel.extra_data or {})
            extra_data["last_token_refresh_at"] = now.isoformat()
            extra_data["refresh_policy"] = policy["mode"]

            channel.access_token = tokens["access_token"]
            channel.refresh_token = tokens.get("refresh_token", channel.refresh_token)
            channel.token_expires_at = token_expires_at
            channel.extra_data = extra_data
            await self.db.commit()
            await self.db.refresh(channel)
            logger.info("Channel token refreshed: %s %s", channel.client_id, channel.channel_type)
            return True, True
        except Exception as e:
            await self.db.rollback()
            logger.warning("Channel token refresh failed: %s %s %s", channel.client_id, channel.channel_type, e)
            return True, False

    def _get_refresh_policy(self, channel: ChannelConnection) -> dict | None:
        policy = AUTO_REFRESH_POLICIES.get(channel.channel_type)
        if not policy:
            return None
        if policy["mode"] == "refresh_token" and not channel.refresh_token:
            return None
        if policy["mode"] == "access_token" and not channel.access_token:
            return None
        return policy

    async def _notify_channel_issue(
        self,
        client: Client,
        channel: ChannelConnection,
        health: str,
        now: datetime,
    ) -> int:
        user_ids = await self._get_target_user_ids(client.id)
        if not user_ids:
            return 0

        title, message = self._build_message(client, channel, health)
        link_url = f"/clients/{client.id}?channel={channel.id}"
        created_count = 0

        for user_id in user_ids:
            if await self._already_notified_today(user_id, channel.id, health, now):
                continue

            await self.notification_service.create(
                client_id=client.id,
                user_id=user_id,
                type=f"channel_{health}",
                title=title,
                message=message,
                link_url=link_url,
            )
            created_count += 1

            await self.notification_service.send_telegram(user_id, f"[SNS Hub] {title}\n{message}")
            user = await self._get_user(user_id)
            if user and user.email:
                await self.notification_service.send_email(
                    to_email=user.email,
                    subject=f"[SNS Hub] {title}",
                    body=message.replace("\n", "<br>"),
                )

        return created_count

    async def _get_target_user_ids(self, client_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(ClientUser.user_id)
            .join(User, User.id == ClientUser.user_id)
            .where(
                ClientUser.client_id == client_id,
                User.status == "active",
            )
        )
        user_ids = [row[0] for row in result.all()]

        if user_ids:
            return user_ids

        fallback = await self.db.execute(
            select(User.id).where(User.status == "active")
        )
        return [row[0] for row in fallback.all()]

    async def _already_notified_today(
        self,
        user_id: uuid.UUID,
        channel_id: uuid.UUID,
        health: str,
        now: datetime,
    ) -> bool:
        since = now - timedelta(hours=24)
        result = await self.db.execute(
            select(Notification.id).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.type == f"channel_{health}",
                    Notification.link_url.is_not(None),
                    Notification.link_url.like(f"%{channel_id}%"),
                    Notification.created_at >= since,
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _get_user(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def _build_message(self, client: Client, channel: ChannelConnection, health: str) -> tuple[str, str]:
        channel_name = channel.account_name or channel.channel_type
        expires_at = (
            channel.token_expires_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if channel.token_expires_at
            else "미확인"
        )

        if health == "reauth_required":
            title = f"{client.name} · {channel.channel_type} 재인증 필요"
            message = (
                f"{channel_name} 채널 토큰이 만료되었습니다.\n"
                f"만료 시각: {expires_at}\n"
                "클라이언트 상세 페이지에서 재연동해 주세요."
            )
        else:
            title = f"{client.name} · {channel.channel_type} 만료 임박"
            message = (
                f"{channel_name} 채널 토큰 만료가 임박했습니다.\n"
                f"만료 예정: {expires_at}\n"
                "사전 재연동을 권장합니다."
            )

        return title, message
