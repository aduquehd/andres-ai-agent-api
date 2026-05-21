#!/usr/bin/env python
"""Test script for fastapi-limiter rate limiting functionality."""

import asyncio
import os

# Add parent directory to path
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from modules.utils.redis import get_redis_url, init_redis


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    try:
        redis_url = await get_redis_url()
        print(f"Redis URL: {redis_url.replace(':' + os.getenv('REDIS_PASSWORD', ''), ':***')}")

        client = await init_redis()

        # Test set and get
        await client.set("test_key", "test_value")
        value = await client.get("test_key")
        assert value == "test_value", f"Expected 'test_value', got {value}"

        # Clean up
        await client.delete("test_key")

        print("✅ Redis connection successful!")
        return True, client
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False, None


async def test_fastapi_limiter_init(redis_client):
    """Test FastAPI Limiter initialization."""
    print("\nTesting FastAPI Limiter initialization...")
    try:
        await FastAPILimiter.init(redis_client)
        print("✅ FastAPI Limiter initialized successfully!")

        # Test that the limiter is working
        # This would normally be tested via actual HTTP requests
        print("ℹ️  Rate limiting will be enforced on HTTP requests to:")
        print("    - GET /api/chats/history (100 req/min per IP)")
        print("    - POST /api/chats/send (30 req/min per IP)")

        return True
    except Exception as e:
        print(f"❌ FastAPI Limiter initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 50)
    print("FastAPI Limiter Rate Limiting Test Suite")
    print("=" * 50)

    redis_ok, redis_client = await test_redis_connection()

    if redis_ok and redis_client:
        limiter_ok = await test_fastapi_limiter_init(redis_client)
    else:
        print("\n⚠️  Skipping FastAPI Limiter test due to Redis connection failure")
        limiter_ok = False

    # Close connections
    if redis_client:
        await FastAPILimiter.close()
        await redis_client.close()

    print("\n" + "=" * 50)
    if redis_ok and limiter_ok:
        print("✅ All tests passed!")
        print("\nRate limiting is configured to use IP addresses from:")
        print("  1. CF-Connecting-IP header (CloudFlare)")
        print("  2. X-Forwarded-For header (proxies/load balancers)")
        print("  3. X-Real-IP header (nginx)")
        print("  4. Client host (direct connection)")
    else:
        print("❌ Some tests failed")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
