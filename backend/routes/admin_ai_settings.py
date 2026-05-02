from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_admin
from models.llm_provider_config import LLMProviderConfig
from models.llm_task_policy import LLMTaskPolicy
from models.user import User
from schemas.llm_settings import (
    LLMProviderConfigResponse,
    LLMProviderConfigUpdateRequest,
    LLMTaskPolicyResponse,
    LLMTaskPolicyUpdateRequest,
)
from services.llm.router import DEFAULT_PROVIDER_ROWS, DEFAULT_TASK_POLICIES

router = APIRouter(prefix="/api/v1/admin/ai-settings", tags=["admin-ai-settings"])


async def _ensure_default_provider_rows(db: AsyncSession) -> None:
    """Insert newly supported models without deleting operator settings."""
    changed = False
    for row in DEFAULT_PROVIDER_ROWS:
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider_name == row["provider_name"],
                LLMProviderConfig.model_name == row["model_name"],
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(LLMProviderConfig(**row))
            changed = True
            continue
        existing.label = row["label"]
        existing.supports_json = row["supports_json"]
        existing.supports_reasoning = row["supports_reasoning"]
        existing.max_tokens = row["max_tokens"]
        if existing.model_name == "gpt-5.5":
            existing.is_active = True
            existing.is_default = True
            existing.timeout_seconds = max(existing.timeout_seconds or 0, row["timeout_seconds"])
            changed = True
    default_result = await db.execute(select(LLMProviderConfig))
    for item in default_result.scalars().all():
        should_be_default = item.provider_name == "gpt" and item.model_name == "gpt-5.5"
        if item.is_default != should_be_default:
            item.is_default = should_be_default
            changed = True
    if changed:
        await db.commit()


async def _ensure_default_task_policies(db: AsyncSession) -> None:
    """Create missing policies and migrate old default GPT 5.4 routes to GPT 5.5."""
    changed = False
    for task_type, row in DEFAULT_TASK_POLICIES.items():
        result = await db.execute(select(LLMTaskPolicy).where(LLMTaskPolicy.task_type == task_type))
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(LLMTaskPolicy(task_type=task_type, **row))
            changed = True
            continue
        if existing.primary_provider == "gpt" and existing.primary_model == "gpt-5.4":
            existing.primary_model = row["primary_model"]
            changed = True
        if existing.fallback_enabled and existing.fallback_provider is None:
            existing.fallback_provider = row.get("fallback_provider")
            existing.fallback_model = row.get("fallback_model")
            changed = True
    if changed:
        await db.commit()


@router.get("/providers", response_model=list[LLMProviderConfigResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await _ensure_default_provider_rows(db)
    result = await db.execute(select(LLMProviderConfig).order_by(LLMProviderConfig.provider_name, LLMProviderConfig.model_name))
    return result.scalars().all()


@router.put("/providers/{provider_id}", response_model=LLMProviderConfigResponse)
async def update_provider(
    provider_id: str,
    body: LLMProviderConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(LLMProviderConfig).where(LLMProviderConfig.id == provider_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Provider config not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    if body.is_default:
        reset_result = await db.execute(select(LLMProviderConfig).where(LLMProviderConfig.id != row.id))
        for item in reset_result.scalars().all():
            item.is_default = False
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/task-policies", response_model=list[LLMTaskPolicyResponse])
async def list_task_policies(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await _ensure_default_task_policies(db)
    result = await db.execute(select(LLMTaskPolicy).order_by(LLMTaskPolicy.task_type))
    return result.scalars().all()


@router.put("/task-policies/{task_type}", response_model=LLMTaskPolicyResponse)
async def update_task_policy(
    task_type: str,
    body: LLMTaskPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(LLMTaskPolicy).where(LLMTaskPolicy.task_type == task_type))
    row = result.scalar_one_or_none()
    if not row:
        defaults = DEFAULT_TASK_POLICIES.get(task_type)
        if not defaults:
            raise HTTPException(status_code=404, detail="Unknown task type")
        row = LLMTaskPolicy(task_type=task_type, **defaults)
        db.add(row)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row
