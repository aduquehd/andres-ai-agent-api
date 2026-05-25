import json
import logging
from ipaddress import ip_address as parse_ip

import httpx
from redis.exceptions import RedisError

from config import settings
from modules.utils.redis import get_redis


logger = logging.getLogger(__name__)

GEO_CACHE_PREFIX = "geo:"
# IP → location mappings are extremely stable. A 30-day TTL keeps the
# ipapi.co free tier well under quota for repeat visitors and shared
# egress IPs (offices, mobile carriers) without going stale in practice.
GEO_CACHE_TTL_SECONDS = 60 * 60 * 24 * 30

EMPTY_GEO: dict[str, str | None] = {"country": None, "region": None, "city": None}


def _is_public_ip(ip: str) -> bool:
    """True only for routable, non-private IPs we can geolocate."""
    if not ip or ip == "unknown":
        return False
    try:
        return parse_ip(ip).is_global
    except ValueError:
        return False


async def get_geographic_data(ip: str) -> dict[str, str | None]:
    """Look up country/region/city for an IP.

    Reads/writes a Redis cache keyed by IP so each IP only hits ipapi.co
    once per TTL window. Falls back to a live API call when the cache is
    unavailable or missing the key. Always returns the standard
    country/region/city dict (values may be ``None``).
    """
    if not _is_public_ip(ip):
        return dict(EMPTY_GEO)

    cache_key = f"{GEO_CACHE_PREFIX}{ip}"
    redis_client = get_redis()

    if redis_client is not None:
        try:
            cached = await redis_client.get(cache_key)
        except RedisError as exc:
            logger.warning("Redis GET failed for %s: %s", cache_key, exc)
            cached = None
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.warning("Discarding malformed geo cache for %s", ip)

    geo = await _fetch_from_ipapi(ip)

    # Only cache successful lookups — caching empty results would lock in
    # transient failures (rate limits, network blips) for 30 days.
    if redis_client is not None and any(geo.values()):
        try:
            await redis_client.set(cache_key, json.dumps(geo), ex=GEO_CACHE_TTL_SECONDS)
        except RedisError as exc:
            logger.warning("Redis SET failed for %s: %s", cache_key, exc)

    return geo


async def _fetch_from_ipapi(ip: str) -> dict[str, str | None]:
    """Call ipapi.co once. Returns EMPTY_GEO on any failure."""
    url = f"https://ipapi.co/{ip}/json/"
    params: dict[str, str] = {}
    if settings.ipapi_secret_api_key:
        params["key"] = settings.ipapi_secret_api_key

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("ipapi.co lookup failed for %s: %s", ip, exc)
        return dict(EMPTY_GEO)

    # ipapi.co signals errors via a JSON body (e.g. rate-limited, reserved
    # range) rather than an HTTP error status.
    if data.get("error"):
        logger.warning("ipapi.co error for %s: %s", ip, data.get("reason"))
        return dict(EMPTY_GEO)

    return {
        "country": data.get("country_code"),
        "region": data.get("region"),
        "city": data.get("city"),
    }
