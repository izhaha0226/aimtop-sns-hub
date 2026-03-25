from datetime import datetime, timezone

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from models.user import User, UserRole, UserStatus
from repositories.user import UserRepository
from schemas.auth import TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)
        self._session = session

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._repo.get_by_email(email)
        if user is None or user.hashed_password is None:
            raise UnauthorizedError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        return self._build_tokens(user)

    async def refresh_token(self, token: str) -> TokenResponse:
        payload = self._decode_refresh(token)
        user = await self._repo.get_by_id(payload["sub"])
        if user is None:
            raise UnauthorizedError("User not found")
        return self._build_tokens(user)

    async def create_invite(
        self,
        email: str,
        name: str,
        role: str,
    ) -> str:
        existing = await self._repo.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = User(
            name=name,
            email=email,
            role=UserRole(role),
            status=UserStatus.INVITED,
        )
        await self._repo.create(user)
        return create_access_token({"sub": str(user.id), "type": "invite"})

    async def accept_invite(self, token: str, password: str) -> TokenResponse:
        payload = self._decode_invite(token)
        user = await self._repo.get_by_id(payload["sub"])
        if user is None:
            raise NotFoundError("User not found")

        await self._repo.update(user, {
            "hashed_password": hash_password(password),
            "status": UserStatus.ACTIVE,
        })
        return self._build_tokens(user)

    async def forgot_password(self, email: str) -> str:
        user = await self._repo.get_by_email(email)
        if user is None:
            raise NotFoundError("User not found")
        return create_access_token({"sub": str(user.id), "type": "reset"})

    async def reset_password(self, token: str, new_password: str) -> None:
        payload = self._decode_reset(token)
        user = await self._repo.get_by_id(payload["sub"])
        if user is None:
            raise NotFoundError("User not found")
        await self._repo.update(user, {
            "hashed_password": hash_password(new_password),
        })

    def _build_tokens(self, user: User) -> TokenResponse:
        data = {"sub": str(user.id), "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(data),
            refresh_token=create_refresh_token(data),
        )

    def _decode_refresh(self, token: str) -> dict:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")
        return payload

    def _decode_invite(self, token: str) -> dict:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid invite token") from exc
        if payload.get("type") != "invite":
            raise UnauthorizedError("Invalid token type")
        return payload

    def _decode_reset(self, token: str) -> dict:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid reset token") from exc
        if payload.get("type") != "reset":
            raise UnauthorizedError("Invalid token type")
        return payload
