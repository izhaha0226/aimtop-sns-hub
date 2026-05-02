import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.benchmarking import (
    ActionLanguageProfileResponse,
    BenchmarkAccountCreateRequest,
    BenchmarkAccountDiagnosticResponse,
    BenchmarkAccountResponse,
    BenchmarkAccountUpdateRequest,
    BenchmarkPostResponse,
    RefreshAccountResponse,
)
from services.benchmark_collector_service import BenchmarkCollectorService

router = APIRouter(prefix="/api/v1/benchmarking", tags=["benchmarking"])


@router.get("/accounts", response_model=list[BenchmarkAccountResponse])
async def list_accounts(
    client_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    return await svc.list_accounts(client_id)


@router.post("/accounts", response_model=BenchmarkAccountResponse)
async def create_account(
    body: BenchmarkAccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    return await svc.create_account(**body.model_dump())


@router.patch("/accounts/{account_id}", response_model=BenchmarkAccountResponse)
async def update_account(
    account_id: uuid.UUID,
    body: BenchmarkAccountUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    account = await svc.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Benchmark account not found")
    return await svc.update_account(account, **body.model_dump(exclude_none=True))


@router.post("/accounts/{account_id}/refresh", response_model=RefreshAccountResponse)
async def refresh_account(
    account_id: uuid.UUID,
    top_k: int = Query(default=10, ge=1, le=50),
    window_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    account = await svc.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Benchmark account not found")
    return await svc.refresh_account(account, top_k=top_k, window_days=window_days)


@router.get("/account-diagnostics", response_model=list[BenchmarkAccountDiagnosticResponse])
async def list_account_diagnostics(
    client_id: uuid.UUID,
    platform: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    return await svc.list_account_diagnostics(client_id=client_id, platform=platform)


@router.get("/top-posts", response_model=list[BenchmarkPostResponse])
async def get_top_posts(
    client_id: uuid.UUID,
    platform: str,
    top_k: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    return await svc.get_top_posts(client_id, platform, top_k)


@router.get("/action-language-profile", response_model=ActionLanguageProfileResponse | None)
async def get_action_language_profile(
    client_id: uuid.UUID,
    platform: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = BenchmarkCollectorService(db)
    profile = await svc.get_action_language_profile(client_id, platform)
    if profile is None:
        return None
    return profile
