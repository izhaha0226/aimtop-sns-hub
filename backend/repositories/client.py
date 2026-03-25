import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.client import Client, ClientUser
from repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession):
        super().__init__(Client, session)

    async def assign_user(
        self,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ClientUser:
        cu = ClientUser(
            client_id=client_id,
            user_id=user_id,
            assigned_at=datetime.now(timezone.utc),
        )
        self._session.add(cu)
        await self._session.flush()
        return cu

    async def unassign_user(
        self,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        stmt = delete(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.user_id == user_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()
