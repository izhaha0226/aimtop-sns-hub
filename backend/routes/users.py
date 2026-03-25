import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user, require_admin
from models.user import User
from schemas.common import ApiResponse
from schemas.user import UserListResponse, UserResponse, UserUpdate
from services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=ApiResponse[UserListResponse])
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ApiResponse[UserListResponse]:
    svc = UserService(db)
    result = await svc.list_users(page=page, size=size)
    return ApiResponse(data=result)


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    svc = UserService(db)
    user = await svc.get_user(user_id)
    return ApiResponse(data=user)


@router.put("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    svc = UserService(db)
    user = await svc.update_user(user_id, body)
    return ApiResponse(data=user)


@router.patch(
    "/{user_id}/deactivate",
    response_model=ApiResponse[UserResponse],
)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ApiResponse[UserResponse]:
    svc = UserService(db)
    user = await svc.deactivate_user(user_id)
    return ApiResponse(data=user)
