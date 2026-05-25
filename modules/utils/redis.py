import os

import redis.asyncio as redis


_redis_client: redis.Redis | None = None


async def get_redis_url() -> str:
    """Get Redis connection URL."""
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")

    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        return f"redis://{redis_host}:{redis_port}/{redis_db}"


async def init_redis() -> redis.Redis:
    """Initialize the shared Redis client and store it for app-wide access."""
    global _redis_client
    redis_url = await get_redis_url()
    _redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    return _redis_client


def get_redis() -> redis.Redis | None:
    """Return the shared Redis client, or None if it hasn't been initialized."""
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
