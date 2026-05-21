from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract client IP address, handling proxies and load balancers."""
    # Check CF-Connecting-IP header (Cloudflare proxy)
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip:
        return cf_connecting_ip.strip()

    # Check X-Forwarded-For header (common with proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (nginx proxy)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to client.host (direct connection)
    if request.client:
        return request.client.host

    return "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent string from request headers."""
    return request.headers.get("User-Agent", "unknown")


def get_browser_id(request: Request) -> str:
    """Extract browser ID from request headers."""
    return request.headers.get("X-Browser-Id", "unknown")
