from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from core.database import get_db
from core.redis import get_redis
from schemas.common import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict])
async def health_check(
    db: AsyncSession = Depends(get_db),
    rd: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[dict]:
    db_ok = await _check_db(db)
    redis_ok = await _check_redis(rd)
    status = {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    return ApiResponse(data=status)


async def _check_db(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis(rd: aioredis.Redis) -> bool:
    try:
        await rd.ping()
        return True
    except Exception:
        return False
