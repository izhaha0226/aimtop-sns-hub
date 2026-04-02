"""
자동 응답 서비스
- 규칙 기반 자동 답글
- 키워드 매칭 / 감성 매칭
"""

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auto_reply import AutoReply
from models.comment import Comment
from services.comment_service import CommentService

logger = logging.getLogger(__name__)


class AutoReplyService:
    """자동 응답 규칙 관리 및 실행"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_reply(self, comment: Comment) -> bool:
        """
        등록된 규칙에 매칭되는지 확인하고 자동 답글 전송
        Returns: 자동 답글 전송 여부
        """
        if not comment.text or comment.replied_at:
            return False

        # 해당 채널의 클라이언트 ID를 통해 규칙 조회
        # comment -> content -> client_id 경로로 조회
        from models.content import Content

        content_result = await self.db.execute(
            select(Content).where(Content.id == comment.content_id)
        )
        content = content_result.scalar_one_or_none()
        if not content or not content.client_id:
            return False

        rules = await self.get_rules(content.client_id, active_only=True)
        if not rules:
            return False

        comment_service = CommentService(self.db)

        for rule in rules:
            if await self._matches_rule(rule, comment, comment_service):
                try:
                    reply_text = self._render_template(rule.reply_template, comment)
                    await comment_service.reply_comment(comment.id, reply_text)
                    logger.info(
                        f"Auto-reply sent: rule={rule.name}, comment={comment.id}"
                    )
                    return True
                except Exception as e:
                    logger.error(
                        f"Auto-reply failed: rule={rule.name}, "
                        f"comment={comment.id}, error={e}"
                    )
                    continue

        return False

    async def _matches_rule(
        self, rule: AutoReply, comment: Comment, comment_service: CommentService
    ) -> bool:
        """규칙이 댓글에 매칭되는지 확인"""
        # 플랫폼 필터
        if rule.platform != "all" and comment.channel_connection_id:
            from models.channel import ChannelConnection

            ch_result = await self.db.execute(
                select(ChannelConnection).where(
                    ChannelConnection.id == comment.channel_connection_id
                )
            )
            channel = ch_result.scalar_one_or_none()
            if channel and channel.channel_type != rule.platform:
                return False

        text = comment.text or ""

        if rule.trigger_type == "keyword":
            # 키워드 매칭 (쉼표로 구분된 키워드 중 하나라도 포함)
            if not rule.trigger_value:
                return False
            keywords = [k.strip().lower() for k in rule.trigger_value.split(",")]
            text_lower = text.lower()
            return any(kw in text_lower for kw in keywords if kw)

        elif rule.trigger_type == "sentiment":
            # 감성 매칭
            if not rule.trigger_value:
                return False
            sentiment = await comment_service.analyze_sentiment(text)
            # 댓글에 감성 저장
            comment.sentiment = sentiment
            return sentiment == rule.trigger_value.strip().lower()

        elif rule.trigger_type == "all":
            # 모든 댓글에 매칭
            return True

        return False

    @staticmethod
    def _render_template(template: str | None, comment: Comment) -> str:
        """답글 템플릿 렌더링 (변수 치환)"""
        if not template:
            return "감사합니다!"

        text = template
        text = text.replace("{{author}}", comment.author_name or "")
        text = text.replace("{{comment}}", comment.text or "")
        return text

    async def get_rules(
        self, client_id: uuid.UUID, active_only: bool = False
    ) -> list:
        """규칙 목록 조회"""
        query = select(AutoReply).where(AutoReply.client_id == client_id)
        if active_only:
            query = query.where(AutoReply.is_active == True)
        query = query.order_by(AutoReply.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_rule(self, data: dict) -> AutoReply:
        """규칙 생성"""
        rule = AutoReply(**data)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        logger.info(f"Auto-reply rule created: {rule.name} (id={rule.id})")
        return rule

    async def update_rule(self, rule_id: uuid.UUID, data: dict) -> AutoReply:
        """규칙 수정"""
        result = await self.db.execute(
            select(AutoReply).where(AutoReply.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise ValueError("규칙을 찾을 수 없습니다")

        for field, value in data.items():
            if hasattr(rule, field) and value is not None:
                setattr(rule, field, value)

        await self.db.commit()
        await self.db.refresh(rule)
        logger.info(f"Auto-reply rule updated: {rule.name} (id={rule.id})")
        return rule

    async def delete_rule(self, rule_id: uuid.UUID) -> bool:
        """규칙 삭제"""
        result = await self.db.execute(
            select(AutoReply).where(AutoReply.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return False

        await self.db.delete(rule)
        await self.db.commit()
        logger.info(f"Auto-reply rule deleted: {rule.name} (id={rule_id})")
        return True
