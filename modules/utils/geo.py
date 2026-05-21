import requests

from config import settings


def _is_private_172_range(ip_address: str) -> bool:
    """Check if IP is in the private 172.16.0.0/12 range (172.16.0.0 - 172.31.255.255)."""
    if not ip_address.startswith("172."):
        return False

    try:
        parts = ip_address.split(".")
        if len(parts) != 4:
            return False

        second_octet = int(parts[1])
        # Private range is 172.16.x.x to 172.31.x.x
        return 16 <= second_octet <= 31
    except (ValueError, IndexError):
        return False


def get_geographic_data(ip_address: str) -> dict:
    """Get geographic information from IP address using ipapi.co (free tier)."""
    # Check for private/local IP addresses
    if (
        ip_address in ["unknown", "127.0.0.1", "::1"]
        or ip_address.startswith("192.168.")
        or ip_address.startswith("10.")
        or _is_private_172_range(ip_address)
    ):
        print(f"  Skipping private/local IP: {ip_address}")
        return {"country": None, "region": None, "city": None}

    try:
        url = f"https://ipapi.co/{ip_address}/json/"
        if settings.ipapi_secret_api_key:
            url += f"?key={settings.ipapi_secret_api_key}"

        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            print(f"  API response for {ip_address}: {data}")
            return {
                "country": data.get("country_code"),
                "region": data.get("region"),
                "city": data.get("city"),
            }
        else:
            print(f"  API error for {ip_address}: Status {response.status_code}")
    except Exception as e:
        print(f"  API exception for {ip_address}: {str(e)}")

    return {"country": None, "region": None, "city": None}
