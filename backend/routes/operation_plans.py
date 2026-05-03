import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.operation_plan import OperationPlan
from models.client import Client
from models.content import Content
from models.user import User
from schemas.operation_plan import (
    OperationPlanAction,
    OperationPlanCreate,
    OperationPlanDraftsResponse,
    OperationPlanListResponse,
    OperationPlanResponse,
    OperationPlanUpdate,
)
from services.operation_plan_service import (
    OperationPlanWorkflowError,
    transition_operation_plan_status,
    utc_now,
)
from services.operation_plan_draft_service import OperationPlanDraftError, build_content_draft_specs_from_plan

router = APIRouter(prefix="/api/v1/operation-plans", tags=["operation-plans"])


async def _get_operation_plan_or_404(plan_id: uuid.UUID, db: AsyncSession) -> OperationPlan:
    result = await db.execute(select(OperationPlan).where(OperationPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="운영계획을 찾을 수 없습니다")
    return plan


def _brand_candidates_from_payload(data: dict | None) -> set[str]:
    if not isinstance(data, dict):
        return set()
    candidates = {
        str(data.get("brand_name") or "").strip(),
    }
    request_payload = data.get("request_payload")
    if isinstance(request_payload, dict):
        candidates.add(str(request_payload.get("brand_name") or "").strip())
    plan_payload = data.get("plan_payload")
    if isinstance(plan_payload, dict):
        candidates.add(str(plan_payload.get("brand_name") or "").strip())
    return {candidate for candidate in candidates if candidate}


async def _ensure_no_cross_client_brand_conflict(
    *,
    db: AsyncSession,
    client_id: uuid.UUID | None,
    payload: dict,
) -> None:
    if not client_id:
        return
    for brand_name in _brand_candidates_from_payload(payload):
        normalized_brand = brand_name.lower()
        result = await db.execute(
            select(Client).where(
                func.lower(Client.name) == normalized_brand,
                Client.id != client_id,
                Client.is_deleted.is_(False),
            )
        )
        conflicting_client = result.scalar_one_or_none()
        if conflicting_client:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"'{brand_name}' 브랜드는 다른 클라이언트({conflicting_client.name})에 속합니다. "
                    "상단 클라이언트를 먼저 맞춘 뒤 운영계획을 다시 생성해주세요."
                ),
            )


