import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.threads_automation import (
    ActionCreateRequest,
    ActionLogResponse,
    ApprovalResponse,
    ApprovalStatusRequest,
    DraftCreateRequest,
    DraftResponse,
    DraftUpdateRequest,
    LearningEventCreateRequest,
    LearningEventResponse,
    PersonaCreateRequest,
    PersonaResponse,
    PersonaUpdateRequest,
    SafetyFilterCreateRequest,
    SafetyFilterResponse,
    SafetyFilterUpdateRequest,
    TargetRuleCreateRequest,
    TargetRuleResponse,
    TargetRuleUpdateRequest,
)
from services.threads_automation_service import ThreadsAutomationService

router = APIRouter(prefix="/api/v1/threads-automation", tags=["threads-automation"])


@router.get("/personas", response_model=list[PersonaResponse])
async def list_personas(
    client_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_personas(client_id)


@router.post("/personas", response_model=PersonaResponse)
async def create_persona(
    body: PersonaCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).create_persona(**body.model_dump())


@router.patch("/personas/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: uuid.UUID,
    body: PersonaUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = ThreadsAutomationService(db)
    persona = await svc.get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Threads persona not found")
    return await svc.update_persona(persona, **body.model_dump(exclude_none=True))


@router.get("/target-rules", response_model=list[TargetRuleResponse])
async def list_target_rules(
    client_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_target_rules(client_id)


@router.post("/target-rules", response_model=TargetRuleResponse)
async def create_target_rule(
    body: TargetRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).create_target_rule(**body.model_dump())


@router.patch("/target-rules/{rule_id}", response_model=TargetRuleResponse)
async def update_target_rule(
    rule_id: uuid.UUID,
    body: TargetRuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = ThreadsAutomationService(db)
    rule = await svc.get_target_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Threads target rule not found")
    return await svc.update_target_rule(rule, **body.model_dump(exclude_none=True))


@router.get("/safety-filters", response_model=list[SafetyFilterResponse])
async def list_safety_filters(
    client_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_safety_filters(client_id)


@router.post("/safety-filters", response_model=SafetyFilterResponse)
async def create_safety_filter(
    body: SafetyFilterCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).create_safety_filter(**body.model_dump())


@router.patch("/safety-filters/{filter_id}", response_model=SafetyFilterResponse)
async def update_safety_filter(
    filter_id: uuid.UUID,
    body: SafetyFilterUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = ThreadsAutomationService(db)
    safety_filter = await svc.get_safety_filter(filter_id)
    if not safety_filter:
        raise HTTPException(status_code=404, detail="Threads safety filter not found")
    return await svc.update_safety_filter(safety_filter, **body.model_dump(exclude_none=True))


@router.get("/drafts", response_model=list[DraftResponse])
async def list_drafts(
    client_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_drafts(client_id=client_id, status=status)


@router.post("/drafts", response_model=DraftResponse)
async def create_draft(
    body: DraftCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).create_draft(requested_by_id=current_user.id, **body.model_dump())


@router.patch("/drafts/{draft_id}", response_model=DraftResponse)
async def update_draft(
    draft_id: uuid.UUID,
    body: DraftUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = ThreadsAutomationService(db)
    draft = await svc.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Threads draft not found")
    return await svc.update_draft(draft, **body.model_dump(exclude_none=True))


@router.get("/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    client_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_approvals(client_id=client_id, status=status)


@router.patch("/approvals/{approval_id}/status", response_model=ApprovalResponse)
async def update_approval_status(
    approval_id: uuid.UUID,
    body: ApprovalStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ThreadsAutomationService(db)
    approval = await svc.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Threads approval item not found")
    return await svc.update_approval_status(
        approval,
        status=body.status,
        reviewed_by_id=current_user.id,
        review_note=body.review_note,
    )


@router.get("/actions", response_model=list[ActionLogResponse])
async def list_actions(
    client_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_actions(client_id)


@router.post("/actions", response_model=ActionLogResponse)
async def create_action(
    body: ActionCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).create_action_log(**body.model_dump())


@router.get("/learning", response_model=list[LearningEventResponse])
async def list_learning_events(
    client_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).list_learning_events(client_id)


@router.post("/learning", response_model=LearningEventResponse)
async def create_learning_event(
    body: LearningEventCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ThreadsAutomationService(db).create_learning_event(**body.model_dump())
