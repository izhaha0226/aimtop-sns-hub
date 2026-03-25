import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from models.client import Client
from repositories.client import ClientRepository
from schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)


class ClientService:
    def __init__(self, session: AsyncSession):
        self._repo = ClientRepository(session)

    async def list_clients(
        self,
        page: int = 1,
        size: int = 20,
    ) -> ClientListResponse:
        offset = (page - 1) * size
        filters = [Client.is_deleted == False]  # noqa: E712
        clients, total = await self._repo.list_all(
            offset=offset,
            limit=size,
            filters=filters,
        )
        return ClientListResponse(
            items=[ClientResponse.model_validate(c) for c in clients],
            total=total,
            page=page,
            size=size,
        )

    async def create_client(self, data: ClientCreate) -> ClientResponse:
        client = Client(**data.model_dump())
        created = await self._repo.create(client)
        return ClientResponse.model_validate(created)

    async def get_client(self, client_id: uuid.UUID) -> ClientResponse:
        client = await self._repo.get_by_id(client_id)
        if client is None or client.is_deleted:
            raise NotFoundError("Client not found")
        return ClientResponse.model_validate(client)

    async def update_client(
        self,
        client_id: uuid.UUID,
        data: ClientUpdate,
    ) -> ClientResponse:
        client = await self._repo.get_by_id(client_id)
        if client is None or client.is_deleted:
            raise NotFoundError("Client not found")
        updates = data.model_dump(exclude_unset=True)
        updated = await self._repo.update(client, updates)
        return ClientResponse.model_validate(updated)

    async def delete_client(self, client_id: uuid.UUID) -> None:
        client = await self._repo.get_by_id(client_id)
        if client is None or client.is_deleted:
            raise NotFoundError("Client not found")
        await self._repo.update(client, {"is_deleted": True})