@router.get("", response_model=OperationPlanListResponse)
async def list_operation_plans(
    client_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(OperationPlan)
    if client_id:
        query = query.where(OperationPlan.client_id == client_id)
    if status:
        query = query.where(OperationPlan.status == status)
    query = query.order_by(OperationPlan.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": len(items)}


@router.post("", response_model=OperationPlanResponse, status_code=201)
async def create_operation_plan(
    body: OperationPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = body.model_dump()
    await _ensure_no_cross_client_brand_conflict(db=db, client_id=body.client_id, payload=payload)
    plan = OperationPlan(
        **payload,
        author_id=current_user.id,
        status="draft",
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=OperationPlanResponse)
async def get_operation_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _get_operation_plan_or_404(plan_id, db)


@router.put("/{plan_id}", response_model=OperationPlanResponse)
async def update_operation_plan(
    plan_id: uuid.UUID,
    body: OperationPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    plan = await _get_operation_plan_or_404(plan_id, db)
    updates = body.model_dump(exclude_none=True)
    effective_client_id = updates.get("client_id", plan.client_id)
    await _ensure_no_cross_client_brand_conflict(db=db, client_id=effective_client_id, payload=updates)
    for field, value in updates.items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{plan_id}/submit", response_model=OperationPlanResponse)
async def submit_operation_plan(
    plan_id: uuid.UUID,
    body: OperationPlanAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_operation_plan_or_404(plan_id, db)
    try:
        plan.status = transition_operation_plan_status(plan.status, "submit", current_user.role)
    except OperationPlanWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    plan.approval_memo = body.memo
    plan.rejected_reason = None
    plan.submitted_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{plan_id}/approve", response_model=OperationPlanResponse)
async def approve_operation_plan(
    plan_id: uuid.UUID,
    body: OperationPlanAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_operation_plan_or_404(plan_id, db)
    try:
        plan.status = transition_operation_plan_status(plan.status, "approve", current_user.role)
    except OperationPlanWorkflowError as exc:
        status_code = 403 if "권한" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    plan.approver_id = current_user.id
    plan.approval_memo = body.memo
    plan.approved_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{plan_id}/reject", response_model=OperationPlanResponse)
async def reject_operation_plan(
    plan_id: uuid.UUID,
    body: OperationPlanAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_operation_plan_or_404(plan_id, db)
    try:
        plan.status = transition_operation_plan_status(plan.status, "reject", current_user.role)
    except OperationPlanWorkflowError as exc:
        status_code = 403 if "권한" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    plan.approver_id = current_user.id
    plan.rejected_reason = body.memo
    plan.rejected_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{plan_id}/generate-drafts", response_model=OperationPlanDraftsResponse, status_code=201)
async def generate_operation_plan_drafts(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_operation_plan_or_404(plan_id, db)
    existing_result = await db.execute(select(Content).where(Content.operation_plan_id == plan.id).order_by(Content.created_at.asc()))
    existing_contents = existing_result.scalars().all()
    if existing_contents:
        try:
            draft_specs = build_content_draft_specs_from_plan(
                operation_plan_id=plan.id,
                status=plan.status,
                plan_payload=plan.plan_payload,
                client_id=plan.client_id,
                author_id=current_user.id,
            )
        except OperationPlanDraftError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        for content, spec in zip(existing_contents, draft_specs, strict=False):
            if content.status in ("draft", "rejected"):
                content.title = spec["title"]
                content.text = spec["text"]
                content.hashtags = spec["hashtags"]
                content.post_type = spec["post_type"]
                content.source_metadata = {
                    **(content.source_metadata or {}),
                    **spec["source_metadata"],
                }
        await db.commit()
        for content in existing_contents:
            await db.refresh(content)

        manual_required_count = sum(
            1 for content in existing_contents if (content.source_metadata or {}).get("channel_action") == "manual_required"
        )
        token_check_required_count = sum(
            1 for content in existing_contents if (content.source_metadata or {}).get("channel_action") == "token_check_required"
        )
        return {
            "operation_plan_id": plan.id,
            "items": existing_contents,
            "total": len(existing_contents),
            "manual_required_count": manual_required_count,
            "token_check_required_count": token_check_required_count,
        }

    try:
        draft_specs = build_content_draft_specs_from_plan(
            operation_plan_id=plan.id,
            status=plan.status,
            plan_payload=plan.plan_payload,
            client_id=plan.client_id,
            author_id=current_user.id,
        )
    except OperationPlanDraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    contents = [
        Content(
            client_id=spec["client_id"],
            author_id=spec["author_id"],
            operation_plan_id=spec["operation_plan_id"],
            post_type=spec["post_type"],
            title=spec["title"],
            text=spec["text"],
            media_urls=spec["media_urls"],
            hashtags=spec["hashtags"],
            status=spec["status"],
            channel_connection_id=spec["channel_connection_id"],
            scheduled_at=spec["scheduled_at"],
            source_metadata=spec["source_metadata"],
        )
        for spec in draft_specs
    ]
    db.add_all(contents)
    await db.commit()
    for content in contents:
        await db.refresh(content)

    manual_required_count = sum(
        1 for content in contents if (content.source_metadata or {}).get("channel_action") == "manual_required"
    )
    token_check_required_count = sum(
        1 for content in contents if (content.source_metadata or {}).get("channel_action") == "token_check_required"
    )
    return {
        "operation_plan_id": plan.id,
        "items": contents,
        "total": len(contents),
        "manual_required_count": manual_required_count,
        "token_check_required_count": token_check_required_count,
    }
