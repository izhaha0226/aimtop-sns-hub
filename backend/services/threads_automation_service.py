from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.threads_automation import (
    ThreadsActionLog,
    ThreadsApprovalQueue,
    ThreadsDraft,
    ThreadsLearningEvent,
    ThreadsPersona,
    ThreadsSafetyFilter,
    ThreadsTargetRule,
)


def _normalise_list(value: list | None) -> list[str]:
    if not value:
        return []
    return [str(item).strip().lower() for item in value if str(item).strip()]


class ThreadsAutomationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_personas(self, client_id: uuid.UUID | None = None) -> list[ThreadsPersona]:
        stmt = select(ThreadsPersona).order_by(ThreadsPersona.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsPersona.client_id == client_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_persona(self, persona_id: uuid.UUID) -> ThreadsPersona | None:
        result = await self.db.execute(select(ThreadsPersona).where(ThreadsPersona.id == persona_id))
        return result.scalar_one_or_none()

    async def create_persona(self, **data) -> ThreadsPersona:
        persona = ThreadsPersona(**data)
        self.db.add(persona)
        await self.db.commit()
        await self.db.refresh(persona)
        return persona

    async def update_persona(self, persona: ThreadsPersona, **data) -> ThreadsPersona:
        for key, value in data.items():
            setattr(persona, key, value)
        await self.db.commit()
        await self.db.refresh(persona)
        return persona

    async def list_target_rules(self, client_id: uuid.UUID | None = None) -> list[ThreadsTargetRule]:
        stmt = select(ThreadsTargetRule).order_by(ThreadsTargetRule.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsTargetRule.client_id == client_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_target_rule(self, rule_id: uuid.UUID) -> ThreadsTargetRule | None:
        result = await self.db.execute(select(ThreadsTargetRule).where(ThreadsTargetRule.id == rule_id))
        return result.scalar_one_or_none()

    async def create_target_rule(self, **data) -> ThreadsTargetRule:
        rule = ThreadsTargetRule(**data)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update_target_rule(self, rule: ThreadsTargetRule, **data) -> ThreadsTargetRule:
        for key, value in data.items():
            setattr(rule, key, value)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def list_safety_filters(self, client_id: uuid.UUID | None = None) -> list[ThreadsSafetyFilter]:
        stmt = select(ThreadsSafetyFilter).order_by(ThreadsSafetyFilter.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsSafetyFilter.client_id == client_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_safety_filter(self, filter_id: uuid.UUID) -> ThreadsSafetyFilter | None:
        result = await self.db.execute(select(ThreadsSafetyFilter).where(ThreadsSafetyFilter.id == filter_id))
        return result.scalar_one_or_none()

    async def create_safety_filter(self, **data) -> ThreadsSafetyFilter:
        safety_filter = ThreadsSafetyFilter(**data)
        self.db.add(safety_filter)
        await self.db.commit()
        await self.db.refresh(safety_filter)
        return safety_filter

    async def update_safety_filter(self, safety_filter: ThreadsSafetyFilter, **data) -> ThreadsSafetyFilter:
        for key, value in data.items():
            setattr(safety_filter, key, value)
        await self.db.commit()
        await self.db.refresh(safety_filter)
        return safety_filter

    async def list_drafts(self, client_id: uuid.UUID | None = None, status: str | None = None) -> list[ThreadsDraft]:
        stmt = select(ThreadsDraft).order_by(ThreadsDraft.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsDraft.client_id == client_id)
        if status:
            stmt = stmt.where(ThreadsDraft.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_draft(self, draft_id: uuid.UUID) -> ThreadsDraft | None:
        result = await self.db.execute(select(ThreadsDraft).where(ThreadsDraft.id == draft_id))
        return result.scalar_one_or_none()

    async def create_draft(self, requested_by_id: uuid.UUID | None = None, **data) -> ThreadsDraft:
        persona = await self.get_persona(data["persona_id"]) if data.get("persona_id") else None
        rule = await self.get_target_rule(data["target_rule_id"]) if data.get("target_rule_id") else None
        fit_score = self._score_fit(data.get("target_post_text"), data.get("target_author_handle"), rule)
        safety_score, labels = await self._score_safety(data["client_id"], data.get("draft_text") or data.get("target_post_text"))
        action_type = data.get("action_type") or "comment"
        approval_required = action_type in {"comment", "repost"} or safety_score < 0.75
        status = "approval_required" if approval_required else "queued"

        draft = ThreadsDraft(
            **data,
            fit_score=fit_score,
            safety_score=safety_score,
            safety_labels_json=labels,
            status=status,
            approval_required=approval_required,
            provider_badge_label=(persona.provider_badge_label if persona else None),
            author_transparency=(persona.author_transparency if persona else None),
            simulation_status=status,
        )
        self.db.add(draft)
        await self.db.flush()
        queue_reason = "댓글/리포스트는 사람 승인 필요" if approval_required else "실제 Threads write 비활성, 자동화 큐만 생성"
        self.db.add(
            ThreadsApprovalQueue(
                client_id=draft.client_id,
                draft_id=draft.id,
                action_type=action_type,
                status="queued",
                queue_reason=queue_reason,
                requested_by_id=requested_by_id,
            )
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def update_draft(self, draft: ThreadsDraft, **data) -> ThreadsDraft:
        for key, value in data.items():
            setattr(draft, key, value)
        if "draft_text" in data:
            draft.safety_score, draft.safety_labels_json = await self._score_safety(draft.client_id, draft.draft_text)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def list_approvals(self, client_id: uuid.UUID | None = None, status: str | None = None) -> list[ThreadsApprovalQueue]:
        stmt = select(ThreadsApprovalQueue).order_by(ThreadsApprovalQueue.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsApprovalQueue.client_id == client_id)
        if status:
            stmt = stmt.where(ThreadsApprovalQueue.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_approval(self, approval_id: uuid.UUID) -> ThreadsApprovalQueue | None:
        result = await self.db.execute(select(ThreadsApprovalQueue).where(ThreadsApprovalQueue.id == approval_id))
        return result.scalar_one_or_none()

    async def update_approval_status(
        self,
        approval: ThreadsApprovalQueue,
        status: str,
        reviewed_by_id: uuid.UUID,
        review_note: str | None = None,
    ) -> ThreadsApprovalQueue:
        approval.status = status
        approval.reviewed_by_id = reviewed_by_id
        approval.reviewed_at = datetime.now(timezone.utc)
        approval.review_note = review_note
        draft = await self.get_draft(approval.draft_id)
        if draft:
            draft.status = "queued" if status == "approved" else status
            draft.simulation_status = draft.status
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def list_actions(self, client_id: uuid.UUID | None = None) -> list[ThreadsActionLog]:
        stmt = select(ThreadsActionLog).order_by(ThreadsActionLog.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsActionLog.client_id == client_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_action_log(self, **data) -> ThreadsActionLog:
        status = "approval_required"
        approval_id = data.get("approval_id")
        if approval_id:
            approval = await self.get_approval(approval_id)
            if approval and approval.status == "approved":
                status = "simulated"
            elif approval and approval.status == "rejected":
                status = "rejected"
        elif data.get("action_type") == "like":
            status = "queued"
        action = ThreadsActionLog(
            **data,
            status=status,
            simulation_status=status,
            external_write_enabled=False,
            message="실제 Threads write 비활성. 승인 큐/시뮬레이션 기록만 생성했습니다.",
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def list_learning_events(self, client_id: uuid.UUID | None = None) -> list[ThreadsLearningEvent]:
        stmt = select(ThreadsLearningEvent).order_by(ThreadsLearningEvent.created_at.desc())
        if client_id:
            stmt = stmt.where(ThreadsLearningEvent.client_id == client_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_learning_event(self, **data) -> ThreadsLearningEvent:
        event = ThreadsLearningEvent(**data)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    def _score_fit(self, text: str | None, author_handle: str | None, rule: ThreadsTargetRule | None) -> float:
        if not rule:
            return 0.5
        haystack = f"{text or ''} {author_handle or ''}".lower()
        signals = (
            _normalise_list(rule.keywords_json)
            + _normalise_list(rule.hashtags_json)
            + _normalise_list(rule.competitor_handles_json)
        )
        if not signals:
            return 0.5
        matches = sum(1 for signal in signals if signal.lstrip("#@") in haystack)
        return round(min(1.0, max(0.1, matches / max(1, len(signals)) + 0.35)), 4)

    async def _score_safety(self, client_id: uuid.UUID, text: str | None) -> tuple[float, list[str]]:
        body = (text or "").lower()
        result = await self.db.execute(
            select(ThreadsSafetyFilter).where(
                ThreadsSafetyFilter.client_id == client_id,
                ThreadsSafetyFilter.is_active == True,  # noqa: E712
            )
        )
        filters = list(result.scalars().all())
        blocked_terms = [term for item in filters for term in _normalise_list(item.blocked_terms_json)]
        sensitive_topics = [term for item in filters for term in _normalise_list(item.sensitive_topics_json)]
        labels: list[str] = []
        penalty = 0.0
        for term in blocked_terms:
            if term and term in body:
                labels.append(f"blocked_term:{term}")
                penalty += 0.5
        for topic in sensitive_topics:
            if topic and topic in body:
                labels.append(f"sensitive_topic:{topic}")
                penalty += 0.2
        if len(body) > 500:
            labels.append("length_warning")
            penalty += 0.1
        score = round(max(0.0, 1.0 - penalty), 4)
        if not labels:
            labels.append("deterministic_fallback_pass")
        return score, labels
