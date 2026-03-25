import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self._model = model
        self._session = session

    async def get_by_id(self, record_id: uuid.UUID) -> ModelType | None:
        stmt = select(self._model).where(self._model.id == record_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: list[Any] | None = None,
    ) -> tuple[list[ModelType], int]:
        stmt = select(self._model)
        count_stmt = select(func.count()).select_from(self._model)

        for f in (filters or []):
            stmt = stmt.where(f)
            count_stmt = count_stmt.where(f)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, instance: ModelType) -> ModelType:
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(
        self,
        instance: ModelType,
        data: dict[str, Any],
    ) -> ModelType:
        for key, value in data.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self._session.delete(instance)
        await self._session.flush()
