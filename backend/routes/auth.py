from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from middleware.auth import get_current_user
from models.user import User, UserRole
from schemas.auth import (
    AcceptInviteRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InviteRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _build_reset_link(token: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}" + f"/forgot-password/reset?token={token}"


def _build_invite_link(token: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}" + f"/signup?invite={token}"


def _email_body(title: str, message: str, action_url: str | None = None) -> str:
    if action_url:
        return (
            f"<h2>{title}</h2>"
            f"<p>{message}</p>"
            f"<p><a href='{action_url}'>바로 이동</a></p>"
            f"<p style='color:#888'>만료된 링크는 무효화됩니다.</p>"
        )
    return f"<h2>{title}</h2><p>{message}</p>"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")
        return TokenResponse(
            access_token=create_access_token(str(user.id), user.role),
            refresh_token=create_refresh_token(str(user.id)),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")


@router.post("/logout")
async def logout():
    return {"message": "로그아웃 되었습니다"}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        # 계정 존재 여부 노출 방지
        return {"message": "해당 이메일로 재설정 링크를 발송했습니다"}

    token = create_access_token(str(user.id), "reset")
    reset_link = _build_reset_link(token)

    sent = await NotificationService(db).send_email(
        to_email=user.email,
        subject="[SNS Hub] 비밀번호 재설정",
        body=_email_body("비밀번호 재설정", "아래 버튼을 클릭해서 비밀번호를 재설정하세요.", reset_link),
    )

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="이메일 발송에 실패했습니다. 관리자에게 문의하세요.",
        )

    return {"message": "해당 이메일로 재설정 링크를 발송했습니다"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.token)
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="유효하지 않은 요청입니다")
        user.hashed_password = hash_password(body.new_password)
        await db.commit()
        return {"message": "비밀번호가 변경되었습니다"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="유효하지 않은 토큰입니다")


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다"
        )
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"message": "비밀번호가 변경되었습니다"}


@router.post("/invite")
async def invite_user(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 초대할 수 있습니다"
        )
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다"
        )
    new_user = User(
        name=body.name,
        email=body.email,
        hashed_password="",
        role=body.role,
        status="inactive",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    invite_token = create_access_token(str(new_user.id), "invite")
    invite_link = _build_invite_link(invite_token)

    sent = await NotificationService(db).send_email(
        to_email=new_user.email,
        subject="[SNS Hub] 초대 안내",
        body=_email_body("SNS Hub 초대", f"{body.name}님, 아래 링크로 가입을 완료하세요.", invite_link),
    )

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="초대 메일 발송에 실패했습니다. 관리자에게 문의하세요.",
        )

    return {"message": "초대가 발송되었습니다", "invite_token": invite_token}


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(body.token)
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="유효하지 않은 초대입니다")
        user.hashed_password = hash_password(body.password)
        user.status = "active"
        await db.commit()
        return TokenResponse(
            access_token=create_access_token(str(user.id), user.role),
            refresh_token=create_refresh_token(str(user.id)),
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="유효하지 않은 초대 토큰입니다")
