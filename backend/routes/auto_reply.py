"""
자동 응답 규칙 관리 라우트
- CRUD for auto-reply rules
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from middleware.auth import get_current_user
from services.auto_reply_service import AutoReplyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auto-reply", tags=["auto-reply"])


class AutoReplyRuleCreate(BaseModel):
    client_id: uuid.UUID
    name: str
    platform: str = "all"  # instagram/youtube/blog/all
    trigger_type: str = "all"  # keyword/sentiment/all
    trigger_value: str | None = None
    reply_template: str | None = None
    is_active: bool = True


class AutoReplyRuleUpdate(BaseModel):
    name: str | None = None
    platform: str | None = None
    trigger_type: str | None = None
    trigger_value: str | None = None
    reply_template: str | None = None
    is_active: bool | None = None


class AutoReplyRuleResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    name: str
    platform: str
    trigger_type: str
    trigger_value: str | None
    reply_template: str | None
    is_active: bool
    created_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("/rules")
async def list_rules(
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """자동 응답 규칙 목록"""
    service = AutoReplyService(db)
    rules = await service.get_rules(client_id)
    return {
        "items": [
            {
                "id": str(r.id),
                "client_id": str(r.client_id),
                "name": r.name,
                "platform": r.platform,
                "trigger_type": r.trigger_type,
                "trigger_value": r.trigger_value,
                "reply_template": r.reply_template,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@router.post("/rules", status_code=201)
async def create_rule(
    body: AutoReplyRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """자동 응답 규칙 생성"""
    service = AutoReplyService(db)
    rule = await service.create_rule(body.model_dump())
    return {
        "id": str(rule.id),
        "name": rule.name,
        "status": "created",
    }


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    body: AutoReplyRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """자동 응답 규칙 수정"""
    service = AutoReplyService(db)
    try:
        rule = await service.update_rule(rule_id, body.model_dump(exclude_none=True))
        return {
            "id": str(rule.id),
            "name": rule.name,
            "status": "updated",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """자동 응답 규칙 삭제"""
    service = AutoReplyService(db)
    success = await service.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다")
    return {"status": "deleted", "rule_id": str(rule_id)}
