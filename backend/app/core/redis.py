import logging
from typing import Optional
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def get_redis_pool() -> ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        pool = await get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
    return _redis_client


async def close_redis() -> None:
    global _redis_client, _redis_pool
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
