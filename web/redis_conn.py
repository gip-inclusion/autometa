"""Redis async connection pool."""

import redis.asyncio as aioredis

from . import config

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is not None:
        try:
            await _pool.ping()
        except ConnectionError, RuntimeError, OSError:
            _pool = None
    if _pool is None:
        _pool = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    return _pool


async def close_redis():
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
