from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from core.config import get_settings

_pool: aioredis.Redis | None = None


def _get_pool() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            get_settings().REDIS_URL,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = _get_pool()
    try:
        yield client
    finally:
        pass


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
