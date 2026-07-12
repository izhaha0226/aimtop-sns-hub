"""전 채널 자동화 API"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.automation import (
    ActionLogResponse,
    CapabilityItem,
    CommentSyncRequest,
    MaterialGenerateRequest,
    MaterialGenerateResponse,
    PolicyResponse,
    PolicyUpsert,
    RunResponse,
)
from services.automation_service import AutomationService
from services.channel_capability import list_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


@router.get("/capabilities", response_model=list[CapabilityItem])
async def get_capabilities(_: User = Depends(get_current_user)):
    return list_capabilities()


@router.get("/policies", response_model=list[PolicyResponse])
async def list_policies(
    client_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = AutomationService(db)
    return await service.list_policies(client_id)


@router.put("/policies/{platform}", response_model=PolicyResponse)
async def upsert_policy(
    platform: str,
    body: PolicyUpsert,
    client_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = AutomationService(db)
    try:
        policy = await service.upsert_policy(client_id, platform, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items = await service.list_policies(client_id)
    for item in items:
        if item["platform"] == platform.strip().lower():
            return item
    return {
        "id": policy.id,
        "client_id": policy.client_id,
        "platform": policy.platform,
        "enabled": policy.enabled,
        "require_approval": policy.require_approval,
        "daily_limit": policy.daily_limit,
        "auto_reply_enabled": policy.auto_reply_enabled,
        "quiet_hours_json": policy.quiet_hours_json,
        "config_json": policy.config_json,
        "capability": None,
        "updated_at": policy.updated_at,
    }


@router.post("/materials/generate", response_model=MaterialGenerateResponse)
async def generate_materials(
    body: MaterialGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AutomationService(db)
    try:
        result = await service.generate_materials(
            client_id=body.client_id,
            author_id=current_user.id,
            title=body.title,
            brief=body.brief,
            objective=body.objective,
            target_audience=body.target_audience,
            core_message=body.core_message,
            channels=body.channels,
            require_approval=body.require_approval,
            generate_images=body.generate_images,
            use_fallback_storyline=body.use_fallback_storyline,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("material generate failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    run = result["run"]
    return {
        "ok": result["ok"],
        "run": run,
        "topic_id": result.get("topic_id"),
        "contents": result.get("contents") or [],
        "errors": result.get("errors") or [],
    }


@router.post("/comments/sync")
async def sync_comments(
    body: CommentSyncRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = AutomationService(db)
    try:
        return await service.sync_comments(
            client_id=body.client_id,
            platform=body.platform,
            apply_auto_reply=body.apply_auto_reply,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs", response_model=list[RunResponse])
async def list_runs(
    client_id: uuid.UUID = Query(...),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await AutomationService(db).list_runs(client_id, limit=limit)


@router.get("/actions", response_model=list[ActionLogResponse])
async def list_actions(
    client_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await AutomationService(db).list_actions(client_id, limit=limit)
