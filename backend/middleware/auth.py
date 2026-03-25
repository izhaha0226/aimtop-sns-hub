import uuid

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import ForbiddenError, UnauthorizedError
from core.security import decode_token
from models.user import User, UserRole
from repositories.user import UserRepository


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    payload = _decode_access(token)
    user_id = _parse_user_id(payload)
    return await _fetch_user(db, user_id)


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise ForbiddenError("Admin access required")
    return user


def _extract_bearer(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Invalid authorization header")
    return authorization[7:]


def _decode_access(token: str) -> dict:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    return payload


def _parse_user_id(payload: dict) -> uuid.UUID:
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token payload") from exc


async def _fetch_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User not found")
    return user
