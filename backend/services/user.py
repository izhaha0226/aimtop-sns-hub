import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from models.user import User, UserStatus
from repositories.user import UserRepository
from schemas.user import UserListResponse, UserResponse, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)

    async def list_users(
        self,
        page: int = 1,
        size: int = 20,
    ) -> UserListResponse:
        offset = (page - 1) * size
        users, total = await self._repo.list_all(offset=offset, limit=size)
        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            size=size,
        )

    async def get_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return UserResponse.model_validate(user)

    async def update_user(
        self,
        user_id: uuid.UUID,
        data: UserUpdate,
    ) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        updates = data.model_dump(exclude_unset=True)
        updated = await self._repo.update(user, updates)
        return UserResponse.model_validate(updated)

    async def deactivate_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        updated = await self._repo.update(
            user,
            {"status": UserStatus.INACTIVE},
        )
        return UserResponse.model_validate(updated)
