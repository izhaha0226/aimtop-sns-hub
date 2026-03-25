import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.user import User
from schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from schemas.common import ApiResponse
from services.client import ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ApiResponse[ClientListResponse])
async def list_clients(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[ClientListResponse]:
    svc = ClientService(db)
    result = await svc.list_clients(page=page, size=size)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[ClientResponse])
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[ClientResponse]:
    svc = ClientService(db)
    client = await svc.create_client(body)
    return ApiResponse(data=client)


@router.get("/{client_id}", response_model=ApiResponse[ClientResponse])
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[ClientResponse]:
    svc = ClientService(db)
    client = await svc.get_client(client_id)
    return ApiResponse(data=client)


@router.put("/{client_id}", response_model=ApiResponse[ClientResponse])
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[ClientResponse]:
    svc = ClientService(db)
    client = await svc.update_client(client_id, body)
    return ApiResponse(data=client)


@router.delete("/{client_id}", response_model=ApiResponse[None])
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current: User = Depends(get_current_user),
) -> ApiResponse[None]:
    svc = ClientService(db)
    await svc.delete_client(client_id)
    return ApiResponse(message="Client deleted")
