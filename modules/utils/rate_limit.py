"""Rate limiting utilities using fastapi-limiter."""

from fastapi import Request

from modules.utils.request import get_client_ip


async def get_client_ip_identifier(request: Request) -> str:
    """
    Get client IP address as identifier for rate limiting.

    This uses the same IP extraction logic as the geo data implementation,
    handling CloudFlare, proxies, and load balancers.
    """
    return get_client_ip(request)
