"""전 채널 소재·운영·댓글 자동화 오케스트레이션"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.automation import AutomationActionLog, AutomationRun, ChannelAutomationPolicy
from models.channel import ChannelConnection
from models.comment import Comment
from models.content import Content
from models.content_topic import ContentTopic
from services.auto_reply_service import AutoReplyService
from services.channel_capability import (
    ALL_PLATFORMS,
    assert_capability,
    get_capability,
    list_capabilities,
    material_platforms,
)
from services.comment_service import CommentService
from services.content_topic_service import (
    build_fallback_storyline,
    create_channel_contents,
    generate_card_images,
    generate_topic_storyline,
)

logger = logging.getLogger(__name__)


class AutomationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── capability ──────────────────────────────────────────────
    def capabilities(self) -> list[dict[str, Any]]:
        return list_capabilities()

    # ── policies ────────────────────────────────────────────────
    async def list_policies(self, client_id: uuid.UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(ChannelAutomationPolicy).where(ChannelAutomationPolicy.client_id == client_id)
        )
        existing = {p.platform: p for p in result.scalars().all()}
        items: list[dict[str, Any]] = []
        for platform in ALL_PLATFORMS:
            policy = existing.get(platform)
            cap = get_capability(platform)
            if policy is None:
                items.append(
                    {
                        "id": None,
                        "client_id": client_id,
                        "platform": platform,
                        "enabled": False,
                        "require_approval": True,
                        "daily_limit": 3,
                        "auto_reply_enabled": False,
                        "quiet_hours_json": None,
                        "config_json": None,
                        "capability": cap,
                        "updated_at": None,
                    }
                )
            else:
                items.append(
                    {
                        "id": policy.id,
                        "client_id": policy.client_id,
                        "platform": policy.platform,
                        "enabled": policy.enabled,
                        "require_approval": policy.require_approval,
                        "daily_limit": policy.daily_limit,
                        "auto_reply_enabled": policy.auto_reply_enabled,
                        "quiet_hours_json": policy.quiet_hours_json,
                        "config_json": policy.config_json,
                        "capability": cap,
                        "updated_at": policy.updated_at,
                    }
                )
        return items

    async def upsert_policy(self, client_id: uuid.UUID, platform: str, data: dict[str, Any]) -> ChannelAutomationPolicy:
        platform = platform.strip().lower()
        if platform not in ALL_PLATFORMS:
            raise ValueError(f"지원하지 않는 채널: {platform}")
        result = await self.db.execute(
            select(ChannelAutomationPolicy).where(
                ChannelAutomationPolicy.client_id == client_id,
                ChannelAutomationPolicy.platform == platform,
            )
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            policy = ChannelAutomationPolicy(client_id=client_id, platform=platform)
            self.db.add(policy)

        for field in (
            "enabled",
            "require_approval",
            "daily_limit",
            "auto_reply_enabled",
            "quiet_hours_json",
            "config_json",
        ):
            if field in data and data[field] is not None:
                setattr(policy, field, data[field])

        # 발행 미지원 채널은 enabled 강제 해제
        cap = get_capability(platform) or {}
        if policy.enabled and not cap.get("automation_ready"):
            policy.enabled = False
            raise ValueError(f"{platform} 채널은 아직 자동화 준비가 되지 않았습니다")

        await self.db.commit()
        await self.db.refresh(policy)
        await self._log(
            client_id=client_id,
            platform=platform,
            action="policy_upsert",
            ok=True,
            target_id=str(policy.id),
            evidence={"enabled": policy.enabled, "require_approval": policy.require_approval},
        )
        return policy

    # ── materials ───────────────────────────────────────────────
    async def generate_materials(
        self,
        *,
        client_id: uuid.UUID,
        author_id: uuid.UUID | None,
        title: str,
        brief: str | None,
        objective: str | None,
        target_audience: str | None,
        core_message: str | None,
        channels: list[str],
        require_approval: bool = True,
        generate_images: bool = False,
        use_fallback_storyline: bool = False,
    ) -> dict[str, Any]:
        if not client_id:
            raise ValueError("client_id는 필수입니다")

        requested = []
        for ch in channels or []:
            p = str(ch).strip().lower()
            if p and p not in requested:
                requested.append(p)
        if not requested:
            requested = ["instagram", "facebook", "threads"]

        allowed = set(material_platforms())
        errors: list[dict[str, Any]] = []
        valid_channels: list[str] = []
        for platform in requested:
            try:
                assert_capability(platform, "material_variant")
                if platform not in allowed:
                    raise ValueError(f"{platform} 소재 변형 미지원")
                valid_channels.append(platform)
            except ValueError as exc:
                errors.append({"platform": platform, "error": str(exc)})

        if not valid_channels:
            raise ValueError("생성 가능한 채널이 없습니다: " + "; ".join(e["error"] for e in errors))

        run = await self._start_run(client_id, "material")
        try:
            topic = ContentTopic(
                client_id=client_id,
                author_id=author_id,
                title=title.strip(),
                brief=brief,
                objective=objective,
                target_audience=target_audience,
                core_message=core_message,
                source_metadata={
                    "automation": True,
                    "channels": valid_channels,
                    "require_approval": require_approval,
                },
                status="draft",
            )
            self.db.add(topic)
            await self.db.flush()

            if use_fallback_storyline:
                topic.card_storyline = build_fallback_storyline(topic)
            else:
                topic.card_storyline = await generate_topic_storyline(topic, self.db)

            if generate_images:
                try:
                    topic.shared_media_urls = await generate_card_images(topic)
                except Exception as exc:
                    logger.warning("automation image gen failed: %s", exc)
                    errors.append({"platform": "*", "error": f"이미지 생성 실패: {exc}"})

            # 채널 연결 매핑 (있으면 content.channel_connection_id 후보)
            channel_map = await self._channel_map(client_id)

            variants = await create_channel_contents(topic, self.db, valid_channels)
            content_rows: list[dict[str, Any]] = []

            for variant in variants:
                platform = variant.get("platform")
                content_id = variant.get("content_id")
                if not content_id:
                    continue
                result = await self.db.execute(select(Content).where(Content.id == content_id))
                content = result.scalar_one_or_none()
                if not content:
                    continue

                conn = channel_map.get(platform)
                if conn:
                    content.channel_connection_id = conn.id

                meta = dict(content.source_metadata or {})
                meta["automation"] = True
                meta["require_approval"] = require_approval
                meta["run_id"] = str(run.id)
                content.source_metadata = meta

                if require_approval:
                    content.status = "pending_approval"
                else:
                    content.status = "approved"

                content_rows.append(
                    {
                        "content_id": str(content.id),
                        "platform": platform,
                        "title": content.title,
                        "status": content.status,
                        "channel_connection_id": str(content.channel_connection_id) if content.channel_connection_id else None,
                        "char_count": len(content.text or ""),
                    }
                )
                await self._log(
                    client_id=client_id,
                    run_id=run.id,
                    platform=platform,
                    action="material_variant_created",
                    ok=True,
                    target_id=str(content.id),
                    evidence={"status": content.status, "title": content.title},
                )

            topic.status = "ready" if content_rows else "draft"
            await self.db.commit()

            summary = {
                "topic_id": str(topic.id),
                "channels": valid_channels,
                "created": len(content_rows),
                "errors": errors,
            }
            await self._finish_run(run, status="ok" if content_rows else "error", summary=summary)
            return {
                "ok": bool(content_rows),
                "run": run,
                "topic_id": topic.id,
                "contents": content_rows,
                "errors": errors,
            }
        except Exception as exc:
            await self.db.rollback()
            await self._finish_run(run, status="error", summary={"error": str(exc)}, error=str(exc))
            raise

    # ── comments ────────────────────────────────────────────────
    async def sync_comments(
        self,
        *,
        client_id: uuid.UUID,
        platform: str | None = None,
        apply_auto_reply: bool = True,
    ) -> dict[str, Any]:
        run = await self._start_run(client_id, "comment_sync")
        query = select(ChannelConnection).where(
            ChannelConnection.client_id == client_id,
            ChannelConnection.is_connected == True,  # noqa: E712
        )
        if platform:
            query = query.where(ChannelConnection.channel_type == platform.strip().lower())

        result = await self.db.execute(query)
        channels = list(result.scalars().all())
        service = CommentService(self.db)
        auto_reply = AutoReplyService(self.db)

        synced = 0
        new_comments = 0
        auto_replied = 0
        escalated = 0
        errors: list[dict[str, Any]] = []

        for channel in channels:
            try:
                assert_capability(channel.channel_type, "comment_fetch")
            except ValueError as exc:
                errors.append({"channel_id": str(channel.id), "platform": channel.channel_type, "error": str(exc)})
                continue
            try:
                added = await service.sync_comments(channel.id)
                new_comments += added
                synced += 1
                await self._log(
                    client_id=client_id,
                    run_id=run.id,
                    platform=channel.channel_type,
                    action="comment_sync",
                    ok=True,
                    target_id=str(channel.id),
                    evidence={"new_comments": added},
                )
            except Exception as exc:
                errors.append({"channel_id": str(channel.id), "platform": channel.channel_type, "error": str(exc)})
                await self._log(
                    client_id=client_id,
                    run_id=run.id,
                    platform=channel.channel_type,
                    action="comment_sync",
                    ok=False,
                    target_id=str(channel.id),
                    error=str(exc),
                )

        if apply_auto_reply:
            # 미응답 댓글에 자동응답 / 위험 에스컬레이션
            pending = await self.db.execute(
                select(Comment)
                .join(ChannelConnection, Comment.channel_connection_id == ChannelConnection.id)
                .where(
                    ChannelConnection.client_id == client_id,
                    Comment.replied_at.is_(None),
                    Comment.is_hidden == False,  # noqa: E712
                )
                .order_by(Comment.created_at.desc())
                .limit(100)
            )
            for comment in pending.scalars().all():
                try:
                    if AutoReplyService.is_danger_comment(comment.text or ""):
                        escalated += 1
                        await self._log(
                            client_id=client_id,
                            run_id=run.id,
                            platform=None,
                            action="comment_escalated",
                            ok=True,
                            target_id=str(comment.id),
                            evidence={"reason": "danger_keyword", "text": (comment.text or "")[:120]},
                        )
                        continue
                    if await auto_reply.check_and_reply(comment):
                        auto_replied += 1
                        await self._log(
                            client_id=client_id,
                            run_id=run.id,
                            platform=None,
                            action="auto_reply",
                            ok=True,
                            target_id=str(comment.id),
                        )
                except Exception as exc:
                    errors.append({"comment_id": str(comment.id), "error": str(exc)})

        summary = {
            "synced_channels": synced,
            "new_comments": new_comments,
            "auto_replied": auto_replied,
            "escalated": escalated,
            "errors": errors,
        }
        await self._finish_run(run, status="ok", summary=summary)
        return {"ok": True, "run": run, **summary}

    async def list_runs(self, client_id: uuid.UUID, limit: int = 30) -> list[AutomationRun]:
        result = await self.db.execute(
            select(AutomationRun)
            .where(AutomationRun.client_id == client_id)
            .order_by(AutomationRun.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_actions(self, client_id: uuid.UUID, limit: int = 50) -> list[AutomationActionLog]:
        result = await self.db.execute(
            select(AutomationActionLog)
            .where(AutomationActionLog.client_id == client_id)
            .order_by(AutomationActionLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def enabled_auto_reply_client_ids(self) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(ChannelAutomationPolicy.client_id)
            .where(
                ChannelAutomationPolicy.enabled == True,  # noqa: E712
                ChannelAutomationPolicy.auto_reply_enabled == True,  # noqa: E712
            )
            .distinct()
        )
        return list(result.scalars().all())

    async def count_today_published(self, client_id: uuid.UUID, platform: str) -> int:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count())
            .select_from(Content)
            .where(
                Content.client_id == client_id,
                Content.target_platform == platform,
                Content.status == "published",
                Content.published_at >= start,
            )
        )
        return int(result.scalar() or 0)

    # ── internals ───────────────────────────────────────────────
    async def _channel_map(self, client_id: uuid.UUID) -> dict[str, ChannelConnection]:
        result = await self.db.execute(
            select(ChannelConnection).where(
                ChannelConnection.client_id == client_id,
                ChannelConnection.is_connected == True,  # noqa: E712
            )
        )
        mapping: dict[str, ChannelConnection] = {}
        for ch in result.scalars().all():
            # 첫 연결 채널 사용
            if ch.channel_type not in mapping:
                mapping[ch.channel_type] = ch
        return mapping

    async def _start_run(self, client_id: uuid.UUID, kind: str) -> AutomationRun:
        run = AutomationRun(client_id=client_id, kind=kind, status="running")
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def _finish_run(
        self,
        run: AutomationRun,
        *,
        status: str,
        summary: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        # re-attach if session was rolled back
        result = await self.db.execute(select(AutomationRun).where(AutomationRun.id == run.id))
        row = result.scalar_one_or_none() or run
        row.status = status
        row.summary_json = summary
        row.error = error
        row.finished_at = datetime.now(timezone.utc)
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        run.status = row.status
        run.summary_json = row.summary_json
        run.error = row.error
        run.finished_at = row.finished_at

    async def _log(
        self,
        *,
        client_id: uuid.UUID,
        action: str,
        ok: bool,
        platform: str | None = None,
        run_id: uuid.UUID | None = None,
        target_id: str | None = None,
        evidence: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        log = AutomationActionLog(
            run_id=run_id,
            client_id=client_id,
            platform=platform,
            action=action,
            target_id=target_id,
            ok=ok,
            evidence_json=evidence,
            error=error,
        )
        self.db.add(log)
        await self.db.commit()
