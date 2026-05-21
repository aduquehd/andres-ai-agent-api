"""Admin authentication using JWT issued as an httpOnly cookie."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Cookie, HTTPException, status

from config import settings


ADMIN_COOKIE_NAME = "admin_session"
ADMIN_TOKEN_TTL_HOURS = 12
JWT_ALGORITHM = "HS256"


def verify_admin_credentials(username: str, password: str) -> bool:
    """Constant-time comparison against configured admin credentials."""
    correct_user = secrets.compare_digest(
        username.encode("utf-8"), settings.admin_user.encode("utf-8")
    )
    correct_pw = secrets.compare_digest(
        password.encode("utf-8"), settings.admin_password.encode("utf-8")
    )
    return correct_user and correct_pw


def create_admin_token(username: str) -> str:
    """Issue a JWT for an authenticated admin session."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ADMIN_TOKEN_TTL_HOURS)).timestamp()),
        "scope": "admin",
    }
    return jwt.encode(payload, settings.fastapi_admin_secret_key, algorithm=JWT_ALGORITHM)


def decode_admin_token(token: str) -> dict:
    return jwt.decode(token, settings.fastapi_admin_secret_key, algorithms=[JWT_ALGORITHM])


def require_admin(
    token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE_NAME)] = None,
) -> str:
    """FastAPI dependency: returns the admin username, or 401."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = decode_admin_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        ) from exc

    if payload.get("scope") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    return payload.get("sub", "")
