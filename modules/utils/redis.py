import os

import redis.asyncio as redis


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
    """Initialize Redis connection for fastapi-limiter."""
    redis_url = await get_redis_url()
    return redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
