from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_admin
from models.user import User
from schemas.app_secret import AppSecretResponse, AppSecretUpdateRequest
from services.runtime_settings import list_secret_settings, upsert_secret_setting, SECRET_CATALOG

router = APIRouter(prefix="/api/v1/admin/secrets", tags=["admin-secrets"])


@router.get("", response_model=list[AppSecretResponse])
async def get_secrets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await list_secret_settings(db)


@router.put("/{secret_key}", response_model=AppSecretResponse)
async def update_secret(
    secret_key: str,
    body: AppSecretUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if secret_key not in SECRET_CATALOG:
        raise HTTPException(status_code=404, detail="지원하지 않는 시크릿 키입니다")
    try:
        await upsert_secret_setting(
            db,
            secret_key=secret_key,
            value=body.value,
            is_active=body.is_active,
            updated_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    secrets = await list_secret_settings(db)
    for item in secrets:
        if item["secret_key"] == secret_key:
            return item
    raise HTTPException(status_code=500, detail="시크릿 저장 후 조회에 실패했습니다")
