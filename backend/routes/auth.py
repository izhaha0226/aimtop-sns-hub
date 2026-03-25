from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.auth import (
    AcceptInviteRequest,
    ForgotPasswordRequest,
    InviteRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from schemas.common import ApiResponse
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    svc = AuthService(db)
    tokens = await svc.login(body.email, body.password)
    return ApiResponse(data=tokens)


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    svc = AuthService(db)
    tokens = await svc.refresh_token(body.refresh_token)
    return ApiResponse(data=tokens)


@router.post("/logout", response_model=ApiResponse[None])
async def logout() -> ApiResponse[None]:
    return ApiResponse(message="Logged out")


@router.post("/invite", response_model=ApiResponse[dict])
async def invite(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    svc = AuthService(db)
    token = await svc.create_invite(body.email, body.name, body.role)
    return ApiResponse(data={"invite_token": token})


@router.post("/accept-invite", response_model=ApiResponse[TokenResponse])
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    svc = AuthService(db)
    tokens = await svc.accept_invite(body.token, body.password)
    return ApiResponse(data=tokens)


@router.post("/forgot-password", response_model=ApiResponse[dict])
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    svc = AuthService(db)
    token = await svc.forgot_password(body.email)
    return ApiResponse(data={"reset_token": token})


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    svc = AuthService(db)
    await svc.reset_password(body.token, body.new_password)
    return ApiResponse(message="Password reset successful")
