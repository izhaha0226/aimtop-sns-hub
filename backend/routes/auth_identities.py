import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.auth_identity import AuthIdentityCreateRequest, AuthIdentityResponse, AuthIdentityUpdateRequest
from services.auth_identity_service import AuthIdentityService

router = APIRouter(prefix="/api/v1/auth/identities", tags=["auth-identities"])


@router.get("", response_model=list[AuthIdentityResponse])
async def list_identities(
    client_id: uuid.UUID | None = Query(default=None),
    current_user_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AuthIdentityService(db)
    return await svc.list_identities(
        client_id=client_id,
        user_id=current_user.id if current_user_only else None,
    )


@router.post("", response_model=AuthIdentityResponse)
async def create_identity(
    body: AuthIdentityCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AuthIdentityService(db)
    return await svc.create_identity(user_id=current_user.id, **body.model_dump())


@router.patch("/{identity_id}", response_model=AuthIdentityResponse)
async def update_identity(
    identity_id: uuid.UUID,
    body: AuthIdentityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = AuthIdentityService(db)
    identity = await svc.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Auth identity not found")
    return await svc.update_identity(identity, **body.model_dump(exclude_none=True))
